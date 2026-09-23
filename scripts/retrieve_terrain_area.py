#!/usr/bin/env python3
"""Retrieve a bounded native-grid diagnostic window from explicitly pinned DEMs.

No reprojection, resampling, mosaic, source preference or slope calculation.
RangeFile enforces 8 MiB per source; request permits at most two sources.
"""
import argparse
import json
import math
from pathlib import Path
import tempfile
import hashlib
import numpy as np
import rasterio
from rasterio.enums import MaskFlags
from rasterio.windows import Window, bounds as window_bounds
from rasterio.transform import from_origin
import tifffile
from shapely import wkb
from shapely.geometry import box
from investigate_terrain_readiness import Capture, RangeFile, sha


def checked_window(values, width, height):
    if len(values)!=4 or any(type(v) is not int for v in values):
        raise ValueError('Window must contain four integers')
    col,row,w,h=values
    if min(col,row)<0 or min(w,h)<1 or w*h>1024*1024:
        raise ValueError('Window outside pixel budget')
    if col+w>width or row+h>height: raise ValueError('Window outside raster')
    return Window(col,row,w,h)


def retrieve(cap, expected, values, index, output):
    remote=RangeFile(cap,{'downloadURL':expected['url']},index)
    if remote.etag!=expected['etag'] or remote.size!=expected['current_file_bytes']:
        raise ValueError('Pinned source version changed; review before retrieval')
    with tifffile.TiffFile(remote) as tif:
        page=tif.pages[0]
        for hp in tif.pages:
            for tag in hp.tags.values(): _=tag.value
        if not page.is_tiled or page.samplesperpixel!=1:
            raise ValueError('Only single-band tiled sources supported')
        win=checked_window(values,page.imagewidth,page.imagelength)
        tw,th=page.tilewidth,page.tilelength;nx=math.ceil(page.imagewidth/tw)
        col,row,width,height=values
        blocks=[]
        for y in range(row//th,(row+height-1)//th+1):
            for x in range(col//tw,(col+width-1)//tw+1):
                k=y*nx+x;remote.seek(page.dataoffsets[k]);remote.read(page.databytecounts[k]);blocks.append([y,x])
        with tempfile.NamedTemporaryFile(suffix='.tif') as sparse:
            sparse.truncate(remote.size)
            for offset,data in remote.parts:sparse.seek(offset);sparse.write(data)
            sparse.flush()
            with rasterio.open(sparse.name) as ds:
                if ds.mask_flag_enums!=([MaskFlags.nodata],):
                    raise ValueError('Only NoData-derived masks supported; separate masks require explicit capture')
                for key,value in [('width',ds.width),('height',ds.height),('bounds',list(ds.bounds)),('resolution',list(ds.res)),('crs_wkt',ds.crs.to_wkt()),('nodata',ds.nodata),('dtype',ds.dtypes[0])]:
                    if expected[key]!=value:raise ValueError('Source header mismatch: '+key)
                if ds.transform!=from_origin(ds.bounds.left,ds.bounds.top,*ds.res):
                    raise ValueError('Only north-up, unrotated source grids supported')
                arr=ds.read(1,window=win);transform=ds.window_transform(win)
                mask=arr==ds.nodata if not np.isnan(ds.nodata) else np.isnan(arr)
                nonfinite=~np.isfinite(arr)&~mask;valid=~mask&~nonfinite
                profile={'driver':'GTiff','width':width,'height':height,'count':1,'dtype':ds.dtypes[0],
                    'crs':ds.crs,'transform':transform,'nodata':ds.nodata,'compress':'deflate'}
                with rasterio.open(output,'w',**profile) as subset:
                    subset.write(arr,1)
                    subset.update_tags(evidence_state='DERIVED',source_id=expected['source_id'],source_etag=remote.etag,
                        operation='Native pixel window; no resampling or datum adjustment')
                with rasterio.open(output) as check:
                    if not np.array_equal(arr,check.read(1),equal_nan=True):raise ValueError('Subset readback mismatch')
                return {'source_id':expected['source_id'],'etag':remote.etag,'source_file_bytes':remote.size,
                    'window':values,'bounds':list(window_bounds(win,ds.transform)),'epsg':ds.crs.to_epsg(),
                    'crs_wkt':ds.crs.to_wkt(),'resolution':list(ds.res),'nodata':ds.nodata,
                    'pixels':width*height,'nodata_pixels':int(mask.sum()),'nonfinite_unmasked_pixels':int(nonfinite.sum()),
                    'valid_pixels':int(valid.sum()),'valid_fraction':float(valid.sum()/(width*height)),
                    'valid_area_m2':float(valid.sum()*abs(transform.a*transform.e)),
                    'coverage':'full_native_pixel_coverage' if valid.all() else 'partial_native_pixel_coverage',
                    'raster_transfer_bytes':remote.used,'captured_blocks':blocks,'subset_file':output.name,
                    'subset_bytes':output.stat().st_size,'subset_sha256':sha(output),'analysis_qualified':False}


def run(request_path, readiness_path, boundary_path, out):
    req=json.loads(request_path.read_text());report=json.loads(readiness_path.read_text());boundary=json.loads(boundary_path.read_text())['boundary']
    if req.get('epsg')!=26919: raise ValueError('Request CRS must be EPSG26919')
    if req['readiness_sha256']!=sha(readiness_path):raise ValueError('Readiness report changed')
    if not 1<=len(req['source_ids'])<=2 or len(set(req['source_ids']))!=len(req['source_ids']):raise ValueError('One or two distinct sources required')
    raw=bytes.fromhex(boundary['wkb_hex'])
    if hashlib.sha256(raw).hexdigest()!=req['county_boundary_sha256'] or boundary['srid']!=26919:raise ValueError('Boundary version/CRS mismatch')
    county=wkb.loads(raw)
    expected=[next(p['raster'] for p in report['projects'] if p['representative_source_id']==sid) for sid in req['source_ids']]
    for r in expected:
        win=checked_window(req['window'],r['width'],r['height'])
        if r['epsg']!=26919 or r['resolution']!=[1.0,1.0]:raise ValueError('Pilot supports native one-meter EPSG26919 only')
        transform=from_origin(r['bounds'][0],r['bounds'][3],*r['resolution'])
        bounds=list(window_bounds(win,transform))
        if bounds!=req['bounds'] or not county.contains(box(*bounds)):raise ValueError('AOI must exactly match native window and lie within pinned county')
    cap=Capture(out)
    (out/'request.json').write_bytes(request_path.read_bytes())
    result={'evidence_state':'DERIVED','request_sha256':sha(request_path),'readiness_sha256':sha(readiness_path),
        'county_boundary_sha256':req['county_boundary_sha256'],'method_sha256':sha(__file__),
        'range_reader_sha256':sha(Path(__file__).with_name('investigate_terrain_readiness.py')),
        'runtime':{'rasterio':rasterio.__version__,'gdal':rasterio.__gdal_version__,'tifffile':tifffile.__version__},
        'diagnostic_only':True,'max_raster_transfer_bytes':len(expected)*8*1024*1024,'sources':[],
        'limits':['Pinned catalog selection is not refreshed county-wide discovery. Source currency, date conflicts and datum/accuracy qualification remain separate.',
          'Native rectangular diagnostic area only; no parcel identity, slope, source priority, county availability or buildability qualification.',
          'Subset is a DERIVED lossless window; archived source ranges are exact original bytes, not a complete source TIFF.']}
    try:
        for i,r in enumerate(expected):
            result['sources'].append(retrieve(cap,r,req['window'],i,out/f'{i}-subset.tif'))
        result['status']='retrieved_not_qualified'
    except Exception as e:
        result['status']='failed';result['error']=f'{type(e).__name__}: {e}'
        (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');raise
    result['raster_transfer_bytes']=sum(x['raster_transfer_bytes'] for x in result['sources'])
    result['subset_bytes']=sum(x['subset_bytes'] for x in result['sources'])
    result['sources_sha256']=sha(out/'sources.json')
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request',type=Path,required=True);p.add_argument('--readiness',type=Path,default=Path('research/terrain-readiness/report.json'))
    p.add_argument('--boundary',type=Path,default=Path('research/piscataquis-ingestion/report.json'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.request,a.readiness,a.boundary,a.output)
