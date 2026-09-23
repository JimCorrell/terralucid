"""Compare all county percentage deficits with the public USDA component table."""
import argparse,json,hashlib,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from collect_county_soils import rows
from verify_county_soil_bundle import verify,file_sha
FIELDS=['mukey','cokey','compname','compkind','majcompflag','comppct_l','comppct_r','comppct_h']
def run(bundle,out):
    verified=verify(bundle);root=Path(__file__).resolve().parents[1]
    metadata=root/'research/soil-metadata-qualification/report.json';r=json.loads(metadata.read_bytes())
    if r['bundle']['report_sha256']!=verified['report_sha256']:raise ValueError('Source batch differs')
    keys={v['mukey'] for v in r['county_linked_tables']['component_percent_sum_exceptions']}
    if not keys or any(not k.isdigit() for k in keys):raise ValueError('Invalid map-unit set')
    original=[]
    for line in (bundle/'records.jsonl').open():
        row=json.loads(line)
        if row['kind']=='component' and row['raw']['mukey'] in keys:original.append({k:row['raw'][k] for k in FIELDS})
    out.mkdir(parents=True,exist_ok=False);sources=[]
    query='SELECT '+','.join(FIELDS)+' FROM component WHERE mukey IN ('+','.join(sorted(keys))+') ORDER BY mukey,cokey'
    payload={'query':query,'format':'JSON+COLUMNNAME'};url='https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
    with urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=90) as response:raw=response.read()
    (out/'components.response').write_bytes(raw);sources.append({'file':'components.response','url':url,'payload':payload,'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat()})
    fresh=rows(json.loads(raw));sort=lambda rs:sorted(rs,key=lambda v:(v['mukey'],v['cokey']))
    url='https://sdmdataaccess.sc.egov.usda.gov/documents/FundamentalQuery.pdf'
    with urllib.request.urlopen(url,timeout=90) as response:raw=response.read()
    (out/'FundamentalQuery.pdf').write_bytes(raw);sources.append({'file':'FundamentalQuery.pdf','url':url,'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat()})
    report={'evidence_state':'DERIVED','method_sha256':file_sha(Path(__file__)),'metadata_report_sha256':file_sha(metadata),'bundle_report_sha256':verified['report_sha256'],
      'mapunits_queried':len(keys),'archived_components':len(original),'fresh_components':len(fresh),'compared_fields':FIELDS,
      'exact_selected_rows_match':sort(original)==sort(fresh),'new_keys':sorted({v['cokey'] for v in fresh}-{v['cokey'] for v in original}),
      'missing_keys':sorted({v['cokey'] for v in original}-{v['cokey'] for v in fresh}),
      'interpretation':'USDA documents that some minor components may not be individually recorded. Matching direct rows supports a source representation limitation rather than a retrieval omission for this scope. It does not identify the omitted components or establish site conditions.',
      'action':'Preserve total and unlisted proportion; no normalization or imputed component. Retain per-map-unit uncertainty.'}
    (out/'sources.json').write_text(json.dumps(sources,indent=2)+'\n');(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.bundle,a.output)
