#!/usr/bin/env python3
"""Reproduce a source-preserving Piscataquis inventory and its coverage evaluation."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import pyproj
import shapely
from shapely import from_wkb
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from shapely.validation import explain_validity
from audit_maine_coverage import parse_date
from investigate_osborn_wetlands import decode
from investigate_wetlands_classification import stream_hash
from prepare_source_staging import ROOT, digest, canonical, literal, jsql, prepare

BASE=ROOT/'research/piscataquis-ingestion'
METHOD='scripts/prepare_piscataquis.py'
GPKG_SHA='a224dc073dc87b1a6fccead6f8701304aa67cf734cd351b7e5fc28c2c3b2018f'


def require(ok,message):
    if not ok:raise ValueError(message)


def package_geometry(blob):
    """Preserve invalid originals as held evidence; never repair topology."""
    try:
        require(blob[:3]==b'GP\x00','Unsupported GeoPackage header')
        flags=blob[3];env=(flags>>1)&7
        require(not flags&0b11110000 and env in range(5),'Unsupported/empty geometry header')
        require(struct.unpack(('<' if flags&1 else '>')+'i',blob[4:8])[0]==300001,'Unexpected source SRS')
        g=from_wkb(blob[8+{0:0,1:32,2:48,3:48,4:64}[env]:])
        require(g.geom_type in ('Polygon','MultiPolygon') and not g.is_empty,'Missing/nonpolygon geometry')
        if not g.is_valid:return None,explain_validity(g)
        return g,None
    except Exception as e:return None,str(e)


def relation(g,boundary):
    if g is None:return 'held'
    if not boundary.intersects(g):return 'outside'
    if boundary.covers(g):return 'interior'
    return 'touch' if boundary.touches(g) else 'interior'


def membership(ids,count):
    require(len(ids)==count and len(set(ids))==count and all(type(i)==int for i in ids),'Membership/count mismatch')
    return sorted(ids)


def manifest(entries):
    groups=defaultdict(list)
    for e in entries:groups[e['source_id']].append((e['object_id'],digest(canonical(e).encode())))
    return {sid:{'count':len(rows),'sha256':digest(''.join(f'{oid}:{sha}\n' for oid,sha in sorted(rows)).encode())} for sid,rows in sorted(groups.items())}


def build():
    capture=json.loads((BASE/'capture.json').read_bytes())
    require(capture['method_sha256']==digest((ROOT/'scripts/collect_piscataquis.py').read_bytes()),'Collector changed')
    evidence={};obs={};registry_sha=digest((BASE/'registry.json').read_bytes())
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            data=(log.parent/r['response_file']).read_bytes()
            require(digest(data)==r['sha256'] and len(data)==r['bytes'] and r['http_status']==200,'Evidence changed or failed')
            evidence[log.parent.name+'/'+r['id']]=dict(r,response_path=(log.parent/r['response_file']).relative_to(BASE).as_posix())
            if log.parent.name=='capture':
                payload=json.loads(data);require(not payload.get('error') and not payload.get('exceededTransferLimit'),'Incomplete evidence')
                obs[r['id']]=(payload,digest(canonical([registry_sha,'runs/capture',r]).encode()),r['sha256'])
    records=[];geometries={}
    for s in capture['sources']:
        sid=s['source_id'];members=set();seen=[]
        get=lambda suffix:obs[sid+'-'+suffix][0]
        for i,_ in enumerate(s['selectors']):
            ids=membership(get(f'ids-{i}')['objectIds'] or [],get(f'count-{i}')['count'])
            require(ids==membership(get(f'ids-end-{i}')['objectIds'] or [],len(ids))==s['selector_ids'][i],'Membership drift')
            members.update(ids)
        for k in ['fields','editingInfo','extent','sourceSpatialReference','objectIdField','maxRecordCount']:
            require(get('metadata-start').get(k)==get('metadata-end').get(k),'Metadata drift')
        for page in s['pages']:
            d,observation,sha=obs[page['probe_id']];sr=d['spatialReference']
            require(sr.get('latestWkid',sr['wkid'])==26919,'Unexpected native CRS')
            rows=d['features'];ids=[r['attributes']['OBJECTID'] for r in rows]
            require(membership(ids,len(page['object_ids']))==page['object_ids'],'Page mismatch')
            for row in rows:
                attrs=row['attributes'];oid=attrs['OBJECTID'];seen.append(oid)
                try:g,hold=decode((row.get('geometry') or {}).get('rings'))
                except Exception as e:g,hold=None,str(e)
                e={'source_id':sid,'object_id':oid,'attributes':attrs,'raw_feature':row,'srid':26919,
                   'wkb_hex':None if g is None else g.wkb_hex,'hold':hold,'quality_flags':[],
                   'provenance':{'observation_sha256':observation,'response_sha256':sha,'probe_id':page['probe_id'],
                                 'method':'Native Esri shell/hole decode; every segment preserved; no repair'}}
                records.append(e);geometries[(sid,oid)]=g
        require(sorted(seen)==sorted(members)==s['object_ids'],'Source coverage mismatch')
    civil=[e for e in records if e['source_id']=='civil-boundaries']
    require(all(e['hold'] is None and e['attributes']['COUNTY']=='Piscataquis' for e in civil),'County scope hold')
    boundary=unary_union([geometries[('civil-boundaries',e['object_id'])] for e in civil])
    require(boundary.is_valid and not boundary.is_empty and digest(boundary.wkb)==capture['county_wkb_sha256'],'Boundary changed')
    shapely.prepare(boundary)
    jurisdiction_parts=defaultdict(list);jurisdiction_attrs=defaultdict(list)
    for e in civil:
        code=e['attributes']['GEOCODE'];jurisdiction_parts[code].append(geometries[('civil-boundaries',e['object_id'])]);jurisdiction_attrs[code].append(e['attributes'])
    parcel_keys=Counter((e['source_id'],e['attributes'].get('GPL' if e['source_id']=='ut-parcels' else 'STATE_ID')) for e in records if e['source_id'] in ('ut-parcels','organized-parcels'))
    for e in records:
        e['scope_relation']=relation(geometries[(e['source_id'],e['object_id'])],boundary)
        if e['hold']:e['quality_flags'].append('geometry_held')
        if e['source_id'] in ('ut-parcels','organized-parcels'):
            p=e['attributes'];code=p.get('GEOCODE');key=p.get('GPL' if e['source_id']=='ut-parcels' else 'STATE_ID')
            if not code:e['quality_flags'].append('missing_jurisdiction_code')
            elif code not in jurisdiction_parts and e['scope_relation']=='interior':e['quality_flags'].append('spatial_county_code_disagreement')
            elif code in jurisdiction_parts and e['scope_relation']=='outside':e['quality_flags'].append('county_code_outside_boundary')
            if not (key or '').strip():e['quality_flags'].append('missing_candidate_key')
            elif parcel_keys[(e['source_id'],key)]>1:e['quality_flags'].append('repeated_candidate_key_in_capture')
            e['parsed_date']=parse_date(p.get('MAPYEAR') if e['source_id']=='ut-parcels' else p.get('FMUPDAT'))
            if e['parsed_date']['state']=='UNKNOWN':e['quality_flags'].append('unknown_source_date')
    print('Native civil/parcel/zoning records evaluated:',len(records),flush=True)
    package=json.loads((ROOT/'research/wetlands-classification/report.json').read_bytes())['package']
    gpkg=ROOT/'research/wetlands-classification/package/maine.gpkg'
    require(stream_hash(gpkg)==GPKG_SHA==package['extracted']['sha256'],'Package changed')
    db=sqlite3.connect(gpkg.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    wkt=db.execute('select definition from gpkg_spatial_ref_sys where srs_id=300001').fetchone()[0]
    require(pyproj.CRS.from_wkt(wkt).equals(pyproj.CRS.from_epsg(5070)),'Unqualified CRS mapping')
    operation=pyproj.Transformer.from_crs(26919,5070,always_xy=True)
    study=transform(operation.transform,boundary);require(study.is_valid,'Invalid transformed study boundary');shapely.prepare(study)
    projects=[];native_package_counts={};candidate_counts={}
    for table,sid in [('ME_Wetlands_Project_Metadata','nwi-project'),('ME_Wetlands','nwi-package')]:
        native_package_counts[sid]=db.execute('select count(*) from '+table).fetchone()[0]
        require(db.execute(f'SELECT count(*) FROM {table} t LEFT JOIN rtree_{table}_Shape r ON t.OBJECTID=r.id WHERE r.id IS NULL').fetchone()[0]==0,'Package rows missing spatial index')
        require(db.execute(f'SELECT count(*) FROM rtree_{table}_Shape').fetchone()[0]==native_package_counts[sid],'Package spatial-index membership differs')
        x0,y0,x1,y1=study.bounds
        rows=db.execute(f'SELECT t.* FROM {table} t JOIN rtree_{table}_Shape r ON t.OBJECTID=r.id WHERE r.maxx>=? AND r.minx<=? AND r.maxy>=? AND r.miny<=? ORDER BY t.OBJECTID',(x0,x1,y0,y1))
        candidate_counts[sid]=0
        for row in rows:
            candidate_counts[sid]+=1
            blob=row['Shape'];g,hold=package_geometry(blob);r=relation(g,study)
            if r=='outside':continue
            attrs={k:row[k] for k in row.keys() if k!='Shape'}
            e={'source_id':sid,'object_id':row['OBJECTID'],'attributes':attrs,'srid':5070,'wkb_hex':None if g is None else g.wkb_hex,
               'hold':hold,'scope_relation':r,'quality_flags':['geometry_held'] if hold else [],
               'provenance':{'package_sha256':package['sha256'],'gpkg_sha256':GPKG_SHA,'table':table,'geometry_blob_sha256':digest(blob),
                             'method':'Native GeoPackage WKB decode; equivalent internal SRS 300001 mapped to EPSG:5070; no coordinate change'}}
            if hold:e['original_geometry_blob_hex']=blob.hex()
            records.append(e);geometries[(sid,e['object_id'])]=g
            if sid=='nwi-project' and g is not None:projects.append((e,g))
        print(sid,'envelope candidates',candidate_counts[sid],flush=True)
    db.close()
    project_union=unary_union([g for _,g in projects]);project_tree=STRtree([g for _,g in projects])
    wetland_project_counts=Counter();no_project=0
    for e in records:
        if e['source_id']!='nwi-package' or e['hold']:continue
        g=geometries[('nwi-package',e['object_id'])]
        ids=[projects[int(i)][0]['object_id'] for i in project_tree.query(g,predicate='intersects') if not g.touches(projects[int(i)][1])]
        e['package_project_candidates']=sorted(ids);wetland_project_counts[len(ids)]+=1
        if not ids:no_project+=1;e['quality_flags'].append('no_positive_area_project_footprint')
    spatial_indexes={}
    for sid in ['ut-parcels','organized-parcels','lupc-zoning','nwi-package']:
        gs=[g for (s,_),g in geometries.items() if s==sid and g is not None]
        spatial_indexes[sid]=STRtree(gs)
    reference_audit=json.loads((ROOT/'research/maine-coverage/report.json').read_bytes())
    references={j['reference']['GEOCODE']:j for j in reference_audit['jurisdictions']}
    jurisdictions=[]
    for code,parts in sorted(jurisdiction_parts.items(),key=lambda kv:str(kv[0])):
        g=unary_union(parts);gp=transform(operation.transform,g);counts={}
        for sid,tree in spatial_indexes.items():
            query=gp if sid=='nwi-package' else g
            counts[sid]=sum(not query.touches(tree.geometries[int(i)]) for i in tree.query(query,predicate='intersects'))
        attrs=jurisdiction_attrs[code]
        tree=spatial_indexes['lupc-zoning'];zs=[tree.geometries[int(i)] for i in tree.query(g,predicate='intersects')]
        zoning_fraction=g.intersection(unary_union(zs)).area/g.area if zs else 0.0
        ref=references.get(code,{})
        jurisdictions.append({'GEOCODE':code,'source_names':sorted({str(a.get('TOWN')) for a in attrs}),
          'source_TYPE_values':sorted({str(a.get('TYPE')) for a in attrs}), 'civil_parts':len(parts),'area_m2':g.area,
          'reference':ref.get('reference'),'reference_status_label':ref.get('reference_status_label'),
          'reference_status_currency':'UNKNOWN; archived GEOCODES status/notes can disagree',
          'valid_lupc_union_area_fraction':zoning_fraction,
          'positive_area_source_features':counts,'parcel_completeness':'UNKNOWN','legal_zoning_coverage':'UNKNOWN'})
    summary={}
    for sid in sorted({e['source_id'] for e in records}):
        es=[e for e in records if e['source_id']==sid]
        summary[sid]={'captured_records':len(es),'scope_relations':dict(Counter(e['scope_relation'] for e in es)),
          'quality_flags':dict(Counter(f for e in es for f in e['quality_flags'])),
          'hold_reasons':dict(Counter(e['hold'] for e in es if e['hold']))}
        if sid.endswith('parcels'):
            summary[sid]['source_date_values']=dict(Counter(str(e['parsed_date'].get('value')) for e in es if e['scope_relation']=='interior'))
    lineage={'projects':[{'object_id':e['object_id'],'attributes':e['attributes'],'county_overlap_m2':g.intersection(study).area} for e,g in projects],
       'county_area_m2':study.area,'county_outside_valid_project_footprints_m2':study.difference(project_union).area,
       'project_count_per_valid_wetland':dict(wetland_project_counts),'wetlands_without_positive_area_project':no_project,
       'interpretation':'Project footprint intersects a feature; not proof of per-feature image use, wetland completeness, delineation, or regulatory applicability.'}
    methods=['scripts/collect_piscataquis.py',METHOD,'scripts/investigate_osborn_wetlands.py','scripts/audit_maine_coverage.py','scripts/prepare_source_staging.py',
             'supabase/migrations/20260921040000_county_source_inventory.sql']
    report={'scope':'Piscataquis County, Maine','evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),
      'evidence':evidence,'inputs':{p:digest((ROOT/p).read_bytes()) for p in methods+['research/piscataquis-ingestion/capture.json','research/wetlands-classification/report.json','research/maine-coverage/report.json']},
      'boundary':{'source':'civil-boundaries COUNTY=Piscataquis; all TYPE values included','wkb_hex':boundary.wkb_hex,'sha256':digest(boundary.wkb),'srid':26919,'area_m2':boundary.area,'state':'DERIVED','legal_boundary_confidence':'UNKNOWN'},
      'package':package,'package_native_counts':native_package_counts,'package_envelope_candidates':candidate_counts,
      'projection':{'from':26919,'to':5070,'description':operation.description,'definition':operation.definition,'accuracy_m':operation.accuracy,
                    'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str,'shapely':shapely.__version__,'GEOS':shapely.geos_version_string},
      'record_manifest':manifest(records),'summary':summary,'jurisdictions':jurisdictions,'wetlands_lineage':lineage,
      'limits':['Civil TYPE is preserved literally (including freshwater parts); it is not a legal organization-status classification.',
        'Jurisdiction intersection counts can include cross-boundary slivers and duplicate a feature across jurisdictions; they are not coverage certification.',
        'Source inventory only; no parcel scoring or offer-readiness conclusions.',
        'County boundary depends on the complete captured Maine civil layer county label and union; legal/county boundary authority not independently established.',
        'Parcel capture combines county attributes and county envelope. Full originals and out-of-scope extras retained; full parcel geometries are never clipped.',
        'Native Esri ring ambiguities/invalidities are held; no Osborn correction transfers to this source version.',
        'Start/end memberships and available metadata match; queries are not an atomic snapshot.',
        'Source assessment features are not distinct legal parcels, surveyed boundaries, title or access rights. Cross-source overlap is not deduplicated.',
        'Associated assessment table and UT valuation books are not expanded in this load.',
        'LUPC source polygons are inventoried regardless of date/flags. Municipal zoning, official map currency, rule-based protections and jurisdiction applicability require separate evidence.',
        'Wetlands use the archived Maine package only; county service identity, release refresh and national availability are not newly qualified.',
        'Project imagery dates do not establish wetland completeness or legal applicability. No mapped wetland is not evidence of absence.',
        'No automatic correction acceptance, geometry repair, legal access, septic or buildability conclusion.']}
    return report,records


def prepare_load(output):
    report,records=build();data=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();(BASE/'report.json').write_bytes(data);audit=digest(data)
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp)/'stage';prepare(BASE,stage,BASE/'report.json')
        output.mkdir(parents=True,exist_ok=False)
        import shutil
        shutil.copytree(stage/'objects',output/'objects')
        m=json.loads((stage/'manifest.json').read_bytes())
        def archive(raw):
            sha=digest(raw);key='sha256/'+sha+'.response';(output/'objects'/key).write_bytes(raw);m['objects'][key]={'sha256':sha,'bytes':len(raw)}
        for p in report['inputs']:archive((ROOT/p).read_bytes())
        with (ROOT/'research/wetlands-classification'/report['package']['response_path']).open('rb') as f:
            for part in report['package']['parts']:
                raw=f.read(part['bytes']);require(digest(raw)==part['sha256'],'Changed package part');archive(raw)
            require(not f.read(1),'Package archive tail')
        with (output/'load.sql').open('w') as f:
            f.write((stage/'load.sql').read_text().rsplit('COMMIT;',1)[0])
            f.write('INSERT INTO ingest.county_inventory_batch(audit_sha256) VALUES ('+literal(audit)+') ON CONFLICT DO NOTHING;\n')
            # Bound statement sizes and network round trips at county scale.
            for offset in range(0,len(records),250):
                values=['('+','.join([literal(audit),literal(e['source_id']),str(e['object_id']),literal(canonical(e))])+')' for e in records[offset:offset+250]]
                f.write('INSERT INTO ingest.county_inventory_feature(audit_sha256,source_id,object_id,input_text) VALUES '+','.join(values)+' ON CONFLICT DO NOTHING;\n')
            # Append evidence to established categories; never reset existing review states.
            findings={'TL-F-0001':'/jurisdictions','TL-F-0007':'/summary','TL-F-0008':'/summary','TL-F-0011':'/summary','TL-F-0018':'/jurisdictions','TL-F-0021':'/jurisdictions','TL-F-0022':'/summary','TL-F-0109':'/summary/lupc-zoning','TL-F-0110':'/jurisdictions','TL-F-0117':'/wetlands_lineage'}
            for fid,pointer in findings.items():
                occurrence=digest(canonical([audit,fid,pointer]).encode())
                f.write('INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(occurrence),literal(fid),literal(audit),jsql({'scope':report['scope'],'report_pointer':pointer,'next_action':'Review county inventory coverage, holds and qualification gaps before parcel screening.'})])+') ON CONFLICT DO NOTHING;\n')
            finding={'finding_id':'TL-F-0029','title':'Piscataquis county inventory qualification',
              'description':'County-wide source inventory requires review of held geometry, parcel identity/coverage, municipal zoning gaps, and wetland imagery/project qualifications before screening.',
              'source_ids':['ut-parcels','organized-parcels','lupc-zoning','nwi-package'],'scope':{'county':'Piscataquis'},'evidence_state':'DERIVED'}
            f.write('INSERT INTO ingest.finding(finding_id,title,description,source_ids,scope,evidence_state) VALUES ('+','.join([literal(finding['finding_id']),literal(finding['title']),literal(finding['description']),"ARRAY["+','.join(map(literal,finding['source_ids']))+"]::text[]",jsql(finding['scope']),literal('DERIVED')])+') ON CONFLICT DO NOTHING;\n')
            ev={'event_id':digest(canonical([audit,'TL-F-0029','initial-review']).encode()),'finding_id':'TL-F-0029','status':'open','priority':'high',
                'next_action':'Prioritize county geometry holds and jurisdiction coverage gaps; review municipal zoning and wetland imagery before enabling parcel screening.',
                'actor':'TerraLucid county ingestion','note':'County sources preserved separately; no corrections accepted or critical unknowns resolved.',
                'evidence_refs':['audit:'+audit+'#/summary','audit:'+audit+'#/jurisdictions','audit:'+audit+'#/wetlands_lineage']}
            f.write('INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(digest(canonical([audit,'TL-F-0029']).encode())),literal('TL-F-0029'),literal(audit),jsql({'report_pointer':'/summary','scope':report['scope']})])+') ON CONFLICT DO NOTHING;\n')
            f.write('SELECT ingest.record_finding_event('+jsql(ev)+',NULL);\n')
            f.write('COMMIT;\n')
        (output/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    print(json.dumps({'audit_sha256':audit,'records':len(records),'summary':report['summary']},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare_load(a.output)
