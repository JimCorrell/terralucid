-- County source inventory, separate from accepted Osborn corrections and screenings.
create table ingest.county_inventory_batch (
 audit_sha256 text primary key references ingest.audit_result(sha256),
 boundary extensions.geometry(MultiPolygon,26919) not null,
 loaded_xid xid8 not null default pg_current_xact_id(),
 created_at timestamptz not null default clock_timestamp()
);
create table ingest.county_inventory_feature (
 audit_sha256 text not null references ingest.county_inventory_batch(audit_sha256),
 source_id text not null,
 object_id bigint not null,
 input_text text not null,
 input_sha256 text not null,
 data jsonb not null,
 geometry extensions.geometry(Geometry),
 primary key(audit_sha256,source_id,object_id)
);
create index county_inventory_geometry on ingest.county_inventory_feature using gist(geometry);
create function ingest.validate_county_inventory_batch() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare a jsonb;
begin
 select document into strict a from ingest.audit_result where sha256=new.audit_sha256;
 if a->>'method' is distinct from 'scripts/prepare_piscataquis.py'
 or a->>'scope' is distinct from 'Piscataquis County, Maine'
 then raise exception 'Unreviewed county inventory method or scope';end if;
 new.boundary:=ST_Multi(ST_GeomFromWKB(decode(a#>>'{boundary,wkb_hex}','hex'),26919));
 if not ST_IsValid(new.boundary) or ST_IsEmpty(new.boundary) then raise exception 'Unusable county boundary';end if;
 new.loaded_xid:=pg_current_xact_id();
 return new;
end $$;
create trigger validate_county_inventory_batch before insert on ingest.county_inventory_batch for each row execute function ingest.validate_county_inventory_batch();
create function ingest.validate_county_inventory_feature() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare old ingest.county_inventory_feature%rowtype; b ingest.county_inventory_batch%rowtype; sr integer;
begin
 select * into old from ingest.county_inventory_feature where audit_sha256=new.audit_sha256 and source_id=new.source_id and object_id=new.object_id;
 if found then
  if old.input_text is distinct from new.input_text then raise exception 'County feature replay differs';end if;
  new.data:=old.data;new.geometry:=old.geometry;new.input_sha256:=old.input_sha256;return new;
 end if;
 select * into strict b from ingest.county_inventory_batch where audit_sha256=new.audit_sha256;
 if b.loaded_xid<>pg_current_xact_id() then raise exception 'County batch is sealed; use a new audit';end if;
 new.data:=new.input_text::jsonb;new.input_sha256:=encode(sha256(convert_to(new.input_text,'UTF8')),'hex');
 if new.data->>'source_id' is distinct from new.source_id or new.data->>'object_id' is distinct from new.object_id::text
 or new.data#>>'{attributes,OBJECTID}' is distinct from new.object_id::text
 or new.source_id not in ('civil-boundaries','ut-parcels','organized-parcels','lupc-zoning','nwi-package','nwi-project')
 or new.data->>'scope_relation' is null or new.data->>'scope_relation' not in ('interior','touch','outside','held')
 then raise exception 'County feature identity/scope differs';end if;
 if new.source_id not in ('nwi-package','nwi-project') then
  perform 1 from ingest.source_response where observation_sha256=new.data#>>'{provenance,observation_sha256}'
   and payload_sha256=new.data#>>'{provenance,response_sha256}' and new.source_id=any(source_ids);
  if not found then raise exception 'Missing source observation';end if;
 end if;
 sr:=case when new.source_id in ('nwi-package','nwi-project') then 5070 else 26919 end;
 if new.data->>'srid' is distinct from sr::text then raise exception 'Unexpected native CRS';end if;
 if new.data->>'hold' is not null then
  if new.data->>'wkb_hex' is not null or new.data->>'scope_relation'<>'held' then raise exception 'Held geometry cannot be used';end if;
  new.geometry:=null;
 else
  new.geometry:=ST_GeomFromWKB(decode(new.data->>'wkb_hex','hex'),sr);
  if new.geometry is null or ST_IsEmpty(new.geometry) or not ST_IsValid(new.geometry)
   or GeometryType(new.geometry) not in ('POLYGON','MULTIPOLYGON') then raise exception 'Unusable decoded geometry';end if;
 end if;
 return new;
end $$;
create trigger validate_county_inventory_feature before insert on ingest.county_inventory_feature for each row execute function ingest.validate_county_inventory_feature();
create function ingest.require_complete_county_inventory() returns trigger language plpgsql
set search_path=pg_catalog,ingest as $$
declare expected jsonb; actual jsonb;
begin
 select document->'record_manifest' into strict expected from ingest.audit_result where sha256=new.audit_sha256;
 select jsonb_object_agg(source_id,jsonb_build_object('count',n,'sha256',h)) into actual from
 (select source_id,count(*) n,encode(sha256(convert_to(string_agg(object_id::text||':'||input_sha256||E'\n','' order by object_id),'UTF8')),'hex') h
  from ingest.county_inventory_feature where audit_sha256=new.audit_sha256 group by source_id) s;
 if expected is distinct from actual then raise exception 'Incomplete or changed county inventory';end if;
 return new;
end $$;
create constraint trigger complete_county_inventory after insert on ingest.county_inventory_batch deferrable initially deferred for each row execute function ingest.require_complete_county_inventory();
create trigger immutable_county_inventory_batch before update or delete on ingest.county_inventory_batch for each row execute function ingest.reject_history_change();
create trigger immutable_county_inventory_feature before update or delete on ingest.county_inventory_feature for each row execute function ingest.reject_history_change();
create view ingest.county_inventory as
 select f.audit_sha256,f.source_id,f.object_id,f.data->'attributes' as source_attributes,f.geometry,
 f.data->>'scope_relation' as scope_relation,f.data->>'hold' as geometry_hold,
 f.data->'provenance' as provenance,f.data->'quality_flags' as quality_flags,
 'DERIVED'::text as geometry_evidence_state,'UNKNOWN'::text as legal_boundary_state,
 false as qualified_for_parcel_screening
 from ingest.county_inventory_feature f;
alter table ingest.county_inventory_batch enable row level security;
alter table ingest.county_inventory_feature enable row level security;
revoke all on ingest.county_inventory_batch,ingest.county_inventory_feature,ingest.county_inventory from public,anon,authenticated,service_role;
revoke all on function ingest.validate_county_inventory_batch(),ingest.validate_county_inventory_feature(),ingest.require_complete_county_inventory() from public,anon,authenticated,service_role;
comment on view ingest.county_inventory is 'Filter by audit and scope_relation. Raw source inventory, not a replacement for accepted corrections or qualified screenings. Native CRS and unresolved geometry/coverage/legal holds remain explicit.';
