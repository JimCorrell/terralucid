#!/usr/bin/env python3
"""Independently review fixed county candidates; never accept or generate replacements."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import shapely
from shapely.geometry import LineString,shape,Polygon
from shapely.ops import polygonize,unary_union
from shapely.strtree import STRtree
from prepare_source_staging import ROOT,canonical,digest

BASE=ROOT/'research/piscataquis-zoning-review'
PARENT=ROOT/'research/piscataquis-zoning-holds'
PARENT_SHA='25f03b37818d1fc5cf25a6fa1e9264d48824c8585dbbf9776574dd6682905b6c'

def segments(rings):
    return Counter(tuple(sorted((tuple(a),tuple(b)))) for r in rings for a,b in zip(r,r[1:]))

def odd_inside(ring,x,y):
    """Half-open horizontal ray crossings; independent of proposal ring ownership."""
    a=np.asarray(ring,dtype=float);x1,y1=a[:-1,0],a[:-1,1];x2,y2=a[1:,0],a[1:,1]
    crosses=(y1>y)!=(y2>y)
    hits=x1[crosses]+(y-y1[crosses])*(x2[crosses]-x1[crosses])/(y2[crosses]-y1[crosses])
    return int(np.count_nonzero(hits>x))%2==1

def review_geometry(rings,candidate):
    if not candidate.is_valid or candidate.is_empty or candidate.geom_type not in ('Polygon','MultiPolygon'):raise ValueError('Invalid candidate')
    parts=list(candidate.geoms) if candidate.geom_type=='MultiPolygon' else [candidate]
    out=[list(p.exterior.coords) for p in parts]+[list(h.coords) for p in parts for h in p.interiors]
    if segments(rings)!=segments(out):raise ValueError('Changed original segment multiset')
    # Noding/polygonization is a diagnostic of original linework only. It never
    # writes a candidate or changes any stored source/correction geometry.
    linework=unary_union([LineString(r) for r in rings]);faces=list(polygonize(linework))
    if not faces:raise ValueError('No bounded source faces')
    tree=STRtree([Polygon(r).envelope for r in rings]);inside=[];mismatches=0;min_clearance=float('inf')
    for face in faces:
        p=face.representative_point();clearance=p.distance(linework)
        if clearance<=0:raise ValueError('Face sample on source boundary')
        min_clearance=min(min_clearance,clearance)
        parity=sum(odd_inside(rings[int(i)],p.x,p.y) for i in tree.query(p))%2
        if parity:inside.append(face)
        if bool(parity)!=candidate.contains(p):mismatches+=1
    diagnostic=unary_union(inside)
    equal=diagnostic.equals(candidate);difference=diagnostic.symmetric_difference(candidate).area
    if mismatches or not equal or difference!=0:raise ValueError('Candidate does not preserve source even-odd fill')
    return {'all_segments_preserved_with_multiplicity':True,'source_faces':len(faces),'filled_faces':len(inside),'face_classification_mismatches':mismatches,'minimum_sample_boundary_distance_m':min_clearance,'equals_independent_even_odd_fill':equal,'symmetric_difference_m2':difference,'candidate_valid':True,'candidate_area_m2':candidate.area}

def build():
    raw=(PARENT/'report.json').read_bytes()
    if digest(raw)!=PARENT_SHA:raise ValueError('Wrong proposal audit')
    prior=json.loads(raw);inputs={'research/piscataquis-zoning-holds/report.json':PARENT_SHA}
    if digest((ROOT/prior['method']).read_bytes())!=prior['method_sha256']:raise ValueError('Changed proposal method')
    inputs[prior['method']]=prior['method_sha256']
    # Verify the complete parent evidence chain, including all maps/specification.
    for relative,sha in prior['inputs'].items():
        if digest((ROOT/relative).read_bytes())!=sha:raise ValueError('Changed parent dependency')
        inputs[relative]=sha
    for e in prior['evidence'].values():
        p=PARENT/e['response_path'];data=p.read_bytes()
        if digest(data)!=e['sha256'] or len(data)!=e['bytes']:raise ValueError('Changed source evidence')
        inputs[p.relative_to(ROOT).as_posix()]=e['sha256']
    county_path=ROOT/'research/piscataquis-ingestion/report.json';county_raw=county_path.read_bytes()
    if digest(county_raw)!=prior['county_audit_sha256']:raise ValueError('Changed original county audit')
    inputs[county_path.relative_to(ROOT).as_posix()]=digest(county_raw);county=json.loads(county_raw)
    cases=[]
    for c in prior['cases']:
        if c['status']!='proposed_not_accepted':continue
        oid=c['object_id'];data=(ROOT/c['candidate_path']).read_bytes()
        if digest(data)!=c['candidate_sha256']:raise ValueError('Changed candidate bytes')
        inputs[c['candidate_path']]=c['candidate_sha256'];artifact=json.loads(data)
        if artifact['properties']['source_feature_sha256']!=c['county_feature_sha256'] or artifact['properties']['county_audit_sha256']!=prior['county_audit_sha256'] or artifact['properties']['object_id']!=oid or artifact['crs']['properties']['name']!='EPSG:26919':raise ValueError('Wrong candidate source/version/CRS')
        native=json.loads((PARENT/prior['evidence'][f'source/native-{oid}']['response_path']).read_bytes());nf=native['features'][0]
        if digest(canonical(nf).encode())!=c['county_feature_sha256'] or native['spatialReference']['wkid']!=26919:raise ValueError('Native source/version mismatch')
        original_evidence=next(e for e in county['evidence'].values() if e['sha256']==c['original_response_sha256'])
        original_path=ROOT/'research/piscataquis-ingestion'/original_evidence['response_path'];original_raw=original_path.read_bytes()
        if digest(original_raw)!=original_evidence['sha256']:raise ValueError('Changed original county page')
        original=next(f for f in json.loads(original_raw)['features'] if f['attributes']['OBJECTID']==oid)
        if original!=nf:raise ValueError('Original county feature differs from reviewed native source')
        inputs[original_path.relative_to(ROOT).as_posix()]=digest(original_raw)
        candidate=shape(artifact['geometry']);checks=review_geometry(nf['geometry']['rings'],candidate)
        geo=json.loads((PARENT/prior['evidence'][f'source/geojson-{oid}']['response_path']).read_bytes());gf=geo['features'][0];g=shape(gf['geometry'])
        if gf['properties']!=nf['attributes'] or geo['crs']['properties']['name']!='EPSG:26919':raise ValueError('Service identity/CRS differs')
        checks.update(service_geojson_valid=g.is_valid,candidate_equals_valid_service_geojson=candidate.equals(g) if g.is_valid else None,area_difference_from_publisher_m2=candidate.area-nf['attributes']['Shape__Area'])
        cases.append({'object_id':oid,'map':c['map'],'zone':c['zone'],'source_feature_sha256':c['county_feature_sha256'],'candidate_sha256':c['candidate_sha256'],'checks':checks,'recommendation':'supported_for_exact_version_acceptance','evidence_state':'DERIVED','activation_status':'not_activated'})
        print(oid,'independent fill review passed',flush=True)
    if len(cases)!=3:raise ValueError('Expected exactly three proposals')
    report={'evidence_state':'DERIVED','method':'scripts/review_county_zoning_proposals.py','method_sha256':digest(Path(__file__).read_bytes()),'proposal_audit_sha256':PARENT_SHA,'county_audit_sha256':prior['county_audit_sha256'],'inputs':inputs,'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'numpy':np.__version__},'cases':cases,'review_conclusion':'All three candidates preserve source linework and independently reconstructed even-odd fill. Recommend exact-version acceptance after a county correction layer is implemented and validated.','limits':['Independent algorithm, same GEOS topology engine; not independent survey or publisher approval.','Review applies to archived versions only; no new source freshness or legal-currency determination.','Map review from the proposal audit is retained for context, not exact topology.','No correction event, default geometry change or screening qualification is created by this review.']}
    BASE.mkdir(exist_ok=True);(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')

if __name__=='__main__':build()
