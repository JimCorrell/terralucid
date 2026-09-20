#!/usr/bin/env python3
"""Append zoning findings to a prepared atomic load using freshly read review tokens."""
import argparse
import json
from pathlib import Path
from prepare_source_staging import ROOT,canonical,digest,literal,jsql


def append_reviews(prepared,current):
    base=ROOT/'research/zoning-ingestion';sha=digest((base/'report.json').read_bytes())
    plan=json.loads((base/'findings-plan.json').read_bytes());plan_sha=digest((base/'findings-plan.json').read_bytes())
    rows={r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    sql=(prepared/'load.sql').read_text()
    if '-- Zoning finding reviews' in sql:raise ValueError('Reviews already prepared')
    sql=sql.removesuffix('COMMIT;\n')+'-- Zoning finding reviews\n'
    for definition in plan['new_findings']:
        values=[literal(definition['finding_id']),literal(definition['title']),literal(definition['description']),
                'ARRAY['+','.join(map(literal,definition['source_ids']))+']::text[]',jsql(definition['scope']),literal(definition['evidence_state'])]
        sql+='INSERT INTO ingest.finding(finding_id,title,description,source_ids,scope,evidence_state) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
        body="BEGIN IF NOT EXISTS (SELECT 1 FROM ingest.finding f WHERE finding_id="+literal(definition['finding_id'])+" AND to_jsonb(f)-'created_at'="+jsql(definition)+") THEN RAISE EXCEPTION 'Finding definition differs'; END IF; END"
        sql+='DO '+literal(body)+';\n'
    for r in plan['reviews']:
        fid=r['finding_id'];old=rows.get(fid,{}).get('event_id')
        event={k:v for k,v in r.items() if k!='report_pointer'}
        event.update(event_id=digest(canonical([fid,sha,plan_sha]).encode()),actor='TerraLucid zoning ingestion',evidence_refs=['audit:'+sha+'#'+r['report_pointer'],'artifact:'+plan_sha])
        occurrence=digest(canonical([fid,sha,'zoning-ingestion']).encode())
        sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(occurrence),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        sql+='SELECT ingest.record_finding_event('+jsql(event)+','+(literal(old) if old else 'NULL')+');\n'
    (prepared/'load.sql').write_text(sql+'COMMIT;\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--current',type=Path,required=True);a=p.parse_args();append_reviews(a.prepared,a.current)
