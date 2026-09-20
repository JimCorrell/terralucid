-- Bounded zoning evidence and reproducible screening, not legal zoning decisions.
create table ingest.zoning_feature (
  audit_sha256 text not null references ingest.audit_result(sha256),
  object_id bigint not null,
  observation_sha256 text not null references ingest.source_response(observation_sha256),
  raw_feature jsonb not null,
  geometry extensions.geometry(Geometry,4326),
  geometry_state text not null check (geometry_state in ('valid','invalid','missing','decode_failed')),
  geometry_detail text,
  primary key(audit_sha256,object_id)
);
create index zoning_feature_geometry on ingest.zoning_feature using gist(geometry);
create function ingest.decode_zoning_geometry() returns trigger
language plpgsql set search_path=pg_catalog,extensions as $$
begin
  if exists(select 1 from ingest.zoning_feature z where z.audit_sha256=new.audit_sha256 and z.object_id=new.object_id and (z.raw_feature is distinct from new.raw_feature or z.observation_sha256 is distinct from new.observation_sha256)) then raise exception 'Zoning feature replay differs'; end if;
  if (new.raw_feature#>>'{properties,OBJECTID}')::bigint is distinct from new.object_id then raise exception 'Zoning feature identity differs'; end if;
  begin
    new.geometry:=extensions.ST_GeomFromGeoJSON((new.raw_feature->'geometry')::text);
    if new.geometry is null or extensions.ST_IsEmpty(new.geometry) then
      new.geometry_state:='missing';new.geometry_detail:='Missing source geometry';
    elsif extensions.ST_SRID(new.geometry)<>4326 then raise exception 'Unexpected SRID';
    else
      new.geometry_state:=case when extensions.ST_IsValid(new.geometry,0) then 'valid' else 'invalid' end;
      new.geometry_detail:=extensions.ST_IsValidReason(new.geometry);
    end if;
  exception when others then
    new.geometry:=null;new.geometry_state:='decode_failed';new.geometry_detail:=SQLERRM;
  end;
  return new;
end $$;
create trigger zoning_geometry before insert on ingest.zoning_feature for each row execute function ingest.decode_zoning_geometry();
create trigger immutable_zoning_feature before update or delete on ingest.zoning_feature for each row execute function ingest.reject_history_change();

create table ingest.zoning_screening (
  audit_sha256 text not null references ingest.audit_result(sha256),
  subject_id text not null,
  source_record_id text references ingest.source_record(record_id),
  correction_id text references ingest.correction_source(correction_id),
  correction_event_id text references ingest.correction_event(event_id),
  input jsonb not null,
  result jsonb not null check ((result->>'legal_zoning_state') is not distinct from 'UNKNOWN' and (result->>'boundary_dependency') is not distinct from 'assessment_geometry' and jsonb_typeof(result->'intersections') is not distinct from 'array'),
  created_at timestamptz not null default clock_timestamp(),
  primary key(audit_sha256,subject_id),
  check ((source_record_id is not null)::int+(correction_id is not null)::int=1),
  check (subject_id=coalesce(correction_id,source_record_id)),
  check (correction_event_id is null or correction_id is not null)
);
create function ingest.validate_zoning_input() returns trigger
language plpgsql set search_path=pg_catalog,ingest as $$
declare c ingest.corrected_source%rowtype; r ingest.source_record%rowtype;
begin
  if exists(select 1 from ingest.zoning_screening s where s.audit_sha256=new.audit_sha256 and s.subject_id=new.subject_id and (s.input is distinct from new.input or s.result is distinct from new.result or s.correction_event_id is distinct from new.correction_event_id or s.source_record_id is distinct from new.source_record_id or s.correction_id is distinct from new.correction_id)) then raise exception 'Zoning screening replay differs'; end if;
  if new.correction_id is not null then
    perform 1 from ingest.correction_source where correction_id=new.correction_id for share;
    select * into strict c from ingest.corrected_source where correction_id=new.correction_id;
    if c.event_id is distinct from new.correction_event_id
      or c.raw_feature is distinct from new.input->'raw_feature'
      or c.effective_properties is distinct from new.input->'effective_properties'
      or c.holds is distinct from new.input->'holds'
      or c.source_snapshot_sha256 is distinct from new.input->>'source_snapshot_sha256'
      or c.source_feature_sha256 is distinct from new.input->>'source_feature_sha256'
      or c.correction_status is distinct from new.input->>'correction_status'
      or c.source_id is distinct from new.input->>'source_id' then
      raise exception 'Correction input changed; export and recompute';
    end if;
  else
    select * into strict r from ingest.source_record where record_id=new.source_record_id for share;
    if r.raw_feature is distinct from new.input->'raw_feature'
      or r.raw_feature->'properties' is distinct from new.input->'effective_properties'
      or to_jsonb(r.quality_flags) is distinct from new.input->'quality_flags'
      or r.batch_id is distinct from new.input->>'source_snapshot_sha256'
      or r.source_id is distinct from new.input->>'source_id' then
      raise exception 'Source input changed; export and recompute';
    end if;
  end if;
  if exists(select 1 from jsonb_array_elements(new.result->'intersections') h where not exists(
      select 1 from ingest.zoning_feature z where z.audit_sha256=new.audit_sha256 and z.object_id=(h->>'object_id')::bigint and z.geometry_state='valid')) then
    raise exception 'Intersection references missing or invalid zoning geometry';
  end if;
  return new;
end $$;
create trigger validate_zoning_input before insert on ingest.zoning_screening for each row execute function ingest.validate_zoning_input();
create trigger immutable_zoning_screening before update or delete on ingest.zoning_screening for each row execute function ingest.reject_history_change();

create view ingest.zoning_screening_current as
select s.*,case when s.correction_id is not null then
    c.event_id is distinct from s.correction_event_id
    or c.raw_feature is distinct from s.input->'raw_feature'
    or c.effective_properties is distinct from s.input->'effective_properties'
    or c.holds is distinct from s.input->'holds'
  else r.raw_feature is distinct from s.input->'raw_feature'
    or to_jsonb(r.quality_flags) is distinct from s.input->'quality_flags'
  end as needs_revisit
from ingest.zoning_screening s
left join ingest.corrected_source c on c.correction_id=s.correction_id
left join ingest.source_record r on r.record_id=s.source_record_id;

alter table ingest.zoning_feature enable row level security;
alter table ingest.zoning_screening enable row level security;
revoke all on ingest.zoning_feature,ingest.zoning_screening,ingest.zoning_screening_current from public,anon,authenticated,service_role;
revoke all on function ingest.decode_zoning_geometry(),ingest.validate_zoning_input() from public,anon,authenticated,service_role;
comment on table ingest.zoning_feature is 'Observed publisher zoning polygons, including invalid geometry and all date/publication fields. No legal-current selection or repair.';
comment on view ingest.zoning_screening_current is 'Historical screening using effective source properties. Needs revisit after source/correction changes; an unchanged input does not certify current legal zoning. Intersections are boundary-dependent DERIVED evidence only.';
