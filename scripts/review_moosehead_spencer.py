#!/usr/bin/env python3
"""Review fixed candidates using a separate cycle walk and full-source fill checks."""
import json,math
from collections import Counter
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,LinearRing,shape
from prepare_source_staging import ROOT,canonical,digest
from review_county_zoning_proposals import review_geometry,segments
BASE=ROOT/'research/moosehead-spencer-review'
PARENT=ROOT/'research/moosehead-spencer'
PARENT_SHA='959a971c95dc6e81a1179d26f345eba9dc2fe9b908c40107f43272b27ef5d49a'
REGISTRY=ROOT/'research/piscataquis-zoning-holds'

def walk_cycles(ring):
    """Extract cycles when a vertex reappears on a traversal stack; no proposal helper."""
    if len(ring)<4 or ring[0]!=ring[-1] or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in ring):raise ValueError('Invalid closed 2D source ring')
    stack=[];positions={};cycles=[]
    for raw in ring:
        p=tuple(raw)
        if p not in positions:positions[p]=len(stack);stack.append(p);continue
        start=positions[p];cycle=stack[start:]+[p]
        if len(cycle)<4 or not Polygon(cycle).is_valid or Polygon(cycle).area<=0:raise ValueError('Degenerate or nonsimple cycle')
        cycles.append(cycle)
        for q in stack[start+1:]:del positions[q]
        stack=stack[:start+1]
    if len(stack)!=1 or not cycles or segments([ring])!=segments(cycles):raise ValueError('Unclosed walk or changed segments')
    return cycles

def signature(ring):return tuple(sorted(segments([ring]).items()))

def review_cycles(rings,candidate):
    if not candidate.is_valid or candidate.is_empty or candidate.geom_type!='MultiPolygon':raise ValueError('Invalid candidate')
    shells=[];holes=[];details=[]
    owners={}
    for j,p in enumerate(candidate.geoms):
        for h in p.interiors:owners.setdefault(signature(h.coords),[]).append(j)
    for i,ring in enumerate(rings):
        cycles=walk_cycles(ring)
        for c in cycles:(holes if LinearRing(c).is_ccw else shells).append(c)
        if len(cycles)>1:
            ccw=[LinearRing(c).is_ccw for c in cycles]
            entry={'source_ring':i,'cycles':len(cycles),'counterclockwise':ccw}
            if all(ccw):
                if len(cycles)!=2 or Polygon(cycles[0]).intersection(Polygon(cycles[1])).geom_type!='Point':raise ValueError('Unsupported hole contact')
                ownership=[owners.get(signature(c),[]) for c in cycles]
                if any(len(o)!=1 for o in ownership) or ownership[0]!=ownership[1]:raise ValueError('Touching holes must retain one common owner')
                entry.update(type='two_holes',candidate_shell_index=ownership[0][0],loop_area_m2=[Polygon(c).area for c in cycles])
            elif len(cycles)==2 and sum(ccw)==1:entry['type']='shell_hole'
            else:raise ValueError('Unsupported cycle roles')
            details.append(entry)
    if Counter(signature(r) for r in shells)!=Counter(signature(p.exterior.coords) for p in candidate.geoms):raise ValueError('Candidate shell cycles differ')
    if Counter(signature(r) for r in holes)!=Counter(signature(h.coords) for p in candidate.geoms for h in p.interiors):raise ValueError('Candidate hole cycles differ')
    return {'exact_shell_cycles':len(shells),'exact_hole_cycles':len(holes),'source_cycle_roles_preserved':True,'split_rings':details}

def build():
    inputs={}
    def checked(p,sha=None):
        raw=p.read_bytes();h=digest(raw)
        if sha is not None and h!=sha:raise ValueError('Changed input: '+str(p))
        inputs[p.relative_to(ROOT).as_posix()]=h;return raw
    prior=json.loads(checked(PARENT/'report.json',PARENT_SHA));checked(ROOT/prior['method'],prior['method_sha256'])
    for p,h in prior['inputs'].items():checked(ROOT/p,h)
    for p in ['scripts/review_county_zoning_proposals.py','scripts/prepare_source_staging.py']:checked(ROOT/p)
    county=json.loads(checked(ROOT/'research/piscataquis-ingestion/report.json',prior['county_audit_sha256']))
    cases=[]
    for c in prior['cases']:
        oid=c['object_id'];artifact=json.loads(checked(ROOT/c['candidate_path'],c['candidate_sha256']))
        props=artifact['properties']
        if c['status']!='proposed_not_accepted' or props!={'object_id':oid,'county_audit_sha256':prior['county_audit_sha256'],'source_feature_sha256':c['source_feature_sha256'],'status':'proposed_not_accepted','evidence_state':'DERIVED'} or artifact['crs']['properties']['name']!='EPSG:26919':raise ValueError('Wrong proposal version/CRS')
        e=next(e for e in county['evidence'].values() if e['sha256']==c['original_response_sha256'])
        original=next(f for f in json.loads(checked(ROOT/'research/piscataquis-ingestion'/e['response_path'],e['sha256']))['features'] if f['attributes']['OBJECTID']==oid)
        native=json.loads(checked(REGISTRY/'runs/source'/f'native-{oid}.response'))
        if native['spatialReference'].get('latestWkid',native['spatialReference']['wkid'])!=26919 or native['features']!=[original] or digest(canonical(original).encode())!=c['source_feature_sha256']:raise ValueError('Source identity differs')
        candidate=shape(artifact['geometry']);rings=original['geometry']['rings'];structural=review_cycles(rings,candidate);fill=review_geometry(rings,candidate)
        if len([d for d in structural['split_rings'] if d['type']=='two_holes'])!=1:raise ValueError('Expected one paired-hole contact')
        cases.append({'object_id':oid,'map':c['map'],'zone':c['zone'],'source_feature_sha256':c['source_feature_sha256'],'candidate_sha256':c['candidate_sha256'],'checks':fill,'cycle_review':structural,'area_difference_from_publisher_m2':candidate.area-original['attributes']['Shape__Area'],'recommendation':'supported_for_exact_version_acceptance','evidence_state':'DERIVED','activation_status':'not_activated'})
        print(oid,'fixed candidate cycle and fill review passed',flush=True)
    if {c['object_id'] for c in cases}!={27208875,27336229} or len(cases)!=2:raise ValueError('Wrong cohort')
    report={'method':'scripts/review_moosehead_spencer.py','method_sha256':digest(Path(__file__).read_bytes()),'evidence_state':'DERIVED','proposal_audit_sha256':PARENT_SHA,'county_audit_sha256':prior['county_audit_sha256'],'inputs':inputs,'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'numpy':np.__version__},'cases':cases,'review_conclusion':'Both fixed candidates preserve exact source cycles, their shell/hole roles and independent even-odd fill. Supported for exact-version acceptance after a tested extension of the county validator.','limits':['Cycle walk is separate from the proposal splitter; fill check is rerun using the previously tested independent ray-crossing algorithm. Same GEOS engine, not publisher/survey confirmation.','Archived source/map evidence is reused; no fresh retrieval or legal-currency determination.','Prior 10.2247 km² coverage scenario is not recomputed or promoted to current coverage.','No candidate regeneration, source edits, correction events, schema change or screening qualification.']}
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':build()
