#!/usr/bin/env python3
"""Validate the bounded capture and prepare one transactional source/finding load."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from audit_maine_coverage import parse_date
from collect_bounded_sources import validate_ids, validate_page
from prepare_source_staging import ROOT, BUCKET, canonical, digest, literal, jsql, prepare

CATALOG = ROOT / 'research/findings/catalog.json'
AUDIT = ROOT / 'research/maine-coverage/report.json'


def identity(*parts):
    return digest(canonical(parts).encode())


def sql_insert(table, columns, expressions):
    return f'INSERT INTO ingest.{table} ({columns}) VALUES (' + ','.join(expressions) + ') ON CONFLICT DO NOTHING;'


def validate_capture(capture):
    batch = json.loads((capture / 'batch.json').read_bytes())
    if batch['collector_sha256'] != digest((ROOT/'scripts/collect_bounded_sources.py').read_bytes()):
        raise ValueError('Collector changed; capture with the recorded collector version')
    observations = {}
    registry_sha = digest((capture/'registry.json').read_bytes())
    for log in (capture/'runs').glob('*/results.json'):
        for record in json.loads(log.read_bytes()):
            if record['id'] in observations or record['status'] != 'JSON_RECEIVED':
                raise ValueError('Duplicate or failed capture observation')
            path=log.parent/record['response_file']
            data=path.read_bytes()
            if digest(data)!=record['sha256'] or len(data)!=record['bytes']:
                raise ValueError('Response checksum mismatch')
            observations[record['id']]={'payload':json.loads(data), 'record':record,
                 'id':digest(canonical([registry_sha,log.parent.relative_to(capture).as_posix(),record]).encode())}
    records=[]
    for source in batch['sources']:
        sid=source['source_id']
        get=lambda suffix:observations[sid+'-'+suffix]['payload']
        start,end=get('metadata-start'),get('metadata-end')
        for key in ['fields','editingInfo','objectIdField','maxRecordCount']:
            if start.get(key)!=end.get(key):raise ValueError('Metadata drift')
        members=set()
        for index,_ in enumerate(source['predicates']):
            count=get(f'count-{index}')['count']
            ids=validate_ids(get(f'ids-{index}'),count,batch['plan']['max_records_per_source'])
            if ids!=validate_ids(get(f'ids-end-{index}'),count,batch['plan']['max_records_per_source']):
                raise ValueError('Source membership drift')
            members.update(ids)
        if sorted(members)!=source['object_ids'] or len(members)>batch['plan']['max_records_per_source']:
            raise ValueError('Combined membership/cap mismatch')
        seen=[]
        for page in source['pages']:
            obs=observations[page['probe_id']]
            features,properties=validate_page(obs['payload'],page['object_ids'],source['geometry'])
            for feature,props in zip(features,properties):
                seen.append(props['OBJECTID'])
                records.append(dict(source_id=sid,object_id=props['OBJECTID'],global_id=props.get('GlobalID'),
                                    raw_feature=feature,properties=props,observation_id=obs['id'],
                                    record_kind='assessment_geometry' if source['geometry'] else 'assessment'))
        if len(seen)!=len(members) or set(seen)!=members:raise ValueError('Missing or duplicate pages')
    return batch,registry_sha,records


def classify(records, audit):
    ref={j['reference']['GEOCODE']:j['reference'] for j in audit['jurisdictions']}
    overlap={j['reference']['GEOCODE'] for j in audit['jurisdictions']
             if j['sources']['ut']['source_feature_count'] and j['sources']['organized']['source_feature_count']}
    key=lambda r:r['properties'].get('GPL' if r['source_id']=='ut-parcels' else 'STATE_ID')
    counts=Counter((r['source_id'],key(r)) for r in records if (key(r) or '').strip())
    assessments=defaultdict(list)
    for r in records:
        if r['source_id']=='organized-assessment' and (key(r) or '').strip():assessments[key(r)].append(r)
    candidates=[]
    for r in records:
        p=r['properties']; code=p.get('GEOCODE'); name=p.get('TOWNNAME',p.get('TOWN'))
        flags=[]
        if not (code or '').strip():flags.append('blank_jurisdiction')
        elif code not in ref:flags.append('unrecognized_jurisdiction')
        elif r['record_kind']=='assessment_geometry' and (name or '').strip().casefold()!=ref[code]['COMMONNAME'].strip().casefold():
            flags.append('code_name_conflict')
        if not (key(r) or '').strip():flags.append('missing_candidate_key')
        elif counts[(r['source_id'],key(r))]>1:flags.append('repeated_candidate_key_in_batch')
        if not (r['global_id'] or '').strip():flags.append('missing_global_id')
        if r['record_kind']=='assessment_geometry':
            raw=p.get('MAPYEAR') if r['source_id']=='ut-parcels' else p.get('FMUPDAT')
            parsed=parse_date(raw)
            if parsed.get('reason')=='missing':flags.append('missing_source_date')
            elif parsed['state']=='UNKNOWN':flags.append('uninterpreted_source_date')
            if code in overlap:flags.append('source_overlap_unresolved')
        else:
            parsed={'raw':p.get('YEAR_CREAT'),'state':'UNKNOWN','precision':None,'value':None,'reason':'field_semantics_unverified'}
            flags.append('assessment_date_semantics')
        if r['source_id']=='organized-parcels':
            matches=assessments.get(key(r),[]) if (key(r) or '').strip() else []
            r['candidate_count']=len(matches)
            if not matches:flags.append('assessment_no_match')
            if len(matches)>1:flags.append('assessment_multiple_candidates')
            for a in matches:
                agrees=bool((code or '').strip()) and code==a['properties'].get('GEOCODE')
                candidates.append((r,a,agrees))
                if not agrees and 'assessment_geocode_disagreement' not in flags:flags.append('assessment_geocode_disagreement')
        r.update(quality_flags=flags,parsed_date=parsed,
                 raw_identifiers={k:p.get(k) for k in ['GEOCODE','TOWNNAME','TOWN','STATE_ID','GPL','TPL','MAP_BK_LOT','PLAN_','LOT'] if k in p})
    return candidates


def prepare_batch(capture,output):
    batch,registry_sha,records=validate_capture(capture)
    audit=json.loads(AUDIT.read_bytes());audit_sha=digest(AUDIT.read_bytes())
    catalog=json.loads(CATALOG.read_bytes())
    method_files=['scripts/prepare_bounded_ingestion.py','scripts/collect_bounded_sources.py',
                  'scripts/audit_maine_coverage.py','scripts/prepare_source_staging.py',
                  'supabase/migrations/20260920030000_bounded_ingestion_findings.sql']
    methods={p:digest((ROOT/p).read_bytes()) for p in method_files}
    manifest_sha=digest((capture/'batch.json').read_bytes())
    batch_id=identity(manifest_sha,registry_sha,audit_sha,digest(CATALOG.read_bytes()),methods)
    for r in records:r['record_id']=identity(batch_id,r['source_id'],r['object_id'])
    candidates=classify(records,audit)
    sql=[sql_insert('load_batch','batch_id,registry_sha256,audit_sha256,manifest_sha256,definition,methods',
                   [literal(batch_id),literal(registry_sha),literal(audit_sha),literal(manifest_sha),jsql(batch),jsql(methods)])]
    for r in records:
        sql.append(sql_insert('source_record','record_id,batch_id,source_id,object_id,global_id,observation_sha256,record_kind,raw_feature,raw_identifiers,parsed_date,quality_flags,geometry_state',
              [literal(r['record_id']),literal(batch_id),literal(r['source_id']),str(r['object_id']),
               literal(r['global_id']) if r['global_id'] else 'NULL',literal(r['observation_id']),literal(r['record_kind']),
               jsql(r['raw_feature']),jsql(r['raw_identifiers']),jsql(r['parsed_date']),
               'ARRAY['+','.join(map(literal,r['quality_flags']))+']::text[]',literal('not_applicable')]))
    for g,a,agrees in candidates:
        sql.append(sql_insert('assessment_candidate','batch_id,geometry_record_id,assessment_record_id,basis,geocode_agrees',
                   [literal(batch_id),literal(g['record_id']),literal(a['record_id']),literal('exact_raw_STATE_ID'),str(agrees).lower()]))
    original_registry=json.loads((ROOT/'research/maine-sources/registry.json').read_bytes())
    original_registry_sha=digest((ROOT/'research/maine-sources/registry.json').read_bytes())
    for f in catalog['findings']:
        fid=f['finding_id']
        sql.append(sql_insert('finding','finding_id,title,description,source_ids,scope,evidence_state',
                   [literal(fid),literal(f['title']),literal(f['description']),
                    'ARRAY['+','.join(map(literal,f['source_ids']))+']::text[]',jsql(f['scope']),literal(f['evidence_state'])]))
        older='registry_source' in f['scope'] or 'registry_sources' in f['scope']
        if older:
            selected=f['scope'].get('registry_sources',[f['scope'].get('registry_source')])
            definition=[s for s in original_registry['sources'] if s['id'] in selected]
            details={'source_definition':definition,'reference':'registry:'+original_registry_sha}
        else:details={'report_pointer':f['scope']['report_pointer'],'reference':'audit:'+audit_sha}
        origin=original_registry_sha if older else audit_sha
        sql.append(sql_insert('finding_occurrence','occurrence_id,finding_id,audit_sha256,registry_sha256,details',
                   [literal(identity(fid,'initial-evidence',origin)),literal(fid),
                    'NULL' if older else literal(audit_sha),literal(original_registry_sha) if older else 'NULL',jsql(details)]))
        # Stable seed event is inserted only once; reruns never reset a later review.
        sql.append(sql_insert('finding_event','event_id,finding_id,status,priority,next_action,actor,note,evidence_refs',
                   [literal(identity(fid,'initial-event')),literal(fid),literal('open'),literal(f['priority']),
                    literal(f['next_action']),literal('TerraLucid ingestion'),literal('Initial follow-up registered from preserved source audit.'),jsql([details['reference']])]))
    mapping={'blank_jurisdiction':6,'unrecognized_jurisdiction':5,'missing_candidate_key':7,
             'repeated_candidate_key_in_batch':8,'missing_global_id':14,'missing_source_date':11,
             'uninterpreted_source_date':12,'source_overlap_unresolved':18,'assessment_date_semantics':19,
             'assessment_no_match':9,'assessment_multiple_candidates':10,'assessment_geocode_disagreement':23}
    occurrences=0
    for r in records:
        for flag in r['quality_flags']:
            if flag=='code_name_conflict':number={'Sweden':2,'Alfred':3}.get(r['properties'].get('TOWN'),4)
            else:number=mapping[flag]
            fid=f'TL-F-{number:04d}'
            sql.append(sql_insert('finding_occurrence','occurrence_id,finding_id,batch_id,record_id,details',
                       [literal(identity(fid,batch_id,r['record_id'],flag)),literal(fid),literal(batch_id),literal(r['record_id']),
                        jsql({'flag':flag,'source_id':r['source_id'],'object_id':r['object_id'],'raw_identifiers':r['raw_identifiers']})]))
            occurrences+=1
    # Geometry is checked by PostGIS at insertion; attach defects without discarding evidence.
    sql.append("INSERT INTO ingest.finding_occurrence (occurrence_id,finding_id,batch_id,record_id,details) "
               "SELECT encode(sha256(convert_to('TL-F-0022:'||record_id,'UTF8')),'hex'),'TL-F-0022',batch_id,record_id,"
               "jsonb_build_object('geometry_state',geometry_state,'reason',geometry_detail) FROM ingest.source_record "
               "WHERE batch_id="+literal(batch_id)+" AND geometry_state IN ('invalid','missing','decode_failed') ON CONFLICT DO NOTHING;")
    summary={'batch_id':batch_id,'manifest_sha256':manifest_sha,'audit_sha256':audit_sha,
             'records':dict(Counter(r['source_id'] for r in records)),
             'assessment_candidate_links':len(candidates),'candidate_counts':dict(Counter(str(r['candidate_count']) for r in records if 'candidate_count' in r)),
             'quality_flags_before_postgis':dict(Counter(flag for r in records for flag in r['quality_flags'])),
             'initial_findings':len(catalog['findings']),'record_occurrences_before_postgis':occurrences,
             'method_checksums':methods}
    prepare(capture,output)
    manifest=json.loads((output/'manifest.json').read_bytes())
    def archive(data):
        digest_=digest(data);key=f'sha256/{digest_}.response'
        (output/'objects'/key).write_bytes(data)
        manifest['objects'][key]={'sha256':digest_,'bytes':len(data)}
    for path in [capture/'batch.json',CATALOG]+[ROOT/p for p in method_files]:archive(path.read_bytes())
    summary_bytes=(json.dumps(summary,indent=2)+'\n').encode();archive(summary_bytes)
    base=(output/'load.sql').read_text()
    if not base.endswith('COMMIT;\n'):raise ValueError('Unexpected base transaction')
    (output/'load.sql').write_text(base[:-len('COMMIT;\n')]+'\n'.join(sql)+'\nCOMMIT;\n')
    manifest['bounded_batch']=summary
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'summary.json').write_bytes(summary_bytes)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    prepare_batch(args.capture,args.output)
