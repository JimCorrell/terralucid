#!/usr/bin/env python3
"""Read-only, topic-specific evidence qualification for a county AOI or source parcel.

Outputs private local JSON. Never updates source data, screenings or offer readiness.
"""
import argparse,hashlib,json,math,os,subprocess,tempfile,uuid
from pathlib import Path
import shapely
from shapely import wkb
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
from apply_prepared_load import connection_environment

ROOT=Path(__file__).resolve().parents[1]
VERSION='area-qualification-v1'
PARCELS={'ut-parcels','organized-parcels'}
GROUPS={'identity':PARCELS,'zoning':{'lupc-zoning'},'wetlands':{'nwi-package','nwi-project'}}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def method_hash():
    return digest({'files':{p:hashlib.sha256((ROOT/'scripts'/p).read_bytes()).hexdigest() for p in ['qualify_area.py','qualification_context.sql','qualification_extract.sql']},'shapely':shapely.__version__,'geos':shapely.geos_version_string})
def validate_request(r):
    for k in ('audit','snapshot'):
        if not isinstance(r.get(k),str) or len(r[k])!=64 or any(c not in '0123456789abcdef' for c in r[k]):raise ValueError('Expected SHA-256 '+k)
    if type(r.get('purchase_candidate')) is not bool:raise ValueError('Explicit purchase-candidate boolean required')
    if 'geometry' in r:
        if 'source_id' in r or 'object_id' in r:raise ValueError('Select either AOI or source parcel')
        g=shape(r['geometry'])
        if g.geom_type not in ('Polygon','MultiPolygon') or g.is_empty or not g.is_valid or g.has_z:raise ValueError('AOI requires valid nonempty 2D polygon geometry')
        if not all(math.isfinite(x) for x in g.bounds) or not(-180<=g.bounds[0]<=g.bounds[2]<=180 and -90<=g.bounds[1]<=g.bounds[3]<=90):raise ValueError('AOI must be longitude/latitude EPSG:4326')
    elif r.get('source_id') not in PARCELS or type(r.get('object_id')) is not int or r['object_id']<0:raise ValueError('Expected assessment source and object ID')

def read_database(request,context_only=False):
    validate_request(request)
    cli=os.environ.get('TERRALUCID_SUPABASE_CLI')
    command=[cli] if cli else ['npx','--yes','supabase@2.117.0']
    result=subprocess.run(command+['db','dump','--linked','--dry-run','--agent','no','--output-format','text'],capture_output=True,text=True,cwd=ROOT,timeout=60)
    if result.returncode:raise RuntimeError('Could not obtain temporary linked database credentials')
    env=connection_environment(result.stdout,'yytsjlmbyqhcqfalbjca')
    env['PGCONNECT_TIMEOUT']='20'
    literal="'"+json.dumps(request,allow_nan=False).replace("'","''")+"'"
    sql=(ROOT/'scripts/qualification_context.sql').read_text().replace('__REQUEST__',literal)
    sql+= ' select document from context;' if context_only else (ROOT/'scripts/qualification_extract.sql').read_text()
    sql="SET ROLE postgres; BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL standard_conforming_strings=on; SET LOCAL search_path=pg_catalog,ingest,extensions; SET LOCAL statement_timeout='5min';\n"+sql+'\nCOMMIT;'
    client='terralucid-qualification-'+uuid.uuid4().hex[:12]
    cmd=['docker','run','--rm','--name',client,'-i','--platform','linux/amd64']
    for key in env:cmd+=['--env',key]
    cmd+=['postgis/postgis:17-3.5','psql','-X','-q','-t','-A','-v','ON_ERROR_STOP=1','-f','-']
    try:
        result=subprocess.run(cmd,input=sql,text=True,capture_output=True,env={**os.environ,**env},timeout=360)
    except subprocess.TimeoutExpired:
        subprocess.run(['docker','rm','-f',client],capture_output=True,timeout=20)
        raise RuntimeError('Read-only client exceeded six-minute deadline; no packet produced') from None
    if result.returncode:
        directory=ROOT/'.local/qualification-errors';directory.mkdir(parents=True,exist_ok=True)
        fd,path=tempfile.mkstemp(prefix='query-',suffix='.log',dir=directory)
        with os.fdopen(fd,'w') as log:log.write(result.stderr)
        raise RuntimeError('Read-only query failed; private diagnostic: '+path)
    return json.loads(result.stdout)

