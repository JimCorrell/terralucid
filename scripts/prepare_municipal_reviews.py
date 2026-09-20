#!/usr/bin/env python3
"""Prepare replay-safe finding reviews; adds one scoped freshness finding."""
import argparse
import json
from pathlib import Path
from prepare_source_staging import ROOT,canonical,digest,jsql,literal


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--current',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();base=ROOT/'research/municipal-corroboration'
    report=json.loads((base/'report.json').read_bytes());sha=digest((base/'report.json').read_bytes())
    plan=json.loads((base/'reviews.json').read_bytes());plan_sha=digest((base/'reviews.json').read_bytes())
    definitions=json.loads((base/'new-findings.json').read_bytes());definitions_sha=digest((base/'new-findings.json').read_bytes())
    current={r['finding_id']:r for r in json.loads(a.current.read_bytes())['rows']}
    if digest((ROOT/report['method']).read_bytes())!=report['method_sha256']:raise ValueError('Stale report')
    for name,expected in report['inputs'].items():
        if digest((ROOT/name).read_bytes())!=expected:raise ValueError('Report input changed')
    sql=['BEGIN;','SET LOCAL standard_conforming_strings = on;']
    for definition in definitions:
        fid=definition['finding_id']
        sql.append('INSERT INTO ingest.finding (finding_id,title,description,source_ids,scope,evidence_state) VALUES ('+
                   ','.join([literal(fid),literal(definition['title']),literal(definition['description']),
                             'ARRAY['+','.join(map(literal,definition['source_ids']))+']::text[]',
                             jsql(definition['scope']),literal(definition['evidence_state'])])+') ON CONFLICT DO NOTHING;')
        # Refuse an ID collision rather than attaching evidence to another finding.
        sql.append("DO $check$ BEGIN IF (SELECT to_jsonb(f)-'created_at' FROM ingest.finding f WHERE finding_id="+
                   literal(fid)+') IS DISTINCT FROM '+jsql(definition)+
                   " THEN RAISE EXCEPTION 'Finding ID already has a different definition'; END IF; END $check$;")
    new_ids={d['finding_id'] for d in definitions}
    for review in plan['reviews']:
        fid=review['finding_id'];previous=current.get(fid,{}).get('event_id')
        if previous is None and fid not in new_ids:raise ValueError('Current review token missing')
        target=report
        for part in review['report_pointer'].strip('/').split('/'):
            target=target[int(part)] if isinstance(target,list) else target[part]
        if not target:raise ValueError('Report evidence missing')
        payload={'event_id':digest(canonical([sha,review,definitions_sha]).encode()),'finding_id':fid,
                 'status':review['status'],'priority':review['priority'],'next_action':review['next_action'],
                 'actor':'TerraLucid municipal corroboration','note':review['note'],
                 'evidence_refs':['audit:'+sha+'#'+review['report_pointer'],'artifact:'+plan_sha,'artifact:'+definitions_sha]}
        occurrence=digest((fid+sha+'municipal-corroboration').encode())
        sql.append('INSERT INTO ingest.finding_occurrence (occurrence_id,finding_id,audit_sha256,details) VALUES ('+
                   ','.join([literal(occurrence),literal(fid),literal(sha),jsql({'report_pointer':review['report_pointer'],
                   'evidence_state':'DERIVED','scope':'Municipal corroboration and proposed snapshot corrections'})])+') ON CONFLICT DO NOTHING;')
        sql.append('SELECT ingest.record_finding_event('+jsql(payload)+','+(literal(previous) if previous else 'NULL')+');')
    sql.append('COMMIT;')
    with a.output.open('x') as f:f.write('\n'.join(sql)+'\n')
    print('Prepared',len(plan['reviews']),'reviews; report',sha)


if __name__=='__main__':main()
