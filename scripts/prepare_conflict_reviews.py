#!/usr/bin/env python3
"""Prepare append-only investigation reviews from a fresh administrative queue read."""
import argparse
import json
from pathlib import Path
from prepare_source_staging import ROOT, digest, jsql, literal


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--current',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    base=ROOT/'research/conflict-investigation'
    report=json.loads((base/'report.json').read_bytes())
    report_sha=digest((base/'report.json').read_bytes())
    plan=json.loads((base/'reviews.json').read_bytes())
    plan_sha=digest((base/'reviews.json').read_bytes())
    current={r['finding_id']:r for r in json.loads(args.current.read_bytes())['rows']}
    if digest((ROOT/report['method']).read_bytes())!=report['method_sha256']:raise ValueError('Stale report method')
    for name,sha in report['inputs'].items():
        if digest((ROOT/name).read_bytes())!=sha:raise ValueError('Report input changed')
    sql=['BEGIN;','SET LOCAL standard_conforming_strings = on;']
    for review in plan['reviews']:
        fid=review['finding_id'];previous=current[fid]['event_id']
        target=report
        for part in review['report_pointer'].strip('/').split('/'):
            target=target[int(part)] if isinstance(target,list) else target[part]
        if not target:raise ValueError('Missing report evidence')
        refs=['audit:'+report_sha+'#'+review['report_pointer'], 'artifact:'+plan_sha]
        payload=dict(event_id=digest((fid+report_sha+plan_sha).encode()),finding_id=fid,
                     status=plan['status'],priority=review['priority'],next_action=review['next_action'],
                     actor='TerraLucid conflict investigation',note=review['note'],evidence_refs=refs)
        occurrence=digest((fid+report_sha+'conflict-investigation').encode())
        sql.append('INSERT INTO ingest.finding_occurrence (occurrence_id,finding_id,audit_sha256,details) VALUES ('+
                   ','.join([literal(occurrence),literal(fid),literal(report_sha),jsql({'report_pointer':review['report_pointer'],
                   'evidence_state':'DERIVED','scope':report['scope']})])+') ON CONFLICT DO NOTHING;')
        sql.append('SELECT ingest.record_finding_event('+jsql(payload)+','+literal(previous)+');')
    sql.append('COMMIT;')
    with args.output.open('x') as f:f.write('\n'.join(sql)+'\n')
    print('Prepared',len(plan['reviews']),'append-only reviews; report',report_sha)


if __name__=='__main__':main()
