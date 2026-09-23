"""Validate a captured soil inventory and prepare a private source-preserving bundle.

Does not connect to Supabase, change qualification, repair geometry, or rate sites.
"""
import argparse,hashlib,json,shutil
from collections import Counter
from pathlib import Path
import shapely,pyproj
from shapely import wkt,wkb
from shapely.geometry import box
from shapely.ops import transform,unary_union
from shapely.validation import explain_validity
from collect_county_soils import rows,sha

def validate_geometry(text,project):
    try:
        g=wkt.loads(text)
        if g.is_empty or g.geom_type not in ('Polygon','MultiPolygon') or not g.is_valid:
            return None,None,'source: '+explain_validity(g)
        projected=transform(project,g)
        if not projected.is_valid or projected.is_empty:return None,None,'projected: '+explain_validity(projected)
        return g,projected,None
    except (ValueError,shapely.errors.GEOSException,TypeError) as e:return None,None,type(e).__name__

def verified_responses(root):
    capture=json.loads((root/'capture.json').read_bytes());raw=(root/'requests.json').read_bytes()
    if sha(raw)!=capture['requests_sha256']:raise ValueError('Request manifest checksum mismatch')
    responses={};logs=json.loads(raw)
    for log in logs:
        name=log['response_file']
        if Path(name).name!=name:raise ValueError('Unsafe response filename')
        raw=(root/name).read_bytes()
        if sha(raw)!=log['sha256'] or len(raw)!=log['bytes']:raise ValueError('Response checksum mismatch: '+name)
        if log['id'] in responses:raise ValueError('Duplicate response identity')
        responses[log['id']]=(rows(json.loads(raw)),log)
    return capture,responses

