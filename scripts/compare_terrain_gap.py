#!/usr/bin/env python3
"""Compare native valid-pixel footprints in the original AOI without resampling."""
import argparse
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import box,shape
from shapely.ops import unary_union
import shapely
from investigate_terrain_readiness import sha


def valid_geometry(path,aoi):
    with rasterio.open(path) as ds:
        if ds.crs.to_epsg()!=26919:raise ValueError('CRS mismatch')
        a=ds.read(1,masked=True)
        valid=(~np.ma.getmaskarray(a))&np.isfinite(a.data)
        pieces=[shape(g) for g,v in shapes(valid.astype('uint8'),mask=valid,transform=ds.transform) if v==1]
        footprint=unary_union(pieces).intersection(aoi)
        if not footprint.is_valid:raise ValueError('Invalid derived valid-pixel geometry')
        return footprint


def coverage(base,alternative,aoi):
    gap=aoi.difference(base);remaining=gap.difference(alternative)
    return {'aoi_m2':aoi.area,'base_valid_m2':base.area,'base_missing_m2':gap.area,
        'alternative_valid_m2':alternative.area,'alternative_missing_m2':aoi.difference(alternative).area,
        'original_gap_covered_m2':gap.intersection(alternative).area,'original_gap_remaining_m2':remaining.area,
        'joint_valid_m2':base.intersection(alternative).area,'base_only_valid_m2':base.difference(alternative).area,
        'alternative_covers_entire_aoi':alternative.covers(aoi),'alternative_covers_original_gap':alternative.covers(gap),
        'combined_coverage':'full_geometric' if remaining.is_empty else 'partial_geometric'}


def run(args):
    request=json.loads(args.request.read_text());pilot=json.loads(args.pilot.read_text());alt=json.loads((args.alternatives/'report.json').read_text())
    if sha(args.request)!=pilot['request_sha256'] or sha(args.pilot)!=alt['pilot_sha256']:raise ValueError('Input versions mismatch')
    if request['bounds']!=alt['aoi_bounds'] or alt['epsg']!=26919:raise ValueError('AOI mismatch')
    aoi=box(*request['bounds']);b=pilot['sources'][0]
    if sha(args.base_subset)!=b['subset_sha256']:raise ValueError('Base subset changed')
    base=valid_geometry(args.base_subset,aoi)
    result={'evidence_state':'DERIVED','method_sha256':sha(__file__),'pilot_sha256':sha(args.pilot),'alternative_report_sha256':sha(args.alternatives/'report.json'),
        'runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string,'rasterio':rasterio.__version__},
        'base_source_id':b['source_id'],'aoi_bounds':request['bounds'],'comparisons':[],
        'limits':['Exact spatial intersection of native valid-pixel footprints with original AOI. No snapping, tolerance, resampling, blending or source choice.',
            'Complete geometric coverage does not establish elevation accuracy, datum compatibility, source currency, suitability or county availability.']}
    for p in alt['projects']:
        s=p['subset'];path=args.alternatives/s['subset_file']
        if sha(path)!=s['subset_sha256']:raise ValueError('Alternative subset changed')
        native=valid_geometry(path,aoi)
        result['comparisons'].append({'source_id':p['source_id'],'title':p['title'],'native_bounds':s['bounds'],
            'native_grid_matches_base':s['bounds']==b['bounds'] and s['window'][2:]==b['window'][2:] and s['crs_wkt']==b['crs_wkt'],
            **coverage(base,native,aoi)})
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',type=Path,default=Path('research/terrain-area-pilot/request.json'))
    p.add_argument('--pilot',type=Path,default=Path('research/terrain-area-pilot/report.json'));p.add_argument('--base-subset',type=Path,required=True)
    p.add_argument('--alternatives',type=Path,required=True);p.add_argument('--output',type=Path,required=True);run(p.parse_args())
