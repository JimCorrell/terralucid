"""Bounded, read-only soil inventory adapter; never site suitability."""
from decimal import Decimal
import json,hashlib
from pathlib import Path
from shapely import wkb
BATCH='b31e3034caee9f70361bb9c769b936b8709fcab38706f89cdee22c9265aad512'
METADATA='96fe753c78865814aacf39b8d8b6102d0dd69bcf48d1de0968a91e70138b6ed1'
UNITS={'component.comppct':'percent','component.slope':'percent','chorizon.hzdept':'cm','chorizon.hzdepb':'cm','chorizon.hzthk':'cm','chorizon.ksat':'um/s','chorizon.awc':'cm/cm','chorizon.sandtotal':'percent','chorizon.claytotal':'percent'}

def qualify_soils(capture,aoi,coverage):
    request=capture['request'].get('soils');ctx=capture['context'].get('soils');data=capture.get('soils')
    if request is None:return {'status':'missing','evidence_state':'UNKNOWN','inventory_intersections_usable':False,'reasons':['soil_source_versions_not_requested'],'blocks_general_discovery':False}
    if not ctx or not data:raise ValueError('Missing requested soil evidence')
    if ctx['batch']!=request['batch'] or ctx['snapshot']!=request['snapshot'] or ctx['batch']!=BATCH or ctx['metadata_sha256']!=METADATA:raise ValueError('Soil scope/metadata differs')
    metadata_path=Path(__file__).resolve().parents[1]/'research/soil-metadata-qualification/report.json'
    metadata_bytes=metadata_path.read_bytes()
    if hashlib.sha256(metadata_bytes).hexdigest()!=METADATA:raise ValueError('Reviewed soil metadata changed')
    metadata=json.loads(metadata_bytes)
    geometries=[];records=[];interior_keys=set()
    for p in data['polygons']:
        g=wkb.loads(p['geometry_wkb'],hex=True)
        if g.is_empty or not g.is_valid:raise ValueError('Invalid effective soil geometry')
        if not g.intersects(aoi):raise ValueError('Unexpected soil extent')
        relation='interior' if g.intersection(aoi).area>0 else 'touch'
        if relation=='interior':geometries.append(g);interior_keys.add(p['mukey'])
        records.append({k:v for k,v in p.items() if k!='geometry_wkb'}|{'aoi_relation':relation})
    by_kind={k:{} for k in ['legend','mapunit','component','chorizon']}
    for row in data['tables']:
        kind=row['kind'];key=row['source_key']
        if key in by_kind[kind]:raise ValueError('Duplicate soil table identity')
        by_kind[kind][key]=row
    reasons=[];missing=[];mixtures=[];profiles=[]
    for mukey in sorted(interior_keys):
        unit=by_kind['mapunit'].get(mukey)
        if not unit:missing.append('mapunit:'+mukey);continue
        legend=by_kind['legend'].get(unit['raw']['lkey'])
        if not legend:missing.append('legend:'+unit['raw']['lkey'])
        components=[r for r in by_kind['component'].values() if r['raw']['mukey']==mukey]
        if not components:missing.append('components:'+mukey)
        percentages=[r['raw'].get('comppct_r') for r in components]
        complete=bool(components) and all(v is not None and str(v).strip() for v in percentages)
        total=sum(Decimal(str(v)) for v in percentages) if complete else None
        mixtures.append({'mukey':mukey,'component_count':len(components),'listed_percent_total':str(total) if total is not None else None,
          'unlisted_percent':str(100-total) if total is not None and total<=100 else None,
          'percentage_state':'unknown' if total is None else 'under_100' if total<100 else 'over_100' if total>100 else 'sums_to_100',
          'normalized':False,'component_locations':'UNKNOWN'})
        for component in components:
            hs=[h for h in by_kind['chorizon'].values() if h['raw']['cokey']==component['source_key']]
            profiles.append({'cokey':component['source_key'],'horizon_count':len(hs),'horizon_state':'records_present' if hs else 'absent_miscellaneous_area' if component['raw'].get('compkind')=='Miscellaneous area' else 'absent_requires_review'})
    cov=coverage(geometries,aoi)
    if not ctx['source_exists']:reasons.append('soil_batch_missing')
    if not ctx['snapshot_current']:reasons.append('soil_geometry_snapshot_stale')
    if not capture['context']['snapshot_current']:reasons.append('county_geometry_snapshot_stale')
    if not capture['aoi_within_county'] or not data['aoi_within_study']:reasons.append('aoi_outside_qualified_scope')
    if data['held_keys']:reasons.append('soil_geometry_holds_require_review')
    if missing:reasons.append('missing_required_soil_links')
    if cov['state']!='full_geometric':reasons.append('incomplete_soil_geometric_coverage')
    usable=not reasons and bool(interior_keys)
    reasons+=['component_mixtures_not_site_locations','field_observation_age_unknown','vt_septic_interpretation_excluded','site_suitability_not_established']
    if any(m['percentage_state']!='sums_to_100' for m in mixtures):reasons.append('component_percentages_not_complete_distribution')
    if any(p['horizon_state']!='records_present' for p in profiles):reasons.append('some_components_have_no_horizons')
    tables=[]
    for row in data['tables']:
        raw=row['raw'];fields=[f for f,v in raw.items() if v is None or (isinstance(v,str) and not v.strip())]
        tables.append(row|{'missing_fields':fields,'excluded_interpretations':['vtsepticsyscl'] if row['kind']=='mapunit' else []})
    return {'status':'stale' if not ctx['snapshot_current'] else 'review_required' if records or data['held_keys'] else 'missing',
      'evidence_state':'DERIVED','inventory_intersections_usable':usable,'blocks_general_discovery':False,'legal_or_site_suitability':'UNKNOWN',
      'coverage':cov,'dependencies':ctx,'reasons':reasons,'held_keys':data['held_keys'],'missing_links':missing,'records':records,
      'survey_metadata':[s for s in metadata['surveys'] if s['areasymbol'] in {r['raw']['areasymbol'] for r in by_kind['legend'].values()}],
      'tables':tables,'component_mixtures':mixtures,'horizon_profiles':profiles,'units':UNITS,
      'date_policy':'saverest is version established; FGDC dates are publication-related; no uniform field age',
      'range_policy':'_l/_r/_h are low/representative/high, not confidence intervals; preserve nulls',
      'finding_candidates':[f['id'] for f in capture.get('findings',[]) if f['id']=='TL-F-0113']}