def prepare(root,out,terrain):
    capture,responses=verified_responses(root)
    if capture['method_sha256']!=sha(Path(__file__).with_name('collect_county_soils.py').read_bytes()):raise ValueError('Capture method changed')
    if capture['status']!='CAPTURED' or not capture['catalog_and_membership_stable']:raise ValueError('Incomplete capture')
    b=capture['boundary'];boundary=wkb.loads(b['wkb_hex'],hex=True)
    if sha(boundary.wkb)!=b['sha256'] or b['srid']!=26919 or not boundary.is_valid:raise ValueError('County boundary mismatch')
    if responses['catalog-start'][0]!=responses['catalog-end'][0] or responses['polygon-ids-start'][0]!=responses['polygon-ids-end'][0]:raise ValueError('Source drift')
    project=pyproj.Transformer.from_crs(4326,26919,always_xy=True)
    out.mkdir(parents=True,exist_ok=False);(out/'objects').mkdir()
    # Archive exact originals by content hash, including method and request context.
    objects={}
    for path in [root/'capture.json',root/'requests.json',Path(__file__),Path(__file__).with_name('collect_county_soils.py')]+[root/r[1]['response_file'] for r in responses.values()]:
        raw=path.read_bytes();key=sha(raw);shutil.copyfile(path,out/'objects'/key);objects[key]={'bytes':len(raw)}
    tables={};counts={};orphans={};nulls={};prepared=0
    keys={'legend':'lkey','mapunit':'mukey','component':'cokey','chorizon':'chkey'}
    with (out/'records.jsonl').open('w') as dest:
        def emit(kind,key,raw,log,ordinal,**extra):
            nonlocal prepared
            record={'kind':kind,'source_key':key,'raw':raw,'provenance':{'response_sha256':log['sha256'],'response_id':log['id'],'row_ordinal':ordinal},**extra}
            dest.write(json.dumps(record,separators=(',',':'),allow_nan=False)+'\n');prepared+=1
        for kind,key in keys.items():
            data,log=responses[kind];table={r[key]:r for r in data}
            if len(table)!=len(data) or any(not k for k in table):raise ValueError('Duplicate/null '+key)
            expected=int(responses[kind+'-count'][0][0]['n'])
            if len(table)!=expected:raise ValueError('Table count mismatch')
            tables[kind]=table;counts[kind]=len(table)
            for ordinal,r in enumerate(data):emit(kind,r[key],r,log,ordinal)
        for child,parent,link in [('mapunit','legend','lkey'),('component','mapunit','mukey'),('chorizon','component','cokey')]:
            orphans[child]=[k for k,r in tables[child].items() if r.get(link) not in tables[parent]]
            if orphans[child]:raise ValueError('Missing parent rows: '+child)
        for kind,fields in [('mapunit',['muname','mukind']),('component',['comppct_r','slope_r','drainagecl']),('chorizon',['hzdept_r','hzdepb_r','ksat_r'])]:
            nulls[kind]={field:sum(r.get(field) in (None,'') for r in tables[kind].values()) for field in fields}
        gs=[];held=[];membership=[];relations=Counter();survey_counts=Counter();notcom=[]
        for name,(data,log) in responses.items():
            if not name.startswith('polygons-'):continue
            for ordinal,r in enumerate(data):
                key=r['mupolygonkey'];membership.append(key)
                if r['mukey'] not in tables['mapunit']:raise ValueError('Polygon mapunit missing')
                mu=tables['mapunit'][r['mukey']];code=tables['legend'][mu['lkey']]['areasymbol']
                native,g,hold=validate_geometry(r['source_wkt'],project.transform)
                relation='held' if hold else 'outside' if not g.intersects(boundary) else 'touch' if g.intersection(boundary).area==0 else 'interior'
                relations[relation]+=1
                if relation=='interior':
                    gs.append(g);survey_counts[code]+=1
                    if 'NOTCOM' in str(mu.get('musym','')).upper() or 'NOTCOM' in str(mu.get('muname','')).upper():notcom.append(g)
                if hold:held.append({'mupolygonkey':key,'hold':hold,'response_sha256':log['sha256']})
                emit('mupolygon',key,r,log,ordinal,geometry_wkb=None if hold else native.wkb_hex,srid=4326,hold=hold,scope_relation=relation,areasymbol=code)
        expected=[r['mupolygonkey'] for r in responses['polygon-ids-start'][0]]
        if len(set(membership))!=len(membership) or sorted(membership)!=sorted(expected) or len(membership)!=capture['polygon_count']:raise ValueError('Polygon membership mismatch')
        # Survey outlines and metadata stay in exact response archives, not fabricated map units.
    print('Prepared records; calculating county coverage',flush=True)
    union=unary_union(gs);gap=boundary.difference(union)
    coverage={'county_area_m2':boundary.area,'uncovered_m2':gap.area,'fraction':max(0,min(1,1-gap.area/boundary.area)),
              'state':'full_geometric' if gap.area==0 else 'partial_geometric',
              'notcom_intersection_m2':unary_union(notcom).intersection(boundary).area if notcom else 0}
    # Terrain filtering is on catalog rectangles only; no claim about actual pixels.
    inventory=json.loads(terrain.read_bytes());geographic=transform(pyproj.Transformer.from_crs(26919,4326,always_xy=True).transform,boundary)
    selected=[];outside=[]
    for item in inventory['terrain']['products']:
        bounds=item['boundingBox'];g=box(bounds['minX'],bounds['minY'],bounds['maxX'],bounds['maxY'])
        (selected if g.intersection(geographic).area>0 else outside).append(item)
    report={'evidence_state':'DERIVED','method':'scripts/prepare_county_soils.py','method_sha256':sha(Path(__file__).read_bytes()),
        'capture_sha256':sha((root/'capture.json').read_bytes()),'boundary_sha256':b['sha256'],
        'runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__},
        'projection':project.description,'counts':counts|{'mupolygon':len(membership),'prepared_records':prepared},'polygon_relations':dict(relations),
        'interior_polygons_by_survey':dict(survey_counts),'survey_outlines':capture['surveys'],'coverage':coverage,
        'geometry_holds':held,'orphan_counts':{k:len(v) for k,v in orphans.items()},'null_attribute_counts':nulls,
        'mapunits_without_components':sum(k not in {r['mukey'] for r in tables['component'].values()} for k in tables['mapunit']),
        'components_without_horizons':sum(k not in {r['cokey'] for r in tables['chorizon'].values()} for k in tables['component']),
        'terrain':{'input_sha256':sha(terrain.read_bytes()),'candidate_count':len(inventory['terrain']['products']),
          'retained_count':len(selected),'excluded_count':len(outside),'advertised_bytes_retained':sum(i['sizeInBytes'] or 0 for i in selected),
          'retained_source_ids':[i['sourceId'] for i in selected],'excluded_source_ids':[i['sourceId'] for i in outside],
          'scope':'positive-area catalog rectangle intersection with transformed county; not valid-pixel coverage'},
        'limits':['Not loaded to Supabase; prepared private source bundle only','No soil suitability or screening approval','Survey/soil and county boundaries differ; all positive intersections retained','Sequential requests are not an atomic snapshot; before/after catalog and ID checks cannot detect every attribute change','Nulls and missing horizons may represent water/miscellaneous units; not automatic defects','No corrections or gap tolerance; field dates, mapping scale and legal suitability remain unqualified']}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    manifest={'objects':objects,'records_sha256':sha((out/'records.jsonl').read_bytes()),'report_sha256':sha((out/'report.json').read_bytes()),'records':prepared,'deployment_status':'prepared_not_loaded'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'counts':report['counts'],'coverage':coverage,'holds':len(held),'terrain':{k:v for k,v in report['terrain'].items() if not k.endswith('source_ids')}},indent=2))
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--terrain',type=Path,required=True);a=p.parse_args();prepare(a.capture,a.output,a.terrain)
