-- Exact reviewed availability interpretation; no new source inherits acceptance.
create table ingest.availability_geometry (
 correction_id text primary key check(correction_id ~ '^[0-9a-f]{64}$'),
 source_audit_sha256 text not null references ingest.audit_result(sha256),
 proposal_audit_sha256 text not null references ingest.audit_result(sha256),
 source_payload_sha256 text not null,
 candidate_sha256 text not null,
 candidate_text text not null,
 geometry extensions.geometry(MultiPolygon,3857) not null,
 evidence_state text not null check(evidence_state='DERIVED'),
 limits jsonb not null,
 created_at timestamptz not null default clock_timestamp(),
 unique(source_audit_sha256,source_payload_sha256)
);
create function ingest.validate_availability_geometry() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare old ingest.availability_geometry%rowtype; p jsonb; c jsonb;
begin
 select * into old from ingest.availability_geometry where correction_id=new.correction_id;
 if found then
  if to_jsonb(old)-'geometry'-'created_at' is distinct from to_jsonb(new)-'geometry'-'created_at' then raise exception 'Proposal replay differs';end if;
  new.geometry:=old.geometry;return new;
 end if;
 -- Bounded authorization to the reviewed proposal, not any self-asserted audit.
 if new.proposal_audit_sha256 is distinct from '73a3f6899afdc374c273a2a69f4ef445926b02b4af6b73351cedfd12a5de7d66'
 or new.source_audit_sha256 is distinct from 'e1449e8384d5d712dfdae9df26814330d1b9f7dc31ae82fc8765bce565b61906'
 or new.source_payload_sha256 is distinct from '434b6becc32ea018436807e4e0868710a86da372ac67524368cc1c464dc8b2b3' then raise exception 'Unreviewed source/proposal version';end if;
 select document into strict p from ingest.audit_result where sha256=new.proposal_audit_sha256;
 if new.candidate_sha256 is distinct from p#>>'{candidate,sha256}'
 or new.candidate_sha256 is distinct from encode(sha256(convert_to(new.candidate_text,'UTF8')),'hex')
 or new.limits is distinct from p->'review'
 or p#>>'{candidate,acceptance}' is distinct from 'proposed_only'
 or p#>>'{checks,every_directed_source_segment_and_multiplicity_preserved}' is distinct from 'true'
 or not exists(select 1 from ingest.source_response s join ingest.audit_result a on s.registry_sha256=a.registry_sha256 where a.sha256=new.source_audit_sha256 and s.payload_sha256=new.source_payload_sha256) then raise exception 'Candidate differs from archived review';end if;
 c:=new.candidate_text::jsonb;
 if c#>>'{crs,properties,name}' is distinct from 'EPSG:3857' or jsonb_array_length(c->'features')<>1
 or c#>>'{features,0,properties,source_OBJECTID}' is distinct from '3' then raise exception 'Candidate CRS/identity differs';end if;
 new.geometry:=ST_SetSRID(ST_GeomFromGeoJSON((c#>'{features,0,geometry}')::text),3857);
 if ST_SRID(new.geometry)<>3857 or not ST_IsValid(new.geometry) or ST_IsEmpty(new.geometry)
 or ST_NumGeometries(new.geometry)<>93
 or (select sum(ST_NumInteriorRings(d.geom)) from ST_Dump(new.geometry)d)<>74 then raise exception 'Candidate validity/topology differs';end if;
 return new;
end $$;
create trigger validate_availability_geometry before insert on ingest.availability_geometry for each row execute function ingest.validate_availability_geometry();
create trigger immutable_availability_geometry before update or delete on ingest.availability_geometry for each row execute function ingest.reject_history_change();

create table ingest.availability_geometry_event (
 event_id text primary key check(event_id ~ '^[0-9a-f]{64}$'),
 event_seq bigint generated always as identity unique,
 correction_id text not null references ingest.availability_geometry(correction_id),
 status text not null check(status in ('accepted','revoked')),
 actor text not null check(length(btrim(actor))>0),
 note text not null check(length(btrim(note))>0),
 created_at timestamptz not null default clock_timestamp()
);
create index availability_event_latest on ingest.availability_geometry_event(correction_id,event_seq desc);
create trigger immutable_availability_event before update or delete on ingest.availability_geometry_event for each row execute function ingest.reject_history_change();
create function ingest.record_availability_event(payload jsonb,expected_event_id text) returns void language plpgsql
set search_path=pg_catalog,ingest as $$
declare current_id text; old jsonb;
begin
 perform 1 from ingest.availability_geometry where correction_id=payload->>'correction_id' for update;
 if not found then raise exception 'Unknown availability proposal';end if;
 select to_jsonb(e)-'event_seq'-'created_at' into old from ingest.availability_geometry_event e where event_id=payload->>'event_id';
 if old is not null then
  if old is distinct from payload then raise exception 'Event ID reused';end if;return;
 end if;
 select event_id into current_id from ingest.availability_geometry_event where correction_id=payload->>'correction_id' order by event_seq desc limit 1;
 if current_id is distinct from expected_event_id then raise exception 'Availability review changed';end if;
 insert into ingest.availability_geometry_event(event_id,correction_id,status,actor,note)
 values(payload->>'event_id',payload->>'correction_id',payload->>'status',payload->>'actor',payload->>'note');
end $$;
create view ingest.effective_availability_geometry as
select g.correction_id,g.source_audit_sha256,g.proposal_audit_sha256,g.source_payload_sha256,g.candidate_sha256,g.evidence_state,g.limits,
 e.event_id as geometry_event_id,coalesce(e.status,'proposed') as correction_status,
 case when e.status='accepted' then g.geometry else null end as effective_geometry,
 e.status is distinct from 'accepted' as geometry_hold
from ingest.availability_geometry g left join lateral(select * from ingest.availability_geometry_event where correction_id=g.correction_id order by event_seq desc limit 1)e on true;

create table ingest.availability_coverage (
 result_id text primary key check(result_id ~ '^[0-9a-f]{64}$'),
 audit_sha256 text not null references ingest.audit_result(sha256),
 correction_id text not null references ingest.availability_geometry(correction_id),
 geometry_event_id text not null references ingest.availability_geometry_event(event_id),
 subject_audit_sha256 text not null references ingest.audit_result(sha256),
 subject_payload_sha256 text not null,
 subject_response_text text not null,
 method_sha256 text not null,
 result jsonb not null,
 result_seq bigint generated always as identity unique,
 created_at timestamptz not null default clock_timestamp()
);
create function ingest.validate_availability_coverage() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare old ingest.availability_coverage%rowtype; g ingest.effective_availability_geometry%rowtype; s jsonb; scope extensions.geometry; audit jsonb;
begin
 select * into old from ingest.availability_coverage where result_id=new.result_id;
 if found then
  if to_jsonb(old)-'result'-'result_seq'-'created_at' is distinct from to_jsonb(new)-'result'-'result_seq'-'created_at'
  or (new.result<>'{}'::jsonb and new.result is distinct from old.result) then raise exception 'Coverage replay differs';end if;
  new.result:=old.result;return new;
 end if;
 perform 1 from ingest.availability_geometry where correction_id=new.correction_id for share;
 select * into strict g from ingest.effective_availability_geometry where correction_id=new.correction_id;
 if g.geometry_hold or new.geometry_event_id is distinct from g.geometry_event_id then raise exception 'Missing/current acceptance required';end if;
 if new.subject_audit_sha256 is distinct from '2f106e1b19fa2b13415741a109d34f1f9dbc4fdb04cf67e77fe882325aebe5ff'
 or new.subject_payload_sha256 is distinct from '813824533f6c03c71fb8024431e0bd9f86e10b46c8e9ba12eb9c2ddf4d13696a'
 or new.subject_payload_sha256 is distinct from encode(sha256(convert_to(new.subject_response_text,'UTF8')),'hex') then raise exception 'Unreviewed study boundary';end if;
 select document into strict audit from ingest.audit_result where sha256=new.audit_sha256;
 if audit->>'method_sha256' is distinct from new.method_sha256
 or audit#>>'{acceptance,event_id}' is distinct from new.geometry_event_id
 or audit#>>'{acceptance,correction_id}' is distinct from new.correction_id
 or audit->>'subject_payload_sha256' is distinct from new.subject_payload_sha256 then raise exception 'Coverage differs from computation audit';end if;
 s:=new.subject_response_text::jsonb;
 if s#>>'{spatialReference,wkid}' is distinct from '4269' or jsonb_array_length(s->'features')<>1
 or s#>>'{features,0,attributes,CID}' is distinct from '230595'
 or jsonb_array_length(s#>'{features,0,geometry,rings}')<>1 then raise exception 'Unexpected subject geometry';end if;
 scope:=ST_SetSRID(ST_GeomFromGeoJSON(jsonb_build_object('type','Polygon','coordinates',s#>'{features,0,geometry,rings}')::text),4269);
 if not ST_IsValid(scope) or ST_IsEmpty(scope) then raise exception 'Invalid subject';end if;
 new.result:=jsonb_build_object('evidence_state','DERIVED','study_CID','230595','boundary_dependency','FEMA study boundary; not legal/surveyed parcel boundary',
  'digital_coverage',ST_Covers(g.effective_geometry,ST_Transform(scope,3857)),
  'method','PostGIS ST_Covers; study EPSG:4269 to source EPSG:3857',
  'postgis_version',PostGIS_Full_Version(),'candidate_sha256',g.candidate_sha256,'source_audit_sha256',g.source_audit_sha256,
  'wetland_completeness','UNKNOWN','present_day_conditions','UNKNOWN','legal_applicability','UNKNOWN',
  'source_imagery','May 1983; later NHD supplementation separately qualified');
 if new.result->>'digital_coverage' is distinct from 'true' then raise exception 'Coverage disagrees with reviewed bounded computation';end if;
 return new;
end $$;
create trigger validate_availability_coverage before insert on ingest.availability_coverage for each row execute function ingest.validate_availability_coverage();
create trigger immutable_availability_coverage before update or delete on ingest.availability_coverage for each row execute function ingest.reject_history_change();
create view ingest.availability_coverage_current as
select c.*,g.geometry_hold or g.geometry_event_id is distinct from c.geometry_event_id as needs_revisit
from ingest.availability_coverage c join ingest.effective_availability_geometry g using(correction_id);
create view ingest.availability_coverage_latest as
select distinct on(correction_id,subject_audit_sha256,subject_payload_sha256) * from ingest.availability_coverage_current
order by correction_id,subject_audit_sha256,subject_payload_sha256,result_seq desc;

alter table ingest.availability_geometry enable row level security;
alter table ingest.availability_geometry_event enable row level security;
alter table ingest.availability_coverage enable row level security;
revoke all on ingest.availability_geometry,ingest.availability_geometry_event,ingest.availability_coverage,ingest.effective_availability_geometry,ingest.availability_coverage_current,ingest.availability_coverage_latest from public,anon,authenticated,service_role;
revoke all on sequence ingest.availability_geometry_event_event_seq_seq,ingest.availability_coverage_result_seq_seq from public,anon,authenticated,service_role;
revoke all on function ingest.validate_availability_geometry(),ingest.record_availability_event(jsonb,text),ingest.validate_availability_coverage() from public,anon,authenticated,service_role;
