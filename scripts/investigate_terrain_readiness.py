#!/usr/bin/env python3
"""Bounded public metadata and raster-block reconnaissance; no ingestion or slopes.

Requires numpy, rasterio, tifffile. Each range is checked before body reads;
per-raster transfer is capped at 8 MiB. Sparse reconstruction is diagnostic only.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tempfile
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict
import xml.etree.ElementTree as ET

import numpy as np
import rasterio
from rasterio.windows import Window
import tifffile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Capture:
    def __init__(self, root):
        self.root = root
        root.mkdir(parents=True, exist_ok=False)
        self.sources = []

    def get(self, url, name, headers=None, limit=2*1024*1024, expected_range=None):
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=60) as r:
            if expected_range is not None:
                start, size = expected_range
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', r.headers.get('Content-Range', ''))
                if r.status != 206 or not match or (int(match[1]), int(match[2])) != (start, start+size-1):
                    raise ValueError('Server did not honor exact bounded Range')
            data = r.read(limit+1)
            if len(data) > limit or (expected_range and len(data) != expected_range[1]):
                raise ValueError('Response length outside bound')
            record = {'file': name, 'url': url, 'sha256': hashlib.sha256(data).hexdigest(),
                      'bytes': len(data), 'status': r.status, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                      'etag': r.headers.get('ETag'), 'last_modified': r.headers.get('Last-Modified'),
                      'content_range': r.headers.get('Content-Range')}
            (self.root/name).write_bytes(data)
            self.sources.append(record)
            (self.root/'sources.json').write_text(json.dumps(self.sources, indent=2)+'\n')
            return data, record


class RangeFile(io.RawIOBase):
    """Seekable TIFF input with exact conditional range reads and a byte budget."""
    def __init__(self, cap, product, index):
        self.cap, self.url, self.index = cap, product['downloadURL'], index
        self.pos, self.used, self.parts, self.etag = 0, 0, [], None
        data, rec = cap.get(self.url, f'{index}-header.bin', {'Range': 'bytes=0-65535'},
                            limit=65536, expected_range=(0,65536))
        self.size = int(rec['content_range'].split('/')[1])
        self.etag = rec['etag']
        if not self.etag:
            raise ValueError('Missing ETag; cannot pin multi-request raster version')
        self.parts.append((0, data)); self.used += len(data)

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos+offset if whence == 1 else self.size+offset
        if not 0 <= self.pos <= self.size: raise ValueError('Seek outside raster')
        return self.pos
    def read(self, size=-1):
        if size < 0: raise ValueError('Unbounded read forbidden')
        start = self.pos; size = min(size, self.size-start)
        if not size: return b''
        for offset, data in self.parts:
            if offset <= start and start+size <= offset+len(data):
                self.pos += size
                return data[start-offset:start-offset+size]
        if self.used+size > 8*1024*1024: raise ValueError('Raster byte budget exceeded')
        data, rec = self.cap.get(self.url, f'{self.index}-range-{len(self.parts)}.bin',
            {'Range': f'bytes={start}-{start+size-1}', 'If-Match': self.etag}, limit=size, expected_range=(start,size))
        if rec['etag'] != self.etag: raise ValueError('Raster version changed')
        self.parts.append((start,data)); self.used += size; self.pos += size
        return data


def sample(cap, product, index):
    remote = RangeFile(cap, product, index)
    with tifffile.TiffFile(remote) as tif:
        page = tif.pages[0]
        for header_page in tif.pages:
            for tag in header_page.tags.values():
                _ = tag.value
        if not page.is_tiled or page.samplesperpixel != 1:
            raise ValueError('Only single-band tiled TIFF supported')
        offsets, counts = page.dataoffsets, page.databytecounts
        tw, th = page.tilewidth, page.tilelength
        nx, ny = math.ceil(page.imagewidth/tw), math.ceil(page.imagelength/th)
        blocks = sorted({(y,x) for y in (0,ny//2,ny-1) for x in (0,nx//2,nx-1)})
        for y,x in blocks:
            k = y*nx+x
            remote.seek(offsets[k]); remote.read(counts[k])
        # Populate only inspected header ranges and selected compressed blocks.
        # Never distribute this incomplete sparse file as a source raster.
        with tempfile.NamedTemporaryFile(suffix='.tif') as named:
            named.truncate(remote.size)
            for offset,data in remote.parts:
                named.seek(offset); named.write(data)
            named.flush()
            with rasterio.open(named.name) as ds:
                result = {'crs_wkt': ds.crs.to_wkt(), 'epsg': ds.crs.to_epsg(),
                    'width': ds.width, 'height': ds.height, 'resolution': list(ds.res),
                    'bounds': list(ds.bounds), 'dtype': ds.dtypes[0], 'nodata': ds.nodata,
                    'units': ds.units, 'tags': ds.tags(), 'band_tags': ds.tags(1),
                    'block_shape': [th,tw], 'samples': []}
                for y,x in blocks:
                    w,h = min(tw, ds.width-x*tw),min(th,ds.height-y*th)
                    a=ds.read(1,window=Window(x*tw,y*th,w,h),masked=True)
                    valid=np.asarray(a.compressed()); finite=valid[np.isfinite(valid)]
                    result['samples'].append({'row':y*th,'column':x*tw,'width':w,'height':h,
                        'pixels':w*h,'masked':int(np.ma.getmaskarray(a).sum()),
                        'nonfinite_unmasked':int(len(valid)-len(finite)),
                        'finite_min':float(finite.min()) if len(finite) else None,
                        'finite_max':float(finite.max()) if len(finite) else None})
    result.update(source_id=product['sourceId'], url=remote.url, etag=remote.etag,
        current_file_bytes=remote.size, catalog_file_bytes=product['sizeInBytes'], bytes_read=remote.used,
        scope='Nine native raster blocks; not county-clipped, not representative statistical sampling or complete valid-pixel coverage')
    return result


def run(args):
    cap=Capture(args.output)
    catalog=json.loads(args.catalog.read_text()); selection=json.loads(args.selection.read_text())
    if sha(args.catalog) != selection['terrain']['input_sha256']: raise ValueError('Catalog hash mismatch')
    ids=set(selection['terrain']['retained_source_ids'])
    products=[p for p in catalog['terrain']['products'] if p['sourceId'] in ids]
    if len(products)!=len(ids): raise ValueError('Missing/duplicate retained products')
    groups=defaultdict(list); cells=defaultdict(list)
    for p in products:
        groups[p['downloadURL'].split('/Projects/')[1].split('/')[0]].append(p)
        b=p['boundingBox']; cells[tuple(b[k] for k in ('minX','minY','maxX','maxY'))].append(p['sourceId'])
    report={'evidence_state':'DERIVED','method_sha256':sha(__file__),
        'catalog_sha256':sha(args.catalog),'selection_sha256':sha(args.selection),
        'runtime':{'rasterio':rasterio.__version__,'gdal':rasterio.__gdal_version__,'tifffile':tifffile.__version__},
        'retained_count':len(products),'advertised_bytes':sum(p['sizeInBytes'] for p in products),
        'exact_catalog_rectangles':len(cells),'multiply_listed_rectangles':sum(len(v)>1 for v in cells.values()),
        'rectangle_multiplicity':{str(n):sum(len(v)==n for v in cells.values()) for n in sorted({len(v) for v in cells.values()})},
        'projects':[], 'limits':['First retained catalog tile per project only. Metadata may vary within a project.',
        'Exact rectangle equality is not equivalent to raster or valid-data coverage equality.',
        'No full raster, mosaic, slope, source priority, terrain availability or suitability accepted.']}
    for i,(project,pp) in enumerate(sorted(groups.items())):
        p=pp[0]
        row={'project':project,'retained_tiles':len(pp),'advertised_bytes':sum(x['sizeInBytes'] for x in pp),
            'representative_source_id':p['sourceId'],'publication_dates':sorted({x['publicationDate'] for x in pp})}
        try:
            raw,_=cap.get(p['metaUrl']+'?format=json',f'{i}-item.json'); item=json.loads(raw)
            row['dates']=item.get('dates'); row['metadata_links']=item.get('webLinks')
            try:
                link=next(x['uri'] for x in item['webLinks'] if x.get('title')=='Product Metadata')
                raw,_=cap.get(link,f'{i}-metadata.xml'); root=ET.fromstring(raw)
                paths=['idinfo/timeperd','dataqual/posacc','spref','dataqual/lineage/srcinfo']
                row['metadata_fields']={path:[ET.tostring(x,encoding='unicode') for x in root.findall(path)] for path in paths}
            except Exception as e: row['metadata_error']=f'{type(e).__name__}: {e}'
            row['raster']=sample(cap,p,i)
        except Exception as e: row['error']=f'{type(e).__name__}: {e}'
        report['projects'].append(row)
        (args.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(project,'complete' if 'raster' in row else row.get('error'),flush=True)
    report['sources_sha256']=sha(args.output/'sources.json')
    (args.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,default=Path('research/soils-terrain-readiness/report.json'))
    parser.add_argument('--selection',type=Path,default=Path('research/county-soils-preparation/report.json'))
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
