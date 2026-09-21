-- Bounded historical service inventory, not legal wetlands or canonical parcels.
create table ingest.wetlands_batch (
 audit_sha256 text primary key references ingest.audit_result(sha256),
 source_audit_sha256 text not null references ingest.audit_result(sha256),
 classification_audit_sha256 text not null references ingest.audit_result(sha256),
 classification_event_id text not null references ingest.finding_event(event_id),
 availability_result_id text not null references ingest.availability_coverage(result_id),
 created_at timestamptz not null default clock_timestamp()
);
create function ingest.validate_wetlands_batch() returns trigger language plpgsql
set search_path=pg_catalog,ingest as $$
declare old ingest.wetlands_batch%rowtype; a jsonb; f ingest.finding_current%rowtype;
begin
 select * into old from ingest.wetlands_batch where audit_sha256=new.audit_sha256;
 if found then
  if to_jsonb(old)-'created_at' is distinct from to_jsonb(new)-'created_at' then raise exception 'Wetlands batch replay differs';end if;
  return new;
 end if;
 select document into strict a from ingest.audit_result where sha256=new.audit_sha256;
 if new.source_audit_sha256<>'e1449e8384d5d712dfdae9df26814330d1b9f7dc31ae82fc8765bce565b61906'
 or new.classification_audit_sha256<>'a1fd940a039662c703ec254963e70cd245f0632c970a62748591e5136f261c12'
 or new.classification_event_id<>'560e8844f3aef6c1b716524080d285790510924422df5db0ba3ae94de7019f48'
 or new.availability_result_id<>'9874844cb3788a81be34652585b6ffb70c57286d56b7959741dc660bca5ac07b'
 or a->>'method' is distinct from 'scripts/prepare_wetlands_load.py'
 or a->>'source_audit_sha256' is distinct from new.source_audit_sha256
 or a->>'classification_audit_sha256' is distinct from new.classification_audit_sha256
 or a->>'classification_event_id' is distinct from new.classification_event_id
 or a->>'availability_coverage_result_id' is distinct from new.availability_result_id
 or a#>>'{summary,features}' is distinct from '669' then raise exception 'Unreviewed wetlands load dependencies';end if;
 -- Serialize against normal review operations; hold through transaction commit.
 perform 1 from ingest.finding where finding_id='TL-F-0027' for share;
 perform 1 from ingest.availability_geometry g join ingest.availability_coverage c using(correction_id)
 where c.result_id=new.availability_result_id for share of g;
 select * into strict f from ingest.finding_current where finding_id='TL-F-0027';
 if f.event_id is distinct from new.classification_event_id or f.status<>'resolved' or f.needs_revisit
 or not exists(select 1 from ingest.availability_coverage_current where result_id=new.availability_result_id and not needs_revisit)
 then raise exception 'Wetlands interpretation dependencies need review';end if;
 return new;
end $$;
create trigger validate_wetlands_batch before insert on ingest.wetlands_batch for each row execute function ingest.validate_wetlands_batch();
create trigger immutable_wetlands_batch before update or delete on ingest.wetlands_batch for each row execute function ingest.reject_history_change();

create table ingest.wetlands_feature (
 audit_sha256 text not null references ingest.wetlands_batch(audit_sha256),
 object_id bigint not null,
 input_text text not null,
 input_sha256 text not null,
 data jsonb not null,
 geometry extensions.geometry(MultiPolygon,3857) not null,
 primary key(audit_sha256,object_id)
);
create index wetlands_feature_geometry on ingest.wetlands_feature using gist(geometry);
create function ingest.validate_wetlands_feature() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare old ingest.wetlands_feature%rowtype; a jsonb; b ingest.wetlands_batch%rowtype; o jsonb; r jsonb;
begin
 select * into old from ingest.wetlands_feature where audit_sha256=new.audit_sha256 and object_id=new.object_id;
 if found then
  if old.input_text is distinct from new.input_text then raise exception 'Wetlands feature replay differs';end if;
  new.input_sha256:=old.input_sha256;new.data:=old.data;new.geometry:=old.geometry;return new;
 end if;
 select * into strict b from ingest.wetlands_batch where audit_sha256=new.audit_sha256;
 select document into strict a from ingest.audit_result where sha256=new.audit_sha256;
 new.input_sha256:=encode(sha256(convert_to(new.input_text,'UTF8')),'hex');new.data:=new.input_text::jsonb;
 if a#>>array['feature_sha256',new.object_id::text] is distinct from new.input_sha256
 or new.data->>'object_id' is distinct from new.object_id::text
 or new.data#>>'{native_core,attributes,Wetlands.OBJECTID}' is distinct from new.object_id::text
 then raise exception 'Wetlands feature differs from audited manifest';end if;
 for o in select * from jsonb_array_elements(new.data->'source_occurrences') loop
  if not exists(select 1 from ingest.source_response s join ingest.audit_result ar on ar.registry_sha256=s.registry_sha256
   where ar.sha256=b.source_audit_sha256 and s.observation_sha256=o->>'observation_sha256' and s.payload_sha256=o->>'payload_sha256')
  then raise exception 'Missing source observation';end if;
 end loop;
 if new.data->>'interpretation'='reviewed_reference_match' then
  select x into strict r from ingest.audit_result ar,jsonb_array_elements(ar.document->'records') x
   where ar.sha256=b.classification_audit_sha256 and x->>'service_objectid'=new.object_id::text;
  if r is distinct from new.data->'review' or r->>'native_core_sha256' is distinct from new.data->>'native_core_sha256'
  or new.data->'effective_lookup' is distinct from new.data#>array['lookup_variants',r->>'selected_lookup_sha256']
  then raise exception 'Reviewed classification differs';end if;
 elsif new.data->>'interpretation'='source_single_variant' then
  if (select count(*) from jsonb_object_keys(new.data->'lookup_variants'))<>1
  or not exists(select 1 from jsonb_each(new.data->'lookup_variants') v where v.value=new.data->'effective_lookup')
  then raise exception 'Unreviewed classification ambiguity';end if;
 else raise exception 'Unknown interpretation';end if;
 new.geometry:=ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON((new.data->'geometry_geojson')::text),3857));
 if ST_IsEmpty(new.geometry) or not ST_IsValid(new.geometry) then raise exception 'Invalid wetlands geometry; no repair';end if;
 return new;
