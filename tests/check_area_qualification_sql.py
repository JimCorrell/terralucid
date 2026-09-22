#!/usr/bin/env python3
"""Exercise extraction SQL in an isolated disposable PostGIS container; no Supabase."""
import json,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
name='terralucid-qualification-'+uuid.uuid4().hex[:8]
def command(args,sql=None):
    r=subprocess.run(args,input=sql,text=True,capture_output=True)
    if r.returncode:raise RuntimeError(r.stderr[-3000:])
    return r.stdout.strip()
def run(sql):return command(['docker','exec','-i',name,'psql','-X','-q','-t','-A','-U','postgres','-d','qualification','-v','ON_ERROR_STOP=1'],sql)
audit='a'*64;snapshot='b'*64
try:
    command(['docker','run','-d','--name',name,'--platform','linux/amd64','-e','POSTGRES_HOST_AUTH_METHOD=trust','postgis/postgis:17-3.5'])
    for _ in range(60):
        log=subprocess.run(['docker','logs',name],capture_output=True,text=True)
        if 'PostgreSQL init process complete' in log.stdout+log.stderr and subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],capture_output=True).returncode==0:break
        time.sleep(.5)
    command(['docker','exec',name,'createdb','-U','postgres','-T','template0','qualification'])
    run('''create schema extensions;create extension postgis with schema extensions;create schema ingest;
    set search_path=pg_catalog,ingest,extensions;
    create table ingest.audit_result(sha256 text,document jsonb);
    create table ingest.source_response(observation_sha256 text);
    create table ingest.county_inventory_batch(audit_sha256 text,boundary geometry);
    create table ingest.county_inventory_feature(audit_sha256 text,source_id text,object_id bigint,geometry geometry,data jsonb);
    create index fixture_gist on ingest.county_inventory_feature using gist(geometry);
    create table ingest.county_geometry_current(source_audit_sha256 text,source_id text,object_id bigint,correction_status text);
    create table ingest.effective_county_inventory(audit_sha256 text,source_id text,object_id bigint,input_sha256 text,
      effective_geometry geometry,effective_geometry_hold text,source_attributes jsonb,effective_quality_flags jsonb,
      provenance jsonb,correction_id text,geometry_event_id text,candidate_sha256 text,correction_status text);
    create table ingest.finding_current(finding_id text,title text,source_ids text[],scope jsonb,status text,priority text,
      event_id text,needs_revisit boolean,next_action text,occurrence_count bigint);
    create function ingest.county_geometry_dependencies(text) returns jsonb language sql as $$select '{}'::jsonb$$;
    create function ingest.county_geometry_snapshot_is_current(text,text) returns boolean language sql as $$select true$$;
    ''')
    run(f"set search_path=pg_catalog,ingest,extensions;insert into ingest.county_inventory_batch values('{audit}',ST_MakeEnvelope(499000,4999000,502000,5002000,26919));")
    def feature(oid,source,original,effective,hold=None,accepted=False):
        h="'held'" if hold else 'null'
        sr=5070 if source.startswith('nwi-') else 26919
        run(f"""set search_path=pg_catalog,ingest,extensions;
        insert into ingest.county_inventory_feature values('{audit}','{source}',{oid},{original},jsonb_build_object('srid',{sr}));
        insert into ingest.effective_county_inventory values('{audit}','{source}',{oid},'{oid}',{effective},{h},'{{}}','[]','{{}}',null,null,null,'{'accepted' if accepted else 'original'}');
        """)
        if accepted:run(f"insert into ingest.county_geometry_current values('{audit}','{source}',{oid},'accepted');")
    inside='ST_MakeEnvelope(500000,5000000,500100,5000100,26919)';outside='ST_MakeEnvelope(520000,5200000,520100,5200100,26919)'
    feature(1,'ut-parcels',inside,inside)
    feature(2,'lupc-zoning',outside,inside,accepted=True)
    feature(3,'lupc-zoning',outside,outside)
    feature(4,'organized-parcels','null','null',hold=True)
    feature(5,'nwi-package',f'ST_Transform({inside},5070)',f'ST_Transform({inside},5070)')
    geometry=json.loads(run(f'set search_path=pg_catalog,ingest,extensions;select ST_AsGeoJSON(ST_Transform({inside},4326));'))
    request={'audit':audit,'snapshot':snapshot,'geometry':geometry,'purchase_candidate':False}
    def extract(r):
        sql=(ROOT/'scripts/qualification_context.sql').read_text().replace('__REQUEST__',"'"+json.dumps(r).replace("'","''")+"'")+(ROOT/'scripts/qualification_extract.sql').read_text()
        return json.loads(run('begin isolation level repeatable read read only;set local search_path=pg_catalog,ingest,extensions;'+sql+'commit;'))
    result=extract(request);ids={f['object_id'] for f in result['features']}
    assert ids=={1,2,4,5},ids
    assert next(f for f in result['features'] if f['object_id']==2)['correction_status']=='accepted'
    assert result['aoi_within_county'] and result['context']['source_exists']
    subject=extract({'audit':audit,'snapshot':snapshot,'source_id':'ut-parcels','object_id':1,'purchase_candidate':False})
    assert subject['aoi_wkb'] is not None
    missing=extract({'audit':audit,'snapshot':snapshot,'source_id':'ut-parcels','object_id':999,'purchase_candidate':False})
    assert missing['aoi_wkb'] is None and missing['features']==[]
    assert run('select count(*) from ingest.county_inventory_feature')=='5'
    print(json.dumps({'passed':['indexed native and projected candidates','accepted extent outside original bbox retained','remote valid feature excluded','unlocated hold retained','source parcel lookup','absent subject fails closed','read-only extraction preserves fixtures']}))
finally:
    subprocess.run(['docker','rm','-f',name],capture_output=True)
