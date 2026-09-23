"""One credential acquisition and one database session; never retries auth."""
import argparse,copy,json,os,queue,re,subprocess,sys,threading,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import qualify_area as q
from apply_prepared_load import connection_environment
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cli',required=True,type=Path)
parser.add_argument('--seed-capture',required=True,type=Path,help='Private verified compact capture containing county holds and the intended audit/snapshot')
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args();cli=args.cli.resolve();out=args.output.resolve()
seed=json.loads(args.seed_capture.read_text());request=seed['request'];q.validate_request(request)
out.mkdir(mode=0o700);os.chdir(ROOT)
report={'started_at':datetime.now(timezone.utc).isoformat(),'credential_acquisitions':0,'database_sessions':0,'stages':[],'status':'FAIL','database_writes':False}
proc=None;client='terralucid-acceptance-'+uuid.uuid4().hex[:12];events=queue.Queue();errors=[]
def read_stdout(stream):
 for line in stream:events.put(line.strip())
 events.put(None)
def read_errors(stream):
 for line in stream:errors.append(line)
def stage(name,sql,deadline):
 print('Starting '+name,flush=True);start=time.monotonic();marker='acceptance_'+uuid.uuid4().hex
 proc.stdin.write(sql+'\n\\echo '+marker+'\n');proc.stdin.flush();lines=[]
 while True:
  remaining=deadline-(time.monotonic()-start)
  if remaining<=0:raise RuntimeError(name+' deadline exceeded')
  try:line=events.get(timeout=remaining)
  except queue.Empty:raise RuntimeError(name+' deadline exceeded')
  if line is None:raise RuntimeError(name+' client disconnected')
  if line==marker:break
  if line:lines.append(line)
 result=json.loads('\n'.join(lines));report['stages'].append({'stage':name,'status':'PASS','seconds':round(time.monotonic()-start,2)})
 print(name+' passed',flush=True);return result
