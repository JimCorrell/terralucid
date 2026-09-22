#!/usr/bin/env python3
"""Reproduce bounded county readiness evidence; never infer clearance from absence."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'research/county-readiness'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def summarize_catalog(d):
    if not isinstance(d,dict) or 'EFFECTIVE' not in d or 'error' in d:raise ValueError('Invalid catalog')
    return {s:{k:len(v) for k,v in d[s].items()} for s in ('EFFECTIVE','HISTORIC','PENDING')}
def ids(d):
    if 'error' in d or d.get('exceededTransferLimit') or 'objectIds' not in d:raise ValueError('Incomplete ID response')
    return d['objectIds'] or []
def main():
    import fitz
    old=read(ROOT/'research/orneville-zp796/report.json');baseline=read(BASE/'baseline.json')['rows'][0]['verification']
    if not baseline['ranking_snapshot_current'] or not baseline['county_fingerprints_unchanged']:raise ValueError('Stale baseline')
    evidence={};inputs={}
    for log in sorted((BASE/'runs').glob('*/results.json')):
        inputs[str(log.relative_to(ROOT))]=sha(log)
        for e in read(log):
            e=dict(e)
            if 'response_file' in e:
                p=log.parent/e['response_file']
                if sha(p)!=e['sha256'] or len(p.read_bytes())!=e['bytes']:raise ValueError('Changed response')
                e['response_path']=str(p.relative_to(ROOT))
            evidence[log.parent.name+'/'+e['id']]=e
    catalog=read(BASE/'runs/catalog/catalog-orneville.response');counts=summarize_catalog(catalog)
    firm=catalog['EFFECTIVE']['FIRM_PANEL'];letters=catalog['EFFECTIVE']['LOMA']
    if len(firm)!=1 or firm[0]['product_NAME']!='230465A' or firm[0]['ref_COMMUN_NAME']!='ORNEVILLE, TOWNSHIP OF':raise ValueError('Unexpected identity')
    rel=catalog['EFFECTIVE_LOMC']['LOMC']['LOMA']['230465A']
    if {x['c_PRODUCT_NAME'] for x in rel}!={x['product_NAME'] for x in letters}:raise ValueError('Letter relation mismatch')
    with zipfile.ZipFile(BASE/'runs/products/orneville-firm.response') as z:
        members={n:{'sha256':hashlib.sha256(z.read(n)).hexdigest(),'bytes':len(z.read(n))} for n in z.namelist()}
        tif=z.read('230465A.tif');doc=fitz.open(stream=tif,filetype='tiff')
        if len(doc)!=4:raise ValueError('Unexpected map pages')
    paths=['research/orneville-zp796/report.json','research/piscataquis-ingestion/report.json','research/twenty-eight-correction-ranking/report.json',
           'research/piscataquis-ingestion/runs/capture/civil-boundaries-page-1.response','research/county-readiness/baseline.json','research/county-readiness/review.json','research/county-readiness/README.md']
    paths += [str(p.relative_to(ROOT)) for p in sorted(BASE.glob('*probes.json'))]+['research/county-readiness/catalog-queries.json','research/county-readiness/availability-retry.json']
    for p in paths:inputs[p]=sha(ROOT/p)
    for p in sorted((BASE/'diagnostics').glob('*.png')):inputs[str(p.relative_to(ROOT))]=sha(p)
    r={'evidence_state':'DERIVED','method':str(Path(__file__).relative_to(ROOT)),'method_sha256':sha(Path(__file__)),
       'source_audit_sha256':old['source_audit_sha256'],'ranking_audit_sha256':old['ranking_audit_sha256'],
       'geometry_snapshot_id':old['geometry_snapshot_id'],'geometry_dependencies':old['geometry_dependencies'],
       'inputs':inputs,'evidence':evidence,'county':{k:baseline[k] for k in ['county_rows','effective_total_holds','effective_zoning_holds','qualified_rows','ranking_snapshot_current']},
       'orneville':{'community_id':'230465','catalog_counts':counts,'base_product':{k:firm[0][k] for k in ['product_NAME','product_EFFECTIVE_DATE_STRING','product_SUBTYPE_ID']},
          'zip_members':members,'tiff_pages':len(doc),'letters':[{'id':x['product_NAME'],'catalog_date':x['product_EFFECTIVE_DATE_STRING']} for x in letters],
          'letter_documents_reviewed':False,'review':read(BASE/'review.json'),
          'nfhl_jurisdiction_features':len(read(BASE/'runs/retry/jurisdiction.response')['features']),
          'nfhl_availability_envelope_ids':ids(read(BASE/'runs/availability-retry/availability-ids.response')),
          'nfhl_hazard_envelope_ids':ids(read(BASE/'runs/spatial/hazards-ids.response')),
          'nfhl_panel_envelope_ids':ids(read(BASE/'runs/spatial/panels-ids.response'))},
       'county_catalog_counts':summarize_catalog(read(BASE/'runs/catalog/catalog-piscataquis.response')),
       'review_conclusion':'Bounded evidence research ready; automated parcel screening and offer readiness unqualified. Implement parcel/AOI dependency and coverage checks; inventory county FEMA products. No absence-based flood clearance.',
       'scope_limits':['No geometry, identity, screening, scoring or legal-currentness promotion','No county flood completeness claim','No review of individual LOMA determinations','No rerun of historical marginal repair benefit curve']}
    (BASE/'report.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('Reproduced county readiness report')
if __name__=='__main__':main()
