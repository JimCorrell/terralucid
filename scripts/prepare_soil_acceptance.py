"""Prepare exact PR59 soil proposals, without acceptance events or live access."""
import argparse,hashlib,json
from pathlib import Path
from verify_county_soil_bundle import verify,file_sha
from prepare_source_staging import literal
ROOT=Path(__file__).resolve().parents[1]
MIGRATION=ROOT/'supabase/migrations/20260923020000_soil_geometry_acceptance.sql'
REPORT=ROOT/'research/soil-holds-investigation/report.json'
REPORT_SHA='ddda7a3674c616b1eda8921cdf7581fe58aecfffd6e8c32bbebd49ed8ca6df8a'
def prepare(bundle,analysis,county,out):
    verified=verify(bundle)
    if file_sha(REPORT)!=REPORT_SHA or file_sha(analysis/'report.json')!=REPORT_SHA:raise ValueError('Reviewed investigation changed')
    r=json.loads(REPORT.read_bytes());boundary=json.loads(county.read_bytes())['boundary']
    if verified['report_sha256']!=r['bundle_report_sha256']:raise ValueError('Different source batch')
    boundary_hex=boundary['wkb_hex']
    if hashlib.sha256(bytes.fromhex(boundary_hex)).hexdigest()!=r['boundary_sha256']:raise ValueError('Boundary changed')
    sources={}
    for line in (bundle/'records.jsonl').open():
        record=json.loads(line)
        if record['kind']=='mupolygon' and record['hold']:sources[record['source_key']]=hashlib.sha256(line.rstrip('\n').encode()).hexdigest()
    if set(sources)!={c['mupolygonkey'] for c in r['candidates']}:raise ValueError('Held membership changed')
    batch=verified['report_sha256'];sql=['BEGIN; SET LOCAL statement_timeout=\'5min\';']
    sql.append('INSERT INTO ingest.soil_geometry_study(source_batch_sha256,investigation_text,investigation_sha256,boundary_wkb,boundary_sha256) VALUES ('+','.join([literal(batch),literal(REPORT.read_text()),literal(REPORT_SHA),"decode("+literal(boundary_hex)+",'hex')",literal(r['boundary_sha256'])])+') ON CONFLICT(source_batch_sha256) DO NOTHING;')
    proposals=[]
    for c in r['candidates']:
        key=c['mupolygonkey'];path=analysis/(key+'.candidate.wkb');candidate=path.read_bytes();sha=file_sha(path)
        if sha!=c['candidate_sha256']:raise ValueError('Candidate differs')
        cid=hashlib.sha256((batch+':'+key+':'+sha).encode()).hexdigest()
        sql.append('INSERT INTO ingest.soil_geometry_correction(correction_id,source_batch_sha256,source_key,source_input_sha256,candidate_wkb,candidate_sha256,evidence_state) VALUES ('+','.join([literal(cid),literal(batch),literal(key),literal(sources[key]),"decode("+literal(candidate.hex())+",'hex')",literal(sha),literal('DERIVED')])+') ON CONFLICT(correction_id) DO NOTHING;')
        proposals.append({'source_key':key,'correction_id':cid,'source_input_sha256':sources[key],'candidate_sha256':sha})
    sql.append('COMMIT;')
    out.mkdir(parents=True,exist_ok=False);(out/'proposals.sql').write_text('\n'.join(sql)+'\n')
    meta={'batch':batch,'investigation_sha256':REPORT_SHA,'migration_sha256':file_sha(MIGRATION),'proposals_sql_sha256':file_sha(out/'proposals.sql'),'acceptance_events':0,'proposals':proposals}
    (out/'preparation.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','analysis','county','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare(a.bundle,a.analysis,a.county,a.output)
