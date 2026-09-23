"""Capture bounded official USDA metadata; requires a new output directory."""
import urllib.request,json,hashlib,argparse
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.output;root.mkdir(parents=True,exist_ok=False);entries=[]
for name in ['TablesAndColumnsReport','TableColumnDescriptionsReport','SoilDataAccessQueryGuide']:
 url='https://sdmdataaccess.sc.egov.usda.gov/documents/'+name+'.pdf'
 with urllib.request.urlopen(url,timeout=90) as r:raw=r.read()
 (root/(name+'.pdf')).write_bytes(raw);entries.append({'file':name+'.pdf','url':url,'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat()})
query="SELECT areasymbol,saversion,saverest,fgdcmetadata FROM sacatalog WHERE areasymbol IN ('ME602','ME612','ME614','ME615','ME619','ME620','ME621') ORDER BY areasymbol"
payload={'query':query,'format':'JSON+COLUMNNAME'};url='https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
with urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=90) as r:raw=r.read()
(root/'survey-metadata.response').write_bytes(raw);entries.append({'file':'survey-metadata.response','url':url,'payload':payload,'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat()})
(root/'sources.json').write_text(json.dumps(entries,indent=2)+'\n');print('Captured',len(entries),'official sources')
