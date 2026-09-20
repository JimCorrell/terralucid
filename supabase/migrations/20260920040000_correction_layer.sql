-- Snapshot-specific interpretation of reviewed evidence; never updates source_record.
create table ingest.correction_source (
  correction_id text primary key check (correction_id ~ '^[0-9a-f]{64}$'),
  audit_sha256 text not null references ingest.audit_result(sha256),
  source_id text not null check (source_id='organized-parcels'),
  source_snapshot_sha256 text not null check (source_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
  object_id bigint not null,
  observation_sha256 text not null references ingest.source_response(observation_sha256),
  source_feature_text text not null,
  source_feature_sha256 text not null check (source_feature_sha256 ~ '^[0-9a-f]{64}$'),
  proposal jsonb,
  holds jsonb not null,
  created_at timestamptz not null default clock_timestamp(),
  unique(audit_sha256,source_id,source_snapshot_sha256,object_id)
);

create function ingest.validate_correction_source() returns trigger
language plpgsql set search_path=pg_catalog,ingest as $$
declare report jsonb; expected jsonb; exceptions jsonb; feature jsonb; change record;
begin
  select document into strict report from ingest.audit_result where sha256=new.audit_sha256;
  feature := new.source_feature_text::jsonb;
  new.source_feature_sha256 := encode(sha256(convert_to(new.source_feature_text,'UTF8')),'hex');
  if new.source_snapshot_sha256 is distinct from report#>>'{crosswalk,source_snapshot_sha256}'
     or (feature#>>'{properties,OBJECTID}')::bigint is distinct from new.object_id then
    raise exception 'Correction source identity differs';
  end if;
  if (select count(*) from jsonb_array_elements(report#>'{crosswalk,proposals}') p
      where (p->>'object_id')::bigint=new.object_id)>1 then
    raise exception 'Ambiguous proposal';
  end if;
  select p into expected from jsonb_array_elements(report#>'{crosswalk,proposals}') p
    where (p->>'object_id')::bigint=new.object_id;
  if new.proposal is distinct from expected then raise exception 'Proposal differs from reviewed audit'; end if;
  select e->'holds' into exceptions from jsonb_array_elements(report#>'{crosswalk,exceptions}') e
    where (e->>'object_id')::bigint=new.object_id;
  if expected is null and exceptions is null then raise exception 'Record outside reviewed scope'; end if;
  if new.holds is distinct from coalesce(exceptions,'[]'::jsonb) then
    raise exception 'Exception holds differ';
  end if;
  if expected is not null then
    if expected->>'status' is distinct from 'proposed'
       or expected->>'evidence_state' is distinct from 'INFERRED'
       or expected->>'source_id' is distinct from new.source_id
       or expected->>'source_snapshot_sha256' is distinct from new.source_snapshot_sha256
       or expected->>'source_feature_sha256' is distinct from encode(sha256(convert_to(new.source_feature_text,'UTF8')),'hex')
       or expected->'holds' is distinct from new.holds
       or expected->>'global_id' is distinct from feature#>>'{properties,GlobalID}'
       or jsonb_typeof(expected->'changes') is distinct from 'object'
       or expected->'changes'='{}'::jsonb then
      raise exception 'Stale or malformed proposal';
    end if;
    for change in select * from jsonb_each(expected->'changes') loop
      if change.key not in ('GEOCODE','STATE_ID')
         or change.value->'from' is distinct from feature->'properties'->change.key
         or jsonb_typeof(change.value->'to') is distinct from 'string' then
        raise exception 'Unsupported correction or raw value differs';
      end if;
    end loop;
  end if;
  return new;
end $$;
create trigger validate_correction_source before insert on ingest.correction_source
for each row execute function ingest.validate_correction_source();
create trigger immutable_correction_source before update or delete on ingest.correction_source
for each row execute function ingest.reject_history_change();

create table ingest.correction_event (
  event_id text primary key check (event_id ~ '^[0-9a-f]{64}$'),
  event_seq bigint generated always as identity unique,
  correction_id text not null references ingest.correction_source(correction_id),
  status text not null check (status in ('accepted','revoked')),
  actor text not null check (length(btrim(actor))>0),
  note text not null check (length(btrim(note))>0),
  created_at timestamptz not null default clock_timestamp()
);
create index correction_event_latest on ingest.correction_event(correction_id,event_seq desc);
create trigger immutable_correction_event before update or delete on ingest.correction_event
for each row execute function ingest.reject_history_change();

create function ingest.record_correction_event(payload jsonb, expected_event_id text) returns void
language plpgsql set search_path=pg_catalog,ingest as $$
declare current_id text; existing jsonb; proposed jsonb;
begin
  select proposal into proposed from ingest.correction_source
    where correction_id=payload->>'correction_id' for update;
  if not found or proposed is null then raise exception 'No eligible correction proposal'; end if;
  select to_jsonb(e)-'event_seq'-'created_at' into existing from ingest.correction_event e
    where event_id=payload->>'event_id';
  if existing is not null then
    if existing<>payload then raise exception 'Event ID reused with different content'; end if;
    return;
  end if;
  select event_id into current_id from ingest.correction_event
    where correction_id=payload->>'correction_id' order by event_seq desc limit 1;
  if current_id is distinct from expected_event_id then raise exception 'Correction changed since review'; end if;
  insert into ingest.correction_event(event_id,correction_id,status,actor,note)
  values(payload->>'event_id',payload->>'correction_id',payload->>'status',payload->>'actor',payload->>'note');
end $$;

create view ingest.corrected_source as
select s.correction_id,s.audit_sha256,s.source_id,s.source_snapshot_sha256,s.object_id,
       s.observation_sha256,s.source_feature_sha256,s.source_feature_text::jsonb as raw_feature,
       coalesce(e.status,case when s.proposal is null then 'held' else 'proposed' end) as correction_status,
       e.event_id,e.actor,e.note,s.proposal,s.holds,
       s.proposal->>'evidence_state' as correction_evidence_state,
       s.source_feature_text::jsonb->'properties' ||
       case when e.status='accepted' then
         (select jsonb_object_agg(key,value->'to') from jsonb_each(s.proposal->'changes'))
       else '{}'::jsonb end as effective_properties,
       array['TL-F-0002','TL-F-0003','TL-F-0010','TL-F-0022','TL-F-0023','TL-F-0024']::text[] as related_finding_ids
from ingest.correction_source s left join lateral
  (select * from ingest.correction_event where correction_id=s.correction_id order by event_seq desc limit 1) e on true;

alter table ingest.correction_source enable row level security;
alter table ingest.correction_event enable row level security;
revoke all on ingest.correction_source,ingest.correction_event,ingest.corrected_source from public,anon,authenticated,service_role;
revoke all on sequence ingest.correction_event_event_seq_seq from public,anon,authenticated,service_role;
revoke all on function ingest.validate_correction_source(),ingest.record_correction_event(jsonb,text) from public,anon,authenticated,service_role;
comment on view ingest.corrected_source is 'Exact historical snapshot only. Accepted is workflow status, evidence remains INFERRED. All geometries remain raw assessment evidence; candidates are not canonical parcel or title links. Holds and related findings remain visible.';
