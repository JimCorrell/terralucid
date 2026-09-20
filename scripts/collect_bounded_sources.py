#!/usr/bin/env python3
"""Collect small, explicit source scopes with exact response and membership controls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 8_000_000


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def validate_ids(payload, expected_count, cap):
    if payload.get('error') or payload.get('exceededTransferLimit'):
        raise ValueError('ID query failed or was truncated')
    ids = payload.get('objectIds') or []
    if len(ids) != expected_count or len(set(ids)) != len(ids) or len(ids) > cap:
        raise ValueError('ID membership/count/cap check failed')
    if not all(isinstance(i, int) and i >= 0 for i in ids):
        raise ValueError('Unexpected object ID')
    return sorted(ids)


def validate_page(payload, expected_ids, geometry):
    if payload.get('error') or payload.get('exceededTransferLimit'):
        raise ValueError('Page failed or was truncated')
    if geometry:
        if payload.get('type') != 'FeatureCollection' or payload.get('crs') not in (
                None, {'type': 'name', 'properties': {'name': 'EPSG:4326'}}):
            raise ValueError('Unexpected GeoJSON/CRS')
        features = payload['features']
        properties = [f['properties'] for f in features]
    else:
        features = payload['features']
        properties = [f['attributes'] for f in features]
    ids = [p['OBJECTID'] for p in properties]
    if len(ids) != len(expected_ids) or set(ids) != set(expected_ids):
        raise ValueError('Missing, duplicate or unexpected page IDs')
    return features, properties


def collect(plan_path, output):
    plan = json.loads(plan_path.read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    run = output / 'runs' / 'bounded'
    run.mkdir(parents=True)
    log, snapshots, collected = [], [], {}

    def request(source, label, query=None):
        probe = source['id'] + '-' + label
        url = source['url'] + ('/query?' + urlencode(query) if query is not None else '?f=pjson')
        observation = {'id': probe, 'source_id': source['id'], 'url': url,
                       'purpose': 'Bounded source load: ' + label,
                       'retrieved_at': datetime.now(timezone.utc).isoformat()}
        try:
            with urlopen(Request(url, headers={'User-Agent': 'TerraLucid bounded source ingestion'}), timeout=45) as response:
                data = response.read(LIMIT + 1)
                observation.update(http_status=response.status, final_url=response.url)
            if len(data) > LIMIT:
                raise ValueError('Response exceeds bounded byte limit; choose smaller pages')
            filename = probe + '.response'
            (run / filename).write_bytes(data)
            observation.update(response_file=filename, sha256=checksum(data), bytes=len(data))
            payload = json.loads(data)
            observation['status'] = 'API_ERROR' if 'error' in payload else 'JSON_RECEIVED'
            if 'error' in payload:
                raise ValueError(str(payload['error']))
            return payload
        except Exception as error:
            observation.setdefault('status', 'REQUEST_FAILED')
            observation['error'] = str(error)
            raise
        finally:
            log.append(observation)
            (run / 'results.json').write_text(json.dumps(log, indent=2) + '\n')
            print(probe, observation['status'], flush=True)

    for source in plan['sources']:
        metadata = request(source, 'metadata-start')
        if not set(source['fields']).issubset({f['name'] for f in metadata['fields']}):
            raise ValueError('Requested field missing from current metadata')
        page_size = min(plan['page_size'], metadata['maxRecordCount'])
        if not 1 <= page_size <= 100:
            raise ValueError('Use an explicit page size between 1 and 100')
        if 'where' in source:
            predicates = [source['where']]
        else:
            keys = sorted({p['STATE_ID'] for p in collected[source['key_source']]
                           if p.get('STATE_ID') and p['STATE_ID'].strip()})
            predicates = ["STATE_ID IN (" + ','.join("'"+k.replace("'", "''")+"'" for k in keys[i:i+20]) + ')'
                          for i in range(0, len(keys), 20)]
        scope_ids, pages, properties = [], [], []
        for index, predicate in enumerate(predicates):
            base = {'f': 'json', 'where': predicate, 'returnGeometry': 'false'}
            total = request(source, f'count-{index}', dict(base, returnCountOnly='true'))['count']
            ids = validate_ids(request(source, f'ids-{index}', dict(base, returnIdsOnly='true')),
                               total, plan['max_records_per_source'])
            scope_ids.append(ids)
        all_ids = sorted({i for group in scope_ids for i in group})
        if len(all_ids) > plan['max_records_per_source']:
            raise ValueError('Combined source scope exceeds cap')
        for offset in range(0, len(all_ids), page_size):
            ids = all_ids[offset:offset+page_size]
            query = {'f': 'geojson' if source['geometry'] else 'json', 'where': '1=1',
                     'objectIds': ','.join(map(str, ids)), 'outFields': ','.join(source['fields']),
                     'returnGeometry': str(source['geometry']).lower(), 'orderByFields': 'OBJECTID'}
            if source['geometry']:
                query['outSR'] = 4326
            label = f'page-{offset//page_size}'
            data = request(source, label, query)
            _, attrs = validate_page(data, ids, source['geometry'])
            properties.extend(attrs)
            pages.append({'probe_id': source['id']+'-'+label, 'object_ids': ids})
        for index, predicate in enumerate(predicates):
            ids = request(source, f'ids-end-{index}', {'f': 'json', 'where': predicate,
                          'returnGeometry': 'false', 'returnIdsOnly': 'true'})
            if validate_ids(ids, len(scope_ids[index]), plan['max_records_per_source']) != scope_ids[index]:
                raise ValueError('Source membership changed during load')
        end = request(source, 'metadata-end')
        for field in ['fields', 'editingInfo', 'objectIdField', 'maxRecordCount']:
            if metadata.get(field) != end.get(field):
                raise ValueError('Source metadata changed during load')
        collected[source['id']] = properties
        snapshots.append({'source_id': source['id'], 'url': source['url'], 'geometry': source['geometry'],
                          'predicates': predicates, 'object_ids': all_ids, 'pages': pages,
                          'metadata_probe': source['id']+'-metadata-start',
                          'editing_info': metadata.get('editingInfo')})
    manifest = {'plan': plan, 'collector_sha256': checksum(Path(__file__).read_bytes()),
                'collected_at': datetime.now(timezone.utc).isoformat(), 'sources': snapshots,
                'controls': 'Start counts equal unique IDs; pages equal requested IDs; end IDs and metadata match. Not an atomic snapshot.'}
    (output / 'batch.json').write_text(json.dumps(manifest, indent=2) + '\n')
    old = json.loads((ROOT / 'research/maine-sources/registry.json').read_bytes())
    registry_sources = []
    for snapshot in snapshots:
        entry = next(s.copy() for s in old['sources'] if s['id'] == snapshot['source_id'])
        entry.update(probe_ids=[r['id'] for r in log if r['source_id'] == entry['id']],
                     coverage=f"{len(snapshot['object_ids'])} records in explicit bounded scope; see batch.json.",
                     access_status='query_tested', access='Bounded attribute/geometry extraction with membership reconciliation.')
        registry_sources.append(entry)
    (output / 'registry.json').write_text(json.dumps({'as_of':manifest['collected_at'], 'scope':plan['purpose'],
                                                     'sources':registry_sources}, indent=2)+'\n')
    print(json.dumps({s['source_id']:len(s['object_ids']) for s in snapshots}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    collect(args.plan,args.output)
