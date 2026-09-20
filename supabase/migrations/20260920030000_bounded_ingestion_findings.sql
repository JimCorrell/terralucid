-- Source records and operational data-quality follow-up; no canonical parcels.
create table ingest.load_batch (
  batch_id text primary key check (batch_id ~ '^[0-9a-f]{64}$'),
  registry_sha256 text not null references ingest.registry_snapshot(sha256),
  audit_sha256 text not null references ingest.audit_result(sha256),
  manifest_sha256 text not null check (manifest_sha256 ~ '^[0-9a-f]{64}$'),
  definition jsonb not null,
  methods jsonb not null,
  loaded_at timestamptz not null default clock_timestamp()
);
create table ingest.source_record (
  record_id text primary key check (record_id ~ '^[0-9a-f]{64}$'),
  batch_id text not null references ingest.load_batch(batch_id),
  source_id text not null,
  object_id bigint not null,
  global_id text,
  observation_sha256 text not null references ingest.source_response(observation_sha256),
  record_kind text not null check (record_kind in ('assessment_geometry','assessment')),
  raw_feature jsonb not null,
  raw_identifiers jsonb not null,
  parsed_date jsonb not null,
  quality_flags text[] not null default '{}',
  geometry extensions.geometry(Geometry,4326),
  geometry_detail text,
  geometry_state text not null check (geometry_state in ('valid','invalid','missing','decode_failed','not_applicable')),
  unique(batch_id,source_id,object_id),
  unique(record_id,batch_id)
);
create index source_record_geometry on ingest.source_record using gist(geometry);
create index source_record_global_id on ingest.source_record(source_id,global_id);

create function ingest.decode_source_geometry() returns trigger
language plpgsql set search_path = pg_catalog, extensions as $$
begin
  if new.record_kind='assessment' then
    new.geometry := null; new.geometry_state := 'not_applicable'; new.geometry_detail := null;
  elsif new.raw_feature->'geometry' is null or new.raw_feature->'geometry'='null'::jsonb then
    new.geometry := null; new.geometry_state := 'missing'; new.geometry_detail := 'Source geometry is absent';
  else
    begin
      new.geometry := extensions.ST_GeomFromGeoJSON((new.raw_feature->'geometry')::text);
      if new.geometry is null then raise exception 'Decoded geometry is null'; end if;
      if extensions.ST_SRID(new.geometry)<>4326 then raise exception 'Unexpected SRID'; end if;
      new.geometry_state := case when extensions.ST_IsEmpty(new.geometry) then 'missing'
                                when extensions.ST_IsValid(new.geometry,0) then 'valid' else 'invalid' end;
      new.geometry_detail := extensions.ST_IsValidReason(new.geometry);
    exception when others then
      new.geometry := null; new.geometry_state := 'decode_failed'; new.geometry_detail := SQLERRM;
    end;
  end if;
  if new.geometry_state in ('invalid','missing','decode_failed') then
    new.quality_flags := array_append(new.quality_flags,'geometry_'||new.geometry_state);
  end if;
  return new;
end $$;
create trigger source_geometry before insert on ingest.source_record
for each row execute function ingest.decode_source_geometry();

create table ingest.assessment_candidate (
  batch_id text not null references ingest.load_batch(batch_id),
  geometry_record_id text not null,
  assessment_record_id text not null,
  basis text not null check (basis='exact_raw_STATE_ID'),
  geocode_agrees boolean not null,
  primary key (geometry_record_id,assessment_record_id),
  foreign key (geometry_record_id,batch_id) references ingest.source_record(record_id,batch_id),
  foreign key (assessment_record_id,batch_id) references ingest.source_record(record_id,batch_id)
);

create table ingest.finding (
  finding_id text primary key check (finding_id ~ '^TL-F-[0-9]{4}$'),
  title text not null check (length(btrim(title))>0),
  description text not null,
  source_ids text[] not null,
  scope jsonb not null,
  evidence_state text not null check (evidence_state in ('VERIFIED','DERIVED','INFERRED','UNKNOWN')),
  created_at timestamptz not null default clock_timestamp()
);
create table ingest.finding_event (
  event_id text primary key check (event_id ~ '^[0-9a-f]{64}$'),
  event_seq bigint generated always as identity unique,
  finding_id text not null references ingest.finding(finding_id),
  status text not null check (status in ('open','in_progress','blocked','deferred','resolved')),
  priority text not null check (priority in ('high','medium','low')),
  next_action text not null check (length(btrim(next_action))>0),
  actor text not null check (length(btrim(actor))>0),
  note text not null check (length(btrim(note))>0),
  evidence_refs jsonb not null check (jsonb_typeof(evidence_refs)='array'),
  created_at timestamptz not null default clock_timestamp(),
  check (status<>'resolved' or jsonb_array_length(evidence_refs)>0)
);
create table ingest.finding_occurrence (
  occurrence_id text primary key check (occurrence_id ~ '^[0-9a-f]{64}$'),
  finding_id text not null references ingest.finding(finding_id),
  audit_sha256 text references ingest.audit_result(sha256),
  registry_sha256 text references ingest.registry_snapshot(sha256),
  batch_id text references ingest.load_batch(batch_id),
  record_id text,
  details jsonb not null,
  created_at timestamptz not null default clock_timestamp(),
  foreign key(record_id,batch_id) references ingest.source_record(record_id,batch_id),
  check (audit_sha256 is not null or registry_sha256 is not null or batch_id is not null),
  check (record_id is null or batch_id is not null)
);
create index finding_occurrence_lookup on ingest.finding_occurrence(finding_id,created_at);
create index finding_event_lookup on ingest.finding_event(finding_id,event_seq desc);

