#!/usr/bin/env python3
"""Run bounded public source probes; save responses and an auditable run log.

Review the manifest before running. POST is used only for a USDA read query.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LIMIT = 2_000_000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path, help='New directory; refuses to overwrite a run')
    args = parser.parse_args()
    probes = json.loads(args.manifest.read_text())
    ids = [p['id'] for p in probes]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z0-9_-]+', i) for i in ids):
        parser.error('Probe IDs must be unique safe filenames')
    if any(not p['url'].startswith('https://') for p in probes):
        parser.error('Only public HTTPS requests are supported')
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for probe in probes:
        result = dict(probe, retrieved_at=datetime.now(timezone.utc).isoformat())
        try:
            headers = {'User-Agent': 'TerraLucid source research'}
            payload = None
            if 'post_json' in probe:
                headers['Content-Type'] = 'application/json'
                payload = json.dumps(probe['post_json']).encode()
            request = Request(probe['url'], data=payload, headers=headers)
            try:
                response = urlopen(request, timeout=25)
            except HTTPError as error:
                response = error
            with response:
                body = response.read(LIMIT + 1)
                result.update(http_status=response.status, final_url=response.url)
            if len(body) > LIMIT:
                raise ValueError('Response exceeds 2 MB research limit')
            result['sha256'] = hashlib.sha256(body).hexdigest()
            result['bytes'] = len(body)
            try:
                data = json.loads(body)
                result['status'] = 'JSON_RECEIVED'
                if isinstance(data, dict) and 'error' in data:
                    result.update(status='API_ERROR', api_error=data['error'])
            except (ValueError, UnicodeDecodeError):
                result['status'] = 'NON_JSON_RESPONSE'
            if not 200 <= result['http_status'] < 300:
                result['status'] = 'HTTP_ERROR'
            filename = probe['id'] + '.response'
            (args.output / filename).write_bytes(body)
            result['response_file'] = filename
        except (URLError, TimeoutError, OSError, ValueError) as error:
            result.update(status='REQUEST_FAILED', error=str(error))
        results.append(result)
        (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(probe['id'], result['status'], flush=True)


if __name__ == '__main__':
    main()
