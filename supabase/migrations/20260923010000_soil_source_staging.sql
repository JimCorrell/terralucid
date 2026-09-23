-- Private, versioned soil source staging. No availability or suitability promotion.
create table ingest.soil_batch (
 report_sha256 text primary key check(report_sha256 ~ '^[0-9a-f]{64}$'),
 report_text text not null,
 manifest jsonb not null,
 row_fingerprint text not null check(row_fingerprint ~ '^[0-9a-f]{64}$'),
 loaded_xid xid8 not null default pg_current_xact_id(),
 created_at timestamptz not null default clock_timestamp(),
 check(encode(sha256(convert_to(report_text,'UTF8')),'hex')=report_sha256),
 check(manifest->>'report_sha256'=report_sha256)
);
create table ingest.soil_archive_object (
 report_sha256 text not null references ingest.soil_batch,
 sha256 text not null check(sha256 ~ '^[0-9a-f]{64}$'),
 byte_count bigint not null check(byte_count>=0),
 storage_bucket text not null check(storage_bucket='terralucid-source-snapshots'),
 storage_object text not null,
 primary key(report_sha256,sha256),
 check(storage_object='sha256/'||sha256||'.response')
);
create table ingest.soil_record (
 report_sha256 text not null references ingest.soil_batch,
 load_ordinal integer not null check(load_ordinal>=0),
 input_text text not null,
 input_sha256 text not null,
 kind text not null check(kind in ('legend','mapunit','component','chorizon','mupolygon')),
 source_key text not null,
 parent_kind text,
 parent_key text,
 response_sha256 text not null,
 source_row_ordinal integer not null check(source_row_ordinal>=0),
 scope_relation text check(scope_relation in ('interior','outside','touch','held')),
 hold text,
 geometry extensions.geometry(Geometry,4326),
 primary key(report_sha256,kind,source_key),
 unique(report_sha256,load_ordinal),
 foreign key(report_sha256,response_sha256) references ingest.soil_archive_object(report_sha256,sha256),
 foreign key(report_sha256,parent_kind,parent_key) references ingest.soil_record(report_sha256,kind,source_key) deferrable initially deferred,
 check((parent_kind is null)=(parent_key is null))
);
create index soil_record_geometry on ingest.soil_record using gist(geometry);
create index soil_record_parent on ingest.soil_record(report_sha256,parent_kind,parent_key);
create function ingest.soil_history_guard() returns trigger language plpgsql
set search_path=pg_catalog,ingest as $$
begin
 if TG_OP<>'INSERT' then raise exception 'Soil source history is append only';end if;
 if (select loaded_xid from ingest.soil_batch where report_sha256=new.report_sha256) is distinct from pg_current_xact_id()
 then raise exception 'Soil batch is sealed; load a new version';end if;
 return new;
end $$;
create function ingest.decode_soil_record() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare d jsonb; key_field text; source_geom geometry;
begin
 d:=new.input_text::jsonb;
 new.input_sha256:=encode(sha256(convert_to(new.input_text,'UTF8')),'hex');
 new.kind:=d->>'kind';new.source_key:=d->>'source_key';
 new.response_sha256:=d#>>'{provenance,response_sha256}';
 new.source_row_ordinal:=(d#>>'{provenance,row_ordinal}')::integer;
 key_field:=case new.kind when 'legend' then 'lkey' when 'mapunit' then 'mukey' when 'component' then 'cokey' when 'chorizon' then 'chkey' when 'mupolygon' then 'mupolygonkey' end;
 if key_field is null or d#>>array['raw',key_field] is distinct from new.source_key then raise exception 'Soil source identity differs';end if;
 new.parent_kind:=case new.kind when 'mapunit' then 'legend' when 'component' then 'mapunit' when 'chorizon' then 'component' when 'mupolygon' then 'mapunit' end;
 new.parent_key:=case new.kind when 'mapunit' then d#>>'{raw,lkey}' when 'component' then d#>>'{raw,mukey}' when 'chorizon' then d#>>'{raw,cokey}' when 'mupolygon' then d#>>'{raw,mukey}' end;
 new.scope_relation:=d->>'scope_relation';new.hold:=d->>'hold';new.geometry:=null;
 if new.kind='mupolygon' then
  if d->>'srid' is distinct from '4326' or new.scope_relation is null then raise exception 'Missing soil CRS/scope';end if;
  if new.hold is not null then
   if d->>'geometry_wkb' is not null or new.scope_relation<>'held' or new.hold='' then raise exception 'Held soil geometry cannot be enabled';end if;
  else
   if new.scope_relation='held' or d->>'geometry_wkb' is null then raise exception 'Missing usable soil geometry';end if;
   new.geometry:=ST_GeomFromWKB(decode(d->>'geometry_wkb','hex'),4326);
   source_geom:=ST_GeomFromText(d#>>'{raw,source_wkt}',4326);
   if ST_IsEmpty(new.geometry) or not ST_IsValid(new.geometry) or ST_NDims(new.geometry)<>2
    or GeometryType(new.geometry) not in ('POLYGON','MULTIPOLYGON') or not ST_OrderingEquals(new.geometry,source_geom)
   then raise exception 'Soil geometry differs from valid source';end if;
  end if;
 elsif d->>'geometry_wkb' is not null or new.hold is not null or new.scope_relation is not null then raise exception 'Tabular soil row has geometry state';
 end if;
 return new;
end $$;
create trigger soil_record_decode before insert on ingest.soil_record for each row execute function ingest.decode_soil_record();
create trigger soil_record_guard before insert or update or delete on ingest.soil_record for each row execute function ingest.soil_history_guard();
create trigger soil_archive_guard before insert or update or delete on ingest.soil_archive_object for each row execute function ingest.soil_history_guard();
-- Batch insertion is allowed; only modifications are guarded.
create trigger soil_batch_guard before update or delete on ingest.soil_batch for each row execute function ingest.soil_history_guard();
alter table ingest.soil_batch enable row level security;
alter table ingest.soil_archive_object enable row level security;
alter table ingest.soil_record enable row level security;
revoke all on ingest.soil_batch,ingest.soil_archive_object,ingest.soil_record from public,anon,authenticated,service_role;
revoke all on function ingest.soil_history_guard(),ingest.decode_soil_record() from public,anon,authenticated,service_role;
comment on table ingest.soil_record is 'Source soil records scoped by report hash. Seven original holds remain; coverage and legal/site qualification are separate. Not an availability adapter.';
