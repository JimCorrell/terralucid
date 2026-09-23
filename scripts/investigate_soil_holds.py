"""Investigate exact-version soil ring touches; candidates are never activated."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter
import shapely,pyproj
from shapely import wkt,wkb,make_valid
from shapely.ops import transform,unary_union
from shapely.validation import explain_validity
from investigate_wetlands_availability import split_touches,assemble,directed_edges
from collect_county_soils import rows
from verify_county_soil_bundle import verify,file_sha

def candidate_from_source(g):
    parts=list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
    rings=[list(r.coords) for p in parts for r in [p.exterior,*p.interiors]]
    loops=[loop for r in rings for loop in split_touches(r)]
    candidate=assemble(loops)
    out_rings=[list(r.coords) for p in candidate.geoms for r in [p.exterior,*p.interiors]]
    if directed_edges(rings)!=directed_edges(out_rings):raise ValueError('Changed directed source edges')
    if not candidate.equals(make_valid(g)):raise ValueError('Independent make-valid diagnostic differs')
    return candidate,{'source_rings':len(rings),'candidate_rings':len(out_rings),
        'twice_visited_vertices':sum(sum(v==2 for v in Counter(map(tuple,r[:-1])).values()) for r in rings),
        'directed_edges_preserved':sum(directed_edges(rings).values()),'coordinate_area_delta':candidate.area-g.area}

def vertex_difference(a,b):
    ac=shapely.get_coordinates(a);bc=shapely.get_coordinates(b)
    if ac.shape!=bc.shape:raise ValueError('Native WKB vertex count differs')
    return float(abs(ac-bc).max())

def verify_controls(controls,evidence):
    from collect_soil_hold_evidence import containment_query
    request=json.loads((evidence/'native-containment-request.json').read_bytes())
    response=evidence/'native-containment.response'
    if file_sha(response)!=request['sha256']:raise ValueError('Containment response changed')
    if request['payload']!={'query':containment_query(controls),'format':'JSON+COLUMNNAME'}:raise ValueError('Containment controls changed')
    result=rows(json.loads(response.read_bytes()))
    if len(result)!=len(controls):raise ValueError('Missing containment results')
    by_id={int(r['control_id']):r for r in result}
    if set(by_id)!=set(range(len(controls))):raise ValueError('Duplicate or unexpected control IDs')
    for i,c in enumerate(controls):
        r=by_id[i]
        if str(r['mupolygonkey'])!=c['mupolygonkey'] or int(r['contains_point'])!=c['expected']:raise ValueError('Native containment differs')
    return {'request':request,'controls':len(controls),'all_match':True,'interiors':sum(c['expected']==1 for c in controls),'holes':sum(c['expected']==0 for c in controls)}

def run(bundle,county_report,evidence,out):
    verified=verify(bundle);out.mkdir(parents=True,exist_ok=False)
    b=json.loads(county_report.read_bytes())['boundary'];boundary=wkb.loads(b['wkb_hex'],hex=True)
    if hashlib.sha256(boundary.wkb).hexdigest()!=b['sha256']:raise ValueError('County boundary differs')
    source_report=json.loads((bundle/'report.json').read_bytes())
    if b['sha256']!=source_report['boundary_sha256']:raise ValueError('Bundle boundary differs')
    request=json.loads((evidence/'live-representations-request.json').read_bytes())
    if file_sha(evidence/'live-representations.response')!=request['sha256']:raise ValueError('Live response changed')
    live={r['mupolygonkey']:r for r in rows(json.loads((evidence/'live-representations.response').read_bytes()))}
    project=pyproj.Transformer.from_crs(4326,26919,always_xy=True)
    back=pyproj.Transformer.from_crs(26919,4326,always_xy=True)
    base=[];candidates=[];summaries=[];mu={};legends={}
    controls=[]
    for line in (bundle/'records.jsonl').open():
        r=json.loads(line)
        if r['kind']=='legend':legends[r['source_key']]=r['raw'];continue
        if r['kind']=='mapunit':mu[r['source_key']]=r['raw'];continue
        if r['kind']!='mupolygon':continue
        if not r['hold']:
            if r['scope_relation']=='interior':base.append(transform(project.transform,wkb.loads(r['geometry_wkb'],hex=True)))
            continue
        key=r['source_key'];native=live[key];g=wkt.loads(r['raw']['source_wkt'])
        if native['source_wkt']!=r['raw']['source_wkt'] or native['mukey']!=r['raw']['mukey']:raise ValueError('Held source version changed')
        candidate,detail=candidate_from_source(g)
        # WKB is an independent precision/representation check, not a replacement.
        binary=wkb.loads(native['source_wkb'],hex=True);binary_candidate,_=candidate_from_source(binary)
        wm=wkt.loads(native['wm_wkt']);wm_candidate,_=candidate_from_source(wm)
        projected=transform(project.transform,candidate)
        if not projected.is_valid:raise ValueError('Candidate invalid after projection')
        candidates.append(projected)
        data=candidate.wkb;path=out/(key+'.candidate.wkb');path.write_bytes(data)
        # Native SQL containment will independently test one interior and each hole.
        for p in candidate.geoms:
            point=p.representative_point();controls.append({'mupolygonkey':key,'kind':'interior','x':point.x,'y':point.y,'expected':1})
            for hole in p.interiors:
                point=shapely.geometry.Polygon(hole).representative_point();controls.append({'mupolygonkey':key,'kind':'hole','x':point.x,'y':point.y,'expected':0})
        unit=mu[r['raw']['mukey']]
        summaries.append({'mupolygonkey':key,'mukey':r['raw']['mukey'],'areasymbol':legends[unit['lkey']]['areasymbol'],
          'mapunit_symbol':unit['musym'],'mapunit_name':unit['muname'],'source_response_sha256':r['provenance']['response_sha256'],
          'source_wkt_sha256':hashlib.sha256(r['raw']['source_wkt'].encode()).hexdigest(),'candidate_sha256':hashlib.sha256(data).hexdigest(),
          'acceptance':'proposed_only','validity':explain_validity(g),'native_sql_valid':native['native_valid'],
          'native_area_square_degrees':float(native['native_coordinate_area']),
          'candidate_native_area_difference_square_degrees':candidate.area-float(native['native_coordinate_area']),
          'wkb_exactly_matches_wkt_coordinates':binary.equals_exact(g,0),
          'wkb_wkt_max_vertex_difference_degrees':vertex_difference(g,binary),
          'wkb_candidate_matches_wkt_candidate':binary_candidate.equals(candidate),
          'wm_original_valid':wm.is_valid,'wm_candidate_valid':wm_candidate.is_valid,
          'wm_candidate_holes':sum(len(p.interiors) for p in wm_candidate.geoms),
          'candidate_holes':sum(len(p.interiors) for p in candidate.geoms),
          'candidate_county_area_m2':projected.intersection(boundary).area,**detail})
    if {r['mupolygonkey'] for r in summaries}!={r['mupolygonkey'] for r in source_report['geometry_holds']}:raise ValueError('Held membership changed')
    (out/'containment-controls.json').write_text(json.dumps(controls,indent=2)+'\n')
    containment=verify_controls(controls,evidence)
    print('Computing union and residual gap',flush=True)
    original_gap=boundary.difference(unary_union(base));combined=unary_union(candidates)
    residual=original_gap.difference(combined);accounted=original_gap.intersection(combined)
    (out/'original-gap.wkb').write_bytes(original_gap.wkb);(out/'residual-gap.wkb').write_bytes(residual.wkb)
    def polygons(g):return [g] if g.geom_type=='Polygon' else [p for part in getattr(g,'geoms',[]) for p in polygons(part)]
    pieces=sorted(polygons(residual),key=lambda p:p.area,reverse=True)
    for row,g in zip(summaries,candidates):row['original_gap_intersection_m2']=g.intersection(original_gap).area
    report={'evidence_state':'DERIVED','method':'scripts/investigate_soil_holds.py','method_sha256':file_sha(Path(__file__)),
      'decode_method_sha256':file_sha(Path(__file__).with_name('investigate_wetlands_availability.py')),
      'bundle_report_sha256':verified['report_sha256'],'bundle_records_sha256':verified['records_sha256'],'boundary_sha256':b['sha256'],
      'runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__},
      'live_evidence':request,'native_containment':containment,'candidates':summaries,
      'coverage':{'original_gap_m2':original_gap.area,'prior_report_gap_m2':source_report['coverage']['uncovered_m2'],
        'candidate_explained_gap_m2':accounted.area,'residual_m2':residual.area,'residual_components':len(pieces),
        'remaining_coverage_state':'full_geometric' if residual.area==0 else 'partial_geometric',
        'largest_residuals':[{'area_m2':p.area,'bounds_26919':p.bounds,'touches_county_boundary':p.intersects(boundary.boundary),
          'representative_point_4326':list(transform(back.transform,p.representative_point()).coords)[0]} for p in pieces[:10]]},
      'limits':['Unaccepted proposals: originals and seven live holds remain unchanged','No snapping, buffering, coordinate movement or new segments in proposed source decode','make_valid used only as an independent diagnostic, never as the candidate constructor','Native WM coordinate representation has publisher-specific projection caveats; not used for metric coverage','Sequential live controls do not certify future source currency','No legal boundary, site suitability or completeness determination']}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['coverage'],indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','county-report','evidence','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.bundle,a.county_report,a.evidence,a.output)
