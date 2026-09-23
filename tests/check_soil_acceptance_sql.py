"""Isolated full-bundle soil acceptance, withdrawal, dependency and coverage tests."""
import argparse,json,subprocess,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_soil_staging import MIGRATION,check_sql
from prepare_source_staging import literal,jsql,digest
from prepare_soil_acceptance import MIGRATION as ACCEPTANCE_MIGRATION
p=argparse.ArgumentParser();p.add_argument('--deployment',type=Path,required=True);p.add_argument('--proposals',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
meta=json.loads((a.deployment/'deployment.json').read_bytes());name='terralucid-soils-test-'+uuid.uuid4().hex[:8]
def command(args,**kwargs):
 r=subprocess.run(args,capture_output=True,**kwargs)
 if r.returncode:raise RuntimeError(r.stderr[-2000:])
 return r.stdout
base=['docker','exec','-i',name,'psql','-X','-q','-t','-A','-U','postgres','-d','soiltest','-v','ON_ERROR_STOP=1']
def sql(text,fail=False):
 r=subprocess.run(base,input=text,text=True,capture_output=True)
 if fail:
  if r.returncode==0:raise AssertionError('Invalid SQL operation succeeded')
  return
 if r.returncode:raise RuntimeError(r.stderr[-2000:])
 return r.stdout.strip()
checks=[]
try:
 command(['docker','run','-d','--name',name,'--platform','linux/amd64','-e','POSTGRES_HOST_AUTH_METHOD=trust','postgis/postgis:17-3.5'])
 for _ in range(60):
  logs=subprocess.run(['docker','logs',name],capture_output=True,text=True)
  if 'PostgreSQL init process complete' in logs.stdout+logs.stderr and subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],capture_output=True).returncode==0:break
  time.sleep(.5)
 command(['docker','exec',name,'createdb','-U','postgres','-T','template0','soiltest'])
 sql('create schema extensions;create extension postgis with schema extensions;create schema ingest;create role anon;create role authenticated;create role service_role;')
 sql(MIGRATION.read_text());assert json.loads(sql("select to_jsonb(exists(select 1 from ingest.soil_batch));")) is False;print('Migration passed; loading full bundle',flush=True)
 with (a.deployment/'load.sql').open() as source:r=command(base,stdin=source,text=True)
 result=json.loads(r);assert result['records']==meta['records'] and result['row_fingerprint']==meta['row_fingerprint'] and result['geometry_mismatches']==0
 checks.append('full_bundle_fingerprint_geometry_and_count_readback')
 batch=meta['batch']
 pm=json.loads((a.proposals/'preparation.json').read_bytes())
 assert digest(ACCEPTANCE_MIGRATION.read_bytes())==pm['migration_sha256']
 assert digest((a.proposals/'proposals.sql').read_bytes())==pm['proposals_sql_sha256']
 sql(ACCEPTANCE_MIGRATION.read_text())
 snap0=sql("select ingest.record_soil_geometry_snapshot('"+batch+"');")
 proposal_sql=(a.proposals/'proposals.sql').read_text()
 sql(proposal_sql)
 assert sql('select count(*) from ingest.soil_geometry_event;')=='0'
 assert sql('select count(*) from ingest.effective_soil_geometry where effective_geometry_hold is not null;')=='7'
 assert sql("select ingest.soil_geometry_snapshot_is_current('"+snap0+"','"+batch+"');")=='f'
 snap1=sql("select ingest.record_soil_geometry_snapshot('"+batch+"');")
 sql(proposal_sql) # Exact replay, no events.
 assert sql("select ingest.soil_geometry_snapshot_is_current('"+snap1+"','"+batch+"');")=='t'
 checks.append('proposal_load_is_inactive_and_invalidates_prior_dependency_snapshot')
 def event(cid,label,status='accepted',expected=None):
  payload={'event_id':digest(label.encode()),'correction_id':cid,'status':status,'actor':'isolated acceptance test','note':label}
  query='select ingest.record_soil_geometry_event('+jsql(payload)+','+('NULL' if expected is None else literal(expected))+');'
  return payload['event_id'],query
 accepted=[]
 for i,row in enumerate(pm['proposals']):
  eid,q=event(row['correction_id'],'initial '+str(i));sql(q);accepted.append((eid,q))
 assert sql('select count(*) from ingest.effective_soil_geometry where effective_geometry_hold is not null;')=='0'
 assert sql("select count(*) from ingest.effective_soil_geometry where correction_status='accepted' and effective_scope_relation='interior';")=='3'
 assert sql("select count(*) from ingest.effective_soil_geometry where correction_status='accepted' and effective_scope_relation='outside';")=='4'
 assert sql('select count(*) from ingest.soil_record where hold is not null and geometry is null;')=='7'
 assert sql('select count(*) from ingest.effective_soil_geometry where qualified_for_parcel_screening;')=='0'
 snap2=sql("select ingest.record_soil_geometry_snapshot('"+batch+"');")
 assert sql("select ingest.soil_geometry_snapshot_is_current('"+snap1+"','"+batch+"');")=='f'
 checks.append('seven_acceptances_clear_only_effective_holds_recompute_scope_preserve_sources')
 cid=pm['proposals'][3]['correction_id'];eid,initial=accepted[3]
 withdrawn,wq=event(cid,'withdraw','withdrawn',eid);sql(wq)
 assert sql('select count(*) from ingest.effective_soil_geometry where effective_geometry_hold is not null;')=='1'
 assert sql("select ingest.soil_geometry_snapshot_is_current('"+snap2+"','"+batch+"');")=='f'
 sql(initial);sql(proposal_sql) # Historical replay cannot restore acceptance.
 assert sql('select count(*) from ingest.effective_soil_geometry where effective_geometry_hold is not null;')=='1'
 sql(event(cid,'stale',expected=eid)[1],True)
 sql(initial.replace('initial 3','changed note'),True)
 _,reaccept=event(cid,'reaccept',expected=withdrawn);sql(reaccept)
 assert sql("select ingest.soil_geometry_snapshot_is_current('"+snap2+"','"+batch+"');")=='f'
 assert sql("select ingest.soil_geometry_snapshot_is_current('"+snap2+"','"+'0'*64+"');")=='f'
 assert sql("select ingest.soil_geometry_snapshot_is_current('missing','"+batch+"');")=='f'
 checks.append('withdrawal_reacceptance_stale_review_and_historical_replay')
 # Attempt tampering through inserts even with ON CONFLICT DO NOTHING.
 for old,new in [(pm['proposals'][0]['source_input_sha256'],'0'*64),(pm['proposals'][0]['candidate_sha256'],'1'*64),('ddda7a3674c616b1eda8921cdf7581fe58aecfffd6e8c32bbebd49ed8ca6df8a','2'*64),(batch,'3'*64)]:
  sql(proposal_sql.replace(old,new),True)
 for table in ['soil_geometry_study','soil_geometry_correction','soil_geometry_event','soil_geometry_snapshot']:
  sql('delete from ingest.'+table+';',True)
  sql('update ingest.'+table+' set created_at=created_at;',True)
 sql("insert into ingest.soil_geometry_snapshot values ('forged','"+batch+"','{}');",True)
 sql("begin isolation level repeatable read;select ingest.record_soil_geometry_snapshot('"+batch+"');commit;",True)
 checks.append('tampered_source_candidate_evidence_batch_snapshot_and_history_rejected')
 # Native directed-edge comparison detects changed geometry independently of hashes.
 assert sql("select count(*) from ((select * from ingest.soil_directed_segments(extensions.ST_GeomFromText('POLYGON((0 0,0 1,1 1,0 0))',4326))) except (select * from ingest.soil_directed_segments(extensions.ST_GeomFromText('POLYGON((0 0,1 1,0 1,0 0))',4326)))) d;")!='0'
 for role in ['anon','authenticated','service_role']:
  for table in ['soil_geometry_study','soil_geometry_correction','soil_geometry_event','soil_geometry_snapshot','effective_soil_geometry']:
   sql('set role '+role+';select * from ingest.'+table+' limit 1;',True)
  sql('set role '+role+";select ingest.record_soil_geometry_snapshot('"+batch+"');",True)
 assert sql("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='ingest' and c.relname in ('soil_geometry_study','soil_geometry_correction','soil_geometry_event','soil_geometry_snapshot') and c.relrowsecurity;")=='4'
 checks.append('private_tables_views_functions_and_rls')
 print('Acceptance lifecycle passed; calculating effective coverage',flush=True)
 coverage=json.loads(sql("select ingest.soil_geometry_coverage('"+batch+"');"))
 assert coverage['held_polygons']==0 and coverage['qualified_for_parcel_screening'] is False
 assert coverage['uncovered_m2']<0.000001 # Diagnostic comparison only; production has no tolerance.
 assert coverage['coverage_state']==('full_geometric' if coverage['uncovered_m2']==0 else 'partial_geometric')
 assert sql("select ingest.soil_geometry_snapshot_is_current('"+coverage['snapshot_id']+"','"+batch+"');")=='t'
 assert json.loads(sql(check_sql(batch,meta['row_fingerprint'],meta['records'])))==result
 checks.append('effective_coverage_recomputed_with_strict_zero_rule_and_source_fingerprint_unchanged')
 a.output.write_text(json.dumps({'status':'PASS','environment':'isolated Docker PostGIS; no live credentials or writes','migration_sha256':digest(ACCEPTANCE_MIGRATION.read_bytes()),'checks':checks,'source_readback':result,'accepted_test_coverage':coverage},indent=2)+'\n')
 print('All acceptance integration check groups passed',flush=True)
finally:subprocess.run(['docker','rm','-f',name],capture_output=True)
