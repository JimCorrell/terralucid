"""Activate reviewed soil corrections with one bounded database session.

Stops on existing correction state; never retries authentication or writes.
"""
import argparse,hashlib,json,os,queue,re,shutil,subprocess,threading,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from apply_prepared_load import connection_environment
from prepare_source_staging import literal,jsql
from prepare_soil_staging import check_sql
from prepare_soil_acceptance import MIGRATION,ROOT
from verify_county_soil_bundle import verify,file_sha
PROJECT='yytsjlmbyqhcqfalbjca';VERSION='20260923020000'
def apply(bundle,proposals,archive,cli,out):
    verified=verify(bundle);meta=json.loads((proposals/'preparation.json').read_bytes())
    tests=json.loads((ROOT/'research/soil-geometry-acceptance/integration-tests.json').read_bytes())
    if tests['status']!='PASS' or tests['migration_sha256']!=file_sha(MIGRATION) or meta['migration_sha256']!=file_sha(MIGRATION) or file_sha(proposals/'proposals.sql')!=meta['proposals_sql_sha256'] or verified['report_sha256']!=meta['batch']:raise ValueError('Tested preparation changed')
    transfer=json.loads((archive/'verification.json').read_bytes())
    if transfer['status']!='PASS' or not transfer['bucket_private'] or transfer['project_ref']!=PROJECT or transfer['investigation_report_sha256']!=meta['investigation_sha256']:raise ValueError('Archive evidence differs')
    required={meta['investigation_sha256']}|{p['candidate_sha256'] for p in meta['proposals']}
    if not required.issubset({x['sha256'] for x in transfer['objects']}) or any(file_sha(archive/x['sha256'])!=x['sha256'] for x in transfer['objects']):raise ValueError('Archive bytes differ')
    pending_sql=(ROOT/'research/soil-holds-investigation/pending-finding-update.sql').read_text()
    pending=json.loads(re.search(r"record_finding_event\('(.+?)'::jsonb",pending_sql).group(1))
    baseline=tests['source_readback'];batch=meta['batch']
    out.mkdir(parents=True,exist_ok=False);report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'FAIL','batch':meta['batch'],'stages':[],'credential_acquisitions':1,'database_sessions':1,'migration_sha256':meta['migration_sha256'],'proposals_sql_sha256':meta['proposals_sql_sha256'],'runner_sha256':file_sha(Path(__file__))}
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
        pre=stage('preflight',f"""SET ROLE postgres; SET statement_timeout='180s'; SET lock_timeout='15s';
        select jsonb_build_object('backend',pg_backend_pid(),'installed',to_regclass('ingest.soil_geometry_study') is not null,
          'migration_sha256',(select encode(sha256(convert_to(array_to_string(statements,E'\\n'),'UTF8')),'hex') from supabase_migrations.schema_migrations where version='{VERSION}'),
          'bucket_private',(select not public from storage.buckets where id='terralucid-source-snapshots'),
          'county_records',(select count(*) from ingest.county_inventory_feature),
          'pending_event',(select to_jsonb(e)-'event_seq'-'created_at' from ingest.finding_event e where event_id='{pending['event_id']}'),
          'finding',(select jsonb_build_object('event_id',event_id,'priority',priority,'status',status) from ingest.finding_current where finding_id='TL-F-0113'));
        """)
        report['preflight']=pre
        if not pre['bucket_private'] or not pre['finding'] or pre['finding']['status']!='in_progress':raise RuntimeError('Unexpected privacy/finding state')
        report['pending_event_reconciliation']='present' if pre['pending_event'] else 'absent'
        if pre['pending_event'] and {k:v for k,v in pre['pending_event'].items() if k!='priority'}!=pending:raise RuntimeError('Pending event content differs')
        source=stage('source_fingerprint',check_sql(batch,baseline['row_fingerprint'],baseline['records']),deadline=210)
        if source!=baseline:raise RuntimeError('Source baseline differs')
        report['source_before']=source
        if pre['installed']:
            if pre['migration_sha256']!=meta['migration_sha256']:raise RuntimeError('Installed migration differs')
        else:
            if pre['migration_sha256'] is not None:raise RuntimeError('Migration history/schema mismatch')
            migration=MIGRATION.read_text()
            stage('migration',"BEGIN;\n"+migration+"\nINSERT INTO supabase_migrations.schema_migrations(version,name,statements) VALUES ("+literal(VERSION)+",'soil_geometry_acceptance',ARRAY["+literal(migration)+"]);COMMIT;")
        # Keep proposal staging, finding reconciliation, acceptance and coverage atomic.
        stage('activation_begin',"BEGIN;DO $$ BEGIN PERFORM 1 FROM ingest.soil_batch WHERE report_sha256="+literal(batch)+" FOR UPDATE;IF EXISTS(SELECT 1 FROM ingest.soil_geometry_correction WHERE source_batch_sha256="+literal(batch)+") THEN RAISE EXCEPTION 'Existing correction state requires review';END IF;END $$;")
        text=(proposals/'proposals.sql').read_text()
        text=text.removeprefix("BEGIN; SET LOCAL statement_timeout='5min';\n").removesuffix('COMMIT;\n')
        if text.startswith('BEGIN') or text.rstrip().endswith('COMMIT;'):raise ValueError('Unexpected transaction wrapper')
        stage('proposals',text)
        expected=pre['finding']['event_id']
        if not pre['pending_event']:
            payload=pending|{'priority':pre['finding']['priority']}
            stage('reconcile_missing_investigation',"select ingest.record_finding_event("+jsql(payload)+","+literal(expected)+");")
            expected=pending['event_id']
        events=[];statements=[]
        for row in meta['proposals']:
            event={'event_id':hashlib.sha256((row['correction_id']+':PR60-initial-acceptance').encode()).hexdigest(),
              'correction_id':row['correction_id'],'status':'accepted','actor':'Codex',
              'note':'User authorized activation after merged PR60; exact PR59 proposal, original directed segments preserved. Geometry only; no suitability or availability qualification.'}
            events.append(event)
            statements.append('DO $$ BEGIN PERFORM ingest.record_soil_geometry_event('+jsql(event)+',NULL);END $$;')
        stage('acceptance_events','\n'.join(statements));report['acceptance_events']=events
        coverage=stage('coverage',"select ingest.soil_geometry_coverage("+literal(batch)+");",deadline=240)
        if coverage['held_polygons']!=0 or coverage['qualified_for_parcel_screening'] is not False:raise RuntimeError('Unexpected effective state')
        if coverage['coverage_state']!=('full_geometric' if coverage['uncovered_m2']==0 else 'partial_geometric'):raise RuntimeError('Coverage rule differs')
        report['coverage']=coverage
        note={'event_id':hashlib.sha256((batch+':PR60-soil-activation-finding').encode()).hexdigest(),'finding_id':'TL-F-0113','status':'in_progress','priority':pre['finding']['priority'],'actor':'Codex',
          'note':'Seven reviewed exact-source soil corrections accepted. All original holds/records remain unchanged. Effective coverage recomputed: '+json.dumps(coverage,sort_keys=True)+'. Geometry acceptance is not soil availability or site suitability qualification.',
          'next_action':'Qualify soil units, scale, survey/source dates and attribute limitations before enabling availability. Retain coverage/runtime and correction snapshot dependencies. Septic/buildability adjudication remains purchase-triggered.',
          'evidence_refs':['soil_batch:'+batch,'investigation_sha256:'+meta['investigation_sha256'],'soil_geometry_snapshot:'+coverage['snapshot_id'],'research/soil-correction-activation/live-verification.json']}
        stage('finding_update','select ingest.record_finding_event('+jsql(note)+','+literal(expected)+');')
        stage('commit','COMMIT;');report['committed']=True
        report['source_after']=stage('source_readback',check_sql(batch,baseline['row_fingerprint'],baseline['records']),deadline=210)
        if report['source_after']!=baseline:raise RuntimeError('Original source changed')
        post=stage('final_readback',f"""select jsonb_build_object('backend',pg_backend_pid(),
          'county_records',(select count(*) from ingest.county_inventory_feature),
          'snapshot_current',ingest.soil_geometry_snapshot_is_current('{coverage['snapshot_id']}','{batch}'),
          'accepted',(select count(*) from ingest.soil_geometry_current where source_batch_sha256='{batch}' and correction_status='accepted'),
          'effective_holds',(select count(*) from ingest.effective_soil_geometry where report_sha256='{batch}' and effective_geometry_hold is not null),
          'rls_tables',(select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='ingest' and c.relname in ('soil_geometry_study','soil_geometry_correction','soil_geometry_event','soil_geometry_snapshot') and c.relrowsecurity),
          'client_grants',(select count(*) from (values('anon'),('authenticated'),('service_role')) r(role) cross join (values('soil_geometry_study'),('soil_geometry_correction'),('soil_geometry_event'),('soil_geometry_snapshot'),('effective_soil_geometry')) t(tab) where has_table_privilege(r.role,'ingest.'||t.tab,'SELECT,INSERT,UPDATE,DELETE')),
          'finding',(select jsonb_build_object('finding_id',finding_id,'event_id',event_id,'status',status,'next_action',next_action) from ingest.finding_current where finding_id='TL-F-0113'));
        """)
        report['readback']=post
        if post['backend']!=pre['backend'] or post['county_records']!=pre['county_records'] or not post['snapshot_current'] or post['accepted']!=7 or post['effective_holds'] or post['rls_tables']!=4 or post['client_grants'] or post['finding']['event_id']!=note['event_id']:raise RuntimeError('Final readback differs')
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
            with os.fdopen(fd,'w') as log:
                diagnostic=''.join(errors)
                if 'env' in locals() and env.get('PGPASSWORD'):diagnostic=diagnostic.replace(env['PGPASSWORD'],'[REDACTED]')
                log.write(diagnostic)
        report['completed_at']=datetime.now(timezone.utc).isoformat();(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Soil correction activation and readback verified',flush=True);return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','proposals','archive','cli','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();apply(a.bundle,a.proposals,a.archive,a.cli,a.output)
