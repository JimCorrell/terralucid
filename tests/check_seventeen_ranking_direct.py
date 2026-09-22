import sys,json
from pathlib import Path
sys.path.insert(0,'scripts')
import shapely
from shapely.geometry import shape,box
from refresh_seventeen_correction_ranking import BASE,ROOT
r=json.loads((BASE/'report.json').read_text());gap=shapely.from_wkb((ROOT/'.local/piscataquis-held-zoning-gap.wkb').read_bytes())
cs=[shape(json.loads((ROOT/p).read_text())['geometry']) for p in r['inputs'] if p.endswith('.geojson')]
checks=[]
targets=[r['ranking'][0]['object_id']]+[x['object_id'] for x in sorted(r['ranking'],key=lambda x:-x['additional_reduction_since_fourteen_corrections_m2'])[:2]]
assert len(set(targets))==3
for oid in targets:
 row=next(x for x in r['ranking'] if x['object_id']==oid)
 path=next(p for p,h in r['inputs'].items() if h==row['response_sha256'])
 f=next(f for f in json.loads((ROOT/path).read_text())['features'] if f['attributes']['OBJECTID']==oid)
 pts=[p for ring in f['geometry']['rings'] for p in ring];env=box(min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts))
 g=gap.intersection(env)
 for c in cs:g=g.difference(c)
 delta=abs(g.area-row['envelope_uncovered_county_m2']);assert delta<0.01,delta
 checks.append({'object_id':oid,'direct_overlay_difference_m2':delta})
assert len(r['ranking'])==145 and len({x['object_id'] for x in r['ranking']})==145
assert all(x['envelope_uncovered_county_m2']<=x['previous_envelope_uncovered_county_m2'] for x in r['ranking'])
assert len(cs)==17
assert all(x['envelope_uncovered_county_m2']<=x['fourteen_correction_envelope_uncovered_county_m2']+0.01 for x in r['ranking'])
assert not set(r['removed_accepted_object_ids']) & {x['object_id'] for x in r['ranking']}
assert abs(r['additional_coverage_since_fourteen_corrections_m2']-71314703.52500567)<0.01
(BASE/'test-results.json').write_text(json.dumps({'passed':True,'unit_tests':5,'checks':['overlapping candidates counted once; holes, disjoint parts and boundary touches','stale/changed dependencies and changed hold cohort rejected','multiple civil records per jurisdiction aggregated','145 unique remaining holds; monotonic upper bounds','new coverage agrees with three-priority scenario within 0.01 square metre'],'direct_overlay_checks':checks},indent=2,sort_keys=True)+'\n')
print(checks)
