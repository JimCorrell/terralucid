#!/usr/bin/env python3
"""Compare Orneville's published FEMA note with signed ZP796 text-only approval."""
import json,re
from datetime import datetime,timezone
from pathlib import Path
import fitz
from prepare_source_staging import ROOT,digest
BASE=ROOT/'research/orneville-zp796'
AUDIT='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
RANKING_SHA='a20ffe8bde648dc77fd502a15283c613b2a04c3b8dbf40c86417edd45f6fab1f'
PRIOR_SHA='b6be9cee16a2af37e7975273cf4cdc383d18a7f9ba1ed6840546135ea3545b33'
MAPS={'orneville-twp'}
def normalize(text):return ' '.join(text.split())
def note(text):
    return re.search(r'The Federal Emergency Management Agency has identified special.*?A copy of the FIRM may be obtained from Commission staff\.',normalize(text)).group()
def compare_note(template,published,title,date):
    return note(template).replace('[full title of the FIRM]',title).replace('[date of FIRM]',date)==note(published)
def validate_review(r):
    if len(r['cases'])!=1:raise ValueError('Changed scope')
    c=r['cases'][0]
    if (c['map'],c['petition'],c['decision_date'],c['decision_stated_effective_date'])!=('orneville-twp','ZP796','2024-07-17','2024-08-01'):raise ValueError('Changed reviewed action')
    if c['legal_currency']!='UNKNOWN' or c['source_value_replacement'] is not None or c['geometry_change_authorized'] is not False:raise ValueError('Unsupported source/legal/geometry promotion')
def main():
    inputs={};evidence={}
    def pin(p):
        b=p.read_bytes();inputs[p.relative_to(ROOT).as_posix()]=digest(b);return b
    priorpath=ROOT/'research/zp750-zp770-dates/report.json';prior=json.loads(pin(priorpath))
    if digest(priorpath.read_bytes())!=PRIOR_SHA:raise ValueError('Changed prior audit')
    review=json.loads(pin(BASE/'review.json'));validate_review(review)
    baseline=json.loads(pin(BASE/'baseline.json'))['rows'][0]['verification']
    if not baseline['ranking_snapshot_current'] or len(baseline['accepted'])!=28:raise ValueError('Stale county baseline')
    if next(f for f in baseline['finding_reviews'] if f['finding_id']=='TL-F-0029')['event_id']!='d372a4479df5d250276a04f649409592708134ce8610530dedbd1e7e1e4a674c':raise ValueError('Newer finding review')
    for f in sorted(BASE.glob('*probes.json')):pin(f)
    pin(BASE/'registry.json')
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for e in json.loads(pin(log)):
            p=log.parent/e['response_file'];b=pin(p)
            if digest(b)!=e['sha256'] or len(b)!=e['bytes'] or e['http_status']!=200:raise ValueError('Changed/failed response')
            evidence[log.parent.name+'/'+e['id']]={**e,'response_path':p.relative_to(ROOT).as_posix()}
    decision=fitz.open(stream=(BASE/'runs/official/zp796-record.response').read_bytes(),filetype='pdf')
    if digest((BASE/'runs/official/zp796-record.response').read_bytes())!=review['cases'][0]['signed_document_sha256']:raise ValueError('Changed manually reviewed decision')
    mapdoc=fitz.open(stream=(BASE/'runs/official/orneville-map.response').read_bytes(),filetype='pdf')
    attrs=json.loads((BASE/'runs/index/map-index.response').read_bytes())['features']
    if len(attrs)!=1 or attrs[0]['attributes']['MAP']!='orneville-twp':raise ValueError('Changed index scope')
    a=attrs[0]['attributes'];date=datetime.fromtimestamp(a['FEMA_Effective_Date']/1000,timezone.utc).strftime('%-m/%-d/%Y')
    matches=compare_note(decision[1].get_text(),mapdoc[0].get_text(),a['FEMA_Map_Name'],date)
    if not matches or date!='4/17/1987' or 'Orneville Twp. (T1 R6 NWP)' not in decision[3].get_text():raise ValueError('Map does not implement reviewed note')
    oldmap=ROOT/'research/map-date-investigation/runs/official/orneville-twp.response';oldbytes=pin(oldmap)
    c=review['cases'][0];c['index_dates']={k:a[k] for k in ['AMEND_DATE','ADOPT_DATE','EFFECTIVE_DATE','last_edited_date_text','FEMA_Map_Name','FEMA_Effective_Date']}
    c['normalized_note_matches_approved_template']=matches;c['current_map_same_bytes_as_PR47']=digest(oldbytes)==evidence['official/orneville-map']['sha256'];c['referenced_firm_date']='1987-04-17'
    r={'evidence_state':'DERIVED','source_audit_sha256':AUDIT,'ranking_audit_sha256':RANKING_SHA,'prior_date_audit_sha256':PRIOR_SHA,'geometry_snapshot_id':prior['geometry_snapshot_id'],'geometry_dependencies':prior['geometry_dependencies'],'method':'scripts/investigate_orneville_zp796.py','method_sha256':digest(Path(__file__).read_bytes()),'inputs':inputs,'evidence':evidence,**review,'review_conclusion':{'historical_action_scope_and_date_established':True,'current_note_matches_signed_template':matches,'prior_wording_reconstructed':False,'source_value_replacements':0,'geometry_changes':0,'current_legal_applicability':'UNKNOWN'}}
    (BASE/'report.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r['review_conclusion']))
if __name__=='__main__':main()
