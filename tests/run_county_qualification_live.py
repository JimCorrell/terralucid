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
 prefix="BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL search_path=pg_catalog,ingest,extensions; SET LOCAL statement_timeout='60s'; "
 audit=request['audit']
 # Original geometry is only a discovery hint. Captures below always use the
 # effective view and must independently demonstrate each test condition.
 overlap_sql=f"""with organized as materialized (
 select object_id,geometry from ingest.county_inventory_feature
 where audit_sha256='{audit}' and source_id='organized-parcels' and geometry is not null
 and data->>'scope_relation'='interior' and ST_Area(geometry) between 100 and 2000000
 order by object_id limit 1000
 ), pair as (
 select o.object_id as organized_id,u.object_id as ut_id
 from organized o cross join lateral (
 select object_id from ingest.county_inventory_feature u
 where u.audit_sha256='{audit}' and u.source_id='ut-parcels' and u.geometry && o.geometry
 and ST_Intersects(u.geometry,o.geometry) and ST_Area(ST_Intersection(u.geometry,o.geometry))>0
 order by object_id limit 1) u order by o.object_id limit 1
 ) select coalesce((select to_jsonb(pair) from pair),'null'::jsonb);"""
 pair=stage('select_cross_source_overlap',prefix+overlap_sql+' COMMIT;',70)
 if pair is None:raise RuntimeError('No cross-source overlap found in bounded 1000-record sample')
 # Choose one valid source parcel in Orneville using the civil polygon as a
 # location hint, without treating its assessment boundary as surveyed.
 parcel_sql=f"""select jsonb_build_object('source_id',f.source_id,'object_id',f.object_id)
 from ingest.county_inventory_feature f
 where f.audit_sha256='{audit}' and f.source_id='ut-parcels' and f.geometry is not null
 and f.data#>>'{{attributes,GEOCODE}}'='21821' and ST_Area(f.geometry) between 100 and 2000000
 order by f.object_id limit 1;"""
 orneville=stage('select_orneville_parcel',prefix+parcel_sql+' COMMIT;',70)
 accepted_sql=f"""select jsonb_build_object('geometry',ST_AsGeoJSON(ST_Transform(ST_Buffer(ST_PointOnSurface(c.geometry),10),4326))::jsonb,
 'correction_id',c.correction_id,'source_id',c.source_id,'object_id',c.object_id)
 from ingest.county_geometry_current c join ingest.county_inventory_batch b on b.audit_sha256=c.source_audit_sha256
 where c.source_audit_sha256='{audit}' and c.correction_status='accepted'
 and ST_Covers(b.boundary,ST_Buffer(ST_PointOnSurface(c.geometry),10)) order by c.correction_id limit 1;"""
 accepted=stage('select_accepted_geometry_area',prefix+accepted_sql+' COMMIT;',70)
 # Use a known held source's compact extent as a selection hint. Locate an
 # independent valid parcel within the county; never repair the held polygon.
 holds=[f for f in seed['features'] if f['source_id']=='lupc-zoning' and f.get('hold') and f.get('held_bounds')]
 values=[]
 for f in holds:
  bounds=f['held_bounds'];assert len(bounds)==4 and all(type(x) in (int,float) for x in bounds)
  values.append('('+str(f['object_id'])+',ST_MakeEnvelope('+','.join(map(str,bounds))+',26919))')
 if not values:raise RuntimeError('Seed capture has no held zoning extents')
 near_sql=f"""with extents(oid,g) as (values {','.join(values)}), candidate as (
 select p.source_id,p.object_id from extents h cross join lateral (
 select p.source_id,p.object_id from ingest.county_inventory_feature p
 join ingest.county_inventory_batch b using(audit_sha256)
 where p.audit_sha256='{audit}' and p.source_id in ('ut-parcels','organized-parcels')
 and p.geometry && h.g and ST_Intersects(p.geometry,h.g)
 and ST_Area(p.geometry) between 100 and 10000000 and ST_Covers(b.boundary,p.geometry)
 order by p.source_id,p.object_id limit 1) p order by h.oid limit 1)
 select (select to_jsonb(candidate) from candidate);"""
 nearby=stage('select_parcel_near_hold',prefix+near_sql+' COMMIT;',70)
 if nearby is None:raise RuntimeError('No small valid county parcel found near seed held extents')
 base={k:request[k] for k in ['audit','snapshot','purchase_candidate']};base['purchase_candidate']=False
 cases=[('orneville_parcel',base|orneville),('overlapping_sources',base|{'source_id':'organized-parcels','object_id':pair['organized_id']}),
 ('parcel_near_hold',base|nearby),('accepted_zoning_area',base|{'geometry':accepted['geometry']})]
 report['cases']=[];packets=[]
 for name,r in cases:
  capture=stage(name,q.query_sql(r).replace("statement_timeout='5min'","statement_timeout='90s'"),105)
  packet=q.qualify(capture);q.private_write(out/name/'capture.json',capture);q.private_write(out/name/'packet.json',packet)
  assert capture['aoi_within_county'],name+' outside county'
  assert not packet['qualified_for_parcel_screening'] and packet['offer_readiness']=='NOT_ASSESSED'
  for topic in ['septic_suitability','buildability']:
   assert packet['topics'][topic]['status']=='not_requested' and not packet['topics'][topic]['blocks_general_discovery']
  for topic in ['soils','terrain']:assert packet['topics'][topic]['status']=='missing' and not packet['topics'][topic]['blocks_general_discovery']
  assert packet['topics']['flood']['inventory_intersections_usable'] is False
  if name=='orneville_parcel':
   ev=packet['topics']['flood']['evidence'];assert any(e['base_product']['product_NAME']=='230465A' and len(e['letters'])==27 for e in ev)
  if name=='overlapping_sources':assert packet['topics']['identity']['cross_source_overlap_candidates']
  if name=='parcel_near_hold':assert packet['topics']['zoning']['held_evidence'] and not packet['topics']['zoning']['inventory_intersections_usable']
  if name=='accepted_zoning_area':assert any(f['correction_id']==accepted['correction_id'] and f['correction_status']=='accepted' for f in packet['topics']['zoning']['records'])
  summary={'case':name,'status':'PASS','request_sha256':q.digest(r),'capture_sha256':q.digest(capture),'packet_sha256':q.digest(packet),
   'topics':{k:{'status':v['status'],'inventory_intersections_usable':v.get('inventory_intersections_usable'),'records':len(v.get('records',[])),'held_evidence':len(v.get('held_evidence',[])),'coverage':v.get('coverage')} for k,v in packet['topics'].items()},
   'overlap_candidates':len(packet['topics']['identity']['cross_source_overlap_candidates'])}
  report['cases'].append(summary);packets.append(packet)
 # Negative source-parcel test: an actual held parcel must fail closed.
 hf=next(f for f in seed['features'] if f['source_id'] in q.PARCELS and f.get('hold'))
 r=base|{'source_id':hf['source_id'],'object_id':hf['object_id']}
 bad=stage('held_source_parcel',q.query_sql(r).replace("statement_timeout='5min'","statement_timeout='90s'"),105)
 q.private_write(out/'held-source-capture.json',bad)
 try:q.qualify(bad)
 except ValueError as e:
  assert 'Source parcel absent or geometry held' in str(e)
  report['held_source_rejected']=True
 else:raise AssertionError('Held source parcel was accepted')
 # Simulate workflow flags locally; no parcel is designated a purchase target.
 simulation=copy.deepcopy(json.loads((out/'orneville_parcel/capture.json').read_text()));simulation['request']['purchase_candidate']=True
 simulated=q.qualify(simulation)
 assert all(simulated['topics'][k]['status']=='review_required' and not simulated['topics'][k]['blocks_general_discovery'] for k in ['septic_suitability','buildability'])
 report['local_purchase_flag_simulation']='PASS; no purchase designation or database write'
 context=stage('fresh_context',q.query_sql(request,True).replace("statement_timeout='5min'","statement_timeout='20s'"),30)
 q.private_write(out/'fresh-context.json',context)
 for summary,packet in zip(report['cases'],packets):
  freshness=q.currency(packet,context);assert not freshness['needs_revisit'];summary['freshness']=freshness
 result=stage('same_session_confirmation',"BEGIN READ ONLY; SELECT json_build_object('backend',pg_backend_pid()); COMMIT;",20)
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
 report['completed_at']=datetime.now(timezone.utc).isoformat();q.private_write(out/'report.json',report)
 print(json.dumps({'status':report['status'],'failure':report.get('failure'),'passed_cases':[c['case'] for c in report.get('cases',[])]}),flush=True);print('Private report: '+str(out/'report.json'),flush=True)
if report['status']!='PASS':raise SystemExit(1)