def held_envelope(f):
    """No decoding/repair: conservative rectangle around every original vertex."""
    try:
        rings=f['raw_held_geometry']['rings']
        if not isinstance(rings,list) or not rings: return None
        points=[]
        for ring in rings:
            if not isinstance(ring,list) or not ring:return None
            for p in ring:
                if not isinstance(p,list) or len(p)<2 or any(type(x) not in (float,int) or not math.isfinite(x) for x in p[:2]):return None
                points.append(p)
        bounds=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
        # Held records in the county's native Esri sources are EPSG:26919.
        # Do not invent a bbox for another representation or CRS.
        if f['native_srid']!=26919:return None
        from shapely.geometry import MultiPoint
        return MultiPoint([(bounds[0],bounds[1]),(bounds[2],bounds[3])]).envelope
    except (KeyError,TypeError,ValueError):return None

def ref(f):
    return {k:f.get(k) for k in ['source_id','object_id','input_sha256','provenance','flags','parsed_date','correction_id','geometry_event_id','candidate_sha256','correction_status']}

def coverage(geometries,aoi):
    if not geometries:return {'fraction':0.0,'uncovered_m2':aoi.area,'state':'missing'}
    covered=unary_union(geometries).intersection(aoi)
    gap=aoi.difference(covered).area
    return {'fraction':covered.area/aoi.area,'uncovered_m2':gap,'state':'full_geometric' if gap==0 else 'partial_geometric'}

