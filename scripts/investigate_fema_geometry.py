#!/usr/bin/env python3
"""Investigate TL-F-0026; propose exact-version decodings, never accept or screen."""
import argparse
from collections import Counter
import json
from pathlib import Path

import pyproj
import shapely
from shapely.geometry import Polygon, mapping, shape
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity

from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql, verify
from investigate_osborn_zoning import edges, split_single_touch
from investigate_osborn_fema import parts, restore, CRS

BASE = ROOT / 'research/fema-geometry-investigation'
PRIOR = ROOT / 'research/osborn-fema'
PRIOR_SHA = '2f106e1b19fa2b13415741a109d34f1f9dbc4fdb04cf67e77fe882325aebe5ff'
METHOD = 'scripts/investigate_fema_geometry.py'
OIDS = {27129510, 27129583}


def require(value, message):
    if not value: raise ValueError(message)


def selected(payload, native=False, sr=4269):
    require(not payload.get('error') and not payload.get('exceededTransferLimit'), 'Failed/incomplete response')
    if native:
        require(payload.get('spatialReference',{}).get('wkid')==sr, 'Unexpected native CRS')
    else:
        require(payload.get('type')=='FeatureCollection' and payload.get('crs')==CRS, 'Expected explicit NAD83 GeoJSON')
    fs=payload.get('features',[]); key='attributes' if native else 'properties'
    require(len(fs)==2 and {f[key]['OBJECTID'] for f in fs}==OIDS, 'Changed/duplicate feature membership')
    for f in fs:
        g=f['geometry']
        if native:
            require(set(g)=={'rings'} and len(g['rings'])==1, 'Only one straight native ring supported')
        else:
            require(g.get('type')=='Polygon' and len(g['coordinates'])==1, 'Unexpected export topology')
    return {f[key]['OBJECTID']:f for f in fs}


def compare_source(old, native, exported, projected):
    require(old==exported, 'Source feature changed since reviewed audit')
    require(old['properties']==native['attributes']==projected['attributes'], 'Attribute drift across representations')
    require(edges(native['geometry']['rings'])==edges(exported['geometry']['coordinates']), 'Changed native/export boundary segments')


