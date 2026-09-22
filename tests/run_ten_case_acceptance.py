#!/usr/bin/env python3
"""Integration test against a DISPOSABLE Docker database with archived county/review fixtures.
No network/Supabase connection is made. Pass container, database and prepared load path.
"""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--container',required=True);p.add_argument('--database',required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
cmd=['docker','exec','-i',a.container,'psql','-X','-q','-t','-A','-U','postgres','-d',a.database,'-v','ON_ERROR_STOP=1']
def run(sql):
 r=subprocess.run(cmd,input=sql,text=True,capture_output=True)
 if r.returncode:raise RuntimeError(r.stderr[-2000:])
 return r.stdout.strip()
def check(ok,msg):
 if not ok:raise AssertionError(msg)
checks=[]
load=(a.prepared/'load.sql').read_text()
old_state_sql="SELECT json_agg(t ORDER BY object_id) FROM (SELECT object_id,correction_id,candidate_sha256,geometry_event_id,encode(sha256(extensions.ST_AsEWKB(geometry)),'hex'),'accepted'=correction_status accepted FROM ingest.county_geometry_current WHERE object_id IN (27334504,27249007,27291625,27208875,27336229,27304757,27270812,27207268,27224591,27320676,27243652,27233351,27314083,27316137,27257109,27321193,27303187))t;"

# Fresh inserts exercise validation rather than the historical-replay fast path.
import sys,copy,re
sys.path.insert(0,'scripts')
from prepare_source_staging import literal,canonical
proposal=json.loads(Path('research/ten-case-zoning-review/report.json').read_text())
activation=json.loads(Path('research/ten-case-acceptance/report.json').read_text())
proposal_sha=activation['proposal_audit_sha256']
statements=re.findall(r'INSERT INTO ingest\.county_geometry_correction\(.*?\) ON CONFLICT DO NOTHING;',load,re.S)
check(len(statements)==11,'wrong insert cohort')
def rejects(statement,fragment,setup=''):
 result=subprocess.run(cmd,input='BEGIN;'+setup+statement+'ROLLBACK;',text=True,capture_output=True)
 check(result.returncode!=0 and fragment in result.stderr,'expected rejection '+fragment+': '+result.stderr[-400:])
for statement in statements:rejects(statement,'Outside reviewed county cohort')
checks.append('previous validator rejects all eleven new exact versions')
run(Path('supabase/migrations/20260922040000_ten_case_acceptance.sql').read_text())
# Initial publication must reject a changed baseline, and failure is atomic.
old_correction=run('SELECT correction_id FROM ingest.county_geometry_current ORDER BY object_id LIMIT 1;')
old_event=run("SELECT geometry_event_id FROM ingest.county_geometry_current WHERE correction_id='"+old_correction+"';")
withdraw="SELECT ingest.record_county_geometry_event(jsonb_build_object('event_id',repeat('7',64),'correction_id','"+old_correction+"','status','withdrawn','actor','disposable test','note','baseline guard'),'"+old_event+"');"
# Strip the prepared transaction wrapper so the temporary withdrawal rolls back
# with the failed activation; do not affect the fixture's subsequent baseline.
rejects(load.replace('BEGIN;','',1).rsplit('COMMIT;',1)[0],'Acceptance baseline changed',withdraw)
check(run('SELECT count(*) FROM ingest.county_geometry_correction')=='17','failed baseline load leaked writes')
checks.append('changed initial baseline rejected atomically')
for i,(statement,c) in enumerate(zip(statements,activation['corrections'])):
    case=next(x for x in proposal['cases'] if x['object_id']==c['object_id'])
    run('BEGIN;'+statement+'ROLLBACK;')
    for path,value,fragment in [
        (f'cases,{i},cycle_review,source_cycle_roles_preserved','false','Missing reviewed cycle roles'),
        (f'cases,{i},independent_fill_check,equals_independent_even_odd_fill','false','differs from exact reviewed'),
        (f'cases,{i},independent_fill_check,all_segments_preserved_with_multiplicity','false','differs from exact reviewed'),
        (f'cases,{i},independent_fill_check,symmetric_difference_m2','1','differs from exact reviewed'),
        (f'cases,{i},recommendation','"unsupported"','differs from exact reviewed'),
        ('source_audit_sha256','"wrong-source"','differs from exact reviewed')]:
        setup="UPDATE ingest.audit_result SET document=jsonb_set(document,'{"+path+"}',"+literal(value)+"::jsonb) WHERE sha256="+literal(proposal_sha)+";"
        rejects(statement,fragment,setup)
    rejects(statement.replace(literal(c['source_input_sha256']),literal('0'*64),1),'differs from exact reviewed')
    rejects(statement.replace(literal(proposal_sha),literal('0'*64),1),'Outside reviewed county cohort')
    raw=Path(case['candidate_path']).read_text()
    rejects(statement.replace(literal(raw),literal(raw+' '),1),'differs from exact reviewed')
    # Corrupt only disposable audit/candidate fixtures to reach the runtime
    # segment and validity guards after matching their new byte hashes.
    artifact=json.loads(raw)
    for mode,fragment in [('translate','changes source segments'),('empty','Invalid county candidate')]:
        changed=copy.deepcopy(artifact)
        if mode=='empty':changed['geometry']['coordinates']=[]
        else:
            for poly in changed['geometry']['coordinates']:
                for ring in poly:
                    for point in ring:point[0]+=1;point[1]+=1
        changed_raw=json.dumps(changed,sort_keys=True,indent=2)+'\n';sha=hashlib.sha256(changed_raw.encode()).hexdigest()
        cid=hashlib.sha256((activation['source_audit_sha256']+':lupc-zoning:'+str(c['object_id'])+':'+sha).encode()).hexdigest()
        modified=statement.replace(literal(raw),literal(changed_raw),1).replace(literal(c['candidate_sha256']),literal(sha),1).replace(literal(c['correction_id']),literal(cid),1)
        setup="UPDATE ingest.audit_result SET document=jsonb_set(document,'{cases,"+str(i)+",candidate_sha256}',"+literal(json.dumps(sha))+"::jsonb) WHERE sha256="+literal(proposal_sha)+";"
        rejects(modified,fragment,setup)