try:
 if not cli.is_file():raise RuntimeError('Configured CLI binary missing')
 subprocess.run(['docker','image','inspect','postgis/postgis:17-3.5','--format','{{.Id}}'],capture_output=True,timeout=15,check=True)
 print('Preflight passed; requesting temporary credentials once through the existing CLI sign-in',flush=True)
 report['credential_acquisitions']=1
 result=subprocess.run([str(cli),'db','dump','--linked','--dry-run','--agent','no','--output-format','text'],capture_output=True,text=True,timeout=45)
 if result.returncode:
  errors.append(result.stderr);raise RuntimeError('CLI temporary-credential acquisition failed')
 env=connection_environment(result.stdout,'yytsjlmbyqhcqfalbjca');env['PGCONNECT_TIMEOUT']='15';env['PGAPPNAME']=client
 report['stages'].append({'stage':'credential_acquisition','status':'PASS'})
 command=['docker','run','--rm','--name',client,'-i','--platform','linux/amd64']
 for k in env:command+=['--env',k]
 command+=['postgis/postgis:17-3.5','psql','-X','-w','-q','-t','-A','-v','ON_ERROR_STOP=1','-f','-']
 proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,**env},bufsize=1)
 report['database_sessions']=1
 threading.Thread(target=read_stdout,args=(proc.stdout,),daemon=True).start();threading.Thread(target=read_errors,args=(proc.stderr,),daemon=True).start()
 result=stage('simple_read',"BEGIN READ ONLY; SELECT json_build_object('probe',1,'readonly',current_setting('transaction_read_only'),'backend',pg_backend_pid()); COMMIT;",25)
 assert result['probe']==1 and result['readonly']=='on';backend=result['backend']
 result=stage('private_function_access',"SET ROLE postgres; BEGIN READ ONLY; SET LOCAL statement_timeout='20s'; SELECT json_build_object('snapshot_current',ingest.county_geometry_snapshot_is_current('"+request['snapshot']+"','"+request['audit']+"'),'backend',pg_backend_pid()); COMMIT;",30)
 assert result['snapshot_current'] and result['backend']==backend
 from prepare_source_staging import jsql
 import hashlib
 gap_path=ROOT/'research/soil-availability/component-gaps.json';gap=json.loads(gap_path.read_bytes())
 assert gap['exact_selected_rows_match'] and not gap['new_keys'] and not gap['missing_keys']
 payload={'event_id':hashlib.sha256(uuid.uuid4().bytes).hexdigest(),'finding_id':'TL-F-0113','status':'in_progress','actor':'Codex',
 'note':'Component gap investigation: all 716 directly queried USDA component records for the 262 county percentage-deficit map units match the captured keys and compared attributes. USDA Fundamental Query page 5 documents unrecorded minor components as a possible source of totals below 100. Preserve unlisted proportions and unknown identity; no normalization or source repairs. Bounded read-only soil availability adapter implemented and isolated SQL/unit checks passed; site suitability remains unknown.',
 'next_action':'Review bounded soil availability checks and carry component mixtures, incomplete proportions, source dates/scale, nulls and Vermont-interpretation exclusion into discovery packets. Site suitability stays purchase-triggered.',
 'evidence_refs':['research/soil-availability/component-gaps.json','sha256:'+hashlib.sha256(gap_path.read_bytes()).hexdigest()]}
 finding_sql="BEGIN; SET LOCAL statement_timeout='30s'; SELECT ingest.record_finding_event("+jsql(payload)+"||jsonb_build_object('priority',priority),event_id) FROM ingest.finding_current WHERE finding_id='TL-F-0113'; SELECT jsonb_build_object('finding_id',finding_id,'event_id',event_id,'status',status) FROM ingest.finding_current WHERE finding_id='TL-F-0113'; COMMIT;"
 report['finding_update']=stage('component_gap_finding',finding_sql,40)
 assert report['finding_update']['event_id']==payload['event_id']
 report['database_writes']='one append-only finding event; no source or qualification state changes'
 selected=stage('select_corrected_soil_area',"BEGIN READ ONLY;SET LOCAL search_path=pg_catalog,ingest,extensions;SELECT jsonb_build_object('geometry',ST_AsGeoJSON(ST_Transform(ST_Buffer(ST_PointOnSurface(ST_Intersection(ST_Transform(c.geometry,26919),s.boundary)),5),4326))::jsonb) FROM ingest.soil_geometry_current c JOIN ingest.soil_geometry_study s USING(source_batch_sha256) WHERE c.source_batch_sha256='"+request['soils']['batch']+"' AND c.correction_status='accepted' AND ST_Intersects(ST_Transform(c.geometry,26919),s.boundary) AND ST_Covers(s.boundary,ST_Buffer(ST_PointOnSurface(ST_Intersection(ST_Transform(c.geometry,26919),s.boundary)),5)) ORDER BY correction_id LIMIT 1;COMMIT;",60)
 alternate={k:v for k,v in request.items() if k not in ('source_id','object_id','geometry')}|selected
 report['cases']=[];packets=[]
 for name,r in [('orneville_source_parcel',request),('accepted_soil_diagnostic_area',alternate)]:
  capture=stage(name,q.query_sql(r),330);packet=q.qualify(capture)
  q.private_write(out/name/'capture.json',capture);q.private_write(out/name/'packet.json',packet)
  t=packet['topics']['soils'];assert t['inventory_intersections_usable'] and t['coverage']['state']=='full_geometric'
  assert not packet['qualified_for_parcel_screening'] and packet['topics']['septic_suitability']['status']=='not_requested'
  if name=='accepted_soil_diagnostic_area':assert any(v['correction_status']=='accepted' for v in t['records'])
  report['cases'].append({'case':name,'packet_sha256':q.digest(packet),'capture_sha256':q.digest(capture),'status':t['status'],'inventory_intersections_usable':t['inventory_intersections_usable'],'coverage':t['coverage'],'soil_polygons':len(t['records']),'component_mixtures':t['component_mixtures'],'horizon_profiles':t['horizon_profiles'],'metadata_sha256':t['dependencies']['metadata_sha256']});packets.append(packet)
 context=stage('fresh_context',q.query_sql(request,True),60)
 for packet,summary in zip(packets,report['cases']):
  summary['freshness']=q.currency(packet,context);assert not summary['freshness']['needs_revisit']
 result=stage('same_session_confirmation',"BEGIN READ ONLY;SELECT json_build_object('backend',pg_backend_pid());COMMIT;",20)
 assert result['backend']==backend
 report.update(status='PASS',method_sha256=q.method_hash(),same_backend_confirmed=True)
except Exception as e:
 report['failure']=str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__
 codes=sorted(set(re.findall(r'EAUTHQUERY|LegacyDbConfigLoginRoleStatusError|\b544\b|\b524\b', ''.join(errors))))
 report['error_codes']=codes
finally:
 if proc:
  try:proc.stdin.close()
  except Exception:pass
  try:proc.wait(timeout=3)
  except subprocess.TimeoutExpired:
   subprocess.run(['docker','rm','-f',client],capture_output=True,timeout=15)
   proc.kill();proc.wait()
 if errors:
  diagnostic=''.join(errors)
  if 'env' in locals() and env.get('PGPASSWORD'):diagnostic=diagnostic.replace(env['PGPASSWORD'],'[REDACTED]')
  q.private_write(out/'diagnostic.json',{'error':diagnostic})
 report['completed_at']=datetime.now(timezone.utc).isoformat();q.private_write(out/'report.json',report)
 print(json.dumps({'status':report['status'],'failure':report.get('failure'),'passed_cases':[c['case'] for c in report.get('cases',[])]}),flush=True);print('Private report: '+str(out/'report.json'),flush=True)
if report['status']!='PASS':raise SystemExit(1)