end $$;
create trigger validate_wetlands_feature before insert on ingest.wetlands_feature for each row execute function ingest.validate_wetlands_feature();
create trigger immutable_wetlands_feature before update or delete on ingest.wetlands_feature for each row execute function ingest.reject_history_change();

create function ingest.assert_wetlands_batch(batch text) returns void language plpgsql
set search_path=pg_catalog,ingest as $$
declare a jsonb;
begin
 select document into strict a from ingest.audit_result where sha256=batch;
 if (select count(*) from ingest.wetlands_feature where audit_sha256=batch)<>669
 or (select count(*) from jsonb_object_keys(a->'feature_sha256'))<>669
 or (select sum(jsonb_array_length(data->'source_occurrences')) from ingest.wetlands_feature where audit_sha256=batch)<>679
 or (select count(*) from ingest.wetlands_feature f,jsonb_object_keys(data->'lookup_variants') where audit_sha256=batch)<>677
 or (select count(*) from ingest.wetlands_feature where audit_sha256=batch and data->>'interpretation'='reviewed_reference_match')<>8
 then raise exception 'Wetlands load is incomplete';end if;
end $$;

create function ingest.require_complete_wetlands_batch() returns trigger language plpgsql
set search_path=pg_catalog,ingest as $$
begin
 perform ingest.assert_wetlands_batch(new.audit_sha256);return new;
end $$;
create constraint trigger complete_wetlands_batch after insert on ingest.wetlands_batch
 deferrable initially deferred for each row execute function ingest.require_complete_wetlands_batch();

create view ingest.wetlands_feature_current as
select w.audit_sha256,b.source_audit_sha256,w.object_id,
 w.data#>>'{native_core,attributes,Wetlands.GLOBALID}' as source_globalid,
 w.data#>>'{native_core,attributes,Wetlands.ATTRIBUTE}' as code,
 w.data#>>'{native_core,attributes,Wetlands.WETLAND_TYPE}' as wetland_type,
 w.geometry,w.data->'native_core' as native_core,w.data->'lookup_variants' as lookup_variants,
 w.data->'source_occurrences' as source_occurrences,w.data->>'interpretation' as interpretation,
 w.data->'effective_lookup' as reviewed_lookup,
 case when w.data->>'interpretation'='reviewed_reference_match' and
  (f.event_id is distinct from b.classification_event_id or f.status is distinct from 'resolved' or coalesce(f.needs_revisit,true))
 then null else w.data->'effective_lookup' end as effective_lookup,
 w.data->'prior_profile' as prior_qualification_profile,
 'DERIVED'::text as evidence_state,a.document->'limits' as limits,
 b.classification_audit_sha256,b.classification_event_id,b.availability_result_id,
 coalesce(c.needs_revisit,true) as availability_needs_revisit,
 w.data->>'interpretation'='reviewed_reference_match' and
  (f.event_id is distinct from b.classification_event_id or f.status is distinct from 'resolved' or coalesce(f.needs_revisit,true)) as classification_needs_revisit,
 coalesce(c.needs_revisit,true) or (w.data->>'interpretation'='reviewed_reference_match' and
  (f.event_id is distinct from b.classification_event_id or f.status is distinct from 'resolved' or coalesce(f.needs_revisit,true))) as needs_revisit
from ingest.wetlands_feature w join ingest.wetlands_batch b using(audit_sha256)
join ingest.audit_result a on a.sha256=w.audit_sha256
left join ingest.finding_current f on f.finding_id='TL-F-0027'
left join ingest.availability_coverage_current c on c.result_id=b.availability_result_id;

alter table ingest.wetlands_batch enable row level security;
alter table ingest.wetlands_feature enable row level security;
revoke all on ingest.wetlands_batch,ingest.wetlands_feature,ingest.wetlands_feature_current from public,anon,authenticated,service_role;
revoke all on function ingest.validate_wetlands_batch(),ingest.validate_wetlands_feature(),ingest.assert_wetlands_batch(text),ingest.require_complete_wetlands_batch() from public,anon,authenticated,service_role;
