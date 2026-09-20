-- LOCAL DISPOSABLE DATABASE ONLY. All synthetic cases roll back.
BEGIN;
DO $$
declare previous text; payload jsonb; failed boolean; before_events bigint;
begin
  if (select count(*) from ingest.source_record)<>2058 or
     (select count(*) from ingest.assessment_candidate)<>737 or
     (select count(*) from ingest.finding)<>40 or
     (select count(*) from ingest.finding_occurrence)<>3353 then
    raise exception 'Fixture or repeat-load counts differ';
  end if;
  if (select count(*) from ingest.source_record where geometry_state='invalid' and geometry_detail is not null)<>3 then
    raise exception 'Invalid source geometry not preserved with explanation';
  end if;
  select event_id into previous from ingest.finding_current where finding_id='TL-F-0002';
  select count(*) into before_events from ingest.finding_event;
  payload=jsonb_build_object('event_id',repeat('a',64),'finding_id','TL-F-0002','status','resolved',
          'priority','high','next_action','Monitor new evidence','actor','Local test',
          'note','Synthetic resolution test only','evidence_refs','[]'::jsonb);
  failed=false;
  begin perform ingest.record_finding_event(payload,previous);
  exception when check_violation then failed=true; end;
  if not failed then raise exception 'Resolution without evidence was accepted'; end if;
  payload=jsonb_set(payload,'{evidence_refs}','["local-test:resolution-evidence"]');
  perform ingest.record_finding_event(payload,previous);
  perform ingest.record_finding_event(payload,previous);
  if (select count(*) from ingest.finding_event)<>before_events+1 then
    raise exception 'Event replay was not idempotent';
  end if;
  failed=false;
  begin perform ingest.record_finding_event(jsonb_set(payload,'{event_id}',to_jsonb(repeat('b',64))),previous);
  exception when raise_exception then
    if SQLERRM not like 'Finding changed%' then raise; end if;
    failed=true;
  end;
  if not failed then raise exception 'Stale review accepted'; end if;
  failed=false;
  begin update ingest.finding_event set note='overwrite' where event_id=repeat('a',64);
  exception when raise_exception then
    if SQLERRM not like 'Append a new finding%' then raise; end if;
    failed=true;
  end;
  if not failed then raise exception 'History overwrite accepted'; end if;
  insert into ingest.finding_occurrence(occurrence_id,finding_id,audit_sha256,details)
  select repeat('c',64),'TL-F-0002',sha256,'{"test":"later occurrence"}'::jsonb from ingest.audit_result limit 1;
  if not (select needs_revisit from ingest.finding_current where finding_id='TL-F-0002') then
    raise exception 'New evidence after resolution was hidden';
  end if;
  payload=jsonb_set(jsonb_set(payload,'{event_id}',to_jsonb(repeat('d',64))),'{status}','"open"');
  perform ingest.record_finding_event(payload,repeat('a',64));
  if (select status<>'open' or needs_revisit from ingest.finding_current where finding_id='TL-F-0002') then
    raise exception 'Explicit reopen failed';
  end if;
end $$;
INSERT INTO ingest.source_record(record_id,batch_id,source_id,object_id,observation_sha256,record_kind,
 raw_feature,raw_identifiers,parsed_date,geometry_state)
SELECT encode(sha256(convert_to(v.kind,'UTF8')),'hex'),r.batch_id,'test_geometry',v.oid,r.observation_sha256,
 'assessment_geometry',v.feature,'{}','{}','valid'
FROM (select * from ingest.source_record limit 1) r
CROSS JOIN (VALUES
 ('missing',900000001,'{"type":"Feature","geometry":null}'::jsonb),
 ('invalid',900000002,'{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[0,0],[1,1],[1,0],[0,1],[0,0]]]}}'::jsonb),
 ('decode_failed',900000003,'{"type":"Feature","geometry":{"type":"Polygon","coordinates":"bad"}}'::jsonb)
) v(kind,oid,feature);
DO $$ begin
 if (select count(distinct geometry_state) from ingest.source_record where source_id='test_geometry'
     and geometry_detail is not null and cardinality(quality_flags)>0)<>3 then
   raise exception 'Geometry defects were dropped or silently repaired';
 end if;
end $$;
ROLLBACK;
