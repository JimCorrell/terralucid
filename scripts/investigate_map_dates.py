#!/usr/bin/env python3
"""Pin a manual seven-map date review to immutable official evidence and ranking."""
import json
from datetime import datetime, timezone
from pathlib import Path
from prepare_source_staging import ROOT,digest
BASE=ROOT/'research/map-date-investigation'
AUDIT='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
RANKING_SHA='a20ffe8bde648dc77fd502a15283c613b2a04c3b8dbf40c86417edd45f6fab1f'
MAPS={'big-moose-twp','beaver-cove','bowdoin-college-grant-west-twp','t1-r13-wels','t1-r11-wels','orneville-twp','shawtown-twp'}
def main():
    inputs={};evidence={}
    def pin(p):
        b=p.read_bytes();inputs[p.relative_to(ROOT).as_posix()]=digest(b);return b
    ranking=json.loads(pin(ROOT/'research/twenty-eight-correction-ranking/report.json'))
    if inputs['research/twenty-eight-correction-ranking/report.json']!=RANKING_SHA:raise ValueError('Changed ranking')
    for f in sorted(BASE.glob('*probes.json')):pin(f)
    review=json.loads(pin(BASE/'review.json'));pin(BASE/'registry.json')
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for e in json.loads(pin(log)):
            key=log.parent.name+'/'+e['id'];evidence[key]=dict(e)
            if 'response_file' not in e:continue
            if Path(e['response_file']).name!=e['response_file']:raise ValueError('Unsafe path')
            p=log.parent/e['response_file'];b=pin(p)
            if digest(b)!=e['sha256'] or len(b)!=e['bytes'] or e['http_status']!=200:raise ValueError('Changed or unsuccessful evidence '+key)
            evidence[key]['response_path']=p.relative_to(ROOT).as_posix()
    raw=json.loads((BASE/'runs/detail/map-index.response').read_bytes())
    attrs={f['attributes']['MAP']:f['attributes'] for f in raw['features']}
    if set(attrs)!=MAPS or len(raw['features'])!=7 or raw.get('exceededTransferLimit'):raise ValueError('Incomplete scope')
    if {r['map'] for r in review['cases']}!=MAPS or len(review['cases'])!=7:raise ValueError('Changed review scope')
    for case in review['cases']:
        if any(ref not in evidence or 'response_path' not in evidence[ref] for ref in case['evidence_refs']):raise ValueError('Missing review evidence')
        if case['legal_currency']!='UNKNOWN' or case['proposed_source_value_replacement'] is not None:raise ValueError('No source/date correction authorized by this review')
        a=attrs[case['map']]
        case['index_dates']={k:{'raw_epoch_ms':a[k],'utc_date':datetime.fromtimestamp(a[k]/1000,timezone.utc).date().isoformat()} if a[k] is not None else None for k in ['ADOPT_DATE','EFFECTIVE_DATE','AMEND_DATE','last_edited_date','FEMA_Effective_Date']}
        case['index_last_edited_date_text']=a['last_edited_date_text']
        case['index_amendment_matches_pdf_latest']=case['index_dates']['AMEND_DATE']['utc_date']==case['pdf_latest_listed_amendment']
    report={'evidence_state':'DERIVED','source_audit_sha256':AUDIT,'ranking_audit_sha256':RANKING_SHA,'geometry_snapshot_id':ranking['geometry_snapshot_id'],'geometry_dependencies':ranking['geometry_dependencies'],'method':'scripts/investigate_map_dates.py','method_sha256':digest(Path(__file__).read_bytes()),'inputs':inputs,'evidence':evidence,**review,'review_conclusion':{'corroborated_history_maps':4,'conflicting_official_date_maps':2,'map_text_correction_maps':1,'legal_currency_resolved':0,'source_value_replacements':0,'geometry_changes':0,'qualification_changes':0}}
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report['review_conclusion']))
if __name__=='__main__':main()
