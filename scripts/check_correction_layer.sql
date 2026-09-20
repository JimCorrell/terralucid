select jsonb_build_object(
 'snapshot_records',(select count(*) from ingest.corrected_source),
 'accepted',(select count(*) from ingest.corrected_source where correction_status='accepted'),
 'held',(select count(*) from ingest.corrected_source where correction_status='held'),
 'records_with_holds',(select count(*) from ingest.corrected_source where holds<>'[]'::jsonb),
 'geocode_changes',(select count(*) from ingest.corrected_source where effective_properties->'GEOCODE' is distinct from raw_feature#>'{properties,GEOCODE}'),
 'identifier_changes',(select count(*) from ingest.corrected_source where effective_properties->'STATE_ID' is distinct from raw_feature#>'{properties,STATE_ID}'),
 'correction_events',(select count(*) from ingest.correction_event),
 'source_records',(select count(*) from ingest.source_record),
 'candidate_links',(select count(*) from ingest.assessment_candidate),
 'findings',(select count(*) from ingest.finding),
 'finding_events',(select count(*) from ingest.finding_event),
 'rls',(select bool_and(relrowsecurity) from pg_class where oid in ('ingest.correction_source'::regclass,'ingest.correction_event'::regclass)),
 'client_access_denied',(select bool_and(not has_table_privilege(r,t,'SELECT,INSERT,UPDATE,DELETE'))
 from unnest(array['anon','authenticated','service_role']) r cross join
 unnest(array['ingest.correction_source','ingest.correction_event','ingest.corrected_source']) t),
 'client_review_denied',(select bool_and(not has_function_privilege(r,'ingest.record_correction_event(jsonb,text)','EXECUTE')) from unnest(array['anon','authenticated','service_role']) r)
) as verification;
