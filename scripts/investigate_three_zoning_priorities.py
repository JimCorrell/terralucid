#!/usr/bin/env python3
"""Three exact-source proposals with separate cycle/fill checks; no activation."""
import json
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,shape,mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.validation import explain_validity
from prepare_source_staging import ROOT,canonical,digest
from investigate_moosehead_spencer import propose
from investigate_osborn_zoning import edges
from review_moosehead_spencer import review_cycles
from review_county_zoning_proposals import review_geometry
from refresh_county_ranking import parts,newly_covered,validate_dependencies,ACTIVATIONS,AUDIT

BASE=ROOT/'research/three-zoning-priorities'
RANKING='research/county-ranking-refresh/report.json'
RANKING_SHA='07efac22afa8829de039ada598fa06533f378c33edc720f40a255b67c75d0136'
IDS=[27304757,27270812,27207268]

def compare_source(original,native,geo,oid):
    for d in [native,geo]:
        if d.get('error') or d.get('exceededTransferLimit') or len(d.get('features',[]))!=1:raise ValueError('Incomplete source response')
    if native['spatialReference'].get('latestWkid',native['spatialReference']['wkid'])!=26919 or geo.get('crs',{}).get('properties',{}).get('name')!='EPSG:26919':raise ValueError('Wrong source CRS')
    nf=native['features'][0];gf=geo['features'][0]
    if nf!=original or nf['attributes']['OBJECTID']!=oid or gf['properties']!=nf['attributes']:raise ValueError('Changed source version or identity')
    gr=gf['geometry']['coordinates']
    if gf['geometry']['type']=='MultiPolygon':gr=[r for p in gr for r in p]
    elif gf['geometry']['type']!='Polygon':raise ValueError('Non-polygon service variant')
    if edges(gr)!=edges(nf['geometry']['rings']):raise ValueError('Service variant changes boundary segments')
    return shape(gf['geometry'])

def scenario_area(gap,proposals,accepted):
    """Union proposal contributions once, then subtract accepted baseline locally."""
    cp=[p for g in accepted for p in parts(g)];tree=STRtree(cp);area=0.
    for p in newly_covered(gap,proposals):
        hits=tree.query(p,predicate='intersects')
        area+=(p.difference(unary_union([cp[int(i)] for i in hits])) if len(hits) else p).area
    return area

