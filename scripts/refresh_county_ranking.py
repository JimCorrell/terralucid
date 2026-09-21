#!/usr/bin/env python3
"""Refresh the historical envelope upper bounds against pinned accepted geometry."""
import json
from collections import Counter
from pathlib import Path
import shapely
from shapely.geometry import box, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
from investigate_osborn_wetlands import decode
from prepare_source_staging import ROOT, canonical, digest

BASE=ROOT/'research/county-ranking-refresh'
AUDIT='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
OLD_SHA='e346d801cff4cad0a65494a53d3992199848266bbe1693de28a3a3b4efb02768'
ACTIVATIONS={
 'research/county-corrections/report.json':'f71944bb815efe7b873c5a49aace783c2056b072d89d2ddcfce9532ae12b05c5',
 'research/moosehead-spencer-acceptance/report.json':'29eb98bf8d6fd719aebb2cf1c1cd062169378a336564a62a8a0b0d983a1fd464'}

def parts(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    if hasattr(g,'geoms'):return [p for child in g.geoms for p in parts(child)]
    return []

def newly_covered(gap,candidates):
    """Union locally before intersecting: overlapping candidates count once."""
    cp=[p for g in candidates for p in parts(g)];tree=STRtree(cp);out=[]
    for p in parts(gap):
        hits=tree.query(p,predicate='intersects')
        if len(hits):out.extend(parts(p.intersection(unary_union([cp[int(i)] for i in hits]))))
    return out

def refreshed_area(original,reduction):
    value=original-reduction
    if value < -0.01 or reduction < -0.01:raise ValueError('Non-monotonic coverage')
    return max(0.,value)

def jurisdiction_reductions(clipped,civil):
    # One civil name may comprise many disjoint records (including islands).
    reductions=Counter()
    for name,g in civil:
        reductions[name]+=sum(p.intersection(g).area for p in clipped if p.intersects(g))
    return reductions

def validate_dependencies(d,corrections,old_ids):
    s=d['snapshot']
    if d['source_audit_sha256']!=AUDIT or s['source_audit_sha256']!=AUDIT or s['needs_revisit']:raise ValueError('Stale/wrong source snapshot')
    expected={c['correction_id']:{'event_id':c['acceptance']['event_id'],'status':'accepted','candidate_sha256':c['candidate_sha256'],'source_input_sha256':c['source_input_sha256']} for c in corrections}
    if s['dependencies']!=expected:raise ValueError('Changed correction dependencies')
    expected_rows=[{'object_id':c['object_id'],'correction_id':c['correction_id'],'candidate_sha256':c['candidate_sha256'],'geometry_event_id':c['acceptance']['event_id'],'source_input_sha256':c['source_input_sha256']} for c in corrections]
    if sorted(d['accepted'],key=lambda x:x['object_id'])!=sorted(expected_rows,key=lambda x:x['object_id']):raise ValueError('Changed accepted inputs')
    remaining=set(old_ids)-{c['object_id'] for c in corrections}
    if len(d['held_object_ids'])!=len(remaining) or set(d['held_object_ids'])!=remaining:raise ValueError('Changed held cohort')

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
    d=json.loads(read('research/county-ranking-refresh/dependencies.json'))
    read('scripts/capture_county_ranking.sql')
    corrections=[];candidates=[]
    for path,sha in ACTIVATIONS.items():
        a=json.loads(read(path,sha))
        for c in a['corrections']:
            corrections.append(c)
            parent='piscataquis-zoning-holds' if 'county-corrections/' in path else 'moosehead-spencer'
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
        rows.append({**r,'previous_rank':rank,'previous_envelope_uncovered_county_m2':r['envelope_uncovered_county_m2'],'accepted_coverage_reduction_m2':reduction,'envelope_uncovered_county_m2':refreshed_area(r['envelope_uncovered_county_m2'],reduction),'potential_gap_by_civil_name_m2':jurisdictions})
    rows.sort(key=lambda r:(-r['envelope_uncovered_county_m2'],r['object_id']))
    for i,r in enumerate(rows,1):r['rank']=i
    report={'evidence_state':'DERIVED','method':'scripts/refresh_county_ranking.py','method_sha256':digest(Path(__file__).read_bytes()),'inputs':inputs,'source_audit_sha256':AUDIT,'historical_ranking_sha256':OLD_SHA,'geometry_snapshot_id':d['snapshot']['snapshot_id'],'geometry_dependencies':d['snapshot']['dependencies'],'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string},'original_held_zoning_rows':162,'effective_held_zoning_rows':len(rows),'removed_accepted_object_ids':sorted(c['object_id'] for c in corrections),'original_gap_m2':gap.area,'newly_covered_m2':sum(g.area for g in added),'effective_gap_m2':refreshed_area(gap.area,sum(g.area for g in added)),'qualified_for_parcel_screening':False,'ranking':rows,'limits':['Envelope/gap overlap is an upper bound, not polygon coverage; priorities overlap and must not be added.','Inventory coverage includes retained source flags; a geometry gap does not establish absent zoning or municipal applicability.','This ranks geometry investigations, not parcels, suitability, legal zoning or acquisition readiness.','Original evidence is preserved; only the five accepted exact versions affect this refresh. Check the snapshot against the intended audit before use.']}
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'remaining':len(rows),'newly_covered_km2':report['newly_covered_m2']/1e6,'top':[{'id':r['object_id'],'previous_rank':r['previous_rank'],'km2':r['envelope_uncovered_county_m2']/1e6,'attributes':r['source_attributes']} for r in rows[:10]]},indent=2))
if __name__=='__main__':run()
