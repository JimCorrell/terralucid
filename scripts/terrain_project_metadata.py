#!/usr/bin/env python3
"""Capture bounded original DEM/project XML linked from representative USGS items."""
import argparse
import json
from pathlib import Path
import urllib.parse
import xml.etree.ElementTree as ET
from investigate_terrain_readiness import Capture, sha


def run(evidence, output):
    cap=Capture(output); report=[]
    for itemfile in sorted(evidence.glob('*-item.json')):
        item=json.loads(itemfile.read_text()); links=[x['uri'] for x in item['webLinks'] if 'prefix=' in x['uri']]
        row={'source_id':item['id'],'item_sha256':sha(itemfile),'documents':[]}
        for li,link in enumerate(links):
            prefix=urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get('prefix',[None])[0]
            if not prefix: row['unsupported_link']=link; continue
            root_url='https://prd-tnm.s3.amazonaws.com/?'+urllib.parse.urlencode({'list-type':2,'prefix':prefix.rstrip('/')+'/','delimiter':'/'})
            raw,_=cap.get(root_url,f'{itemfile.stem}-{li}-root.xml')
            root=ET.fromstring(raw)
            if root.findtext('{*}IsTruncated')!='false': raise ValueError('Root directory listing truncated')
            keys=[(c.findtext('{*}Key'),int(c.findtext('{*}Size'))) for c in root.findall('{*}Contents')]
            report_prefixes=[x.findtext('{*}Prefix') for x in root.findall('{*}CommonPrefixes') if x.findtext('{*}Prefix').endswith('/reports/')]
            row.setdefault('listings',[]).append({'prefix':prefix,'scope':'Root objects and discovered reports directories only','report_prefixes':report_prefixes})
            for report_prefix in report_prefixes:
                token=None
                for page in range(10):
                    query={'list-type':2,'prefix':report_prefix}
                    if token: query['continuation-token']=token
                    listing='https://prd-tnm.s3.amazonaws.com/?'+urllib.parse.urlencode(query)
                    raw,_=cap.get(listing,f'{itemfile.stem}-{li}-reports-{page}.xml')
                    root=ET.fromstring(raw)
                    keys.extend((c.findtext('{*}Key'),int(c.findtext('{*}Size'))) for c in root.findall('{*}Contents'))
                    if root.findtext('{*}IsTruncated')=='false': break
                    token=root.findtext('{*}NextContinuationToken')
                    if not token: raise ValueError('Missing listing continuation token')
                else: raise ValueError('Report listing exceeds ten-page bound')
            selected=[(k,n) for k,n in keys if k.lower().endswith('.xml') and any(s in k.lower() for s in ('dem','projectlevel','project_level')) and 'spatial_metadata/' not in k and n<=2*1024*1024]
            row['selected_xml_count']=len(selected)
            if len(selected)>40: raise ValueError('XML scope exceeds 40 documents per link')
            for j,(key,size) in enumerate(selected):
                url='https://prd-tnm.s3.amazonaws.com/'+urllib.parse.quote(key,safe='/')
                name=f'{itemfile.stem}-{li}-{j}.xml';raw,record=cap.get(url,name)
                try:
                    xml=ET.fromstring(raw)
                except ET.ParseError as error:
                    row['documents'].append({'file':name,'url':url,'sha256':record['sha256'],'parse_error':str(error)})
                    continue
                fields={path:[ET.tostring(x,encoding='unicode') for x in xml.findall(path)] for path in
                    ('idinfo/timeperd','dataqual/posacc','spref','idinfo/descript/abstract','idinfo/descript/supplinf')}
                row['documents'].append({'file':name,'url':url,'sha256':record['sha256'],'fields':fields})
        report.append(row)
        (output/'report.json').write_text(json.dumps({'method_sha256':sha(__file__),'projects':report},indent=2)+'\n')
        print(item['id'],len(row['documents']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence,a.output)
