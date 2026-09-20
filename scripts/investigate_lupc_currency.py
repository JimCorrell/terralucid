#!/usr/bin/env python3
"""Reproduce bounded LUPC qualification evidence; no zoning or screening writes."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql

BASE = ROOT / 'research/lupc-currency'
METHOD = 'scripts/investigate_lupc_currency.py'
PRIOR = '4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c'


def require(value, message):
    if not value:
        raise ValueError(message)


def complete_features(payload):
    require(not payload.get('error') and not payload.get('exceededTransferLimit')
            and isinstance(payload.get('features'), list) and bool(payload['features']),
            'Failed, empty or incomplete feature response')
    return [f['attributes'] for f in payload['features']]


def index(rows, key):
    require(all(r.get(key) is not None for r in rows), 'Missing identifier')
    result = {r[key]: r for r in rows}
    require(len(result) == len(rows), 'Duplicate identifier')
    return result


def reconcile(ids, rows):
    require(not ids.get('error') and not ids.get('exceededTransferLimit')
            and isinstance(ids.get('objectIds'), list), 'Failed ID response')
    require(len(ids['objectIds']) == len(set(ids['objectIds']))
            and set(ids['objectIds']) == set(index(rows, 'OBJECTID')), 'Membership mismatch')
    require(all(r['MAP'] == 'osborn' for r in rows), 'Outside bounded map')


def build():
    inputs, evidence, payloads = {}, {}, {}
    def dependency(path, expected=None):
        data = (ROOT / path).read_bytes()
        require(expected is None or digest(data) == expected, 'Dependency drift: ' + path)
        inputs[path] = digest(data)
        return data
    for log in sorted((BASE / 'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            p = log.parent / r['response_file']
            data = p.read_bytes()
            require(digest(data) == r['sha256'] and len(data) == r['bytes']
                    and r['http_status'] == 200, 'Capture integrity failure')
            require(r['id'] not in payloads, 'Duplicate probe')
            evidence[log.parent.name + '/' + r['id']] = dict(r, response_path=p.relative_to(BASE).as_posix())
            payloads[r['id']] = data
    parsed = lambda name: json.loads(payloads[name])
    review = json.loads(dependency('research/lupc-currency/review.json'))
    for document in review['documents']:
        r = evidence[document['evidence_ref']]
        require(document['sha256'] == r['sha256'] and r['pdf_signature'], 'Review belongs to another PDF')
    for row in review['publication_observations'] + review['dependencies']:
        for ref in row.get('evidence_refs', [row.get('evidence_ref')]):
            require(ref in evidence, 'Unknown review evidence')
    pub = complete_features(parsed('published-attributes'))
    offline = complete_features(parsed('offline-attributes'))
    reconcile(parsed('published-ids'), pub)
    reconcile(parsed('offline-ids'), offline)
    pg, og = index(pub, 'GlobalID'), index(offline, 'GlobalID')
    require(set(pg) == set(og) and len(pg) == 383, 'Changed cross-service membership')
    common = set(pub[0]) & set(offline[0]) - {'OBJECTID'}
    require(all(set(r) == set(pub[0]) for r in pub)
            and all(set(r) == set(offline[0]) for r in offline), 'Nonuniform fields')
    differences = Counter(k for gid in pg for k in common if pg[gid][k] != og[gid][k])
    require(not differences, 'Published/offline common attributes differ')
    prior = json.loads(dependency('research/zoning-ingestion/report.json', PRIOR))
    logpath = 'research/zoning-ingestion/capture/runs/bounded/results.json'
    logs = json.loads(dependency(logpath))
    original_rows = []
    for old in logs:
        if not old['id'].startswith('lupc-zoning-page-'):
            continue
        old_data = json.loads(dependency('research/zoning-ingestion/capture/runs/bounded/' + old['response_file'], old['sha256']))
        require(not old_data.get('error'), 'Failed old capture')
        original_rows.extend(f['properties'] for f in old_data['features'])
    original = index(original_rows, 'OBJECTID')
    require(original == index(offline, 'OBJECTID'), 'Offline attributes changed since ingestion')
    maps = complete_features(parsed('map-record'))
    require(len(maps) == 1 and maps[0]['MAP'] == 'osborn', 'Ambiguous map record')
    m = maps[0]
    old_map = prior['evidence']['documents/osborn-official-map']['sha256']
    require(digest(payloads['osborn-map']) == old_map, 'Map changed; manual re-review required')
    updates = complete_features(parsed('update-records'))
    require(len(updates) == 1 and updates[0]['DATA_LAYER'] == 'Zones', 'Unexpected update records')
    error = parsed('download-service').get('error')
    require(error and error['code'] == 499, 'Download access changed; review required')
    publication = payloads['publication'].decode()
    require('attributes.last_edited_date_text' in publication
            and 'may be out of step briefly' in publication, 'Publication semantics changed')
    for path in ['research/lupc-currency/probes.json', 'research/lupc-currency/followup.json',
                 'scripts/collect_document_evidence.py', 'scripts/prepare_source_staging.py']:
        dependency(path)
    def dates(rows, field):
        return [{'raw_milliseconds': raw, 'utc': None if raw is None else datetime.fromtimestamp(raw / 1000, timezone.utc).isoformat(), 'count': count}
                for raw, count in sorted(Counter(r[field] for r in rows).items(), key=lambda kv: str(kv[0]))]
    return {
        'evidence_state': 'DERIVED', 'method': METHOD, 'method_sha256': digest((ROOT / METHOD).read_bytes()),
        'scope': review['scope'], 'evidence': evidence, 'inputs': inputs,
        'attribute_comparison': {'records_each_service': len(pub), 'membership_reconciled_against_ids': True,
            'unique_GlobalID_sets_equal': True, 'common_fields_compared': sorted(common),
            'different_OBJECTID_count': sum(pg[k]['OBJECTID'] != og[k]['OBJECTID'] for k in pg),
            'noncomparable_fields': {'published_only': sorted(set(pub[0])-set(offline[0])),
                                     'offline_only': sorted(set(offline[0])-set(pub[0]))},
            'matching_common_attributes': True, 'offline_attributes_identical_to_ingested_snapshot': True,
            'geometry_comparison': 'Not performed: queries intentionally omit geometry; identity/attribute reconciliation does not establish geometric equality or legal currency.',
            'flags': {k: dict(Counter(str(r[k]) for r in offline)) for k in ['PUBLISH','DRAW','END_DATE']},
            'date_histograms': {k: dates(offline,k) for k in ['START_DATE','last_edited_date']}},
        'publication_dates': {'map_unchanged_from_ingestion': True,
            'map_dates': {k: {'raw_milliseconds':m[k], 'utc':None if m[k] is None else datetime.fromtimestamp(m[k]/1000,timezone.utc).isoformat()}
                          for k in ['ADOPT_DATE','EFFECTIVE_DATE','AMEND_DATE','last_edited_date','FEMA_Effective_Date']},
            'displayed_update_date': m['last_edited_date_text'],
            'service_update_label': {k:updates[0][k] for k in ['DATA_LAYER','UPDATE_DATE','UPDATE_TEXT']},
            'rule_revision_date': '2026-04-06',
            'interpretation': 'Initial effective/amend fields, per-map display/edit time, service-wide update label, rule edition and FEMA adoption date are different clocks. None certifies all current legal amendments or a parcel zone.'},
        'document_review': review, 'download_access': {'http_status':200,'application_error':error},
        'qualification': {'legal_current_selection':'UNKNOWN','complete_regulatory_coverage':'UNKNOWN',
                          'redistribution_permission':'UNKNOWN','screening_only':True,
                          'geometry_or_screening_changes':False},
        'finding_review': review['finding_review']}


def prepare_load(report, output, current):
    prepare(BASE, output, BASE / 'report.json')
    manifest = json.loads((output / 'manifest.json').read_bytes())
    for path, sha in report['inputs'].items():
        data = (ROOT / path).read_bytes()
        require(digest(data) == sha, 'Changed input')
        key = 'sha256/' + sha + '.response'
        (output / 'objects' / key).write_bytes(data)
        manifest['objects'][key] = {'sha256':sha,'bytes':len(data)}
    (output / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    old = next(r['event_id'] for r in json.loads(current.read_bytes())['rows'] if r['finding_id']=='TL-F-0109')
    sha = digest((BASE/'report.json').read_bytes())
    event = dict(report['finding_review'], actor='TerraLucid LUPC qualification review',
                 event_id=digest(canonical(['TL-F-0109',sha,'currency-review']).encode()),
                 evidence_refs=['audit:'+sha+'#/publication_dates','audit:'+sha+'#/document_review'])
    occurrence = digest(canonical(['TL-F-0109',sha,'currency-investigation']).encode())
    sql = (output/'load.sql').read_text().removesuffix('COMMIT;\n')
    sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([
        literal(occurrence),literal('TL-F-0109'),literal(sha),jsql({'report_pointer':'/document_review','map':'osborn'})])+') ON CONFLICT DO NOTHING;\n'
    sql += 'SELECT ingest.record_finding_event('+jsql(event)+','+literal(old)+');\nCOMMIT;\n'
    (output/'load.sql').write_text(sql)
    print(json.dumps({'audit_sha256':sha,'archive_objects':len(manifest['objects'])}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path)
    args=p.parse_args()
    if args.prepare and not args.current:p.error('--prepare requires --current')
    report=build()
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    if args.prepare:prepare_load(report,args.prepare,args.current)
    else:print(json.dumps({'records':report['attribute_comparison']['records_each_service'],'qualification':report['qualification']}))