def build():
    inputs, evidence, payloads = {}, {}, {}
    def dependency(path, expected=None):
        data=(ROOT/path).read_bytes()
        require(expected is None or digest(data)==expected, 'Changed input: '+path)
        inputs[path]=digest(data)
        return data
    prior=json.loads(dependency('research/osborn-fema/report.json',PRIOR_SHA))
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            require(Path(r['response_file']).name==r['response_file'], 'Unsafe response path')
            path=log.parent/r['response_file'];data=path.read_bytes()
            require(r['http_status']==200 and digest(data)==r['sha256'] and len(data)==r['bytes'], 'Failed capture integrity')
            require(r['id'] not in payloads, 'Duplicate probe')
            payloads[r['id']]=data
            evidence[log.parent.name+'/'+r['id']]=dict(r,response_path=path.relative_to(BASE).as_posix())
    parsed=lambda name:json.loads(payloads[name])
    native=selected(parsed('native-rings'),True)
    exported=selected(parsed('geojson-recheck'))
    projected=selected(parsed('projected-rings'),True,26919)
    meta=parsed('layer-metadata')
    require(not meta.get('error') and meta['extent']['spatialReference']['wkid']==4269
            and not meta.get('hasZ') and not meta.get('hasM'), 'Unexpected layer metadata')
    old, locations = {}, {}
    for ref,r in prior['evidence'].items():
        if not r['id'].startswith('hazards-geometry-'):continue
        path='research/osborn-fema/'+r['response_path']
        payload=json.loads(dependency(path,r['sha256']))
        require(payload.get('crs')==CRS and not payload.get('error') and not payload.get('exceededTransferLimit'), 'Invalid prior page')
        for f in payload['features']:
            oid=f['properties']['OBJECTID'];require(oid not in old,'Duplicate prior ID')
            old[oid]=f;locations[oid]={'prior_evidence_ref':ref,'response_sha256':r['sha256']}
    ids=prior['evidence']['membership/hazards-ids']
    captured=json.loads(dependency('research/osborn-fema/'+ids['response_path'],ids['sha256']))
    require(not captured.get('error') and set(captured['objectIds'])==set(old)
            and len(captured['objectIds'])==len(old)==1503, 'Prior hazard membership mismatch')
    review=json.loads(dependency('research/fema-geometry-investigation/map-review.json'))
    document=prior['large_document_evidence']
    pdf=(PRIOR/document['response_path']).read_bytes()
    require(digest(pdf)==document['retrieval']['sha256']==review['pdf_sha256']
            and len(pdf)==document['retrieval']['bytes'] and parts(pdf)==document['parts'], 'Original PDF changed')
    for row in review['service_renders']:
        require(evidence[row['evidence_ref']]['sha256']==row['sha256']
                and payloads[row['evidence_ref'].split('/')[-1]].startswith(b'\x89PNG\r\n\x1a\n'), 'Changed/failed map rendering')
    def prior_payload(ref):
        r=prior['evidence'][ref]
        return json.loads(dependency('research/osborn-fema/'+r['response_path'],r['sha256']))
    jurisdiction=prior_payload('identity/osborn-jurisdiction')
    require(jurisdiction['spatialReference']['wkid']==4269 and len(jurisdiction['features'])==1, 'Changed jurisdiction')
    j=Polygon(jurisdiction['features'][0]['geometry']['rings'][0])
    require(j.is_valid,'Invalid jurisdiction')
    panels=prior_payload('features/panels-features')['features']
    lomrs=prior_payload('features/lomr-features')['features']
    project=pyproj.Transformer.from_crs(4269,26919,always_xy=True)
    jp=transform(project.transform,j)
    candidates, results = [], []
    for oid in sorted(OIDS):
        nf,ef,pf=native[oid],exported[oid],projected[oid]
        compare_source(old[oid],nf,ef,pf)
        nr=nf['geometry']['rings'][0];er=ef['geometry']['coordinates'][0];pr=pf['geometry']['rings'][0]
        require(not Polygon(nr).is_valid and not shape(ef['geometry']).is_valid, 'Original is no longer invalid')
        nc,nd=split_single_touch(nr);ec,ed=split_single_touch(er);pc,pd=split_single_touch(pr)
        require(not nd['shell_counterclockwise'] and nd['hole_counterclockwise']
                and nc.equals(ec), 'Native roles do not corroborate export decode')
        local=transform(project.transform,ec)
        require(local.is_valid and local.hausdorff_distance(pc)<0.000001, 'Projected representations differ; review required')
        require(edges([er])==edges([list(ec.exterior.coords),list(ec.interiors[0].coords)]), 'Proposal changed linework')
        hole=Polygon(ec.interiors[0]);holep=transform(project.transform,hole)
        neighbors=[];clips=[]
        for other_oid,f in sorted(old.items()):
            if other_oid in OIDS:continue
            g=shape(f['geometry'])
            if not g.is_valid:raise ValueError('Unexpected additional invalid prior feature')
            if not g.intersects(hole):continue
            part=g.intersection(hole)
            if part.area<=0:continue
            clip=transform(project.transform,part);clips.append(clip)
            neighbors.append({'OBJECTID':other_oid,'zone':f['properties']['FLD_ZONE'],
                'subtype':f['properties']['ZONE_SUBTY'],'intersection_area_m2':clip.area,
                'original_feature_sha256':digest(canonical(f).encode()),**locations[other_oid]})
        feature_sha=digest(canonical(old[oid]).encode())
        candidate={'type':'Feature','crs':CRS,'properties':{
            'source_OBJECTID':oid,'source_GlobalID':ef['properties']['GlobalID'],
            'source_feature_sha256':feature_sha,'prior_audit_sha256':PRIOR_SHA,
            'status':'proposed_not_accepted','evidence_state':'DERIVED','source_crs':'EPSG:4269',
            'FLD_ZONE':ef['properties']['FLD_ZONE'],'ZONE_SUBTY':ef['properties']['ZONE_SUBTY'],
            'legal_applicability':'UNKNOWN','method':'Split only the existing vertex touch into its opposite-winding shell/hole; preserve every segment.'},
            'geometry':mapping(ec)}
        candidate_bytes=(json.dumps(candidate,sort_keys=True,indent=2)+'\n').encode()
        path=BASE/'candidates'/f'{oid}.geojson';path.parent.mkdir(exist_ok=True);path.write_bytes(candidate_bytes)
        dependency(path.relative_to(ROOT).as_posix(),digest(candidate_bytes))
        candidates.append(local)
        results.append({'OBJECTID':oid,'source_feature_sha256':feature_sha,**locations[oid],
            'source_attributes':ef['properties'],'unchanged_original_feature':True,'attributes_equal_across_representations':True,
            'native_geos_validity_reason':explain_validity(Polygon(nr)),
            'export_geos_validity_reason':explain_validity(shape(ef['geometry'])),
            'native_diagnostics':nd,'export_diagnostics':ed,'service_projected_diagnostics':pd,
            'projection_comparison':{'local_operation':project.description,'hausdorff_distance_m':local.hausdorff_distance(pc),
                'symmetric_difference_m2':local.symmetric_difference(pc).area,'service_projected_candidate_area_m2':pc.area},
            'proposal':{'status':'proposed_not_accepted','evidence_state':'DERIVED','sha256':digest(candidate_bytes),
                'storage_object':'sha256/'+digest(candidate_bytes)+'.response','path':path.relative_to(ROOT).as_posix(),
                'valid':ec.is_valid,'shells':1,'holes':1,'segments_preserved_with_multiplicity':True,
                'area_m2':local.area,'hole_area_m2':holep.area,'shell_area_m2':Polygon(local.exterior).area,
                'publisher_area_square_degrees':nf['attributes']['SHAPE.STArea()'],
                'decoded_area_square_degrees':ec.area,'jurisdiction_covers_candidate':j.covers(ec),
                'jurisdiction_intersection_area_m2':local.intersection(jp).area},
            'hole_context':{'features':neighbors,'union_area_m2':unary_union(clips).area,
                'coverage_fraction':unary_union(clips).area/holep.area,
                'limit':'Neighboring source features corroborate partitioning, not independent legal authority; a hole is not a flood-risk clearance.'},
            'panel_intersections':[f['properties']['FIRM_PAN'] for f in panels if shape(f['geometry']).intersects(ec)],
            'LOMR_footprints_covering_candidate':[f['properties']['CASE_NO'] for f in lomrs if shape(f['geometry']).covers(ec)]})
    valid_clips=[]
    for oid,f in sorted(old.items()):
        if oid in OIDS:continue
        g=shape(f['geometry']);require(g.is_valid,'Unexpected invalid original')
        gp=transform(project.transform,g);require(gp.is_valid,'Projection introduced invalidity')
        clip=gp.intersection(jp)
        if clip.area>0:valid_clips.append(clip)
    baseline=unary_union(valid_clips);candidate_union=unary_union(candidates).intersection(jp)
    require(abs(baseline.area-prior['hazards']['valid_union_area_m2'])<0.0001,'Changed baseline computation')
    for path in ['research/fema-geometry-investigation/probes.json','research/fema-geometry-investigation/render-probes.json',
                 'scripts/collect_document_evidence.py','scripts/investigate_osborn_zoning.py',
                 'scripts/investigate_osborn_fema.py','scripts/prepare_source_staging.py']:
        dependency(path)
    return {'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),
        'scope':{'finding_id':'TL-F-0026','OBJECTIDs':sorted(OIDS),'prior_audit_sha256':PRIOR_SHA,'community':'Osborn'},
        'evidence':evidence,'inputs':inputs,'large_document_evidence':document,
        'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str},
        'source_crs':'EPSG:4269 NAD83','area_crs':'EPSG:26919 NAD83 UTM19N','features':results,
        'interpretation':{'reference':'service/esri-polygon-reference',
            'conclusion':'Vertex-touching rings permitted by Esri persist in the GeoJSON export, where unsplit rings fail GEOS validation. Native ring structure and documented winding support an alternate shell/hole decode, not a claim that the source boundary is wrong.',
            'operation':'Reuse the prior narrow single-touch decoder. No snapping, buffering, polygonization, make_valid, coordinate movement or segment deletion.',
            'acceptance':'Proposed only for the exact original feature versions; no FEMA geometry correction/acceptance layer exists yet. Originals remain excluded from dependent calculations.'},
        'map_evidence':review,
        'coverage_diagnostic':{'adopted':False,'basis':'Counterfactual jurisdiction coverage using two proposed decodings; not parcel screening or legal coverage.',
            'prior_valid_union_m2':baseline.area,'candidate_union_m2':candidate_union.area,
            'candidate_overlap_with_prior_valid_m2':candidate_union.intersection(baseline).area,
            'remaining_geometric_gap_m2':jp.difference(baseline.union(candidate_union)).area,
            'all_existing_results_unchanged':True},
        'finding_reviews':[
            {'finding_id':'TL-F-0026','status':'in_progress','priority':'high','report_pointer':'/features',
             'next_action':'Review the exact-version shell/hole proposals; retain original exclusion until accepted through a FEMA geometry interpretation layer. Resolve or explicitly carry the 0443D map discrepancy in dependent use.',
             'note':'Both native Esri rings contain exactly one vertex touch and opposite-winding nested loops. Proposed valid decodings preserve every segment and agree with service projection. Map context supports the larger feature but does not certify either touch; the smaller feature falls in a blank part of the reviewed 0443D enclosure. Proposals archived, not accepted.'},
            {'finding_id':'TL-F-0105','status':'in_progress','priority':'medium','report_pointer':'/map_evidence',
             'next_action':'Reconcile current NFHL hazard depiction with the blank 0443D revision enclosure at OBJECTID 27129510; continue neighboring-revision and amendment coverage qualification before parcel screening.',
             'note':'TL-F-0026 now has two exact-version decoding proposals. Native/export identity and ring roles are corroborated; live service rendering depicts hazards where the reviewed 0443D enclosure is blank at the approximate locator. This is an unresolved map/service evidence discrepancy, not proof of legal map error or a basis to remove the hazard. Existing adoption and coverage unknowns remain.'}]}


