-- Read-only fixed-candidate review verification.
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
 'review_audit_present',exists(select 1 from ingest.audit_result where sha256='6a649c0cfffedf0fde0d3790a6f44fc8a0990baa9e5e5b7e705f7569e513900a'),
 'review_occurrences',(select count(*) from ingest.finding_occurrence where audit_sha256='6a649c0cfffedf0fde0d3790a6f44fc8a0990baa9e5e5b7e705f7569e513900a'),
 'investigated_features_still_held',(select count(*)=2 from effective where source_id='lupc-zoning' and object_id in (27208875,27336229) and effective_geometry_hold is not null),
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
