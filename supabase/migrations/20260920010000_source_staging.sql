-- Source audit staging only. No canonical parcels or suitability findings.
create schema if not exists extensions;
create extension if not exists postgis with schema extensions;
-- An existing PostGIS installation elsewhere must be reviewed, never moved here.
do $$
begin
  if (select extnamespace <> 'extensions'::regnamespace
      from pg_extension where extname = 'postgis') then
    raise exception 'Existing PostGIS schema differs; review before applying';
  end if;
end $$;

create schema ingest;
revoke all on schema ingest from public, anon, authenticated, service_role;

create table ingest.registry_snapshot (
  sha256 text primary key check (sha256 ~ '^[0-9a-f]{64}$'),
  byte_count bigint not null check (byte_count > 0),
  document jsonb not null check (jsonb_typeof(document->'sources') = 'array'),
  storage_bucket text not null check (storage_bucket = 'terralucid-source-snapshots'),
  storage_object text not null check (storage_object = 'sha256/' || sha256 || '.response'),
  loaded_at timestamptz not null default now()
);

create table ingest.source_response (
  -- Identity covers registry version, run path and complete retrieval log.
  observation_sha256 text primary key check (observation_sha256 ~ '^[0-9a-f]{64}$'),
  registry_sha256 text not null references ingest.registry_snapshot(sha256),
  run_path text not null,
  probe_id text not null,
  source_ids text[] not null check (cardinality(source_ids) > 0),
  retrieved_at timestamptz not null,
  http_status integer not null check (http_status between 100 and 599),
  outcome text not null,
  retrieval_log jsonb not null,
  payload_sha256 text not null check (payload_sha256 ~ '^[0-9a-f]{64}$'),
  byte_count bigint not null check (byte_count > 0),
  storage_bucket text not null check (storage_bucket = 'terralucid-source-snapshots'),
  storage_object text not null check (storage_object = 'sha256/' || payload_sha256 || '.response'),
  loaded_at timestamptz not null default now()
);

create table ingest.geometry_sample (
  observation_sha256 text not null references ingest.source_response(observation_sha256),
  feature_ordinal integer not null check (feature_ordinal >= 0),
  raw_feature jsonb not null,
  geometry extensions.geometry(Geometry,4326) not null,
  transformation text not null check (transformation = 'GeoJSON geometry decoded; requested outSR=4326; no repair'),
  primary key (observation_sha256, feature_ordinal)
);
create index geometry_sample_gist on ingest.geometry_sample using gist (geometry);

comment on schema ingest is 'Private source staging; use administrative ingestion, never expose through Data API.';
comment on table ingest.geometry_sample is 'Bounded source geometry samples, not canonical parcels or legal boundaries. Original GeoJSON retained; invalid geometry is not repaired silently.';
comment on column ingest.source_response.outcome is 'Retrieval outcome, not VERIFIED/DERIVED/INFERRED/UNKNOWN classification of parcel facts.';

revoke all on all tables in schema ingest from public, anon, authenticated, service_role;
alter table ingest.registry_snapshot enable row level security;
alter table ingest.source_response enable row level security;
alter table ingest.geometry_sample enable row level security;
-- No client policies. Administrative database access is required for this pilot.
alter default privileges in schema ingest revoke all on tables from public, anon, authenticated, service_role;
