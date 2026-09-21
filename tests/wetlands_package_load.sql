-- Disposable fixture only; all synthetic mutations roll back.
begin;
do $$
declare p ingest.wetlands_package_feature%rowtype; b text; dep text; e jsonb;
begin
 select audit_sha256 into strict b from ingest.wetlands_package_batch;
 select * into p from ingest.wetlands_package_feature limit 1;
 if (select count(*) from ingest.wetlands_package_current where identity_state='INFERRED' and not needs_revisit)<>669
 or (select count(*) from ingest.wetlands_package_feature where extensions.ST_IsValid(geometry) and extensions.ST_SRID(geometry)=5070 and encode(sha256(geometry_blob),'hex')=data->>'geometry_blob_sha256')<>669 then raise exception 'Package initial state differs';end if;
 if has_table_privilege('anon','ingest.wetlands_package_current','SELECT')
 or exists(select 1 from pg_class where oid in('ingest.wetlands_package_feature'::regclass,'ingest.wetlands_package_batch'::regclass) and not relrowsecurity) then raise exception 'Privacy gate failed';end if;
 begin
  update ingest.wetlands_package_feature set input_text=input_text;
  raise exception using message='Mutable history',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
  insert into ingest.wetlands_package_feature(audit_sha256,object_id,service_audit_sha256,service_object_id,input_text)
  values(b,p.object_id,p.service_audit_sha256,p.service_object_id,p.input_text||' ') on conflict do nothing;
  raise exception using message='Changed replay accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
  insert into ingest.wetlands_package_feature(audit_sha256,object_id,service_audit_sha256,service_object_id,input_text)
  values(b,-1,p.service_audit_sha256,p.service_object_id,p.input_text);
  raise exception using message='Unreviewed package row accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
  insert into ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object)
  select repeat('f',64),registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,'sha256/'||repeat('f',64)||'.response' from ingest.audit_result where sha256=b;
  insert into ingest.wetlands_package_batch(audit_sha256,comparison_audit_sha256,service_audit_sha256)
  select repeat('f',64),comparison_audit_sha256,service_audit_sha256 from ingest.wetlands_package_batch where audit_sha256=b;
  set constraints all immediate;
  raise exception using message='Incomplete batch accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 set constraints all deferred;
 select event_id into dep from ingest.finding_current where finding_id='TL-F-0027';
 e:=jsonb_build_object('event_id',repeat('d',64),'finding_id','TL-F-0027','status','in_progress','priority','medium','actor','isolated fixture','note','Reopen','next_action','Review','evidence_refs','[]'::jsonb);
 perform ingest.record_finding_event(e,dep);
 if (select count(*) from ingest.wetlands_package_current where needs_revisit and candidate_service_effective_lookup is null)<>8 then raise exception 'Classification staleness missing';end if;
 select geometry_event_id into dep from ingest.effective_availability_geometry;
 select jsonb_build_object('event_id',repeat('e',64),'correction_id',correction_id,'status','revoked','actor','isolated fixture','note','Withdraw') into e from ingest.effective_availability_geometry;
 perform ingest.record_availability_event(e,dep);
 insert into ingest.wetlands_package_feature(audit_sha256,object_id,service_audit_sha256,service_object_id,input_text)
 select audit_sha256,object_id,service_audit_sha256,service_object_id,input_text from ingest.wetlands_package_feature on conflict do nothing;
 if (select count(*) from ingest.wetlands_package_current where needs_revisit)<>669 then raise exception 'Replay/withdrawal bypassed staleness';end if;
end $$;
rollback;
select 'PASS: package exact blobs, native CRS, inferred identities, privacy, completeness, immutability, replay and review dependencies';
