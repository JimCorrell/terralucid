"""Create a streamed, transactional SQL load from a verified soil bundle."""
import argparse,csv,hashlib,json
from pathlib import Path
from verify_county_soil_bundle import verify,file_sha
from prepare_source_staging import literal,jsql
ROOT=Path(__file__).resolve().parents[1]
MIGRATION=ROOT/'supabase/migrations/20260923010000_soil_source_staging.sql'
def fingerprint(lines):
    h=hashlib.sha256()
    for line in lines:h.update((hashlib.sha256(line.rstrip('\n').encode()).hexdigest()+'\n').encode())
    return h.hexdigest()
def prepare(bundle,out):
    verified=verify(bundle);out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((bundle/'manifest.json').read_bytes());report=(bundle/'report.json').read_text();batch=verified['report_sha256']
    with (bundle/'records.jsonl').open() as source:fp=fingerprint(source)
    # The streamed COPY is transactional; replay is a separate readback-only path.
    with (out/'load.sql').open('w') as sql:
        sql.write("BEGIN; SET LOCAL statement_timeout='15min'; SET LOCAL standard_conforming_strings=on;\n")
        sql.write('INSERT INTO ingest.soil_batch(report_sha256,report_text,manifest,row_fingerprint) VALUES ('+','.join([literal(batch),literal(report),jsql(manifest),literal(fp)])+');\n')
        for key,info in manifest['objects'].items():
            sql.write('INSERT INTO ingest.soil_archive_object VALUES ('+','.join([literal(batch),literal(key),str(info['bytes']),literal('terralucid-source-snapshots'),literal('sha256/'+key+'.response')])+');\n')
        sql.write('COPY ingest.soil_record(report_sha256,load_ordinal,input_text) FROM STDIN WITH (FORMAT csv);\n')
        writer=csv.writer(sql,lineterminator='\n')
        with (bundle/'records.jsonl').open() as source:
            for ordinal,line in enumerate(source):writer.writerow([batch,ordinal,line.rstrip('\n')])
        sql.write('\\.\nSET CONSTRAINTS ALL IMMEDIATE;\n')
        sql.write(check_sql(batch,fp,manifest['records'],assertions=True))
        sql.write('\nCOMMIT;\n')
        sql.write(check_sql(batch,fp,manifest['records']))
    meta={'batch':batch,'row_fingerprint':fp,'records':manifest['records'],'migration_sha256':file_sha(MIGRATION),'load_sha256':file_sha(out/'load.sql')}
    (out/'deployment.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

def check_sql(batch,fp,count,assertions=False):
    # Server recomputes every row hash from stored original text, not a supplied hash.
    query=f"""select jsonb_build_object(
      'records',count(*),'row_fingerprint',encode(sha256(convert_to(string_agg(encode(sha256(convert_to(input_text,'UTF8')),'hex')||E'\\n','' order by load_ordinal),'UTF8')),'hex'),
      'holds',count(*) filter(where hold is not null),'geometry_rows',count(geometry),
      'geometry_mismatches',count(*) filter(where geometry is not null and not extensions.ST_OrderingEquals(geometry,extensions.ST_GeomFromWKB(decode(input_text::jsonb->>'geometry_wkb','hex'),4326))))
      from ingest.soil_record where report_sha256='{batch}'"""
    if not assertions:return query+';\n'
    return f"""DO $check$ DECLARE v jsonb; r jsonb; b ingest.soil_batch%rowtype; k text; n integer; BEGIN
    select * into strict b from ingest.soil_batch where report_sha256='{batch}';r:=b.report_text::jsonb;
    {query.replace('select jsonb_build_object','select jsonb_build_object',1).replace('from ingest.soil_record','into v from ingest.soil_record',1)};
    if (v->>'records')::integer<>{count} or v->>'row_fingerprint'<>'{fp}' or (v->>'geometry_mismatches')::integer<>0
      or (v->>'holds')::integer<>jsonb_array_length(r->'geometry_holds') then raise exception 'Soil load fingerprint/state mismatch';end if;
    for k,n in select key,value::text::integer from jsonb_each(r->'counts') where key<>'prepared_records' loop
      if (select count(*) from ingest.soil_record where report_sha256=b.report_sha256 and kind=k)<>n then raise exception 'Soil kind count mismatch';end if;
    end loop;
    for k,n in select key,value::text::integer from jsonb_each(r->'polygon_relations') loop
      if (select count(*) from ingest.soil_record where report_sha256=b.report_sha256 and scope_relation=k)<>n then raise exception 'Soil scope count mismatch';end if;
    end loop;
    END $check$;"""
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.bundle,a.output),indent=2))
