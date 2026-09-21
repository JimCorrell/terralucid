#!/usr/bin/env python3
"""Propose an exact-segment decode for NWI availability OBJECTID 3; never activate it."""
import argparse
import json
import math
from collections import Counter
from pathlib import Path
import fitz
import pyproj
import shapely
from shapely.geometry import LinearRing, MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity
from investigate_osborn_wetlands import decode
from prepare_source_staging import ROOT, canonical, digest, prepare, literal, jsql, verify

BASE = ROOT/'research/wetlands-availability'
METHOD = 'scripts/investigate_wetlands_availability.py'
PRIOR = 'e1449e8384d5d712dfdae9df26814330d1b9f7dc31ae82fc8765bce565b61906'


def require(ok,message):
    if not ok:raise ValueError(message)


def directed_edges(rings):
    return Counter((tuple(a),tuple(b)) for r in rings for a,b in zip(r,r[1:]))


def split_touches(ring):
    """Decompose only exact twice-visited vertices, with unchanged directed edges.

    Every resulting cycle must be simple, nondegenerate and retain its winding.
    Crossings without a repeated source vertex, triple visits and zero edges fail.
    This is a bounded proposal method, never an automatic ingestion repair.
    """
    require(len(ring) >= 4 and ring[0] == ring[-1],'Expected closed ring')
    require(all(len(p) == 2 and all(math.isfinite(v) for v in p) for p in ring),'Nonfinite/non-2D ring')
    require(all(a != b for a,b in zip(ring,ring[1:])),'Zero-length source edge')
    require(max(Counter(map(tuple,ring[:-1])).values()) <= 2,'Vertex visited more than twice')
    pending,loops = [ring],[]
    while pending:
        r = pending.pop();seen = {};split = False
        for i,p in enumerate(r[:-1]):
            key = tuple(p)
            if key in seen:
                a = seen[key];parts = [r[a:i+1],r[i:]+r[1:a+1]]
                require(all(len(x) >= 4 for x in parts),'Degenerate cycle')
                pending.extend(reversed(parts));split = True;break
            seen[key] = i
        if not split:
            g = Polygon(r);require(g.is_valid and g.area > 0,'Non-simple/nonpositive cycle: '+explain_validity(g));loops.append(r)
    require(directed_edges([ring]) == directed_edges(loops),'Changed directed source segments')
    return loops


def assemble(loops):
    shells = [Polygon(r) for r in loops if not LinearRing(r).is_ccw]
    holes = [Polygon(r) for r in loops if LinearRing(r).is_ccw]
    require(bool(shells),'Missing clockwise shell')
    assigned = [[] for _ in shells]
    for h in holes:
        owners = [i for i,s in enumerate(shells) if s.covers(h)]
        require(len(owners) == 1,'Ambiguous/uncontained hole')
        assigned[owners[0]].append(list(h.exterior.coords))
    g = MultiPolygon([Polygon(s.exterior.coords,h) for s,h in zip(shells,assigned)])
    require(g.is_valid and not g.is_empty,'Invalid assembled topology: '+explain_validity(g))
    output = [list(p.exterior.coords) for p in g.geoms]+[list(h.coords) for p in g.geoms for h in p.interiors]
    require(directed_edges(loops) == directed_edges(output),'Assembly changed source segments')
    return g


