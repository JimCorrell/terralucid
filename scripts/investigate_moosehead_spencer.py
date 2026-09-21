#!/usr/bin/env python3
"""Bounded investigation of two archived county features; propose, never activate."""
import json,math
from collections import defaultdict
from pathlib import Path
import shapely
from shapely.geometry import Polygon,LinearRing,Point,shape,mapping
from shapely.ops import unary_union
from prepare_source_staging import ROOT,canonical,digest
from investigate_osborn_zoning import split_single_touch,edges
from investigate_county_zoning_cases import interpret
from review_county_zoning_proposals import review_geometry
BASE=ROOT/'research/moosehead-spencer'
PARENT=ROOT/'research/piscataquis-zoning-holds'
PARENT_SHA='25f03b37818d1fc5cf25a6fa1e9264d48824c8585dbbf9776574dd6682905b6c'
COUNTY_SHA='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
ACTIVATION_SHA='f71944bb815efe7b873c5a49aace783c2056b072d89d2ddcfce9532ae12b05c5'

def split_touching_holes(ring):
    """Only two simple CCW hole loops, with disjoint interiors and one shared vertex.

    Preserve traversal coordinates and segment multiplicity exactly. Shell ownership
    and whole-feature validity are separate mandatory checks by interpret().
    """
    if len(ring)<7 or ring[0]!=ring[-1] or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in ring):raise ValueError('Expected finite closed 2D ring')
    if any(a==b for a,b in zip(ring,ring[1:])):raise ValueError('Consecutive duplicate vertex')
    positions=defaultdict(list)
    for i,p in enumerate(ring[:-1]):positions[tuple(p)].append(i)
    repeated=[v for v in positions.values() if len(v)>1]
    if len(repeated)!=1 or len(repeated[0])!=2:raise ValueError('Expected one twice-visited vertex')
    a,b=repeated[0];loops=[ring[a:b+1],ring[b:]+ring[1:a+1]]
    if any(len(r)<4 for r in loops):raise ValueError('Degenerate loop')
    polys=[Polygon(r) for r in loops]
    if any(not p.is_valid or p.area<=0 or not LinearRing(r).is_ccw for p,r in zip(polys,loops)):raise ValueError('Expected two simple counterclockwise holes')
    if not polys[0].intersection(polys[1]).equals(Point(ring[a])):raise ValueError('Expected only the shared vertex, no overlap or edge')
    if edges([ring])!=edges(loops):raise ValueError('Changed source segments')
    return loops,{'type':'two_touching_holes','zero_based_indices':[a,b],'repeated_vertex':ring[a],'loop_area_m2':[p.area for p in polys],'loop_coordinate_counts':[len(r) for r in loops],'counterclockwise':[True,True],'intersection_type':'Point','interior_overlap_m2':0,'segments_preserved_with_multiplicity':True}

def propose(rings):
    loops=[];splits=[]
    for i,r in enumerate(rings):
        if Polygon(r).is_valid:loops.append(r);continue
        try:
            p,d=split_single_touch(r);parts=[list(p.exterior.coords),list(p.interiors[0].coords)];d=dict(d,type='nested_shell_hole')
        except ValueError:parts,d=split_touching_holes(r)
        loops.extend(parts);splits.append(dict(d,source_ring=i))
    g,assembly=interpret(loops)
    if edges(rings)!=edges([list(p.exterior.coords) for p in g.geoms]+[list(h.coords) for p in g.geoms for h in p.interiors]):raise ValueError('Changed complete-feature segments')
    return g,{'splits':splits,'assembly':assembly}

