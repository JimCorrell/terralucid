#!/usr/bin/env python3
"""Archive bounded public MSC catalog searches using its published read-only form."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL = 'https://msc.fema.gov/portal/advanceSearch'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();probes=json.loads(args.manifest.read_bytes())
    ids=[r['id'] for r in probes]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch('[a-z0-9-]+',i) for i in ids):
        raise ValueError('Unsafe or duplicate ID')
    if any(r['url']!=URL or r['post_form'].get('method')!='search' for r in probes):
        raise ValueError('Only public MSC catalog search is allowed')
    args.output.mkdir(parents=True,exist_ok=False);results=[]
    for probe in probes:
        r=dict(probe,request_method='POST',retrieved_at=datetime.now(timezone.utc).isoformat())
        try:
            request=Request(URL,data=urlencode(probe['post_form']).encode(),headers={
                'Content-Type':'application/x-www-form-urlencoded','User-Agent':'TerraLucid source qualification'})
            try:response=urlopen(request,timeout=60)
            except HTTPError as error:response=error
            with response:
                data=response.read(25000001)
                r.update(http_status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'))
            if len(data)>25000000:raise ValueError('Response exceeds 25 MB cap')
            filename=r['id']+'.response';(args.output/filename).write_bytes(data)
            r.update(response_file=filename,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
            try:
                payload=json.loads(data)
                r['status']='API_ERROR' if isinstance(payload,dict) and payload.get('error') else 'JSON_RECEIVED'
            except (ValueError,UnicodeDecodeError):r['status']='NON_JSON_RESPONSE'
            if not 200<=r['http_status']<300:r['status']='HTTP_ERROR'
        except Exception as error:r.update(status='REQUEST_FAILED',error=str(error))
        results.append(r);(args.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(r['id'],r['status'],r.get('bytes'),flush=True)


if __name__=='__main__':main()
