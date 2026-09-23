"""Full-bundle isolated PostGIS load plus privacy, mutation and rollback tests."""
import argparse,json,subprocess,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_soil_staging import MIGRATION,check_sql
from prepare_source_staging import literal,jsql,digest
p=argparse.ArgumentParser();p.add_argument('--deployment',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
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
 sql("update ingest.soil_record set input_text=input_text where report_sha256='"+batch+"';",True)
 sql("delete from ingest.soil_archive_object where report_sha256='"+batch+"';",True)
 sql("update ingest.soil_batch set row_fingerprint=row_fingerprint;",True)
 sql("insert into ingest.soil_record(report_sha256,load_ordinal,input_text) select report_sha256,999999,input_text from ingest.soil_record limit 1;",True)
 checks.append('sealed_batch_rejects_mutations_and_late_appends')
 sql("insert into ingest.soil_batch select * from ingest.soil_batch;",True)
 assert json.loads(sql(check_sql(batch,meta['row_fingerprint'],meta['records'])))==result
 checks.append('duplicate_batch_rejected_without_changes')
 for role in ['anon','authenticated','service_role']:
  sql('set role '+role+';select * from ingest.soil_record limit 1;',True)
 assert sql("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='ingest' and c.relname in ('soil_record','soil_batch','soil_archive_object') and c.relrowsecurity;")=='3'
 checks.append('client_roles_denied_and_rls_enabled')
 # Invalid payloads must roll back even their newly inserted batch.
 report='{}';fixture=digest(report.encode());src='0'*64
 pre="BEGIN;INSERT INTO ingest.soil_batch(report_sha256,report_text,manifest,row_fingerprint) VALUES ("+','.join([literal(fixture),literal(report),jsql({'report_sha256':fixture} ),literal('0'*64)])+");INSERT INTO ingest.soil_archive_object VALUES ("+','.join([literal(fixture),literal(src),'1',literal('terralucid-source-snapshots'),literal('sha256/'+src+'.response')])+');'
 base_record={'kind':'mupolygon','source_key':'1','raw':{'mupolygonkey':'1','mukey':'2','source_wkt':'POLYGON ((0 0,1 0,1 1,0 0))'},'provenance':{'response_sha256':src,'row_ordinal':0},'srid':4326,'hold':None,'scope_relation':'interior','geometry_wkb':None}
 from shapely.geometry import Polygon
 good=Polygon([(0,0),(1,0),(1,1),(0,0)]).wkb_hex
 bad=Polygon([(0,0),(1,1),(0,1),(1,0),(0,0)]).wkb_hex
 for change in [{'geometry_wkb':bad},{'geometry_wkb':good,'hold':'held','scope_relation':'held'},{'geometry_wkb':good,'srid':26919},{'geometry_wkb':good}]:
  r=base_record|change
  sql(pre+'INSERT INTO ingest.soil_record(report_sha256,load_ordinal,input_text) VALUES ('+literal(fixture)+',0,'+literal(json.dumps(r))+');COMMIT;',True)
  assert sql("select count(*) from ingest.soil_batch where report_sha256='"+fixture+"';")=='0'
 checks.append('invalid_geometry_hold_crs_and_missing_parent_roll_back')
 a.output.write_text(json.dumps({'status':'PASS','checks':checks,'readback':result},indent=2)+'\n');print('All five integration check groups passed',flush=True)
finally:subprocess.run(['docker','rm','-f',name],capture_output=True)
