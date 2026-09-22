#!/usr/bin/env python3
"""Versioned ranking refresh after eight accepted county corrections."""
import json
from pathlib import Path
import shapely
from shapely.geometry import box,shape
from shapely.strtree import STRtree
from investigate_osborn_wetlands import decode
from prepare_source_staging import ROOT,canonical,digest
from refresh_county_ranking import AUDIT,OLD_SHA,ACTIVATIONS as FIRST_ACTIVATIONS,newly_covered,refreshed_area,jurisdiction_reductions,validate_dependencies
BASE=ROOT/'research/eight-correction-ranking'
ACTIVATIONS=FIRST_ACTIVATIONS|{'research/three-zoning-acceptance/report.json':'7e5ec1b5350fbb6d657551ef31d1739a34a4e3e22d0e5f312d7c5e8bd3e87c17'}
PREVIOUS_SHA='07efac22afa8829de039ada598fa06533f378c33edc720f40a255b67c75d0136'

def run():
    inputs={}
    def read(path,sha=None):
        p=ROOT/path;b=p.read_bytes();h=digest(b)
        if sha is not None and sha!=h:raise ValueError('Changed input '+path)
        inputs[path]=h;return b
    old=json.loads(read('research/piscataquis-zoning-holds/ranking.json',OLD_SHA))
    read(old['method'],old['method_sha256'])
    if old['county_audit_sha256']!=AUDIT:raise ValueError('Wrong historical county')
    gap=shapely.from_wkb(read('.local/piscataquis-held-zoning-gap.wkb',old['gap_wkb_sha256']))
    if not gap.is_valid or abs(gap.area-old['county_outside_valid_zoning_union_m2'])>0.01:raise ValueError('Changed gap')
    previous=json.loads(read('research/county-ranking-refresh/report.json',PREVIOUS_SHA))
    previous_rows={r['object_id']:r for r in previous['ranking']}
    for p in ['scripts/refresh_county_ranking.py','scripts/investigate_osborn_wetlands.py','scripts/prepare_source_staging.py']:read(p)
    d=json.loads(read('research/eight-correction-ranking/dependencies.json'))
    read('scripts/capture_county_ranking.sql')
    corrections=[];candidates=[]
    for path,sha in ACTIVATIONS.items():
        a=json.loads(read(path,sha))
        for c in a['corrections']:
            corrections.append(c)
            parent={'county-corrections':'piscataquis-zoning-holds','moosehead-spencer-acceptance':'moosehead-spencer','three-zoning-acceptance':'three-zoning-priorities'}[Path(path).parent.name]
            candidate=json.loads(read(f'research/{parent}/candidates/{c["object_id"]}.geojson',c['candidate_sha256']))
            if candidate['crs']['properties']['name']!='EPSG:26919':raise ValueError('Wrong CRS')
            g=shape(candidate['geometry'])
            if not g.is_valid:raise ValueError('Invalid accepted candidate')
            candidates.append(g)
    validate_dependencies(d,corrections,[r['object_id'] for r in old['ranking']])
    remaining=set(d['held_object_ids']);features={};civil=[]
    needed={r['response_sha256'] for r in old['ranking'] if r['object_id'] in remaining}
    for path,sha in old['inputs'].items():
        if sha not in needed and 'civil-boundaries-page-' not in path:continue
        page=json.loads(read(path,sha))
        for f in page['features']:
            if 'civil-boundaries-page-' in path:
                g,hold=decode(f['geometry']['rings'])
                if hold:raise ValueError('Held civil geometry')
                civil.append((f['attributes']['TOWN'],g))
            elif f['attributes']['OBJECTID'] in remaining:features[f['attributes']['OBJECTID']]=f
    print('Pinned sources and live dependencies verified; intersecting accepted coverage',flush=True)
    added=newly_covered(gap,candidates);tree=STRtree(added);rows=[]
    for rank,r in enumerate(old['ranking'],1):
        oid=r['object_id']
        if oid not in remaining:continue
        f=features[oid]
        if digest(canonical(f).encode())!=r['source_feature_sha256']:raise ValueError('Changed held feature')
        points=[p for ring in f['geometry']['rings'] for p in ring]
        env=box(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
        clipped=[added[int(i)].intersection(env) for i in tree.query(env,predicate='intersects')]
        reduction=sum(g.area for g in clipped)
        reductions=jurisdiction_reductions(clipped,civil)
        jurisdictions={name:refreshed_area(area,reductions[name]) for name,area in r['potential_gap_by_civil_name_m2'].items() if name in reductions}
        if set(jurisdictions)!=set(r['potential_gap_by_civil_name_m2']):raise ValueError('Missing jurisdiction')
        prior=previous_rows[oid]
        updated=refreshed_area(r['envelope_uncovered_county_m2'],reduction)
        additional=prior['envelope_uncovered_county_m2']-updated
        if additional < -0.01:raise ValueError('Coverage regressed from five-correction ranking')
        rows.append({**r,'five_correction_rank':prior['rank'],'five_correction_envelope_uncovered_county_m2':prior['envelope_uncovered_county_m2'],'additional_reduction_since_five_corrections_m2':max(0.,additional),'previous_rank':rank,'previous_envelope_uncovered_county_m2':r['envelope_uncovered_county_m2'],'accepted_coverage_reduction_m2':reduction,'envelope_uncovered_county_m2':refreshed_area(r['envelope_uncovered_county_m2'],reduction),'potential_gap_by_civil_name_m2':jurisdictions})
    rows.sort(key=lambda r:(-r['envelope_uncovered_county_m2'],r['object_id']))
    for i,r in enumerate(rows,1):r['rank']=i
    report={'evidence_state':'DERIVED','method':'scripts/refresh_eight_correction_ranking.py','method_sha256':digest(Path(__file__).read_bytes()),'inputs':inputs,'source_audit_sha256':AUDIT,'historical_ranking_sha256':OLD_SHA,'five_correction_ranking_sha256':PREVIOUS_SHA,'additional_coverage_since_five_corrections_m2':sum(g.area for g in added)-previous['newly_covered_m2'],'geometry_snapshot_id':d['snapshot']['snapshot_id'],'geometry_dependencies':d['snapshot']['dependencies'],'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string},'original_held_zoning_rows':162,'effective_held_zoning_rows':len(rows),'removed_accepted_object_ids':sorted(c['object_id'] for c in corrections),'original_gap_m2':gap.area,'newly_covered_m2':sum(g.area for g in added),'effective_gap_m2':refreshed_area(gap.area,sum(g.area for g in added)),'qualified_for_parcel_screening':False,'ranking':rows,'limits':['Envelope/gap overlap is an upper bound, not polygon coverage; priorities overlap and must not be added.','Inventory coverage includes retained source flags; a geometry gap does not establish absent zoning or municipal applicability.','This ranks geometry investigations, not parcels, suitability, legal zoning or acquisition readiness.','Original evidence is preserved; only the eight accepted exact versions affect this refresh. Check the snapshot against the intended audit before use.']}
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'remaining':len(rows),'newly_covered_km2':report['newly_covered_m2']/1e6,'top':[{'id':r['object_id'],'previous_rank':r['previous_rank'],'km2':r['envelope_uncovered_county_m2']/1e6,'attributes':r['source_attributes']} for r in rows[:10]]},indent=2))
if __name__=='__main__':run()
