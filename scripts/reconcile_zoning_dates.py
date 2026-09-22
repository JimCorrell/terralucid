#!/usr/bin/env python3
"""Pin two manually reviewed signed decisions without overwriting map metadata."""
import json
from pathlib import Path
from prepare_source_staging import ROOT,digest
BASE=ROOT/'research/zp750-zp770-dates'
AUDIT='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
RANKING_SHA='a20ffe8bde648dc77fd502a15283c613b2a04c3b8dbf40c86417edd45f6fab1f'
PRIOR_SHA='0520e8136fe08fe664b0f45f9cb2f8eee2c259d514d74ea9e9e18ff707aaea34'
MAPS={'shawtown-twp','t1-r11-wels'}
def validate_review(review):
    rows=review['cases']
    if len(rows)!=2 or {c['map'] for c in rows}!=MAPS:raise ValueError('Changed scope')
    expected={'ZP750':('shawtown-twp','2015-06-10','2015-06-25',14),'ZP770':('t1-r11-wels','2018-04-11','2018-04-26',7)}
    for c in rows:
        if expected.get(c['petition'])!=(c['map'],c['decision_date'],c['decision_stated_effective_date'],c['effective_date_page']):raise ValueError('Changed manual decision transcription; requires new review')
        if c['legal_currency']!='UNKNOWN' or c['source_value_replacement'] is not None or c['reconciliation_status']!='historical_decision_date_established_filing_variance_open':raise ValueError('Unsupported legal/source promotion')

def main():
    inputs={};evidence={}
    def pin(p):
        b=p.read_bytes();inputs[p.relative_to(ROOT).as_posix()]=digest(b);return b
    oldpath=ROOT/'research/map-date-investigation/report.json';old=json.loads(pin(oldpath))
    if digest(oldpath.read_bytes())!=PRIOR_SHA:raise ValueError('Changed prior review')
    review=json.loads(pin(BASE/'review.json'));validate_review(review)
    baseline=json.loads(pin(BASE/'baseline.json'))['rows'][0]['verification']
    if not baseline['ranking_snapshot_current'] or len(baseline['accepted'])!=28:raise ValueError('Stale county baseline')
    event=next(r for r in baseline['finding_reviews'] if r['finding_id']=='TL-F-0029')['event_id']
    if event!='5ae4e427a628d38c38eb0f12e0217d014e72f33ead616ed14bd756dfca43caf7':raise ValueError('Newer review; reread before appending')
    for p in sorted(BASE.glob('*probes.json')):pin(p)
    pin(BASE/'registry.json')
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for e in json.loads(pin(log)):
            key=log.parent.name+'/'+e['id'];evidence[key]=dict(e)
            if 'response_file' not in e:continue
            if Path(e['response_file']).name!=e['response_file']:raise ValueError('Unsafe response path')
            p=log.parent/e['response_file'];b=pin(p)
            if digest(b)!=e['sha256'] or len(b)!=e['bytes']:raise ValueError('Changed response')
            evidence[key]['response_path']=p.relative_to(ROOT).as_posix()
    prior_refs=set()
    for c in review['cases']:
        e=evidence[c['signed_evidence']]
        if e['http_status']!=200 or not e['pdf_signature']:raise ValueError('Decision PDF missing')
        if c['signed_document_sha256']!=e['sha256']:raise ValueError('Signed document differs from manual review')
        for x in c['other_observed_dates']:prior_refs.update(x.get('prior_evidence',[]))
    for ref in sorted(prior_refs):
        e=old['evidence'][ref];p=ROOT/e['response_path']
        if digest(pin(p))!=e['sha256']:raise ValueError('Changed prior evidence')
    report={'evidence_state':'DERIVED','source_audit_sha256':AUDIT,'ranking_audit_sha256':RANKING_SHA,'prior_date_audit_sha256':PRIOR_SHA,'geometry_snapshot_id':old['geometry_snapshot_id'],'geometry_dependencies':old['geometry_dependencies'],'method':'scripts/reconcile_zoning_dates.py','method_sha256':digest(Path(__file__).read_bytes()),'inputs':inputs,'evidence':evidence,'prior_evidence':{k:old['evidence'][k] for k in sorted(prior_refs)},**review,'review_conclusion':{'decision_stated_dates_established':2,'filing_variances_still_open':2,'source_value_replacements':0,'geometry_changes':0,'legal_currency_established':0}}
    (BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    plan={'actor':'TerraLucid ZP750/ZP770 signed-decision reconciliation','expected_event_id':event,'finding_id':'TL-F-0029','status':'in_progress','priority':'high','note':'Signed decisions establish decision-stated historical effective dates: ZP750 June25,2015 (p14); ZP770 April26,2018 (p7). Preserve conflicting map/annual values; 2018 annual summary adds April24. Filing variance and current legal applicability remain unresolved; no source values or geometry changed.','next_action':'Use explicitly named decision_stated_effective_date with signed-source provenance for these two historical actions. On material parcel/transaction dependency, obtain original filings2015-119 and2018-067 and recorded maps/agency reconciliation; do not reinterpret annual dates without evidence. Retain Orneville ZP796 correction-record follow-up and remaining four map-currentness limits. County remains 134 zoning/21 parcel holds, 28 accepted versions, zero qualified rows; use current ranking and parcel-triggered review.'}
    (BASE/'finding-review.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(report['review_conclusion']))
if __name__=='__main__':main()
