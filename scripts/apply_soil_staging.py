"""Apply tested soil staging after archive readback; one DB credential acquisition.

Existing batches take a readback-only path. Never retries authentication or writes.
"""
import argparse,hashlib,json,os,queue,shutil,subprocess,threading,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from apply_prepared_load import connection_environment
from prepare_source_staging import literal,jsql
from prepare_soil_staging import MIGRATION,check_sql
from verify_county_soil_bundle import verify,file_sha
PROJECT='yytsjlmbyqhcqfalbjca';VERSION='20260923010000'
def apply(bundle,deployment,archive,cli,out):
    verify(bundle);meta=json.loads((deployment/'deployment.json').read_bytes());manifest=json.loads((bundle/'manifest.json').read_bytes())
    if file_sha(deployment/'load.sql')!=meta['load_sha256'] or file_sha(MIGRATION)!=meta['migration_sha256'] or file_sha(bundle/'report.json')!=meta['batch']:raise ValueError('Deployment changed since preparation')
    transfer=json.loads((archive/'verification.json').read_bytes())
    if transfer['status']!='PASS' or not transfer['bucket_private'] or transfer['project_ref']!=PROJECT or transfer['bundle_report_sha256']!=meta['batch']:raise ValueError('Archive evidence mismatch')
    required=set(manifest['objects'])|{file_sha(bundle/'report.json'),file_sha(bundle/'manifest.json')}
    if {x['sha256'] for x in transfer['objects']}!=required or any(file_sha(archive/key)!=key for key in required):raise ValueError('Archive readback bytes mismatch')
    out.mkdir(parents=True,exist_ok=False);report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'FAIL','batch':meta['batch'],'stages':[],'credential_acquisitions':1,'database_sessions':1}
    client='terralucid-soil-load-'+uuid.uuid4().hex[:12];proc=None;errors=[];events=queue.Queue()
    def stdout(stream):
        for line in stream:events.put(line.strip())
        events.put(None)
    def stderr(stream):
        for line in stream:errors.append(line)
    def stage(name,text=None,path=None,deadline=120):
        print(name,flush=True);start=time.monotonic();marker='soil_'+uuid.uuid4().hex
        if path:
            with path.open() as source:shutil.copyfileobj(source,proc.stdin,1024*1024)
        else:proc.stdin.write(text+'\n')
        proc.stdin.write('\\echo '+marker+'\n');proc.stdin.flush();lines=[]
        while True:
            remaining=deadline-(time.monotonic()-start)
            if remaining<=0:raise RuntimeError(name+' timeout')
            try:line=events.get(timeout=remaining)
            except queue.Empty:raise RuntimeError(name+' timeout')
            if line is None:raise RuntimeError(name+' connection ended; inspect private diagnostics before retry')
            if line==marker:break
            if line:lines.append(line)
        report['stages'].append({'name':name,'seconds':round(time.monotonic()-start,2)})
        return json.loads('\n'.join(lines)) if lines else None
    try:
        result=subprocess.run([str(cli),'db','dump','--linked','--dry-run','--agent','no','--output-format','text'],capture_output=True,text=True,timeout=45)
        if result.returncode:raise RuntimeError('One database credential lookup failed; no retry')
        env=connection_environment(result.stdout,PROJECT);env['PGCONNECT_TIMEOUT']='15';env['PGAPPNAME']=client
        command=['docker','run','--rm','--name',client,'-i','--platform','linux/amd64']
        for key in env:command+=['--env',key]
        command+=['postgis/postgis:17-3.5','psql','-X','-w','-q','-t','-A','-v','ON_ERROR_STOP=1','-f','-']
        proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,**env})
        threading.Thread(target=stdout,args=(proc.stdout,),daemon=True).start();threading.Thread(target=stderr,args=(proc.stderr,),daemon=True).start()
        boundary=json.loads((bundle/'report.json').read_bytes())['boundary_sha256']
        pre=stage('preflight',f"""SET ROLE postgres; BEGIN READ ONLY; SET LOCAL statement_timeout='30s';
        select jsonb_build_object('backend',pg_backend_pid(),'installed',to_regclass('ingest.soil_batch') is not null,
          'migration_sha256',(select encode(sha256(convert_to(array_to_string(statements,E'\\n'),'UTF8')),'hex') from supabase_migrations.schema_migrations where version='{VERSION}'),
          'bucket_private',(select not public from storage.buckets where id='terralucid-source-snapshots'),
          'county_boundary_present',exists(select 1 from ingest.county_inventory_batch b join ingest.audit_result a on a.sha256=b.audit_sha256 where a.document#>>'{{boundary,sha256}}'='{boundary}'),
          'county_records',(select count(*) from ingest.county_inventory_feature),'findings',(select count(*) from ingest.finding_event));COMMIT;""")
        if not pre['bucket_private'] or not pre['county_boundary_present']:raise RuntimeError('Privacy or county boundary preflight failed')
        if pre['installed']:
            if pre['migration_sha256']!=meta['migration_sha256']:raise RuntimeError('Installed migration differs')
        else:
            if pre['migration_sha256'] is not None:raise RuntimeError('Migration history/schema mismatch')
            migration=MIGRATION.read_text()
            stage('migration',"BEGIN; SET LOCAL statement_timeout='60s';\n"+migration+"\nINSERT INTO supabase_migrations.schema_migrations(version,name,statements) VALUES ("+literal(VERSION)+",'soil_source_staging',ARRAY["+literal(migration)+"]);COMMIT;")
        batch=meta['batch']
        exists=stage('batch_lookup',"select to_jsonb(exists(select 1 from ingest.soil_batch where report_sha256='"+batch+"'));")
        if exists:
            result=stage('existing_batch_readback',check_sql(batch,meta['row_fingerprint'],meta['records'],True)+'\n'+check_sql(batch,meta['row_fingerprint'],meta['records']))
        else:result=stage('atomic_source_load',path=deployment/'load.sql',deadline=1200)
        if result['records']!=meta['records'] or result['row_fingerprint']!=meta['row_fingerprint'] or result['geometry_mismatches']!=0:raise RuntimeError('Readback differs')
        report['readback']=result;report['replayed_existing_batch']=exists
        privacy=stage('privacy_and_archive_references',f"""BEGIN READ ONLY; SET LOCAL statement_timeout='30s';select jsonb_build_object(
          'backend',pg_backend_pid(),'county_records',(select count(*) from ingest.county_inventory_feature),
          'rls_tables',(select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='ingest' and c.relname in ('soil_batch','soil_archive_object','soil_record') and c.relrowsecurity),
          'client_grants',(select count(*) from (values('anon'),('authenticated'),('service_role')) r(role) cross join (values('soil_batch'),('soil_archive_object'),('soil_record')) t(tab) where has_table_privilege(r.role,'ingest.'||t.tab,'SELECT,INSERT,UPDATE,DELETE')),
          'client_policies',(select count(*) from pg_policies where schemaname='ingest' and tablename in ('soil_batch','soil_archive_object','soil_record')),
          'archive_count',(select count(*) from ingest.soil_archive_object where report_sha256='{batch}'),
          'missing_storage_objects',(select count(*) from ingest.soil_archive_object a left join storage.objects o on o.bucket_id=a.storage_bucket and o.name=a.storage_object where a.report_sha256='{batch}' and o.id is null),
          'record_table_bytes',pg_total_relation_size('ingest.soil_record'),'database_bytes',pg_database_size(current_database()));COMMIT;""")
        if privacy['backend']!=pre['backend'] or privacy['county_records']!=pre['county_records'] or privacy['rls_tables']!=3 or privacy['client_grants'] or privacy['client_policies'] or privacy['missing_storage_objects'] or privacy['archive_count']!=len(manifest['objects']):raise RuntimeError('Postload privacy/archive check failed')
        report['privacy']=privacy;report['same_backend_confirmed']=True
        if not exists:
            payload={'event_id':hashlib.sha256(uuid.uuid4().bytes).hexdigest(),'finding_id':'TL-F-0113','status':'in_progress','actor':'Codex',
             'next_action':'Investigate seven held soil polygons and the 41.13 km2 residual coverage gap; verify units, scale and source dates before enabling soil availability. Septic suitability remains purchase-triggered.',
             'note':'Prepared soil bundle is now loaded into private Supabase soil staging: 38,237 exact source records; 82 original archive objects plus report and manifest downloaded and hash verified. Seven geometry holds retained with null analytical geometry; 41.13 km2 residual unchanged. No geometry repairs or qualification promotion.',
             'evidence_refs':['soil_batch:'+batch,'research/soil-staging-load/live-verification.json']}
            stage('finding_history',"BEGIN;SELECT ingest.record_finding_event("+jsql(payload)+"||jsonb_build_object('priority',priority),event_id) FROM ingest.finding_current WHERE finding_id='TL-F-0113';COMMIT;")
        report['finding']=stage('finding_readback',"select jsonb_build_object('finding_id',finding_id,'event_id',event_id,'status',status,'next_action',next_action) from ingest.finding_current where finding_id='TL-F-0113';")
        report['status']='PASS'
    except Exception as error:
        report['failure']=str(error) if isinstance(error,RuntimeError) else type(error).__name__
        raise
    finally:
        if proc:
            try:proc.stdin.close()
            except (BrokenPipeError,OSError):pass
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                subprocess.run(['docker','rm','-f',client],capture_output=True,timeout=15);proc.kill();proc.wait()
        if errors:
            fd=os.open(out/'client.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,'w') as log:log.write(''.join(errors))
        report['completed_at']=datetime.now(timezone.utc).isoformat();(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Soil staging load and readback verified',flush=True);return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','deployment','archive','cli','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();apply(a.bundle,a.deployment,a.archive,a.cli,a.output)
