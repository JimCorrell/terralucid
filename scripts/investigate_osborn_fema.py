#!/usr/bin/env python3
"""Qualify captured Osborn FEMA evidence without repairing geometry or screening parcels."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pyproj
import shapely
from shapely.geometry import Polygon, box, shape
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity

from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql, verify

BASE = ROOT / 'research/osborn-fema'
METHOD = 'scripts/investigate_osborn_fema.py'
CRS = {'type': 'name', 'properties': {'name': 'EPSG:4269'}}
PART_SIZE = 20 * 1024 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def features(payload, spatial=False):
    require(not payload.get('error') and not payload.get('exceededTransferLimit')
            and isinstance(payload.get('features'), list), 'Failed/incomplete feature response')
    if spatial:
        require(payload.get('type') == 'FeatureCollection' and payload.get('crs') == CRS,
                'Expected explicit native NAD83 EPSG:4269')
        require(all(f.get('geometry') for f in payload['features']), 'Missing geometry')
    return payload['features']


def indexed(rows):
    result = {r['OBJECTID']: r for r in rows}
    require(len(result) == len(rows), 'Duplicate OBJECTID')
    return result


def reconcile(payload, rows):
    require(not payload.get('error') and not payload.get('exceededTransferLimit')
            and isinstance(payload.get('objectIds'), list), 'Failed ID query')
    ids = payload['objectIds']
    require(len(ids) == len(set(ids)) and set(ids) == set(indexed(rows)), 'Membership mismatch')


def parts(data):
    return [{'offset': offset, 'bytes': len(data[offset:offset+PART_SIZE]),
             'sha256': digest(data[offset:offset+PART_SIZE]),
             'storage_object': 'sha256/' + digest(data[offset:offset+PART_SIZE]) + '.response'}
            for offset in range(0, len(data), PART_SIZE)]


def restore(document, directory):
    chunks, offset = [], 0
    for part in document['parts']:
        require(part['offset'] == offset, 'Part order/offset mismatch')
        require(part['storage_object'] == 'sha256/' + part['sha256'] + '.response', 'Unsafe part key')
        data = (directory / part['storage_object']).read_bytes()
        require(len(data) == part['bytes'] and digest(data) == part['sha256'], 'Part integrity failure')
        chunks.append(data); offset += len(data)
    data = b''.join(chunks)
    require(len(data) == document['retrieval']['bytes']
            and digest(data) == document['retrieval']['sha256'], 'Original document integrity failure')
    return data


def build():
    evidence, payloads, inputs = {}, {}, {}
    def dependency(path, expected=None):
        data = (ROOT / path).read_bytes()
        require(expected is None or digest(data) == expected, 'Dependency drift: ' + path)
        inputs[path] = digest(data)
        return data
    for log in sorted((BASE / 'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            require(Path(r['response_file']).name == r['response_file'], 'Unsafe response path')
            p = log.parent / r['response_file']; data = p.read_bytes()
            require(digest(data) == r['sha256'] and len(data) == r['bytes'], 'Capture integrity failure')
            require(r['id'] not in payloads, 'Duplicate probe')
            evidence[log.parent.name + '/' + r['id']] = dict(r, response_path=p.relative_to(BASE).as_posix())
            payloads[r['id']] = (r, data)
    def parsed(name):
        r, data = payloads[name]
        require(r['http_status'] == 200, 'HTTP failure: ' + name)
        result = json.loads(data)
        require(not result.get('error'), 'API failure: ' + name)
        return result
    review = json.loads(dependency('research/osborn-fema/review.json'))
    plan = json.loads(dependency('research/osborn-fema/findings-plan.json'))
    original_log = json.loads(dependency('research/osborn-fema/large-documents/original-products-results.json'))
    large = json.loads(dependency('research/osborn-fema/large-documents/results.json'))
    require(len(large) == 1, 'Unexpected large-document capture')
    r = large[0]; data = (BASE / 'large-documents' / r['response_file']).read_bytes()
    require(r['http_status'] == 200 and data.startswith(b'%PDF-')
            and digest(data) == r['sha256'] and len(data) == r['bytes'], 'Large PDF integrity failure')
    require(original_log == [r] + json.loads((BASE/'runs/products/results.json').read_bytes()), 'Product log partition changed')
    document = {'retrieval': r, 'response_path': 'large-documents/' + r['response_file'],
                'parts': parts(data), 'encoding': 'Concatenate exact bytes in offset order; no compression or PDF rewrite.',
                'storage_reason': 'Original exceeds private bucket 50 MiB object limit; audit references parts, no ordinary source_response row for this PDF.'}
    all_refs = dict(evidence, **{'large-documents/osborn-lomr-document': r})
    for d in review['documents']:
        if d['evidence_ref'].startswith('prior:'):
            dependency(d['evidence_ref'][6:], d['sha256'])
        else:
            require(all_refs[d['evidence_ref']]['sha256'] == d['sha256'], 'Document review checksum mismatch')
    for p in sorted(BASE.glob('*queries.json')):
        dependency(p.relative_to(ROOT).as_posix())
    for path in ['research/osborn-fema/probes.json', 'research/osborn-fema/metadata.json',
                 'research/osborn-fema/discovery-followup.json', 'scripts/collect_document_evidence.py',
                 'scripts/collect_fema_catalog.py', 'scripts/collect_fema_products.py',
                 'scripts/prepare_source_staging.py', 'research/lupc-currency/report.json']:
        dependency(path)
    jurisdiction = parsed('osborn-jurisdiction')
    require(jurisdiction.get('spatialReference', {}).get('wkid') == 4269, 'Jurisdiction CRS mismatch')
    jf = features(jurisdiction)
    require(len(jf) == 1 and jf[0]['attributes']['CID'] == '230595'
            and jf[0]['attributes']['DFIRM_ID'] == '23009C', 'Unexpected jurisdiction')
    rings = jf[0]['geometry']['rings']
    require(len(rings) == 1, 'Review Esri ring roles before decoding changed boundary')
    j = Polygon(rings[0]); require(j.is_valid and not j.is_empty, 'Invalid jurisdiction')
    project = pyproj.Transformer.from_crs(4269, 26919, always_xy=True)
    jp = transform(project.transform, j)
    groups = {}
    for kind in ['availability', 'panels', 'lomr', 'loma']:
        fs = features(parsed(kind + '-features'), True)
        reconcile(parsed(kind + '-ids'), [f['properties'] for f in fs])
        groups[kind] = fs
    for name in ['availability', 'panels', 'lomr', 'loma', 'hazards']:
        q = parse_qs(urlparse(payloads[name+'-ids'][0]['url']).query)
        require(q.get('inSR') == ['4269'] and q.get('geometryType') == ['esriGeometryEnvelope']
                and q.get('spatialRel') == ['esriSpatialRelIntersects']
                and tuple(map(float, q['geometry'][0].split(','))) == j.bounds, 'Query scope/CRS mismatch')
    membership, spatial = {}, {}
    for kind, fs in groups.items():
        rows, clips = [], []
        for f in fs:
            g = shape(f['geometry']); require(g.is_valid and not g.is_empty, 'Invalid supporting geometry: '+kind)
            gp = transform(project.transform, g); require(gp.is_valid, 'Invalid projected supporting geometry')
            clip = gp.intersection(jp)
            keys = {'availability':['OBJECTID','STUDY_ID'], 'panels':['OBJECTID','FIRM_PAN','PANEL_TYP','EFF_DATE','PNP_REASON'],
                    'lomr':['OBJECTID','CASE_NO','EFF_DATE','STATUS','SOURCE_CIT'],
                    'loma':['OBJECTID','CASENUMBER','CID','STATUS','REVAL_STAT','OUTCOME']}[kind]
            rows.append(dict({k:f['properties'][k] for k in keys}, intersects_jurisdiction=not clip.is_empty,
                             intersection_area_m2=clip.area))
            if not clip.is_empty: clips.append(clip)
        membership[kind] = rows
        spatial[kind] = {'envelope_candidates':len(fs), 'intersecting_count':len(clips),
                         'intersection_union_area_m2':unary_union(clips).area}
    attrs = [f['attributes'] for name in sorted(payloads) if name.startswith('hazards-attributes-')
             for f in features(parsed(name))]
    hazard = [f for name in sorted(payloads) if name.startswith('hazards-geometry-')
              for f in features(parsed(name), True)]
    reconcile(parsed('hazards-ids'), attrs)
    reconcile(parsed('hazards-ids'), [f['properties'] for f in hazard])
    require(indexed(attrs) == indexed([f['properties'] for f in hazard]), 'Attributes changed between captures')
    grouped, invalid, retained, all_clips = defaultdict(list), [], [], []
    for f in sorted(hazard, key=lambda f: f['properties']['OBJECTID']):
        a = f['properties']; g = shape(f['geometry'])
        require(not g.is_empty and g.geom_type in ('Polygon','MultiPolygon'), 'Unexpected hazard geometry')
        if not g.is_valid:
            invalid.append({'attributes':a, 'reason':explain_validity(g), 'bounds_native_4269':list(g.bounds),
                            'bounding_box_intersects_jurisdiction':box(*g.bounds).intersects(j),
                            'disposition':'Preserved unchanged; excluded from all intersection/area calculations. No repair accepted.'})
            continue
        gp = transform(project.transform,g); require(gp.is_valid, 'Projection introduced invalidity')
        clip = gp.intersection(jp)
        if clip.area <= 0: continue
        key = (a['FLD_ZONE'], a['ZONE_SUBTY'], a['SFHA_TF'])
        grouped[key].append(clip);all_clips.append(clip);retained.append(a['OBJECTID'])
    hazard_result = {'envelope_candidates':len(hazard), 'attributes_and_geometry_membership_equal':True,
        'invalid_count':len(invalid), 'invalid_features':invalid, 'valid_positive_area_intersections':len(retained),
        'intersecting_OBJECTIDs':retained,
        'by_zone': [dict(zone=k[0], subtype=k[1], sfha=k[2], features=len(v), union_area_m2=unary_union(v).area)
                    for k,v in sorted(grouped.items(),key=lambda x:str(x[0]))],
        'valid_union_area_m2':unary_union(all_clips).area,
        'valid_union_coverage_fraction':unary_union(all_clips).area/jp.area,
        'limits':'Partial geometry coverage excluding invalid features; areas are NAD83 UTM19 planar unions, not legal boundaries, parcel determinations or clearance. Zone X subtypes remain distinct.'}
    catalog = parsed('catalog-osborn'); effective = catalog['EFFECTIVE']
    printed = sorted(r['FIRM_PAN'] for r in membership['panels'] if r['intersection_area_m2']>0 and r['PANEL_TYP']=='Countywide, Panel Printed')
    require(printed == sorted(r['product_NAME'] for r in effective['FIRM_PANEL']), 'Catalog/printed panel mismatch')
    panel_ids = sorted(r['FIRM_PAN'] for r in membership['panels'] if r['intersection_area_m2']>0)
    require(panel_ids == sorted(review['fis_osborn_panels']), 'GIS/FIS panel mismatch')
    lomr = effective['LOMR']
    require(len(lomr) == 1 and lomr[0]['product_NAME']=='22-01-0871P-230595'
            and lomr[0]['product_EFFECTIVE_DATE_STRING']=='01/08/2024', 'Catalog revision changed')
    main_lomr = next(r for r in membership['lomr'] if r['CASE_NO']=='22-01-0871P')
    require(datetime.fromtimestamp(main_lomr['EFF_DATE']/1000,timezone.utc).date().isoformat()
            == review['lomr_effective_date'], 'Letter/service effective date mismatch')
    by_cid = features(parsed('osborn-loma-by-cid'))
    study = features(parsed('hancock-study'))
    require(len(study)==1 and study[0]['attributes']['DFIRM_ID']=='23009C', 'Unexpected study')
    return {'evidence_state':'DERIVED', 'method':METHOD, 'method_sha256':digest((ROOT/METHOD).read_bytes()),
        'scope':review['scope'], 'evidence':evidence, 'inputs':inputs, 'large_document_evidence':document,
        'environment':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str},
        'geometry_method':{'source_crs':'EPSG:4269 NAD83','area_crs':'EPSG:26919 NAD83 UTM19N',
                           'transform':project.description,'repair':False,'parcel_overlay':False},
        'jurisdiction':{'attributes':jf[0]['attributes'],'bounds_native_4269':list(j.bounds),'area_m2':jp.area,
                         'authority':'FEMA jurisdiction screening scope; not surveyed or legal parcel boundary'},
        'spatial_summary':spatial,'membership':membership,'hazards':hazard_result,
        'study_info':study[0]['attributes'], 'osborn_CID_loma_query_count':len(by_cid),
        'catalog_summary':{k:len(v) for k,v in effective.items()},
        'date_reconciliation':{'catalog_field':'product_EFFECTIVE_DATE_STRING','catalog_value':'01/08/2024',
            'letter_issue_date':review['lomr_issue_date'],'letter_and_NFHL_effective_date':review['lomr_effective_date'],
            'interpretation':'This catalog field records the issue date for this product; preserve raw value. Do not infer a global catalog-date correction.'},
        'document_review':review,'findings_plan':plan,
        'qualification':{'effective_FEMA_revision_for_Osborn':'VERIFIED document and service agreement for 22-01-0871P',
                         'complete_revision_history':'UNKNOWN','LUPC_adoption_of_2024_revision':'UNKNOWN',
                         'site_or_parcel_applicability':'UNKNOWN','statewide_coverage':'NOT_EVALUATED',
                         'geometry_or_screening_changes':False}}


def prepare_load(report, output, current):
    prepare(BASE, output, BASE/'report.json')
    manifest = json.loads((output/'manifest.json').read_bytes())
    def archive(data):
        sha=digest(data);key='sha256/'+sha+'.response'
        (output/'objects'/key).write_bytes(data);manifest['objects'][key]={'sha256':sha,'bytes':len(data)}
    for path, sha in report['inputs'].items():
        data=(ROOT/path).read_bytes();require(digest(data)==sha,'Changed input');archive(data)
    document=report['large_document_evidence'];data=(BASE/document['response_path']).read_bytes()
    require(parts(data)==document['parts'],'Changed large document')
    for part in document['parts']:archive(data[part['offset']:part['offset']+part['bytes']])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows={r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    plan=report['findings_plan'];sha=digest((BASE/'report.json').read_bytes())
    sql=(output/'load.sql').read_text().removesuffix('COMMIT;\n')
    for d in plan['new_findings']:
        require(d['finding_id'] not in rows, 'New finding ID already exists; inspect definition')
        values=[literal(d['finding_id']),literal(d['title']),literal(d['description']),
                'ARRAY['+','.join(map(literal,d['source_ids']))+']::text[]',jsql(d['scope']),literal(d['evidence_state'])]
        sql+='INSERT INTO ingest.finding(finding_id,title,description,source_ids,scope,evidence_state) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
        sql+='DO '+literal("BEGIN IF NOT EXISTS (SELECT 1 FROM ingest.finding f WHERE finding_id="+literal(d['finding_id'])+" AND to_jsonb(f)-'created_at'="+jsql(d)+") THEN RAISE EXCEPTION 'Finding definition differs'; END IF; END")+';\n'
    new_ids={d['finding_id'] for d in plan['new_findings']}
    for r in plan['reviews']:
        fid=r['finding_id'];require(fid in rows or fid in new_ids,'Missing prior finding token')
        event={k:v for k,v in r.items() if k!='report_pointer'}
        event.update(event_id=digest(canonical([fid,sha,'fema-review']).encode()),actor='TerraLucid FEMA qualification',evidence_refs=['audit:'+sha+'#'+r['report_pointer']])
        occurrence=digest(canonical([fid,sha,'fema-qualification']).encode())
        sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(occurrence),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        old=rows.get(fid,{}).get('event_id')
        sql+='SELECT ingest.record_finding_event('+jsql(event)+','+(literal(old) if old else 'NULL')+');\n'
    (output/'load.sql').write_text(sql+'COMMIT;\n')
    print(json.dumps({'audit_sha256':sha,'objects':len(manifest['objects'])}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path)
    p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path)
    a=p.parse_args()
    if a.verify_download:
        if not a.prepared:p.error('--verify-download requires --prepared')
        print(verify(a.prepared,a.verify_download))
        report=json.loads((BASE/'report.json').read_bytes())
        require(digest((BASE/'report.json').read_bytes()) in [v['sha256'] for v in json.loads((a.prepared/'manifest.json').read_bytes())['objects'].values()], 'Report not archived')
        restore(report['large_document_evidence'],a.verify_download)
        print('Exact original large PDF reconstructed and verified')
    else:
        if a.prepare and not a.current:p.error('--prepare requires --current')
        report=build();(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(report,a.prepare,a.current)
        else:print(json.dumps({'features':report['hazards']['envelope_candidates'],'invalid':report['hazards']['invalid_count']}))
