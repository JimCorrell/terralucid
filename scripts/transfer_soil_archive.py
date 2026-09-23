"""Upload without overwrite and download/hash every private soil archive object.

One CLI key lookup; credentials remain in memory. No auth or upload retries.
"""
import argparse,concurrent.futures,hashlib,json,os,subprocess,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
from verify_county_soil_bundle import verify,file_sha
PROJECT='yytsjlmbyqhcqfalbjca';BUCKET='terralucid-source-snapshots'
def transfer(bundle,out,cli):
    verified=verify(bundle);out.mkdir(parents=True,exist_ok=False)
    result=subprocess.run([str(cli),'projects','api-keys','--project-ref',PROJECT,'--output','json','--agent','no'],capture_output=True,text=True,timeout=45)
    if result.returncode:raise RuntimeError('One archive credential lookup failed; no retry')
    data=json.loads(result.stdout)
    if isinstance(data,dict):data=data.get('api_keys',data.get('data',data.get('keys',[])))
    keys=[r['api_key'] for r in data if r.get('name')=='service_role' and r.get('api_key')]
    if len(keys)!=1:raise RuntimeError('Expected one existing archive service key; no keys printed or created')
    key=keys[0];base='https://'+PROJECT+'.supabase.co/storage/v1'
    headers={'apikey':key,'Authorization':'Bearer '+key}
    def request(url,method='GET',body=None):
        return urllib.request.urlopen(urllib.request.Request(url,data=body,method=method,headers=headers|({'Content-Type':'application/octet-stream','x-upsert':'false'} if body is not None else {})),timeout=90)
    with request(base+'/bucket/'+BUCKET) as response:bucket=json.load(response)
    if bucket.get('public') is not False or bucket.get('id')!=BUCKET:raise RuntimeError('Archive bucket must exist and be private')
    manifest=json.loads((bundle/'manifest.json').read_bytes());objects={k:bundle/'objects'/k for k in manifest['objects']}
    for filename in ['report.json','manifest.json']:objects[file_sha(bundle/filename)]=bundle/filename
    def one(item):
        digest,path=item;relative='sha256/'+digest+'.response';target=out/digest;existed=True
        def download():
            with request(base+'/object/authenticated/'+BUCKET+'/'+relative) as response:
                fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
                with os.fdopen(fd,'wb') as dest:
                    while True:
                        block=response.read(1024*1024)
                        if not block:break
                        dest.write(block)
        try:download()
        except urllib.error.HTTPError as error:
            raw=error.read()
            try:detail=json.loads(raw)
            except ValueError:detail={}
            if error.code!=404 and str(detail.get('statusCode'))!='404':raise RuntimeError('Archive access HTTP '+str(error.code)) from None
            existed=False
            with request(base+'/object/'+BUCKET+'/'+relative,'POST',path.read_bytes()) as response:response.read()
            download()
        if file_sha(target)!=digest or target.stat().st_size!=path.stat().st_size:raise RuntimeError('Archive readback mismatch; never overwritten: '+digest)
        return {'sha256':digest,'bytes':target.stat().st_size,'storage_object':relative,'already_present':existed,'readback_matches':True}
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for record in executor.map(one,objects.items()):
            results.append(record)
            if len(results)%20==0:print('Archive objects verified:',len(results),flush=True)
    report={'status':'PASS','project_ref':PROJECT,'bucket':BUCKET,'bucket_private':True,'credential_lookups':1,
            'verified_at':datetime.now(timezone.utc).isoformat(),'bundle_report_sha256':verified['report_sha256'],
            'objects':sorted(results,key=lambda r:r['sha256']),'verified_bytes':sum(r['bytes'] for r in results)}
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('Verified all '+str(len(results))+' archive objects',flush=True)
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cli',type=Path,required=True);a=p.parse_args();transfer(a.bundle,a.output,a.cli)