create function ingest.reject_history_change() returns trigger
language plpgsql set search_path=pg_catalog as $$
begin
  raise exception 'Append a new finding event or occurrence; original history is immutable';
end $$;
create trigger immutable_finding before update or delete on ingest.finding
for each row execute function ingest.reject_history_change();
create trigger immutable_finding_event before update or delete on ingest.finding_event
for each row execute function ingest.reject_history_change();
create trigger immutable_finding_occurrence before update or delete on ingest.finding_occurrence
for each row execute function ingest.reject_history_change();

create view ingest.finding_current as
select f.*,e.status,e.priority,e.next_action,e.actor,e.note,e.event_id,e.event_seq,
       e.created_at as last_reviewed_at,
       (select count(*) from ingest.finding_occurrence o where o.finding_id=f.finding_id) as occurrence_count,
       e.status='resolved' and exists(select 1 from ingest.finding_occurrence o
          where o.finding_id=f.finding_id and o.created_at>e.created_at) as needs_revisit
from ingest.finding f join lateral
  (select * from ingest.finding_event where finding_id=f.finding_id order by event_seq desc limit 1) e on true;

create view ingest.assessment_match_summary as
select r.batch_id,r.record_id,r.raw_identifiers,r.quality_flags,
       count(c.assessment_record_id) as candidate_count,
       case when count(c.assessment_record_id)=0 then 'unmatched'
            when count(c.assessment_record_id)=1 then 'one_candidate' else 'multiple_candidates' end as match_state,
       coalesce(bool_and(c.geocode_agrees),false) as all_candidate_geocodes_agree
from ingest.source_record r left join ingest.assessment_candidate c on c.geometry_record_id=r.record_id
where r.source_id='organized-parcels' group by r.record_id;

alter table ingest.load_batch enable row level security;
alter table ingest.source_record enable row level security;
alter table ingest.assessment_candidate enable row level security;
alter table ingest.finding enable row level security;
alter table ingest.finding_event enable row level security;
alter table ingest.finding_occurrence enable row level security;
revoke all on all tables in schema ingest from public,anon,authenticated,service_role;
revoke all on all sequences in schema ingest from public,anon,authenticated,service_role;
revoke all on function ingest.decode_source_geometry(),ingest.reject_history_change() from public,anon,authenticated,service_role;
comment on table ingest.source_record is 'Selected source attributes and original assessment geometries; source/version identifiers, not legal parcel identity. Geometry validity is not boundary confidence.';
comment on table ingest.assessment_candidate is 'Exact raw identifier candidates only; zero/one/multiple matches are preserved, not certified title or canonical parcel joins.';
comment on view ingest.finding_current is 'Latest append-only follow-up event. Resolved findings with later occurrences are explicitly flagged needs_revisit.';

-- Administrative review with optimistic concurrency and replay-safe event identity.
create function ingest.record_finding_event(payload jsonb, expected_event_id text) returns void
language plpgsql set search_path=pg_catalog,ingest as $$
declare current_id text; existing jsonb;
begin
  perform 1 from ingest.finding where finding_id=payload->>'finding_id' for update;
  if not found then raise exception 'Finding does not exist'; end if;
  select to_jsonb(e)-'event_seq'-'created_at' into existing
    from ingest.finding_event e where event_id=payload->>'event_id';
  if existing is not null then
    if existing<>payload then raise exception 'Event ID reused with different content'; end if;
    return;
  end if;
  select event_id into current_id from ingest.finding_event
    where finding_id=payload->>'finding_id' order by event_seq desc limit 1;
  if current_id is distinct from expected_event_id then
    raise exception 'Finding changed since review; read current state before retrying';
  end if;
  insert into ingest.finding_event(event_id,finding_id,status,priority,next_action,actor,note,evidence_refs)
  values(payload->>'event_id',payload->>'finding_id',payload->>'status',payload->>'priority',
         payload->>'next_action',payload->>'actor',payload->>'note',payload->'evidence_refs');
end $$;
revoke all on function ingest.record_finding_event(jsonb,text) from public,anon,authenticated,service_role;
