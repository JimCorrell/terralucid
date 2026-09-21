#!/usr/bin/env python3
"""Load only the reviewed 669 package candidates; never replace service geometry."""
import argparse
import json
from pathlib import Path
import sqlite3
import pyproj
from prepare_source_staging import ROOT, BUCKET, digest, canonical, literal, jsql, verify
from prepare_zoning_geometry import write_prepared
from investigate_wetlands_classification import stream_hash, gpkg_geometry, verify_package

BASE=ROOT/'research/wetlands-package-load'
METHOD='scripts/prepare_wetlands_package_load.py'
MIGRATION='supabase/migrations/20260921030000_wetlands_package_load.sql'
COMPARISON='076cb7321ad0b8cad052a4bf51a18028413b88e788082ddbc347158919ec18ed'
SERVICE='5802819c4376110fcac2a58b3bdf652e82524472ae15ba62913a4375551f3d39'


def candidates(details):
    result=[];seen=set()
    for r in details['records']:
        near=[c for c in r['candidates'] if c.get('hausdorff_distance_m',float('inf'))<=2]
        if len(near)!=1 or not near[0]['code_agrees'] or not near[0]['type_agrees']:raise ValueError('Unqualified candidate set')
        c=near[0]
        if c['package_objectid'] in seen:raise ValueError('Shared candidate')
        seen.add(c['package_objectid']);result.append((r,c))
    if seen!={r['object_id'] for r in details['reverse_scope_records']}:raise ValueError('Reverse scope differs')
    return result


