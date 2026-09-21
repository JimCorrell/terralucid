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
run(load);run(load);check(run('SELECT count(*) FROM ingest.county_geometry_event')=='3','exact replay duplicated events');checks.append('authentic activation and full load replay')
run(Path('tests/county_geometry_corrections.sql').read_text());checks.append('withdrawal, reacceptance, immutable history, stale review/snapshot, source/candidate binding, segment multiplicity, privacy, unchanged source counts')
report=json.loads(Path('research/county-corrections/report.json').read_text());c=report['corrections'][0];cid=c['correction_id'];eid=c['acceptance']['event_id'];audit=report['source_audit_sha256']
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
run(load);check(run('SELECT count(*) FROM ingest.county_geometry_event')=='7','historical activation reset history');checks.append('historical full activation replay preserves later events')
result={'checks':checks,'passed':True,'load_sha256':hashlib.sha256(load.encode()).hexdigest(),'test_files':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),Path('tests/county_geometry_corrections.sql')]},'database_version':run('SELECT version();'),'postgis_version':run('SELECT extensions.postgis_full_version();'),'fixture':'120449 original archived county records and proposal/review audit chain; disposable Docker database','snapshot_lock_wait_seconds':round(elapsed,2)}
a.report.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,indent=2))
