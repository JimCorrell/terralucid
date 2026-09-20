#!/usr/bin/env python3
"""Reproduce the bounded TL-F-0025 investigation; propose, never accept, a decode."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import shapely
from shapely.geometry import LinearRing, Point, Polygon, mapping, shape
from shapely.ops import transform
from shapely.validation import explain_validity
import pyproj
from pyproj import Transformer

from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql

BASE = ROOT / 'research/osborn-zoning-investigation'
METHOD = 'scripts/investigate_osborn_zoning.py'
OID = 27232839
PRIOR_SHA = '4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c'


def edges(rings):
    """Undirected segment multiset; multiplicity matters, winding may differ."""
    return Counter(tuple(sorted((tuple(a), tuple(b))))
                   for ring in rings for a, b in zip(ring, ring[1:]))


def split_single_touch(ring):
    """Only a simple shell/hole touching at one repeated vertex is supported.

    No snapping, tolerance, polygonization, make_valid, or guessed hole deletion.
    Unsupported patterns fail closed. This is a proposal-specific interpretation,
    not a general geometry-repair function or an ingestion fallback.
    """
    if (len(ring) < 7 or ring[0] != ring[-1] or
            any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in ring)):
        raise ValueError('Expected a finite, closed 2D ring')
    if any(a == b for a, b in zip(ring, ring[1:])):
        raise ValueError('Consecutive duplicate vertices are unsupported')
    positions = defaultdict(list)
    for i, p in enumerate(ring[:-1]):
        positions[tuple(p)].append(i)
    repeated = [v for v in positions.values() if len(v) > 1]
    if len(repeated) != 1 or len(repeated[0]) != 2:
        raise ValueError('Expected exactly one twice-visited non-closure vertex')
    a, b = repeated[0]
    loops = [ring[a:b + 1], ring[b:] + ring[1:a + 1]]
    if any(len(r) < 4 for r in loops):
        raise ValueError('Degenerate loop')
    polygons = [Polygon(r) for r in loops]
    if any(not p.is_valid or p.area <= 0 for p in polygons):
        raise ValueError('Invalid component loop')
    if polygons[0].area < polygons[1].area:
        loops.reverse()
        polygons.reverse()
    shell, hole = polygons
    contact = shell.boundary.intersection(hole.boundary)
    if (not shell.covers(hole) or not contact.equals(Point(ring[a])) or
            LinearRing(loops[0]).is_ccw == LinearRing(loops[1]).is_ccw):
        raise ValueError('Not opposite-winding nested loops with one vertex contact')
    candidate = Polygon(loops[0], [loops[1]])
    if not candidate.is_valid or edges([ring]) != edges(loops):
        raise ValueError('Invalid assembly or changed boundary segments')
    return candidate, {
        'repeated_vertex': ring[a], 'zero_based_indices': [a, b],
        'input_coordinate_count_including_closure': len(ring),
        'shell_coordinate_count_including_closure': len(loops[0]),
        'hole_coordinate_count_including_closure': len(loops[1]),
        'shell_counterclockwise': LinearRing(loops[0]).is_ccw,
        'hole_counterclockwise': LinearRing(loops[1]).is_ccw,
        'boundary_contact_type': contact.geom_type,
        'all_segments_preserved_with_multiplicity': True,
        'candidate_valid': candidate.is_valid,
    }


def checked_bytes(path, expected=None):
    data = path.read_bytes()
    if expected is not None and digest(data) != expected:
        raise ValueError('Evidence checksum changed: ' + str(path))
    return data


def single_feature(payload, native=False):
    if payload.get('error') or payload.get('exceededTransferLimit') or len(payload.get('features', [])) != 1:
        raise ValueError('Missing, failed or incomplete single-feature response')
    f = payload['features'][0]
    if f['attributes' if native else 'properties']['OBJECTID'] != OID:
        raise ValueError('Unexpected feature')
    return f


def build():
    inputs = {}
    def input_bytes(relative, expected=None):
        data = checked_bytes(ROOT / relative, expected)
        inputs[relative] = digest(data)
        return data

    prior_path = 'research/zoning-ingestion/report.json'
    prior = json.loads(input_bytes(prior_path, PRIOR_SHA))
    prior_log_path = 'research/zoning-ingestion/capture/runs/bounded/results.json'
    prior_log = json.loads(input_bytes(prior_log_path))
    old_record = next(r for r in prior_log if r['id'] == 'lupc-zoning-page-1')
    old_path = 'research/zoning-ingestion/capture/runs/bounded/' + old_record['response_file']
    old_payload = json.loads(input_bytes(old_path, old_record['sha256']))
    old_feature = next(f for f in old_payload['features'] if f['properties']['OBJECTID'] == OID)
    evidence, payloads = {}, {}
    for log in sorted((BASE / 'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            path = log.parent / r['response_file']
            data = checked_bytes(path, r['sha256'])
            if len(data) != r['bytes'] or r['http_status'] != 200:
                raise ValueError('Failed evidence retrieval')
            evidence[log.parent.name + '/' + r['id']] = dict(r, response_path=path.relative_to(BASE).as_posix())
            payloads[r['id']] = data
    native = json.loads(payloads['native-rings'])
    geographic = json.loads(payloads['rings-4326'])
    exported = json.loads(payloads['geojson-recheck'])
    if native['spatialReference']['wkid'] != 26919 or geographic['spatialReference']['wkid'] != 4326:
        raise ValueError('Unexpected service CRS')
    if exported.get('crs') not in (None, {'type': 'name', 'properties': {'name': 'EPSG:4326'}}):
        raise ValueError('Unexpected GeoJSON CRS')
    nf = single_feature(native, True)
    gf = single_feature(geographic, True)
    ef = single_feature(exported)
    if nf['attributes'] != gf['attributes'] or nf['attributes'] != ef['properties'] or ef != old_feature:
        raise ValueError('Source drift: this proposal only applies to the unchanged reviewed feature')
    meta = json.loads(payloads['layer-metadata'])
    if meta['extent']['spatialReference']['wkid'] != 26919 or meta.get('hasZ') or meta.get('hasM'):
        raise ValueError('Unexpected layer CRS or dimensionality')
    for f in (nf, gf):
        if set(f['geometry']) != {'rings'} or len(f['geometry']['rings']) != 1:
            raise ValueError('Only one straight native ring supported')
    if ef['geometry']['type'] != 'Polygon' or len(ef['geometry']['coordinates']) != 1:
        raise ValueError('Unexpected original GeoJSON structure')
    nr, gr, er = nf['geometry']['rings'][0], gf['geometry']['rings'][0], ef['geometry']['coordinates'][0]
    if edges([gr]) != edges([er]):
        raise ValueError('GeoJSON and service geographic segments differ')
    nc, nd = split_single_touch(nr)
    gc, gd = split_single_touch(gr)
    ec, ed = split_single_touch(er)
    if nd['shell_counterclockwise'] or not nd['hole_counterclockwise'] or not gc.equals(ec):
        raise ValueError('Native ring roles do not corroborate the export interpretation')
    projector = Transformer.from_crs(4326, 26919, always_xy=True)
    projected = transform(projector.transform, ec)
    old_map = input_bytes('research/zoning-ingestion/runs/documents/osborn-official-map.response')
    review = json.loads(input_bytes('research/osborn-zoning-investigation/map-review.json'))
    if review['pdf_sha256'] != digest(payloads['osborn-official-map']):
        raise ValueError('Map review belongs to a different document')
    for relative in ('research/osborn-zoning-investigation/probes.json',
                     'scripts/collect_document_evidence.py', 'scripts/prepare_source_staging.py'):
        input_bytes(relative)
    affected = [dict(subject_id=s['subject_id'], source_feature_sha256=s['source_feature_sha256'],
                     basis='Original screening envelope candidate only; not a legal zoning assignment')
                for s in prior['screenings'] if OID in s['result'].get('invalid_zone_envelope_candidates', [])]
    candidate = {'type': 'Feature', 'properties': {
        'source_object_id': OID, 'source_feature_sha256': digest(canonical(old_feature).encode()),
        'prior_audit_sha256': PRIOR_SHA, 'status': 'proposed_not_accepted',
        'evidence_state': 'DERIVED', 'legal_zoning_state': 'UNKNOWN',
        'method': 'Split one self-touching ring into its existing shell and hole; preserve all segments.'},
        'geometry': mapping(ec)}
    candidate_bytes = (json.dumps(candidate, sort_keys=True, indent=2) + '\n').encode()
    (BASE / 'candidate.geojson').write_bytes(candidate_bytes)
    inputs['research/osborn-zoning-investigation/candidate.geojson'] = digest(candidate_bytes)
    report = {
        'evidence_state': 'DERIVED', 'method': METHOD,
        'method_sha256': digest((ROOT / METHOD).read_bytes()),
        'scope': {'finding_id': 'TL-F-0025', 'object_id': OID, 'map': 'osborn', 'prior_audit_sha256': PRIOR_SHA},
        'runtime': {'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
                    'pyproj': pyproj.__version__, 'proj': pyproj.proj_version_str},
        'evidence': evidence, 'inputs': inputs,
        'source_comparison': {
            'unchanged_entire_geojson_feature': True, 'all_attributes_match_across_formats': True,
            'native_crs': 'EPSG:26919', 'export_crs': 'EPSG:4326',
            'original_feature_sha256': digest(canonical(old_feature).encode()),
            'native_single_ring_geos_valid': Polygon(nr).is_valid,
            'native_geos_reason': explain_validity(Polygon(nr)),
            'export_geos_valid': shape(ef['geometry']).is_valid,
            'export_geos_reason': explain_validity(shape(ef['geometry'])),
            'native_diagnostics': nd, 'geographic_service_diagnostics': gd, 'geojson_diagnostics': ed,
            'native_shell_area_m2': Polygon(nc.exterior).area,
            'native_hole_area_m2': Polygon(nc.interiors[0]).area,
            'native_candidate_area_m2': nc.area,
            'publisher_shape_area_m2': nf['attributes']['Shape__Area'],
            'projected_geojson_candidate_area_m2': projected.area,
            'projection_hausdorff_distance_m': projected.hausdorff_distance(nc),
            'local_projection_operation': projector.get_last_used_operation().description,
            'projection_limit': 'About 1.02 m separates the service-native boundary and the locally projected geographic export. The service datum transformation has not been reconciled. The proposal preserves the original EPSG:4326 export exactly; it does not replace it with transformed native coordinates or claim cross-CRS coordinate equivalence.',
            'area_limit': 'Agreement with the publisher area is internal consistency, not independent legal-boundary verification.',
        },
        'format_interpretation': {
            'evidence_ref': 'source/esri-ring-specification',
            'observation': 'Esri permits vertex self-touching and prescribes even-odd display filling; native exteriors are clockwise and holes counterclockwise.',
            'conclusion': 'The native single ring has a vertex touch allowed by the documented Esri representation. Its unsplit GeoJSON ring is invalid under the GEOS checks used by this pilot. This is a representation compatibility issue, not proof that the publisher wetland boundary is wrong.',
            'supported_decode': 'Split only at the repeated vertex. The two simple loops have opposite winding; the exterior covers the hole and their boundaries share exactly that point. Every input segment and its multiplicity are retained.',
        },
        'map_evidence': dict(review, unchanged_from_prior_capture=old_map == payloads['osborn-official-map']),
        'proposal': {
            'status': 'proposed_not_accepted', 'evidence_state': 'DERIVED',
            'candidate_sha256': digest(candidate_bytes),
            'candidate_storage_object': 'sha256/' + digest(candidate_bytes) + '.response',
            'geometry_type': 'Polygon', 'shells': 1, 'holes': 1,
            'original_coordinate_and_segment_preservation': True,
            'legal_zoning_state': 'UNKNOWN',
            'acceptance_gate': 'Review and explicitly accept this exact-version alternate interpretation in a geometry correction layer, then recompute dependent screening as a new result version. No accepted geometry mechanism exists yet.',
        },
        'downstream': {'prior_envelope_candidates': affected, 'prior_results_changed': False,
                       'original_exclusion_retained': True,
                       'limit': 'No new parcel intersection, coverage, legal zoning or buildability result is adopted by this investigation.'},
        'finding_review': {
            'finding_id': 'TL-F-0025', 'status': 'in_progress', 'priority': 'high',
            'next_action': 'Review the proposed exact-version shell/hole decoding; if accepted, add geometry interpretation history and recompute affected zoning screening. Retain original exclusion until then.',
            'note': 'Native Esri rings and unchanged GeoJSON reveal one repeated vertex forming a shell and a touching hole. A valid alternate decode preserves every coordinate/segment and agrees with native ring roles. Official map supports regional P-WL2 context but cannot independently certify the point-touch topology or legal boundary. Proposal archived, not accepted; prior results unchanged.'},
    }
    return report


def prepare_load(report, output, current):
    # The shared preparer checks the report/method/source logs; archive dependencies too.
    for relative, sha in report['inputs'].items():
        checked_bytes(ROOT / relative, sha)
    prepare(BASE, output, BASE / 'report.json')
    manifest = json.loads((output / 'manifest.json').read_bytes())
    for relative, sha in report['inputs'].items():
        data = checked_bytes(ROOT / relative, sha)
        key = 'sha256/' + sha + '.response'
        (output / 'objects' / key).write_bytes(data)
        manifest['objects'][key] = {'sha256': sha, 'bytes': len(data)}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    rows = json.loads(current.read_bytes())['rows']
    old = next(r['event_id'] for r in rows if r['finding_id'] == 'TL-F-0025')
    sha = digest((BASE / 'report.json').read_bytes())
    event = dict(report['finding_review'], actor='TerraLucid Osborn geometry investigation',
                 event_id=digest(canonical(['TL-F-0025', sha, 'review']).encode()),
                 evidence_refs=['audit:' + sha + '#/proposal', 'audit:' + sha + '#/map_evidence'])
    occurrence = digest(canonical(['TL-F-0025', sha, 'geometry-investigation']).encode())
    sql = (output / 'load.sql').read_text().removesuffix('COMMIT;\n')
    sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES (' + ','.join([
        literal(occurrence), literal('TL-F-0025'), literal(sha),
        jsql({'report_pointer': '/proposal', 'object_id': OID})]) + ') ON CONFLICT DO NOTHING;\n'
    sql += 'SELECT ingest.record_finding_event(' + jsql(event) + ',' + literal(old) + ');\nCOMMIT;\n'
    (output / 'load.sql').write_text(sql)
    print(json.dumps({'audit_sha256': sha, 'objects': len(manifest['objects']),
                      'proposal': 'not accepted', 'finding_status': 'in_progress'}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare', type=Path)
    p.add_argument('--current', type=Path)
    args = p.parse_args()
    if args.prepare and not args.current:
        p.error('--prepare requires fresh --current finding state')
    report = build()
    (BASE / 'report.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    if args.prepare:
        prepare_load(report, args.prepare, args.current)
    else:
        print(json.dumps(report['source_comparison'], indent=2))
