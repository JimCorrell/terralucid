#!/usr/bin/env python3
"""Build proposed, snapshot-specific corrections and a municipal corroboration audit.

No function in this module applies a correction to source or canonical records.
"""
import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import quote,urljoin

import shapely
from shapely.geometry import LinearRing,Polygon,MultiPolygon,shape,mapping
from shapely.ops import transform
from shapely.geometry.polygon import orient
from pyproj import Transformer

from prepare_bounded_ingestion import validate_capture
from prepare_source_staging import ROOT,canonical,digest,prepare

BASE=ROOT/'research/municipal-corroboration'
PRIOR=ROOT/'research/conflict-investigation'
METHOD='scripts/prepare_municipal_crosswalk.py'


class Links(HTMLParser):
    def __init__(self):super().__init__();self.base='';self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='base':self.base=attrs['href']
        if tag=='a' and 'href' in attrs:self.links.append(attrs['href'])


def decode_native_rings(rings):
    """Strict ArcGIS straight-ring interpretation, not geometry repair.

    Clockwise exterior rings; counterclockwise holes must have one containing
    exterior. Reject ambiguous/invalid inputs instead of guessing or fixing them.
    """
    if not rings:raise ValueError('Empty polygon')
    shells=[];holes=[]
    for ring in rings:
        if len(ring)<4 or ring[0]!=ring[-1] or any(len(p)!=2 for p in ring):
            raise ValueError('Only closed 2D straight rings supported')
        polygon=Polygon(ring)
        if not polygon.is_valid or polygon.area<=0:raise ValueError('Invalid ring')
        (holes if LinearRing(ring).is_ccw else shells).append(ring)
    assigned=[[] for _ in shells]
    for hole in holes:
        parents=[i for i,shell in enumerate(shells) if Polygon(shell).contains(Polygon(hole))]
        if len(parents)!=1:raise ValueError('Hole has no unique exterior')
        assigned[parents[0]].append(hole)
    if not shells:raise ValueError('No exterior rings')
    polygons=[Polygon(shell,assigned[i]) for i,shell in enumerate(shells)]
    result=MultiPolygon(polygons) if len(polygons)>1 else polygons[0]
    if not result.is_valid:raise ValueError('Invalid ring assembly; no repair attempted')
    return result


def source_matches(proposal,feature,capture_sha256):
    """A proposal never transfers to another snapshot or changed source feature."""
    return proposal['source_snapshot_sha256']==capture_sha256 and proposal['source_feature_sha256']==digest(canonical(feature).encode())


def propose_record(feature,spatial,candidates,assessment_by_id,scope_sha,assessment_sha,refs):
    p=feature['properties'];town=p['TOWN'];code={'Sweden':'17310','Alfred':'31020'}[town]
    expected_raw={'Sweden':'17290','Alfred':'31030'}[town]
    if spatial['state']!='valid':return None,['invalid_original_geometry']
    if spatial['point_codes']!=[code] or p['GEOCODE']!=expected_raw:
        return None,['jurisdiction_evidence_disagrees']
    raw_key=p.get('STATE_ID') or ''
    prefix='17310_' if town=='Sweden' else '31030_'
    if not raw_key.startswith(prefix):return None,['unexpected_identifier_prefix']
    changes={'GEOCODE':{'from':p['GEOCODE'],'to':code}}
    holds=[];target=None
    if town=='Alfred':
        ids=candidates['prefix_trial_assessment_object_ids']
        if len(ids)!=1:holds.append('identifier_no_unique_assessment_candidate')
        else:
            a=assessment_by_id[ids[0]];ap=a['attributes']
            trial='31020_'+raw_key[len('31030_'):]
            if not (p.get('MAP_BK_LOT') or '').strip() or p['MAP_BK_LOT']!=ap.get('MAP_BK_LOT') or ap.get('GEOCODE')!=code or ap.get('STATE_ID')!=trial:
                holds.append('identifier_candidate_disagrees')
            else:
                changes['STATE_ID']={'from':raw_key,'to':trial}
                target={'object_id':ap['OBJECTID'],'global_id':ap.get('GlobalID'),
                        'state_id':ap['STATE_ID'],'source_snapshot_sha256':assessment_sha,
                        'source_feature_sha256':digest(canonical(a).encode()),'relationship_status':'candidate_only'}
    if town=='Sweden' and not candidates['exact_assessment_object_ids']:holds.append('assessment_unmatched')
    proposal={'status':'proposed','evidence_state':'INFERRED','municipality':town,
              'source_id':'organized-parcels','source_snapshot_sha256':scope_sha,
              'source_feature_sha256':digest(canonical(feature).encode()),
              'object_id':p['OBJECTID'],'global_id':p['GlobalID'],'raw_source_date':p.get('FMUPDAT'),
              'changes':changes,'assessment_candidate':target,'holds':holds,
              'evidence_refs':refs,'municipal_corroboration_scope':'Town/map context and selected labels only; individual geometry not municipally verified.'}
    proposal['proposal_id']=digest(canonical(proposal).encode())
    return proposal,holds


