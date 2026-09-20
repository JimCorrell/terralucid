#!/usr/bin/env python3
"""Reconcile TL-F-0025 for one archived feature; never modify geometry or screening."""
import argparse
import json
import math
from pathlib import Path

import pyproj
from pyproj import Transformer
from pyproj.crs import CoordinateOperation
from pyproj.enums import TransformDirection
from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql

BASE = ROOT / 'research/osborn-projection'
METHOD = 'scripts/investigate_osborn_projection.py'
OID = 27232839


def require(condition, message):
    if not condition:
        raise ValueError(message)


def distances(a, b):
    require(len(a) == len(b) and bool(a), 'Unequal or empty coordinate sequences')
    values = [math.dist(x, y) for x, y in zip(a, b)]
    require(all(math.isfinite(v) for v in values), 'Nonfinite distance')
    return {'minimum_m': min(values), 'maximum_m': max(values)}


def build():
    evidence, payloads, inputs = {}, {}, {}
    for log in sorted((BASE / 'runs').glob('*/results.json')):
        for record in json.loads(log.read_bytes()):
            path = log.parent / record['response_file']
            data = path.read_bytes()
            require(digest(data) == record['sha256'] and len(data) == record['bytes']
                    and record['http_status'] == 200, 'Failed capture integrity')
            require(record['id'] not in payloads, 'Duplicate probe')
            evidence[log.parent.name + '/' + record['id']] = dict(
                record, response_path=path.relative_to(BASE).as_posix())
            payloads[record['id']] = data

    def dependency(relative, expected=None):
        data = (ROOT / relative).read_bytes()
        require(expected is None or digest(data) == expected, 'Changed dependency: ' + relative)
        inputs[relative] = digest(data)
        return json.loads(data)

    prior = dependency('research/osborn-zoning-investigation/report.json',
                       '1c37372f5957128a95b3a9d25a7a43286423cbf1ed8831d70bd305b90d933067')
    rings, attributes = {}, []
    for name, srid in [('native', 26919), ('nad83-geographic', 4269),
                       ('default-wgs84', 4326), ('explicit-1188', 4326),
                       ('explicit-1515', 4326), ('explicit-108190', 4326)]:
        response = json.loads(payloads[name])
        require(not response.get('error') and not response.get('exceededTransferLimit')
                and len(response.get('features', [])) == 1, 'Incomplete query: ' + name)
        feature = response['features'][0]
        require(response['spatialReference']['wkid'] == srid
                and feature['attributes']['OBJECTID'] == OID, 'Wrong CRS or feature')
        rr = feature['geometry']['rings']
        require(len(rr) == 1 and len(rr[0]) == 345 and rr[0][0] == rr[0][-1]
                and all(len(p) == 2 and all(math.isfinite(v) for v in p) for p in rr[0]),
                'Unexpected ring structure')
        rings[name] = rr[0]
        attributes.append(feature['attributes'])
    require(all(a == attributes[0] for a in attributes), 'Attribute drift')
    for name, old_id in [('native', 'native-rings'), ('default-wgs84', 'rings-4326')]:
        old = prior['evidence']['source/' + old_id]
        old_payload = dependency('research/osborn-zoning-investigation/' + old['response_path'], old['sha256'])
        require(old_payload['features'] == json.loads(payloads[name])['features'], 'Feature drift since PR11')
    meta = json.loads(payloads['layer-metadata'])
    service = json.loads(payloads['service-metadata'])
    require(meta == json.loads(payloads['layer-metadata-end']), 'Metadata changed during capture')
    require(meta['sourceSpatialReference']['wkid'] == 26919 and not meta.get('hasZ')
            and not meta.get('hasM') and meta['advancedQueryCapabilities']['supportsQueryWithDatumTransformation'],
            'Unsupported metadata')
    require(rings['default-wgs84'] == rings['explicit-108190'], 'Default no longer matches explicit 108190')

    native_to_nad = Transformer.from_crs(26919, 4269, always_xy=True)
    nad_to_native = Transformer.from_crs(4269, 26919, always_xy=True)
    default_to_native = Transformer.from_crs(4326, 26919, always_xy=True)
    operation = Transformer.from_pipeline('ESRI:108190')
    nad = [native_to_nad.transform(*p) for p in rings['native']]
    # Authority transformations have latitude/longitude axes; CRS transformers above use x/y.
    predicted, restored = [], []
    for lon, lat in nad:
        wlat, wlon = operation.transform(lat, lon, direction=TransformDirection.INVERSE)
        predicted.append((wlon, wlat))
    for lon, lat in rings['default-wgs84']:
        nlat, nlon = operation.transform(lat, lon)
        restored.append(nad_to_native.transform(nlon, nlat))
    projected = lambda points: [default_to_native.transform(*p) for p in points]
    comparisons = {
        'local_default_roundtrip_vs_native': distances(projected(rings['default-wgs84']), rings['native']),
        'explicit_108190_roundtrip_vs_native': distances(restored, rings['native']),
        'inverse_108190_prediction_vs_service': distances(projected(predicted), projected(rings['default-wgs84'])),
        'explicit_1188_vs_service_default': distances(projected(rings['explicit-1188']), projected(rings['default-wgs84'])),
        'explicit_1515_vs_service_default': distances(projected(rings['explicit-1515']), projected(rings['default-wgs84'])),
        'native_inverse_projection_vs_service_nad83': distances([nad_to_native.transform(*p) for p in nad],
                                                               [nad_to_native.transform(*p) for p in rings['nad83-geographic']]),
    }
    require(comparisons['explicit_108190_roundtrip_vs_native']['maximum_m'] < 0.000001
            and comparisons['inverse_108190_prediction_vs_service']['maximum_m'] < 0.000001,
            'Explicit operation does not reconcile coordinates')
    require(comparisons['local_default_roundtrip_vs_native']['minimum_m'] > 1
            and comparisons['explicit_1515_vs_service_default']['minimum_m'] > 0.001,
            'Discriminating controls no longer distinguish operations')
    operations = {}
    for authority, code in [('EPSG', '1188'), ('EPSG', '1515'), ('ESRI', '108190')]:
        op = CoordinateOperation.from_authority(authority, code)
        operations[authority + ':' + code] = {'name': op.name, 'projjson': op.to_json_dict(),
                                             'pipeline': op.to_proj4()}
    operations_path = BASE / 'operations.json'
    operations_path.write_text(json.dumps(operations, sort_keys=True, indent=2) + '\n')
    for path in (operations_path, BASE / 'probes.json', ROOT / 'scripts/collect_document_evidence.py',
                 ROOT / 'scripts/prepare_source_staging.py'):
        inputs[path.relative_to(ROOT).as_posix()] = digest(path.read_bytes())
    return {
        'evidence_state': 'DERIVED', 'method': METHOD, 'method_sha256': digest((ROOT / METHOD).read_bytes()),
        'scope': {'finding_id': 'TL-F-0025', 'object_id': OID, 'coordinate_occurrences': 345,
                  'coverage': 'One unchanged Osborn polygon, not statewide or other source versions.'},
        'runtime': {'pyproj': pyproj.__version__, 'proj': pyproj.proj_version_str,
                    'proj_database_sha256': digest((Path(pyproj.datadir.get_data_dir()) / 'proj.db').read_bytes())},
        'evidence': evidence, 'inputs': inputs, 'comparisons': comparisons,
        'observations': {'default_equals_explicit_108190_every_coordinate': True,
                         'unchanged_from_PR11': True, 'attributes_match': True,
                         'metadata_unchanged_during_capture': True,
                         'default_operation_declared_in_metadata': any(k in obj for obj in (meta, service)
                                                                     for k in ('datumTransformation', 'datumTransformations')),
                         'local_default_operation': default_to_native.get_last_used_operation().description},
        'conclusion': 'The observed service default is numerically equivalent to inverse ESRI:108190 (WGS_1984_(ITRF00)_To_NAD_1983). Local automatic EPSG:1188 uses a different datum operation, explaining the approximately 1.022 m discrepancy. Explicit service 108190 matches every default coordinate; 1188 and 1515 controls do not.',
        'limits': ['Numerical closure is not survey accuracy or independent positional verification.',
                   'Hidden server default configuration is not established; conclusion is based on observed output and explicit controls.',
                   'No geometry, screening, metric, acceptance event or global CRS policy changes. Historical unresolved-projection caveats remain immutable; consult this later review.',
                   'No claim of current legal zoning, title, access or buildability. TL-F-0109 remains separate.',
                   'New versions, precision-sensitive native-coordinate work and other datasets require explicit CRS operation qualification.'],
        'finding_review': {'finding_id': 'TL-F-0025', 'status': 'resolved', 'priority': 'medium',
                           'next_action': 'Reopen on changed source or contradictory evidence. Qualify and pin transformations before new native-coordinate or precision-sensitive analysis; retain TL-F-0109 legal-currency review.',
                           'note': 'PR12 accepted the segment-preserving ring interpretation. This review reconciles the remaining one-metre discrepancy using all 345 vertices and explicit service transformation controls. Resolution applies to this source version only; accepted geometry and all screening results remain unchanged.'}}


