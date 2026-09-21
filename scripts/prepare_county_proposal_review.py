#!/usr/bin/env python3
"""Archive an exact-version review against its existing registry; append findings only."""
import argparse,json
from pathlib import Path
from prepare_source_staging import ROOT,digest,canonical,literal,jsql,BUCKET
from review_county_zoning_proposals import BASE,PARENT,PARENT_SHA


def stage(output):
    raw=(BASE/'report.json').read_bytes();r=json.loads(raw);audit=digest(raw)
    plan=json.loads((BASE/'finding-review.json').read_bytes())
    if r['proposal_audit_sha256']!=PARENT_SHA or digest((PARENT/'report.json').read_bytes())!=PARENT_SHA:raise ValueError('Changed proposal audit')
    if digest((ROOT/r['method']).read_bytes())!=r['method_sha256']:raise ValueError('Changed review method')
    objects={}
    def archive(data):
        sha=digest(data);key='sha256/'+sha+'.response';objects[key]=data;return key
    report_key=archive(raw)
    for path,sha in r['inputs'].items():
        b=(ROOT/path).read_bytes()
        if digest(b)!=sha:raise ValueError('Changed input: '+path)
        archive(b)
    for p in [ROOT/r['method'],Path(__file__),BASE/'finding-review.json',ROOT/'tests/test_county_zoning_review.py',PARENT/'registry.json']:archive(p.read_bytes())
    registry_sha=digest((PARENT/'registry.json').read_bytes())
    if registry_sha!=json.loads((PARENT/'archive-manifest.json').read_bytes())['registry_sha256']:raise ValueError('Changed registry')
    sql=['BEGIN;','SET LOCAL standard_conforming_strings = on;']
    sql.append('INSERT INTO ingest.audit_result (sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join([literal(audit),literal(registry_sha),literal('DERIVED'),literal(r['method']),literal(r['method_sha256']),jsql(r),literal(BUCKET),literal(report_key)])+') ON CONFLICT DO NOTHING;')
    sql.append('INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(digest(canonical([audit,'TL-F-0029']).encode())),literal('TL-F-0029'),literal(audit),jsql({'report_pointer':'/cases','proposal_audit_sha256':PARENT_SHA,'scope':'Independent review supports three exact-version proposals; activation pending'})])+') ON CONFLICT DO NOTHING;')
    event={k:v for k,v in plan.items() if k!='expected_event_id'};event['event_id']=digest(canonical([audit,event]).encode());event['evidence_refs']=['audit:'+audit+'#/cases','audit:'+audit+'#/review_conclusion']
    sql.append('SELECT ingest.record_finding_event('+jsql(event)+','+literal(plan['expected_event_id'])+');');sql.append('COMMIT;')
    output.mkdir(parents=True,exist_ok=False)
    for key,b in objects.items():
        p=output/'objects'/key;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(b)
    manifest={'bucket':BUCKET,'registry_sha256':registry_sha,'audit_sha256':audit,'finding_event_id':event['event_id'],'reuses_existing_source_observations':True,'new_source_observations':0,'objects':{key:{'sha256':digest(b),'bytes':len(b)} for key,b in sorted(objects.items())}}
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');(output/'load.sql').write_text('\n'.join(sql)+'\n');(BASE/'archive-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'audit_sha256':audit,'finding_event_id':event['event_id'],'objects':len(objects)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);stage(p.parse_args().output)
