#!/usr/bin/env python3
"""Resolve the exact eight-record NWI lookup ambiguity using publisher references."""
import argparse
import ast
import csv
import hashlib
import io
import json
import shutil
import sqlite3
import struct
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import shapely
import pyproj
from shapely import from_wkb
from shapely.ops import transform
from investigate_osborn_wetlands import decode, reconcile, group_source_rows
from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql, verify

BASE = ROOT/'research/wetlands-classification'
METHOD = 'scripts/investigate_wetlands_classification.py'
PRIOR = 'e1449e8384d5d712dfdae9df26814330d1b9f7dc31ae82fc8765bce565b61906'
CSV_MEMBER = 'NWI-Code-Definitions/NWI_Code_Definitions.csv'
PY_MEMBER = 'WetlandsCodeChecker112/wetlands-code-checker-interpreter_external1.1.2.py'
GPKG_MEMBER = 'ME_geopackage_wetlands.gpkg'


def require(ok,message):
    if not ok:raise ValueError(message)


def stream_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def gpkg_geometry(blob):
    require(blob[:2] == b'GP' and blob[2] == 0,'Unsupported GeoPackage geometry')
    flags = blob[3];env = (flags>>1)&7
    require(not flags&0b11110000 and env in range(5),'Extended/empty/unsupported GeoPackage geometry')
    order = '<' if flags&1 else '>'
    require(struct.unpack(order+'i',blob[4:8])[0] == 300001,'Unexpected package geometry SRS')
    offset = 8+{0:0,1:32,2:48,3:48,4:64}[env]
    g = from_wkb(blob[offset:]);require(g.geom_type in ['Polygon','MultiPolygon'] and g.is_valid and not g.is_empty,'Invalid candidate geometry')
    return g


def choose_lookup(variants, reference):
    """Only CSV empty strings and service nulls are treated as equivalent."""
    matches, disagreements = [], []
    for attrs in variants:
        differences = {k:{'service':attrs['NWI_Wetland_Codes.'+k],'reference':v} for k,v in reference.items()
                       if (attrs['NWI_Wetland_Codes.'+k] if attrs['NWI_Wetland_Codes.'+k] != '' else None) != (v if v != '' else None)}
        if differences:disagreements.append({'lookup_objectid':attrs['NWI_Wetland_Codes.OBJECTID'],'differences':differences})
        else:matches.append(attrs)
    require(len(matches) == 1,'No unique complete reference match; retain hold')
    return matches[0],disagreements


def literal_dictionaries(data):
    """Read publisher data literals without executing downloaded Python."""
    tree = ast.parse(data);result = {}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ['ParsedCodeDict','ParsedCodeDict2']:
            result[node.targets[0].id] = ast.literal_eval(node.value)
    require(set(result) == {'ParsedCodeDict','ParsedCodeDict2'},'Changed decoder data structure')
    return result


