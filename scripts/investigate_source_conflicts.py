#!/usr/bin/env python3
"""Reproduce a dated conflict investigation; optionally prepare its private audit load."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil
import tempfile

import pyproj
from pyproj import Transformer
import shapely
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity

from prepare_bounded_ingestion import validate_capture
from prepare_source_staging import ROOT, digest, prepare

BASE = ROOT / 'research/conflict-investigation'
CAPTURES = {'spatial': BASE/'2026-09-20', 'relationships': BASE/'relationships-2026-09-20'}
REFERENCE = ROOT/'research/maine-coverage/report.json'
METHOD = 'scripts/investigate_source_conflicts.py'


def spatial_comparison(geometry, boundaries):
    """Never repair invalid geometry or infer full containment from an interior point."""
    if geometry is None:
        return {'state': 'missing', 'reason': 'No geometry'}
    if geometry.is_empty or not geometry.is_valid or geometry.area <= 0:
        return {'state': 'invalid', 'reason': explain_validity(geometry)}
    point = geometry.representative_point()
    return {'state': 'valid', 'point_codes': sorted(c for c, b in boundaries.items() if b.covers(point)),
            'fully_covered_codes': sorted(c for c, b in boundaries.items() if b.covers(geometry)),
            'area_fraction_by_code': {c: round(geometry.intersection(b).area/geometry.area, 12)
                                     for c, b in sorted(boundaries.items()) if geometry.intersects(b)}}


def assess_candidates(parcels, assessments, arundel):
    by_key, arundel_by_key = defaultdict(list), defaultdict(list)
    for r in assessments:
        key = r['properties'].get('STATE_ID')
        if key and key.strip(): by_key[key].append(r)
    for r in arundel:
        key = r['properties'].get('STATE_ID')
        if key and key.strip(): arundel_by_key[key].append(r)
    rows, groups = [], defaultdict(Counter)
    for r in parcels:
        p = r['properties']; town = p['TOWN']; key = p.get('STATE_ID')
        if town not in ('Alfred', 'Sweden'): continue
        # The complete assessment scope includes every possible exact match for these keys.
        prefix = '31030_' if town == 'Alfred' else '17310_'
        if not key or not key.startswith(prefix): raise ValueError('Key outside complete assessment query scope')
        exact = by_key[key]
        trial = '31020_' + key[len('31030_'):] if town == 'Alfred' else None
        alternative = by_key.get(trial, []) if trial else []
        groups[town]['records'] += 1
        groups[town]['exact_'+('zero' if not exact else 'one' if len(exact)==1 else 'multiple')] += 1
        groups[town]['exact_links'] += len(exact)
        groups[town]['exact_links_different_geocode'] += sum(a['properties'].get('GEOCODE') != p['GEOCODE'] for a in exact)
        groups[town]['keys_shared_with_arundel_geometry_records'] += bool(arundel_by_key[key])
        if trial:
            groups[town]['prefix_trial_'+('zero' if not alternative else 'one' if len(alternative)==1 else 'multiple')] += 1
            groups[town]['prefix_trial_links'] += len(alternative)
            groups[town]['prefix_trial_equal_nonblank_map_lot_links'] += sum(
                bool((p.get('MAP_BK_LOT') or '').strip()) and p['MAP_BK_LOT']==a['properties'].get('MAP_BK_LOT') for a in alternative)
        rows.append({'object_id': r['object_id'], 'town': town, 'raw_state_id': key,
                     'exact_assessment_object_ids': [a['object_id'] for a in exact],
                     'exact_assessment_geocodes': [a['properties'].get('GEOCODE') for a in exact],
                     'arundel_geometry_object_ids_sharing_key': [a['object_id'] for a in arundel_by_key[key]],
                     'prefix_trial_key': trial, 'prefix_trial_assessment_object_ids': [a['object_id'] for a in alternative]})
    for town, summary in groups.items():
        selected = [r for r in rows if r['town']==town]
        summary['distinct_raw_keys'] = len({r['raw_state_id'] for r in selected})
        summary['distinct_exact_assessment_records'] = len({i for r in selected for i in r['exact_assessment_object_ids']})
        summary['distinct_prefix_trial_assessment_records'] = len({i for r in selected for i in r['prefix_trial_assessment_object_ids']})
    return dict(groups), rows


def investigate():
    batches, registries, datasets, evidence, inputs = {}, {}, {}, {}, {}
    sources = {}
    for name, path in CAPTURES.items():
        batch, _, records = validate_capture(path)
        batches[name], datasets[name] = batch, records
        registry = json.loads((path/'registry.json').read_bytes()); registries[name] = registry
        for entry in registry['sources']:
            if entry['id'] not in sources:
                sources[entry['id']] = dict(entry, probe_ids=[])
            sources[entry['id']]['probe_ids'] += entry['probe_ids']
        for log in sorted((path/'runs').glob('*/results.json')):
            for item in json.loads(log.read_bytes()):
                evidence[name+'/'+item['id']] = dict(item, response_path=f"runs/{name}/{item['response_file']}")
        for f in [path/'batch.json', path/'registry.json']:
            inputs[f.relative_to(ROOT).as_posix()] = digest(f.read_bytes())
    inputs[REFERENCE.relative_to(ROOT).as_posix()] = digest(REFERENCE.read_bytes())
    for dependency in ['scripts/prepare_bounded_ingestion.py', 'scripts/collect_bounded_sources.py',
                       'scripts/prepare_source_staging.py', 'scripts/audit_maine_coverage.py']:
        inputs[dependency] = digest((ROOT/dependency).read_bytes())
    inputs['research/conflict-investigation/requirements.txt'] = digest((BASE/'requirements.txt').read_bytes())
    audit = json.loads(REFERENCE.read_bytes())
    reference = {j['reference']['GEOCODE']: j['reference'] for j in audit['jurisdictions']}
    project = Transformer.from_crs('EPSG:4326', 'EPSG:26919', always_xy=True).transform
    civil = defaultdict(list)
    for r in datasets['spatial']:
        if r['source_id']=='civil-boundaries':
            g = transform(project, shape(r['raw_feature']['geometry']))
            if g.is_empty or not g.is_valid: raise ValueError('Civil reference geometry invalid; do not repair silently')
            civil[r['properties']['GEOCODE']].append(g)
    boundaries = {c: unary_union(gs) for c, gs in civil.items()}
    if any(not b.is_valid for b in boundaries.values()): raise ValueError('Invalid reference union')
    groups, spatial_rows = {}, []
    parcels = [r for r in datasets['spatial'] if r['source_id']=='organized-parcels']
    page_refs = {(s['source_id'], oid): 'spatial/'+page['probe_id']
                 for s in batches['spatial']['sources'] for page in s['pages'] for oid in page['object_ids']}
    for r in parcels:
        p = r['properties']; group_key = p['GEOCODE']+'|'+p['TOWN']
        g = r['raw_feature'].get('geometry')
        comparison = spatial_comparison(transform(project, shape(g)) if g else None, boundaries)
        row = {'object_id': r['object_id'], 'global_id': r['global_id'],
               'raw_geocode': p['GEOCODE'], 'raw_town': p['TOWN'], 'raw_state_id': p.get('STATE_ID'),
               'evidence_ref': page_refs[(r['source_id'],r['object_id'])], **comparison}
        spatial_rows.append(row)
        group = groups.setdefault(group_key, {'raw_geocode':p['GEOCODE'], 'raw_town':p['TOWN'],
            'reference_name_for_raw_code':reference[p['GEOCODE']]['COMMONNAME'],
            'rows':0, 'valid':0, 'invalid_or_missing':[], 'point_code_counts':Counter(),
            'full_coverage_counts':Counter(), 'state_id_prefix_counts':Counter(), 'area_fraction_ranges':{}})
        group['rows']+=1
        group['state_id_prefix_counts'][(p.get('STATE_ID') or '').split('_')[0]]+=1
        if comparison['state']!='valid':group['invalid_or_missing'].append(r['object_id']);continue
        group['valid']+=1
        group['point_code_counts'][','.join(comparison['point_codes']) or 'none_in_selected_reference']+=1
        for c in comparison['fully_covered_codes']:group['full_coverage_counts'][c]+=1
        for c, ratio in comparison['area_fraction_by_code'].items():
            bounds = group['area_fraction_ranges'].setdefault(c,[ratio,ratio])
            bounds[0],bounds[1]=min(bounds[0],ratio),max(bounds[1],ratio)
    expected={(c['source_group']['GEOCODE']+'|'+c['source_group']['TOWN']):c['source_group']['n']
              for c in audit['code_name_conflicts'] if c['source']=='organized'}
    if {k:g['rows'] for k,g in groups.items()} != expected:
        raise ValueError('Conflict group membership/count differs from prior audit; investigate drift')
    assessments=[r for r in datasets['relationships'] if r['source_id']=='organized-assessment']
    arundel=[r for r in datasets['relationships'] if r['source_id']=='organized-parcels']
    matches, candidate_rows=assess_candidates(parcels,assessments,arundel)
    unmatched = {}
    repeated = {}
    for town in ['Alfred','Sweden']:
        town_rows = [r for r in candidate_rows if r['town']==town]
        key_groups = defaultdict(list)
        for r in town_rows:key_groups[r['raw_state_id']].append(r['object_id'])
        repeated[town] = {k:v for k,v in sorted(key_groups.items()) if len(v)>1}
        match_field = 'prefix_trial_assessment_object_ids' if town=='Alfred' else 'exact_assessment_object_ids'
        unmatched[town] = dict(Counter(r['raw_state_id'] for r in town_rows if not r[match_field]))
    report={'evidence_state':'DERIVED','method':METHOD,'method_sha256':digest((ROOT/METHOD).read_bytes()),
        'scope':'All ten code/name conflict groups recorded in the coverage audit; selected complete assessment projections.',
        'limitations':['Civil/assessment GIS is not legal boundary evidence.', 'Point coverage is not full polygon containment.',
                      'Invalid geometries are excluded from spatial adjudication, never repaired.',
                      'Prefix substitution is a diagnostic hypothesis only, not an accepted crosswalk.',
                      'Neither a name nor exact STATE_ID equality establishes parcel identity.'],
        'runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string,
                   'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str,'calculation_crs':'EPSG:26919'},
        'inputs':inputs,'evidence':evidence,'capture_controls':{n:b['controls'] for n,b in batches.items()},
        'counts':{'conflict_geometries':len(parcels),'civil_features':sum(map(len,civil.values())),
                  'civil_codes':len(civil),'assessment_records':len(assessments),'arundel_geometry_identifiers':len(arundel)},
        'spatial_groups':list(groups.values()),'spatial_records':spatial_rows,
        'assessment_summary':matches,'assessment_candidates':candidate_rows,
        'unmatched_raw_keys':unmatched,'repeated_raw_keys':repeated}
    registry={'as_of':max(b['collected_at'] for b in batches.values()),'scope':report['scope'],'sources':list(sources.values())}
    for s in registry['sources']:
        s['probe_ids']=sorted(set(s['probe_ids']))
        s['coverage']='Conflict investigation projection; see report and exact recorded predicates.'
    return report,registry


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prepare',type=Path)
    args=p.parse_args();report,registry=investigate()
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    if args.prepare:
        with tempfile.TemporaryDirectory() as directory:
            audit=Path(directory);(audit/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
            for name,path in CAPTURES.items():
                shutil.copytree(path/'runs/bounded',audit/'runs'/name)
            prepare(audit,args.prepare,args.output)
            manifest=json.loads((args.prepare/'manifest.json').read_bytes())
            for name in report['inputs']:
                data=(ROOT/name).read_bytes();sha=digest(data);key=f'sha256/{sha}.response'
                (args.prepare/'objects'/key).write_bytes(data)
                manifest['objects'][key]={'sha256':sha,'bytes':len(data)}
            (args.prepare/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'counts':report['counts'],'groups':report['spatial_groups'],
                      'assessments':report['assessment_summary']},indent=2))


if __name__=='__main__':main()
