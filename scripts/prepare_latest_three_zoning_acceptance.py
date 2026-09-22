#!/usr/bin/env python3
"""Prepare three additional reviewed county acceptances, preserving all original records."""
import argparse,csv,json
from pathlib import Path
from prepare_source_staging import ROOT,digest,canonical,literal,jsql,BUCKET

BASE=ROOT/'research/latest-three-zoning-acceptance'
COUNTY='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
PROPOSAL='33259813dfcc2b5fa814d0f49547df52c71e5bab9f3a5e3de1e60106efe86673'
REVIEW='33259813dfcc2b5fa814d0f49547df52c71e5bab9f3a5e3de1e60106efe86673'
MIGRATION='supabase/migrations/20260922020000_latest_three_zoning_acceptance.sql'

def prepare(output,transfer):
    proposal_path=ROOT/'research/latest-three-zoning-priorities/report.json';review_path=ROOT/'research/latest-three-zoning-priorities/report.json'
    if digest(proposal_path.read_bytes())!=PROPOSAL or digest(review_path.read_bytes())!=REVIEW:raise ValueError('Changed reviewed audit')
    p=json.loads(proposal_path.read_bytes());baseline=json.loads((BASE/'baseline.json').read_bytes());
    if baseline['snapshot']['needs_revisit'] or baseline['snapshot']['snapshot_id']!=p['geometry_snapshot_id'] or baseline['snapshot']['dependencies']!=p['geometry_dependencies']:raise ValueError('Changed effective baseline')
    review=json.loads(review_path.read_bytes());cases=[c for c in p['cases'] if c['status']=='proposed_not_accepted'];ids={c['object_id'] for c in cases}
    if ids!={27233351,27314083,27316137} or len(cases)!=3:raise ValueError('Wrong acceptance cohort')
    proof=json.loads((ROOT/'research/piscataquis-ingestion/transport-verification.json').read_bytes())
    import hashlib
    h=hashlib.sha256()
    with transfer.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    if h.hexdigest()!=proof['copy_sql_sha256']:raise ValueError('Changed original county transfer')
    originals={};csv.field_size_limit(100_000_000)
    with transfer.open() as f:
        for line in f:
            if not line.startswith(COUNTY+',lupc-zoning,'):continue
            oid=int(line.split(',',3)[2])
            if oid in ids:
                row=next(csv.reader([line]));originals[oid]=row[3]
    if set(originals)!=ids:raise ValueError('Missing exact serialized county inputs')
    rows=[];objects={}
    def archive(b):
        sha=digest(b);key='sha256/'+sha+'.response';objects[key]=b;return sha,key
    inputs={}
    for path in [proposal_path,review_path,ROOT/MIGRATION,Path(__file__),ROOT/'research/piscataquis-ingestion/transport-verification.json',BASE/'baseline.json']:
        inputs[path.relative_to(ROOT).as_posix()]=archive(path.read_bytes())[0]
    for c in cases:
        candidate=(ROOT/c['candidate_path']).read_bytes();source=json.loads(originals[c['object_id']]);sf=canonical(source['raw_feature'])
        rc=next(r for r in review['cases'] if r['object_id']==c['object_id'])
        if digest(candidate)!=c['candidate_sha256'] or rc['candidate_sha256']!=c['candidate_sha256'] or digest(sf.encode())!=rc['source_feature_sha256'] or source['hold'] is None:raise ValueError('Candidate/source mismatch')
        archive(candidate);source_input_sha=digest(originals[c['object_id']].encode());archive(originals[c['object_id']].encode())
        correction=digest(f"{COUNTY}:lupc-zoning:{c['object_id']}:{c['candidate_sha256']}".encode())
        event={'event_id':digest((correction+':initial-acceptance').encode()),'correction_id':correction,'status':'accepted','actor':'TerraLucid county correction activation','note':'Accept the independently reviewed exact-version DERIVED representation; preserve original source, legal unknowns and other qualification holds.'}
        rows.append({'correction_id':correction,'object_id':c['object_id'],'source_input_sha256':source_input_sha,'source_feature_sha256':digest(sf.encode()),'candidate_sha256':c['candidate_sha256'],'acceptance':event})
    report={'evidence_state':'DERIVED','method':'scripts/prepare_latest_three_zoning_acceptance.py','method_sha256':digest(Path(__file__).read_bytes()),'source_audit_sha256':COUNTY,'proposal_audit_sha256':PROPOSAL,'review_audit_sha256':REVIEW,'inputs':inputs,'baseline_snapshot_id':baseline['snapshot']['snapshot_id'],'corrections':rows,'expected_original_zoning_holds':162,'expected_effective_zoning_holds':148,'expected_original_total_holds':183,'expected_effective_total_holds':169,'qualified_for_parcel_screening':False,'limits':['Geometry interpretations only, not legal zoning or surveyed boundaries.','Other county holds, municipal applicability, parcel identity and wetland age remain unresolved. T1 R11 index amendment date 2005-08-18 versus PDF ZP770 effective 2018-04-26 remains open; geometry acceptance does not resolve legal currency.','Three additional exact versions only; preserve the prior eleven corrections. New captures require new review.']}
    BASE.mkdir(exist_ok=True);raw=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();(BASE/'report.json').write_bytes(raw);audit,key=archive(raw)
    registry_path=ROOT/'research/piscataquis-zoning-holds/registry.json';registry,_=archive(registry_path.read_bytes())
    plan=json.loads((BASE/'finding-review.json').read_bytes());archive((BASE/'finding-review.json').read_bytes())
    sql=['BEGIN;','SET LOCAL TRANSACTION ISOLATION LEVEL READ COMMITTED;','SET LOCAL standard_conforming_strings = on;']
    # Initial activation requires the reviewed baseline under the writer lock.
    # Historical full replays bypass only this baseline check, then immutable
    # correction/event validators verify every exact payload without reactivating.
    sql.append("DO $$ BEGIN PERFORM 1 FROM ingest.county_inventory_batch WHERE audit_sha256="+literal(COUNTY)+" FOR UPDATE; END $$;")
    sql.append("DO $$ DECLARE n integer; BEGIN SELECT count(*) INTO n FROM ingest.county_geometry_correction WHERE source_audit_sha256="+literal(COUNTY)+" AND object_id IN (27233351,27314083,27316137); IF n=0 THEN IF NOT ingest.county_geometry_snapshot_is_current("+literal(baseline['snapshot']['snapshot_id'])+","+literal(COUNTY)+") THEN RAISE EXCEPTION 'Acceptance baseline changed'; END IF; ELSIF n<>3 OR NOT EXISTS(SELECT 1 FROM ingest.audit_result WHERE sha256="+literal(audit)+") THEN RAISE EXCEPTION 'Partial acceptance requires review'; END IF; END $$;")
    sql.append('INSERT INTO ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join([literal(audit),literal(registry),literal('DERIVED'),literal(report['method']),literal(report['method_sha256']),jsql(report),literal(BUCKET),literal(key)])+') ON CONFLICT DO NOTHING;')
    for r in rows:
        c=next(c for c in cases if c['object_id']==r['object_id']);sf=canonical(json.loads(originals[r['object_id']])['raw_feature']);candidate=(ROOT/c['candidate_path']).read_text()
        sql.append('INSERT INTO ingest.county_geometry_correction(correction_id,source_audit_sha256,source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state) VALUES ('+','.join([literal(r['correction_id']),literal(COUNTY),literal('lupc-zoning'),str(r['object_id']),literal(r['source_input_sha256']),literal(sf),literal(PROPOSAL),literal(REVIEW),literal(candidate),literal(r['candidate_sha256']),literal('DERIVED')])+') ON CONFLICT DO NOTHING;')
        sql.append('SELECT ingest.record_county_geometry_event('+jsql(r['acceptance'])+',NULL);')
    sql.append('SELECT ingest.record_county_geometry_snapshot('+literal(COUNTY)+');')
    sql.append('INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(digest((audit+':TL-F-0029').encode())),literal('TL-F-0029'),literal(audit),jsql({'report_pointer':'/corrections','note':'Three additional exact-version acceptances; original holds retained, other county qualification remains open.'})])+') ON CONFLICT DO NOTHING;')
    event={k:v for k,v in plan.items() if k!='expected_event_id'};event['event_id']=digest(canonical([audit,event]).encode());event['evidence_refs']=['audit:'+audit+'#/corrections']
    sql.append('SELECT ingest.record_finding_event('+jsql(event)+','+literal(plan['expected_event_id'])+');');sql.append('COMMIT;')
    output.mkdir(exist_ok=False,parents=True)
    for key,b in objects.items():
        target=output/'objects'/key;target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(b)
    manifest={'bucket':BUCKET,'registry_sha256':registry,'audit_sha256':audit,'finding_event_id':event['event_id'],'objects':{key:{'sha256':digest(b),'bytes':len(b)} for key,b in sorted(objects.items())}}
    (output/'load.sql').write_text('\n'.join(sql)+'\n');(output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');(BASE/'archive-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'audit_sha256':audit,'objects':len(objects),'corrections':len(rows)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--county-transfer',required=True,type=Path);a=p.parse_args();prepare(a.output,a.county_transfer)
