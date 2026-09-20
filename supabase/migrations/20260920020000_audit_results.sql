-- Derived reports reference the immutable registry version and exact archived bytes.
create table ingest.audit_result (
  sha256 text primary key check (sha256 ~ '^[0-9a-f]{64}$'),
  registry_sha256 text not null references ingest.registry_snapshot(sha256),
  evidence_state text not null check (evidence_state = 'DERIVED'),
  method_path text not null,
  method_sha256 text not null check (method_sha256 ~ '^[0-9a-f]{64}$'),
  document jsonb not null,
  storage_bucket text not null check (storage_bucket = 'terralucid-source-snapshots'),
  storage_object text not null check (storage_object = 'sha256/' || sha256 || '.response'),
  loaded_at timestamptz not null default now()
);
revoke all on ingest.audit_result from public, anon, authenticated, service_role;
alter table ingest.audit_result enable row level security;
comment on table ingest.audit_result is 'Reproducible source-level audit results; DERIVED does not certify legal jurisdiction status or parcel completeness.';
