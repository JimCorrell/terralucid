#!/usr/bin/env python3
"""Rank held county zoning by envelope/gap overlap; never repair source geometry."""
import json
from collections import Counter
from pathlib import Path
import shapely
from shapely.geometry import box
from shapely.ops import unary_union
from investigate_osborn_wetlands import decode
from prepare_source_staging import ROOT, canonical, digest

BASE=ROOT/'research/piscataquis-zoning-holds'
COUNTY=ROOT/'research/piscataquis-ingestion'
AUDIT='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'

def rank():
    raw=(COUNTY/'report.json').read_bytes()
    if digest(raw)!=AUDIT:raise ValueError('County audit changed')
    prior=json.loads(raw);boundary=shapely.from_wkb(bytes.fromhex(prior['boundary']['wkb_hex']))
    log=json.loads((COUNTY/'runs/capture/results.json').read_bytes())
    valid=[];held=[];inputs={};civil=[];seen=set()
    for r in log:
        if not (r['id'].startswith('lupc-zoning-page-') or r['id'].startswith('civil-boundaries-page-')):continue
        expected=prior['evidence']['capture/'+r['id']]
        if any(r[k]!=expected[k] for k in r):raise ValueError('Capture log differs from pinned audit')
        p=COUNTY/'runs/capture'/r['response_file'];b=p.read_bytes()
        if digest(b)!=r['sha256'] or len(b)!=r['bytes']:raise ValueError('Changed source page')
        d=json.loads(b)
        if d.get('error') or d.get('exceededTransferLimit') or d['spatialReference'].get('latestWkid',d['spatialReference']['wkid'])!=26919:raise ValueError('Incomplete/changed page')
        inputs[p.relative_to(ROOT).as_posix()]=r['sha256']
        for f in d['features']:
            g,hold=decode(f['geometry']['rings'])
            if r['id'].startswith('civil-'):
                if hold:raise ValueError('Invalid study boundary')
                civil.append((f['attributes'],g));continue
            oid=f['attributes']['OBJECTID']
            if oid in seen:raise ValueError('Duplicate zoning identity')
            seen.add(oid)
            if hold:
                points=[p for ring in f['geometry']['rings'] for p in ring]
                env=box(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
                held.append((f,hold,env,r['sha256']))
            else:valid.append(g)
    if len(seen)!=42901 or len(held)!=162 or not unary_union([g for _,g in civil]).equals(boundary):raise ValueError('County membership differs')
    print('Source verified; computing valid union',flush=True)
    coverage=unary_union(valid);gap=boundary.difference(coverage);rows=[]
    (ROOT/'.local/piscataquis-held-zoning-gap.wkb').write_bytes(gap.wkb)
    for f,hold,env,sha in held:
        impact=env.intersection(gap)
        jurisdictions=Counter()
        for a,g in civil:
            if impact.intersects(g):jurisdictions[a['TOWN']]+=impact.intersection(g).area
        rows.append({'object_id':f['attributes']['OBJECTID'],'source_attributes':f['attributes'],'source_feature_sha256':digest(canonical(f).encode()),'response_sha256':sha,'hold':hold,'ring_count':len(f['geometry']['rings']),'envelope_county_m2':env.intersection(boundary).area,'envelope_uncovered_county_m2':impact.area,'potential_gap_by_civil_name_m2':dict(jurisdictions.most_common()),'interpretation':'DERIVED prioritization upper bound only; envelope overlap is not polygon coverage or legal zoning'})
    rows.sort(key=lambda r:(-r['envelope_uncovered_county_m2'],r['object_id']))
    report={'evidence_state':'DERIVED','method':'scripts/investigate_county_zoning.py','method_sha256':digest(Path(__file__).read_bytes()),'county_audit_sha256':AUDIT,'inputs':inputs,'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string},'valid_zoning_rows':len(valid),'held_zoning_rows':len(held),'gap_wkb_sha256':digest(gap.wkb),'county_area_m2':boundary.area,'county_outside_valid_zoning_union_m2':gap.area,'ranking':rows,'limits':['Bounding boxes overstate possible coverage and rankings are not additive.','All original holds remain. No repair, coordinate change or county correction acceptance.','A gap in usable geometry does not establish absent zoning or municipal applicability.']}
    BASE.mkdir(parents=True,exist_ok=True);(BASE/'ranking.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps([{'id':r['object_id'],'potential_gap_km2':r['envelope_uncovered_county_m2']/1e6,'attributes':r['source_attributes'],'hold':r['hold'],'rings':r['ring_count']} for r in rows[:8]],indent=2))

if __name__=='__main__':rank()
