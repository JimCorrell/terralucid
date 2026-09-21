#!/usr/bin/env python3
"""Capture the official Maine NWI package without extracting or modifying it."""
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'research/wetlands-classification'
URL = 'https://documentst.ecosphere.fws.gov/wetlands/data/State-Downloads/ME_geopackage_wetlands.zip'
CAP = 550_000_000
PART = 40_000_000


def main():
    path = BASE/'package/maine.zip.response'
    path.parent.mkdir(exist_ok=True)
    if path.exists(): raise ValueError('Capture already exists; preserve it')
    retrieved = datetime.now(timezone.utc).isoformat()
    h = hashlib.sha256(); size = 0
    with urllib.request.urlopen(URL,timeout=120) as r:
        headers = dict(r.headers); status = r.status; final_url = r.url
        if status != 200 or int(r.headers.get('Content-Length',CAP+1)) > CAP: raise ValueError('Unexpected status/size')
        with path.open('xb') as f:
            while True:
                data = r.read(1024*1024)
                if not data: break
                size += len(data)
                if size > CAP: raise ValueError('Response exceeds cap')
                h.update(data);f.write(data)
    if size != int(headers['Content-Length']): raise ValueError('Truncated package')
    parts = []
    with path.open('rb') as f:
        offset = 0
        while True:
            data = f.read(PART)
            if not data: break
            sha = hashlib.sha256(data).hexdigest()
            parts.append({'offset':offset,'bytes':len(data),'sha256':sha,'storage_object':'sha256/'+sha+'.response'});offset += len(data)
    log = {'url':URL,'retrieved_at':retrieved,'final_url':final_url,'http_status':status,'headers':headers,'bytes':size,'sha256':h.hexdigest(),'response_path':'package/maine.zip.response','parts':parts}
    (BASE/'package-capture.json').write_text(json.dumps(log,indent=2)+'\n')
    print(json.dumps({'bytes':size,'sha256':h.hexdigest(),'parts':len(parts)}))

if __name__ == '__main__': main()
