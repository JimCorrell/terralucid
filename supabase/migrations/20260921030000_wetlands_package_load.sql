-- Independent bounded package records; links are inferred, never replacements.
create table ingest.wetlands_package_batch (
 audit_sha256 text primary key references ingest.audit_result(sha256),
 comparison_audit_sha256 text not null references ingest.audit_result(sha256),
 service_audit_sha256 text not null references ingest.wetlands_batch(audit_sha256),
 created_at timestamptz not null default clock_timestamp()
);
create function ingest.validate_wetlands_package_batch() returns trigger language plpgsql
set search_path=pg_catalog,ingest as $$
declare a jsonb; old ingest.wetlands_package_batch%rowtype;
begin
 select * into old from ingest.wetlands_package_batch where audit_sha256=new.audit_sha256;
 if found then
  if to_jsonb(old)-'created_at' is distinct from to_jsonb(new)-'created_at' then raise exception 'Package batch replay differs';end if;return new;
 end if;
 select document into strict a from ingest.audit_result where sha256=new.audit_sha256;
 if new.comparison_audit_sha256<>'076cb7321ad0b8cad052a4bf51a18028413b88e788082ddbc347158919ec18ed'
 or new.service_audit_sha256<>'5802819c4376110fcac2a58b3bdf652e82524472ae15ba62913a4375551f3d39'
 or a->>'comparison_audit_sha256' is distinct from new.comparison_audit_sha256
 or a->>'service_audit_sha256' is distinct from new.service_audit_sha256
 or a->>'method' is distinct from 'scripts/prepare_wetlands_package_load.py'
 or a#>>'{package,sha256}' is distinct from 'ae1332336dbe5b6d255c29d75134c2959370ce9aa43c94fc2abb413475f1dcd1'
 or a#>>'{package,extracted,sha256}' is distinct from 'a224dc073dc87b1a6fccead6f8701304aa67cf734cd351b7e5fc28c2c3b2018f'
 then raise exception 'Unreviewed package dependencies';end if;
 perform 1 from ingest.finding where finding_id='TL-F-0027' for share;
 perform 1 from ingest.availability_geometry g join ingest.availability_coverage c using(correction_id)
 join ingest.wetlands_batch b on b.availability_result_id=c.result_id where b.audit_sha256=new.service_audit_sha256 for share of g;
 if (select count(*) from ingest.wetlands_feature_current where audit_sha256=new.service_audit_sha256 and not needs_revisit)<>669 then raise exception 'Service dependencies require review';end if;
 return new;
end $$;
create trigger validate_wetlands_package_batch before insert on ingest.wetlands_package_batch for each row execute function ingest.validate_wetlands_package_batch();
create trigger immutable_wetlands_package_batch before update or delete on ingest.wetlands_package_batch for each row execute function ingest.reject_history_change();

