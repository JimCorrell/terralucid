#!/usr/bin/env python3
"""Archived-source feasibility assessment; no proposals, acceptance or live writes."""
import json
from collections import Counter
from pathlib import Path
import shapely
from shapely.geometry import shape, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from prepare_source_staging import ROOT,canonical,digest
from investigate_moosehead_spencer import propose
from review_moosehead_spencer import review_cycles
from review_county_zoning_proposals import review_geometry
from refresh_county_ranking import parts

BASE=ROOT/'research/county-backlog-assessment'
RANK='research/seventeen-correction-ranking/report.json'
SHA='8b5f2fb7041826aea92ac697489fc8dea3308df3ffffd3384e31ff6e27f5b6e7'

def run():
    inputs={}
    def read(path,expected=None):
        raw=(ROOT/path).read_bytes();h=digest(raw)
        if expected is not None and h!=expected:raise ValueError('Changed input '+path)
        inputs[path]=h;return raw
    ranking=json.loads(read(RANK,SHA))
    for p in ['scripts/investigate_moosehead_spencer.py','scripts/investigate_county_zoning_cases.py','scripts/investigate_osborn_zoning.py','scripts/review_moosehead_spencer.py','scripts/review_county_zoning_proposals.py','scripts/refresh_county_ranking.py','scripts/prepare_source_staging.py']:read(p)
    accepted=[];features={};remaining={r['object_id'] for r in ranking['ranking']}
    for p,h in ranking['inputs'].items():
        if '/candidates/' in p:accepted.extend(parts(shape(json.loads(read(p,h))['geometry'])))
        elif 'lupc-zoning-page-' in p:
            for f in json.loads(read(p,h))['features']:
                if f['attributes']['OBJECTID'] in remaining:features[f['attributes']['OBJECTID']]=f
    assert set(features)==remaining and len(remaining)==145
    gap=shapely.from_wkb(read('.local/piscataquis-held-zoning-gap.wkb',ranking['inputs']['.local/piscataquis-held-zoning-gap.wkb']))
    gaps=parts(gap);gt=STRtree(gaps);at=STRtree(accepted)
    def contribution(g):
        hits=gt.query(g,predicate='intersects')
        c=unary_union(parts(g.intersection(unary_union([gaps[int(i)] for i in hits]))))
        hits=at.query(c)
        return c.difference(unary_union([accepted[int(i)] for i in hits])) if len(hits) else c
    rows=[];contributions={};envelopes=[]
    for r in ranking['ranking']:
        oid=r['object_id'];f=features[oid];assert digest(canonical(f).encode())==r['source_feature_sha256']
        rings=f['geometry']['rings'];points=[p for ring in rings for p in ring]
        env=box(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points));envelopes.append(env)
        row={'object_id':oid,'map':r['source_attributes']['MAP'],'zone':r['source_attributes']['ZONE'],'prior_rank':r['rank'],'hold':r['hold'],'source_feature_sha256':r['source_feature_sha256'],'response_sha256':r['response_sha256'],'ring_count':len(rings),'coordinate_count':len(points),'envelope_upper_bound_m2':r['envelope_uncovered_county_m2'],'status':'requires_new_method_or_source_evidence'}
        try:
            g,d=propose(rings);cycles=review_cycles(rings,g);fill=review_geometry(rings,g)
            c=contribution(g);contributions[oid]=c
            splits=Counter(s['type'] for s in d['splits']);nested=len(d['assembly']['nested_hole_assignments'])
            row.update(status='archived_geometry_checks_pass_only',split_types=dict(splits),nested_hole_assignments=nested,scenario_gain_m2=c.area,candidate_area_m2=g.area,cycle_roles_preserved=cycles['source_cycle_roles_preserved'],fill_checks=fill)
            assert c.area<=row['envelope_upper_bound_m2']+0.01
        except ValueError as e:row['reason']=str(e)
        rows.append(row);print(oid,row['status'],flush=True)
    supported=sorted([r for r in rows if r['object_id'] in contributions],key=lambda r:(-r['scenario_gain_m2'],r['object_id']))
    curves=[]
    for n in [3,5,10,20,40,len(supported)]:
        chosen=supported[:n];area=unary_union([contributions[r['object_id']] for r in chosen]).area
        curves.append({'count':len(chosen),'object_ids':[r['object_id'] for r in chosen],'union_scenario_gain_m2':area})
    # Union all held envelopes before intersecting, never sum overlapping upper bounds.
    print('Computing union envelope bound',flush=True)
    envelope_bound=contribution(unary_union(envelopes)).area
    county=json.loads(read('research/piscataquis-ingestion/report.json',ranking['source_audit_sha256']))
    summary={'counts':dict(Counter(r['status'] for r in rows)),'hold_families':dict(Counter(r['hold'].split('[')[0] for r in rows)),'map_count':len({r['map'] for r in rows}),'supported_map_count':len({r['map'] for r in supported}),'split_types':dict(sum((Counter(r.get('split_types',{})) for r in rows),Counter())),'nested_ownership_case_count':sum(r.get('nested_hole_assignments',0)>0 for r in rows),'union_envelope_upper_bound_m2':envelope_bound,'current_inventory_gap_m2':ranking['effective_gap_m2'],'gap_outside_all_held_envelopes_m2':ranking['effective_gap_m2']-envelope_bound,'scenario_curve':curves,'parcel_hold_counts':{s:county['summary'][s]['scope_relations']['held'] for s in ['ut-parcels','organized-parcels']}}
    report={'evidence_state':'DERIVED','status':'assessment_only_not_proposals','method':'scripts/assess_county_backlog.py','method_sha256':digest(Path(__file__).read_bytes()),'inputs':inputs,'geometry_snapshot_id':ranking['geometry_snapshot_id'],'source_audit_sha256':ranking['source_audit_sha256'],'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string},'summary':summary,'cases':rows,'scenario_priority_ids':[r['object_id'] for r in supported],'limits':['Archived-source computational feasibility only; no fresh native/GeoJSON comparison or official map review for these cases. Passing checks is not acceptance.','Scenario gains are conditional interpretations, not confirmed coverage, parcel utility or legal zoning. Unsupported features have unknown gains.','Sorted individual gains provide a reproducible scenario, not an optimal marginal-gain ordering. Union totals remove overlap.','Snapshot is pinned to PR44; check current dependencies before implementation. No live writes or holds cleared.','All county qualification issues, both amendment-date discrepancies and parcel/source/legal unknowns remain.']}
    BASE.mkdir(exist_ok=True);(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
