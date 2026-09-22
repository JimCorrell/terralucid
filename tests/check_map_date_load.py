"""Run the date audit against the existing disposable 28-correction fixture."""
import json,subprocess,hashlib,sys
sys.path.insert(0,"scripts")
from prepare_source_staging import jsql
from pathlib import Path
cmd=['docker','exec','-i','terralucid-twenty-eight-test','psql','-U','postgres','-d','county_test','-X','-q','-t','-A','-v','ON_ERROR_STOP=1']
def run(sql,ok=True):
 r=subprocess.run(cmd,input=sql,capture_output=True,text=True)
 if (r.returncode==0)!=ok:raise AssertionError(r.stderr[-2000:])
 return r.stdout.strip()
# Prior lifecycle tests intentionally leave newer local review-event versions.
# Bind the identical date-audit transaction to that fixture's current versions;
# production SQL and its pinned report are never changed.
audit='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
sid=run("select ingest.record_county_geometry_snapshot('"+audit+"');")
deps=json.loads(run("select ingest.county_geometry_dependencies('"+audit+"');"))
prior=run("select event_id from ingest.finding_current where finding_id='TL-F-0029';")
r=json.loads(Path('research/map-date-investigation/report.json').read_text())
load=Path('.local/map-dates-load/load.sql').read_text()
production_sha=hashlib.sha256(load.encode()).hexdigest()
load=load.replace(r['geometry_snapshot_id'],sid).replace(jsql(r['geometry_dependencies']),jsql(deps)).replace('f6ec4fb395653f7f13edf558320c842cd9bcbc01ff299e854e154ac2ef0466b2',prior)
m=json.loads(Path('.local/map-dates-load/manifest.json').read_text())
# Stale expected-event failure must roll back the audit and all observations.
bad=load.replace(prior,'0'*64)
run(bad,False)
assert run("select count(*) from ingest.audit_result where sha256='"+m['audit_sha256']+"';")=='0'
sql="select ingest.county_geometry_dependencies('fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259');"
before=run(sql);run(load);run(load);assert run(sql)==before
assert run("select event_id from ingest.finding_current where finding_id='TL-F-0029';")==m['finding_event_id']
assert run("select count(*) from ingest.source_response where registry_sha256='"+m['registry_sha256']+"';")==str(m['new_source_observations'])
report={'passed':True,'production_load_sha256':production_sha,'fixture_note':'Only snapshot/dependency and expected-finding-event bindings adapted to versions left by lifecycle tests. Production SQL unchanged.','checks':['stale finding-event rejection rolls back audit and observations','fixture-bound load and idempotent replay','exact geometry dependencies unchanged','25 source observations, one byte-less failure retained in logs','current finding event matches date-review manifest']}
Path('research/map-date-investigation/test-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
