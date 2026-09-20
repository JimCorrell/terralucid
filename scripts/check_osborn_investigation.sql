-- Historical checkpoint for the proposed-only TL-F-0025 investigation.
select json_build_object(
  'audit_present', exists(select 1 from ingest.audit_result where sha256='1c37372f5957128a95b3a9d25a7a43286423cbf1ed8831d70bd305b90d933067'),
  'observations', (select count(*) from ingest.source_response where registry_sha256=(select registry_sha256 from ingest.audit_result where sha256='1c37372f5957128a95b3a9d25a7a43286423cbf1ed8831d70bd305b90d933067')),
  'proposal_status', (select document#>>'{proposal,status}' from ingest.audit_result where sha256='1c37372f5957128a95b3a9d25a7a43286423cbf1ed8831d70bd305b90d933067'),
  'investigation_occurrences', (select count(*) from ingest.finding_occurrence where finding_id='TL-F-0025' and audit_sha256='1c37372f5957128a95b3a9d25a7a43286423cbf1ed8831d70bd305b90d933067'),
  'finding', (select json_build_object('status',status,'priority',priority,'occurrences',occurrence_count,'needs_revisit',needs_revisit,'event_id',event_id) from ingest.finding_current where finding_id='TL-F-0025'),
  'source_records', (select count(*) from ingest.source_record),
  'assessment_candidates', (select count(*) from ingest.assessment_candidate),
  'zoning_features', (select count(*) from ingest.zoning_feature),
  'zoning_screenings', (select count(*) from ingest.zoning_screening),
  'original_geometry_state', (select geometry_state from ingest.zoning_feature where audit_sha256='4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c' and object_id=27232839),
  'findings', (select count(*) from ingest.finding),
  'finding_events', (select count(*) from ingest.finding_event),
  'bucket_private', (select not public from storage.buckets where id='terralucid-source-snapshots')
) as verification;
