"""Capture public USDA native geometry evidence once, preserving requests and hashes."""
import argparse, hashlib, json, math, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL='https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'

def capture(payload, output, name):
    response=output/(name+'.response'); manifest=output/(name+'-request.json')
    if response.exists() or manifest.exists():raise ValueError('Evidence already exists; choose a new destination')
    output.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    with urllib.request.urlopen(urllib.request.Request(URL,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=90) as r:raw=r.read()
    response.write_bytes(raw)
    manifest.write_text(json.dumps({'url':URL,'payload':payload,'retrieved_at':started,'sha256':hashlib.sha256(raw).hexdigest()},indent=2)+'\n')

def containment_query(controls):
    queries=[]
    for index,c in enumerate(controls):
        key=str(c['mupolygonkey']);x=float(c['x']);y=float(c['y'])
        if not key.isdigit() or not math.isfinite(x+y) or not (-180<=x<=180 and -90<=y<=90):raise ValueError('Invalid control')
        queries.append(f"SELECT {index} AS control_id,mupolygonkey,mupolygongeo.STContains(geometry::Point({x!r},{y!r},4326)) AS contains_point FROM mupolygon WHERE mupolygonkey={key}")
    if not queries:raise ValueError('No controls')
    return ' UNION ALL '.join(queries)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group(required=True);group.add_argument('--controls',type=Path);group.add_argument('--representation-request',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.controls:capture({'query':containment_query(json.loads(a.controls.read_bytes())),'format':'JSON+COLUMNNAME'},a.output,'native-containment')
    else:
        request=json.loads(a.representation_request.read_bytes())
        if request['url']!=URL:raise ValueError('Unexpected source URL')
        capture(request['payload'],a.output,'live-representations')
