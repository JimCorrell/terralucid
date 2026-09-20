#!/usr/bin/env python3
"""Prepare exact-version acceptance and recomputation; never connect to a database."""
import argparse
import json
from pathlib import Path
import shapely
import pyproj
from prepare_source_staging import ROOT, BUCKET, canonical, digest, literal, jsql
from prepare_zoning_ingestion import geometry_state, overlap_result
from prepare_bounded_ingestion import validate_capture

BASE = ROOT / 'research/zoning-geometry-correction'
PRIOR = '4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c'
PROPOSAL = '1c37372f5957128a95b3a9d25a7a43286423cbf1ed8831d70bd305b90d933067'
CANDIDATE = '95a8e3fe2fc8b4150bbcc8dee8ae1308afd198debfe40091673a8018335aabb2'
METHOD = 'scripts/prepare_zoning_geometry.py'
OID = 27232839
CORRECTION = digest(canonical([PRIOR, OID, PROPOSAL, CANDIDATE]).encode())
EVENT = dict(event_id=digest(canonical([CORRECTION, 'initial-acceptance']).encode()),
             correction_id=CORRECTION, status='accepted', actor='TerraLucid user-authorized geometry review',
             note='User authorized activation after merging PR #11. Accept only the reviewed shell/hole decoding of the exact original EPSG:4326 feature; retain DERIVED evidence and the projection/legal-currency caveats.')


def read_checked(path, expected):
    data = path.read_bytes()
    if digest(data) != expected:
        raise ValueError('Reviewed artifact changed: ' + str(path))
    return data


def proposal():
    path = ROOT / 'research/osborn-zoning-investigation'
    report = json.loads(read_checked(path / 'report.json', PROPOSAL))
    data = read_checked(path / 'candidate.geojson', CANDIDATE)
    return report, data


def write_prepared(output, sql, objects):
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'bucket': BUCKET, 'objects': {}}
    for data in objects:
        sha = digest(data); key = 'sha256/' + sha + '.response'
        target = output / 'objects' / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest['objects'][key] = {'sha256': sha, 'bytes': len(data)}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'load.sql').write_text(sql)


def acceptance(output):
    report, candidate = proposal()
    _, _, zones = validate_capture(ROOT / 'research/zoning-ingestion/capture')
    original = next(z['raw_feature'] for z in zones if z['object_id'] == OID)
    text = canonical(original)
    if digest(text.encode()) != report['source_comparison']['original_feature_sha256']:
        raise ValueError('Original feature changed')
    limits = {'projection': report['source_comparison']['projection_limit'],
              'legal_zoning_state': 'UNKNOWN', 'finding_id': 'TL-F-0025'}
    values = [literal(CORRECTION), literal(PRIOR), str(OID), literal(PROPOSAL), literal(text),
              literal(digest(text.encode())), literal(candidate.decode()), literal(CANDIDATE),
              literal('DERIVED'), jsql(limits)]
    sql = 'BEGIN;\nSET LOCAL standard_conforming_strings=on;\n'
    sql += 'INSERT INTO ingest.zoning_geometry_correction(correction_id,source_audit_sha256,object_id,proposal_audit_sha256,source_feature_text,source_feature_sha256,candidate_text,candidate_sha256,evidence_state,limits) VALUES (' + ','.join(values) + ') ON CONFLICT DO NOTHING;\n'
    sql += 'SELECT ingest.record_zoning_geometry_event(' + jsql(EVENT) + ',NULL);\nCOMMIT;\n'
    write_prepared(output, sql, [candidate, (ROOT/'research/osborn-zoning-investigation/report.json').read_bytes()])
    return {'correction_id': CORRECTION, 'event_id': EVENT['event_id']}


def export_document(path):
    data = json.loads(path.read_bytes())
    return data['rows'][0]['inputs'] if 'rows' in data else data


