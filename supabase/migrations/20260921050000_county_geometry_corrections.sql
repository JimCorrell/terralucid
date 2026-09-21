-- Bounded activation of the three independently reviewed county interpretations.
create function ingest.county_segment_counts(rings jsonb)
returns table(a jsonb,b jsonb,n bigint) language sql immutable set search_path=pg_catalog as $$
 with points as (
  select ri,pi,p,lead(p) over(partition by ri order by pi) q
  from jsonb_array_elements(rings) with ordinality r(ring,ri),
       lateral jsonb_array_elements(ring) with ordinality v(p,pi)
 ) select least(p,q),greatest(p,q),count(*) from points where q is not null group by 1,2
$$;
create table ingest.county_geometry_correction (
 correction_id text primary key check(correction_id ~ '^[0-9a-f]{64}$'),
 source_audit_sha256 text not null,
 source_id text not null check(source_id='lupc-zoning'),
 object_id bigint not null,
 source_input_sha256 text not null,
 source_feature_text text not null,
 proposal_audit_sha256 text not null references ingest.audit_result(sha256),
 review_audit_sha256 text not null references ingest.audit_result(sha256),
 candidate_text text not null,
 candidate_sha256 text not null,
 geometry extensions.geometry(MultiPolygon,26919) not null,
 evidence_state text not null check(evidence_state='DERIVED'),
 created_at timestamptz not null default clock_timestamp(),
 foreign key(source_audit_sha256,source_id,object_id) references ingest.county_inventory_feature(audit_sha256,source_id,object_id),
 unique(source_audit_sha256,source_id,object_id)
);
create function ingest.validate_county_geometry_correction() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare old ingest.county_geometry_correction%rowtype; f ingest.county_inventory_feature%rowtype;
 p jsonb; r jsonb; pc jsonb; rc jsonb; c jsonb; rings jsonb; feature_sha text;
