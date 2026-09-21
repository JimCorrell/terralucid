#!/usr/bin/env python3
"""Qualify bounded datum-operation closure and native package project coverage."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import shapely
from shapely.geometry import shape, Polygon
from shapely.ops import transform, unary_union
import pyproj
from pyproj.enums import TransformDirection
from prepare_source_staging import ROOT, digest, canonical, literal, jsql, prepare, verify
from prepare_wetlands_load import build as service_build
from prepare_wetlands_package_load import build as package_build
from investigate_osborn_wetlands import group_source_rows, decode
from investigate_wetlands_classification import gpkg_geometry, verify_package

BASE=ROOT/'research/wetlands-projection-lineage'
METHOD='scripts/investigate_wetlands_lineage.py'
PACKAGE_AUDIT='6703cb4fd92661c09a4baadc1daee77b86ef1f20dff2155bdae2dfcf74ccce02'
CONTROLS={1886218,2274990,2320442,9415660}


def require(ok,message):
    if not ok:raise ValueError(message)


def projected(g,authority):
    geographic=pyproj.Transformer.from_crs(3857,4326,always_xy=True)
    albers=pyproj.Transformer.from_crs(4269,5070,always_xy=True)
    op=pyproj.Transformer.from_pipeline(authority)
    direction=TransformDirection.FORWARD if authority=='ESRI:108190' else TransformDirection.INVERSE
    def apply(x,y,z=None):
        lon,lat=geographic.transform(x,y)
        nlat,nlon=op.transform(lat,lon,direction=direction)
        return albers.transform(nlon,nlat)
    return transform(apply,g)


def coverage(g,footprints):
    hits=[{'package_project_id':oid,'overlap_m2':g.intersection(p).area} for oid,p in footprints if g.intersects(p)]
    positive=[h for h in hits if h['overlap_m2']>0]
    return {'positive_area_projects':positive,'boundary_touch_projects':[h['package_project_id'] for h in hits if h['overlap_m2']==0],
      'uncovered_m2':g.difference(unary_union([p for _,p in footprints])).area}


def build():
    objects={};evidence={};payloads={}
    def read(path,expected=None):
        data=(ROOT/path).read_bytes();require(expected is None or digest(data)==expected,'Changed evidence: '+path);objects[path]=data;return data
    package_report=json.loads(read('research/wetlands-package-load/report.json',PACKAGE_AUDIT))
    package_rebuilt,package_entries,_=package_build();require(canonical(package_report)==canonical(package_rebuilt),'Package load changed')
    service_report,features,_=service_build();service={f['object_id']:f for f in features}
    # Pin all bounded service derivation inputs and the package's native byte lineage.
    for path,sha in service_report['inputs'].items():read(path,sha)
    for path,sha in package_report['inputs'].items():read(path,sha)
    for path in [METHOD,'scripts/investigate_osborn_wetlands.py','scripts/prepare_wetlands_load.py','scripts/prepare_wetlands_package_load.py','scripts/collect_document_evidence.py','scripts/prepare_source_staging.py']:
        read(path)
    for name in ['probes.json','documentation-probes.json','registry.json']:read('research/wetlands-projection-lineage/'+name)
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            data=(log.parent/r['response_file']).read_bytes()
            require(r['http_status']==200 and digest(data)==r['sha256'] and len(data)==r['bytes'],'Failed/changed control capture')
            evidence[log.parent.name+'/'+r['id']]=dict(r,response_path=(log.parent/r['response_file']).relative_to(BASE).as_posix());payloads[r['id']]=data
    def parsed(name):
        d=json.loads(payloads[name]);require(not d.get('error') and not d.get('exceededTransferLimit'),'Failed/truncated query');return d
    meta=parsed('layer-metadata');require(meta==parsed('layer-metadata-end'),'Metadata drift')
    require(meta['sourceSpatialReference']['latestWkid']==3857 and meta['advancedQueryCapabilities']['supportsQueryWithDatumTransformation'],'Unsupported controls')
    native=parsed('native');require(native['spatialReference'].get('latestWkid',native['spatialReference']['wkid'])==3857,'Native CRS changed')
    cores,_=group_source_rows(native['features']);require({c['attributes']['Wetlands.OBJECTID'] for c in cores}==CONTROLS,'Control scope changed')
    for c in cores:require(canonical(c)==canonical(service[c['attributes']['Wetlands.OBJECTID']]['native_core']),'Control native source changed')
    require(parsed('default-albers')==parsed('explicit-108190'),'Default differs from explicit 108190')
    projected_controls={}
    for name in ['default-albers','explicit-1188','explicit-1515','explicit-108190']:
        d=parsed(name);require(d['spatialReference']['wkid']==5070,'Control CRS differs')
        cc,_=group_source_rows(d['features']);require({x['attributes']['Wetlands.OBJECTID'] for x in cc}==CONTROLS,'Missing control feature')
        projected_controls[name]={}
        for c in cc:
            oid=c['attributes']['Wetlands.OBJECTID'];require(c['attributes']==service[oid]['native_core']['attributes'],'Control attribute drift')
            g,hold=decode(c['geometry']['rings']);require(hold is None,'Invalid control geometry');projected_controls[name][oid]=g
    operations={}
    for authority in ['ESRI:108190','EPSG:1188','EPSG:1515']:
        t=pyproj.Transformer.from_pipeline(authority)
        operations[authority]={'name':t.description,'pipeline':t.definition,'reported_accuracy_m':t.accuracy,
          'direction':'forward WGS84 to NAD83' if authority.startswith('ESRI') else 'inverse NAD83-to-WGS84 operation'}
    rows=[];control_metrics=[];package_geometries={}
    for e in package_entries:
        oid=e['service_object_id'];source=shape(service[oid]['geometry_geojson']);g=gpkg_geometry(bytes.fromhex(e['geometry_blob_hex']));package_geometries[e['object_id']]=g
        metrics={};converted={}
        for authority in operations:
            h=projected(source,authority);require(h.is_valid,'Invalid projected geometry');converted[authority]=h
            metrics[authority]=h.hausdorff_distance(g)
        require(metrics['ESRI:108190']<0.001 and metrics['EPSG:1188']>1 and metrics['EPSG:1515']>0.001,'Discriminating closure changed')
        rows.append({'service_objectid':oid,'package_objectid':e['object_id'],'geometry_blob_sha256':e['geometry_blob_sha256'],'service_feature_sha256':e['service_feature_sha256'],'hausdorff_to_package_m':metrics})
        if oid in CONTROLS:
            control_metrics.append({'service_objectid':oid,'service_default_to_package_m':projected_controls['default-albers'][oid].hausdorff_distance(g),
              'local_to_service_explicit_m':{a:converted[a].hausdorff_distance(projected_controls['explicit-'+a.split(':')[1]][oid]) for a in operations}})
    # Native package project coverage, without using service-projected footprints.
    p=ROOT/'research/wetlands-classification/package/maine.gpkg';db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    union=unary_union(list(package_geometries.values()));xmin,ymin,xmax,ymax=union.bounds
    project_rows=db.execute('select w.* from ME_Wetlands_Project_Metadata w join rtree_ME_Wetlands_Project_Metadata_Shape r on r.id=w.OBJECTID where r.minx<=? and r.maxx>=? and r.miny<=? and r.maxy>=? order by w.OBJECTID',(xmax,xmin,ymax,ymin)).fetchall()
    projects=[];footprints=[]
    prior=json.loads(read('research/osborn-wetlands/report.json',service_report['source_audit_sha256']))
    image=prior['evidence']['coverage/image-year-features'];source_images=json.loads(read('research/osborn-wetlands/'+image['response_path'],image['sha256']))['features']
    lineage_fields=['PROJECT_NAME','STATUS','IMAGE_YR','IMAGE_DATE','IMAGE_SCALE','ALL_SCALES','EMULSION','COMMENTS','SOURCE_TYPE']
    for row in project_rows:
        g=gpkg_geometry(row['Shape'])
        if not g.intersects(union):continue
        footprints.append((row['OBJECTID'],g));attrs={k:row[k] for k in row.keys() if k!='Shape'}
        matches=[f for f in source_images if f['attributes'].get('PROJECT_NAME')==row['PROJECT_NAME']]
        require(len(matches)==1,'Project-name comparison ambiguous')
        f=matches[0];sg,hold=decode(f['geometry']['rings']);require(hold is None,'Invalid service imagery footprint')
        projects.append({'attributes':attrs,'geometry_blob_sha256':digest(row['Shape']),
          'service_project_id':f['attributes']['OBJECTID'],
          'lineage_attribute_differences':{k:{'package':attrs.get(k),'service':f['attributes'].get(k)} for k in lineage_fields if attrs.get(k)!=f['attributes'].get(k)},
          'service_108190_to_package_hausdorff_m':projected(sg,'ESRI:108190').hausdorff_distance(g)})
    for r in rows:r['project_coverage']=coverage(package_geometries[r['package_objectid']],footprints)
    scopepath='research/osborn-fema/runs/identity/osborn-jurisdiction.response'
    scope=json.loads(read(scopepath,'813824533f6c03c71fb8024431e0bd9f86e10b46c8e9ba12eb9c2ddf4d13696a'))
    scope_projection=pyproj.Transformer.from_crs(4269,5070,always_xy=True)
    scope_g=transform(scope_projection.transform,Polygon(scope['features'][0]['geometry']['rings'][0]))
    scope_coverage=coverage(scope_g,footprints);db.close()
    details=(json.dumps({'records':rows},sort_keys=True,indent=2)+'\n').encode();detail_path='research/wetlands-projection-lineage/detailed-results.response';(ROOT/detail_path).write_bytes(details);objects[detail_path]=details
    summary={'features':len(rows),'operation_ranges_m':{a:{'minimum':min(r['hausdorff_to_package_m'][a] for r in rows),'maximum':max(r['hausdorff_to_package_m'][a] for r in rows)} for a in operations},
      'control_features':len(control_metrics),'default_equals_explicit_108190':True,
      'local_to_service_explicit_maximum_m':{a:max(c['local_to_service_explicit_m'][a] for c in control_metrics) for a in operations},
      'default_operation_declared_in_metadata':any(k in d for d in [meta,parsed('service-metadata')] for k in ['datumTransformation','datumTransformations']),
      'package_projects':len(projects),'project_footprint_108190_maximum_m':max(p['service_108190_to_package_hausdorff_m'] for p in projects),
      'features_with_uncovered_project_area':sum(r['project_coverage']['uncovered_m2']>0 for r in rows),
      'maximum_uncovered_feature_m2':max(r['project_coverage']['uncovered_m2'] for r in rows),
      'project_count_per_feature':dict(sorted(Counter(len(r['project_coverage']['positive_area_projects']) for r in rows).items())),
      'study_boundary_uncovered_m2':scope_coverage['uncovered_m2'],'lineage_difference_fields':sum(len(p['lineage_attribute_differences']) for p in projects)}
    report={'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest(objects[METHOD]),'inputs':{p:digest(d) for p,d in sorted(objects.items())},'evidence':evidence,
      'package_audit_sha256':PACKAGE_AUDIT,'package':package_report['package'],'details':{'path':detail_path,'sha256':digest(details),'bytes':len(details)},
      'summary':summary,'operations':operations,'controls':control_metrics,'projects':projects,'study_project_coverage':scope_coverage,'study_scope_operation':scope_projection.definition,
      'runtime':{'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str,'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'sqlite':sqlite3.sqlite_version,'proj_network_enabled':pyproj.network.is_network_enabled(),'proj_database_sha256':digest((Path(pyproj.datadir.get_data_dir())/'proj.db').read_bytes())},
      'conclusion':'The bounded displacement is numerically reconciled by explicit ESRI:108190, distinguished from EPSG:1188 and EPSG:1515. Four unchanged live service controls have default output identical to explicit 108190. This supports an operation-choice explanation, not proof of hidden publisher production history or positional accuracy. Package project footprints qualify spatial lineage only; dates and remaining gaps are recorded separately.',
      'limits':['No source geometry, acceptance event, source preference, candidate identity or stored comparison metric is changed. Earlier results remain historical evidence.',
        'All per-feature identities remain INFERRED. Numerical closure is not survey accuracy, legal delineation or a statewide transformation policy.',
        'Package project coverage is a spatial association, not a direct per-feature provenance key or proof of exhaustive/current wetlands. Overlapping footprints and boundary touches are preserved.',
        'May 1983 imagery and undated NHD supplementation remain qualified; publication/retrieval dates do not imply new imagery. Wider package coverage and refresh remain unqualified.'],
      'finding_review':{'finding_id':'TL-F-0117','status':'in_progress','priority':'medium',
        'note':'Numerically reconciled the bounded service/package displacement using explicit ESRI:108190 for all 669 pairs, with four unchanged live service controls and EPSG:1188/1515 alternatives. Four package projects cover all 669 features and the study boundary; lineage attributes agree with the archived service and retain May 1983 imagery plus undated NHD supplementation. Native project coverage is recorded per feature, including multi-project overlaps. No geometry correction or identity acceptance; old imagery, undated supplementation, wider qualification, refresh and legal applicability remain open.',
        'next_action':'Qualify wider package geometry/project coverage and freshness before statewide ingestion; keep the explicit operation version pinned for any proposed new comparison, and retain source/identity/legal qualifications.'}}
    return report,objects


def prepare_load(report,objects,output,current):
    prepare(BASE,output,BASE/'report.json');manifest=json.loads((output/'manifest.json').read_bytes())
    def archive(data):
        sha=digest(data);key='sha256/'+sha+'.response';(output/'objects'/key).write_bytes(data);manifest['objects'][key]={'sha256':sha,'bytes':len(data)}
    for data in objects.values():archive(data)
    with (ROOT/'research/wetlands-classification'/report['package']['response_path']).open('rb') as src:
        for part in report['package']['parts']:
            data=src.read(part['bytes']);require(digest(data)==part['sha256'],'Changed package part');archive(data)
        require(not src.read(1),'Unarchived package tail')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    sha=digest((BASE/'report.json').read_bytes());sql=(output/'load.sql').read_text().removesuffix('COMMIT;\n')
    state=next(r for r in json.loads(current.read_bytes())['rows'] if r['finding_id']=='TL-F-0117')
    event=dict(report['finding_review'],actor='TerraLucid wetlands projection and lineage review',event_id=digest(canonical([sha,'TL-F-0117']).encode()),evidence_refs=['audit:'+sha+'#/summary','audit:'+sha+'#/projects','audit:'+sha+'#/conclusion'])
    sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(event['event_id']),literal('TL-F-0117'),literal(sha),jsql({'report_pointer':'/summary'})])+') ON CONFLICT DO NOTHING;\n'
    sql+='SELECT ingest.record_finding_event('+jsql(event)+','+literal(state['event_id'])+');\nCOMMIT;\n';(output/'load.sql').write_text(sql)
    print(json.dumps({'audit_sha256':sha,'archive_objects':len(manifest['objects']),'summary':report['summary']}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path);p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path);a=p.parse_args()
    if a.verify_download:
        print(verify(a.prepared,a.verify_download));print(verify_package(json.loads((BASE/'report.json').read_bytes()),a.verify_download))
    else:
        r,objects=build();(BASE/'report.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(r,objects,a.prepare,a.current)
        else:print(json.dumps(r['summary'],indent=2))
