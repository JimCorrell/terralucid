-- Disposable fixture only: 669 features and pinned prior finding/availability state.
begin;
do $$
declare b text; w ingest.wetlands_feature%rowtype; event jsonb; dep text;
begin
 select audit_sha256 into strict b from ingest.wetlands_batch;
 perform ingest.assert_wetlands_batch(b);
 if (select count(*) from ingest.wetlands_feature_current where needs_revisit or effective_lookup is null)<>0
 or (select count(*) from ingest.wetlands_feature where not extensions.ST_IsValid(geometry))<>0
 or (select count(*) from ingest.wetlands_feature_current where interpretation='reviewed_reference_match')<>8
 or (select count(*) from ingest.wetlands_feature_current where (prior_qualification_profile->>'intersection_area_m2')::numeric>0)<>499
 then raise exception 'Wetlands initial state differs';end if;
 if exists(select 1 from pg_class where oid in('ingest.wetlands_batch'::regclass,'ingest.wetlands_feature'::regclass) and not relrowsecurity)
 or has_table_privilege('anon','ingest.wetlands_feature_current','SELECT')
 or has_table_privilege('service_role','ingest.wetlands_feature','INSERT') then raise exception 'Privacy gate failed';end if;
 select * into w from ingest.wetlands_feature limit 1;
 begin
  insert into ingest.wetlands_feature(audit_sha256,object_id,input_text) values(b,w.object_id,w.input_text||' ') on conflict do nothing;
  raise exception using message='Changed replay accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
  insert into ingest.wetlands_feature(audit_sha256,object_id,input_text) values(b,-1,w.input_text);
  raise exception using message='Unknown feature accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
  delete from ingest.wetlands_feature where object_id=w.object_id;
  raise exception using message='Mutable history',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 -- A batch cannot commit with missing features, even when the caller omits assert.
 begin
  insert into ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object)
   select repeat('f',64),registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,'sha256/'||repeat('f',64)||'.response' from ingest.audit_result where sha256=b;
  insert into ingest.wetlands_batch(audit_sha256,source_audit_sha256,classification_audit_sha256,classification_event_id,availability_result_id)
   select repeat('f',64),source_audit_sha256,classification_audit_sha256,classification_event_id,availability_result_id from ingest.wetlands_batch where audit_sha256=b;
  set constraints all immediate;
  raise exception using message='Incomplete batch accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 set constraints all deferred;
 -- Reopening classification holds only the eight reviewed definitions.
 select event_id into dep from ingest.finding_current where finding_id='TL-F-0027';
 event:=jsonb_build_object('event_id',repeat('d',64),'finding_id','TL-F-0027','status','in_progress','priority','medium','actor','isolated test','note','Contradiction fixture','next_action','Review','evidence_refs','[]'::jsonb);
 perform ingest.record_finding_event(event,dep);
 if (select count(*) from ingest.wetlands_feature_current where classification_needs_revisit and effective_lookup is null)<>8
 or (select count(*) from ingest.wetlands_feature_current where not needs_revisit)<>661 then raise exception 'Classification staleness not scoped';end if;
 -- Historical feature replay cannot promote stale interpretation.
 insert into ingest.wetlands_feature(audit_sha256,object_id,input_text) select audit_sha256,object_id,input_text from ingest.wetlands_feature on conflict do nothing;
 if (select count(*) from ingest.wetlands_feature_current where classification_needs_revisit)<>8 then raise exception 'Replay refreshed review';end if;
 select geometry_event_id into dep from ingest.effective_availability_geometry;
 select jsonb_build_object('event_id',repeat('e',64),'correction_id',correction_id,'status','revoked','actor','isolated test','note','Withdrawal fixture') into event from ingest.effective_availability_geometry;
 perform ingest.record_availability_event(event,dep);
 if (select count(*) from ingest.wetlands_feature_current where availability_needs_revisit and needs_revisit)<>669 then raise exception 'Availability withdrawal not propagated';end if;
end $$;
rollback;
select 'PASS: wetlands counts, privacy, immutable/versioned rows, scoped classification hold and availability staleness';
