#!/usr/bin/env python3
"""Bounded proposals for five reviewed features; never an ingestion fallback."""
import json,math
from pathlib import Path
from collections import Counter
import shapely
from shapely.geometry import Polygon,MultiPolygon,LinearRing,shape,mapping
from shapely.validation import explain_validity
from investigate_osborn_zoning import split_single_touch,edges
from prepare_source_staging import ROOT,canonical,digest

BASE=ROOT/'research/piscataquis-zoning-holds'
IDS=[27334504,27208875,27336229,27249007,27291625]

def interpret(rings):
    """Split only proved nested single touches; attach holes to innermost shells.

    Fail on crossing, nonnested contacts, duplicate shells, unsupported dimensions,
    or invalid final topology. No tolerance, snapping, simplification or make_valid.
    """
    loops=[];splits=[]
    for i,r in enumerate(rings):
        if len(r)<4 or r[0]!=r[-1] or any(len(p)!=2 or not all(math.isfinite(x) for x in p) for p in r):raise ValueError('Unsupported ring')
        p=Polygon(r)
        if p.is_valid:loops.append(r)
        else:
            candidate,diagnostic=split_single_touch(r)
            loops.extend([list(candidate.exterior.coords),list(candidate.interiors[0].coords)])
            splits.append({'source_ring':i,'diagnostic':diagnostic})
    shells=[Polygon(r) for r in loops if not LinearRing(r).is_ccw]
    holes=[Polygon(r) for r in loops if LinearRing(r).is_ccw]
    if not shells:raise ValueError('No clockwise shells')
    assigned=[[] for _ in shells];nested=[]
    for i,h in enumerate(holes):
        owners=[j for j,s in enumerate(shells) if s.covers(h)]
        if not owners:raise ValueError('Uncontained hole')
        owners.sort(key=lambda j:shells[j].area)
        if any(not shells[b].covers(shells[a]) or shells[b].equals(shells[a]) for a,b in zip(owners,owners[1:])):raise ValueError('Non-nested or duplicate containing shells')
        assigned[owners[0]].append(list(h.exterior.coords))
        if len(owners)>1:nested.append({'hole_index_after_split':i,'containing_shell_indices':owners,'chosen_innermost_shell':owners[0]})
    parts=[Polygon(s.exterior.coords,h) for s,h in zip(shells,assigned)]
    g=MultiPolygon(parts)
    if not g.is_valid or g.is_empty:raise ValueError('Invalid final topology: '+explain_validity(g))
    output=[list(p.exterior.coords) for p in parts]+[list(h.coords) for p in parts for h in p.interiors]
    if edges(rings)!=edges(output):raise ValueError('Boundary segment multiset changed')
    return g,{'splits':splits,'nested_hole_assignments':nested,'source_rings':len(rings),'candidate_shells':len(parts),'candidate_holes':sum(len(p.interiors) for p in parts),'segments_preserved_with_multiplicity':True}

