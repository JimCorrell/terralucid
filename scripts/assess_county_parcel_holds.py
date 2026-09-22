#!/usr/bin/env python3
"""Inventory archived parcel exceptions without interpreting legal boundaries."""
import json
from collections import Counter
from pathlib import Path
from prepare_source_staging import ROOT,canonical,digest
from investigate_osborn_wetlands import decode
from investigate_moosehead_spencer import propose
from review_moosehead_spencer import review_cycles
from review_county_zoning_proposals import review_geometry
BASE=ROOT/'research/county-backlog-assessment'

def run():
    inputs={}
    def read(p,sha=None):
        raw=(ROOT/p).read_bytes();h=digest(raw)
        if sha and sha!=h:raise ValueError('Changed input '+p)
        inputs[p]=h;return raw
    county=json.loads(read('research/piscataquis-ingestion/report.json','fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'))
    for p in ['scripts/investigate_osborn_wetlands.py','scripts/investigate_moosehead_spencer.py','scripts/investigate_county_zoning_cases.py','scripts/investigate_osborn_zoning.py','scripts/review_moosehead_spencer.py','scripts/review_county_zoning_proposals.py','scripts/prepare_source_staging.py']:read(p)
    rows=[];counts={}
    for source in ['ut-parcels','organized-parcels']:
        seen={}
        for key,e in county['evidence'].items():
            if not key.startswith('capture/'+source+'-page-'):continue
            page=json.loads(read('research/piscataquis-ingestion/'+e['response_path'],e['sha256']))
            for f in page['features']:
                oid=f['attributes']['OBJECTID'];sha=digest(canonical(f).encode())
                if oid in seen:
                    if seen[oid]!=sha:raise ValueError('Conflicting repeat')
                    continue
                seen[oid]=sha
                g,hold=decode(f['geometry']['rings'])
                if not hold:continue
                row={'source':source,'object_id':oid,'source_feature_sha256':sha,'response_sha256':e['sha256'],'hold':hold,'ring_count':len(f['geometry']['rings']),'coordinate_count':sum(map(len,f['geometry']['rings'])),'status':'requires_new_method_or_source_evidence'}
                try:
                    candidate,d=propose(f['geometry']['rings']);review_cycles(f['geometry']['rings'],candidate);review_geometry(f['geometry']['rings'],candidate)
                    row.update(status='archived_geometry_checks_pass_only',split_types=dict(Counter(s['type'] for s in d['splits'])),nested_hole_assignments=len(d['assembly']['nested_hole_assignments']))
                except ValueError as ex:row['reason']=str(ex)
                rows.append(row)
        counts[source]=len(seen)
        assert counts[source]==county['summary'][source]['captured_records']
        assert sum(r['source']==source for r in rows)==county['summary'][source]['scope_relations']['held']
    report={'evidence_state':'DERIVED','status':'assessment_only_not_proposals','method':'scripts/assess_county_parcel_holds.py','method_sha256':digest(Path(__file__).read_bytes()),'inputs':inputs,'scanned_source_records':counts,'counts':dict(Counter(r['status'] for r in rows)),'cases':rows,'limits':['21 holds are in the broader capture, not proven county-interior legal parcels.','Computational reuse of zoning methods does not authorize parcel correction. No candidates saved, source/map/title review completed, or holds cleared.','Assessment geometry is not a legal boundary; source identities remain separate.']}
    (BASE/'parcel-holds.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(report['counts'])
if __name__=='__main__':run()