def build():
    inputs,evidence,payloads = {},{},{}
    def dependency(path,expected=None):
        data = (ROOT/path).read_bytes();require(expected is None or digest(data) == expected,'Changed dependency: '+path)
        inputs[path] = digest(data);return data
    prior = json.loads(dependency('research/osborn-wetlands/report.json',PRIOR))
    for path in ['scripts/investigate_osborn_wetlands.py','scripts/prepare_source_staging.py','scripts/collect_document_evidence.py','research/wetlands-availability/probes.json']:
        dependency(path)
    review = json.loads(dependency('research/wetlands-availability/review.json'))
    old = prior['evidence']['coverage/mapping-status-features']
    original = dependency('research/osborn-wetlands/'+old['response_path'],old['sha256'])
    image_ref = prior['evidence']['coverage/image-year-features']
    footprints = json.loads(dependency('research/osborn-wetlands/'+image_ref['response_path'],image_ref['sha256']))
    jurisdiction = json.loads(dependency('research/osborn-fema/runs/identity/osborn-jurisdiction.response','813824533f6c03c71fb8024431e0bd9f86e10b46c8e9ba12eb9c2ddf4d13696a'))
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            require(Path(r['response_file']).name == r['response_file'],'Unsafe response path')
            path = log.parent/r['response_file'];data = path.read_bytes()
            require(r['http_status'] == 200 and digest(data) == r['sha256'] and len(data) == r['bytes'],'Failed/changed capture')
            evidence[log.parent.name+'/'+r['id']] = dict(r,response_path=path.relative_to(BASE).as_posix())
            require(r['id'] not in payloads,'Duplicate probe');payloads[r['id']] = data
    def parsed(name):
        d = json.loads(payloads[name]);require('error' not in d and not d.get('exceededTransferLimit'),'Failed/truncated JSON');return d
    require(payloads['native-status'] == original,'Native source changed; review a new version')
    native = parsed('native-status');export = parsed('geojson-status')
    require(native['spatialReference']['latestWkid'] == 3857 and len(native['features']) == 1,'Unexpected native CRS/count')
    nf = native['features'][0];require(nf['attributes']['OBJECTID'] == 3 and nf['attributes']['STATUS'] == 'Digital','Wrong source identity')
    require(export.get('crs') == {'type':'name','properties':{'name':'EPSG:3857'}} and len(export['features']) == 1,'Unexpected export CRS/count')
    ef = export['features'][0];require(ef['properties'] == nf['attributes'] and ef['geometry']['type'] == 'MultiPolygon','Changed exported attributes/type')
    exported = shape(ef['geometry']);require(not exported.is_valid,'Export no longer has the reviewed defect')
    rings = nf['geometry']['rings'];export_rings = [r for p in ef['geometry']['coordinates'] for r in p]
    # GeoJSON may reverse orientation; undirected multiplicities still must match.
    def undirected(rs):return Counter(tuple(sorted((tuple(a),tuple(b)))) for r in rs for a,b in zip(r,r[1:]))
    require(undirected(rings) == undirected(export_rings),'Export boundary differs')
    loops,details,touches = [],[],[]
    geographic = pyproj.Transformer.from_crs(3857,4326,always_xy=True)
    for i,r in enumerate(rings):
        result = split_touches(r);loops.extend(result)
        if len(result) > 1:
            repeated = [list(p) for p,count in Counter(map(tuple,r[:-1])).items() if count == 2]
            touches.extend(repeated)
            details.append({'ring_index':i,'original_coordinates':len(r),'original_validity':explain_validity(Polygon(r)),'repeated_vertices_epsg3857':repeated,'repeated_vertices_epsg4326':[list(geographic.transform(*p)) for p in repeated],'cycles':[{'coordinates':len(x),'counterclockwise':LinearRing(x).is_ccw,'valid':Polygon(x).is_valid} for x in result]})
    candidate = assemble(loops)
    require(directed_edges(rings) == directed_edges([list(p.exterior.coords) for p in candidate.geoms]+[list(h.coords) for p in candidate.geoms for h in p.interiors]),'Candidate changed directed segments')
    jf = jurisdiction['features'][0];require(jurisdiction['spatialReference']['wkid'] == 4269 and jf['attributes']['CID'] == '230595' and len(jf['geometry']['rings']) == 1,'Wrong scope')
    project = pyproj.Transformer.from_crs(4269,3857,always_xy=True);scope = transform(project.transform,Polygon(jf['geometry']['rings'][0]));require(scope.is_valid,'Invalid scope')
    fp = []
    require(footprints['spatialReference']['latestWkid'] == 3857,'Changed footprint CRS')
    for f in footprints['features']:
        g,hold = decode(f['geometry']['rings']);require(hold is None,'Invalid source footprint');fp.append(g)
    coverage = {'scope':'Exact prior FEMA CID 230595 study boundary; not legal/surveyed parcel boundary','candidate_covers_scope':candidate.covers(scope),'candidate_uncovered_coordinate_area':scope.difference(candidate).area,'image_source_footprints_cover_scope':unary_union(fp).covers(scope),'all_11_touch_vertices_outside_scope':all(not scope.covers(Point(p)) for p in touches),'transform':project.get_last_used_operation().definition,'transform_reported_accuracy_m':project.get_last_used_operation().accuracy,'limit':'EPSG:3857 coordinate-space coverage diagnostics, not ground area. Availability is not wetland completeness, currency or legal applicability.'}
    pix = fitz.Pixmap(payloads['osborn-status-map']);require(pix.width == 800 and pix.height == 800 and pix.n == 4,'Unexpected map image')
    pixels = pix.samples
    colors = Counter(tuple(pixels[i:i+4]) for i in range(0,len(pixels),4))
    renderer = parsed('status-layer')['drawingInfo']['renderer'];digital = [v['symbol']['color'] for v in renderer['uniqueValueInfos'] if v['value'] == 'Digital']
    require(len(digital) == 1 and colors == Counter({tuple(digital[0]):640000}),'Changed map depiction; inspect again')
    data = (canonical({'type':'FeatureCollection','crs':{'type':'name','properties':{'name':'EPSG:3857'}},'features':[{'type':'Feature','properties':{'source_OBJECTID':3,'STATUS':'Digital','evidence_state':'DERIVED','acceptance':'proposed_only'},'geometry':mapping(candidate)}]})+'\n').encode()
    path = BASE/'candidates/status-3.geojson';path.parent.mkdir(exist_ok=True);path.write_bytes(data);dependency(path.relative_to(ROOT).as_posix())
    return {'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),'evidence':evidence,'inputs':inputs,'prior_audit_sha256':PRIOR,'review':review,'ring_details':details,'coverage':coverage,
      'candidate':{'path':path.relative_to(ROOT).as_posix(),'sha256':digest(data),'acceptance':'proposed_only','valid':candidate.is_valid,'polygons':len(candidate.geoms),'holes':sum(len(p.interiors) for p in candidate.geoms),'original_rings':len(rings),'decomposed_cycles':len(loops),'original_coordinates_with_closures':sum(map(len,rings)),'candidate_coordinates_with_closures':sum(map(len,loops)),'directed_boundary_segments_preserved':sum(directed_edges(rings).values()),'coordinate_area_epsg3857':candidate.area,'publisher_shape_area':nf['attributes']['SHAPE_Area'],'publisher_shape_area_difference':candidate.area-nf['attributes']['SHAPE_Area'],'area_limit':'Web Mercator coordinate area only; numerical comparison is not ground acreage.'},
      'checks':{'native_bytes_identical_to_prior_capture':True,'export_attributes_identical':True,'native_export_undirected_edges_identical':True,'every_directed_source_segment_and_multiplicity_preserved':True,'no_snapping_buffer_make_valid_or_coordinate_movement':True,'original_export_validity':explain_validity(exported),'source_map_rgba':list(next(iter(colors))),'source_map_pixels_matching_Digital_renderer':640000},
      'runtime':{'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str,'PyMuPDF':fitz.VersionBind},
      'finding_reviews':[{'finding_id':'TL-F-0028','status':'in_progress','priority':'medium','report_pointer':'/candidate','note':'Five rings contain eleven exact twice-visited vertices. Esri documents vertex touches; native and GeoJSON share unchanged segments, but GeoJSON fails strict validity. Decomposing the existing cycles gives a valid 93-shell/74-hole proposal preserving every directed segment and multiplicity. Original bytes preserved; proposal not accepted. Osborn coverage is corroborated by the service rendering and source-imagery footprints, not field completeness.','next_action':'Review the exact-version proposed decode for acceptance with explicit geometry-version dependencies before enabling any coverage overlay; retain original and future-version holds. No national boundary accuracy or legal wetland determination is implied.'},{'finding_id':'TL-F-0117','status':'in_progress','priority':'medium','report_pointer':'/coverage','note':'TL-F-0028 diagnosis supports an exact-segment availability decode. All repeated vertices are outside Osborn; proposed Digital coverage agrees with service rendering and four imagery-source footprints. Geometry remains a proposal. May 1983 imagery, package/service identity and projection, broader qualification and regulatory applicability remain open.','next_action':'Review availability proposal acceptance before a bounded coverage layer; separately qualify package/service identity, projection and refresh. Preserve old-imagery and field/legal due-diligence limits.'}]}


def prepare_load(report,output,current):
    prepare(BASE,output,BASE/'report.json');manifest = json.loads((output/'manifest.json').read_bytes())
    for path,sha in report['inputs'].items():
        data = (ROOT/path).read_bytes();require(digest(data) == sha and len(data) <= 52428800,'Changed/oversized input');key = 'sha256/'+sha+'.response'
        (output/'objects'/key).write_bytes(data);manifest['objects'][key] = {'sha256':sha,'bytes':len(data)}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows = {r['finding_id']:r for r in json.loads(current.read_bytes())['rows']};sha = digest((BASE/'report.json').read_bytes());sql = (output/'load.sql').read_text().removesuffix('COMMIT;\n')
    for r in report['finding_reviews']:
        fid = r['finding_id'];eid = digest(canonical([fid,sha,'availability']).encode());require(fid in rows,'Missing review token')
        event = {k:v for k,v in r.items() if k != 'report_pointer'};event.update(event_id=eid,actor='TerraLucid NWI availability investigation',evidence_refs=['audit:'+sha+'#'+r['report_pointer'],'audit:'+sha+'#/review'])
        sql += 'INSERT INTO ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details) VALUES ('+','.join([literal(eid),literal(fid),literal(sha),jsql({'report_pointer':r['report_pointer']})])+') ON CONFLICT DO NOTHING;\n'
        sql += 'SELECT ingest.record_finding_event('+jsql(event)+','+literal(rows[fid]['event_id'])+');\n'
    (output/'load.sql').write_text(sql+'COMMIT;\n');print(json.dumps({'audit_sha256':sha,'objects':len(manifest['objects'])}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--current',type=Path);p.add_argument('--verify-download',type=Path);p.add_argument('--prepared',type=Path);a = p.parse_args()
    if a.verify_download:
        if not a.prepared:p.error('--verify-download requires --prepared')
        require('sha256/'+digest((BASE/'report.json').read_bytes())+'.response' in json.loads((a.prepared/'manifest.json').read_bytes())['objects'],'Current report absent from archive');print(verify(a.prepared,a.verify_download))
    else:
        if a.prepare and not a.current:p.error('--prepare requires --current')
        report = build();(BASE/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        if a.prepare:prepare_load(report,a.prepare,a.current)
        else:print(json.dumps({'candidate':report['candidate'],'coverage':report['coverage']},indent=2))