def build():
    inputs={}
    def checked(path,sha=None):
        p=ROOT/path;raw=p.read_bytes();h=digest(raw)
        if sha is not None and h!=sha:raise ValueError('Changed input '+path)
        inputs[path]=h;return raw
    def rel(p):return p.relative_to(ROOT).as_posix()
    ranking=json.loads(checked(RANKING,RANKING_SHA))
    if ranking['source_audit_sha256']!=AUDIT or [c['object_id'] for c in ranking['ranking'][:3]]!=IDS:raise ValueError('Wrong ranked cohort')
    deps=json.loads(checked(rel(BASE/'dependencies.json')))
    corrections=[];accepted=[]
    for p,h in ACTIVATIONS.items():
        activation=json.loads(checked(p,h))
        for c in activation['corrections']:
            corrections.append(c);parent='piscataquis-zoning-holds' if 'county-corrections/' in p else 'moosehead-spencer'
            accepted.append(shape(json.loads(checked(f'research/{parent}/candidates/{c["object_id"]}.geojson',c['candidate_sha256']))['geometry']))
    old=json.loads(checked('research/piscataquis-zoning-holds/ranking.json',ranking['historical_ranking_sha256']))
    validate_dependencies(deps,corrections,[c['object_id'] for c in old['ranking']])
    if deps['snapshot']['snapshot_id']!=ranking['geometry_snapshot_id'] or deps['snapshot']['dependencies']!=ranking['geometry_dependencies']:raise ValueError('Ranking needs refresh')
    gap=shapely.from_wkb(checked('.local/piscataquis-held-zoning-gap.wkb',old['gap_wkb_sha256']))
    maps=json.loads(checked(rel(BASE/'map-review.json')));evidence={};payload={}
    for log in sorted((BASE/'runs').glob('*/results.json')):
        records=json.loads(checked(rel(log)))
        for e in records:
            key=log.parent.name+'/'+e['id'];evidence[key]=dict(e)
            if 'response_file' not in e:continue
            raw=checked(rel(log.parent/e['response_file']),e['sha256'])
            if len(raw)!=e['bytes'] or e['http_status']!=200:raise ValueError('Incomplete/failed payload')
            evidence[key]['response_path']=rel(log.parent/e['response_file']);payload[e['id']]=(raw,key)
    for p in BASE.glob('*probes.json'):checked(rel(p))
    checked(rel(BASE/'registry.json'))
    cases=[];candidates=[];(BASE/'candidates').mkdir(exist_ok=True)
    for ranked in ranking['ranking'][:3]:
        oid=ranked['object_id'];path=next(p for p,h in ranking['inputs'].items() if h==ranked['response_sha256'])
        original=next(f for f in json.loads(checked(path,ranked['response_sha256']))['features'] if f['attributes']['OBJECTID']==oid)
        if digest(canonical(original).encode())!=ranked['source_feature_sha256']:raise ValueError('Wrong original feature')
        native=json.loads(payload[f'native-{oid}'][0]);geo=json.loads(payload[f'geojson-{oid}'][0]);gg=compare_source(original,native,geo,oid)
        mapname=original['attributes']['MAP'];me=maps['maps'][mapname]
        if digest(payload[mapname+'-map'][0])!=me['pdf_sha256']:raise ValueError('Map review version differs')
        rings=original['geometry']['rings'];candidate,details=propose(rings)
        # Read the serialized fixed proposal back for checks by distinct algorithms.
        artifact={'type':'Feature','crs':{'type':'name','properties':{'name':'EPSG:26919'}},'properties':{'object_id':oid,'county_audit_sha256':AUDIT,'source_feature_sha256':ranked['source_feature_sha256'],'status':'proposed_not_accepted','evidence_state':'DERIVED'},'geometry':mapping(candidate)}
        path=BASE/'candidates'/f'{oid}.geojson';path.write_text(json.dumps(artifact,sort_keys=True,indent=2)+'\n')
        fixed=shape(json.loads(checked(rel(path)))['geometry']);cycle=review_cycles(rings,fixed);fill=review_geometry(rings,fixed)
        candidates.append(fixed)
        cases.append({'object_id':oid,'rank':ranked['rank'],'map':mapname,'zone':original['attributes']['ZONE'],'source_feature_sha256':ranked['source_feature_sha256'],'original_response_sha256':ranked['response_sha256'],'native_evidence':payload[f'native-{oid}'][1],'geojson_evidence':payload[f'geojson-{oid}'][1],'native_matches_original':True,'service_attributes_and_segments_match':True,'service_geojson_valid':gg.is_valid,'service_geojson_validity':explain_validity(gg),'original_hold':ranked['hold'],'source_ring_count':len(rings),'invalid_rings':[{'index':i,'reason':explain_validity(Polygon(r))} for i,r in enumerate(rings) if not Polygon(r).is_valid],'details':details,'cycle_review':cycle,'independent_fill_check':fill,'publisher_area_m2':original['attributes']['Shape__Area'],'area_difference_from_publisher_m2':fixed.area-original['attributes']['Shape__Area'],'additional_effective_baseline_gap_m2':scenario_area(gap,[fixed],accepted),'candidate_path':rel(path),'candidate_sha256':inputs[rel(path)],'status':'proposed_not_accepted','recommendation':'supported_for_exact_version_acceptance_after_validator_extension','map_evidence':me})
        print(oid,'source, fixed cycles and fill verified',flush=True)
    for p in ['scripts/investigate_moosehead_spencer.py','scripts/investigate_county_zoning_cases.py','scripts/investigate_osborn_zoning.py','scripts/review_moosehead_spencer.py','scripts/review_county_zoning_proposals.py','scripts/refresh_county_ranking.py','scripts/prepare_source_staging.py','scripts/probe_sources.py','scripts/collect_document_evidence.py','scripts/capture_county_ranking.sql']:checked(p)
    # Retain the archived representation specification used by the existing method.
    parent=json.loads(checked('research/piscataquis-zoning-holds/report.json','25f03b37818d1fc5cf25a6fa1e9264d48824c8585dbbf9776574dd6682905b6c'))
    spec=parent['evidence']['specification/esri-ring-specification'];checked('research/piscataquis-zoning-holds/'+spec['response_path'],spec['sha256'])
    report={'method':'scripts/investigate_three_zoning_priorities.py','method_sha256':digest(Path(__file__).read_bytes()),'evidence_state':'DERIVED','source_audit_sha256':AUDIT,'ranking_audit_sha256':RANKING_SHA,'geometry_snapshot_id':deps['snapshot']['snapshot_id'],'geometry_dependencies':deps['snapshot']['dependencies'],'inputs':inputs,'evidence':evidence,'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'numpy':np.__version__},'cases':cases,'proposed_combined_additional_gap_m2':scenario_area(gap,candidates,accepted),'scenario_method':'Union of proposal intersections with the original valid-zoning gap, minus union of all five accepted candidates; spatially indexed exact overlay.','review_conclusion':'All three exact-source proposals preserve complete segment multiplicity, source cycle roles and independent even-odd fill. Supported for reviewable exact-version activation after a tested extension of the bounded county validator.','limits':['No activation: all 157 zoning and 21 parcel holds remain; five prior acceptances are unchanged.','Distinct cycle/fill algorithms use the same GEOS engine and are not publisher approval or survey evidence.','Official maps provide context and limitations, not exact contact coordinates or legal currency.','Scenario is potential usable inventory geometry, not absent zoning, buildability or qualified parcel screening.']}
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print('Combined scenario km2',report['proposed_combined_additional_gap_m2']/1e6,flush=True)
if __name__=='__main__':build()
