-- Bounded, exact-version zoning geometry interpretation. Originals remain immutable.
create table ingest.zoning_geometry_correction (
 correction_id text primary key check(correction_id ~ '^[0-9a-f]{64}$'),
 source_audit_sha256 text not null,
 object_id bigint not null,
 proposal_audit_sha256 text not null references ingest.audit_result(sha256),
 source_feature_text text not null,
 source_feature_sha256 text not null,
 candidate_text text not null,
 candidate_sha256 text not null,
 geometry extensions.geometry(Polygon,4326) not null,
 evidence_state text not null check(evidence_state='DERIVED'),
 limits jsonb not null,
 created_at timestamptz not null default clock_timestamp(),
 foreign key(source_audit_sha256,object_id) references ingest.zoning_feature(audit_sha256,object_id),
 unique(source_audit_sha256,object_id)
);
create function ingest.validate_zoning_geometry_correction() returns trigger
language plpgsql set search_path=pg_catalog,ingest,extensions as $$
declare r jsonb; original jsonb; candidate jsonb; existing ingest.zoning_geometry_correction%rowtype;
begin
 select * into existing from ingest.zoning_geometry_correction where correction_id=new.correction_id;
 if found then
   if (to_jsonb(existing)-'created_at'-'geometry') is distinct from (to_jsonb(new)-'created_at'-'geometry') then raise exception 'Geometry proposal replay differs'; end if;
   new.geometry:=existing.geometry;return new;
 end if;
 select raw_feature into strict original from ingest.zoning_feature
 where audit_sha256=new.source_audit_sha256 and object_id=new.object_id for update;
 select document into strict r from ingest.audit_result where sha256=new.proposal_audit_sha256;
 candidate:=new.candidate_text::jsonb;
 if new.source_feature_text::jsonb is distinct from original
 or new.source_feature_sha256 is distinct from encode(sha256(convert_to(new.source_feature_text,'UTF8')),'hex')
 or new.candidate_sha256 is distinct from encode(sha256(convert_to(new.candidate_text,'UTF8')),'hex')
 or r#>>'{scope,prior_audit_sha256}' is distinct from new.source_audit_sha256
 or (r#>>'{scope,object_id}')::bigint is distinct from new.object_id
 or r#>>'{source_comparison,original_feature_sha256}' is distinct from new.source_feature_sha256
 or r#>>'{proposal,candidate_sha256}' is distinct from new.candidate_sha256
 or r#>>'{proposal,status}' is distinct from 'proposed_not_accepted'
 or candidate#>>'{properties,source_feature_sha256}' is distinct from new.source_feature_sha256
 or candidate#>>'{properties,prior_audit_sha256}' is distinct from new.source_audit_sha256
 or candidate#>>'{properties,legal_zoning_state}' is distinct from 'UNKNOWN'
 or new.limits is distinct from jsonb_build_object('projection',r#>>'{source_comparison,projection_limit}',
     'legal_zoning_state','UNKNOWN','finding_id','TL-F-0025') then
   raise exception 'Geometry interpretation differs from exact reviewed proposal';
 end if;
 new.geometry:=ST_GeomFromGeoJSON((candidate->'geometry')::text);
 if new.geometry is null or ST_IsEmpty(new.geometry) or not ST_IsValid(new.geometry,0)
 or ST_SRID(new.geometry)<>4326 or ST_NumInteriorRings(new.geometry)<>1
 or not ST_Equals(ST_Boundary(new.geometry),ST_Boundary(ST_GeomFromGeoJSON((original->'geometry')::text))) then
   raise exception 'Reviewed geometry is invalid or changes boundary linework';
 end if;
 return new;
end $$;
create trigger validate_zoning_geometry_correction before insert on ingest.zoning_geometry_correction
for each row execute function ingest.validate_zoning_geometry_correction();
create trigger immutable_zoning_geometry_correction before update or delete on ingest.zoning_geometry_correction
for each row execute function ingest.reject_history_change();

create table ingest.zoning_geometry_event (
 event_id text primary key check(event_id ~ '^[0-9a-f]{64}$'),
 event_seq bigint generated always as identity unique,
 correction_id text not null references ingest.zoning_geometry_correction(correction_id),
 status text not null check(status in ('accepted','revoked')),
 actor text not null check(length(btrim(actor))>0),
 note text not null check(length(btrim(note))>0),
 created_at timestamptz not null default clock_timestamp()
);
create index zoning_geometry_event_latest on ingest.zoning_geometry_event(correction_id,event_seq desc);
create trigger immutable_zoning_geometry_event before update or delete on ingest.zoning_geometry_event
for each row execute function ingest.reject_history_change();
create function ingest.record_zoning_geometry_event(payload jsonb,expected_event_id text) returns void
language plpgsql set search_path=pg_catalog,ingest as $$
declare current_id text; existing jsonb;
begin
 perform 1 from ingest.zoning_geometry_correction where correction_id=payload->>'correction_id' for update;
 if not found then raise exception 'No reviewed geometry proposal';end if;
 select to_jsonb(e)-'event_seq'-'created_at' into existing from ingest.zoning_geometry_event e where event_id=payload->>'event_id';
 if existing is not null then
   if existing is distinct from payload then raise exception 'Geometry event ID reused';end if;
   return;
 end if;
 select event_id into current_id from ingest.zoning_geometry_event where correction_id=payload->>'correction_id' order by event_seq desc limit 1;
 if current_id is distinct from expected_event_id then raise exception 'Geometry review changed';end if;
 insert into ingest.zoning_geometry_event(event_id,correction_id,status,actor,note)
 values(payload->>'event_id',payload->>'correction_id',payload->>'status',payload->>'actor',payload->>'note');
end $$;

create view ingest.corrected_zoning_feature as
select z.*,c.correction_id,c.proposal_audit_sha256,c.source_feature_sha256,c.candidate_sha256,
 coalesce(e.status,case when c.correction_id is null then 'original' else 'proposed' end) as correction_status,
 e.event_id as geometry_event_id,c.evidence_state as correction_evidence_state,c.limits,
 case when e.status='accepted' then c.geometry else z.geometry end as effective_geometry,
 case when e.status='accepted' then c.candidate_text::jsonb->'geometry' else z.raw_feature->'geometry' end as effective_geojson,
 case when e.status='accepted' then 'valid' else z.geometry_state end as effective_geometry_state
from ingest.zoning_feature z
left join ingest.zoning_geometry_correction c on c.source_audit_sha256=z.audit_sha256 and c.object_id=z.object_id
left join lateral(select * from ingest.zoning_geometry_event where correction_id=c.correction_id order by event_seq desc limit 1)e on true;
create function ingest.zoning_geometry_dependencies(source_audit text) returns jsonb
language sql stable set search_path=pg_catalog,ingest as $$
 select coalesce(jsonb_object_agg(correction_id,jsonb_build_object('event_id',geometry_event_id,
 'status',correction_status,'candidate_sha256',candidate_sha256)),'{}'::jsonb)
 from ingest.corrected_zoning_feature where audit_sha256=source_audit and correction_id is not null
$$;

-- Preserve original result rows. Historical Osborn results lack geometry event dependencies.
create or replace view ingest.zoning_screening_current as
select s.*, (case when s.correction_id is not null then
 c.event_id is distinct from s.correction_event_id or c.raw_feature is distinct from s.input->'raw_feature'
 or c.effective_properties is distinct from s.input->'effective_properties' or c.holds is distinct from s.input->'holds'
 else r.raw_feature is distinct from s.input->'raw_feature' or to_jsonb(r.quality_flags) is distinct from s.input->'quality_flags' end)
 or (s.result->>'jurisdiction_code'='09230' and ingest.zoning_geometry_dependencies(s.audit_sha256)<>'{}'::jsonb) as needs_revisit
from ingest.zoning_screening s
left join ingest.corrected_source c on c.correction_id=s.correction_id
left join ingest.source_record r on r.record_id=s.source_record_id;

create table ingest.zoning_screening_revision (
 audit_sha256 text not null references ingest.audit_result(sha256),
 parent_audit_sha256 text not null,
 subject_id text not null,
 revision_seq bigint generated always as identity unique,
 input jsonb not null,
 geometry_dependencies jsonb not null check(jsonb_typeof(geometry_dependencies)='object'),
 result jsonb not null check(result->>'legal_zoning_state' is not distinct from 'UNKNOWN'
   and result->>'boundary_dependency' is not distinct from 'assessment_geometry'
   and jsonb_typeof(result->'intersections') is not distinct from 'array'),
 created_at timestamptz not null default clock_timestamp(),
 primary key(audit_sha256,subject_id),
 foreign key(parent_audit_sha256,subject_id) references ingest.zoning_screening(audit_sha256,subject_id)
);
create function ingest.validate_zoning_revision() returns trigger
language plpgsql set search_path=pg_catalog,ingest as $$
declare p ingest.zoning_screening%rowtype; r ingest.source_record%rowtype; expected jsonb; existing ingest.zoning_screening_revision%rowtype;
begin
 select * into existing from ingest.zoning_screening_revision where audit_sha256=new.audit_sha256 and subject_id=new.subject_id;
 if found then
   if (to_jsonb(existing)-'created_at'-'revision_seq') is distinct from (to_jsonb(new)-'created_at'-'revision_seq') then raise exception 'Screening revision replay differs';end if;
   return new; -- Exact historical replay must not reactivate or recompute an old interpretation.
 end if;
 select * into strict p from ingest.zoning_screening where audit_sha256=new.parent_audit_sha256 and subject_id=new.subject_id;
 -- This bounded consumer covers the existing Osborn UT inputs only.
 if p.source_record_id is null or p.result->>'jurisdiction_code' is distinct from '09230' or p.input is distinct from new.input then
   raise exception 'Revision outside reviewed original Osborn input';end if;
 select * into strict r from ingest.source_record where record_id=p.source_record_id for share;
 if r.raw_feature is distinct from new.input->'raw_feature'
 or to_jsonb(r.quality_flags) is distinct from new.input->'quality_flags'
 or r.batch_id is distinct from new.input->>'source_snapshot_sha256'
 or r.source_id is distinct from new.input->>'source_id' then raise exception 'Screening source changed';end if;
 -- Serialize against both new proposals and acceptance/withdrawal on this source version.
 perform 1 from ingest.zoning_feature where audit_sha256=new.parent_audit_sha256 order by object_id for share;
 perform 1 from ingest.zoning_geometry_correction where source_audit_sha256=new.parent_audit_sha256 order by correction_id for share;
 if new.geometry_dependencies is distinct from ingest.zoning_geometry_dependencies(new.parent_audit_sha256) then
   raise exception 'Geometry dependencies changed; export and recompute';end if;
 select s into expected from ingest.audit_result a,
 lateral jsonb_array_elements(a.document->'screenings')s
 where a.sha256=new.audit_sha256 and s->>'subject_id'=new.subject_id;
 if expected is null or expected->'result' is distinct from new.result
 or expected->'geometry_dependencies' is distinct from new.geometry_dependencies
 or expected->>'parent_audit_sha256' is distinct from new.parent_audit_sha256 then
   raise exception 'Revision differs from archived computation';end if;
 if exists(select 1 from jsonb_array_elements(new.result->'intersections')h where not exists(
   select 1 from ingest.corrected_zoning_feature z where z.audit_sha256=new.parent_audit_sha256
   and z.object_id=(h->>'object_id')::bigint and z.effective_geometry_state='valid')) then
   raise exception 'Revision references invalid effective zoning geometry';end if;
 if new.result->'source_quality_flags' is distinct from p.result->'source_quality_flags'
 or new.result->'source_holds' is distinct from p.result->'source_holds'
 or new.result->'related_finding_ids' is distinct from p.result->'related_finding_ids' then
   raise exception 'Revision lost source findings or holds';end if;
 return new;
end $$;
create trigger validate_zoning_revision before insert on ingest.zoning_screening_revision
for each row execute function ingest.validate_zoning_revision();
create trigger immutable_zoning_revision before update or delete on ingest.zoning_screening_revision
for each row execute function ingest.reject_history_change();
create view ingest.zoning_screening_revision_current as
select v.*,v.geometry_dependencies is distinct from ingest.zoning_geometry_dependencies(v.parent_audit_sha256)
 or r.raw_feature is distinct from v.input->'raw_feature'
 or to_jsonb(r.quality_flags) is distinct from v.input->'quality_flags' as needs_revisit
from ingest.zoning_screening_revision v
join ingest.zoning_screening p on p.audit_sha256=v.parent_audit_sha256 and p.subject_id=v.subject_id
left join ingest.source_record r on r.record_id=p.source_record_id;
-- One default result per original version/subject. Stale latest rows stay visibly stale.
create view ingest.zoning_screening_latest as
select s.audit_sha256 as source_audit_sha256,s.subject_id,
 coalesce(v.audit_sha256,s.audit_sha256) as result_audit_sha256,
 s.source_record_id,s.correction_id,s.correction_event_id,
 coalesce(v.input,s.input) as input,coalesce(v.result,s.result) as result,
 coalesce(v.geometry_dependencies,'{}'::jsonb) as geometry_dependencies,
 case when v.audit_sha256 is null then s.needs_revisit else v.needs_revisit end as needs_revisit
from ingest.zoning_screening_current s left join lateral(
 select * from ingest.zoning_screening_revision_current where parent_audit_sha256=s.audit_sha256
 and subject_id=s.subject_id order by revision_seq desc limit 1)v on true;

alter table ingest.zoning_geometry_correction enable row level security;
alter table ingest.zoning_geometry_event enable row level security;
alter table ingest.zoning_screening_revision enable row level security;
revoke all on ingest.zoning_geometry_correction,ingest.zoning_geometry_event,ingest.zoning_screening_revision,
 ingest.corrected_zoning_feature,ingest.zoning_screening_revision_current,ingest.zoning_screening_latest from public,anon,authenticated,service_role;
revoke all on sequence ingest.zoning_geometry_event_event_seq_seq,ingest.zoning_screening_revision_revision_seq_seq from public,anon,authenticated,service_role;
revoke all on function ingest.validate_zoning_geometry_correction(),ingest.record_zoning_geometry_event(jsonb,text),
 ingest.zoning_geometry_dependencies(text),ingest.validate_zoning_revision() from public,anon,authenticated,service_role;
comment on view ingest.corrected_zoning_feature is 'Default exact-source geometry interpretation. Accepted decoding remains DERIVED; original and unresolved limits are retained. No new snapshot inherits a correction.';
comment on view ingest.zoning_screening_latest is 'Default latest screening per original audit/subject, with explicit dependency staleness. Stale latest results do not silently fall back. No legal zoning certification.';
