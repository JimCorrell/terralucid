-- Read-only three-priority investigation verification; no activation.
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
 'investigation_audit_present',exists(select 1 from ingest.audit_result where sha256='a4b734b5498166be9a802b3cdc4dd08c24567ac10bb9f6764962f187e346d797'),
 'investigation_occurrences',(select count(*) from ingest.finding_occurrence where audit_sha256='a4b734b5498166be9a802b3cdc4dd08c24567ac10bb9f6764962f187e346d797'),
 'source_observations',(select count(*) from ingest.source_response where registry_sha256='aae385a3e7c80713f4c79df7506ba76f6010cabf87675c6b647c5b285211f9a0'),
 'three_cases_still_held',(select count(*)=3 from effective where source_id='lupc-zoning' and object_id in (27304757,27270812,27207268) and effective_geometry_hold is not null),
 'ranking_audit_present',exists(select 1 from ingest.audit_result where sha256='07efac22afa8829de039ada598fa06533f378c33edc720f40a255b67c75d0136'),
 'ranking_occurrences',(select count(*) from ingest.finding_occurrence where audit_sha256='07efac22afa8829de039ada598fa06533f378c33edc720f40a255b67c75d0136'),
 'ranking_snapshot_current',ingest.county_geometry_snapshot_is_current('6953a46ca94beb0c5fa74bac958926d015afb78c65ccfe28c35b08fc10f9d048','fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'),
 'wrong_source_rejected',not ingest.county_geometry_snapshot_is_current('6953a46ca94beb0c5fa74bac958926d015afb78c65ccfe28c35b08fc10f9d048','wrong-audit'),
 'old_snapshot_rejected',not ingest.county_geometry_snapshot_is_current('d0756dd73405ebd6ae3aa3a72db2d91a9f2fd5a74355e1324f628c14f25bc4c9','fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'),
 'activation_audit_present',exists(select 1 from ingest.audit_result where sha256='29eb98bf8d6fd719aebb2cf1c1cd062169378a336564a62a8a0b0d983a1fd464'),
 'activation_occurrences',(select count(*) from ingest.finding_occurrence where audit_sha256='29eb98bf8d6fd719aebb2cf1c1cd062169378a336564a62a8a0b0d983a1fd464'),
 'new_features_effective_holds_cleared',(select count(*)=2 from effective where source_id='lupc-zoning' and object_id in (27208875,27336229) and effective_geometry_hold is null),
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
