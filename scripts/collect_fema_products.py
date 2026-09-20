#!/usr/bin/env python3
"""Capture selected FEMA products with a 60 MB cap; preserve exact returned bytes."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request,urlopen


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();probes=json.loads(a.manifest.read_bytes())
    ids=[r['id'] for r in probes]
    if len(set(ids))!=len(ids) or any(not re.fullmatch('[a-z0-9-]+',i) for i in ids):raise ValueError('Unsafe/duplicate ID')
    if any(not r['url'].startswith('https://msc.fema.gov/portal/downloadProduct?') for r in probes):raise ValueError('Only published MSC product downloads are supported')
    a.output.mkdir(parents=True,exist_ok=False);results=[]
    for probe in probes:
        record=dict(probe,retrieved_at=datetime.now(timezone.utc).isoformat())
        try:
            try:response=urlopen(Request(probe['url'],headers={'User-Agent':'TerraLucid municipal evidence review'}),timeout=60)
            except HTTPError as error:response=error
            with response:
                data=response.read(60_000_001)
                record.update(http_status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'))
            if len(data)>60_000_000:raise ValueError('Document exceeds 60 MB evidence cap')
            filename=probe['id']+'.response';(a.output/filename).write_bytes(data)
            record.update(response_file=filename,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),
                          status='NON_JSON_RESPONSE' if 200<=record['http_status']<300 else 'HTTP_ERROR',
                          pdf_signature=data.startswith(b'%PDF-'))
            if probe.get('format')=='pdf' and not record['pdf_signature'] and record['status']!='HTTP_ERROR':
                record['status']='UNEXPECTED_FORMAT'
        except Exception as error:
            record.update(status='REQUEST_FAILED',error=str(error))
        results.append(record)
        (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(probe['id'],record['status'],record.get('bytes'),flush=True)


if __name__=='__main__':main()