def build():
    ranking=json.loads((BASE/'ranking.json').read_bytes());evidence={};payload={}
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            raw=(log.parent/r['response_file']).read_bytes()
            if r['http_status']!=200 or digest(raw)!=r['sha256'] or len(raw)!=r['bytes']:raise ValueError('Failed/changed retrieval')
            evidence[log.parent.name+'/'+r['id']]=dict(r,response_path=(log.parent/r['response_file']).relative_to(BASE).as_posix());payload[r['id']]=raw
    gap_raw=(ROOT/'.local/piscataquis-held-zoning-gap.wkb').read_bytes()
    if digest(gap_raw)!=ranking['gap_wkb_sha256']:raise ValueError('Gap cache changed; rerun ranking')
    gap=shapely.from_wkb(gap_raw);candidates=[]
    countylog=json.loads((ROOT/'research/piscataquis-ingestion/runs/capture/results.json').read_bytes());cases=[]
    (BASE/'candidates').mkdir(exist_ok=True)
    for oid in IDS:
        ranked=next(r for r in ranking['ranking'] if r['object_id']==oid)
        record=next(r for r in countylog if r['sha256']==ranked['response_sha256'])
        raw=(ROOT/'research/piscataquis-ingestion/runs/capture'/record['response_file']).read_bytes()
        if digest(raw)!=ranked['response_sha256']:raise ValueError('Original changed')
        old=next(f for f in json.loads(raw)['features'] if f['attributes']['OBJECTID']==oid)
        if digest(canonical(old).encode())!=ranked['source_feature_sha256']:raise ValueError('Feature mismatch')
        native=json.loads(payload[f'native-{oid}']);geo=json.loads(payload[f'geojson-{oid}'])
        for d in [native,geo]:
            if d.get('error') or d.get('exceededTransferLimit') or len(d.get('features',[]))!=1:raise ValueError('Incomplete feature response')
        if native['spatialReference'].get('latestWkid',native['spatialReference']['wkid'])!=26919 or geo.get('crs',{}).get('properties',{}).get('name')!='EPSG:26919':raise ValueError('Unexpected CRS')
        nf=native['features'][0];gf=geo['features'][0]
        if nf['attributes']['OBJECTID']!=oid or gf['properties']['OBJECTID']!=oid:raise ValueError('Unexpected identity')
        unchanged=old['geometry']==nf['geometry'] and all(nf['attributes'].get(k)==v for k,v in old['attributes'].items())
        if not unchanged:raise ValueError('Changed source version; no proposal')
        gg=shape(gf['geometry']);gr=gf['geometry']['coordinates']
        geo_rings=gr if gf['geometry']['type']=='Polygon' else [r for p in gr for r in p]
        rings=nf['geometry']['rings']
        c={'object_id':oid,'map':old['attributes']['MAP'],'zone':old['attributes']['ZONE'],'county_feature_sha256':ranked['source_feature_sha256'],'original_response_sha256':ranked['response_sha256'],'native_feature_sha256':digest(canonical(nf).encode()),'native_coordinates_and_selected_attributes_unchanged':unchanged,'geojson_attributes_match_native':nf['attributes']==gf['properties'],'service_geojson_valid':gg.is_valid,'service_geojson_validity':explain_validity(gg),'service_geojson_same_native_segments':edges(rings)==edges(geo_rings),'original_hold':ranked['hold'],'rank':1+ranking['ranking'].index(ranked),'invalid_rings':[{'index':i,'reason':explain_validity(Polygon(r))} for i,r in enumerate(rings) if not Polygon(r).is_valid]}
        try:
            g,details=interpret(rings)
            if not c['geojson_attributes_match_native'] or not c['service_geojson_same_native_segments']:raise ValueError('Service variants differ')
            candidates.append(g)
            artifact={'type':'Feature','crs':{'type':'name','properties':{'name':'EPSG:26919'}},'properties':{'object_id':oid,'county_audit_sha256':ranking['county_audit_sha256'],'source_feature_sha256':ranked['source_feature_sha256'],'status':'proposed_not_accepted','evidence_state':'DERIVED'},'geometry':mapping(g)}
            raw=(json.dumps(artifact,sort_keys=True,indent=2)+'\n').encode();p=BASE/'candidates'/f'{oid}.geojson';p.write_bytes(raw)
            c.update(candidate_equals_service_geojson=g.equals(gg) if gg.is_valid else None,additional_gap_area_m2=g.intersection(gap).area,status='proposed_not_accepted',candidate_sha256=digest(raw),candidate_path=p.relative_to(ROOT).as_posix(),candidate_area_m2=g.area,publisher_area_m2=old['attributes']['Shape__Area'],area_difference_from_publisher_m2=g.area-old['attributes']['Shape__Area'],details=details)
        except ValueError as e:c.update(status='held_no_proposal',reason=str(e))
        cases.append(c)
    paths=['scripts/investigate_county_zoning.py','scripts/investigate_osborn_zoning.py','scripts/investigate_osborn_wetlands.py','research/piscataquis-zoning-holds/ranking.json','research/piscataquis-zoning-holds/map-review.json']
    report={'evidence_state':'DERIVED','method':'scripts/investigate_county_zoning_cases.py','method_sha256':digest(Path(__file__).read_bytes()),'evidence':evidence,'inputs':{p:digest((ROOT/p).read_bytes()) for p in paths},'county_audit_sha256':ranking['county_audit_sha256'],'cases':cases,'proposed_combined_gap_area_m2':shapely.union_all(candidates).intersection(gap).area,'limits':['Proposals only. County holds and effective geometry unchanged.','PDFs corroborate general context, not exact vertex topology or legal currency.','Published area agreement is a numeric cross-check, not authority.','Unsupported touch patterns remain held; no automatic general repair.','No parcel screening or geometry acceptance; Osborn acceptance does not transfer.']}
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in c.items() if k in ('object_id','status','reason','service_geojson_valid','service_geojson_same_native_segments','candidate_area_m2','area_difference_from_publisher_m2')} for c in cases],indent=2))

if __name__=='__main__':build()
