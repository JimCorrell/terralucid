#!/usr/bin/env python3
"""Archive the ranking and append TL-F-0029 only while its snapshot is current."""
import argparse,json
from pathlib import Path
from prepare_source_staging import ROOT,digest,canonical,literal,jsql,BUCKET
from refresh_twenty_eight_correction_ranking import BASE,AUDIT,OLD_SHA
from prepare_county_ranking_refresh import snapshot_guard

def stage(output):
    raw=(BASE/'report.json').read_bytes();r=json.loads(raw);audit=digest(raw)
    if r['source_audit_sha256']!=AUDIT or r['historical_ranking_sha256']!=OLD_SHA:raise ValueError('Changed source')
    if digest((ROOT/r['method']).read_bytes())!=r['method_sha256']:raise ValueError('Changed method')
    plan=json.loads((BASE/'finding-review.json').read_bytes());objects={}
    def archive(b):
        key='sha256/'+digest(b)+'.response';objects[key]=b;return key
    report_key=archive(raw)
    for path,sha in r['inputs'].items():
        b=(ROOT/path).read_bytes()
        if digest(b)!=sha:raise ValueError('Changed input '+path)
        archive(b)
    registry=ROOT/'research/piscataquis-zoning-holds'
    for p in [ROOT/r['method'],Path(__file__),BASE/'finding-review.json',BASE/'test-results.json',ROOT/'tests/test_twenty_eight_correction_ranking.py',ROOT/'tests/test_county_ranking_refresh.py',ROOT/'tests/check_twenty_eight_ranking_direct.py',ROOT/'scripts/prepare_county_ranking_refresh.py',registry/'registry.json']:archive(p.read_bytes())
    registry_sha=digest((registry/'registry.json').read_bytes())
    if registry_sha!=json.loads((registry/'archive-manifest.json').read_bytes())['registry_sha256']:raise ValueError('Changed registry')
    sql=['BEGIN;','SET LOCAL TRANSACTION ISOLATION LEVEL READ COMMITTED;','SET LOCAL standard_conforming_strings = on;']+snapshot_guard(r)
    sql.append('INSERT INTO ingest.audit_result (sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join([literal(audit),literal(registry_sha),literal('DERIVED'),literal(r['method']),literal(r['method_sha256']),jsql(r),literal(BUCKET),literal(report_key)])+') ON CONFLICT DO NOTHING;')
    sql.append('INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(digest(canonical([audit,'TL-F-0029']).encode())),literal('TL-F-0029'),literal(audit),jsql({'report_pointer':'/ranking','geometry_snapshot_id':r['geometry_snapshot_id'],'remaining_zoning_holds':r['effective_held_zoning_rows']})])+') ON CONFLICT DO NOTHING;')
    event={k:v for k,v in plan.items() if k!='expected_event_id'};event['event_id']=digest(canonical([audit,event]).encode());event['evidence_refs']=['audit:'+audit+'#/ranking','audit:'+audit+'#/geometry_dependencies']
    sql.append('SELECT ingest.record_finding_event('+jsql(event)+','+literal(plan['expected_event_id'])+');');sql.append('COMMIT;')
    output.mkdir(parents=True,exist_ok=False)
    for key,b in objects.items():
        p=output/'objects'/key;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(b)
    manifest={'bucket':BUCKET,'registry_sha256':registry_sha,'audit_sha256':audit,'finding_event_id':event['event_id'],'reuses_existing_source_observations':True,'new_source_observations':0,'objects':{key:{'sha256':digest(b),'bytes':len(b)} for key,b in sorted(objects.items())}}
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');(output/'load.sql').write_text('\n'.join(sql)+'\n');(BASE/'archive-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'audit_sha256':audit,'finding_event_id':event['event_id'],'objects':len(objects),'bytes':sum(len(b) for b in objects.values())}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);stage(p.parse_args().output)
