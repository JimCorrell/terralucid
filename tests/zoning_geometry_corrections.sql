-- Disposable database only, after historical fixtures, acceptance and revision load.
-- Every synthetic change rolls back. Never execute against the live project.
begin;
do $$
declare actual_area double precision; h jsonb; e jsonb; c text; initial text; v ingest.zoning_screening_revision%rowtype; later text:=repeat('b',64);
begin
 select correction_id,geometry_event_id into strict c,initial from ingest.corrected_zoning_feature where object_id=27232839;
 if (select count(*) from ingest.zoning_geometry_correction)<>1
 or (select count(*) from ingest.zoning_geometry_event)<>1
 or (select count(*) from ingest.zoning_screening_revision)<>153
 or (select count(*) from ingest.zoning_screening_latest)<>2648
 or (select count(*) from ingest.zoning_screening_latest where needs_revisit)<>0
 or (select count(*) from ingest.zoning_screening_current where needs_revisit)<>153
 or (select count(*) from ingest.zoning_screening_revision_current where needs_revisit)<>0 then
 raise exception 'Initial count or dependency invariant failed';end if;
 if not exists(select 1 from ingest.corrected_zoning_feature where correction_id=c and geometry_state='invalid'
 and effective_geometry_state='valid' and correction_evidence_state='DERIVED'
 and extensions.ST_NumInteriorRings(effective_geometry)=1
 and extensions.ST_Equals(extensions.ST_Boundary(geometry),extensions.ST_Boundary(effective_geometry))) then
 raise exception 'Original/accepted geometry invariant failed';end if;
 if (select sum(jsonb_array_length(result->'intersections')) from ingest.zoning_screening_revision)<>652
 or exists(select 1 from ingest.zoning_screening_revision where result->>'legal_zoning_state'<>'UNKNOWN')
 or (select count(*) from ingest.zoning_screening_revision where result->>'status'='source_geometry_unusable')<>1
 or exists(select 1 from ingest.zoning_screening_revision rev join ingest.zoning_screening p
 on p.audit_sha256=rev.parent_audit_sha256 and p.subject_id=rev.subject_id
 where rev.result->'related_finding_ids' is distinct from p.result->'related_finding_ids') then
 raise exception 'Screening or evidence invariant failed';end if;
 select rev.* into v from ingest.zoning_screening_revision rev where exists(
 select 1 from jsonb_array_elements(rev.result->'intersections') x where x->>'object_id'='27232839');
 select x into h from jsonb_array_elements(v.result->'intersections')x where x->>'object_id'='27232839';
 select extensions.ST_Area(extensions.ST_Intersection(
 extensions.ST_Transform(extensions.ST_GeomFromGeoJSON((v.input#>'{raw_feature,geometry}')::text),26919),
 extensions.ST_Transform(effective_geometry,26919))) into actual_area
 from ingest.corrected_zoning_feature where correction_id=c;
 if abs(actual_area-(h->>'area_m2')::double precision)>0.1 then raise exception 'Independent corrected overlap differs';end if;
 update ingest.source_record set quality_flags=array_append(quality_flags,'synthetic_geometry_test') where record_id=v.subject_id;
 if not (select needs_revisit from ingest.zoning_screening_latest where subject_id=v.subject_id) then raise exception 'Source flag change not detected';end if;
 update ingest.source_record set quality_flags=array_remove(quality_flags,'synthetic_geometry_test') where record_id=v.subject_id;
 if (select count(*) from ingest.zoning_screening_latest where input->'holds'<>'[]'::jsonb)<>119 then raise exception 'Existing holds lost';end if;
 if exists(select 1 from pg_class where oid in ('ingest.zoning_geometry_correction'::regclass,
 'ingest.zoning_geometry_event'::regclass,'ingest.zoning_screening_revision'::regclass) and not relrowsecurity)
 or has_table_privilege('anon','ingest.zoning_screening_latest','SELECT')
 or has_function_privilege('authenticated','ingest.record_zoning_geometry_event(jsonb,text)','EXECUTE') then
 raise exception 'Private access invariant failed';end if;
 begin
 update ingest.zoning_geometry_correction set evidence_state='DERIVED' where correction_id=c;
 raise exception using message='Mutable geometry history',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
 delete from ingest.zoning_screening_revision;
 raise exception using message='Mutable screening history',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
 insert into ingest.zoning_geometry_correction(correction_id,source_audit_sha256,object_id,proposal_audit_sha256,
 source_feature_text,source_feature_sha256,candidate_text,candidate_sha256,evidence_state,limits)
 select repeat('c',64),source_audit_sha256,object_id,proposal_audit_sha256,source_feature_text,
 source_feature_sha256,candidate_text||' ',candidate_sha256,evidence_state,limits from ingest.zoning_geometry_correction where correction_id=c;
 raise exception using message='Changed candidate accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 begin
 insert into ingest.zoning_geometry_correction(correction_id,source_audit_sha256,object_id,proposal_audit_sha256,
 source_feature_text,source_feature_sha256,candidate_text,candidate_sha256,evidence_state,limits)
 select repeat('c',64),source_audit_sha256,object_id,proposal_audit_sha256,'{}',
 source_feature_sha256,candidate_text,candidate_sha256,evidence_state,limits from ingest.zoning_geometry_correction where correction_id=c;
 raise exception using message='Changed source accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 e:=jsonb_build_object('event_id',later,'correction_id',c,'status','revoked','actor','isolated test','note','withdrawal test');
 begin
 perform ingest.record_zoning_geometry_event(e,null);
 raise exception using message='Stale review accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 perform ingest.record_zoning_geometry_event(e,initial);
 if not exists(select 1 from ingest.corrected_zoning_feature where correction_id=c and correction_status='revoked'
 and effective_geometry_state='invalid' and effective_geojson=raw_feature->'geometry')
 or (select count(*) from ingest.zoning_screening_revision_current where needs_revisit)<>153
 or (select count(*) from ingest.zoning_screening_latest where needs_revisit)<>153 then
 raise exception 'Withdrawal did not restore original and flag dependents';end if;
 select * into v from ingest.zoning_screening_revision limit 1;
 insert into ingest.zoning_screening_revision(audit_sha256,parent_audit_sha256,subject_id,input,geometry_dependencies,result)
 values(v.audit_sha256,v.parent_audit_sha256,v.subject_id,v.input,v.geometry_dependencies,v.result) on conflict do nothing;
 -- Copy report only to reach a new-row stale-input guard without conflicting on the historical key.
 insert into ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object)
 select repeat('d',64),registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,'sha256/'||repeat('d',64)||'.response'
 from ingest.audit_result where sha256=v.audit_sha256;
 begin
 insert into ingest.zoning_screening_revision(audit_sha256,parent_audit_sha256,subject_id,input,geometry_dependencies,result)
 values(repeat('d',64),v.parent_audit_sha256,v.subject_id,v.input,v.geometry_dependencies,v.result);
 raise exception using message='Stale geometry input accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
 select to_jsonb(t)-'created_at'-'event_seq' into e from ingest.zoning_geometry_event t where event_id=initial;
 perform ingest.record_zoning_geometry_event(e,null);
 if (select correction_status from ingest.corrected_zoning_feature where correction_id=c)<>'revoked' then
 raise exception 'Initial event replay undid withdrawal';end if;
 begin
 perform ingest.record_zoning_geometry_event(e||jsonb_build_object('note','conflicting replay'),null);
 raise exception using message='Conflicting event replay accepted',errcode='XX000';
 exception when sqlstate 'P0001' then null;end;
end $$;
rollback;