def build():
    inputs={}
    def checked(path,sha=None):
        raw=path.read_bytes();actual=digest(raw)
        if sha is not None and actual!=sha:raise ValueError('Changed input: '+str(path))
        inputs[path.relative_to(ROOT).as_posix()]=actual;return raw
    parent=json.loads(checked(PARENT/'report.json',PARENT_SHA));county=json.loads(checked(ROOT/'research/piscataquis-ingestion/report.json',COUNTY_SHA))
    activation=json.loads(checked(ROOT/'research/county-corrections/report.json',ACTIVATION_SHA))
    checkpoint=json.loads(checked(ROOT/'research/county-corrections/checkpoint.json'))
    if checkpoint['audit_sha256']!=ACTIVATION_SHA or checkpoint['acceptances_loaded']!=3:raise ValueError('Wrong effective baseline')
    ranking=json.loads(checked(PARENT/'ranking.json',parent['inputs']['research/piscataquis-zoning-holds/ranking.json']))
    gap=shapely.from_wkb(checked(ROOT/'.local/piscataquis-held-zoning-gap.wkb',ranking['gap_wkb_sha256']))
    accepted=[]
    for c in activation['corrections']:
        accepted.append(shape(json.loads(checked(PARENT/'candidates'/f"{c['object_id']}.geojson",c['candidate_sha256']))['geometry']))
    gap=gap.difference(unary_union(accepted))
    maps=json.loads(checked(PARENT/'map-review.json',parent['inputs']['research/piscataquis-zoning-holds/map-review.json']))
    spec=parent['evidence']['specification/esri-ring-specification'];checked(PARENT/spec['response_path'],spec['sha256'])
    cases=[];candidates=[]
    for oid in [27208875,27336229]:
        prior=next(c for c in parent['cases'] if c['object_id']==oid)
        e=next(e for e in county['evidence'].values() if e['sha256']==prior['original_response_sha256'])
        original=next(f for f in json.loads(checked(ROOT/'research/piscataquis-ingestion'/e['response_path'],e['sha256']))['features'] if f['attributes']['OBJECTID']==oid)
        native_e=parent['evidence'][f'source/native-{oid}'];native=json.loads(checked(PARENT/native_e['response_path'],native_e['sha256']))
        if native.get('error') or native.get('exceededTransferLimit') or len(native['features'])!=1 or native['spatialReference'].get('latestWkid',native['spatialReference']['wkid'])!=26919:raise ValueError('Invalid native response')
        nf=native['features'][0]
        if nf!=original or digest(canonical(nf).encode())!=prior['county_feature_sha256']:raise ValueError('Original/native mismatch')
        ge=parent['evidence'][f'source/geojson-{oid}'];geo=json.loads(checked(PARENT/ge['response_path'],ge['sha256']))
        if geo.get('error') or geo.get('exceededTransferLimit') or len(geo['features'])!=1 or geo['crs']['properties']['name']!='EPSG:26919':raise ValueError('Invalid service variant')
        gf=geo['features'][0];gr=gf['geometry']['coordinates'];gr=gr if gf['geometry']['type']=='Polygon' else [r for p in gr for r in p]
        if gf['properties']!=nf['attributes'] or edges(gr)!=edges(nf['geometry']['rings']):raise ValueError('Service source segments/attributes differ')
        map_e=parent['evidence']['maps/'+prior['map']+'-map'];checked(PARENT/map_e['response_path'],map_e['sha256'])
        rings=nf['geometry']['rings'];g,details=propose(rings);checks=review_geometry(rings,g);candidates.append(g)
        feature={'type':'Feature','crs':{'type':'name','properties':{'name':'EPSG:26919'}},'properties':{'object_id':oid,'county_audit_sha256':COUNTY_SHA,'source_feature_sha256':prior['county_feature_sha256'],'status':'proposed_not_accepted','evidence_state':'DERIVED'},'geometry':mapping(g)}
        raw=(json.dumps(feature,sort_keys=True,indent=2)+'\n').encode();p=BASE/'candidates'/f'{oid}.geojson';p.write_bytes(raw);inputs[p.relative_to(ROOT).as_posix()]=digest(raw)
        cases.append({'object_id':oid,'map':prior['map'],'zone':prior['zone'],'source_feature_sha256':prior['county_feature_sha256'],'original_response_sha256':prior['original_response_sha256'],'native_matches_original':True,'service_segments_and_attributes_match':True,'service_geojson_valid':shape(gf['geometry']).is_valid,'source_ring_count':len(rings),'details':details,'independent_fill_check':checks,'publisher_area_m2':nf['attributes']['Shape__Area'],'area_difference_from_publisher_m2':g.area-nf['attributes']['Shape__Area'],'additional_effective_baseline_gap_m2':g.intersection(gap).area,'candidate_path':p.relative_to(ROOT).as_posix(),'candidate_sha256':digest(raw),'status':'proposed_not_accepted','map_evidence':maps['maps'][prior['map']+'-map']})
        print(oid,'candidate and independent fill checks passed',flush=True)
    for p in ['scripts/investigate_osborn_zoning.py','scripts/investigate_county_zoning_cases.py','scripts/review_county_zoning_proposals.py','scripts/prepare_source_staging.py']:checked(ROOT/p)
    if not candidates[0].disjoint(candidates[1]):raise ValueError('Unexpected overlap: combined area requires separate review')
    # The two disjoint candidates have disjoint intersections with the same gap.
    combined=sum(c['additional_effective_baseline_gap_m2'] for c in cases)
    report={'method':'scripts/investigate_moosehead_spencer.py','method_sha256':digest(Path(__file__).read_bytes()),'evidence_state':'DERIVED','county_audit_sha256':COUNTY_SHA,'prior_investigation_audit_sha256':PARENT_SHA,'effective_baseline_activation_audit_sha256':ACTIVATION_SHA,'effective_baseline_snapshot_id':checkpoint['dependency_snapshot_id'],'inputs':inputs,'source_observations':'Reuse checksum-pinned original county and PR29 service/map observations; no new retrieval or currency claim.','runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string},'cases':cases,'candidates_disjoint':True,'proposed_combined_additional_gap_m2':combined,'combined_area_method':'Sum of intersections after verifying candidates are disjoint; equivalent to union intersection.','review_conclusion':'Two bounded proposals preserve all source segments and independently reconstructed even-odd fill. Review before extending exact-version acceptance.','limits':['Proposals only; both source holds and all three existing acceptances remain unchanged.','Independent fill algorithm uses the same GEOS engine; not publisher confirmation or survey evidence.','Map context cannot certify exact vertex contact or legal currency; no tracing.','Gap contribution is a DERIVED scenario against the pinned PR31 effective baseline, not legal coverage or buildability.','No automatic repair, snapping, simplification, coordinate movement, screening qualification or activation.']}
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':build()