def build():
    evidence={};observations={}
    for log in sorted((BASE/'runs').glob('*/results.json')):
        for r in json.loads(log.read_bytes()):
            data=(log.parent/r['response_file']).read_bytes()
            if digest(data)!=r['sha256'] or len(data)!=r['bytes'] or not 200<=r['http_status']<300:
                raise ValueError('Corrupt or unsuccessful evidence')
            ref=log.parent.name+'/'+r['id']
            evidence[ref]=dict(r,response_path=(log.parent/r['response_file']).relative_to(BASE).as_posix())
            observations[r['id']]=(r,data)
    documents=json.loads((BASE/'documents.json').read_bytes())
    for doc in documents:
        parser=Links();parser.feed(observations[doc['publication_page']][1].decode())
        if doc['observed_href'] not in parser.links or doc['document_base']!=parser.base:
            raise ValueError('PDF publication link not corroborated')
        if quote(urljoin(parser.base,doc['observed_href']),safe=':/?=&%')!=doc['url']:
            raise ValueError('PDF URL differs from the published link')
        if not observations[doc['id']][1].startswith(b'%PDF-'):raise ValueError('Not a PDF')
    for town,page in [('Alfred','alfred-town-maps'),('Sweden','sweden-town-assessing')]:
        parser=Links();parser.feed(observations[page][1].decode())
        if f'https://jeodonnell.com/cama/{town.lower()}/' not in parser.links:
            raise ValueError('Municipal assessor linkage missing')
    review=json.loads((BASE/'document-review.json').read_bytes())
    for row in review['documents']:
        if row['sha256']!=evidence[row['evidence_ref']]['sha256']:raise ValueError('Visual review refers to different PDF')
    prior=json.loads((PRIOR/'report.json').read_bytes());prior_sha=digest((PRIOR/'report.json').read_bytes())
    if digest((ROOT/prior['method']).read_bytes())!=prior['method_sha256']:raise ValueError('Prior report method changed')
    for name,sha in prior['inputs'].items():
        if digest((ROOT/name).read_bytes())!=sha:raise ValueError('Prior report input changed')
    _,_,source_records=validate_capture(PRIOR/'2026-09-20')
    _,_,related=validate_capture(PRIOR/'relationships-2026-09-20')
    scope_sha=digest((PRIOR/'2026-09-20/batch.json').read_bytes())
    assessment_sha=digest((PRIOR/'relationships-2026-09-20/batch.json').read_bytes())
    spatial={r['object_id']:r for r in prior['spatial_records']}
    candidates={r['object_id']:r for r in prior['assessment_candidates']}
    assessment_by_id={r['object_id']:r['raw_feature'] for r in related if r['source_id']=='organized-assessment'}
    features={r['object_id']:r['raw_feature'] for r in source_records if r['source_id']=='organized-parcels'}
    proposals=[];exceptions=[];dates={town:Counter() for town in ['Sweden','Alfred']}
    shared=Counter(i for r in prior['assessment_candidates'] if r['town']=='Sweden' for i in r['exact_assessment_object_ids'])
    for oid,candidate in sorted(candidates.items()):
        feature=features[oid];town=feature['properties']['TOWN'];dates[town][str(feature['properties'].get('FMUPDAT'))]+=1
        refs=['audit:'+prior_sha, 'document-review:'+digest((BASE/'document-review.json').read_bytes()),
              'documents/'+('alfred-town-index' if town=='Alfred' else 'sweden-provider-index')]
        proposal,holds=propose_record(feature,spatial[oid],candidate,assessment_by_id,scope_sha,assessment_sha,refs)
        if town=='Sweden' and any(shared[i]>1 for i in candidate['exact_assessment_object_ids']):holds.append('shared_assessment_candidate')
        if holds:exceptions.append({'object_id':oid,'municipality':town,'raw_state_id':candidate['raw_state_id'],'holds':holds})
        if proposal:
            # Holds are part of the immutable proposal identity.
            proposal['proposal_id']=digest(canonical({k:v for k,v in proposal.items() if k!='proposal_id'}).encode())
            proposals.append(proposal)
    native=json.loads(observations['alfred-native-rings'][1]);geojson=json.loads(observations['alfred-geojson-recheck'][1])
    if native.get('exceededTransferLimit') or geojson.get('exceededTransferLimit') or native.get('spatialReference',{}).get('wkid')!=4326:
        raise ValueError('Native geometry response incomplete or wrong CRS')
    nf={f['attributes']['OBJECTID']:f for f in native['features']};gf={f['properties']['OBJECTID']:f for f in geojson['features']}
    if set(nf)!={439584,439585} or set(gf)!=set(nf):raise ValueError('Geometry comparison membership differs')
    for oid in nf:
        if nf[oid]['attributes']!={k:v for k,v in features[oid]['properties'].items() if k in nf[oid]['attributes']} or gf[oid]['properties']!=nf[oid]['attributes']:
            raise ValueError('Geometry comparison source attributes changed')
        if canonical(gf[oid]['geometry'])!=canonical(features[oid]['geometry']):raise ValueError('GeoJSON geometry changed')
    rings=nf[439584]['geometry']['rings'];decoded=decode_native_rings(rings)
    original=shape(gf[439584]['geometry']);inset=shape(gf[439585]['geometry'])
    if len(rings)!=len(original.geoms) or not all(Polygon(r).equals(part) for r,part in zip(rings,original.geoms)):
        raise ValueError('Native rings and GeoJSON components differ')
    holes=[Polygon(r) for r in rings if LinearRing(r).is_ccw]
    if len(holes)!=1 or not holes[0].equals(inset):raise ValueError('Inset ring no longer matches neighboring feature')
    project=Transformer.from_crs(4326,26919,always_xy=True).transform
    geometry_evidence={'object_id':439584,'status':'proposed_alternate_decode','evidence_state':'DERIVED',
        'original_geojson_valid':original.is_valid,'native_decode_valid':decoded.is_valid,
        'native_ring_orientations':['counterclockwise' if LinearRing(r).is_ccw else 'clockwise' for r in rings],
        'exterior_parts':len(decoded.geoms),'holes':sum(len(g.interiors) for g in decoded.geoms),
        'inset_matches_object_id':439585,'native_decode_overlap_with_inset_m2':round(transform(project,decoded).intersection(transform(project,inset)).area,8),
        'decoded_geojson':mapping(MultiPolygon([orient(part,sign=1.0) for part in decoded.geoms])),
        'output_ring_winding':'GeoJSON exteriors counterclockwise; holes clockwise; ring roles derived from preserved native input','evidence_refs':['geometry/alfred-native-rings','formats/alfred-geojson-recheck','formats/esri-ring-specification','documents/alfred-town-map4'],
        'limit':'Explicit interpretation of native ring semantics, not a surveyed correction. Original GeoJSON remains stored and excluded from this crosswalk.'}
    inputs={name:digest((ROOT/name).read_bytes()) for name in [
        'research/conflict-investigation/report.json','scripts/investigate_source_conflicts.py','research/municipal-corroboration/document-review.json',
        'research/municipal-corroboration/documents.json','research/municipal-corroboration/pages.json',
        'research/municipal-corroboration/geometry-probe.json','research/municipal-corroboration/format-probes.json',
        'research/municipal-corroboration/requirements.txt','scripts/prepare_bounded_ingestion.py',
        'scripts/collect_bounded_sources.py','scripts/prepare_source_staging.py','scripts/collect_document_evidence.py']}
    inputs.update(prior['inputs'])
    crosswalk={'status':'proposed','evidence_state':'INFERRED','scope':'Only exact captured source versions and feature checksums; no automatic application on refresh.',
               'source_snapshot_sha256':scope_sha,'assessment_snapshot_sha256':assessment_sha,
               'source_url':next(s['url'] for s in json.loads((PRIOR/'2026-09-20/batch.json').read_bytes())['sources'] if s['source_id']=='organized-parcels'),
               'proposals':proposals,'exceptions':exceptions}
    report={'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),
            'inputs':inputs,'evidence':evidence,'document_review':review,'source_dates':dates,
            'runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string},
            'crosswalk':crosswalk,'geometry_format_evidence':geometry_evidence,
            'summary':{'jurisdiction_proposals':len(proposals),'identifier_proposals':sum('STATE_ID' in p['changes'] for p in proposals),
                       'by_town':dict(Counter(p['municipality'] for p in proposals)),'exception_records':len(exceptions),
                       'hold_counts':dict(Counter(h for e in exceptions for h in e['holds'])),
                       'municipal_documents':len(documents),'source_observations':len(evidence)},
            'limitations':['Municipal corroboration is town/map context and selected labels, not an individual review of every geometry.',
                           'Proposals do not establish current parcels, title, legal boundaries, or accepted assessment identity.',
                           'Town-linked assessor maps may share source lineage with state GIS and are not independent surveys.',
                           'No source or canonical rows are updated; no finding is automatically resolved.']}
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prepare',type=Path);a=p.parse_args();report=build()
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    if a.prepare:
        prepare(BASE,a.prepare,a.output)
        manifest=json.loads((a.prepare/'manifest.json').read_bytes())
        for name in report['inputs']:
            data=(ROOT/name).read_bytes();sha=digest(data);key=f'sha256/{sha}.response'
            (a.prepare/'objects'/key).write_bytes(data);manifest['objects'][key]={'sha256':sha,'bytes':len(data)}
        (a.prepare/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__':main()