def prepare_load(report, output, current):
    prepare(BASE, output, BASE / 'report.json')
    manifest = json.loads((output / 'manifest.json').read_bytes())
    for relative, sha in report['inputs'].items():
        data = (ROOT / relative).read_bytes()
        require(digest(data) == sha, 'Changed input')
        key = 'sha256/' + sha + '.response'
        (output / 'objects' / key).write_bytes(data)
        manifest['objects'][key] = {'sha256': sha, 'bytes': len(data)}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    old = next(r['event_id'] for r in json.loads(current.read_bytes())['rows'] if r['finding_id'] == 'TL-F-0025')
    sha = digest((BASE / 'report.json').read_bytes())
    event = dict(report['finding_review'], actor='TerraLucid projection investigation',
                 event_id=digest(canonical(['TL-F-0025', sha, 'projection-review']).encode()),
                 evidence_refs=['audit:' + sha + '#/comparisons', 'audit:' + sha + '#/conclusion'])
    occurrence = digest(canonical(['TL-F-0025', sha, 'projection-investigation']).encode())
    sql = (output / 'load.sql').read_text().removesuffix('COMMIT;\n')
    sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES (' + ','.join([
        literal(occurrence), literal('TL-F-0025'), literal(sha),
        jsql({'report_pointer': '/comparisons', 'object_id': OID})]) + ') ON CONFLICT DO NOTHING;\n'
    sql += 'SELECT ingest.record_finding_event(' + jsql(event) + ',' + literal(old) + ');\nCOMMIT;\n'
    (output / 'load.sql').write_text(sql)
    print(json.dumps({'audit_sha256': sha, 'archive_objects': len(manifest['objects'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', type=Path)
    parser.add_argument('--current', type=Path)
    args = parser.parse_args()
    if args.prepare and not args.current:
        parser.error('--prepare requires --current')
    report = build()
    (BASE / 'report.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    if args.prepare:
        prepare_load(report, args.prepare, args.current)
    else:
        print(json.dumps(report['comparisons'], indent=2))
