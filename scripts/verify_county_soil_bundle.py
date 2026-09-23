"""Verify private bundle bytes and every prepared row against archived source rows."""
import argparse,json,hashlib
from collections import Counter
from functools import lru_cache
from pathlib import Path
from collect_county_soils import rows

def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def verify(root):
    manifest=json.loads((root/'manifest.json').read_bytes())
    for key,value in manifest['objects'].items():
        if len(key)!=64 or any(c not in '0123456789abcdef' for c in key):raise ValueError('Invalid object key')
        path=root/'objects'/key
        if path.stat().st_size!=value['bytes'] or file_sha(path)!=key:raise ValueError('Archive checksum mismatch')
    for name,key in [('records.jsonl','records_sha256'),('report.json','report_sha256')]:
        if file_sha(root/name)!=manifest[key]:raise ValueError('Bundle checksum mismatch: '+name)
    report=json.loads((root/'report.json').read_bytes())
    if report['method_sha256'] not in manifest['objects']:raise ValueError('Missing preparation method archive')
    @lru_cache(maxsize=4)
    def source_rows(key):
        if key not in manifest['objects']:raise ValueError('Missing source response')
        return rows(json.loads((root/'objects'/key).read_bytes()))
    seen=set();counts=Counter();keys={'legend':'lkey','mapunit':'mukey','component':'cokey','chorizon':'chkey','mupolygon':'mupolygonkey'}
    with (root/'records.jsonl').open() as source:
        for line in source:
            r=json.loads(line);identity=(r['kind'],r['source_key'])
            if identity in seen:raise ValueError('Duplicate prepared identity')
            seen.add(identity);counts[r['kind']]+=1
            provenance=r['provenance'];ordinal=provenance['row_ordinal']
            if type(ordinal)!=int or ordinal<0:raise ValueError('Invalid source row ordinal')
            if source_rows(provenance['response_sha256'])[ordinal]!=r['raw']:raise ValueError('Prepared source row differs')
            if r['raw'][keys[r['kind']]]!=r['source_key']:raise ValueError('Prepared key differs')
            if r['kind']=='mupolygon':
                if bool(r['hold'])!=(r['geometry_wkb'] is None) or bool(r['hold'])!=(r['scope_relation']=='held'):raise ValueError('Hold/geometry mismatch')
    if len(seen)!=manifest['records'] or any(counts[k]!=report['counts'][k] for k in keys):raise ValueError('Record counts differ')
    return {'status':'PASS','records_verified':len(seen),'objects_verified':len(manifest['objects']),
            'report_sha256':manifest['report_sha256'],'records_sha256':manifest['records_sha256']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);a=p.parse_args();print(json.dumps(verify(a.bundle),indent=2))
