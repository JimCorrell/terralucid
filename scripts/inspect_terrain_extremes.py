#!/usr/bin/env python3
"""Inspect bounded native neighborhoods at previously recorded terrain extremes."""
import argparse
import json
from pathlib import Path
import numpy as np
from compare_terrain_heights import read,sha,stats


def patch(data,valid,transform,x,y,radius=5):
    col,row=~transform*(x,y);row,col=int(np.floor(row)),int(np.floor(col))
    if row-radius<0 or col-radius<0 or row+radius>=data.shape[0] or col+radius>=data.shape[1]:
        raise ValueError('Neighborhood exceeds preserved subset')
    a=data[row-radius:row+radius+1,col-radius:col+radius+1]
    v=valid[row-radius:row+radius+1,col-radius:col+radius+1]
    a=np.where(v & np.isfinite(a),a,np.nan)
    cx,cy=transform*(col+.5,row+.5)
    return a,[float(cx),float(cy)]


def describe(a):
    r,c=np.indices(a.shape);design=np.column_stack([np.ones(a.size),c.ravel(),r.ravel()])
    valid=np.isfinite(a);keep=valid.ravel()
    if keep.sum()<3 or np.linalg.matrix_rank(design[keep])<3:raise ValueError('Insufficient plane support')
    fitted=design@np.linalg.lstsq(design[keep],a.ravel()[keep],rcond=None)[0]
    detrended=a-fitted.reshape(a.shape)
    middle=a.shape[0]//2
    def profile(values):return [float(x) if np.isfinite(x) else None for x in values]
    return {'valid_cells':int(valid.sum()),'missing_cells':int((~valid).sum()),
            'min_m':float(np.nanmin(a)),'max_m':float(np.nanmax(a)),
            'plane_residual_rms_m':float(np.sqrt(np.nanmean(detrended**2))),
            'max_adjacent_step_m':float(max(np.nanmax(abs(np.diff(a,axis=0))),np.nanmax(abs(np.diff(a,axis=1))))),
            'west_to_east_center_profile_m':profile(a[middle,:]),
            'north_to_south_center_profile_m':profile(a[:,middle])}


def run(args):
    reports=[Path('research/terrain-overlap/report.json'),Path('research/terrain-slopes/report.json')]
    height,slopes=[json.loads(p.read_text()) for p in reports]
    names=['eastern2017','western2016','western2024'];paths=[args.base,args.western2016,args.western2024]
    if height['input_sha256']!=slopes['input_sha256'] or [sha(p) for p in paths]!=[height['input_sha256'][n] for n in names]:
        raise ValueError('Input versions mismatch')
    points={}
    for label,report,key in [('height',height,'largest_absolute_residual_locations'),('slope',slopes,'largest_absolute_difference_locations')]:
        for comparison in report['comparisons']:
            for point in comparison[key]:
                xy=(point['easting'],point['northing'])
                points.setdefault(xy,[]).append(label+':'+comparison['alternative'])
    arrays=[read(p) for p in paths]
    result={'evidence_state':'DERIVED','analysis_qualified':False,'method_sha256':sha(__file__),
        'helper_sha256':sha(Path(__file__).with_name('compare_terrain_heights.py')),
        'input_sha256':height['input_sha256'],'prior_report_sha256':[sha(p) for p in reports],
        'method':'11x11 native cells around every unique recorded top-five height/slope location. No resampling or missing-cell fill; fit plane only to valid cells, profile nulls preserve missingness. Pair differences compare corresponding nearest native centers; exact centers retained. Least-squares plane residuals describe shape, not error against ground truth.',
        'runtime':{'numpy':np.__version__},'sites':[]}
    for (x,y),reasons in sorted(points.items()):
        patches=[];site={'target_center_epsg26919':[x,y],'selected_by':reasons,'sources':{}}
        for name,(data,valid,t) in zip(names,arrays):
            a,center=patch(data,valid,t,x,y);patches.append(a)
            site['sources'][name]={'native_center_epsg26919':center,**describe(a)}
        site['paired_native_differences']={
            'western2016_minus_eastern2017':stats(patches[1]-patches[0]),
            'western2024_minus_eastern2017':stats(patches[2]-patches[0]),
            'western2024_minus_western2016':stats(patches[2]-patches[1])}
        result['sites'].append(site)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','western2016','western2024','output']:p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