def qualify(capture):
    r=capture['request'];validate_request(r);ctx=capture['context']
    if ctx.get('source_audit')!=r['audit'] or ctx.get('geometry_snapshot')!=r['snapshot']:raise ValueError('Capture dependencies do not match requested scope')
    if not ctx['source_exists']:raise ValueError('Unknown county source audit')
    if not capture.get('aoi_wkb'):raise ValueError('Source parcel absent or geometry held; supply a valid independent AOI to investigate')
    aoi=wkb.loads(capture['aoi_wkb'],hex=True)
    if aoi.is_empty or not aoi.is_valid or aoi.geom_type not in ('Polygon','MultiPolygon') or aoi.area<=0:raise ValueError('Unusable AOI')
    valid=[];held=[];unknown=[];geometries={}
    for f in capture['features']:
        if f.get('hold'):
            env=held_envelope(f)
            if env is None:unknown.append(ref(f)|{'reason':'held_geometry_extent_unknown','hold':f['hold']})
            elif env.intersects(aoi):held.append(ref(f)|{'reason':'held_envelope_intersects','hold':f['hold'],'envelope_bounds':list(env.bounds)})
            continue
        g=wkb.loads(f['geometry_wkb'],hex=True)
        if not g.is_valid or g.is_empty:raise ValueError('Unexpected unusable effective geometry')
        if g.intersects(aoi):
            f=dict(f);f['aoi_relation']='touch' if g.intersection(aoi).area==0 else 'interior'
            valid.append(f);geometries[(f['source_id'],f['object_id'])]=g
    topics={}
    for topic,sources in GROUPS.items():
        records=[f for f in valid if f['source_id'] in sources]
        blocks=[f for f in held+unknown if f['source_id'] in sources|{'civil-boundaries'}]
        reasons=[]
        if not ctx['snapshot_current']:reasons.append('stale_geometry_snapshot')
        if not capture['aoi_within_county']:reasons.append('aoi_not_fully_within_county_scope')
        if blocks:reasons.append('potentially_affected_by_held_geometry')
        interior=[f for f in records if f['aoi_relation']=='interior']
        if not interior:reasons.append('no_positive_area_source_evidence')
        measure_source='nwi-project' if topic=='wetlands' else 'lupc-zoning' if topic=='zoning' else None
        cov=coverage([geometries[(f['source_id'],f['object_id'])] for f in interior if measure_source is None or f['source_id']==measure_source],aoi)
        if cov['state']!='full_geometric':reasons.append('incomplete_geometric_coverage')
        if topic=='identity':reasons+=['canonical_identity_unresolved','assessment_boundary_not_surveyed','source_currentness_unverified']
        if topic=='zoning':reasons+=['current_legal_applicability_unverified','municipal_zoning_not_loaded']
        if topic=='wetlands':reasons+=['imagery_age_and_completeness_unverified_for_site','inventory_absence_not_wetland_clearance']
        topics[topic]={'status':'stale' if not ctx['snapshot_current'] else 'review_required' if interior or blocks else 'missing',
            'evidence_state':'DERIVED','reasons':reasons,'coverage':cov,
            'inventory_intersections_usable':bool(ctx['snapshot_current'] and capture['aoi_within_county'] and not blocks and interior),
            'held_evidence':blocks,'records':[ref(f)|{'aoi_relation':f['aoi_relation'],'source_identifiers':{k:f.get('attributes',{}).get(k) for k in ['GEOCODE','GPL','STATE_ID','MAPYEAR','FMUPDAT']}} for f in records],
            'legal_or_site_suitability':'UNKNOWN'}
        topics[topic]['finding_candidates']=[f['id'] for f in capture.get('findings',[]) if set(f.get('source_ids',[])) & sources or f['id']=='TL-F-0029']
        if topics[topic]['finding_candidates']:topics[topic]['reasons'].append('finding_applicability_requires_review')
    # Cross-source intersection is only an identity-review candidate, never a merge.
    parcels=[f for f in valid if f['source_id'] in PARCELS and f['aoi_relation']=='interior']
    overlaps=[]
    organized=[f for f in parcels if f['source_id']=='organized-parcels']
    tree=STRtree([geometries[(f['source_id'],f['object_id'])] for f in organized])
    for left in [f for f in parcels if f['source_id']=='ut-parcels']:
        lg=geometries[(left['source_id'],left['object_id'])]
        for index in tree.query(lg,predicate='intersects'):
            right=organized[int(index)]
            rg=geometries[(right['source_id'],right['object_id'])]
            area=lg.intersection(rg).intersection(aoi).area
            if area>0:overlaps.append({'ut_object_id':left['object_id'],'organized_object_id':right['object_id'],'overlap_within_aoi_m2':area,'identity_state':'UNKNOWN','match_evidence_state':'INFERRED'})
    topics['identity']['cross_source_overlap_candidates']=sorted(overlaps,key=lambda x:(x['ut_object_id'],x['organized_object_id']))
    if overlaps:topics['identity']['reasons'].append('cross_source_identity_conflict_candidates')
    civil=[f for f in valid if f['source_id']=='civil-boundaries' and f['aoi_relation']=='interior']
    orneville=[geometries[(f['source_id'],f['object_id'])] for f in civil if str(f['attributes'].get('GEOCODE'))=='21821']
    evidence=[]
    if orneville:
        for audit in capture.get('readiness_audits',[]):
            d=audit['document'];o=d.get('orneville',{})
            if o.get('community_id')=='230465':
                evidence.append({'audit_sha256':audit['sha256'],'community_id':'230465','base_product':o['base_product'],
                    'letters':o['letters'],'letter_documents_reviewed':o['letter_documents_reviewed'],
                    'nfhl_hazard_envelope_ids':o['nfhl_hazard_envelope_ids'],'review':o['review'],
                    'aoi_coverage_by_orneville_civil_boundary':coverage(orneville,aoi),'evidence_state':'VERIFIED','parcel_applicability':'UNKNOWN'})
    topics['flood']={'status':'review_required' if evidence else 'missing','evidence':evidence,'evidence_state':'UNKNOWN',
        'inventory_intersections_usable':False,'reasons':['flood_overlay_not_qualified','empty_digital_response_is_not_clearance','current_map_and_letter_applicability_unverified'],
        'legal_or_site_suitability':'UNKNOWN'}
    for name in ['soils','terrain']:
        topics[name]={'status':'missing','evidence_state':'UNKNOWN','reasons':['no_qualified_source_adapter_in_this_version'],'blocks_general_discovery':False}
    for name in ['septic_suitability','buildability']:
        topics[name]={'status':'review_required' if r['purchase_candidate'] else 'not_requested','evidence_state':'UNKNOWN',
            'reasons':['purchase_candidate_site_investigation_required'] if r['purchase_candidate'] else ['purchase_investigation_not_requested'],
            'blocks_general_discovery':False}
    topics['access_title']={'status':'review_required' if r['purchase_candidate'] else 'not_requested','evidence_state':'UNKNOWN','reasons':['rights_not_established_by_mapped_access']}
    # Preserve all open register entries as scope candidates; do not imply each applies.
    findings=[dict(f,applicability='UNASSESSED register scope candidate') for f in capture.get('findings',[])]
    return {'schema':VERSION,'method_sha256':method_hash(),'request':r,'context':ctx,'capture_sha256':digest(capture),
        'captured_at':capture.get('captured_at'),'aoi_sha256':hashlib.sha256(bytes.fromhex(capture['aoi_wkb'])).hexdigest(),'aoi_within_county':capture['aoi_within_county'],
        'jurisdiction_candidates':[ref(f)|{'source_attributes':f['attributes'],'authority_state':'UNKNOWN; historical civil attributes only'} for f in civil],
        'topics':topics,'potential_findings':findings,'geometry_evidence_state':'DERIVED','canonical_parcel_identity':'UNKNOWN',
        'qualified_for_parcel_screening':False,'offer_readiness':'NOT_ASSESSED',
        'limits':['Read-only evidence packet, not parcel clearance or a suitability score','Check currency before reuse; dependencies are conservative across all source observations, audits and findings','Currentness means unchanged captured dependencies, not current real-world facts','Municipal applicability and other FEMA communities need explicit source adapters'],
        'runtime':capture.get('runtime',{})}

