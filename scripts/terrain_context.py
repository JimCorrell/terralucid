"""Frozen terrain catalog context for discovery; no elevation coverage inference."""
import hashlib
import json
from pathlib import Path
import pyproj
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
CATALOG='research/soils-terrain-readiness/report.json'
SELECTION='research/county-soils-preparation/report.json'
EVIDENCE=['research/terrain-overlap/report.json','research/terrain-slopes/report.json','research/terrain-extremes/report.json']
FILES=[CATALOG,SELECTION]+EVIDENCE


def file_hash(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog_context(aoi,root=ROOT):
    catalog=json.loads((root/CATALOG).read_bytes())
    selection=json.loads((root/SELECTION).read_bytes())
    if file_hash(root/CATALOG)!=selection['terrain']['input_sha256']:
        raise ValueError('Terrain catalog does not match county selection')
    retained=set(selection['terrain']['retained_source_ids'])
    products=catalog['terrain']['products']
    by_id={p['sourceId']:p for p in products}
    if len(by_id)!=len(products) or not retained.issubset(by_id):raise ValueError('Incomplete or duplicate terrain catalog')
    # Broad candidate search only: transformed AOI envelope, densified by PROJ.
    bounds=Transformer.from_crs(26919,4326,always_xy=True).transform_bounds(*aoi.bounds,densify_pts=21,errcheck=True)
    candidates=[]
    for source_id in sorted(retained):
        p=by_id[source_id];b=p['boundingBox']
        if b['maxX']<bounds[0] or b['minX']>bounds[2] or b['maxY']<bounds[1] or b['minY']>bounds[3]:continue
        candidates.append({k:p.get(k) for k in ['sourceId','title','publicationDate','lastUpdated','sizeInBytes','boundingBox','metaUrl','downloadURL']})
    return {'status':'review_required' if candidates else 'missing','evidence_state':'DERIVED',
        'blocks_general_discovery':False,'catalog_candidates':candidates,
        'candidate_search_bounds_epsg4326':list(bounds),
        'candidate_basis':'Intersection of frozen catalog rectangles with AOI envelope transformed from EPSG26919 to EPSG4326 using 21-point edge densification; approximate discovery candidates only, including touches.',
        'source_versions':{p:file_hash(root/p) for p in FILES},
        'elevation_availability':'UNKNOWN; requires bounded valid-data retrieval for this AOI',
        'slope_result':None,'preferred_source':None,
        'reasons':['catalog_rectangles_are_not_valid_elevation_coverage','publication_dates_are_not_acquisition_dates',
                   'no_source_preference_or_height_correction_accepted','pilot_diagnostics_not_extrapolated_to_this_aoi'],
        'tracked_uncertainty':{'finding_id':'TL-F-0104','applicability':'UNASSESSED; pilot evidence is not parcel-specific',
            'investigation_policy':'Retain source-specific outputs and disagreement/boundary flags; investigate correctness when it could affect a purchase decision.'},
        'next_action':'Retrieve bounded source-specific elevation for a selected AOI when needed; retain NoData and source-boundary support. Site buildability remains purchase-triggered.'}