def evaluate(inputs):
    report, candidate_bytes = proposal()
    candidate = json.loads(candidate_bytes)
    read_checked(ROOT / 'research/zoning-ingestion/report.json', PRIOR)
    expected = {CORRECTION: {'event_id': EVENT['event_id'], 'status': 'accepted', 'candidate_sha256': CANDIDATE}}
    if inputs['source_audit_sha256'] != PRIOR or inputs['geometry_dependencies'] != expected:
        raise ValueError('This bounded recomputation requires the reviewed initial acceptance')
    _, _, original = validate_capture(ROOT / 'research/zoning-ingestion/capture')
    originals = {z['object_id']: z['raw_feature'] for z in original}
    if len(inputs['zones']) != len(originals) or {z['object_id'] for z in inputs['zones']} != set(originals):
        raise ValueError('Zoning membership changed')
    evaluated = []
    for z in inputs['zones']:
        oid = z['object_id']
        if z['raw_feature'] != originals[oid]:
            raise ValueError('Zoning source changed')
        geometry = candidate['geometry'] if oid == OID else originals[oid]['geometry']
        if z['effective_geojson'] != geometry:
            raise ValueError('Effective geometry differs from reviewed interpretation')
        if oid == OID and (z['correction_id'] != CORRECTION or z['geometry_event_id'] != EVENT['event_id'] or z['correction_status'] != 'accepted'):
            raise ValueError('Missing exact acceptance event')
        g, state, _ = geometry_state({'geometry': geometry})
        if state != z['effective_geometry_state']:
            raise ValueError('Database and local geometry validity differ')
        evaluated.append(({'object_id': oid, 'properties': z['raw_feature']['properties']}, g, state))
    prior = json.loads((ROOT/'research/zoning-ingestion/report.json').read_bytes())
    previous = {s['subject_id']: s for s in prior['screenings'] if s['result']['jurisdiction_code'] == '09230'}
    if len(inputs['subjects']) != 153 or {s['subject_id'] for s in inputs['subjects']} != set(previous):
        raise ValueError('Osborn subject membership changed')
    screenings = []
    changed_metrics = []
    for s in inputs['subjects']:
        old = previous[s['subject_id']]
        inp = s['input']
        if s['previous_result'] != old['result'] or digest(canonical(inp['raw_feature']).encode()) != old['source_feature_sha256']:
            raise ValueError('Original screening or input changed')
        result = overlap_result(inp['raw_feature'], evaluated, True)
        for key in ('jurisdiction_code', 'source_holds', 'source_quality_flags', 'related_finding_ids'):
            result[key] = s['previous_result'][key]
        result['geometry_correction_evidence_state'] = 'DERIVED'
        result['geometry_correction_limits'] = {CORRECTION: next(z['limits'] for z in inputs['zones'] if z['object_id'] == OID)}
        result['flags'].append('accepted_zoning_geometry_interpretation')
        if any(h['object_id'] == OID for h in result['intersections']):
            result['flags'].append('zoning_projection_difference_unresolved')
        keys = ('covered_fraction', 'intersection_area_sum_m2', 'intersections', 'boundary_touches')
        if any(result[k] != old['result'][k] for k in keys):
            changed_metrics.append({'subject_id': s['subject_id'],
                'previous_covered_fraction': old['result']['covered_fraction'],
                'new_covered_fraction': result['covered_fraction'],
                'new_target_intersections': [h for h in result['intersections'] if h['object_id'] == OID]})
        screenings.append({'subject_id': s['subject_id'], 'parent_audit_sha256': PRIOR,
            'geometry_dependencies': expected, 'source_feature_sha256': old['source_feature_sha256'], 'result': result})
    return screenings, changed_metrics


