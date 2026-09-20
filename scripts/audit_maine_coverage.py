#!/usr/bin/env python3
"""Derive a dated coverage/identifier report from archived research responses."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'research/maine-coverage'
STATUS = {'C': 'City', 'T': 'Town', 'P': 'Plantation', 'U': 'Unorganized Township', 'R': 'Reservation'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_date(raw):
    """Retain raw input; never turn a year-only observation into a day."""
    result = {'raw': raw, 'precision': None, 'value': None, 'state': 'UNKNOWN'}
    if raw is None or str(raw).strip() == '':
        return dict(result, reason='missing')
    text = str(raw).strip()
    try:
        if re.fullmatch(r'[1-9][0-9]{3}', text):
            return dict(result, precision='year', value=int(text), state='DERIVED')
        if re.fullmatch(r'[0-9]{8}', text):
            value = datetime.strptime(text, '%Y%m%d').date()
        elif re.fullmatch(r'[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}', text):
            value = datetime.strptime(text, '%m/%d/%Y').date()
        else:
            raise ValueError('Unsupported date format')
        return dict(result, precision='day', value=value.isoformat(), state='DERIVED')
    except ValueError:
        return dict(result, reason='malformed_or_uninterpreted')


def attributes(payload, complete=True):
    if 'error' in payload or 'features' not in payload:
        raise ValueError('Missing successful feature response')
    if complete and payload.get('exceededTransferLimit'):
        raise ValueError('Truncated response cannot support complete aggregate claims')
    return [x['attributes'] for x in payload['features']]


def derive(audit):
    payloads, evidence, selected = {}, {}, {}
    for log in sorted((audit / 'runs').glob('*/results.json')):
        for record in json.loads(log.read_bytes()):
            probe = record['id']
            observation = log.parent.name + '/' + probe
            if observation in evidence:
                raise ValueError(f'Duplicate observation: {observation}')
            data = (log.parent / record['response_file']).read_bytes()
            if sha(data) != record['sha256'] or len(data) != record['bytes']:
                raise ValueError(f'Corrupt response: {probe}')
            evidence[observation] = dict(record, response_path=(log.parent / record['response_file']).relative_to(audit).as_posix())
            if record['status'] == 'JSON_RECEIVED':
                if probe in payloads:
                    raise ValueError(f'Ambiguous successful probe: {probe}')
                selected[probe] = observation
                payloads[probe] = json.loads(data)

    def count(key):
        value = payloads[key]['count']
        if not isinstance(value, int) or value < 0:
            raise ValueError(f'Invalid count: {key}')
        return value

    def rows(key, complete=True):
        return attributes(payloads[key], complete)

    reference = rows('geocodes-records')
    if len(reference) != count('geocodes-count') or len({r['GEOCODE'] for r in reference}) != len(reference):
        raise ValueError('Reference table count/uniqueness failed')
    ref = {r['GEOCODE']: r for r in reference}
    units = {k: v for k, v in ref.items() if v['STATUS'] in STATUS}
    civil = rows('civil-code-types')
    if sum(r['n'] for r in civil) != count('civil-count'):
        raise ValueError('Civil aggregate does not reconcile')
    civil_codes = {r['GEOCODE'] for r in civil}
    coverage, conflicts, unknowns = {}, [], []
    missing_by_code = {}
    for source, namefield in [('ut', 'TOWNNAME'), ('organized', 'TOWN'), ('assessment', None)]:
        groups = rows(source + '-jurisdictions')
        if sum(r['n'] for r in groups) != count(source + '-count'):
            raise ValueError(f'Coverage count mismatch: {source}')
        indexed = defaultdict(list)
        for row in groups:
            code = row['GEOCODE']
            indexed[code].append(row)
            if code not in ref:
                unknowns.append(dict(source=source, source_group=row))
            elif namefield and (row[namefield] or '').strip().casefold() != ref[code]['COMMONNAME'].strip().casefold():
                candidates = [k for k, v in units.items()
                              if v['COMMONNAME'].casefold() == (row[namefield] or '').strip().casefold()
                              and (not row.get('COUNTY') or v['COUNTY'] == row['COUNTY'])]
                conflicts.append(dict(source=source, source_group=row, reference_name=ref[code]['COMMONNAME'],
                                      exact_name_candidate_codes=candidates, resolution='unresolved; source unchanged'))
        coverage[source] = indexed
        missing = rows(source + '-missing-by-jurisdiction')
        if sum(r['n'] for r in missing) != count(source + '-key-null') + count(source + '-key-empty'):
            raise ValueError('Missing-key count mismatch')
        by_code = Counter()
        for r in missing:
            by_code[r['GEOCODE']] += r['n']
        missing_by_code[source] = by_code

    jurisdiction_rows = []
    for code, entry in sorted(ref.items()):
        sources = {}
        for name in coverage:
            groups = coverage[name].get(code, [])
            n = sum(r['n'] for r in groups)
            sources[name] = dict(source_feature_count=n, presence='observed_by_reported_code' if n else 'not_observed',
                                 completeness='UNKNOWN', missing_candidate_key_rows=missing_by_code[name][code],
                                 raw_groups=groups)
        jurisdiction_rows.append(dict(reference=entry, reference_status_label=STATUS.get(entry['STATUS']),
                                      in_status_coded_denominator=code in units,
                                      civil_polygons_observed=code in civil_codes, sources=sources))

    keys = []
    for source, field, prefix in [('ut','TPL','ut-tpl'),('ut','GPL','ut-gpl'),
                                  ('organized','STATE_ID','organized-state-id'),('assessment','STATE_ID','assessment-state-id')]:
        present, distinct = count(prefix+'-present-simple'), count(prefix+'-distinct-simple')
        if not 0 <= distinct <= present <= count(source+'-count'):
            raise ValueError('Inconsistent candidate-key counts')
        keys.append(dict(source=source,field=field,rows=count(source+'-count'),present=present,
                         missing=count(source+'-count')-present,distinct=distinct,
                         excess_rows_over_distinct_keys=present-distinct,
                         method="Server count with IS NOT NULL AND <> ''; distinct under source collation; no client normalization"))
    for source in coverage:
        keys.append(dict(source=source, field='GlobalID', rows=count(source+'-count'),
                         present=count(source+'-globalid-present'), distinct=count(source+'-globalid-distinct'),
                         method='IS NOT NULL; source distinct count. Uniqueness applies to this source snapshot only.'))

    dates = {}
    for source, field in [('organized','FMUPDAT'),('ut','MAPYEAR')]:
        groups = rows(source+'-dates')
        if sum(r['n'] for r in groups) != count(source+'-count'):
            raise ValueError('Date aggregate count mismatch')
        state_counts = Counter()
        for row in groups:
            parsed = parse_date(row[field])
            row['parsed_date'] = parsed
            state_counts[parsed.get('reason', parsed['precision'])] += row['n']
        dates[source] = dict(source_field=field, counts=dict(state_counts), groups=groups)

    samples = [r for i in range(6) for r in rows('organized-join-sample-'+str(i))]
    expected_oids = {r['sample_oid'] for r in rows('organized-sample-oids')}
    if len(samples) != len(expected_oids) or {r['OBJECTID'] for r in samples} != expected_oids:
        raise ValueError('Sample object IDs incomplete or repeated')
    sample_keys = sorted({r['STATE_ID'] for r in samples if r['STATE_ID'] and r['STATE_ID'].strip()})
    join_counts = {}
    for side in ['geometry','assessment']:
        indexed = defaultdict(list)
        for i in range((len(sample_keys)+29)//30):
            for row in rows('join-'+side+'-'+str(i)):
                if row['STATE_ID'] not in sample_keys:
                    raise ValueError('Unexpected join key; inspect source collation')
                indexed[row['STATE_ID']].append(row)
        join_counts[side] = indexed
    matches, patterns = [], Counter()
    for key in sample_keys:
        a = join_counts['geometry'][key]; b = join_counts['assessment'][key]
        na, nb = sum(r['n'] for r in a), sum(r['n'] for r in b)
        if not na:
            raise ValueError('Selected geometry key disappeared')
        pattern = 'unmatched' if nb == 0 else 'one_to_one' if na == nb == 1 else 'one_to_many' if na == 1 else 'many_to_one' if nb == 1 else 'many_to_many'
        patterns[pattern] += 1
        matches.append(dict(state_id=key, geometry_rows=na, assessment_rows=nb, cardinality=pattern,
                            geometry_groups=a, assessment_groups=b,
                            geocodes_agree=bool(b) and {r['GEOCODE'] for r in a} == {r['GEOCODE'] for r in b}))

    controls = {}
    for source in ['ut','organized','assessment','civil','geocodes']:
        before, after = count(source+'-count'), count(source+'-count-end')
        controls[source] = {'start_count': before, 'end_count': after, 'unchanged': before == after}
        if before != after:
            raise ValueError('Source count drift; audit must be repeated or reconciled')
    for source in ['ut','organized','assessment']:
        before = payloads[source+'-metadata'].get('editingInfo')
        after = payloads[source+'-metadata-end'].get('editingInfo')
        controls[source]['editing_info_start'] = before
        controls[source]['editing_info_end'] = after
        if before != after:
            raise ValueError('Source editing metadata changed during audit')
    observed = {source: {code for code in units if code in coverage[source]} for source in coverage}
    by_status = []
    for status, label in STATUS.items():
        members = {k for k,v in units.items() if v['STATUS']==status}
        by_status.append(dict(status=status,label=label,reference_codes=len(members),
                              **{s:len(codes & members) for s,codes in observed.items()}))
    outcome_counts = Counter(r['status'] for r in evidence.values())
    return dict(evidence_state='DERIVED',as_of=max(r['retrieved_at'] for r in evidence.values()),
                method='scripts/audit_maine_coverage.py', method_sha256=sha(Path(__file__).read_bytes()),
                scope='Source presence and identifier audit, not legal jurisdiction certification or parcel completeness.',
                summary=dict(reference_rows=len(ref),status_coded_reference_codes=len(units),
                             excluded_county_island_codes=len(ref)-len(units),civil_polygon_count=count('civil-count'),
                             civil_codes_including_blank=len(civil_codes),source_rows={s:count(s+'-count') for s in coverage},
                             presence_by_status=by_status,
                             parcel_source_overlap_codes=len(observed['ut'] & observed['organized']),
                             parcel_source_union_codes=len(observed['ut'] | observed['organized']),
                             neither_parcel_source_codes=len(set(units)-(observed['ut'] | observed['organized'])),
                             response_outcomes=dict(outcome_counts)),
                controls=controls,jurisdictions=jurisdiction_rows,code_name_conflicts=conflicts,
                conflict_support={name:count(name+'-identifier-prefix') for name in ['sweden','alfred']},
                unrecognized_source_groups=unknowns,key_profiles=keys,date_profiles=dates,
                assessment_year_creat='Retained as source values; interpretation and per-jurisdiction date profile remain unvalidated. Initial grouped response was truncated.',
                join_sample=dict(selection='Minimum geometry OBJECTID per reported code/name/county group; not random.',
                                 source_rows=len(samples),distinct_nonblank_keys=len(sample_keys),
                                 missing_key_sample_rows=sum(not (r['STATE_ID'] or '').strip() for r in samples),
                                 cardinalities=dict(patterns),results=matches),
                excluded_semantic_checks=['assessment-dates: transfer limit',
                                          'organized-duplicate-sample and assessment-duplicate-sample: havingClause ignored'],
                selected_successful_responses=selected,evidence=evidence)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit',type=Path,default=AUDIT)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    report=derive(args.audit)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report['summary'],indent=2))
    print(json.dumps(report['join_sample']['cardinalities'],indent=2))


if __name__=='__main__':
    main()
