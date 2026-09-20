#!/usr/bin/env python3
"""Prepare the committed research audit for Supabase; never connect or upload.

Usage: python3 scripts/prepare_source_staging.py prepare --output .local/source-load
       python3 scripts/prepare_source_staging.py verify --output .local/source-load --download DIRECTORY
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'research/maine-sources'
BUCKET = 'terralucid-source-snapshots'
GEOMETRY_PROBES = {'ut-parcels-geometry', 'organized-parcels-geometry', 'lupc-zones-geometry'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def literal(value):
    if '\x00' in value:
        raise ValueError('PostgreSQL text cannot contain NUL')
    return "'" + value.replace("'", "''") + "'"


def jsql(value):
    return literal(canonical(value)) + '::jsonb'


def prepare(audit, output):
    # Validate everything in memory before producing a load file.
    objects = {}

    def archive(data):
        sha = digest(data)
        key = f'sha256/{sha}.response'
        objects[key] = data
        return sha, key

    registry_bytes = (audit / 'registry.json').read_bytes()
    registry = json.loads(registry_bytes)
    registry_sha, registry_key = archive(registry_bytes)
    source_ids = [s['id'] for s in registry['sources']]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError('Duplicate source IDs')
    probes = {}
    for source in registry['sources']:
        for probe in source.get('probe_ids', []):
            probes.setdefault(probe, []).append(source['id'])
    sql = ['BEGIN;', 'SET LOCAL standard_conforming_strings = on;']
    sql.append('INSERT INTO ingest.registry_snapshot '
               '(sha256,byte_count,document,storage_bucket,storage_object) VALUES (' +
               ','.join([literal(registry_sha), str(len(registry_bytes)), jsql(registry),
                         literal(BUCKET), literal(registry_key)]) + ') ON CONFLICT DO NOTHING;')
    observations = 0
    geometries = 0
    outcomes = {}
    seen = set()
    for result_file in sorted((audit / 'runs').glob('*/results.json')):
        archive(result_file.read_bytes())
        run_path = result_file.parent.relative_to(audit).as_posix()
        for record in json.loads(result_file.read_bytes()):
            probe = record['id']
            if (run_path, probe) in seen:
                raise ValueError(f'Duplicate probe in run: {probe}')
            seen.add((run_path, probe))
            if probe not in probes:
                raise ValueError(f'Unmapped probe: {probe}')
            filename = record['response_file']
            if Path(filename).name != filename:
                raise ValueError('Response file must be a basename')
            data = (result_file.parent / filename).read_bytes()
            if digest(data) != record['sha256'] or len(data) != record['bytes']:
                raise ValueError(f'Checksum or byte count mismatch: {filename}')
            payload_sha, key = archive(data)
            observation_sha = digest(canonical([registry_sha, run_path, record]).encode())
            values = [literal(observation_sha), literal(registry_sha), literal(run_path),
                      literal(probe), 'ARRAY[' + ','.join(map(literal, sorted(probes[probe]))) + ']::text[]',
                      literal(record['retrieved_at']), str(int(record['http_status'])),
                      literal(record['status']), jsql(record), literal(payload_sha),
                      str(len(data)), literal(BUCKET), literal(key)]
            sql.append('INSERT INTO ingest.source_response '
                       '(observation_sha256,registry_sha256,run_path,probe_id,source_ids,retrieved_at,'
                       'http_status,outcome,retrieval_log,payload_sha256,byte_count,storage_bucket,storage_object) VALUES (' +
                       ','.join(values) + ') ON CONFLICT DO NOTHING;')
            observations += 1
            outcomes[record['status']] = outcomes.get(record['status'], 0) + 1
            if probe in GEOMETRY_PROBES:
                query = parse_qs(urlparse(record['url']).query)
                if query.get('outSR') != ['4326'] or record['status'] != 'JSON_RECEIVED':
                    raise ValueError(f'Unexpected geometry CRS/outcome: {probe}')
                payload = json.loads(data)
                crs = payload.get('crs')
                if payload.get('type') != 'FeatureCollection' or crs not in (
                    None, {'type': 'name', 'properties': {'name': 'EPSG:4326'}}
                ):
                    raise ValueError(f'Unexpected GeoJSON or CRS override: {probe}')
                for ordinal, feature in enumerate(payload['features']):
                    if feature.get('type') != 'Feature' or not feature.get('geometry'):
                        raise ValueError(f'Missing geometry: {probe}')
                    sql.append('INSERT INTO ingest.geometry_sample '
                               '(observation_sha256,feature_ordinal,raw_feature,geometry,transformation) VALUES (' +
                               ','.join([literal(observation_sha), str(ordinal), jsql(feature),
                                         'extensions.ST_GeomFromGeoJSON(' + literal(canonical(feature['geometry'])) + ')',
                                         literal('GeoJSON geometry decoded; requested outSR=4326; no repair')]) +
                               ') ON CONFLICT DO NOTHING;')
                    geometries += 1
    if not observations:
        raise ValueError('No recorded responses found')
    sql.append('COMMIT;')
    manifest = {'bucket': BUCKET, 'registry_sha256': registry_sha,
                'sources': len(source_ids), 'observations': observations,
                'geometry_samples': geometries, 'outcomes': outcomes,
                'objects': {key: {'sha256': digest(data), 'bytes': len(data)}
                            for key, data in sorted(objects.items())}}
    # A fresh destination prevents stale files from entering a later upload.
    output.mkdir(parents=True, exist_ok=False)
    for key, data in objects.items():
        target = output / 'objects' / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (output / 'load.sql').write_text('\n'.join(sql) + '\n')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return {k: v for k, v in manifest.items() if k != 'objects'} | {'objects': len(objects)}


def verify(output, downloaded):
    manifest = json.loads((output / 'manifest.json').read_text())
    for key, expected in manifest['objects'].items():
        data = (downloaded / key).read_bytes()
        if digest(data) != expected['sha256'] or len(data) != expected['bytes']:
            raise ValueError(f'Stored object differs: {key}')
    return {'verified_objects': len(manifest['objects'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'verify'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download', type=Path)
    args = parser.parse_args()
    if args.action == 'verify' and args.download is None:
        parser.error('--download is required for verify')
    result = prepare(AUDIT, args.output) if args.action == 'prepare' else verify(args.output, args.download)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