create table ingest.wetlands_package_feature (
 audit_sha256 text not null references ingest.wetlands_package_batch(audit_sha256),
 object_id bigint not null,
 service_audit_sha256 text not null,
 service_object_id bigint not null,
 input_text text not null,
 input_sha256 text not null,
 data jsonb not null,
 geometry_blob bytea not null,
 geometry extensions.geometry(MultiPolygon,5070) not null,
 primary key(audit_sha256,object_id),
 unique(audit_sha256,service_object_id),
 foreign key(service_audit_sha256,service_object_id) references ingest.wetlands_feature(audit_sha256,object_id)
);
create index wetlands_package_geometry on ingest.wetlands_package_feature using gist(geometry);
create function ingest.validate_wetlands_package_feature() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare old ingest.wetlands_package_feature%rowtype; a jsonb; b ingest.wetlands_package_batch%rowtype; s ingest.wetlands_feature%rowtype;
begin
 select * into old from ingest.wetlands_package_feature where audit_sha256=new.audit_sha256 and object_id=new.object_id;
 if found then
  if old.input_text is distinct from new.input_text or old.service_audit_sha256 is distinct from new.service_audit_sha256 or old.service_object_id is distinct from new.service_object_id then raise exception 'Package feature replay differs';end if;
  new.input_sha256:=old.input_sha256;new.data:=old.data;new.geometry_blob:=old.geometry_blob;new.geometry:=old.geometry;return new;
 end if;
 select * into strict b from ingest.wetlands_package_batch where audit_sha256=new.audit_sha256;
 select document into strict a from ingest.audit_result where sha256=new.audit_sha256;
 new.data:=new.input_text::jsonb;new.input_sha256:=encode(sha256(convert_to(new.input_text,'UTF8')),'hex');
 if a#>>array['feature_sha256',new.object_id::text] is distinct from new.input_sha256
 or new.data->>'object_id' is distinct from new.object_id::text
 or new.data#>>'{attributes,OBJECTID}' is distinct from new.object_id::text
 or new.data->>'service_object_id' is distinct from new.service_object_id::text
 or new.service_audit_sha256 is distinct from b.service_audit_sha256
 or new.data->>'identity_state' is distinct from 'INFERRED' then raise exception 'Package feature differs from manifest';end if;
 select * into strict s from ingest.wetlands_feature where audit_sha256=new.service_audit_sha256 and object_id=new.service_object_id;
 if new.data->>'service_feature_sha256' is distinct from s.input_sha256
 or new.data#>>'{attributes,ATTRIBUTE}' is distinct from s.data#>>'{native_core,attributes,Wetlands.ATTRIBUTE}'
 or new.data#>>'{attributes,WETLAND_TYPE}' is distinct from s.data#>>'{native_core,attributes,Wetlands.WETLAND_TYPE}' then raise exception 'Service candidate differs';end if;
 new.geometry_blob:=decode(new.data->>'geometry_blob_hex','hex');
 if encode(sha256(new.geometry_blob),'hex') is distinct from new.data->>'geometry_blob_sha256'
 or substring(new.geometry_blob from 1 for 2)<>decode('4750','hex') or get_byte(new.geometry_blob,2)<>0
 or get_byte(new.geometry_blob,3)<>1
 or get_byte(new.geometry_blob,4)+256*get_byte(new.geometry_blob,5)+65536*get_byte(new.geometry_blob,6)+16777216::bigint*get_byte(new.geometry_blob,7)<>300001
 then raise exception 'Unexpected package geometry header/checksum';end if;
 -- Reviewed header flag 1: little endian, no envelope; 8-byte header. Preserve blob.
 new.geometry:=ST_Multi(ST_SetSRID(ST_GeomFromWKB(substring(new.geometry_blob from 9)),5070));
 if ST_IsEmpty(new.geometry) or not ST_IsValid(new.geometry) then raise exception 'Invalid native package geometry';end if;
 return new;
end $$;
create trigger validate_wetlands_package_feature before insert on ingest.wetlands_package_feature for each row execute function ingest.validate_wetlands_package_feature();
create trigger immutable_wetlands_package_feature before update or delete on ingest.wetlands_package_feature for each row execute function ingest.reject_history_change();
create function ingest.require_complete_wetlands_package() returns trigger language plpgsql
set search_path=pg_catalog,ingest as $$
begin
 if (select count(*) from ingest.wetlands_package_feature where audit_sha256=new.audit_sha256)<>669
 or (select count(*) from ingest.audit_result a,jsonb_object_keys(a.document->'feature_sha256') where a.sha256=new.audit_sha256)<>669 then raise exception 'Incomplete package batch';end if;
 return new;
end $$;
create constraint trigger complete_wetlands_package after insert on ingest.wetlands_package_batch deferrable initially deferred for each row execute function ingest.require_complete_wetlands_package();
create view ingest.wetlands_package_current as
select p.audit_sha256,p.object_id,p.data->'attributes' as source_attributes,p.geometry,p.data->>'geometry_blob_sha256' as geometry_blob_sha256,
 p.service_audit_sha256,p.service_object_id,'INFERRED'::text as identity_state,'DERIVED'::text as geometry_evidence_state,
 p.data->'comparison_metrics' as comparison_metrics,b.comparison_audit_sha256,a.document->'limits' as limits,
 s.classification_event_id,s.availability_result_id,s.effective_lookup as candidate_service_effective_lookup,
 coalesce(s.needs_revisit,true) as needs_revisit
from ingest.wetlands_package_feature p join ingest.wetlands_package_batch b using(audit_sha256)
join ingest.audit_result a on a.sha256=p.audit_sha256
left join ingest.wetlands_feature_current s on s.audit_sha256=p.service_audit_sha256 and s.object_id=p.service_object_id;
alter table ingest.wetlands_package_batch enable row level security;
alter table ingest.wetlands_package_feature enable row level security;
revoke all on ingest.wetlands_package_batch,ingest.wetlands_package_feature,ingest.wetlands_package_current from public,anon,authenticated,service_role;
revoke all on function ingest.validate_wetlands_package_batch(),ingest.validate_wetlands_package_feature(),ingest.require_complete_wetlands_package() from public,anon,authenticated,service_role;
