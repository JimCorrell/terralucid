#!/usr/bin/env python3
"""Reproduce bounded zoning screening from archived evidence and a versioned DB export."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile
import shapely
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity
import pyproj
from pyproj import Transformer
from prepare_source_staging import ROOT, canonical, digest, literal, jsql, prepare
from prepare_bounded_ingestion import validate_capture

BASE=ROOT/'research/zoning-ingestion'
METHOD='scripts/prepare_zoning_ingestion.py'
PROJECT=Transformer.from_crs(4326,26919,always_xy=True).transform


def geometry_state(feature):
    try:
        if not feature.get('geometry'):return None,'missing','Source geometry absent'
        g=shape(feature['geometry'])
        if g.is_empty:return g,'missing','Empty source geometry'
        if g.geom_type not in ('Polygon','MultiPolygon'):return g,'invalid','Expected polygonal source geometry'
        return g,('valid' if g.is_valid else 'invalid'),explain_validity(g)
    except Exception as e:return None,'decode_failed',str(e)


def effective_input(row,feature):
    """Consume the recorded effective interpretation, never silently use raw codes."""
    if digest(canonical(feature).encode())!=row['source_feature_sha256']:
        raise ValueError('Changed correction source feature')
    if row['correction_status']=='accepted' and not row['event_id']:
        raise ValueError('Accepted correction lacks review event')
    if row['correction_status']!='accepted' and row['effective_properties']!=feature['properties']:
        raise ValueError('Unaccepted correction changes source properties')
    return dict(row,raw_feature=feature,quality_flags=[],interpretation='correction_layer',
                correction_evidence_state='INFERRED' if row['correction_status']=='accepted' else None)


def overlap_result(feature,zones,coverage_available):
    """Observed geometry intersections, not legal zone assignments or exclusive areas."""
    g,state,reason=geometry_state(feature)
    base={'legal_zoning_state':'UNKNOWN','boundary_dependency':'assessment_geometry',
          'geometry_state':state,'geometry_detail':reason,'intersections':[],
          'covered_fraction':None,'intersection_area_sum_m2':None,'boundary_touches':[],
          'invalid_zone_envelope_candidates':[], 'flags':['legal_currency_unverified','assessment_boundary_not_surveyed']}
    if not coverage_available:
        return dict(base,status='no_qualified_digital_coverage',evidence_state='UNKNOWN')
    if state!='valid':return dict(base,status='source_geometry_unusable',evidence_state='UNKNOWN')
    projected=transform(PROJECT,g);pieces=[];area_sum=0
    for z,zg,zstate in zones:
        if zg is None:base['flags'].append('zoning_geometry_missing');continue
        if not g.envelope.intersects(zg.envelope):continue
        if zstate!='valid':base['invalid_zone_envelope_candidates'].append(z['object_id']);continue
        if not g.intersects(zg):continue
        intersection=projected.intersection(transform(PROJECT,zg));area=intersection.area
        if area<=0:base['boundary_touches'].append(z['object_id']);continue
        pieces.append(intersection);area_sum+=area
        base['intersections'].append({'object_id':z['object_id'],'zone':z['properties']['ZONE'],
                                      'area_m2':area,'parcel_area_fraction':min(1.0,max(0.0,area/projected.area))})
    covered=min(1.0,max(0.0,unary_union(pieces).area/projected.area)) if pieces else 0.0
    if any(s!='valid' for _,_,s in zones):base['flags'].append('invalid_zoning_geometry_in_capture')
    if covered<1-1e-9:base['flags'].append('not_fully_covered_by_valid_captured_geometry')
    if base['invalid_zone_envelope_candidates']:base['flags'].append('possible_overlap_with_invalid_zone')
    base['flags']+=['map_omits_some_rule_based_protections','source_date_fields_not_legal_current_filter']
    return dict(base,status='observed_overlaps' if pieces else 'no_observed_overlap',evidence_state='DERIVED',
                covered_fraction=covered,intersection_area_sum_m2=area_sum,source_area_m2=projected.area)


def build():
    batch,_,zones=validate_capture(BASE/'capture')
    evidence={}
    runs={p.parent.name:p.parent for p in (BASE/'runs').glob('*/results.json')}
    runs['zones']=BASE/'capture/runs/bounded'
    for name,path in sorted(runs.items()):
        for r in json.loads((path/'results.json').read_bytes()):
            data=(path/r['response_file']).read_bytes()
            if digest(data)!=r['sha256'] or len(data)!=r['bytes']:raise ValueError('Evidence checksum differs')
            evidence[name+'/'+r['id']]=dict(r,response_path='runs/'+name+'/'+r['response_file'])
    qualification=json.loads((BASE/'qualification.json').read_bytes())
    for doc in qualification['document_review']:
        if evidence[doc['evidence_ref']]['sha256']!=doc['sha256']:raise ValueError('Document review version differs')
    # Validate observed publication links. No guessed document endpoints.
    from html.parser import HTMLParser
    from urllib.parse import urljoin
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.hrefs=[];self.base=''
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='a' and 'href' in a:self.hrefs.append(a['href'])
            if tag=='base':self.base=a.get('href','')
    for link in qualification['publication_links']:
        parent=evidence[link['page']];path=runs[link['page'].split('/')[0]]/parent['response_file']
        parser=Links();parser.feed(path.read_text())
        if link['url'] not in [urljoin(parser.base or parent['url'],h) for h in parser.hrefs]:raise ValueError('Publication link changed')
    source=json.loads((BASE/'analysis-inputs.json').read_bytes())
    _,_,captured=validate_capture(ROOT/'research/conflict-investigation/2026-09-20')
    raw={r['object_id']:r['raw_feature'] for r in captured if r['source_id']=='organized-parcels'}
    corrections=json.loads((ROOT/'research/municipal-corroboration/report.json').read_bytes())['crosswalk']
    proposals={p['object_id']:p for p in corrections['proposals']}
    inputs=[]
    for row in source['corrections']:
        feature=raw[row['object_id']];p=proposals.get(row['object_id']);expected=dict(feature['properties'])
        if row['source_snapshot_sha256']!=corrections['source_snapshot_sha256']:raise ValueError('Unexpected correction snapshot')
        if row['correction_status']=='accepted':
            if p is None:raise ValueError('Accepted record lacks reviewed proposal')
            expected.update({k:v['to'] for k,v in p['changes'].items()})
        if expected!=row['effective_properties']:raise ValueError('Effective values do not match reviewed interpretation')
        inputs.append(effective_input(row,feature))
    for r in source['ut_records']:
        inputs.append(dict(r,source_snapshot_sha256=r['batch_id'],source_feature_sha256=digest(canonical(r['raw_feature']).encode()),
                           effective_properties=r['raw_feature']['properties'],holds=[],interpretation='source_record'))
    if len(inputs)!=2648 or len({r.get('correction_id',r.get('record_id')) for r in inputs})!=2648:raise ValueError('Pilot input scope differs')
    evaluated=[]
    zone_states=[]
    for z in zones:
        g,state,reason=geometry_state(z['raw_feature']);evaluated.append((z,g,state))
        zone_states.append({'object_id':z['object_id'],'geometry_state':state,'geometry_detail':reason,'properties':z['properties']})
    results=[]
    for r in inputs:
        code=r['effective_properties']['GEOCODE']
        if code not in ('09230','21110','17310','31020','31030'):raise ValueError('Unexpected effective jurisdiction')
        result=overlap_result(r['raw_feature'],evaluated,code=='09230')
        result.update(jurisdiction_code=code,source_holds=r['holds'],source_quality_flags=r['quality_flags'],
                      related_finding_ids=sorted(set(r['related_finding_ids']+['TL-F-0109' if code=='09230' else 'TL-F-0110']+(['TL-F-0025'] if code=='09230' else []))))
        results.append({'subject_id':r.get('correction_id',r.get('record_id')),
                        'correction_event_id':r.get('event_id'),
                        'source_feature_sha256':r['source_feature_sha256'],'result':result})
    dependencies=[METHOD,'scripts/collect_bounded_sources.py','scripts/collect_document_evidence.py',
      'scripts/prepare_source_staging.py','scripts/prepare_bounded_ingestion.py','scripts/export_zoning_inputs.sql',
      'scripts/prepare_zoning_reviews.py','supabase/migrations/20260920050000_zoning_screening.sql',
      'research/municipal-corroboration/report.json','research/conflict-investigation/2026-09-20/batch.json',
      'research/maine-ingestion/2026-09-20/batch.json']
    dependencies += [p.relative_to(ROOT).as_posix() for p in sorted(BASE.glob('*.json')) if p.name not in ('report.json','registry.json')]
    dependencies += [(BASE/'capture'/n).relative_to(ROOT).as_posix() for n in ('batch.json','registry.json')]
    report={'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),
       'runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str},
       'inputs':{n:digest((ROOT/n).read_bytes()) for n in dependencies},'evidence':evidence,'qualification':qualification,
       'scope':batch['plan'],'zone_snapshot_sha256':digest((BASE/'capture/batch.json').read_bytes()),
       'method_notes':['All captured MAP=osborn polygons retained, irrespective of date or publication flag; no authoritative legal-current filter established.',
          'Only valid raw polygonal geometry participates. No repair, snapping, PDF digitization, or assignment of neighboring LUPC zones to municipal jurisdictions.',
          'Areas in EPSG:26919 metres. Positive-area intersections retained without sliver threshold; zero-area touches recorded separately.',
          'Union coverage avoids double-counting; per-zone intersections may overlap and are not mutually exclusive. Fractions are bounded to [0,1] for floating-point roundoff.',
          'Municipal coverage unavailable means unknown, never unregulated. Legal zoning and buildability remain unknown.'],
       'zone_features':zone_states,'screenings':results,
       'summary':{'zoning_features':len(zones),'zone_geometry_states':dict(Counter(z['geometry_state'] for z in zone_states)),
         'inputs':len(inputs),'by_jurisdiction':dict(Counter(r['result']['jurisdiction_code'] for r in results)),
         'screening_states':dict(Counter(r['result']['status'] for r in results)),
         'intersection_rows':sum(len(r['result']['intersections']) for r in results),
         'records_with_source_holds':sum(bool(r['result']['source_holds']) for r in results),
         'records_near_invalid_zone':sum(bool(r['result']['invalid_zone_envelope_candidates']) for r in results)}}
    return report,inputs,zones,runs


def prepare_load(output,report,inputs,zones,runs):
    report_path=BASE/'report.json';report_bytes=report_path.read_bytes();sha=digest(report_bytes)
    old=json.loads((ROOT/'research/maine-sources/registry.json').read_bytes())
    sources=[]
    for sid in ('lupc-zoning','municipal-zoning'):
        entry=next(dict(x) for x in old['sources'] if x['id']==sid)
        entry.update(probe_ids=[v['id'] for k,v in report['evidence'].items()
            if (k.startswith('zones/') or any(s in v['id'] for s in ('lupc','osborn','kingsbury-spatial','kingsbury-neighbor','kingsbury-historical','kingsbury-published')))==(sid=='lupc-zoning')],
          coverage='Bounded pilot; see zoning-ingestion report qualification and exact predicates.',
          freshness='See preserved publisher fields, document review and unresolved current-zone selection.',
          rights='Private research archive only; no bulk redistribution license established.')
        entry['source_urls']=sorted({v['url'] for v in report['evidence'].values() if v['id'] in entry['probe_ids']})
        entry['access_status']='query_tested' if sid=='lupc-zoning' else 'partially_tested'
        entry['access']='383 Osborn features captured; one invalid polygon excluded from calculations.' if sid=='lupc-zoning' else 'Municipal publication routes tested; no usable digital polygons qualified; Alfred code request returned 403.'
        entry['limitations']=list(entry['limitations'])+['See qualification.json for this pilot; no current legal zone or buildability certified.']
        sources.append(entry)
    registry={'as_of':max(v['retrieved_at'] for v in report['evidence'].values()),'scope':'Bounded zoning pilot: Osborn GIS; municipal publication evidence and explicit unknown coverage.','sources':sources}
    (BASE/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    with tempfile.TemporaryDirectory() as tmp:
        audit=Path(tmp);shutil.copy(BASE/'registry.json',audit/'registry.json')
        for name,path in runs.items():shutil.copytree(path,audit/'runs'/name)
        prepare(audit,output,report_path)
    manifest=json.loads((output/'manifest.json').read_bytes())
    for name in report['inputs']:
        data=(ROOT/name).read_bytes();h=digest(data);key='sha256/'+h+'.response'
        (output/'objects'/key).write_bytes(data);manifest['objects'][key]={'sha256':h,'bytes':len(data)}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    registry_sha=manifest['registry_sha256']
    observations={r['id']:digest(canonical([registry_sha,'runs/zones',r]).encode()) for r in json.loads((runs['zones']/'results.json').read_bytes())}
    local_obs={}
    capture_registry=digest((BASE/'capture/registry.json').read_bytes())
    for r in json.loads((runs['zones']/'results.json').read_bytes()):local_obs[digest(canonical([capture_registry,'runs/bounded',r]).encode())]=observations[r['id']]
    # One transaction includes audit, features, results, and later prepared finding reviews.
    sql=(output/'load.sql').read_text().removesuffix('COMMIT;\n')
    sql+="SET LOCAL work_mem='32MB';\n"
    for z in zones:
        sql+='INSERT INTO ingest.zoning_feature(audit_sha256,object_id,observation_sha256,raw_feature) VALUES ('+','.join([literal(sha),str(z['object_id']),literal(local_obs[z['observation_id']]),jsql(z['raw_feature'])])+') ON CONFLICT DO NOTHING;\n'
    by_subject={r['subject_id']:r for r in report['screenings']}
    for inp in inputs:
        subject=inp.get('correction_id',inp.get('record_id'));r=by_subject[subject]
        values=[literal(sha),literal(subject),literal(inp['record_id']) if 'record_id' in inp else 'NULL',literal(inp['correction_id']) if 'correction_id' in inp else 'NULL',literal(inp['event_id']) if inp.get('event_id') else 'NULL',jsql(inp),jsql(r['result'])]
        sql+='INSERT INTO ingest.zoning_screening(audit_sha256,subject_id,source_record_id,correction_id,correction_event_id,input,result) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
    sql+='COMMIT;\n';(output/'load.sql').write_text(sql)
    print(json.dumps({'audit_sha256':sha,**report['summary']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);a=p.parse_args()
    report,inputs,zones,runs=build();(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    if a.prepare:prepare_load(a.prepare,report,inputs,zones,runs)
    else:print(json.dumps(report['summary'],indent=2))
