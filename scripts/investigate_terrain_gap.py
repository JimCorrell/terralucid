#!/usr/bin/env python3
"""Inspect catalog alternatives and retrieve bounded native windows around a pilot gap.

No resampling or mosaicking. Header discovery and pixel retrieval each have the
existing 8 MiB/source cap; at most two alternatives (32 MiB aggregate raster cap).
"""
import argparse
import json
import math
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds,Window,bounds as window_bounds
from rasterio.transform import from_origin
from shapely import wkb
from shapely.geometry import box
import tifffile
from investigate_terrain_readiness import Capture,RangeFile,sha
from retrieve_terrain_area import retrieve


def enclosing_window(bounds, transform, width, height):
    w=from_bounds(*bounds,transform=transform)
    c,r=math.floor(w.col_off),math.floor(w.row_off)
    right,bottom=math.ceil(w.col_off+w.width),math.ceil(w.row_off+w.height)
    if min(c,r)<0 or right>width or bottom>height:raise ValueError('AOI is not contained by native raster')
    if (right-c)*(bottom-r)>1024*1024:raise ValueError('Window exceeds pixel budget')
    return [c,r,right-c,bottom-r]


def header(cap,product,index):
    remote=RangeFile(cap,product,index)
    with tifffile.TiffFile(remote) as tif:
        for p in tif.pages:
            for tag in p.tags.values():_=tag.value
        with tempfile.NamedTemporaryFile(suffix='.tif') as f:
            f.truncate(remote.size)
            for offset,data in remote.parts:f.seek(offset);f.write(data)
            f.flush()
            with rasterio.open(f.name) as ds:
                if ds.crs is None or ds.crs.to_epsg()!=26919 or ds.res!=(1.0,1.0):raise ValueError('Unsupported CRS/resolution')
                if ds.transform!=from_origin(ds.bounds.left,ds.bounds.top,*ds.res):raise ValueError('Unsupported grid orientation')
                return {'source_id':product['sourceId'],'url':product['downloadURL'],'etag':remote.etag,
                    'current_file_bytes':remote.size,'width':ds.width,'height':ds.height,'bounds':list(ds.bounds),
                    'resolution':list(ds.res),'crs_wkt':ds.crs.to_wkt(),'epsg':ds.crs.to_epsg(),
                    'nodata':ds.nodata,'dtype':ds.dtypes[0],'units':ds.units,'header_transfer_bytes':remote.used}


def run(args):
    req=json.loads(args.request.read_text());pilot=json.loads(args.pilot.read_text())
    if sha(args.request)!=pilot['request_sha256']:raise ValueError('Pilot request changed')
    catalog=json.loads(args.catalog.read_text())
    selection=json.loads(args.selection.read_text())
    if sha(args.catalog)!=selection['terrain']['input_sha256']:raise ValueError('Pinned catalog mismatch')
    county_data=json.loads(args.boundary.read_text())['boundary']
    import hashlib
    raw=bytes.fromhex(county_data['wkb_hex'])
    if hashlib.sha256(raw).hexdigest()!=req['county_boundary_sha256'] or county_data['srid']!=26919:raise ValueError('County boundary changed')
    county=wkb.loads(raw);aoi=box(*req['bounds'])
    if not county.contains(aoi):raise ValueError('AOI outside county')
    geographic=box(*transform_bounds(26919,4326,*req['bounds'],densify_pts=21))
    retained=set(selection['terrain']['retained_source_ids']);candidates=[]
    for p in catalog['terrain']['products']:
        b=p['boundingBox']
        if p['sourceId'] in retained and geographic.intersects(box(b['minX'],b['minY'],b['maxX'],b['maxY'])):
            candidates.append(p)
    alternatives=[p for p in candidates if p['sourceId'] not in req['source_ids']]
    if not 1<=len(alternatives)<=2:raise ValueError('Expected one or two alternatives; review larger scope before retrieval')
    cap=Capture(args.output)
    result={'evidence_state':'DERIVED','method_sha256':sha(__file__),'retrieval_method_sha256':sha(Path(__file__).with_name('retrieve_terrain_area.py')),
        'range_reader_sha256':sha(Path(__file__).with_name('investigate_terrain_readiness.py')),
        'request_sha256':sha(args.request),'pilot_sha256':sha(args.pilot),'catalog_sha256':sha(args.catalog),
        'selection_sha256':sha(args.selection),'county_boundary_sha256':req['county_boundary_sha256'],
        'aoi_bounds':req['bounds'],'epsg':26919,'candidate_ids':[p['sourceId'] for p in candidates],
        'max_raster_transfer_bytes':len(alternatives)*16*1024*1024,'projects':[],
        'limits':['Pinned catalog discovery only, not a fresh exhaustive product search.',
          'Native windows enclose AOI and can extend by a border pixel; compare masks spatially, never by array index alone.',
          'No preferred source, resampling, mosaic, slope, county availability or suitability qualification.']}
    for i,p in enumerate(alternatives):
        raw,_=cap.get(p['metaUrl']+'?format=json',f'{i}-item.json');item=json.loads(raw)
        row={'source_id':p['sourceId'],'title':p['title'],'dates':item.get('dates'),'metadata_links':item.get('webLinks')}
        link=next((x['uri'] for x in item['webLinks'] if x.get('title')=='Product Metadata'),None)
        if link:
            raw,_=cap.get(link,f'{i}-product.xml');root=ET.fromstring(raw)
            row['product_time_fields']={k:[x.text for x in root.findall(k)] for k in ['idinfo/timeperd/timeinfo/rngdates/begdate','idinfo/timeperd/timeinfo/rngdates/enddate','idinfo/timeperd/current']}
        expected=header(cap,p,f'{i}-header')
        win=enclosing_window(req['bounds'],from_origin(expected['bounds'][0],expected['bounds'][3],*expected['resolution']),expected['width'],expected['height'])
        native_bounds=window_bounds(Window(*win),from_origin(expected['bounds'][0],expected['bounds'][3],*expected['resolution']))
        if not box(*native_bounds).covers(aoi) or not county.contains(box(*native_bounds)):raise ValueError('Native enclosing window outside study area')
        row['header']=expected;row['subset']=retrieve(cap,expected,win,f'{i}-pixels',args.output/f'{i}-subset.tif')
        row['raster_transfer_bytes']=expected['header_transfer_bytes']+row['subset']['raster_transfer_bytes']
        result['projects'].append(row)
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
        print(p['title'],row['subset']['coverage'],row['raster_transfer_bytes'],flush=True)
    result['raster_transfer_bytes']=sum(p['raster_transfer_bytes'] for p in result['projects'])
    result['sources_sha256']=sha(args.output/'sources.json')
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name,default in [('request','research/terrain-area-pilot/request.json'),('pilot','research/terrain-area-pilot/report.json'),('catalog','research/soils-terrain-readiness/report.json'),('selection','research/county-soils-preparation/report.json'),('boundary','research/piscataquis-ingestion/report.json')]:p.add_argument('--'+name,type=Path,default=Path(default))
    p.add_argument('--output',type=Path,required=True);run(p.parse_args())
