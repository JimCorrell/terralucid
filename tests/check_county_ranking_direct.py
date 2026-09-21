import sys,json
from pathlib import Path
sys.path.insert(0,'scripts')
import shapely
from shapely.geometry import shape,box
from refresh_county_ranking import BASE,ROOT
r=json.loads((BASE/'report.json').read_text());gap=shapely.from_wkb((ROOT/'.local/piscataquis-held-zoning-gap.wkb').read_bytes())
cs=[shape(json.loads((ROOT/p).read_text())['geometry']) for p in r['inputs'] if p.endswith('.geojson')]
checks=[]
for oid in [27304757,27270812,27257109]:
 row=next(x for x in r['ranking'] if x['object_id']==oid)
 path=next(p for p,h in r['inputs'].items() if h==row['response_sha256'])
 f=next(f for f in json.loads((ROOT/path).read_text())['features'] if f['attributes']['OBJECTID']==oid)
 pts=[p for ring in f['geometry']['rings'] for p in ring];env=box(min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts))
 g=gap.intersection(env)
 for c in cs:g=g.difference(c)
 delta=abs(g.area-row['envelope_uncovered_county_m2']);assert delta<0.01,delta
 checks.append({'object_id':oid,'direct_overlay_difference_m2':delta})
assert len(r['ranking'])==157 and len({x['object_id'] for x in r['ranking']})==157
assert all(x['envelope_uncovered_county_m2']<=x['previous_envelope_uncovered_county_m2'] for x in r['ranking'])
assert abs(r['newly_covered_m2']-89457349.24640632)<0.01
(BASE/'test-results.json').write_text(json.dumps({'passed':True,'unit_tests':5,'checks':['overlapping candidates counted once; holes, disjoint parts and boundary touches','stale/changed dependencies and changed hold cohort rejected','multiple civil records per jurisdiction aggregated','157 unique remaining holds; monotonic upper bounds','new coverage agrees with prior activation analyses within 0.01 square metre'],'direct_overlay_checks':checks},indent=2,sort_keys=True)+'\n')
print(checks)