def build():
    objects={}
    def read(path,sha=None):
        data=(ROOT/path).read_bytes()
        if sha and digest(data)!=sha:raise ValueError('Changed evidence: '+path)
        objects[path]=data;return data
    comparison=json.loads(read('research/wetlands-package-comparison/report.json',COMPARISON))
    service=json.loads(read('research/wetlands-load/report.json',SERVICE))
    details=json.loads(read(comparison['details']['path'],comparison['details']['sha256']))
    for path in [METHOD,MIGRATION,'scripts/prepare_source_staging.py','scripts/prepare_zoning_geometry.py','scripts/investigate_wetlands_classification.py']:read(path)
    package=comparison['package'];gpkg=ROOT/'research/wetlands-classification/package/maine.gpkg'
    archive=ROOT/'research/wetlands-classification'/package['response_path']
    if stream_hash(archive)!=package['sha256'] or stream_hash(gpkg)!=package['extracted']['sha256']:raise ValueError('Package bytes changed')
    db=sqlite3.connect(gpkg.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    wkt=db.execute('select definition from gpkg_spatial_ref_sys where srs_id=300001').fetchone()[0]
    if wkt!=package['srs_wkt'] or not pyproj.CRS.from_wkt(wkt).equals(pyproj.CRS.from_epsg(5070)):raise ValueError('Native CRS is not equivalent to EPSG:5070')
    entries=[]
    for r,c in candidates(details):
        row=db.execute('select * from ME_Wetlands where OBJECTID=?',(c['package_objectid'],)).fetchone()
        if row is None or digest(row['Shape'])!=c['geometry_blob_sha256']:raise ValueError('Candidate geometry changed')
        attrs={k:row[k] for k in row.keys() if k!='Shape'}
        if any(attrs[k]!=c[k] for k in ['NWI_ID','ATTRIBUTE','WETLAND_TYPE']):raise ValueError('Candidate attributes changed')
        if service['feature_sha256'][str(r['service_objectid'])]!=r['load_feature_sha256']:raise ValueError('Changed service candidate')
        gpkg_geometry(row['Shape'])
        entries.append({'object_id':row['OBJECTID'],'attributes':attrs,'geometry_blob_hex':row['Shape'].hex(),
          'geometry_blob_sha256':c['geometry_blob_sha256'],'source_srs_id':300001,'postgis_srid':5070,
          'service_object_id':r['service_objectid'],'service_feature_sha256':r['load_feature_sha256'],'comparison_metrics':c,
          'identity_state':'INFERRED','geometry_evidence_state':'DERIVED'})
    db.close()
    if len(entries)!=669:raise ValueError('Bounded scope differs')
    report={'method':METHOD,'method_sha256':digest(objects[METHOD]),'evidence_state':'DERIVED',
      'inputs':{p:digest(d) for p,d in sorted(objects.items())},'comparison_audit_sha256':COMPARISON,'service_audit_sha256':SERVICE,
      'package':package,'crs_mapping':{'source_srs_id':300001,'postgis_srid':5070,'source_wkt':wkt,'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str,'operation':'Equivalent CRS identifier assignment only; coordinates and source geometry bytes unchanged'},
      'summary':{'package_features':669,'inferred_candidate_links':669,'geometry_replacements':0},
      'limits':service['limits'],'feature_sha256':{str(e['object_id']):digest(canonical(e).encode()) for e in entries},
      'finding_review':{'finding_id':'TL-F-0117','status':'in_progress','priority':'medium',
        'note':'Loaded 669 bounded Maine package features separately with exact native geometry blobs, attributes and INFERRED links to reviewed service candidates. Native package CRS is equivalent to EPSG:5070; only its identifier is mapped, with no coordinate transformation or displacement correction. Existing service defaults remain unchanged. Projection cause, cross-release identity, statewide coverage, imagery refresh and legal applicability remain unqualified.',
        'next_action':'Investigate the consistent service/package displacement and qualify package imagery/project coverage before wider ingestion; preserve independent source geometries and inferred identities.'}}
    return report,entries,objects


def prepare(output,current):
    report,entries,objects=build();BASE.mkdir(exist_ok=True);data=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();(BASE/'report.json').write_bytes(data);sha=digest(data)
    registry=digest((ROOT/'research/osborn-wetlands/registry.json').read_bytes())
    sql='BEGIN;\nSET LOCAL standard_conforming_strings=on;\n'
    sql+='INSERT INTO ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join([literal(sha),literal(registry),literal('DERIVED'),literal(METHOD),literal(report['method_sha256']),jsql(report),literal(BUCKET),literal('sha256/'+sha+'.response')])+') ON CONFLICT DO NOTHING;\n'
    sql+='INSERT INTO ingest.wetlands_package_batch(audit_sha256,comparison_audit_sha256,service_audit_sha256) VALUES ('+','.join(map(literal,[sha,COMPARISON,SERVICE]))+') ON CONFLICT DO NOTHING;\n'
    for e in entries:
        sql+='INSERT INTO ingest.wetlands_package_feature(audit_sha256,object_id,service_audit_sha256,service_object_id,input_text) VALUES ('+','.join([literal(sha),str(e['object_id']),literal(SERVICE),str(e['service_object_id']),literal(canonical(e))])+') ON CONFLICT DO NOTHING;\n'
    event=dict(report['finding_review'],event_id=digest(canonical([sha,'TL-F-0117']).encode()),actor='TerraLucid bounded package ingestion',evidence_refs=['audit:'+sha+'#/summary','audit:'+sha+'#/limits'])
    state=next(r for r in json.loads(current.read_bytes())['rows'] if r['finding_id']=='TL-F-0117')
    sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(event['event_id']),literal('TL-F-0117'),literal(sha),jsql({'report_pointer':'/summary'})])+') ON CONFLICT DO NOTHING;\n'
    sql+='SELECT ingest.record_finding_event('+jsql(event)+','+literal(state['event_id'])+');\nCOMMIT;\n'
    payloads=list(objects.values())+[data]
    with (ROOT/'research/wetlands-classification'/report['package']['response_path']).open('rb') as src:
        for part in report['package']['parts']:
            chunk=src.read(part['bytes'])
            if digest(chunk)!=part['sha256']:raise ValueError('Package part changed')
            payloads.append(chunk)
        if src.read(1):raise ValueError('Package tail unarchived')
    write_prepared(output,sql,payloads);print(json.dumps({'audit_sha256':sha,**report['summary']}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--current',type=Path);p.add_argument('--verify-download',type=Path);a=p.parse_args()
    if a.verify_download:
        print(verify(a.output,a.verify_download));print(verify_package(json.loads((BASE/'report.json').read_bytes()),a.verify_download))
    elif a.current:prepare(a.output,a.current)
    else:p.error('--current required')