def recompute(export_path, output, current_path):
    inputs = export_document(export_path)
    screenings, changes = evaluate(inputs)
    dependencies = [METHOD, 'scripts/prepare_zoning_ingestion.py', 'scripts/prepare_source_staging.py',
        'scripts/prepare_bounded_ingestion.py', 'scripts/export_zoning_geometry.sql',
        'supabase/migrations/20260920060000_zoning_geometry_corrections.sql',
        'research/osborn-zoning-investigation/report.json', 'research/osborn-zoning-investigation/candidate.geojson',
        'research/zoning-ingestion/report.json', 'research/zoning-ingestion/capture/batch.json']
    input_bytes = (json.dumps(inputs, sort_keys=True, indent=2) + '\n').encode()
    (BASE/'analysis-inputs.json').write_bytes(input_bytes)
    dependencies.append('research/zoning-geometry-correction/analysis-inputs.json')
    report = {'evidence_state': 'DERIVED', 'method': METHOD, 'method_sha256': digest((ROOT/METHOD).read_bytes()),
        'source_audit_sha256': PRIOR, 'proposal_audit_sha256': PROPOSAL,
        'geometry_acceptance': EVENT, 'candidate_sha256': CANDIDATE,
        'inputs': {p: digest((ROOT/p).read_bytes()) for p in dependencies},
        'runtime': {'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
                    'pyproj': pyproj.__version__, 'proj': pyproj.proj_version_str},
        'summary': {'recomputed': len(screenings), 'other_screenings_retained': 2495,
            'intersection_rows': sum(len(s['result']['intersections']) for s in screenings),
            'usable_sources': sum(s['result']['status']=='observed_overlaps' for s in screenings),
            'invalid_assessment_sources': sum(s['result']['status']=='source_geometry_unusable' for s in screenings),
            'metric_changes': changes}, 'screenings': screenings,
        'limits': ['Original source geometries and prior results remain immutable.',
            'Accepted decoding is DERIVED, not a verified legal boundary; legal zoning remains UNKNOWN.',
            'Projection difference and legal-currency caveats persist. No native-coordinate substitution.',
            'The 153 Osborn revisions refresh collection-wide invalid-zone flags; only one record gains the target overlap.']}
    data = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()
    (BASE/'report.json').write_bytes(data); sha = digest(data)
    if output:
        registry_sha = digest((ROOT/'research/osborn-zoning-investigation/registry.json').read_bytes())
        sql = 'BEGIN;\nSET LOCAL standard_conforming_strings=on;\n'
        values = [literal(sha), literal(registry_sha), literal('DERIVED'), literal(METHOD), literal(report['method_sha256']),
                  jsql(report), literal(BUCKET), literal('sha256/'+sha+'.response')]
        sql += 'INSERT INTO ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
        by_id = {s['subject_id']: s for s in inputs['subjects']}
        for s in screenings:
            sql += 'INSERT INTO ingest.zoning_screening_revision(audit_sha256,parent_audit_sha256,subject_id,input,geometry_dependencies,result) VALUES ('+','.join([
                literal(sha), literal(PRIOR), literal(s['subject_id']), jsql(by_id[s['subject_id']]['input']),
                jsql(s['geometry_dependencies']), jsql(s['result'])])+') ON CONFLICT DO NOTHING;\n'
        old = next(r['event_id'] for r in json.loads(current_path.read_bytes())['rows'] if r['finding_id']=='TL-F-0025')
        event = {'event_id': digest(canonical(['TL-F-0025',sha,'accepted-recomputed']).encode()), 'finding_id':'TL-F-0025',
            'status':'in_progress','priority':'high','actor':'TerraLucid geometry correction activation',
            'next_action':'Reconcile the approximately one-metre native/export projection difference before precision-sensitive or native-coordinate use. Track legal currency separately with TL-F-0109.',
            'note':'The reviewed exact-version shell/hole interpretation is accepted as DERIVED. All 153 Osborn screenings were recomputed as immutable revisions using the accepted geometry; original sources and results remain. Projection and legal-currency caveats persist.',
            'evidence_refs':['audit:'+sha+'#/summary','audit:'+PROPOSAL+'#/proposal']}
        occurrence = digest(canonical(['TL-F-0025',sha,'accepted-recomputed']).encode())
        sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(occurrence),literal('TL-F-0025'),literal(sha),jsql({'report_pointer':'/summary'})])+') ON CONFLICT DO NOTHING;\n'
        sql += 'SELECT ingest.record_finding_event('+jsql(event)+','+literal(old)+');\nCOMMIT;\n'
        write_prepared(output, sql, [data]+[(ROOT/p).read_bytes() for p in dependencies])
    return {'audit_sha256':sha, **report['summary']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['accept','recompute']);p.add_argument('--output',type=Path)
    p.add_argument('--export',type=Path);p.add_argument('--current',type=Path)
    a=p.parse_args()
    if a.action=='accept' and not a.output:p.error('accept requires --output')
    if a.action=='recompute' and (not a.export or (a.output and not a.current)):p.error('recompute requires --export and --current when preparing a load')
    print(json.dumps(acceptance(a.output) if a.action=='accept' else recompute(a.export,a.output,a.current),indent=2))
