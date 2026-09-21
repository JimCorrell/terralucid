#!/usr/bin/env python3
"""Prepare authorized exact-version availability acceptance and bounded coverage."""
import argparse
import json
from pathlib import Path
from prepare_source_staging import ROOT, BUCKET, canonical, digest, literal, jsql, verify
from prepare_zoning_geometry import write_prepared

BASE = ROOT/'research/availability-acceptance'
METHOD = 'scripts/prepare_availability_acceptance.py'
MIGRATION = 'supabase/migrations/20260921010000_availability_acceptance.sql'
SOURCE = 'e1449e8384d5d712dfdae9df26814330d1b9f7dc31ae82fc8765bce565b61906'
PROPOSAL = '73a3f6899afdc374c273a2a69f4ef445926b02b4af6b73351cedfd12a5de7d66'
CANDIDATE = '173e3680d2a5474ec7ffbbe460206ddc90374fe21e37c4be3f46e915c0a6e836'
PAYLOAD = '434b6becc32ea018436807e4e0868710a86da372ac67524368cc1c464dc8b2b3'
SUBJECT_AUDIT = '2f106e1b19fa2b13415741a109d34f1f9dbc4fdb04cf67e77fe882325aebe5ff'
SUBJECT = '813824533f6c03c71fb8024431e0bd9f86e10b46c8e9ba12eb9c2ddf4d13696a'
CORRECTION = digest(canonical([SOURCE,PAYLOAD,PROPOSAL,CANDIDATE]).encode())
EVENT = {'event_id':digest(canonical([CORRECTION,'initial-acceptance']).encode()),'correction_id':CORRECTION,'status':'accepted','actor':'TerraLucid user-authorized availability activation','note':'User approved activation after merged PR #22. Accept only the reviewed exact-segment EPSG:3857 decode, retain DERIVED evidence, original archive, imagery-age and field/legal qualifications.'}


def build():
    inputs = {}
    def read(path,expected=None):
        data = (ROOT/path).read_bytes()
        if expected is not None and digest(data)!=expected:raise ValueError('Reviewed bytes changed: '+path)
        inputs[path]=digest(data);return data
    proposal = json.loads(read('research/wetlands-availability/report.json',PROPOSAL))
    candidate = read(proposal['candidate']['path'],CANDIDATE)
    subject = read('research/osborn-fema/runs/identity/osborn-jurisdiction.response',SUBJECT)
    read('research/osborn-wetlands/report.json',SOURCE)
    read('research/osborn-fema/report.json',SUBJECT_AUDIT)
    for path in [METHOD,MIGRATION,'scripts/prepare_source_staging.py','scripts/prepare_zoning_geometry.py']:read(path)
    report = {'evidence_state':'DERIVED','method':METHOD,'method_sha256':inputs[METHOD],'inputs':inputs,'source_audit_sha256':SOURCE,'proposal_audit_sha256':PROPOSAL,'source_payload_sha256':PAYLOAD,'candidate_sha256':CANDIDATE,'subject_audit_sha256':SUBJECT_AUDIT,'subject_payload_sha256':SUBJECT,'acceptance':EVENT,'limits':proposal['review'],
      'coverage':{'scope':'FEMA study boundary CID 230595, not a legal/surveyed parcel boundary','expected_digital_coverage':True,'computation':'PostGIS ST_Covers against accepted EPSG:3857 geometry; subject transformed from EPSG:4269; database stores runtime and event dependency.','state':'DERIVED','wetland_completeness':'UNKNOWN','present_day_conditions':'UNKNOWN','legal_applicability':'UNKNOWN','source_imagery':'May 1983; supplementation separately qualified'},
      'finding_reviews':[{'finding_id':'TL-F-0028','status':'resolved','priority':'medium','note':'User-authorized exact-version decode is accepted as DERIVED. Original bytes and proposal remain archived. A bounded Osborn Digital coverage result is computed by PostGIS, retaining the source, candidate, study boundary and acceptance event. Revocation blocks new coverage and marks existing results stale; reacceptance requires recomputation. This resolves this representation hold, not mapping completeness or legal wetlands.','next_action':'Use the exact accepted version and check coverage needs_revisit. Review new source versions separately. Keep imagery age, source completeness and legal applicability qualified.'},{'finding_id':'TL-F-0117','status':'in_progress','priority':'medium','note':'Availability interpretation activated and bounded Osborn coverage recorded with acceptance dependencies. TL-F-0028 is resolved for this exact representation; wider wetlands ingestion, package/service identity and projection, source-image age and field/legal applicability remain open.','next_action':'Qualify package/service identity and projection plus bounded feature ingestion before wider coverage. Preserve imagery age and wetland absence/legal-applicability unknowns.'}]}
    return report,candidate,subject


def prepare(output,current):
    report,candidate,subject=build();data=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();BASE.mkdir(exist_ok=True);(BASE/'report.json').write_bytes(data);sha=digest(data)
    registry=digest((ROOT/'research/wetlands-availability/registry.json').read_bytes());sql='BEGIN;\nSET LOCAL standard_conforming_strings=on;\n'
    values=[literal(sha),literal(registry),literal('DERIVED'),literal(METHOD),literal(report['method_sha256']),jsql(report),literal(BUCKET),literal('sha256/'+sha+'.response')]
    sql+='INSERT INTO ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
    values=[literal(CORRECTION),literal(SOURCE),literal(PROPOSAL),literal(PAYLOAD),literal(CANDIDATE),literal(candidate.decode()),literal('DERIVED'),jsql(report['limits'])]
    sql+='INSERT INTO ingest.availability_geometry(correction_id,source_audit_sha256,proposal_audit_sha256,source_payload_sha256,candidate_sha256,candidate_text,evidence_state,limits) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
    sql+='SELECT ingest.record_availability_event('+jsql(EVENT)+',NULL);\n'
    result_id=digest(canonical([sha,CORRECTION,EVENT['event_id'],SUBJECT]).encode())
    values=[literal(result_id),literal(sha),literal(CORRECTION),literal(EVENT['event_id']),literal(SUBJECT_AUDIT),literal(SUBJECT),literal(subject.decode()),literal(report['method_sha256']),"'{}'::jsonb"]
    sql+='INSERT INTO ingest.availability_coverage(result_id,audit_sha256,correction_id,geometry_event_id,subject_audit_sha256,subject_payload_sha256,subject_response_text,method_sha256,result) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
    rows={r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    for r in report['finding_reviews']:
        fid=r['finding_id'];eid=digest(canonical([fid,sha,'availability-accepted']).encode());event=dict(r,event_id=eid,actor='TerraLucid availability activation',evidence_refs=['audit:'+sha+'#/acceptance','audit:'+sha+'#/coverage'])
        sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(eid),literal(fid),literal(sha),jsql({'report_pointer':'/coverage'})])+') ON CONFLICT DO NOTHING;\n'
        sql+='SELECT ingest.record_finding_event('+jsql(event)+','+literal(rows[fid]['event_id'])+');\n'
    write_prepared(output,sql+'COMMIT;\n',[data]+[(ROOT/p).read_bytes() for p in report['inputs']])
    print(json.dumps({'audit_sha256':sha,'correction_id':CORRECTION,'event_id':EVENT['event_id'],'result_id':result_id}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--current',type=Path);p.add_argument('--verify-download',type=Path);a=p.parse_args()
    if a.verify_download:
        if not a.output:p.error('verification requires --output')
        print(verify(a.output,a.verify_download))
    else:
        if not a.output or not a.current:p.error('preparation requires --output and --current')
        prepare(a.output,a.current)
