#!/usr/bin/env python3
"""Compare the pinned 669-feature service inventory with the archived Maine package.

Read-only source comparison; no identity links, geometry replacements or refresh.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3
import shapely
from shapely.geometry import box, shape
from shapely.ops import transform
import pyproj
from prepare_source_staging import ROOT, BUCKET, canonical, digest, literal, jsql, verify
from prepare_zoning_geometry import write_prepared
from prepare_wetlands_load import build as feature_inputs
from investigate_wetlands_classification import gpkg_geometry, stream_hash

BASE=ROOT/'research/wetlands-package-comparison'
METHOD='scripts/compare_wetlands_package.py'
LOAD='5802819c4376110fcac2a58b3bdf652e82524472ae15ba62913a4375551f3d39'
CLASSIFICATION='a1fd940a039662c703ec254963e70cd245f0632c970a62748591e5136f261c12'
GATES=[1,2,5,10]
SEARCH_PAD=10


def classify(metrics,gate=2):
    near=[m for m in metrics if m.get('hausdorff_distance_m',float('inf'))<=gate]
    if not near:return 'no_candidate_within_gate'
    if len(near)>1:return 'multiple_candidates_within_gate'
    return 'single_agreeing_candidate' if near[0]['code_agrees'] and near[0]['type_agrees'] else 'single_conflicting_candidate'


def comparison(g,other,code,kind,row):
    intersects=other.intersects(g)
    intersection=g.intersection(other).area if intersects else 0.0
    result={'package_objectid':row['OBJECTID'],'NWI_ID':row['NWI_ID'],'ATTRIBUTE':row['ATTRIBUTE'],'WETLAND_TYPE':row['WETLAND_TYPE'],
      'geometry_blob_sha256':digest(row['Shape']),'geometry_hold':None,
      'code_agrees':code==row['ATTRIBUTE'],'type_agrees':kind==row['WETLAND_TYPE'],
      'intersection_m2':intersection,
      'service_overlap_fraction':intersection/g.area,'package_overlap_fraction':intersection/other.area,
      'symmetric_difference_m2':g.symmetric_difference(other).area if intersects else g.area+other.area,
      'area_difference_m2':other.area-g.area,'exact_geometry_equal':g.equals(other)}
    # Each extremal x/y difference is a lower bound on full-shape Hausdorff.
    # Keep the candidate and overlap metrics; skip only a provably >10m distance.
    lower=max(abs(a-b) for a,b in zip(g.bounds,other.bounds))
    result['hausdorff_lower_bound_m']=lower
    if lower>SEARCH_PAD:result['distance_evaluation']='lower_bound_exceeds_all_gates'
    else:
        result['hausdorff_distance_m']=g.hausdorff_distance(other)
        result['distance_evaluation']='discrete_hausdorff'
    return result


def build():
    objects={}
    def read(path,sha=None):
        data=(ROOT/path).read_bytes()
        if sha is not None and digest(data)!=sha:raise ValueError('Changed dependency: '+path)
        objects[path]=data;return json.loads(data)
    load=read('research/wetlands-load/report.json',LOAD)
    classification=read('research/wetlands-classification/report.json',CLASSIFICATION)
    rebuilt,features,_=feature_inputs()
    if canonical(load)!=canonical(rebuilt):raise ValueError('Feature load no longer reproduces')
    # Reuse the complete load's pinned native/effective inputs and decoder versions.
    for path,sha in load['inputs'].items():
        data=(ROOT/path).read_bytes()
        if digest(data)!=sha:raise ValueError('Changed load input: '+path)
        objects[path]=data
    for path in [METHOD,'scripts/investigate_wetlands_classification.py']:
        objects[path]=(ROOT/path).read_bytes()
    package=classification['package'];base=ROOT/'research/wetlands-classification'
    archive=base/package['response_path'];gpkg=base/'package/maine.gpkg'
    if archive.stat().st_size!=package['bytes'] or stream_hash(archive)!=package['sha256']:raise ValueError('Changed original package ZIP')
    if gpkg.stat().st_size!=package['extracted']['bytes'] or stream_hash(gpkg)!=package['extracted']['sha256']:raise ValueError('Changed extracted working copy')
    db=sqlite3.connect(gpkg.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    wkt=db.execute('select definition from gpkg_spatial_ref_sys where srs_id=300001').fetchone()[0]
    if wkt!=package['srs_wkt']:raise ValueError('Changed package CRS')
    count=db.execute('select count(*) from ME_Wetlands').fetchone()[0]
    if count!=package['inventory_rows']:raise ValueError('Changed package row count')
    if db.execute('select count(*) from rtree_ME_Wetlands_Shape').fetchone()[0]!=count:raise ValueError('Incomplete spatial index')
    if db.execute('select count(*) from ME_Wetlands w left join rtree_ME_Wetlands_Shape r on r.id=w.OBJECTID where r.id is null').fetchone()[0]:raise ValueError('Missing spatial index membership')
    crs=pyproj.CRS.from_wkt(wkt);project=pyproj.Transformer.from_crs(3857,crs,always_xy=True)
    scope_project=pyproj.Transformer.from_crs(4269,crs,always_xy=True)
    # Densify the geographic envelope edges to 0.001 degrees for reverse scope.
    scope=transform(scope_project.transform,shapely.segmentize(box(*load['scope']['envelope_epsg4269']),0.001))
    def query(bounds,pad=0):
        xmin,ymin,xmax,ymax=bounds
        return db.execute('select w.* from ME_Wetlands w join rtree_ME_Wetlands_Shape r on r.id=w.OBJECTID where r.minx<=? and r.maxx>=? and r.miny<=? and r.maxy>=? order by w.OBJECTID',(xmax+pad,xmin-pad,ymax+pad,ymin-pad)).fetchall()
    decoded={};package_records={}
    def geometry(row):
        oid=row['OBJECTID']
        if oid not in decoded:
            try:decoded[oid]=(gpkg_geometry(row['Shape']),None)
            except (ValueError,shapely.errors.GEOSException) as e:decoded[oid]=(None,str(e))
            g,hold=decoded[oid]
            if g is not None:shapely.prepare(g)
            package_records[oid]={'object_id':oid,'NWI_ID':row['NWI_ID'],'ATTRIBUTE':row['ATTRIBUTE'],'WETLAND_TYPE':row['WETLAND_TYPE'],
              'geometry_blob_sha256':digest(row['Shape']),'geometry_hold':hold}
        return decoded[oid]
    reverse_scope=[];reverse_holds=[]
    for row in query(scope.bounds):
        g,hold=geometry(row)
        if hold:reverse_holds.append(row['OBJECTID'])
        elif g.intersects(scope):reverse_scope.append(row['OBJECTID'])
    records=[];reverse=defaultdict(list)
    for i,f in enumerate(features):
        attrs=f['native_core']['attributes'];g=transform(project.transform,shape(f['geometry_geojson']))
        if not g.is_valid or g.is_empty:raise ValueError('Invalid projected service geometry')
        metrics=[]
        for row in query(g.bounds,SEARCH_PAD):
            other,hold=geometry(row)
            if hold:
                metrics.append({'package_objectid':row['OBJECTID'],'geometry_hold':hold,'geometry_blob_sha256':digest(row['Shape'])});continue
            m=comparison(g,other,attrs['Wetlands.ATTRIBUTE'],attrs['Wetlands.WETLAND_TYPE'],row);metrics.append(m)
            if m.get('hausdorff_distance_m',float('inf'))<=2:reverse[row['OBJECTID']].append(f['object_id'])
        records.append({'service_objectid':f['object_id'],'service_globalid':attrs['Wetlands.GLOBALID'],
          'native_core_sha256':f['native_core_sha256'],'load_feature_sha256':load['feature_sha256'][str(f['object_id'])],
          'ATTRIBUTE':attrs['Wetlands.ATTRIBUTE'],'WETLAND_TYPE':attrs['Wetlands.WETLAND_TYPE'],
          'effective_lookup':f['effective_lookup'],'classification_interpretation':f['interpretation'],
          'candidates':metrics,'candidate_states':{str(gate):classify(metrics,gate) for gate in GATES},
          'interpretation':'INFERRED spatial candidates only; no accepted identity link or geometry correction'})
        if (i+1)%100==0:print('Compared',i+1,'service features',flush=True)
    operation=project.get_last_used_operation();scope_operation=scope_project.get_last_used_operation()
    reverse_rows=[dict(package_records[oid],service_candidates_within_2m=reverse[oid]) for oid in reverse_scope]
    primary=[m for r in records for m in r['candidates'] if m.get('hausdorff_distance_m',float('inf'))<=2]
    unmatched=[r['service_objectid'] for r in records if r['candidate_states']['2']=='no_candidate_within_gate']
    multiple=[r['service_objectid'] for r in records if r['candidate_states']['2']=='multiple_candidates_within_gate']
    conflicting=[r['service_objectid'] for r in records if r['candidate_states']['2']=='single_conflicting_candidate']
    shared={str(k):v for k,v in reverse.items() if len(v)>1}
    summary={'service_features':len(records),'package_inventory_rows':count,'bbox_candidate_pairs':sum(len(r['candidates']) for r in records),
      'unique_package_candidates_inspected':len(decoded),'candidate_geometry_holds':sum(v[1] is not None for v in decoded.values()),
      'sensitivity':{str(gate):dict(sorted(Counter(r['candidate_states'][str(gate)] for r in records).items())) for gate in GATES},
      'service_without_2m_candidate':unmatched,'service_with_multiple_2m_candidates':multiple,'service_with_conflicting_2m_candidate':conflicting,
      'package_candidates_shared_by_multiple_service_features':shared,
      'reverse_scope_package_features':len(reverse_rows),'reverse_scope_geometry_holds':reverse_holds,
      'reverse_scope_without_service_2m_candidate':[r['object_id'] for r in reverse_rows if not r['service_candidates_within_2m']],
      'reverse_scope_multiple_service_candidates':[r['object_id'] for r in reverse_rows if len(r['service_candidates_within_2m'])>1],
      'primary_candidate_distance_range_m':[min(m['hausdorff_distance_m'] for m in primary),max(m['hausdorff_distance_m'] for m in primary)] if primary else None,
      'primary_exact_geometry_equal':sum(m['exact_geometry_equal'] for m in primary),
      'primary_package_ids_equal_reverse_scope':set(reverse)==set(reverse_scope),
      'primary_package_ids_unique':len(reverse),
      'primary_code_disagreements':sum(not m['code_agrees'] for m in primary),'primary_type_disagreements':sum(not m['type_agrees'] for m in primary)}
    db.close()
    # Keep the reviewable report compact; full candidate evidence is private/hash-pinned.
    details=(json.dumps({'records':records,'reverse_scope_records':reverse_rows},sort_keys=True,indent=2)+'\n').encode()
    detail_path='research/wetlands-package-comparison/detailed-results.response'
    BASE.mkdir(exist_ok=True);(ROOT/detail_path).write_bytes(details);objects[detail_path]=details
    report={'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest(objects[METHOD]),'inputs':{p:digest(d) for p,d in sorted(objects.items())},
      'load_audit_sha256':LOAD,'classification_audit_sha256':CLASSIFICATION,'classification_event_id':load['classification_event_id'],
      'availability_result_id':load['availability_coverage_result_id'],'package':package,
      'parameters':{'bbox_padding_m':SEARCH_PAD,'primary_hausdorff_gate_m':2,'sensitivity_gates_m':GATES,'reverse_scope':'Original geographic study envelope; edges densified at 0.001 degrees, projected to package CRS; includes touching features',
        'matching':'All spatial bounding-box candidates retained; no identifier/code prefilter and no nearest-match selection. Prepared disjoint predicate skips overlays; disjoint symmetric-difference area equals summed areas',
        'distance':'GEOS discrete Hausdorff on full polygons without densification; extremal coordinate lower bound >10m skips exact distance but retains candidate/overlap. Investigative tolerance, not accuracy or legal-boundary guarantee'},
      'transformation':{'definition':operation.definition,'reported_accuracy_m':operation.accuracy,'package_crs_wkt':wkt,'scope_definition':scope_operation.definition,'scope_reported_accuracy_m':scope_operation.accuracy},
      'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str,'sqlite':sqlite3.sqlite_version},
      'summary':summary,'details':{'path':detail_path,'sha256':digest(details),'bytes':len(details),'service_records':len(records),'reverse_scope_records':len(reverse_rows)},
      'limits':load['limits'],'decision':{
        'accepted_changes':'None: no identity crosswalk, geometry replacement or projection correction.',
        'bounded_candidate_agreement':not(unmatched or multiple or conflicting or shared or reverse_holds) and len(reverse_rows)==669 and set(reverse)==set(reverse_scope),
        'recommendation':'If bounded candidate agreement passes, a separate versioned package load for this scope is supported as the next proposal; retain source identifiers/geometries and INFERRED candidate links. This does not qualify statewide ingestion.',
        'open':'Projection cause, cross-release identity, statewide geometry/coverage, imagery refresh and legal applicability remain unqualified.'}}
    return report,objects


def prepare(report,objects,output,current):
    data=(BASE/'report.json').read_bytes();sha=digest(data);registry=digest((ROOT/'research/osborn-wetlands/registry.json').read_bytes())
    sql='BEGIN;\nSET LOCAL standard_conforming_strings=on;\n'
    values=[literal(sha),literal(registry),literal('DERIVED'),literal(METHOD),literal(report['method_sha256']),jsql(report),literal(BUCKET),literal('sha256/'+sha+'.response')]
    sql+='INSERT INTO ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object) VALUES ('+','.join(values)+') ON CONFLICT DO NOTHING;\n'
    r=report['summary'];event={'finding_id':'TL-F-0117','status':'in_progress','priority':'medium','actor':'TerraLucid bounded package comparison',
      'event_id':digest(canonical([sha,'TL-F-0117']).encode()),
      'note':'Compared all 669 reviewed service features against the archived Maine package without identity/code prefilters. Summary: '+canonical(r)+'. Candidates remain INFERRED; no accepted crosswalk or statewide qualification. Imagery age, refresh, projection cause and legal applicability remain open.',
      'next_action':'Review a separate bounded package ingestion proposal using the comparison and sensitivity results. Keep geometry and identity candidates separate; investigate projection cause and qualify broader geometry, imagery/project coverage and refresh before statewide ingestion.',
      'evidence_refs':['audit:'+sha+'#/summary','audit:'+sha+'#/decision']}
    state=next(r for r in json.loads(current.read_bytes())['rows'] if r['finding_id']=='TL-F-0117')
    sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(event['event_id']),literal('TL-F-0117'),literal(sha),jsql({'report_pointer':'/summary'})])+') ON CONFLICT DO NOTHING;\n'
    sql+='SELECT ingest.record_finding_event('+jsql(event)+','+literal(state['event_id'])+');\nCOMMIT;\n'
    # Existing package parts are dependencies and must be restored/hash-verified too.
    payloads=list(objects.values())+[data]
    archive=ROOT/'research/wetlands-classification'/report['package']['response_path']
    with archive.open('rb') as src:
        for part in report['package']['parts']:
            if src.tell()!=part['offset']:raise ValueError('Package offsets differ')
            chunk=src.read(part['bytes'])
            if digest(chunk)!=part['sha256']:raise ValueError('Package part changed')
            payloads.append(chunk)
        if src.read(1):raise ValueError('Package tail unarchived')
    write_prepared(output,sql,payloads);print(json.dumps({'audit_sha256':sha,'summary':r}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path);p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path);a=p.parse_args()
    if a.verify_download:
        from investigate_wetlands_classification import verify_package
        print(verify(a.prepared,a.verify_download));print(verify_package(json.loads((BASE/'report.json').read_bytes()),a.verify_download))
    else:
        report,objects=build();BASE.mkdir(exist_ok=True);(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        if a.prepare:
            if not a.current:p.error('--prepare needs --current')
            prepare(report,objects,a.prepare,a.current)
        else:print(json.dumps(report['summary'],indent=2))