checks.append('fresh inserts enforce source/audit/candidate binding, cycle/fill evidence, runtime validity and exact segment multiplicity for all eleven cases')

old_state=run(old_state_sql)
old_snapshot=run("SELECT snapshot_id FROM ingest.county_geometry_snapshot_current WHERE NOT needs_revisit;")
check(len(old_snapshot)==64,'expected one current baseline snapshot')
run(load);run(load);check(run('SELECT count(*) FROM ingest.county_geometry_event')=='28','exact replay duplicated events');checks.append('authentic twenty-eight-feature activation and full load replay');check(run(old_state_sql)==old_state,'prior seventeen corrections changed');check(run("SELECT needs_revisit FROM ingest.county_geometry_snapshot_current WHERE snapshot_id='"+old_snapshot+"';")=='t','old snapshot did not become stale');check(run("SELECT count(*) FROM ingest.county_geometry_snapshot_current WHERE NOT needs_revisit")=='1','new snapshot missing');checks.append('prior seventeen approvals unchanged; old snapshot stale and new snapshot current')
check(run("SELECT ingest.county_geometry_snapshot_is_current(document->>'geometry_snapshot_id',document->>'source_audit_sha256') FROM ingest.audit_result WHERE sha256='8b5f2fb7041826aea92ac697489fc8dea3308df3ffffd3384e31ff6e27f5b6e7'")== 'f','old ranking is not stale')

for oid in [27342226,27365331,27364426,27339379,27364538,27324664,27321394,27366878,27261431,27304932,27358396]:run(Path('tests/ten_case_acceptance.sql').read_text().replace('TEST_OBJECT_ID',str(oid)))
checks.append('withdrawal, reacceptance, immutable history, stale review/snapshot, source/candidate binding, segment multiplicity, privacy, unchanged source counts')
report=json.loads(Path('research/ten-case-acceptance/report.json').read_text());c=report['corrections'][0];cid=c['correction_id'];eid=c['acceptance']['event_id'];audit=report['source_audit_sha256']
def event(i,status,expected):
 payload=json.dumps(dict(event_id=i*64,correction_id=cid,status=status,actor='isolated concurrency test',note='disposable fixture only'))
 return "SELECT ingest.record_county_geometry_event('"+payload+"'::jsonb,'"+expected+"');"
# A withdrawal in an uncommitted transaction must block snapshot capture.
first=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
first.stdin.write("BEGIN; SET application_name='county_correction_lock_test';"+event('d','withdrawn',eid)+"SELECT pg_sleep(3);COMMIT;\n");first.stdin.close()
for _ in range(100):
 if run("SELECT count(*) FROM pg_stat_activity WHERE application_name='county_correction_lock_test' AND wait_event='PgSleep'")=='1':break
 time.sleep(.05)
else:raise AssertionError('did not observe transaction holding lock')
start=time.monotonic();sid=run("SELECT ingest.record_county_geometry_snapshot('"+audit+"');");elapsed=time.monotonic()-start
first.wait();check(first.returncode==0,'concurrent writer failed');check(elapsed>1,'snapshot did not wait for writer');check(run("SELECT dependencies->'"+cid+"'->>'status' FROM ingest.county_geometry_snapshot WHERE snapshot_id='"+sid+"'")=="withdrawn",'snapshot missed committed withdrawal');run(event('8','accepted','d'*64));checks.append('snapshot waits for concurrent writer then captures committed withdrawal')
# A concurrent stale review must wait and then fail after a committed newer event.
# Use another disposable transaction and restore status afterwards; originals are untouched.
first=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
first.stdin.write("BEGIN; SET application_name='county_correction_lock_test';"+event('e','withdrawn','8'*64)+"SELECT pg_sleep(3);COMMIT;\n");first.stdin.close()
for _ in range(100):
 if run("SELECT count(*) FROM pg_stat_activity WHERE application_name='county_correction_lock_test' AND wait_event='PgSleep'")=='1':break
 time.sleep(.05)
else:raise AssertionError('did not observe committed-review lock')
r=subprocess.run(cmd,input=event('f','accepted','8'*64),text=True,capture_output=True);first.wait()
check(first.returncode==0 and r.returncode!=0 and 'review changed' in r.stderr,'concurrent stale review was not rejected')
run(event('9','accepted','e'*64));checks.append('concurrent reviews serialize and reject stale expected event')
# Historical prepared activation replay must preserve the subsequent review history.
run(load);check(run('SELECT count(*) FROM ingest.county_geometry_event')=='32','historical activation reset history');checks.append('historical full activation replay preserves later events')
check(run(old_state_sql)==old_state,'new-feature lifecycle changed original approvals')
result={'checks':checks,'passed':True,'load_sha256':hashlib.sha256(load.encode()).hexdigest(),'test_files':{str(f.resolve().relative_to(Path.cwd())):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),Path('tests/ten_case_acceptance.sql')]},'database_version':run('SELECT version();'),'postgis_version':run('SELECT extensions.postgis_full_version();'),'fixture':'120449 original archived county records and proposal/review audit chain; disposable Docker database','snapshot_lock_wait_seconds':round(elapsed,2)}
a.report.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,indent=2))
