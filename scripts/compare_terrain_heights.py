#!/usr/bin/env python3
"""Local, mask-aware height diagnostics; no corrected or merged raster is written."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stats(values):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if not v.size:
        return {'count': 0}
    return dict(count=int(v.size), mean_m=float(v.mean()), median_m=float(np.median(v)),
                rms_difference_m=float(np.sqrt(np.mean(v*v))),
                p05_m=float(np.percentile(v, 5)), p95_m=float(np.percentile(v, 95)),
                abs_p95_m=float(np.percentile(abs(v), 95)), max_abs_m=float(abs(v).max()))


def sample(data, valid, transform, target, shape, bilinear=True):
    """Sample at target centers; bilinear requires all four native samples valid."""
    r, c = np.indices(shape)
    x, y = target * (c + .5, r + .5)
    sc, sr = ~transform * (x, y)
    sc, sr = sc - .5, sr - .5
    if not bilinear:
        ci, ri = np.floor(sc+.5).astype(int), np.floor(sr+.5).astype(int)
        inside = (ri >= 0) & (ci >= 0) & (ri < data.shape[0]) & (ci < data.shape[1])
        ri, ci = np.clip(ri, 0, data.shape[0]-1), np.clip(ci, 0, data.shape[1]-1)
        return np.where(inside & valid[ri, ci], data[ri, ci], np.nan)
    c0, r0 = np.floor(sc).astype(int), np.floor(sr).astype(int)
    dc, dr = sc-c0, sr-r0
    inside = (r0 >= 0) & (c0 >= 0) & (r0+1 < data.shape[0]) & (c0+1 < data.shape[1])
    r0, c0 = np.clip(r0, 0, data.shape[0]-2), np.clip(c0, 0, data.shape[1]-2)
    ok = inside.copy()
    out = np.zeros(shape, dtype=float)
    for dy, dx, weight in [(0,0,(1-dr)*(1-dc)), (0,1,(1-dr)*dc), (1,0,dr*(1-dc)), (1,1,dr*dc)]:
        ok &= valid[r0+dy, c0+dx]
        out += np.where(valid[r0+dy,c0+dx], data[r0+dy,c0+dx], 0) * weight
    return np.where(ok, out, np.nan)


def seam(base, alternative):
    """Four-neighbor edges oriented retained base -> hypothetical alternative fill."""
    steps, continuation, offsets = [], [], []
    total = 0
    for axis in (0, 1):
        for reverse in (False, True):
            a, b = [slice(None), slice(None)], [slice(None), slice(None)]
            a[axis], b[axis] = slice(None,-1), slice(1,None)
            if reverse: a,b=b,a
            a,b=tuple(a),tuple(b)
            edge=np.isfinite(base[a]) & ~np.isfinite(base[b])
            total += int(edge.sum())
            ok=edge & np.isfinite(alternative[a]) & np.isfinite(alternative[b])
            steps.extend((alternative[b]-base[a])[ok])
            continuation.extend((alternative[b]-alternative[a])[ok])
            offsets.extend((alternative[a]-base[a])[ok])
    return {'candidate_edges':total, 'supported_edges':len(steps),
            'unsupported_edges':total-len(steps), 'cross_source_step':stats(steps),
            'within_alternative_step':stats(continuation), 'source_switch_contribution':stats(offsets)}


def read(path):
    with rasterio.open(path) as ds:
        if ds.crs.to_epsg()!=26919 or ds.count!=1 or ds.transform.b or ds.transform.d or ds.res!=(1,1):
            raise ValueError('Expected north-up single-band 1m EPSG26919 raster')
        a=ds.read(1, masked=True)
        valid=~np.ma.getmaskarray(a) & np.isfinite(a.data)
        return a.data.astype(float),valid,ds.transform


def run(args):
    pilot=json.loads(Path('research/terrain-area-pilot/report.json').read_text())
    alternatives=json.loads(Path('research/terrain-gap/report.json').read_text())
    paths=[args.base, args.western2016, args.western2024]
    expected=[pilot['sources'][0]['subset_sha256']]+[p['subset']['subset_sha256'] for p in alternatives['projects']]
    if [sha(p) for p in paths]!=expected: raise ValueError('Source subset version mismatch')
    arrays=[read(p) for p in paths]
    data,valid,t=arrays[0]; base=np.where(valid,data,np.nan)
    result={'evidence_state':'DERIVED','method_sha256':sha(__file__),
            'input_sha256':dict(zip(['eastern2017','western2016','western2024'],expected)),
            'runtime':{'numpy':np.__version__,'rasterio':rasterio.__version__},
            'alignment':'Float64 bilinear sampling at Eastern native pixel centers; all four source pixels must be valid and finite; no extrapolation. Nearest-center diagnostic sensitivity on identical supported cells.',
            'sign':'alternative minus Eastern 2017; seam oriented Eastern-valid cell toward Eastern-NoData cell',
            'analysis_qualified':False, 'aoi_bounds':pilot['sources'][0]['bounds'], 'comparisons':[]}
    # Locate the hypothetical boundary from valid/NoData four-neighbor edges.
    boundary=np.zeros(valid.shape,bool)
    for axis in (0,1):
        a,b=[slice(None),slice(None)],[slice(None),slice(None)]
        a[axis],b[axis]=slice(None,-1),slice(1,None)
        a,b=tuple(a),tuple(b)
        edge=valid[a]!=valid[b]
        boundary[a] |= edge & valid[a]
        boundary[b] |= edge & valid[b]
    rr,cc=np.where(boundary); bx,by=t*(cc+.5,rr+.5)
    result['boundary_retained_cell_centers_bounds']=[float(bx.min()),float(by.min()),float(bx.max()),float(by.max())]
    result['boundary_definition']='Internal four-neighbor Eastern valid/NoData edges; not a surveyed boundary or official project acquisition boundary; AOI perimeter excluded.'
    for label,(d,v,st) in zip(['western2016','western2024'],arrays[1:]):
        aligned=sample(d,v,st,t,base.shape)
        nearest=sample(d,v,st,t,base.shape,False)
        residual=aligned-base
        quadrants={}
        for name,rs,cs in [('NW',slice(0,256),slice(0,256)),('NE',slice(0,256),slice(256,None)),('SW',slice(256,None),slice(0,256)),('SE',slice(256,None),slice(256,None))]:
            quadrants[name]=stats(residual[rs,cs])
        extremes=[]
        for index in np.argsort(np.nan_to_num(abs(residual),nan=-1).ravel())[-5:][::-1]:
            row,col=np.unravel_index(index,residual.shape); x,y=t*(float(col)+.5,float(row)+.5)
            extremes.append({'easting':x,'northing':y,'difference_m':float(residual[row,col])})
        result['comparisons'].append({'alternative':label,'overlap':stats(residual),
            'quadrants':quadrants,'largest_absolute_residual_locations':extremes,'bilinear_minus_nearest':stats((aligned-nearest)[np.isfinite(base)]),
            'base_gap_cells':int((~valid).sum()),'supported_gap_cells':int((~valid & np.isfinite(aligned)).sum()),
            'seam':seam(base,aligned)})
    d1,v1,t1=arrays[1];d2,v2,t2=arrays[2]
    if t1!=t2 or d1.shape!=d2.shape:raise ValueError('Alternative native grids differ')
    # Restrict native centers to original AOI, excluding enclosing fringe.
    rr,cc=np.indices(d1.shape);x,y=t1*(cc+.5,rr+.5)
    bounds=pilot['sources'][0]['bounds']
    inside=(x>=bounds[0])&(x<bounds[2])&(y>=bounds[1])&(y<bounds[3])
    result['western2024_minus_2016_native_overlap']=stats((d2-d1)[v1&v2&inside])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','western2016','western2024','output']:p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
