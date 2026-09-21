-- Disposable PostGIS database only. Synthetic mutations roll back; never run live.
begin;
do $$
declare c text; initial text; e jsonb; v ingest.availability_coverage%rowtype; g ingest.availability_geometry%rowtype;
begin
 select * into strict g from ingest.availability_geometry; c:=g.correction_id;
 select geometry_event_id into strict initial from ingest.effective_availability_geometry;
 select * into strict v from ingest.availability_coverage;
 if (select count(*) from ingest.availability_geometry_event)<>1
 or not (select result->>'digital_coverage'='true' and not needs_revisit from ingest.availability_coverage_latest)
 or (select geometry_hold from ingest.effective_availability_geometry)
 or not extensions.ST_IsValid(g.geometry) or extensions.ST_NumGeometries(g.geometry)<>93
 or v.result->>'legal_applicability'<>'UNKNOWN' or v.result->>'wetland_completeness'<>'UNKNOWN' then raise exception 'Initial state differs';end if;
 if exists(select 1 from pg_class where oid in('ingest.availability_geometry'::regclass,'ingest.availability_geometry_event'::regclass,'ingest.availability_coverage'::regclass) and not relrowsecurity)
 or has_table_privilege('anon','ingest.availability_coverage_latest','SELECT')
 or has_function_privilege('authenticated','ingest.record_availability_event(jsonb,text)','EXECUTE') then raise exception 'Privacy gate failed';end if;
 begin
  update ingest.availability_geometry set evidence_state='DERIVED';
  raise exception using message='Mutable geometry',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
  delete from ingest.availability_coverage;
  raise exception using message='Mutable coverage',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
  insert into ingest.availability_geometry(correction_id,source_audit_sha256,proposal_audit_sha256,source_payload_sha256,candidate_sha256,candidate_text,evidence_state,limits)
  values(repeat('a',64),g.source_audit_sha256,g.proposal_audit_sha256,g.source_payload_sha256,g.candidate_sha256,g.candidate_text||' ',g.evidence_state,g.limits);
  raise exception using message='Altered candidate accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
  insert into ingest.availability_coverage(result_id,audit_sha256,correction_id,geometry_event_id,subject_audit_sha256,subject_payload_sha256,subject_response_text,method_sha256,result)
  values(repeat('a',64),v.audit_sha256,c,initial,v.subject_audit_sha256,v.subject_payload_sha256,v.subject_response_text||' ',v.method_sha256,'{}');
  raise exception using message='Altered study boundary accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 e:=jsonb_build_object('event_id',repeat('b',64),'correction_id',c,'status','revoked','actor','isolated test','note','Withdrawal must invalidate result');
 begin
  perform ingest.record_availability_event(e,null);
  raise exception using message='Stale event accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 perform ingest.record_availability_event(e,initial);
 if not (select geometry_hold and effective_geometry is null from ingest.effective_availability_geometry)
 or not (select needs_revisit from ingest.availability_coverage_latest) then raise exception 'Revocation did not hold/stale';end if;
 begin
  insert into ingest.availability_coverage(result_id,audit_sha256,correction_id,geometry_event_id,subject_audit_sha256,subject_payload_sha256,subject_response_text,method_sha256,result)
  values(repeat('a',64),v.audit_sha256,c,initial,v.subject_audit_sha256,v.subject_payload_sha256,v.subject_response_text,v.method_sha256,'{}');
  raise exception using message='Revoked geometry used for new result',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 -- Exact historical replays remain no-ops, even after withdrawal.
 select to_jsonb(x)-'event_seq'-'created_at' into e from ingest.availability_geometry_event x where event_id=initial;
 perform ingest.record_availability_event(e,null);
 insert into ingest.availability_coverage(result_id,audit_sha256,correction_id,geometry_event_id,subject_audit_sha256,subject_payload_sha256,subject_response_text,method_sha256,result)
 values(v.result_id,v.audit_sha256,c,initial,v.subject_audit_sha256,v.subject_payload_sha256,v.subject_response_text,v.method_sha256,'{}') on conflict do nothing;
 if not (select geometry_hold from ingest.effective_availability_geometry) then raise exception 'Replay reactivated withdrawal';end if;
 begin
  perform ingest.record_availability_event(e||jsonb_build_object('note','Changed replay'),null);
  raise exception using message='Conflicting replay accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 perform ingest.record_availability_event(jsonb_build_object('event_id',repeat('c',64),'correction_id',c,'status','accepted','actor','isolated test','note','New acceptance requires fresh computation'),repeat('b',64));
 if (select geometry_hold from ingest.effective_availability_geometry)
 or not (select needs_revisit from ingest.availability_coverage_latest) then raise exception 'Reacceptance incorrectly refreshed historical result';end if;
 begin
  insert into ingest.availability_coverage(result_id,audit_sha256,correction_id,geometry_event_id,subject_audit_sha256,subject_payload_sha256,subject_response_text,method_sha256,result)
  values(repeat('a',64),v.audit_sha256,c,repeat('c',64),v.subject_audit_sha256,v.subject_payload_sha256,v.subject_response_text,v.method_sha256,'{}');
  raise exception using message='Old audit reused with new event',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
end $$;
rollback;
select 'PASS: exact versions, PostGIS coverage, privacy, immutability, stale tokens, withdrawal, replay and reacceptance';