def currency(packet,context):
    reasons=[]
    if packet.get('schema')!=VERSION or packet.get('method_sha256')!=method_hash():reasons.append('qualification_method_changed')
    if packet.get('context')!=context:reasons.append('captured_dependencies_changed')
    if not context.get('snapshot_current'):reasons.append('geometry_snapshot_stale')
    if not context.get('source_exists'):reasons.append('source_audit_missing')
    return {'needs_revisit':bool(reasons),'reasons':reasons,'use_policy':'recompute_before_use' if reasons else 'unchanged_dependencies_only; retain all topic limits'}

def private_write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation prevents silently replacing prior evidence.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('capture');q.add_argument('--request',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('check');q.add_argument('--packet',type=Path,required=True)
    a=p.parse_args()
    if a.command=='capture':
        if a.output.exists():raise ValueError('Output directory must be new')
        request=json.loads(a.request.read_bytes());capture=read_database(request);packet=qualify(capture)
        private_write(a.output/'capture.json',capture);private_write(a.output/'packet.json',packet)
        print('Private evidence packet written; no database changes')
    else:
        packet=json.loads(a.packet.read_bytes());result=currency(packet,read_database(packet['request'],True));print(json.dumps(result));return 2 if result['needs_revisit'] else 0
    return 0
if __name__=='__main__':raise SystemExit(main())