def build():
    inputs, evidence, payloads = {}, {}, {}
    def dependency(path,expected=None):
        data = (ROOT/path).read_bytes();require(expected is None or digest(data) == expected,'Changed dependency: '+path)
        inputs[path] = digest(data);return data
    prior = json.loads(dependency('research/osborn-wetlands/report.json',PRIOR))
    for path in ['scripts/investigate_osborn_wetlands.py','scripts/prepare_source_staging.py','scripts/collect_document_evidence.py','scripts/collect_maine_wetlands_package.py']:
        dependency(path)
    for path in BASE.glob('*probes.json'):dependency(path.relative_to(ROOT).as_posix())
    review = json.loads(dependency('research/wetlands-classification/review.json'))
    package = json.loads(dependency('research/wetlands-classification/package-capture.json'))
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            require(Path(r['response_file']).name == r['response_file'],'Unsafe response path')
            path = log.parent/r['response_file'];data = path.read_bytes()
            require(r['http_status'] == 200 and digest(data) == r['sha256'] and len(data) == r['bytes'],'Changed/failed evidence')
            evidence[log.parent.name+'/'+r['id']] = dict(r,response_path=path.relative_to(BASE).as_posix())
            require(r['id'] not in payloads,'Duplicate probe');payloads[r['id']] = data
    ids = [x['objectid'] for x in prior['joined_code_conflicts']]
    old = []
    for name in ['wetland-page-10','wetland-page-11']:
        r = prior['evidence']['features/'+name]
        data = dependency('research/osborn-wetlands/'+r['response_path'],r['sha256'])
        old.extend(f for f in json.loads(data)['features'] if f['attributes']['Wetlands.OBJECTID'] in ids)
    current = reconcile(json.loads(payloads['current-eight-features']),ids,'Wetlands.OBJECTID',joined=True)
    cores,_ = group_source_rows(current);oldcores,_ = group_source_rows(old)
    require(canonical(cores) == canonical(oldcores),'Native records changed; new source review required')
    require({canonical(f) for f in old} == {canonical(f) for f in current},'Lookup variants changed; review again')
    with zipfile.ZipFile(io.BytesIO(payloads['code-definitions'])) as z:
        csvbytes = z.read(CSV_MEMBER)
        metadata_bytes = z.read('NWI-Code-Definitions/NWI_Code_Definitions_Metadata.xml')
    metadata = ET.fromstring(metadata_bytes)
    reference_metadata = {n:[e.text for e in metadata.iter(n)] for n in ['pubdate','metd','accconst','useconst']}
    definitions = list(csv.DictReader(io.StringIO(csvbytes.decode('utf-8-sig'))))
    refs = {}
    for code in ['PUBFh','PUBFx']:
        selected = [r for r in definitions if r['ATTRIBUTE'] == code];require(len(selected) == 1,'Reference code not unique');refs[code] = selected[0]
    with zipfile.ZipFile(io.BytesIO(payloads['code-interpreter'])) as z:pybytes = z.read(PY_MEMBER)
    dictionaries = literal_dictionaries(pybytes)
    decoder_check = {}
    for code,row in refs.items():
        labels = {k:dictionaries[d][token] for k,d,token in [('system','ParsedCodeDict','P'),('class','ParsedCodeDict','UB'),('water_regime','ParsedCodeDict2','F'),('modifier','ParsedCodeDict2',code[-1])]}
        for key,field,token in [('system','SYSTEM_NAME','P'),('class','CLASS_NAME','UB'),('water_regime','WATER_REGIME_NAME','F'),('modifier','MODIFIER1_NAME',code[-1])]:
            require(labels[key].startswith(row[field]+' ('+token+'): '),'Decoder/table disagree')
        decoder_check[code] = labels
    archive = BASE/package['response_path']
    require(archive.stat().st_size == package['bytes'] and stream_hash(archive) == package['sha256'],'Changed package')
    with zipfile.ZipFile(archive) as z:
        require(z.namelist() == [GPKG_MEMBER],'Changed package members')
        gpkg = BASE/'package/maine.gpkg'
        # Extraction to a working copy never alters the preserved ZIP. ZipFile checks CRC.
        with z.open(GPKG_MEMBER) as src,gpkg.open('wb') as dst:shutil.copyfileobj(src,dst)
        gpkg_info = {'member':GPKG_MEMBER,'bytes':z.getinfo(GPKG_MEMBER).file_size,'sha256':stream_hash(gpkg)}
    db = sqlite3.connect(gpkg.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory = sqlite3.Row
    wkt = db.execute('select definition from gpkg_spatial_ref_sys where srs_id=300001').fetchone()[0]
    crs = pyproj.CRS.from_wkt(wkt);project = pyproj.Transformer.from_crs(3857,crs,always_xy=True)
    records = []
    for core in cores:
        oid = core['attributes']['Wetlands.OBJECTID'];code = core['attributes']['Wetlands.ATTRIBUTE']
        variants = {canonical(f['attributes']):f['attributes'] for f in current if f['attributes']['Wetlands.OBJECTID'] == oid}
        winner,disagreements = choose_lookup(list(variants.values()),refs[code])
        require(len(variants) == 2 and len(disagreements) == 1,'Changed conflict cardinality')
        g,hold = decode(core['geometry']['rings']);require(hold is None,'Invalid native geometry')
        g = transform(project.transform,g);xmin,ymin,xmax,ymax = g.bounds
        # Broad spatial candidates only: do not join on service OBJECTID or GlobalID.
        candidates = db.execute('select w.* from ME_Wetlands w join rtree_ME_Wetlands_Shape r on r.id=w.OBJECTID where r.minx<=? and r.maxx>=? and r.miny<=? and r.maxy>=?',(xmax+2,xmin-2,ymax+2,ymin-2)).fetchall()
        metrics = []
        for row in candidates:
            other = gpkg_geometry(row['Shape']);distance = g.hausdorff_distance(other)
            metrics.append({'package_objectid':row['OBJECTID'],'NWI_ID':row['NWI_ID'],'ATTRIBUTE':row['ATTRIBUTE'],'WETLAND_TYPE':row['WETLAND_TYPE'],'geometry_blob_sha256':digest(row['Shape']),'hausdorff_distance_m':distance,'symmetric_difference_m2':g.symmetric_difference(other).area,'candidate_within_2m':distance <= 2})
        near = [m for m in metrics if m['candidate_within_2m']]
        require(len(near) == 1 and near[0]['ATTRIBUTE'] == code,'Package corroboration ambiguous/disagrees')
        records.append({'service_objectid':oid,'service_globalid':core['attributes']['Wetlands.GLOBALID'],'native_core_sha256':digest(canonical(core).encode()),'prior_native_geometry_sha256':digest(canonical(core['geometry']).encode()),'ATTRIBUTE':code,'selected_lookup_objectid':winner['NWI_Wetland_Codes.OBJECTID'],'selected_lookup_sha256':digest(canonical({k:v for k,v in winner.items() if k.startswith('NWI_Wetland_Codes.')}).encode()),'reference_row_sha256':digest(canonical(refs[code]).encode()),'interpretation_evidence_state':'DERIVED','interpretation_status':'reviewed_reference_match','remaining_variants':disagreements,'package_candidates':metrics,'package_identity_state':'INFERRED spatial counterpart only; different identifiers and non-identical projected boundary'})
    count = db.execute('select count(*) from ME_Wetlands').fetchone()[0];db.close()
    return {'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),'evidence':evidence,'inputs':inputs,'review':review,'prior_audit_sha256':PRIOR,'records':records,'reference_rows':refs,'decoder_labels':decoder_check,'reference_metadata':reference_metadata,
      'reference_members':{'csv':{'member':CSV_MEMBER,'sha256':digest(csvbytes)},'python':{'member':PY_MEMBER,'sha256':digest(pybytes),'execution':'Not executed; named literal dictionaries read using AST literal_eval.'}},
      'package':dict(package,extracted=gpkg_info,inventory_rows=count,srs_wkt=wkt,comparison_operation=project.get_last_used_operation().definition,comparison_reported_accuracy_m=project.get_last_used_operation().accuracy,scope='Entire ZIP archived; eight-record comparison only. Not statewide feature ingestion or identity/geometry reconciliation.'),
      'checks':{'native_records_and_lookup_variants_unchanged':True,'unique_reference_row_per_code':True,'exact_complete_reference_match_per_feature':True,'empty_csv_fields_normalized_to_null':True,'package_spatial_candidates_agree_on_code':True,'upstream_lookup_defect_still_present':True},
      'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str,'sqlite':sqlite3.sqlite_version},
      'finding_reviews':[{'finding_id':'TL-F-0027','status':'resolved','priority':'medium','report_pointer':'/records','note':'The exact eight-record lookup ambiguity is resolved for interpretation: official CSV has one row per PUBFh/PUBFx, matching the complete service variant in every reference field; official decoder labels agree. Preserve competing rows with eight missing fields. Upstream duplicate lookup remains present; publisher repair is not claimed. Package spatial candidates corroborate codes, not canonical identity or exact geometry.','next_action':'Use the pinned reference-matched interpretation for these exact records. On new snapshots recheck core/lookup hashes and reference versions; reopen for discrepancies. Do not use repeated joined rows as separate wetlands.'},{'finding_id':'TL-F-0117','status':'in_progress','priority':'medium','report_pointer':'/package','note':'Maine package archived intact and compared for the eight conflicted codes. Candidate counterparts agree on classifications, but package NWI_ID differs from service GlobalID and projected boundaries differ by about a metre. This is not statewide loading or identity/geometry reconciliation. Old-image and legal applicability qualifications remain. TL-F-0028 is unchanged.','next_action':'Investigate TL-F-0028 availability geometry. Before wider ingestion reconcile package/service identity and projection, qualify package/project coverage and refresh behavior, and retain imagery age plus field/regulatory due diligence.'}]}


def prepare_load(report,output,current):
    prepare(BASE,output,BASE/'report.json');manifest = json.loads((output/'manifest.json').read_bytes())
    def archive(data):
        sha = digest(data);key = 'sha256/'+sha+'.response';require(len(data) <= 52428800,'Oversize archive object')
        (output/'objects'/key).write_bytes(data);manifest['objects'][key] = {'sha256':sha,'bytes':len(data)}
    for path,sha in report['inputs'].items():
        data = (ROOT/path).read_bytes();require(digest(data) == sha,'Changed input');archive(data)
    with (BASE/report['package']['response_path']).open('rb') as f:
        for part in report['package']['parts']:
            require(f.tell() == part['offset'],'Bad part offset');data = f.read(part['bytes']);require(digest(data) == part['sha256'],'Bad part hash');archive(data)
        require(not f.read(1),'Unarchived package tail')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows = {r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    sha = digest((BASE/'report.json').read_bytes());sql = (output/'load.sql').read_text().removesuffix('COMMIT;\n')
    for r in report['finding_reviews']:
        fid = r['finding_id'];eid = digest(canonical([fid,sha,'wetlands-classification']).encode());require(fid in rows,'Missing prior review')
        event = {k:v for k,v in r.items() if k != 'report_pointer'}
        event.update(event_id=eid,actor='TerraLucid wetlands classification review',evidence_refs=['audit:'+sha+'#'+r['report_pointer'],'audit:'+sha+'#/review'])
        sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(eid),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        sql += 'SELECT ingest.record_finding_event('+jsql(event)+','+literal(rows[fid]['event_id'])+');\n'
    (output/'load.sql').write_text(sql+'COMMIT;\n');print(json.dumps({'audit_sha256':sha,'archive_objects':len(manifest['objects'])}))


def verify_package(report,download):
    h = hashlib.sha256();size = 0
    for p in report['package']['parts']:
        data = (download/p['storage_object']).read_bytes();require(size == p['offset'] and len(data) == p['bytes'] and digest(data) == p['sha256'],'Changed downloaded part')
        h.update(data);size += len(data)
    require(size == report['package']['bytes'] and h.hexdigest() == report['package']['sha256'],'Package reconstruction differs')
    return {'original_package_bytes_verified':size,'sha256':h.hexdigest()}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path);p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path);a = p.parse_args()
    if a.verify_download:
        if not a.prepared:p.error('--verify-download requires --prepared')
        require('sha256/'+digest((BASE/'report.json').read_bytes())+'.response' in json.loads((a.prepared/'manifest.json').read_bytes())['objects'],'Report absent from archive')
        print(verify(a.prepared,a.verify_download));print(verify_package(json.loads((BASE/'report.json').read_bytes()),a.verify_download))
    else:
        if a.prepare and not a.current:p.error('--prepare requires --current')
        report = build();(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(report,a.prepare,a.current)
        else:print(json.dumps({'records':len(report['records']),'checks':report['checks']}))
