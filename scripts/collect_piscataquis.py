#!/usr/bin/env python3
"""Capture native county-envelope sources, retaining membership/metadata controls.

County boundary is a DERIVED union of all civil polygons with COUNTY=Piscataquis.
Envelope capture is deliberately broader; exact county membership is evaluated later.
Existing successful responses may be resumed, never overwritten. End controls must pass.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from shapely.ops import unary_union
from investigate_osborn_wetlands import decode
from prepare_source_staging import ROOT, digest

BASE=ROOT/'research/piscataquis-ingestion'
RUN=BASE/'runs/capture'
LIMIT=25_000_000


def collect():
    RUN.mkdir(parents=True,exist_ok=True)
    logpath=RUN/'results.json'
    log=json.loads(logpath.read_bytes()) if logpath.exists() else []
    lookup={r['id']:r for r in log}; log_lock=Lock()
    registry=json.loads((ROOT/'research/maine-sources/registry.json').read_bytes())
    source_lookup={s['id']:s for s in registry['sources']}
    def request(sid,label,params=None):
        pid=sid+'-'+label
        url=source_lookup[sid]['source_urls'][0]+('/query?' + urlencode(params) if params is not None else '?f=pjson')
        if pid in lookup:
            r=lookup[pid]; data=(RUN/r['response_file']).read_bytes()
            if r['url']!=url or digest(data)!=r['sha256'] or len(data)!=r['bytes']:raise ValueError('Changed resumed request')
        else:
            with urlopen(Request(url,headers={'User-Agent':'TerraLucid county source audit'}),timeout=120) as response:
                data=response.read(LIMIT+1); status=response.status; final=response.url
            if len(data)>LIMIT:raise ValueError('Response cap exceeded; reduce page size')
            d=json.loads(data)
            if status!=200 or d.get('error') or d.get('exceededTransferLimit'):raise ValueError(str(d)[:200])
            r={'id':pid,'source_id':sid,'url':url,'purpose':'County source capture: '+label,'retrieved_at':datetime.now(timezone.utc).isoformat(),
               'http_status':status,'final_url':final,'response_file':pid+'.response','sha256':digest(data),'bytes':len(data),'status':'JSON_RECEIVED'}
            (RUN/r['response_file']).write_bytes(data)
            with log_lock:
                log.append(r);lookup[pid]=r
                logpath.write_text(json.dumps(log,indent=2)+'\n')
            print(pid,len(data),flush=True)
        d=json.loads(data)
        if d.get('error') or d.get('exceededTransferLimit'):raise ValueError('Incomplete request')
        return d
    def capture(sid,selectors,fields):
        meta=request(sid,'metadata-start')
        sr=meta['extent']['spatialReference'];srid=sr.get('latestWkid',sr['wkid'])
        if srid!=26919:raise ValueError('Changed native CRS')
        if not set(fields).issubset({f['name'] for f in meta['fields']}):raise ValueError('Missing fields')
        groups=[]
        def get_members(item):
            i,sel=item
            q=dict(sel,f='json',returnGeometry='false')
            count=request(sid,f'count-{i}',dict(q,returnCountOnly='true'))['count']
            ids=request(sid,f'ids-{i}',dict(q,returnIdsOnly='true'))['objectIds'] or []
            if len(ids)!=count or len(set(ids))!=count or count>100000:raise ValueError('Membership/count/cap mismatch')
            return sorted(ids)
        with ThreadPoolExecutor(max_workers=4) as pool:
            groups=list(pool.map(get_members,enumerate(selectors)))
        members=sorted(set().union(*map(set,groups))); features=[];pages=[]
        def get_page(offset):
            ids=members[offset:offset+100]; label=f'page-{offset//100}'
            d=request(sid,label,{'f':'json','objectIds':','.join(map(str,ids)),'outFields':','.join(fields),'returnGeometry':'true','outSR':26919})
            psr=d['spatialReference']
            if psr.get('latestWkid',psr['wkid'])!=26919:raise ValueError('Page CRS changed')
            rows=d['features'];actual=[r['attributes']['OBJECTID'] for r in rows]
            if sorted(actual)!=ids:raise ValueError('Missing/duplicate/unexpected page IDs')
            return rows,{'probe_id':sid+'-'+label,'object_ids':ids}
        with ThreadPoolExecutor(max_workers=4) as pool:
            for rows,page in pool.map(get_page,range(0,len(members),100)):
                features.extend(rows);pages.append(page)
        def check_end(item):
            i,sel=item
            end=request(sid,f'ids-end-{i}',dict(sel,f='json',returnIdsOnly='true',returnGeometry='false'))['objectIds'] or []
            if sorted(end)!=groups[i]:raise ValueError('Membership changed during capture')
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(check_end,enumerate(selectors)))
        end=request(sid,'metadata-end')
        for key in ['fields','editingInfo','extent','sourceSpatialReference','objectIdField','maxRecordCount']:
            if meta.get(key)!=end.get(key):raise ValueError('Metadata changed during capture')
        return {'source_id':sid,'srid':srid,'selectors':selectors,'selector_ids':groups,'object_ids':members,'pages':pages,'editing_info':meta.get('editingInfo')}, features
    civil_fields=[f['name'] for f in json.loads((BASE/'runs/discovery/civil-boundaries-metadata.response').read_bytes())['fields']]
    civil,rows=capture('civil-boundaries',[{'where':"COUNTY = 'Piscataquis'"}],civil_fields)
    gs=[]
    for row in rows:
        g,hold=decode(row['geometry']['rings'])
        if hold:raise ValueError('County scope has held civil geometry: '+hold)
        gs.append(g)
    boundary=unary_union(gs)
    if boundary.is_empty or not boundary.is_valid:raise ValueError('Unusable county boundary')
    xmin,ymin,xmax,ymax=boundary.bounds
    spatial={'where':'1=1','geometry':','.join(map(str,[xmin,ymin,xmax,ymax])),'geometryType':'esriGeometryEnvelope','inSR':26919,'spatialRel':'esriSpatialRelIntersects'}
    sources=[civil]
    old=json.loads((ROOT/'research/maine-ingestion/2026-09-20/batch.json').read_bytes())['plan']['sources']
    for sid in ['ut-parcels','organized-parcels']:
        where="GEOCODE LIKE '21%'" + (" OR UPPER(COUNTY) = 'PISCATAQUIS'" if sid=='organized-parcels' else '')
        fields=next(s['fields'] for s in old if s['id']==sid)
        s,_=capture(sid,[{'where':where},spatial],fields);sources.append(s)
    fields=json.loads((ROOT/'research/zoning-ingestion/capture/batch.json').read_bytes())['plan']['sources'][0]['fields']
    # The county-wide zoning count timed out (HTTP 504); bounded tiles avoid
    # one expensive request. Reconcile every tile and deduplicate exact source IDs.
    tiles=[]
    for ix in range(4):
        for iy in range(4):
            tile=dict(spatial,geometry=','.join(map(str,[xmin+(xmax-xmin)*ix/4,ymin+(ymax-ymin)*iy/4,xmin+(xmax-xmin)*(ix+1)/4,ymin+(ymax-ymin)*(iy+1)/4])))
            tiles.append(tile)
    s,_=capture('lupc-zoning',tiles,fields);sources.append(s)
    batch={'scope':'Piscataquis County civil polygon union; no jurisdiction-type exclusions',
           'county_bounds_26919':list(boundary.bounds),'county_wkb_sha256':digest(boundary.wkb),
           'county_area_m2':boundary.area,'sources':sources,'method_sha256':digest(Path(__file__).read_bytes()),
           'controls':'Start count/IDs, exact page membership, end IDs and metadata; not an atomic snapshot. Envelope extras retained for audit.'}
    (BASE/'capture.json').write_text(json.dumps(batch,indent=2)+'\n')
    out=[]
    for sid in ['civil-boundaries','ut-parcels','organized-parcels','lupc-zoning']:
        s=source_lookup[sid].copy();s.update(probe_ids=[r['id'] for r in log if r['source_id']==sid],coverage='County/envelope source capture; see capture.json');out.append(s)
    # Include preliminary discovery captures in the same archive.
    for r in json.loads((BASE/'runs/discovery/results.json').read_bytes()):
        next(s for s in out if s['id']==r['source_id'])['probe_ids'].append(r['id'])
    (BASE/'registry.json').write_text(json.dumps({'as_of':datetime.now(timezone.utc).isoformat(),'scope':batch['scope'],'sources':out},indent=2)+'\n')
    print({s['source_id']:len(s['object_ids']) for s in sources},flush=True)

if __name__=='__main__':collect()
