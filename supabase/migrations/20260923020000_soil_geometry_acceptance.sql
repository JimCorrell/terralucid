-- Exact-version soil proposals. No acceptance events or source changes on migration.
create function ingest.reject_soil_geometry_change() returns trigger language plpgsql as $$
begin raise exception 'Soil geometry history is append only';end $$;
create table ingest.soil_geometry_study (
 source_batch_sha256 text primary key references ingest.soil_batch(report_sha256),
 investigation_text text not null,
 investigation_sha256 text not null,
 boundary_wkb bytea not null,
 boundary_sha256 text not null,
 boundary extensions.geometry(MultiPolygon,26919) not null,
 created_at timestamptz not null default clock_timestamp()
);
create function ingest.validate_soil_geometry_study() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare b ingest.soil_batch%rowtype; d jsonb; old ingest.soil_geometry_study%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'Soil review requires READ COMMITTED';end if;
 select * into strict b from ingest.soil_batch where report_sha256=new.source_batch_sha256 for update;
 select * into old from ingest.soil_geometry_study where source_batch_sha256=new.source_batch_sha256;
 if found and row(old.investigation_text,old.investigation_sha256,old.boundary_wkb,old.boundary_sha256)
 is distinct from row(new.investigation_text,new.investigation_sha256,new.boundary_wkb,new.boundary_sha256)
 then raise exception 'Soil study replay differs';end if;
 d:=new.investigation_text::jsonb;
 if new.source_batch_sha256<>'b31e3034caee9f70361bb9c769b936b8709fcab38706f89cdee22c9265aad512'
 or new.investigation_sha256<>'ddda7a3674c616b1eda8921cdf7581fe58aecfffd6e8c32bbebd49ed8ca6df8a'
 or encode(sha256(convert_to(new.investigation_text,'UTF8')),'hex') is distinct from new.investigation_sha256
 or d->>'bundle_report_sha256' is distinct from new.source_batch_sha256
 or encode(sha256(new.boundary_wkb),'hex') is distinct from new.boundary_sha256
 or d->>'boundary_sha256' is distinct from new.boundary_sha256
 or b.report_text::jsonb->>'boundary_sha256' is distinct from new.boundary_sha256
 then raise exception 'Outside reviewed soil study';end if;
 new.boundary:=ST_Multi(ST_GeomFromWKB(new.boundary_wkb,26919));
 if not ST_IsValid(new.boundary) or ST_IsEmpty(new.boundary) or ST_NDims(new.boundary)<>2 then raise exception 'Invalid study boundary';end if;
 return new;
end $$;
create trigger validate_soil_geometry_study before insert on ingest.soil_geometry_study for each row execute function ingest.validate_soil_geometry_study();
create trigger immutable_soil_geometry_study before update or delete on ingest.soil_geometry_study for each row execute function ingest.reject_soil_geometry_change();

-- Ordered endpoint bytes preserve direction, coordinate precision and multiplicity.
create function ingest.soil_directed_segments(g extensions.geometry)
returns table(a bytea,b bytea,n bigint) language sql immutable set search_path=pg_catalog,extensions as $$
 select ST_AsEWKB(ST_StartPoint(geom)),ST_AsEWKB(ST_EndPoint(geom)),count(*)
 from ST_DumpSegments(g) group by 1,2
