-- Read-only deployment checks for the bounded investigation; no accepted geometry.
with f as (
 select source_id,object_id,input_sha256,geometry is null as held
 from ingest.county_inventory_feature
 where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
), fingerprints as (
 select source_id,count(*) n,encode(sha256(convert_to(string_agg(object_id::text||':'||input_sha256||E'\n','' order by object_id),'UTF8')),'hex') h from f group by source_id
)
select json_build_object(
 'verified_at',clock_timestamp(),
 'county_rows',(select count(*) from f),
 'county_geometry_holds',(select count(*) from f where held),
 'county_zoning_holds',(select count(*) from f where held and source_id='lupc-zoning'),
 'county_fingerprints_unchanged',(select jsonb_object_agg(source_id,jsonb_build_object('count',n,'sha256',h)) from fingerprints)=(select document->'record_manifest' from ingest.audit_result where sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'),
 'investigation_audit_present',exists(select 1 from ingest.audit_result where sha256='25f03b37818d1fc5cf25a6fa1e9264d48824c8585dbbf9776574dd6682905b6c'),
 'investigation_occurrences',(select count(*) from ingest.finding_occurrence where audit_sha256='25f03b37818d1fc5cf25a6fa1e9264d48824c8585dbbf9776574dd6682905b6c'),
 'finding_reviews',(select json_agg(t order by finding_id) from (select finding_id,event_id,status,priority,next_action,occurrence_count from ingest.finding_current where finding_id in ('TL-F-0029','TL-F-0022','TL-F-0109'))t),
 'archive_bucket_private',(select not public from storage.buckets where id='terralucid-source-snapshots')
) as verification;
