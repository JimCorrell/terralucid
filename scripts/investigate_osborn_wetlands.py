#!/usr/bin/env python3
"""Qualify a bounded NWI snapshot; preserve native rings and exclude invalid decodings."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import shapely
import pyproj
from shapely.geometry import Polygon, MultiPolygon, LinearRing
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity
from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql, verify

BASE = ROOT/'research/osborn-wetlands'
METHOD = 'scripts/investigate_osborn_wetlands.py'


def require(ok, message):
    if not ok: raise ValueError(message)


def decode(rings):
    """Esri clockwise shells, counterclockwise holes; no repair or reorientation.

    Ambiguous/non-simple rings are held, not fed into overlay calculations.
    A hole must have exactly one containing shell. All source vertices are retained.
    """
    if not rings: return None, 'Missing rings'
    shells, holes = [], []
    for ring in rings:
        if len(ring) < 4 or ring[0] != ring[-1] or any(len(p) != 2 for p in ring):
            return None, 'Nonclosed/unsupported ring'
        p = Polygon(ring)
        if p.is_empty or not p.is_valid: return None, explain_validity(p)
        (holes if LinearRing(ring).is_ccw else shells).append(p)
    if not shells: return None, 'No clockwise shell'
    assigned = [[] for _ in shells]
    for hole in holes:
        owners = [i for i,s in enumerate(shells) if s.covers(hole)]
        if len(owners) != 1: return None, 'Ambiguous/uncontained hole'
        assigned[owners[0]].append(list(hole.exterior.coords))
    polygons = [Polygon(s.exterior.coords,h) for s,h in zip(shells,assigned)]
    result = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
    if not result.is_valid: return None, explain_validity(result)
    return result, None


def reconcile(payload, expected, key, joined=False):
    require('error' not in payload and not payload.get('exceededTransferLimit'), 'API error/truncated page')
    require(payload.get('spatialReference',{}).get('latestWkid',payload.get('spatialReference',{}).get('wkid')) == 3857,'Changed native CRS')
    rows = payload['features']; actual = [f['attributes'][key] for f in rows]
    require(set(actual) == set(expected) and (joined or len(actual) == len(set(actual))),'Missing/duplicate/unexpected feature IDs')
    require(all(set(f['geometry']) == {'rings'} for f in rows),'Unsupported geometry')
    return rows


def group_source_rows(rows):
    """Group only identical native source records; retain every lookup conflict."""
    groups = defaultdict(list)
    for f in rows: groups[f['attributes']['Wetlands.OBJECTID']].append(f)
    source_rows, joined_conflicts = [], []
    for oid,variants in sorted(groups.items()):
        cores = [dict(geometry=f['geometry'],attributes={k:v for k,v in f['attributes'].items() if k.startswith('Wetlands.')}) for f in variants]
        require(len({canonical(c) for c in cores}) == 1,'Conflicting native feature versions; hold capture')
        source_rows.append(cores[0])
        attributes = [f['attributes'] for f in variants]
        differences = {k:sorted({canonical(a[k]) for a in attributes}) for k in attributes[0] if len({canonical(a[k]) for a in attributes}) > 1}
        if differences:
            joined_conflicts.append({'objectid':oid,'attribute':cores[0]['attributes']['Wetlands.ATTRIBUTE'],'differing_join_fields':{k:[json.loads(v) for v in vals] for k,vals in differences.items()},'interpretation_hold':'Preserve all code-join variants; do not select one joined definition.'})
    return source_rows, joined_conflicts


def build():
    inputs, evidence, payloads = {}, {}, {}
    def dependency(path, expected=None):
        data = (ROOT/path).read_bytes()
        require(expected is None or digest(data) == expected,'Changed dependency: '+path)
        inputs[path] = digest(data); return data
    dependency('research/osborn-fema/report.json','2f106e1b19fa2b13415741a109d34f1f9dbc4fdb04cf67e77fe882325aebe5ff')
    jurisdiction = json.loads(dependency('research/osborn-fema/runs/identity/osborn-jurisdiction.response','813824533f6c03c71fb8024431e0bd9f86e10b46c8e9ba12eb9c2ddf4d13696a'))
    for path in sorted(BASE.glob('*probes.json')): dependency(path.relative_to(ROOT).as_posix())
    for path in ['scripts/prepare_source_staging.py','scripts/collect_document_evidence.py']:
        dependency(path)
    review = json.loads(dependency('research/osborn-wetlands/review.json'))
    plan = json.loads(dependency('research/osborn-wetlands/findings-plan.json'))
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            require(Path(r['response_file']).name == r['response_file'],'Unsafe path')
            path = log.parent/r['response_file']; data = path.read_bytes()
            require(digest(data) == r['sha256'] and len(data) == r['bytes'],'Changed source')
            require(r['http_status'] == 200,'Failed source: '+r['id'])
            evidence[log.parent.name+'/'+r['id']] = dict(r,response_path=path.relative_to(BASE).as_posix())
            require(r['id'] not in payloads,'Duplicate probe'); payloads[r['id']] = data
    def parsed(name):
        d = json.loads(payloads[name]); require('error' not in d and not d.get('exceededTransferLimit'),'Incomplete response: '+name);return d
    require(jurisdiction['spatialReference']['wkid'] == 4269 and len(jurisdiction['features']) == 1,'Wrong scope')
    jf = jurisdiction['features'][0]
    require(jf['attributes']['CID'] == '230595' and jf['attributes']['DFIRM_ID'] == '23009C','Wrong Osborn identity')
    require(len(jf['geometry']['rings']) == 1,'Changed scope topology')
    j = Polygon(jf['geometry']['rings'][0]);require(j.is_valid,'Invalid scope')
    scope_transform = pyproj.Transformer.from_crs(4269,26919,always_xy=True)
    native_transform = pyproj.Transformer.from_crs(3857,26919,always_xy=True)
    scope = transform(scope_transform.transform,j)
    ids = parsed('wetland-ids')['objectIds']
    require(len(set(ids)) == parsed('wetland-count')['count'],'Distinct identifier/count mismatch')
    require(sorted(ids) == sorted(parsed('wetland-ids-end')['objectIds']),'Wetland membership changed')
    require(parsed('nwi-layer') == parsed('wetland-layer-end'),'Wetland metadata changed')
    rows, page_ids = [], []
    for probe in json.loads((BASE/'feature-probes.json').read_bytes()):
        if not probe['id'].startswith('wetland-page-'):continue
        expected = list(map(int,parse_qs(urlparse(probe['url']).query)['objectIds'][0].split(',')))
        require(0 < len(expected) <= 50 <= parsed('nwi-layer')['maxRecordCount'],'Page exceeds limit')
        page_ids.extend(expected); rows.extend(reconcile(parsed(probe['id']),expected,'Wetlands.OBJECTID',joined=True))
    require(Counter(page_ids) == Counter(ids),'Page plan differs from captured ID list')
    raw_row_count = len(rows)
    rows, joined_conflicts = group_source_rows(rows)
    profiles, valid_intersections, classifications, codes = [], [], Counter(), Counter()
    globalids = []
    for f in sorted(rows,key=lambda f:f['attributes']['Wetlands.OBJECTID']):
        a = f['attributes'];globalids.append(a['Wetlands.GLOBALID']);classifications[a['Wetlands.WETLAND_TYPE']] += 1;codes[a['Wetlands.ATTRIBUTE']] += 1
        g,reason = decode(f['geometry']['rings'])
        record = {'objectid':a['Wetlands.OBJECTID'],'globalid':a['Wetlands.GLOBALID'],'attribute':a['Wetlands.ATTRIBUTE'],'wetland_type':a['Wetlands.WETLAND_TYPE'],'native_geometry_sha256':digest(canonical(f['geometry']).encode()),'decode_hold':reason,'intersection_area_m2':None}
        if g is not None:
            local = transform(native_transform.transform,g)
            if not local.is_valid:record['decode_hold'] = 'Invalid after projection: '+explain_validity(local)
            else:
                intersection = local.intersection(scope);record['intersection_area_m2'] = intersection.area
                if intersection.area > 0:valid_intersections.append(intersection)
        profiles.append(record)
    coverage = {}
    for name in ['image-year','mapping-status']:
        expected = parsed(name+'-ids')['objectIds']
        require(len(expected) == len(set(expected)) == parsed(name+'-count')['count'],'Coverage count mismatch')
        require(sorted(expected) == sorted(parsed(name+'-ids-end')['objectIds']),'Coverage membership changed')
        require(parsed(name+'-layer') == parsed(name+'-layer-end'),'Coverage metadata changed')
        features = reconcile(parsed(name+'-features'),expected,'OBJECTID')
        polygons, records = [], []
        for f in features:
            g,reason = decode(f['geometry']['rings']);local = transform(native_transform.transform,g) if g is not None else None
            if local is not None and not local.is_valid:reason = 'Invalid projected coverage';local = None
            if local is not None:polygons.append(local)
            records.append({'attributes':f['attributes'],'decode_hold':reason,'scope_intersection_area_m2':local.intersection(scope).area if local is not None else None})
        uncovered = scope.difference(unary_union(polygons)).area if len(polygons) == len(features) else None
        coverage[name] = {'features':records,'scope_uncovered_area_m2':uncovered,'interpretation':'Mapping availability / imagery lineage only; not completeness of real wetlands or regulatory coverage.'}
    require([c['objectid'] for c in joined_conflicts] == plan['new_findings'][0]['scope']['objectids'],'Classification conflict scope changed; review again')
    require(all(f['attributes']['IMAGE_YR'] == 1983 and f['attributes']['IMAGE_DATE'] == '05/83' for f in coverage['image-year']['features']),'Image dates changed; review again')
    valid_areas = [p for p in profiles if p['intersection_area_m2'] is not None and p['intersection_area_m2'] > 0]
    summary = {'envelope_features':len(rows),'identifier_rows':len(ids),'raw_feature_rows_across_pages':raw_row_count,'repeated_identifier_excess':len(ids)-len(set(ids)),'conflicting_code_joins':len(joined_conflicts),'decoded_without_repair':sum(p['decode_hold'] is None for p in profiles),'held_features':sum(p['decode_hold'] is not None for p in profiles),'positive_area_scope_intersections':len(valid_areas),'valid_mapped_wetland_and_deepwater_union_m2':unary_union(valid_intersections).area,'scope_area_m2':scope.area,'globalid_missing':sum(not x for x in globalids),'globalid_duplicate_excess':len([x for x in globalids if x])-len(set(x for x in globalids if x)),'classification_counts_in_envelope':dict(sorted(classifications.items())),'attribute_counts_in_envelope':dict(sorted(codes.items()))}
    return {'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),'evidence':evidence,'inputs':inputs,'review':review,'findings_plan':plan,'summary':summary,'features':profiles,'coverage':coverage,'joined_code_conflicts':joined_conflicts,
      'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str},
      'scope':{'definition':'Prior FEMA CID 230595 jurisdiction; bounded source qualification, not legal/surveyed boundary. Envelope includes neighboring features.','envelope_epsg4269':list(j.bounds),'area_crs':'EPSG:26919','native_service_crs':'EPSG:3857','transformations':[{'definition':t.get_last_used_operation().definition,'reported_accuracy_m':t.get_last_used_operation().accuracy} for t in [scope_transform,native_transform]],'boundary_dependency':'All intersections/coverage depend on this exact FEMA jurisdiction version. No parcel screening.'},
      'checks':{'counts_ids_pages_reconciled':True,'start_end_metadata_and_ids_equal':True,'same_id_edits_during_capture_not_excluded':'No editingInfo version token; start/end membership and metadata do not prove atomicity.','globalid_persistence_across_releases':'UNKNOWN'},
      'finding_reviews':[{'finding_id':'TL-F-0117','status':'in_progress','priority':'medium','report_pointer':'/summary','note':'Bounded Osborn NWI inventory, source-imagery and availability evidence preserved. Image metadata is May 1983 with later NHD stream additions. Distinct IDs reconcile to the count; eight IDs have conflicting joined classification definitions, held without choosing a definition. Native geometry is retained and unsupported/invalid decodings held. Maine package ingestion, cross-release identity, present-day accuracy and regulatory boundaries remain unqualified.','next_action':review['next_action']}] + plan['reviews']}


def prepare_load(report, output, current):
    prepare(BASE,output,BASE/'report.json')
    manifest = json.loads((output/'manifest.json').read_bytes())
    for path,sha in report['inputs'].items():
        data = (ROOT/path).read_bytes();require(digest(data) == sha,'Changed input');require(len(data) <= 52428800,'Oversized object')
        key = 'sha256/'+sha+'.response';(output/'objects'/key).write_bytes(data);manifest['objects'][key] = {'sha256':sha,'bytes':len(data)}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows = {r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    sha = digest((BASE/'report.json').read_bytes());sql = (output/'load.sql').read_text().removesuffix('COMMIT;\n')
    for d in report['findings_plan']['new_findings']:
        require(d['finding_id'] not in rows,'Finding ID already exists; inspect before preparing')
        values = [literal(d['finding_id']),literal(d['title']),literal(d['description']),'ARRAY['+','.join(map(literal,d['source_ids']))+']::text[]',jsql(d['scope']),literal(d['evidence_state'])]
        sql += 'INSERT INTO ingest.finding(finding_id,title,description,source_ids,scope,evidence_state) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
        sql += 'DO '+literal("BEGIN IF NOT EXISTS (SELECT 1 FROM ingest.finding f WHERE finding_id="+literal(d['finding_id'])+" AND to_jsonb(f)-'created_at'="+jsql(d)+") THEN RAISE EXCEPTION 'Finding definition differs'; END IF; END")+';\n'
    for r in report['finding_reviews']:
        fid = r['finding_id'];require(fid in rows or fid in {d['finding_id'] for d in report['findings_plan']['new_findings']},'Missing current finding token');eid = digest(canonical([fid,sha,'wetlands']).encode())
        event = {k:v for k,v in r.items() if k != 'report_pointer'}
        event.update(event_id=eid,actor='TerraLucid Osborn wetlands source qualification',evidence_refs=['audit:'+sha+'#'+r['report_pointer'],'audit:'+sha+'#/review'])
        sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(eid),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        sql += 'SELECT ingest.record_finding_event('+jsql(event)+','+(literal(rows[fid]['event_id']) if fid in rows else 'NULL')+');\n'
    (output/'load.sql').write_text(sql+'COMMIT;\n')
    print(json.dumps({'audit_sha256':sha,'archive_objects':len(manifest['objects'])}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path)
    p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path)
    a = p.parse_args()
    if a.verify_download:
        if not a.prepared:p.error('--verify-download requires --prepared')
        require('sha256/'+digest((BASE/'report.json').read_bytes())+'.response' in json.loads((a.prepared/'manifest.json').read_bytes())['objects'],'Current report absent from prepared archive')
        print(verify(a.prepared,a.verify_download))
    else:
        if a.prepare and not a.current:p.error('--prepare requires --current')
        report = build();(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(report,a.prepare,a.current)
        else:print(json.dumps(report['summary'],indent=2))
