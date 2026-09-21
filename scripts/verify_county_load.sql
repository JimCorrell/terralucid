-- Read-only full county load verification. May exceed the query service timeout.
-- Run in a read-only transaction with a sufficient local statement timeout.
with features as (
 select source_id,object_id,input_sha256,geometry,data->>'hold' as hold,data->>'scope_relation' as scope_relation from ingest.county_inventory_feature where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
), fingerprints as (
 select source_id,count(*) n,encode(sha256(convert_to(string_agg(object_id::text||':'||input_sha256||E'\n','' order by object_id),'UTF8')),'hex') h from features group by source_id
), scope_counts as (
 select source_id,scope_relation,count(*) as records from features group by source_id,scope_relation
)
select json_build_object(
 'audit_sha256','fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259',
 'verified_at',clock_timestamp(),
 'feature_rows',(select count(*) from features),
 'held_geometries',(select count(*) from features where hold is not null),
 'unexpected_geometry_state',(select count(*) from features where (hold is not null and geometry is not null) or (hold is null and (geometry is null or not extensions.ST_IsValid(geometry))) or (geometry is not null and extensions.ST_SRID(geometry)<>case when source_id in ('nwi-package','nwi-project') then 5070 else 26919 end)),
 'manifest_matches',(select jsonb_object_agg(source_id,jsonb_build_object('count',n,'sha256',h)) from fingerprints)=(select document->'record_manifest' from ingest.audit_result where sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'),
 'scope_counts',(select json_agg(scope_counts order by source_id,scope_relation) from scope_counts),
 'database_size',pg_size_pretty(pg_database_size(current_database())),
 'feature_table_size',pg_size_pretty(pg_total_relation_size('ingest.county_inventory_feature')),
 'private_tables',(select bool_and(relrowsecurity and not has_table_privilege('anon',oid,'select') and not has_table_privilege('authenticated',oid,'select')) from pg_class where oid in ('ingest.county_inventory_batch'::regclass,'ingest.county_inventory_feature'::regclass)),
 'private_view',not has_table_privilege('anon','ingest.county_inventory','select') and not has_table_privilege('authenticated','ingest.county_inventory','select'),
 'bucket_private',(select not public from storage.buckets where id='terralucid-source-snapshots'),
 'source_observations',(select count(*) from ingest.source_response where registry_sha256='9a6e413813712a882aee259ad3bbf5ebf320f889b5b56829a9beb880382d0a10'),
 'finding_occurrences',(select count(*) from ingest.finding_occurrence where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'),
 'county_finding',(select row_to_json(f) from (select finding_id,status,priority,next_action,occurrence_count,event_id from ingest.finding_current where finding_id='TL-F-0029')f)
) as verification;
