-- Read-only Orneville ZP796 investigation and unchanged county state.
-- Corrections only remove holds; count effective holds over all originally held rows.
-- Original fingerprints still cover the complete county cohort.
with f as (
 select source_id,object_id,input_sha256,geometry is null as held
 from ingest.county_inventory_feature
 where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
), fingerprints as (
 select source_id,count(*) n,encode(sha256(convert_to(string_agg(object_id::text||':'||input_sha256||E'\n','' order by object_id),'UTF8')),'hex') h from f group by source_id
), effective as (
 select source_id,object_id,effective_geometry_hold,qualified_for_parcel_screening from ingest.effective_county_inventory
 where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259' and original_geometry is null
)
select json_build_object(
 'verified_at',clock_timestamp(),
 'orneville_audit_present',exists(select 1 from ingest.audit_result where sha256='da6b8017e2940b505db5801900d76a1840d5b597b4f5889d58cae2d8016a1e00'),
 'orneville_observations',(select count(*) from ingest.source_response where registry_sha256='83ac49137456def36683e14fed0f4e9fe81bb5815a98d4836c720730f9cb029e'),
 'reconciliation_audit_present',exists(select 1 from ingest.audit_result where sha256='b6be9cee16a2af37e7975273cf4cdc383d18a7f9ba1ed6840546135ea3545b33'),
 'reconciliation_observations',(select count(*) from ingest.source_response where registry_sha256='b6b34f87481e669e20204e1b82f71a9806e271526fb2f26c8fc25b43aba56630'),
 'map_date_audit_present',exists(select 1 from ingest.audit_result where sha256='0520e8136fe08fe664b0f45f9cb2f8eee2c259d514d74ea9e9e18ff707aaea34'),
 'map_date_observations',(select count(*) from ingest.source_response where registry_sha256='c514fb755ee10a770e58eaa1c94baab8f9d71ca1f526ed3dce9bea7f54fb7b9c'),
 'ranking_audit_present',exists(select 1 from ingest.audit_result where sha256='a20ffe8bde648dc77fd502a15283c613b2a04c3b8dbf40c86417edd45f6fab1f'),
 'ranking_occurrences',(select count(*) from ingest.finding_occurrence where audit_sha256='a20ffe8bde648dc77fd502a15283c613b2a04c3b8dbf40c86417edd45f6fab1f'),
 'ranking_snapshot_current',ingest.county_geometry_snapshot_is_current('2781767e923e3ddb8871737e6d41d162bf1c91fef8a632da9b9e9a5927888316','fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'),
 'prior_ranking_needs_revisit',not ingest.county_geometry_snapshot_is_current('9c6eaf3da53ce57b66ecdb200d3abf72d11d38bd3fcdd8db5fe41a7cde62151c','fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'),
 'activation_audit_present',exists(select 1 from ingest.audit_result where sha256='c4a72f6e0674e204416c9f3205314dbc42166f73d66cb1456441655158d47b30'),
 'activation_occurrences',(select count(*) from ingest.finding_occurrence where audit_sha256='c4a72f6e0674e204416c9f3205314dbc42166f73d66cb1456441655158d47b30'),
 'new_features_effective_holds_cleared',(select count(*)=11 from effective where source_id='lupc-zoning' and object_id in (27342226,27365331,27364426,27339379,27364538,27324664,27321394,27366878,27261431,27304932,27358396) and effective_geometry_hold is null),
 'county_rows',(select count(*) from f),
 'original_total_holds',(select count(*) from f where held),
 'original_zoning_holds',(select count(*) from f where held and source_id='lupc-zoning'),
 'county_fingerprints_unchanged',(select jsonb_object_agg(source_id,jsonb_build_object('count',n,'sha256',h)) from fingerprints)=(select document->'record_manifest' from ingest.audit_result where sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'),
 'effective_total_holds',(select count(*) from effective where effective_geometry_hold is not null),
 'effective_zoning_holds',(select count(*) from effective where source_id='lupc-zoning' and effective_geometry_hold is not null),
 'qualified_rows',(select count(*) from ingest.effective_county_inventory where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259' and qualified_for_parcel_screening),
 'accepted',(select json_agg(t order by object_id) from (select object_id,correction_id,candidate_sha256,geometry_event_id,effective_scope_relation,extensions.ST_IsValid(effective_geometry) valid,extensions.ST_SRID(effective_geometry) srid from ingest.effective_county_inventory where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259' and correction_status='accepted')t),
 'snapshots',(select json_agg(t) from (select snapshot_id,source_audit_sha256,needs_revisit from ingest.county_geometry_snapshot_current)t),
 'finding_reviews',(select json_agg(t order by finding_id) from (select finding_id,event_id,status,priority,next_action,occurrence_count from ingest.finding_current where finding_id in ('TL-F-0029','TL-F-0022','TL-F-0109'))t),
 'archive_bucket_private',(select not public from storage.buckets where id='terralucid-source-snapshots')
) as verification;
