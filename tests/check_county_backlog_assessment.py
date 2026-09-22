#!/usr/bin/env python3
"""Check cohort completeness and selected scenario gains with sequential overlays."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import shapely
from shapely.geometry import shape
from prepare_source_staging import ROOT,canonical,digest
from investigate_moosehead_spencer import propose
BASE=ROOT/'research/county-backlog-assessment'

def run():
    report=json.loads((BASE/'report.json').read_text());parcel=json.loads((BASE/'parcel-holds.json').read_text())
    for doc in [report,parcel]:
        assert digest((ROOT/doc['method']).read_bytes())==doc['method_sha256']
        for p,h in doc['inputs'].items():assert digest((ROOT/p).read_bytes())==h,p
    ranking=json.loads((ROOT/'research/seventeen-correction-ranking/report.json').read_text())
    assert len(report['cases'])==145 and {r['object_id'] for r in report['cases']}=={r['object_id'] for r in ranking['ranking']}
    assert len(parcel['cases'])==21 and len({(r['source'],r['object_id']) for r in parcel['cases']})==21
    live=json.loads((BASE/'live-baseline.json').read_text())['rows'][0]['verification']
    assert live['ranking_snapshot_current'] and live['county_fingerprints_unchanged']
    assert len(live['accepted'])==17 and live['effective_zoning_holds']==145 and live['effective_total_holds']==166
    curves=report['summary']['scenario_curve'];values=[r['union_scenario_gain_m2'] for r in curves]
    assert values==sorted(values) and values[-1]<=report['summary']['union_envelope_upper_bound_m2']+.01
    for r in curves:
        individual=sum(c['scenario_gain_m2'] for c in report['cases'] if c['object_id'] in r['object_ids'])
        assert r['union_scenario_gain_m2']<=individual+.01
    gap=shapely.from_wkb((ROOT/'.local/piscataquis-held-zoning-gap.wkb').read_bytes())
    accepted=[shape(json.loads((ROOT/p).read_text())['geometry']) for p in ranking['inputs'] if '/candidates/' in p]
    ids=set(report['scenario_priority_ids'][:3]);features={}
    for p in report['inputs']:
        if 'lupc-zoning-page-' in p:
            for f in json.loads((ROOT/p).read_text())['features']:
                if f['attributes']['OBJECTID'] in ids:features[f['attributes']['OBJECTID']]=f
    direct=[]
    for oid in sorted(ids):
        g,_=propose(features[oid]['geometry']['rings']);g=g.intersection(gap)
        for a in accepted:g=g.difference(a)
        row=next(c for c in report['cases'] if c['object_id']==oid)
        difference=abs(g.area-row['scenario_gain_m2']);assert difference<.01
        direct.append({'object_id':oid,'sequential_overlay_difference_m2':difference})
    out={'passed':True,'report_sha256':digest((BASE/'report.json').read_bytes()),'parcel_report_sha256':digest((BASE/'parcel-holds.json').read_bytes()),'test_method_sha256':digest(Path(__file__).read_bytes()),'checks':['All pinned inputs/methods unchanged','145 zoning and 21 parcel cases uniquely accounted for','Live PR44 baseline current at recorded verification time','Scenario unions monotonic and bounded by summed individual gains and envelope union','Top three scenario gains agree with sequential full-geometry subtraction within 0.01 m²'],'direct_checks':direct}
    (BASE/'test-results.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':run()
