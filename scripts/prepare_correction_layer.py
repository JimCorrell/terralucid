#!/usr/bin/env python3
"""Prepare the bounded PR #7 correction layer; no network or database writes."""
import argparse
import json
from pathlib import Path
from prepare_source_staging import ROOT, canonical, digest, literal, jsql as sql_json
from prepare_bounded_ingestion import validate_capture

AUDIT = ROOT/'research/municipal-corroboration/report.json'
AUDIT_SHA = '6e08cd827867fbf816d94c82bd22b44d6889caf8936726f144bd00307de52e8f'
CAPTURE = ROOT/'research/conflict-investigation/2026-09-20'
ASSESSMENTS = ROOT/'research/conflict-investigation/relationships-2026-09-20'


def validate_proposal(p, feature, snapshot, assessments, assessment_snapshot):
    if p['source_snapshot_sha256'] != snapshot or p['source_feature_sha256'] != digest(canonical(feature).encode()):
        raise ValueError('Stale source feature or snapshot')
    if p['proposal_id'] != digest(canonical({k:v for k,v in p.items() if k!='proposal_id'}).encode()):
        raise ValueError('Proposal identity differs')
    for field, change in p['changes'].items():
        if field not in ('GEOCODE','STATE_ID') or feature['properties'].get(field)!=change['from']:
            raise ValueError('Unsupported field or changed raw value')
    target=p['assessment_candidate']
    if target:
        a=assessments[target['object_id']]
        if target['relationship_status']!='candidate_only' or target['source_snapshot_sha256']!=assessment_snapshot or target['source_feature_sha256']!=digest(canonical(a).encode()):
            raise ValueError('Stale assessment candidate')


def prepare(output, archive_prepared):
    report_bytes=AUDIT.read_bytes()
    if digest(report_bytes)!=AUDIT_SHA:raise ValueError('Reviewed audit changed; new review required')
    report=json.loads(report_bytes)
    for name,sha in report['inputs'].items():
        if digest((ROOT/name).read_bytes())!=sha:raise ValueError('Reviewed input changed: '+name)
    if digest((ROOT/report['method']).read_bytes())!=report['method_sha256']:raise ValueError('Reviewed method changed')
    _,capture_registry,records=validate_capture(CAPTURE)
    # PR #6 archived this capture under the combined registry and runs/spatial.
    # Capture-local observation IDs therefore differ from stored observation IDs.
    archived_registry='34bec3531a5aa0ee696d73973afe35befe8b6018b9340b5b7b73340b199b9fac'
    observation_ids={}
    for log in (CAPTURE/'runs').glob('*/results.json'):
        for entry in json.loads(log.read_bytes()):
            original=digest(canonical([capture_registry,log.parent.relative_to(CAPTURE).as_posix(),entry]).encode())
            observation_ids[original]=digest(canonical([archived_registry,'runs/spatial',entry]).encode())
    for record in records:record['observation_id']=observation_ids[record['observation_id']]
    _,_,related=validate_capture(ASSESSMENTS)
    snapshot=digest((CAPTURE/'batch.json').read_bytes())
    assessment_snapshot=digest((ASSESSMENTS/'batch.json').read_bytes())
    assessments={r['object_id']:r['raw_feature'] for r in related if r['source_id']=='organized-assessment'}
    proposals={p['object_id']:p for p in report['crosswalk']['proposals']}
    exceptions={e['object_id']:e['holds'] for e in report['crosswalk']['exceptions']}
    selected=[r for r in records if r['source_id']=='organized-parcels' and r['properties'].get('TOWN') in ('Sweden','Alfred')]
    if len(selected)!=2325 or len(proposals)!=2324 or len(exceptions)!=119:raise ValueError('Reviewed scope differs')
    sql=['BEGIN;','SET LOCAL standard_conforming_strings=on;']
    for r in selected:
        oid=r['object_id'];p=proposals.get(oid);feature=r['raw_feature'];holds=exceptions.get(oid,[])
        if p:
            validate_proposal(p,feature,snapshot,assessments,assessment_snapshot)
            if holds!=p['holds']:raise ValueError('Holds differ')
        elif holds!=['invalid_original_geometry']:raise ValueError('Unexpected excluded record')
        cid=digest(canonical([AUDIT_SHA,r['source_id'],snapshot,oid]).encode())
        values=[literal(cid),literal(AUDIT_SHA),literal(r['source_id']),literal(snapshot),str(oid),literal(r['observation_id']),literal(canonical(feature)),sql_json(p) if p else 'NULL',sql_json(holds)]
        # Compare existing rows on replay rather than silently ignoring collisions.
        sql.append('INSERT INTO ingest.correction_source(correction_id,audit_sha256,source_id,source_snapshot_sha256,object_id,observation_sha256,source_feature_text,proposal,holds) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;')
        sql.append('DO '+literal('BEGIN IF NOT EXISTS (SELECT 1 FROM ingest.correction_source WHERE correction_id='+literal(cid)+' AND source_feature_text='+literal(canonical(feature))+' AND proposal IS NOT DISTINCT FROM '+(sql_json(p) if p else 'NULL')+' AND holds='+sql_json(holds)+' AND observation_sha256='+literal(r['observation_id'])+') THEN RAISE EXCEPTION \'Correction replay differs\'; END IF; END')+';')
        if p:
            event={'correction_id':cid,'status':'accepted','actor':'TerraLucid correction-layer implementation',
                   'note':'User authorized correction layer after PR #7 merge. Accept reviewed historical GEOCODE/STATE_ID interpretation only; preserve holds, candidate-only relationships, original geometry and freshness finding TL-F-0024.'}
            event['event_id']=digest(canonical(event).encode())
            sql.append('SELECT ingest.record_correction_event('+sql_json(event)+',NULL);')
    sql.append('COMMIT;')
    # Reuse the already verified private archive. No new source acquisition.
    archived=archive_prepared/'manifest.json'
    manifest=json.loads(archived.read_bytes()) if archived.exists() else None
    if manifest is None:raise ValueError('Restore/reprepare municipal archive manifest before preparing this load')
    if manifest['objects'].get('sha256/'+AUDIT_SHA+'.response',{}).get('sha256')!=AUDIT_SHA:raise ValueError('Archive does not include reviewed report')
    output.mkdir(parents=True,exist_ok=False)
    (output/'load.sql').write_text('\n'.join(sql)+'\n')
    (output/'manifest.json').write_text(json.dumps({'objects':manifest['objects'],'audit_sha256':AUDIT_SHA,'records':2325,'accepted':2324,'held_records':119},indent=2)+'\n')
    print('Prepared 2,325 snapshot records, 2,324 acceptances, 119 records retaining holds')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--archive-prepared',required=True,type=Path)
    args=parser.parse_args();prepare(args.output,args.archive_prepared)
