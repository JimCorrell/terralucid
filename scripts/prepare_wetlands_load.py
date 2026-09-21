#!/usr/bin/env python3
"""Prepare a bounded, versioned NWI service feature load from archived evidence."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import shapely
from shapely.geometry import mapping
from investigate_osborn_wetlands import decode, group_source_rows, reconcile
from prepare_source_staging import ROOT, BUCKET, canonical, digest, literal, jsql, verify
from prepare_zoning_geometry import write_prepared

BASE = ROOT/'research/wetlands-load'
METHOD = 'scripts/prepare_wetlands_load.py'
MIGRATION = 'supabase/migrations/20260921020000_bounded_wetlands.sql'
SOURCE = 'e1449e8384d5d712dfdae9df26814330d1b9f7dc31ae82fc8765bce565b61906'
CLASSIFICATION = 'a1fd940a039662c703ec254963e70cd245f0632c970a62748591e5136f261c12'
CLASS_EVENT = '560e8844f3aef6c1b716524080d285790510924422df5db0ba3ae94de7019f48'
COVERAGE = '9874844cb3788a81be34652585b6ffb70c57286d56b7959741dc660bca5ac07b'
AVAILABILITY = '72c1e0f8114cc0f8c8cae6be84c3f575ca80758e1c640ecfa98704835dae56a2'


def checked(ok, message):
    if not ok: raise ValueError(message)


def select_lookup(core, variants, review, references):
    """Only an exact previously reviewed native core/lookup can use the resolution."""
    if review is None:
        checked(len(variants)==1, 'Unreviewed lookup conflict')
        return next(iter(variants.values())), 'source_single_variant'
    code = core['attributes']['Wetlands.ATTRIBUTE']
    checked(digest(canonical(core).encode())==review['native_core_sha256'], 'Reviewed core changed')
    checked(digest(canonical(core['geometry']).encode())==review['prior_native_geometry_sha256'], 'Reviewed geometry changed')
    checked(digest(canonical(references[code]).encode())==review['reference_row_sha256'], 'Reference row changed')
    selected = variants.get(review['selected_lookup_sha256'])
    checked(selected is not None, 'Reviewed lookup missing/changed')
    checked(selected['NWI_Wetland_Codes.OBJECTID']==review['selected_lookup_objectid'], 'Lookup identity differs')
    checked(all((selected['NWI_Wetland_Codes.'+k] or None)==(v or None) for k,v in references[code].items()), 'Reference mismatch')
    return selected, 'reviewed_reference_match'


def build():
    objects = {}
    def read(path, expected=None):
        data = (ROOT/path).read_bytes(); sha=digest(data)
        checked(expected is None or expected==sha, 'Changed reviewed bytes: '+path)
        objects[path]=data
        return json.loads(data) if path.endswith('.json') else data
    source=read('research/osborn-wetlands/report.json',SOURCE)
    review=read('research/wetlands-classification/report.json',CLASSIFICATION)
    read('research/availability-acceptance/report.json',AVAILABILITY)
    registry=read('research/osborn-wetlands/registry.json')
    registry_sha=digest(objects['research/osborn-wetlands/registry.json'])
    for name in [METHOD,MIGRATION,'scripts/investigate_osborn_wetlands.py','scripts/prepare_source_staging.py','scripts/prepare_zoning_geometry.py']:
        read(name)
    checked(digest(objects['scripts/investigate_osborn_wetlands.py'])==source['method_sha256'], 'Decoder version changed')
    rows=[]; occurrences=defaultdict(list)
    for key,e in sorted(source['evidence'].items()):
        if not key.startswith('features/wetland-page-'): continue
        path='research/osborn-wetlands/'+e['response_path']
        payload=json.loads(read(path,e['sha256']))
        checked(len(objects[path])==e['bytes'], 'Page byte count differs')
        # Exact source-audit hashes pin the already reconciled requested page membership.
        ids=[f['attributes']['Wetlands.OBJECTID'] for f in payload['features']]
        page=reconcile(payload,ids,'Wetlands.OBJECTID',joined=True)
        log={k:v for k,v in e.items() if k!='response_path'}
        observation=digest(canonical([registry_sha,'runs/features',log]).encode())
        for ordinal,f in enumerate(page):
            lookup={k:v for k,v in f['attributes'].items() if k.startswith('NWI_Wetland_Codes.')}
            occurrences[f['attributes']['Wetlands.OBJECTID']].append({'observation_sha256':observation,'payload_sha256':e['sha256'],'ordinal':ordinal,'lookup_sha256':digest(canonical(lookup).encode())})
        rows.extend(page)
    cores,conflicts=group_source_rows(rows)
    checked(len(cores)==669 and len(rows)==679, 'Bounded capture membership differs')
    checked(conflicts==source['joined_code_conflicts'], 'Conflict set changed')
    profiles={p['objectid']:p for p in source['features']}
    reviews={p['service_objectid']:p for p in review['records']}
    checked(set(reviews)=={c['objectid'] for c in conflicts}, 'Reviewed conflict membership differs')
    grouped=defaultdict(dict)
    for f in rows:
        lookup={k:v for k,v in f['attributes'].items() if k.startswith('NWI_Wetland_Codes.')}
        grouped[f['attributes']['Wetlands.OBJECTID']][digest(canonical(lookup).encode())]=lookup
    entries=[]
    for core in cores:
        oid=core['attributes']['Wetlands.OBJECTID']; profile=profiles[oid]
        checked(digest(canonical(core['geometry']).encode())==profile['native_geometry_sha256'], 'Profile geometry differs')
        g,hold=decode(core['geometry']['rings'])
        checked(hold is None and profile['decode_hold'] is None, 'Unexpected geometry hold; review capture')
        selected,interpretation=select_lookup(core,grouped[oid],reviews.get(oid),review['reference_rows'])
        entries.append({'object_id':oid,'native_core':core,'native_core_sha256':digest(canonical(core).encode()),
          'lookup_variants':dict(sorted(grouped[oid].items())),'effective_lookup':selected,'interpretation':interpretation,
          'review':reviews.get(oid),'source_occurrences':occurrences[oid], 'geometry_geojson':mapping(g),
          'prior_profile':profile})
    checked(sum(len(e['lookup_variants']) for e in entries)==677,'Joined variant count differs')
    report={'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest(objects[METHOD]),
      'inputs':{p:digest(d) for p,d in sorted(objects.items())},'source_audit_sha256':SOURCE,
      'classification_audit_sha256':CLASSIFICATION,'classification_event_id':CLASS_EVENT,
      'availability_coverage_result_id':COVERAGE,'scope':source['scope'],
      'imagery_lineage':source['coverage']['image-year'],'source_checks':source['checks'],
      'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string},
      'limits':{'wetland_completeness':'UNKNOWN','present_day_conditions':'UNKNOWN','legal_applicability':'UNKNOWN',
        'imagery':'May 1983; later NHD supplementation has no established acquisition date',
        'identity':'Service snapshot OBJECTID only; GlobalID cross-release persistence UNKNOWN; no package crosswalk',
        'geometry':'Native EPSG:3857 decoded without repair; not a legal delineation',
        'scope':'All envelope records retained, including neighbors; prior profile intersects FEMA study boundary, not parcel boundary'},
      'summary':{'features':len(entries),'raw_page_occurrences':len(rows),'distinct_joined_variants':677,'reviewed_classifications':len(reviews),
        'valid_geometries':len(entries),'prior_positive_area_study_intersections':sum(p['intersection_area_m2']>0 for p in profiles.values())},
      'feature_sha256':{str(e['object_id']):digest(canonical(e).encode()) for e in entries},
      'finding_review':{'finding_id':'TL-F-0117','status':'in_progress','priority':'medium',
        'note':'Loaded 669 exact-version service inventory features with 677 joined lookup variants and all 679 page occurrences. Eight classifications use the pinned TL-F-0027 resolution; accepted availability result and review dependencies are retained. No parcel screening or statewide package feature ingestion. May 1983 imagery, inventory completeness, package/service identity and projection, refresh and legal applicability remain qualified.',
        'next_action':'Qualify a bounded package/service comparison beyond the eight conflicts before wider ingestion; retain unmatched/multiple candidates and projection differences. Review imagery refresh and field/regulatory evidence separately.'}}
    return report,entries,list(objects.values())


def prepare(output,current):
    report,entries,objects=build();data=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();sha=digest(data)
    BASE.mkdir(exist_ok=True);(BASE/'report.json').write_bytes(data)
    state={r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    checked(state['TL-F-0027']['event_id']==CLASS_EVENT and state['TL-F-0027']['status']=='resolved' and not state['TL-F-0027']['needs_revisit'], 'Classification needs new review')
    reg=digest((ROOT/'research/osborn-wetlands/registry.json').read_bytes())
    sql='BEGIN;\nSET LOCAL standard_conforming_strings=on;\n'
    values=[literal(sha),literal(reg),literal('DERIVED'),literal(METHOD),literal(report['method_sha256']),jsql(report),literal(BUCKET),literal('sha256/'+sha+'.response')]
    sql+='INSERT INTO ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
    sql+='INSERT INTO ingest.wetlands_batch(audit_sha256,source_audit_sha256,classification_audit_sha256,classification_event_id,availability_result_id) VALUES ('+','.join(map(literal,[sha,SOURCE,CLASSIFICATION,CLASS_EVENT,COVERAGE]))+') ON CONFLICT DO NOTHING;\n'
    for e in entries:
        sql+='INSERT INTO ingest.wetlands_feature(audit_sha256,object_id,input_text) VALUES ('+','.join([literal(sha),str(e['object_id']),literal(canonical(e))])+') ON CONFLICT DO NOTHING;\n'
    sql+='SELECT ingest.assert_wetlands_batch('+literal(sha)+');\n'
    event=dict(report['finding_review'],event_id=digest(canonical([sha,'TL-F-0117']).encode()),actor='TerraLucid bounded wetlands ingestion',evidence_refs=['audit:'+sha+'#/summary','audit:'+sha+'#/limits'])
    sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(event['event_id']),literal('TL-F-0117'),literal(sha),jsql({'report_pointer':'/summary'})])+') ON CONFLICT DO NOTHING;\n'
    sql+='SELECT ingest.record_finding_event('+jsql(event)+','+literal(state['TL-F-0117']['event_id'])+');\nCOMMIT;\n'
    write_prepared(output,sql,objects+[data])
    print(json.dumps({'audit_sha256':sha,**report['summary']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--current',type=Path);p.add_argument('--verify-download',type=Path);a=p.parse_args()
    if a.verify_download:print(verify(a.output,a.verify_download))
    elif a.current:prepare(a.output,a.current)
    else:p.error('--current required for preparation')
