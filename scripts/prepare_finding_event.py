#!/usr/bin/env python3
"""Prepare a reviewable finding-history update; does not connect to the database."""
import argparse
import json
import re
import uuid
from pathlib import Path
from prepare_source_staging import digest,jsql,literal


def event_sql(finding_id,expected_event,status,priority,next_action,actor,note,evidence):
    if not re.fullmatch(r'TL-F-[0-9]{4}',finding_id) or not re.fullmatch(r'[0-9a-f]{64}',expected_event):
        raise ValueError('Use the stable finding ID and current event_id from finding_current')
    if status not in ['open','in_progress','blocked','deferred','resolved'] or priority not in ['high','medium','low']:
        raise ValueError('Invalid status or priority')
    if not all(v.strip() for v in [next_action,actor,note]) or any(not v.strip() for v in evidence):
        raise ValueError('Review text and supplied evidence references must not be blank')
    if status=='resolved' and not evidence:raise ValueError('Resolution requires supporting evidence references')
    payload=dict(event_id=digest(uuid.uuid4().bytes),finding_id=finding_id,status=status,priority=priority,
                 next_action=next_action,actor=actor,note=note,evidence_refs=evidence)
    return 'BEGIN;\nSET LOCAL standard_conforming_strings = on;\nSELECT ingest.record_finding_event('+jsql(payload)+','+literal(expected_event)+');\nCOMMIT;\n'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['finding-id','expected-event','status','priority','next-action','actor','note']:
        p.add_argument('--'+arg,required=True)
    p.add_argument('--evidence',action='append',default=[])
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sql=event_sql(a.finding_id,a.expected_event,a.status,a.priority,a.next_action,a.actor,a.note,a.evidence)
    with a.output.open('x') as output:output.write(sql)
    print('Prepared review event:',a.output)