$$;
create table ingest.soil_geometry_correction (
 correction_id text primary key check(correction_id ~ '^[0-9a-f]{64}$'),
 source_batch_sha256 text not null references ingest.soil_geometry_study,
 kind text not null default 'mupolygon' check(kind='mupolygon'),
 source_key text not null,
 source_input_sha256 text not null,
 candidate_wkb bytea not null,
 candidate_sha256 text not null,
 geometry extensions.geometry(MultiPolygon,4326) not null,
 evidence_state text not null check(evidence_state='DERIVED'),
 created_at timestamptz not null default clock_timestamp(),
 foreign key(source_batch_sha256,kind,source_key) references ingest.soil_record(report_sha256,kind,source_key),
 unique(source_batch_sha256,source_key)
);
create function ingest.validate_soil_geometry_correction() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare f ingest.soil_record%rowtype; p jsonb; c jsonb; original geometry; old ingest.soil_geometry_correction%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'Soil review requires READ COMMITTED';end if;
 perform 1 from ingest.soil_batch where report_sha256=new.source_batch_sha256 for update;
 select * into old from ingest.soil_geometry_correction where correction_id=new.correction_id;
 if found and row(old.source_batch_sha256,old.kind,old.source_key,old.source_input_sha256,old.candidate_wkb,old.candidate_sha256,old.evidence_state)
 is distinct from row(new.source_batch_sha256,new.kind,new.source_key,new.source_input_sha256,new.candidate_wkb,new.candidate_sha256,new.evidence_state)
 then raise exception 'Soil correction replay differs';end if;
 select * into strict f from ingest.soil_record where report_sha256=new.source_batch_sha256 and kind='mupolygon' and source_key=new.source_key;
 select investigation_text::jsonb into strict p from ingest.soil_geometry_study where source_batch_sha256=new.source_batch_sha256;
 select v into strict c from jsonb_array_elements(p->'candidates') v where v->>'mupolygonkey'=new.source_key;
 if f.input_sha256 is distinct from new.source_input_sha256
 or f.input_sha256 is distinct from encode(sha256(convert_to(f.input_text,'UTF8')),'hex')
 or f.hold is null or f.geometry is not null or f.scope_relation is distinct from 'held'
 or c->>'source_wkt_sha256' is distinct from encode(sha256(convert_to(f.input_text::jsonb#>>'{raw,source_wkt}','UTF8')),'hex')
 or c->>'source_response_sha256' is distinct from f.response_sha256
 or c->>'candidate_sha256' is distinct from new.candidate_sha256
 or encode(sha256(new.candidate_wkb),'hex') is distinct from new.candidate_sha256
 or c->>'acceptance' is distinct from 'proposed_only'
 or c->>'native_sql_valid' is distinct from '1'
 or p#>>'{native_containment,all_match}' is distinct from 'true'
 or new.correction_id is distinct from encode(sha256(convert_to(new.source_batch_sha256||':'||new.source_key||':'||new.candidate_sha256,'UTF8')),'hex')
 then raise exception 'Soil candidate differs from reviewed source/evidence';end if;
 new.geometry:=ST_GeomFromWKB(new.candidate_wkb,4326);
 if ST_IsEmpty(new.geometry) or not ST_IsValid(new.geometry) or ST_NDims(new.geometry)<>2
 or not ST_IsValid(ST_Transform(new.geometry,26919)) then raise exception 'Invalid soil candidate';end if;
 original:=ST_GeomFromText(f.input_text::jsonb#>>'{raw,source_wkt}',4326);
 if exists((select * from ingest.soil_directed_segments(original) except select * from ingest.soil_directed_segments(new.geometry))
 union all(select * from ingest.soil_directed_segments(new.geometry) except select * from ingest.soil_directed_segments(original)))
 then raise exception 'Soil candidate changes directed source segments';end if;
 return new;
end $$;
create trigger validate_soil_geometry_correction before insert on ingest.soil_geometry_correction for each row execute function ingest.validate_soil_geometry_correction();
create trigger immutable_soil_geometry_correction before update or delete on ingest.soil_geometry_correction for each row execute function ingest.reject_soil_geometry_change();

create sequence ingest.soil_geometry_event_event_seq_seq;
create table ingest.soil_geometry_event (
 event_id text primary key check(event_id ~ '^[0-9a-f]{64}$'),
 event_seq bigint not null unique,
 correction_id text not null references ingest.soil_geometry_correction(correction_id),
 expected_event_id text,
 status text not null check(status in ('accepted','withdrawn')),
 actor text not null check(length(btrim(actor))>0),
 note text not null check(length(btrim(note))>0),
 created_at timestamptz not null default clock_timestamp()
);
create index soil_geometry_event_latest on ingest.soil_geometry_event(correction_id,event_seq desc);
create function ingest.validate_soil_geometry_event() returns trigger language plpgsql set search_path=pg_catalog,ingest as $$
declare source_batch text; current_id text; old ingest.soil_geometry_event%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'Soil review requires READ COMMITTED';end if;
 select source_batch_sha256 into strict source_batch from ingest.soil_geometry_correction where correction_id=new.correction_id;
 perform 1 from ingest.soil_batch where report_sha256=source_batch for update;
 select * into old from ingest.soil_geometry_event where event_id=new.event_id;
 if found then
  if to_jsonb(old)-'event_seq'-'created_at' is distinct from to_jsonb(new)-'event_seq'-'created_at' then raise exception 'Soil event ID reused';end if;
  new.event_seq:=old.event_seq;return new;
 end if;
 select event_id into current_id from ingest.soil_geometry_event where correction_id=new.correction_id order by event_seq desc limit 1;
 if current_id is distinct from new.expected_event_id then raise exception 'Soil geometry review changed';end if;
 -- Allocate after the batch lock: sequence order must follow serialized review order.
 new.event_seq:=nextval('ingest.soil_geometry_event_event_seq_seq');
 return new;
end $$;
create trigger validate_soil_geometry_event before insert on ingest.soil_geometry_event for each row execute function ingest.validate_soil_geometry_event();
create trigger immutable_soil_geometry_event before update or delete on ingest.soil_geometry_event for each row execute function ingest.reject_soil_geometry_change();
create function ingest.record_soil_geometry_event(payload jsonb,expected_event_id text) returns text language plpgsql set search_path=pg_catalog,ingest as $$
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'Soil review requires READ COMMITTED';end if;
 if (select count(*) from jsonb_object_keys(payload))<>5 or not payload ?& array['event_id','correction_id','status','actor','note'] then raise exception 'Unexpected soil event fields';end if;
 insert into ingest.soil_geometry_event(event_id,correction_id,expected_event_id,status,actor,note)
 values(payload->>'event_id',payload->>'correction_id',expected_event_id,payload->>'status',payload->>'actor',payload->>'note') on conflict(event_id) do nothing;
 return payload->>'event_id';
end $$;
create view ingest.soil_geometry_current as
 select c.*,e.event_id as geometry_event_id,coalesce(e.status,'proposed') as correction_status
 from ingest.soil_geometry_correction c left join lateral(
 select event_id,status from ingest.soil_geometry_event where correction_id=c.correction_id order by event_seq desc limit 1)e on true;

create function ingest.soil_geometry_dependencies(source_batch text) returns jsonb language sql stable set search_path=pg_catalog,ingest as $$
 select coalesce(jsonb_object_agg(correction_id,jsonb_build_object('event_id',geometry_event_id,'status',correction_status,'candidate_sha256',candidate_sha256,'source_input_sha256',source_input_sha256)),'{}'::jsonb)
 from ingest.soil_geometry_current where source_batch_sha256=source_batch
$$;
create table ingest.soil_geometry_snapshot (
 snapshot_id text primary key,
 source_batch_sha256 text not null references ingest.soil_batch(report_sha256),
 dependencies jsonb not null check(jsonb_typeof(dependencies)='object'),
 created_at timestamptz not null default clock_timestamp()
);
create function ingest.validate_soil_geometry_snapshot() returns trigger language plpgsql set search_path=pg_catalog,ingest as $$
declare old ingest.soil_geometry_snapshot%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'Soil review requires READ COMMITTED';end if;
 perform 1 from ingest.soil_batch where report_sha256=new.source_batch_sha256 for share;
 select * into old from ingest.soil_geometry_snapshot where snapshot_id=new.snapshot_id;
 if found then
  if to_jsonb(old)-'created_at' is distinct from to_jsonb(new)-'created_at' then raise exception 'Soil snapshot replay differs';end if;
  return new;
 end if;
 if new.dependencies is distinct from ingest.soil_geometry_dependencies(new.source_batch_sha256)
 or new.snapshot_id is distinct from encode(sha256(convert_to(new.source_batch_sha256||':'||new.dependencies::text,'UTF8')),'hex') then raise exception 'Soil dependencies changed';end if;
 return new;
end $$;
create trigger validate_soil_geometry_snapshot before insert on ingest.soil_geometry_snapshot for each row execute function ingest.validate_soil_geometry_snapshot();
create trigger immutable_soil_geometry_snapshot before update or delete on ingest.soil_geometry_snapshot for each row execute function ingest.reject_soil_geometry_change();
create function ingest.record_soil_geometry_snapshot(source_batch text) returns text language plpgsql set search_path=pg_catalog,ingest as $$
declare d jsonb; sid text;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'Soil review requires READ COMMITTED';end if;
 perform 1 from ingest.soil_batch where report_sha256=source_batch for share;
 if not found then raise exception 'Unknown soil source audit';end if;
 d:=ingest.soil_geometry_dependencies(source_batch);sid:=encode(sha256(convert_to(source_batch||':'||d::text,'UTF8')),'hex');
 insert into ingest.soil_geometry_snapshot(snapshot_id,source_batch_sha256,dependencies) values(sid,source_batch,d) on conflict do nothing;
 return sid;
end $$;
create view ingest.soil_geometry_snapshot_current as
 select s.*,s.dependencies is distinct from ingest.soil_geometry_dependencies(s.source_batch_sha256) as needs_revisit from ingest.soil_geometry_snapshot s;
create function ingest.soil_geometry_snapshot_is_current(sid text,intended_source_batch text) returns boolean language sql stable set search_path=pg_catalog,ingest as $$
 select exists(select 1 from ingest.soil_geometry_snapshot_current where snapshot_id=sid and source_batch_sha256=intended_source_batch and not needs_revisit)
$$;

create view ingest.effective_soil_geometry as
 select f.report_sha256,f.source_key,f.input_sha256,f.response_sha256,
 f.input_text::jsonb->'raw' as source_attributes,
 f.input_text::jsonb->'provenance' as provenance,
 f.geometry as original_geometry,f.hold as original_geometry_hold,f.scope_relation as original_scope_relation,
 case when c.correction_status='accepted' then c.geometry else f.geometry end as effective_geometry,
 case when c.correction_status='accepted' then null else f.hold end as effective_geometry_hold,
 case when c.correction_status='accepted' then
  case when not extensions.ST_Intersects(extensions.ST_Transform(c.geometry,26919),s.boundary) then 'outside'
   when extensions.ST_Touches(extensions.ST_Transform(c.geometry,26919),s.boundary) then 'touch' else 'interior' end
  else f.scope_relation end as effective_scope_relation,
 c.correction_id,c.candidate_sha256,c.geometry_event_id,coalesce(c.correction_status,'original') as correction_status,
 s.investigation_sha256,s.boundary_sha256,
 'DERIVED'::text as geometry_evidence_state,'UNKNOWN'::text as site_suitability_state,
 false as qualified_for_parcel_screening
 from ingest.soil_record f left join ingest.soil_geometry_study s on s.source_batch_sha256=f.report_sha256
 left join ingest.soil_geometry_current c on c.source_batch_sha256=f.report_sha256 and c.source_key=f.source_key and c.source_input_sha256=f.input_sha256
 where f.kind='mupolygon';

-- Return a dependency-bound result; callers persist it with their downstream audit.
-- Recompute from effective geometry, never reuse the hypothetical proposal report.
create function ingest.soil_geometry_coverage(source_batch text) returns jsonb language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare sid text; b geometry; u geometry; gap geometry; held bigint; area double precision;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'Soil review requires READ COMMITTED';end if;
 sid:=ingest.record_soil_geometry_snapshot(source_batch);
 select boundary into strict b from ingest.soil_geometry_study where source_batch_sha256=source_batch;
 select ST_UnaryUnion(ST_Collect(ST_Transform(effective_geometry,26919))) into u
 from ingest.effective_soil_geometry where report_sha256=source_batch and effective_geometry_hold is null and effective_scope_relation='interior';
 select count(*) into held from ingest.effective_soil_geometry where report_sha256=source_batch and effective_geometry_hold is not null;
 gap:=case when u is null then b else ST_Difference(b,u) end;area:=ST_Area(gap);
 return jsonb_build_object('source_batch_sha256',source_batch,'snapshot_id',sid,'boundary_area_m2',ST_Area(b),
 'uncovered_m2',area,'coverage_state',case when area=0 then 'full_geometric' else 'partial_geometric' end,
 'held_polygons',held,'evidence_state','DERIVED','qualified_for_parcel_screening',false,
 'postgis_version',postgis_full_version());
end $$;

alter table ingest.soil_geometry_study enable row level security;
alter table ingest.soil_geometry_correction enable row level security;
alter table ingest.soil_geometry_event enable row level security;
alter table ingest.soil_geometry_snapshot enable row level security;
revoke all on ingest.soil_geometry_study,ingest.soil_geometry_correction,ingest.soil_geometry_event,
 ingest.soil_geometry_snapshot,ingest.soil_geometry_current,ingest.effective_soil_geometry,
 ingest.soil_geometry_snapshot_current from public,anon,authenticated,service_role;
revoke all on sequence ingest.soil_geometry_event_event_seq_seq from public,anon,authenticated,service_role;
revoke all on function ingest.reject_soil_geometry_change(),ingest.validate_soil_geometry_study(),
 ingest.soil_directed_segments(extensions.geometry),ingest.validate_soil_geometry_correction(),
 ingest.validate_soil_geometry_event(),ingest.record_soil_geometry_event(jsonb,text),
 ingest.soil_geometry_dependencies(text),ingest.validate_soil_geometry_snapshot(),
 ingest.record_soil_geometry_snapshot(text),ingest.soil_geometry_snapshot_is_current(text,text),
 ingest.soil_geometry_coverage(text) from public,anon,authenticated,service_role;
