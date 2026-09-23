-- Shared dependency capture; caller supplies a validated JSON request literal.
with request as (select __REQUEST__::jsonb as j),
context as (
 select jsonb_build_object(
 'soils',__SOIL_CONTEXT__,
 'database_runtime',postgis_full_version(),
 'source_audit',j->>'audit','geometry_snapshot',j->>'snapshot',
 'source_exists',exists(select 1 from ingest.county_inventory_batch where audit_sha256=j->>'audit'),
 'snapshot_current',ingest.county_geometry_snapshot_is_current(j->>'snapshot',j->>'audit'),
 'geometry_dependencies',ingest.county_geometry_dependencies(j->>'audit'),
 'evidence_catalog_sha256',(select encode(sha256(convert_to(coalesce(string_agg(sha256,',' order by sha256),''),'UTF8')),'hex') from ingest.audit_result),
 'source_observations_sha256',(select encode(sha256(convert_to(coalesce(string_agg(observation_sha256,',' order by observation_sha256),''),'UTF8')),'hex') from ingest.source_response),
 'county_batches',(select coalesce(jsonb_agg(audit_sha256 order by audit_sha256),'[]'::jsonb) from ingest.county_inventory_batch),
 'finding_dependencies',(select coalesce(jsonb_object_agg(finding_id,jsonb_build_object('event_id',event_id,'occurrences',occurrence_count,'needs_revisit',needs_revisit)),'{}'::jsonb) from ingest.finding_current)
 ) as document from request
)
