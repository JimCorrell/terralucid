#!/usr/bin/env python3
"""Verify and reproduce both alternative windows without any network access."""
import argparse,json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from retrieve_terrain_area import retrieve
from investigate_terrain_readiness import sha


def run(evidence,output):
    report=json.loads((evidence/'report.json').read_text());manifest=json.loads((evidence/'sources.json').read_text())
    if sha(evidence/'sources.json')!=report['sources_sha256']:raise ValueError('Manifest changed')
    for e in manifest:
        if sha(evidence/e['file'])!=e['sha256']:raise ValueError('Source changed')
    class Replay:
        def get(self,url,name,headers=None,limit=None,expected_range=None):
            e=next(x for x in manifest if x['file']==name and x['url']==url)
            start,length=expected_range
            if not e['content_range'].startswith(f'bytes {start}-{start+length-1}/'):raise ValueError('Wrong range')
            if headers.get('If-Match') not in (None,e['etag']):raise ValueError('Wrong version')
            raw=(evidence/name).read_bytes()
            if len(raw)!=length or len(raw)>limit:raise ValueError('Wrong body length')
            return raw,e
    with tempfile.TemporaryDirectory() as temp,patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden')):
        for i,p in enumerate(report['projects']):
            expected=p['subset']
            actual=retrieve(Replay(),p['header'],expected['window'],f'{i}-pixels',Path(temp)/expected['subset_file'])
            if actual!=expected:raise ValueError('Subset/report replay mismatch')
    result={'status':'PASS','report_sha256':sha(evidence/'report.json'),'method_sha256':sha(__file__),
        'hashed_source_objects':len(manifest),'subsets_reproduced_exactly':len(report['projects']),'network_requests':0}
    output.write_text(json.dumps(result,indent=2)+'\n');print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence,a.output)
