-- Run only in a disposable database after the authentic county load and replay.
begin;
do $$
declare a text; r ingest.county_inventory_feature%rowtype; blocked boolean; n bigint;
begin
 select audit_sha256 into strict a from ingest.county_inventory_batch;
 select * into strict r from ingest.county_inventory_feature where audit_sha256=a order by source_id,object_id limit 1;
 if (select count(*) from ingest.county_inventory_batch)<>1 then raise exception 'Replay duplicated batch';end if;
 if exists(select 1 from ingest.county_inventory_feature where audit_sha256=a and
  ((data->>'hold' is not null and geometry is not null) or
   (data->>'hold' is null and (geometry is null or not extensions.ST_IsValid(geometry))))) then raise exception 'Geometry hold bypass';end if;
 if has_table_privilege('anon','ingest.county_inventory_feature','select')
 or has_table_privilege('authenticated','ingest.county_inventory','select')
 or not (select relrowsecurity from pg_class where oid='ingest.county_inventory_feature'::regclass)
 then raise exception 'Private inventory exposed';end if;
 blocked:=false;
 begin
  insert into ingest.county_inventory_feature(audit_sha256,source_id,object_id,input_text)
  values(a,r.source_id,r.object_id,r.input_text||' ') on conflict do nothing;
 exception when others then blocked:=SQLERRM='County feature replay differs';end;
 if not blocked then raise exception 'Changed replay accepted';end if;
 blocked:=false;
 begin
  insert into ingest.county_inventory_feature(audit_sha256,source_id,object_id,input_text)
  values(a,r.source_id,999999999,r.input_text);
 exception when others then blocked:=SQLERRM='County batch is sealed; use a new audit';end;
 if not blocked then raise exception 'Sealed batch changed';end if;
 blocked:=false;
 begin delete from ingest.county_inventory_feature where audit_sha256=a and source_id=r.source_id and object_id=r.object_id;
 exception when others then blocked:=true;end;
 if not blocked then raise exception 'History deletion accepted';end if;
 blocked:=false;
 begin
  insert into ingest.audit_result(sha256,registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,storage_object)
  select repeat('f',64),registry_sha256,evidence_state,method_path,method_sha256,document,storage_bucket,'sha256/'||repeat('f',64)||'.response' from ingest.audit_result where sha256=a;
  insert into ingest.county_inventory_batch(audit_sha256) values(repeat('f',64));
  set constraints all immediate;
 exception when others then blocked:=SQLERRM='Incomplete or changed county inventory';end;
 if not blocked then raise exception 'Incomplete inventory committed';end if;
 select count(*) into n from ingest.county_inventory_feature where audit_sha256=a;
 raise notice 'County privacy, replay, completeness, holds, sealing and immutable history checks passed (% records)',n;
end $$;
rollback;