def prepare_load(report,output,current):
    prepare(BASE,output,BASE/'report.json')
    manifest=json.loads((output/'manifest.json').read_bytes())
    def archive(data):
        sha=digest(data);key='sha256/'+sha+'.response'
        require(len(data)<=52428800,'Object exceeds private bucket limit')
        (output/'objects'/key).write_bytes(data);manifest['objects'][key]={'sha256':sha,'bytes':len(data)}
    for path,sha in report['inputs'].items():
        data=(ROOT/path).read_bytes();require(digest(data)==sha,'Changed input');archive(data)
    document=report['large_document_evidence'];pdf=(PRIOR/document['response_path']).read_bytes()
    require(parts(pdf)==document['parts'] and digest(pdf)==document['retrieval']['sha256'],'Changed original PDF')
    for part in document['parts']:archive(pdf[part['offset']:part['offset']+part['bytes']])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows={r['finding_id']:r for r in json.loads(current.read_bytes())['rows']}
    sha=digest((BASE/'report.json').read_bytes());sql=(output/'load.sql').read_text().removesuffix('COMMIT;\n')
    for r in report['finding_reviews']:
        fid=r['finding_id'];old=rows[fid]['event_id']
        event={k:v for k,v in r.items() if k!='report_pointer'}
        event.update(event_id=digest(canonical([fid,sha,'geometry-investigation']).encode()),actor='TerraLucid FEMA geometry investigation',evidence_refs=['audit:'+sha+'#'+r['report_pointer']])
        occurrence=digest(canonical([fid,sha,'geometry-investigation']).encode())
        sql+='INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(occurrence),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        sql+='SELECT ingest.record_finding_event('+jsql(event)+','+literal(old)+');\n'
    (output/'load.sql').write_text(sql+'COMMIT;\n')
    print(json.dumps({'audit_sha256':sha,'archive_objects':len(manifest['objects']),'proposals':'not accepted'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path)
    p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path)
    a=p.parse_args()
    if a.verify_download:
        if not a.prepared:p.error('--verify-download requires --prepared')
        print(verify(a.prepared,a.verify_download))
        data=(BASE/'report.json').read_bytes();manifest=json.loads((a.prepared/'manifest.json').read_bytes())
        require('sha256/'+digest(data)+'.response' in manifest['objects'],'Report differs from prepared archive')
        restore(json.loads(data)['large_document_evidence'],a.verify_download)
        print('Original revision PDF reconstructed and verified')
    else:
        if a.prepare and not a.current:p.error('--prepare requires --current')
        report=build();(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(report,a.prepare,a.current)
        else:print(json.dumps({'features':len(report['features']),'status':'proposed_not_accepted','coverage_diagnostic':report['coverage_diagnostic']}))