begin
 perform 1 from ingest.county_inventory_batch where audit_sha256=new.source_audit_sha256 for update;
 select * into old from ingest.county_geometry_correction where correction_id=new.correction_id;
 if found then
  if row(old.correction_id,old.source_audit_sha256,old.source_id,old.object_id,old.source_input_sha256,old.source_feature_text,old.proposal_audit_sha256,old.review_audit_sha256,old.candidate_text,old.candidate_sha256,old.evidence_state) is distinct from row(new.correction_id,new.source_audit_sha256,new.source_id,new.object_id,new.source_input_sha256,new.source_feature_text,new.proposal_audit_sha256,new.review_audit_sha256,new.candidate_text,new.candidate_sha256,new.evidence_state) then raise exception 'County correction replay differs';end if;
  new.geometry:=old.geometry;return new;
 end if;
 if new.source_audit_sha256<>'fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
 or new.proposal_audit_sha256<>'25f03b37818d1fc5cf25a6fa1e9264d48824c8585dbbf9776574dd6682905b6c'
 or new.review_audit_sha256<>'b7d02438499be17b55445bb5b2c5cd621cbe6f24182d238569524e0c9ab20cb7'
 or new.object_id not in (27334504,27249007,27291625) then raise exception 'Outside reviewed county cohort';end if;
 select * into strict f from ingest.county_inventory_feature where audit_sha256=new.source_audit_sha256 and source_id=new.source_id and object_id=new.object_id;
 select document into strict p from ingest.audit_result where sha256=new.proposal_audit_sha256;
 select document into strict r from ingest.audit_result where sha256=new.review_audit_sha256;
 select v into strict pc from jsonb_array_elements(p->'cases') v where (v->>'object_id')::bigint=new.object_id;
 select v into strict rc from jsonb_array_elements(r->'cases') v where (v->>'object_id')::bigint=new.object_id;
 c:=new.candidate_text::jsonb;feature_sha:=encode(sha256(convert_to(new.source_feature_text,'UTF8')),'hex');
 if f.input_sha256 is distinct from new.source_input_sha256
 or f.input_sha256 is distinct from encode(sha256(convert_to(f.input_text,'UTF8')),'hex')
 or new.source_feature_text::jsonb is distinct from f.data->'raw_feature'
 or f.data->>'hold' is null or f.geometry is not null or f.data->>'srid' is distinct from '26919'
 or p->>'county_audit_sha256' is distinct from new.source_audit_sha256
 or r->>'county_audit_sha256' is distinct from new.source_audit_sha256
 or r->>'proposal_audit_sha256' is distinct from new.proposal_audit_sha256
 or pc->>'county_feature_sha256' is distinct from feature_sha
 or rc->>'source_feature_sha256' is distinct from feature_sha
 or pc->>'status' is distinct from 'proposed_not_accepted'
 or rc->>'recommendation' is distinct from 'supported_for_exact_version_acceptance'
 or rc#>'{checks,equals_independent_even_odd_fill}' is distinct from 'true'::jsonb
 or rc#>'{checks,all_segments_preserved_with_multiplicity}' is distinct from 'true'::jsonb
 or rc#>'{checks,symmetric_difference_m2}' is distinct from '0'::jsonb
 or new.candidate_sha256 is distinct from encode(sha256(convert_to(new.candidate_text,'UTF8')),'hex')
 or pc->>'candidate_sha256' is distinct from new.candidate_sha256
 or rc->>'candidate_sha256' is distinct from new.candidate_sha256
 or c#>>'{properties,source_feature_sha256}' is distinct from feature_sha
 or c#>>'{properties,county_audit_sha256}' is distinct from new.source_audit_sha256
 or c#>>'{properties,object_id}' is distinct from new.object_id::text
 or c#>>'{properties,status}' is distinct from 'proposed_not_accepted'
 or c#>>'{properties,evidence_state}' is distinct from 'DERIVED'
 or c#>>'{crs,properties,name}' is distinct from 'EPSG:26919'
 or c#>>'{geometry,type}' is distinct from 'MultiPolygon'
 or new.correction_id is distinct from encode(sha256(convert_to(new.source_audit_sha256||':'||new.source_id||':'||new.object_id::text||':'||new.candidate_sha256,'UTF8')),'hex')
 then raise exception 'County correction differs from exact reviewed source/candidate';end if;
 new.geometry:=ST_SetSRID(ST_GeomFromGeoJSON((c->'geometry')::text),26919);
 if new.geometry is null or ST_IsEmpty(new.geometry) or not ST_IsValid(new.geometry) then raise exception 'Invalid county candidate';end if;
 select jsonb_agg(ring) into rings from jsonb_array_elements(c#>'{geometry,coordinates}') poly,
 lateral jsonb_array_elements(poly) ring;
 if exists((select * from ingest.county_segment_counts(f.data#>'{raw_feature,geometry,rings}') except select * from ingest.county_segment_counts(rings))
 union all (select * from ingest.county_segment_counts(rings) except select * from ingest.county_segment_counts(f.data#>'{raw_feature,geometry,rings}'))) then
 raise exception 'County candidate changes source segments';end if;
 return new;
end $$;
create trigger validate_county_geometry_correction before insert on ingest.county_geometry_correction for each row execute function ingest.validate_county_geometry_correction();
create trigger immutable_county_geometry_correction before update or delete on ingest.county_geometry_correction for each row execute function ingest.reject_history_change();

create sequence ingest.county_geometry_event_event_seq_seq;
create table ingest.county_geometry_event (
 event_id text primary key check(event_id ~ '^[0-9a-f]{64}$'),
 event_seq bigint not null unique,
 correction_id text not null references ingest.county_geometry_correction(correction_id),
 expected_event_id text,
 status text not null check(status in ('accepted','withdrawn')),
 actor text not null check(length(btrim(actor))>0),
 note text not null check(length(btrim(note))>0),
 created_at timestamptz not null default clock_timestamp()
);
create index county_geometry_event_latest on ingest.county_geometry_event(correction_id,event_seq desc);
create function ingest.validate_county_geometry_event() returns trigger language plpgsql set search_path=pg_catalog,ingest as $$
declare source_audit text; current_id text; old ingest.county_geometry_event%rowtype;
begin
 select source_audit_sha256 into strict source_audit from ingest.county_geometry_correction where correction_id=new.correction_id;
 perform 1 from ingest.county_inventory_batch where audit_sha256=source_audit for update;
 select * into old from ingest.county_geometry_event where event_id=new.event_id;
 if found then
  if to_jsonb(old)-'event_seq'-'created_at' is distinct from to_jsonb(new)-'event_seq'-'created_at' then raise exception 'County event ID reused';end if;
  new.event_seq:=old.event_seq;return new;
 end if;
 select event_id into current_id from ingest.county_geometry_event where correction_id=new.correction_id order by event_seq desc limit 1;
 if current_id is distinct from new.expected_event_id then raise exception 'County geometry review changed';end if;
 -- Allocate after the batch lock: sequence order must follow serialized review order.
 new.event_seq:=nextval('ingest.county_geometry_event_event_seq_seq');
 return new;
end $$;
create trigger validate_county_geometry_event before insert on ingest.county_geometry_event for each row execute function ingest.validate_county_geometry_event();
create trigger immutable_county_geometry_event before update or delete on ingest.county_geometry_event for each row execute function ingest.reject_history_change();
create function ingest.record_county_geometry_event(payload jsonb,expected_event_id text) returns text language plpgsql set search_path=pg_catalog,ingest as $$
begin
 if (select count(*) from jsonb_object_keys(payload))<>5 or not payload ?& array['event_id','correction_id','status','actor','note'] then raise exception 'Unexpected county event fields';end if;
 insert into ingest.county_geometry_event(event_id,correction_id,expected_event_id,status,actor,note)
 values(payload->>'event_id',payload->>'correction_id',expected_event_id,payload->>'status',payload->>'actor',payload->>'note') on conflict(event_id) do nothing;
 return payload->>'event_id';
end $$;
create view ingest.county_geometry_current as
 select c.*,e.event_id as geometry_event_id,coalesce(e.status,'proposed') as correction_status
 from ingest.county_geometry_correction c left join lateral(
 select event_id,status from ingest.county_geometry_event where correction_id=c.correction_id order by event_seq desc limit 1)e on true;
create view ingest.effective_county_inventory as
 select f.audit_sha256,f.source_id,f.object_id,f.input_sha256,f.data->'attributes' as source_attributes,
 f.geometry as original_geometry,f.data->>'hold' as original_geometry_hold,f.data->>'scope_relation' as original_scope_relation,
 case when c.correction_status='accepted' then c.geometry else f.geometry end as effective_geometry,
 case when c.correction_status='accepted' then null else f.data->>'hold' end as effective_geometry_hold,
 case when c.correction_status='accepted' then case when not extensions.ST_Intersects(c.geometry,b.boundary) then 'outside'
 when extensions.ST_Touches(c.geometry,b.boundary) then 'touch' else 'interior' end else f.data->>'scope_relation' end as effective_scope_relation,
 f.data->'quality_flags' as original_quality_flags,
 case when c.correction_status='accepted' then (f.data->'quality_flags')-'geometry_held' else f.data->'quality_flags' end as effective_quality_flags,
 f.data->'provenance' as provenance,c.correction_id,c.proposal_audit_sha256,c.review_audit_sha256,c.candidate_sha256,c.geometry_event_id,
 coalesce(c.correction_status,'original') as correction_status,
 'DERIVED'::text as geometry_evidence_state,'UNKNOWN'::text as legal_boundary_state,false as qualified_for_parcel_screening
 from ingest.county_inventory_feature f join ingest.county_inventory_batch b on b.audit_sha256=f.audit_sha256
 left join ingest.county_geometry_current c on c.source_audit_sha256=f.audit_sha256 and c.source_id=f.source_id and c.object_id=f.object_id and c.source_input_sha256=f.input_sha256;

create function ingest.county_geometry_dependencies(source_audit text) returns jsonb language sql stable set search_path=pg_catalog,ingest as $$
 select coalesce(jsonb_object_agg(correction_id,jsonb_build_object('event_id',geometry_event_id,'status',correction_status,'candidate_sha256',candidate_sha256,'source_input_sha256',source_input_sha256)),'{}'::jsonb)
 from ingest.county_geometry_current where source_audit_sha256=source_audit
$$;
create table ingest.county_geometry_snapshot (
 snapshot_id text primary key,
 source_audit_sha256 text not null references ingest.county_inventory_batch(audit_sha256),
 dependencies jsonb not null check(jsonb_typeof(dependencies)='object'),
 created_at timestamptz not null default clock_timestamp()
);
create function ingest.validate_county_geometry_snapshot() returns trigger language plpgsql set search_path=pg_catalog,ingest as $$
declare old ingest.county_geometry_snapshot%rowtype;
begin
 perform 1 from ingest.county_inventory_batch where audit_sha256=new.source_audit_sha256 for share;
 select * into old from ingest.county_geometry_snapshot where snapshot_id=new.snapshot_id;
 if found then
  if to_jsonb(old)-'created_at' is distinct from to_jsonb(new)-'created_at' then raise exception 'County snapshot replay differs';end if;
  return new;
 end if;
 if new.dependencies is distinct from ingest.county_geometry_dependencies(new.source_audit_sha256)
 or new.snapshot_id is distinct from encode(sha256(convert_to(new.source_audit_sha256||':'||new.dependencies::text,'UTF8')),'hex') then raise exception 'County dependencies changed';end if;
 return new;
end $$;
create trigger validate_county_geometry_snapshot before insert on ingest.county_geometry_snapshot for each row execute function ingest.validate_county_geometry_snapshot();
create trigger immutable_county_geometry_snapshot before update or delete on ingest.county_geometry_snapshot for each row execute function ingest.reject_history_change();
create function ingest.record_county_geometry_snapshot(source_audit text) returns text language plpgsql set search_path=pg_catalog,ingest as $$
declare d jsonb; sid text;
begin
 perform 1 from ingest.county_inventory_batch where audit_sha256=source_audit for share;
 if not found then raise exception 'Unknown county source audit';end if;
 d:=ingest.county_geometry_dependencies(source_audit);sid:=encode(sha256(convert_to(source_audit||':'||d::text,'UTF8')),'hex');
 insert into ingest.county_geometry_snapshot(snapshot_id,source_audit_sha256,dependencies) values(sid,source_audit,d) on conflict do nothing;
 return sid;
end $$;
create view ingest.county_geometry_snapshot_current as
 select s.*,s.dependencies is distinct from ingest.county_geometry_dependencies(s.source_audit_sha256) as needs_revisit from ingest.county_geometry_snapshot s;
create function ingest.county_geometry_snapshot_is_current(sid text,intended_source_audit text) returns boolean language sql stable set search_path=pg_catalog,ingest as $$
 select exists(select 1 from ingest.county_geometry_snapshot_current where snapshot_id=sid and source_audit_sha256=intended_source_audit and not needs_revisit)
$$;
alter table ingest.county_geometry_correction enable row level security;
alter table ingest.county_geometry_event enable row level security;
alter table ingest.county_geometry_snapshot enable row level security;
revoke all on ingest.county_geometry_correction,ingest.county_geometry_event,ingest.county_geometry_snapshot,ingest.county_geometry_current,ingest.effective_county_inventory,ingest.county_geometry_snapshot_current from public,anon,authenticated,service_role;
revoke all on sequence ingest.county_geometry_event_event_seq_seq from public,anon,authenticated,service_role;
revoke all on function ingest.county_segment_counts(jsonb),ingest.validate_county_geometry_correction(),ingest.validate_county_geometry_event(),ingest.record_county_geometry_event(jsonb,text),ingest.county_geometry_dependencies(text),ingest.validate_county_geometry_snapshot(),ingest.record_county_geometry_snapshot(text),ingest.county_geometry_snapshot_is_current(text,text) from public,anon,authenticated,service_role;
