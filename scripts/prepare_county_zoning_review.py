#!/usr/bin/env python3
"""Stage the held-zoning research audit and append findings; no geometry acceptance."""
import argparse,json
from pathlib import Path
from investigate_county_zoning_cases import BASE
from prepare_source_staging import ROOT,prepare,digest,canonical,literal,jsql


def stage(output):
    r=json.loads((BASE/'report.json').read_bytes());audit=digest((BASE/'report.json').read_bytes())
    plan=json.loads((BASE/'finding-review.json').read_bytes())
    for path,sha in r['inputs'].items():
        if digest((ROOT/path).read_bytes())!=sha:raise ValueError('Changed report dependency')
    prepare(BASE,output,BASE/'report.json');m=json.loads((output/'manifest.json').read_bytes())
    paths=list(r['inputs'])+[c['candidate_path'] for c in r['cases'] if c['status']=='proposed_not_accepted']
    paths+=['research/piscataquis-zoning-holds/finding-review.json','scripts/prepare_county_zoning_review.py']
    paths += [p.relative_to(ROOT).as_posix() for p in BASE.glob('*probes.json')]
    for path in paths:
        raw=(ROOT/path).read_bytes();sha=digest(raw);key='sha256/'+sha+'.response'
        for c in r['cases']:
            if c.get('candidate_path')==path and c['candidate_sha256']!=sha:raise ValueError('Changed candidate')
        (output/'objects'/key).write_bytes(raw);m['objects'][key]={'sha256':sha,'bytes':len(raw)}
    sql=(output/'load.sql').read_text().rsplit('COMMIT;',1)[0]
    for fid in ['TL-F-0029','TL-F-0022']:
        occurrence=digest(canonical([audit,fid,'/cases']).encode())
        sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(occurrence),literal(fid),literal(audit),jsql({'report_pointer':'/cases','county_audit_sha256':r['county_audit_sha256'],'scope':'Five held county zoning features; three proposed interpretations, none accepted'})])+') ON CONFLICT DO NOTHING;\n'
    event={k:v for k,v in plan.items() if k!='expected_event_id'}
    event['event_id']=digest(canonical([audit,event]).encode());event['evidence_refs']=['audit:'+audit+'#/cases','audit:'+audit+'#/proposed_combined_gap_area_m2']
    sql+='SELECT ingest.record_finding_event('+jsql(event)+','+literal(plan['expected_event_id'])+');\nCOMMIT;\n'
    (output/'load.sql').write_text(sql);(output/'manifest.json').write_text(json.dumps(m,sort_keys=True,indent=2)+'\n')
    (BASE/'archive-manifest.json').write_text(json.dumps(m,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'audit_sha256':audit,'event_id':event['event_id'],'objects':len(m['objects']),'observations':m['observations']}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);stage(p.parse_args().output)
