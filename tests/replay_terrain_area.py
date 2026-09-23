#!/usr/bin/env python3
"""Reproduce a pilot subset using only hashed archived HTTP-range bodies."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from retrieve_terrain_area import retrieve
from investigate_terrain_readiness import sha


def replay(evidence, readiness, output):
    report=json.loads((evidence/'report.json').read_text())
    manifest=json.loads((evidence/'sources.json').read_text())
    if sha(evidence/'sources.json')!=report['sources_sha256']:raise ValueError('Manifest changed')
    if sha(readiness)!=report['readiness_sha256']:raise ValueError('Readiness changed')
    for e in manifest:
        if sha(evidence/e['file'])!=e['sha256']:raise ValueError('Source bytes changed')
    projects=json.loads(readiness.read_text())['projects']
    class Replay:
        def get(self,url,name,headers=None,limit=None,expected_range=None):
            e=next(e for e in manifest if e['file']==name and e['url']==url)
            start,length=expected_range
            if not e['content_range'].startswith(f'bytes {start}-{start+length-1}/'):raise ValueError('Range mismatch')
            if headers.get('If-Match') not in (None,e['etag']):raise ValueError('Version mismatch')
            raw=(evidence/name).read_bytes()
            if len(raw)!=length or len(raw)>limit:raise ValueError('Length mismatch')
            return raw,e
    with tempfile.TemporaryDirectory() as tmp,patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden during replay')):
        for i,expected in enumerate(report['sources']):
            source=next(p['raster'] for p in projects if p['representative_source_id']==expected['source_id'])
            actual=retrieve(Replay(),source,expected['window'],i,Path(tmp)/expected['subset_file'])
            if actual!=expected:raise ValueError('Replayed subset/report differs')
    result={'status':'PASS','report_sha256':sha(evidence/'report.json'),'replay_method_sha256':sha(__file__),
        'source_objects_hash_verified':len(manifest),'subsets_exactly_reproduced':len(report['sources']),'network_requests':0}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--readiness',type=Path,default=Path('research/terrain-readiness/report.json'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();replay(a.evidence,a.readiness,a.output)
