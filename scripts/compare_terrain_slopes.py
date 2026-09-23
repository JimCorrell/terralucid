#!/usr/bin/env python3
"""Bounded native-source slope comparison, never a buildability qualification."""
import argparse
import json
from pathlib import Path
import numpy as np
from compare_terrain_heights import read, sample, sha


def slope(data, valid, resolution=1):
    """Weighted 3x3 derivatives; require all nine finite samples, no edge padding."""
    if resolution <= 0: raise ValueError('Positive metric resolution required')
    z = np.lib.stride_tricks.sliding_window_view(data, (3,3))
    v = np.lib.stride_tricks.sliding_window_view(valid & np.isfinite(data), (3,3)).all(axis=(-2,-1))
    dx = ((z[...,0,2]+2*z[...,1,2]+z[...,2,2])-(z[...,0,0]+2*z[...,1,0]+z[...,2,0]))/(8*resolution)
    dy = ((z[...,2,0]+2*z[...,2,1]+z[...,2,2])-(z[...,0,0]+2*z[...,0,1]+z[...,0,2]))/(8*resolution)
    out = np.full(data.shape,np.nan)
    out[1:-1,1:-1] = np.where(v,np.degrees(np.arctan(np.hypot(dx,dy))),np.nan)
    return out


def boundary_hold(labels):
    """Internal target-grid 3x3 neighborhoods containing both source labels."""
    z=np.lib.stride_tricks.sliding_window_view(labels,(3,3))
    out=np.zeros(labels.shape,bool)
    out[1:-1,1:-1]=z.any(axis=(-2,-1)) & ~z.all(axis=(-2,-1))
    return out


def stats(a):
    a=np.asarray(a);a=a[np.isfinite(a)]
    if not a.size:return {'count':0}
    return {'count':int(a.size),'mean_degrees':float(a.mean()),'median_degrees':float(np.median(a)),
            'p05_degrees':float(np.percentile(a,5)),'p95_degrees':float(np.percentile(a,95)),
            'absolute_p95_degrees':float(np.percentile(abs(a),95)),'max_absolute_degrees':float(abs(a).max())}


def run(args):
    prior=Path('research/terrain-overlap/report.json');p=json.loads(prior.read_text())
    paths=[args.base,args.western2016,args.western2024]
    names=['eastern2017','western2016','western2024']
    if [sha(x) for x in paths]!=[p['input_sha256'][n] for n in names]:raise ValueError('Subset version mismatch')
    arrays=[read(x) for x in paths]
    native=[slope(d,v) for d,v,t in arrays]
    base,valid,t=arrays[0];hold=boundary_hold(valid)
    edge=np.ones(base.shape,bool);edge[1:-1,1:-1]=False
    result={'evidence_state':'DERIVED','analysis_qualified':False,'method_sha256':sha(__file__),
            'height_method_sha256':sha(Path(__file__).with_name('compare_terrain_heights.py')),
            'height_report_sha256':sha(prior),'input_sha256':p['input_sha256'],
            'runtime':{'numpy':np.__version__},'aoi_bounds':p['aoi_bounds'],
            'operator':'3x3 weighted derivatives [1,2,1]/8 across opposite columns/rows; degrees(atan(hypot(dx,dy))); meters horizontally and vertically.',
            'comparison':'Compute native slopes first. Bilinear sample Western slope angles at Eastern centers, requiring four finite native slopes. Sign Western minus Eastern; not slope of a resampled DEM.',
            'seam_hold_definition':'Any internal Eastern-grid 3x3 neighborhood containing both retained-Eastern and fill labels. Native slope support required separately. No padding outside captured subsets.',
            'internal_seam_hold_cells':int(hold.sum()),'aoi_edge_hold_cells':int(edge.sum()),
            'native_valid_slope_centers':dict(zip(names,[int(np.isfinite(a).sum()) for a in native])),
            'comparisons':[]}
    for name,(d,v,st),s in zip(names[1:],arrays[1:],native[1:]):
        aligned=sample(s,np.isfinite(s),st,t,base.shape)
        nearest=sample(s,np.isfinite(s),st,t,base.shape,False)
        overlap=np.isfinite(native[0]) & np.isfinite(aligned)
        # Hypothetical source assignment only, never a merged elevation surface.
        selected=np.where(valid,native[0],aligned)
        supported=np.isfinite(selected)&~hold&~edge
        missing=~np.isfinite(selected)&~hold&~edge
        delta=aligned-native[0]
        extremes=[]
        for index in np.argsort(np.nan_to_num(abs(delta),nan=-1).ravel())[-5:][::-1]:
            row,col=np.unravel_index(index,delta.shape);x,y=t*(float(col)+.5,float(row)+.5)
            extremes.append({'easting':x,'northing':y,'difference_degrees':float(delta[row,col]),'eastern_slope_degrees':float(native[0][row,col]),'western_slope_degrees':float(aligned[row,col])})
        result['comparisons'].append({'alternative':name,'largest_absolute_difference_locations':extremes,'slope_difference':stats((aligned-native[0])[overlap]),
            'sampling_sensitivity':stats((aligned-nearest)[overlap]),
            'hypothetical_source_assignment':{'supported_cells':int(supported.sum()),'support_missing_cells':int(missing.sum()),
                'source_boundary_held_cells':int(hold.sum()),'aoi_edge_held_cells':int(edge.sum()),
                'total_cells':int(base.size)},
            'seam_adjacent_source_difference':stats((aligned-native[0])[hold & overlap])})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','western2016','western2024','output']:p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
