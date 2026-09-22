#!/usr/bin/env python3
"""Stage source observations, three proposals and a finding review; never activate."""
import argparse,json
from pathlib import Path
from prepare_source_staging import ROOT,digest,canonical,literal,jsql,BUCKET
from prepare_county_ranking_refresh import snapshot_guard
from investigate_big_moose_t2_barnard import BASE,AUDIT,RANKING_SHA,IDS

def stage(output):
    raw=(BASE/'report.json').read_bytes();r=json.loads(raw);audit=digest(raw)
    if r['source_audit_sha256']!=AUDIT or r['ranking_audit_sha256']!=RANKING_SHA or [c['object_id'] for c in r['cases']]!=IDS:raise ValueError('Changed scope')
    if digest((ROOT/r['method']).read_bytes())!=r['method_sha256']:raise ValueError('Changed method')
    plan=json.loads((BASE/'finding-review.json').read_bytes());objects={}
    def archive(b):
        key='sha256/'+digest(b)+'.response';objects[key]=b;return key
    report_key=archive(raw)
    for path,sha in r['inputs'].items():
        b=(ROOT/path).read_bytes()
        if digest(b)!=sha:raise ValueError('Changed input '+path)
        archive(b)
    for p in [ROOT/r['method'],Path(__file__),ROOT/'scripts/prepare_county_ranking_refresh.py',BASE/'finding-review.json',BASE/'test-results.json',ROOT/'tests/test_big_moose_t2_barnard.py',ROOT/'tests/test_moosehead_spencer.py',ROOT/'tests/test_moosehead_spencer_review.py']:archive(p.read_bytes())
    registry_raw=(BASE/'registry.json').read_bytes();registry=json.loads(registry_raw);registry_sha=digest(registry_raw);registry_key=archive(registry_raw)
    probes={p:[s['id'] for s in registry['sources'] if p in s['probe_ids']] for source in registry['sources'] for p in source['probe_ids']}
    sql=['BEGIN;','SET LOCAL TRANSACTION ISOLATION LEVEL READ COMMITTED;','SET LOCAL standard_conforming_strings = on;']+snapshot_guard(r)
    sql.append('INSERT INTO ingest.registry_snapshot(sha256,byte_count,document,storage_bucket,storage_object) VALUES ('+','.join([literal(registry_sha),str(len(registry_raw)),jsql(registry),literal(BUCKET),literal(registry_key)])+') ON CONFLICT DO NOTHING;')
    observations=0;failed=0;expected={}
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for e in json.loads(log.read_bytes()):
            key=log.parent.name+'/'+e['id'];expected[key]=dict(e)
            if 'response_file' not in e:
                # A failed request without response bytes is preserved in the
                # archived retrieval log, not invented as a source_response row.
                failed+=1;continue
            if Path(e['response_file']).name!=e['response_file'] or e['id'] not in probes:raise ValueError('Unsafe/unmapped response')
            p=log.parent/e['response_file'];b=p.read_bytes();sha=digest(b)
            if sha!=e['sha256'] or len(b)!=e['bytes'] or e['http_status']!=200:raise ValueError('Changed response')
            expected[key]['response_path']=p.relative_to(ROOT).as_posix()
            run_path=log.parent.relative_to(BASE).as_posix();observation=digest(canonical([registry_sha,run_path,e]).encode())
            values=[literal(observation),literal(registry_sha),literal(run_path),literal(e['id']),'ARRAY['+','.join(map(literal,probes[e['id']]))+']::text[]',literal(e['retrieved_at']),str(e['http_status']),literal(e['status']),jsql(e),literal(sha),str(len(b)),literal(BUCKET),literal(archive(b))]
            sql.append('INSERT INTO ingest.source_response(observation_sha256,registry_sha256,run_path,probe_id,source_ids,retrieved_at,http_status,outcome,retrieval_log,payload_sha256,byte_count,storage_bucket,storage_object) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;');observations+=1
    if expected!=r['evidence']:raise ValueError('Evidence/log mismatch')
    sql.append('INSERT INTO ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join([literal(audit),literal(registry_sha),literal('DERIVED'),literal(r['method']),literal(r['method_sha256']),jsql(r),literal(BUCKET),literal(report_key)])+') ON CONFLICT DO NOTHING;')
    sql.append('INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(digest(canonical([audit,'TL-F-0029']).encode())),literal('TL-F-0029'),literal(audit),jsql({'report_pointer':'/cases','scope':'Three source-preserving proposals and separate cycle/fill checks; no activation','geometry_snapshot_id':r['geometry_snapshot_id']})])+') ON CONFLICT DO NOTHING;')
    event={k:v for k,v in plan.items() if k!='expected_event_id'};event['event_id']=digest(canonical([audit,event]).encode());event['evidence_refs']=['audit:'+audit+'#/cases','audit:'+audit+'#/review_conclusion']
    sql.append('SELECT ingest.record_finding_event('+jsql(event)+','+literal(plan['expected_event_id'])+');');sql.append('COMMIT;')
    output.mkdir(parents=True,exist_ok=False)
    for key,b in objects.items():
        p=output/'objects'/key;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(b)
    manifest={'bucket':BUCKET,'registry_sha256':registry_sha,'audit_sha256':audit,'finding_event_id':event['event_id'],'new_source_observations':observations,'failed_requests_preserved_in_logs':failed,'objects':{key:{'sha256':digest(b),'bytes':len(b)} for key,b in sorted(objects.items())}}
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');(output/'load.sql').write_text('\n'.join(sql)+'\n');(BASE/'archive-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='objects'}|{'objects':len(objects),'bytes':sum(len(b) for b in objects.values())}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);stage(p.parse_args().output)
