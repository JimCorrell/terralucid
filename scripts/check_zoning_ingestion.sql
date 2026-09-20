select jsonb_build_object(
 'zone_features',(select count(*) from ingest.zoning_feature),
 'zone_geometry_states',(select jsonb_object_agg(geometry_state,n) from (select geometry_state,count(*) n from ingest.zoning_feature group by geometry_state) x),
 'screenings',(select count(*) from ingest.zoning_screening),
 'screening_states',(select jsonb_object_agg(state,n) from (select result->>'status' state,count(*) n from ingest.zoning_screening group by 1) x),
 'intersections',(select sum(jsonb_array_length(result->'intersections')) from ingest.zoning_screening),
 'records_with_holds',(select count(*) from ingest.zoning_screening where input->'holds'<>'[]'::jsonb),
 'needs_revisit',(select count(*) from ingest.zoning_screening_current where needs_revisit),
 'legal_zoning_unknown',(select bool_and(result->>'legal_zoning_state'='UNKNOWN') from ingest.zoning_screening),
 'correction_events_retained',(select count(*) from ingest.zoning_screening where correction_event_id is not null),
 'original_source_records',(select count(*) from ingest.source_record),
 'original_candidate_links',(select count(*) from ingest.assessment_candidate),
 'findings',(select count(*) from ingest.finding),
 'finding_events',(select count(*) from ingest.finding_event),
 'rls',(select bool_and(relrowsecurity) from pg_class where oid in ('ingest.zoning_feature'::regclass,'ingest.zoning_screening'::regclass)),
 'client_access_denied',(select bool_and(not has_table_privilege(r,t,'SELECT,INSERT,UPDATE,DELETE'))
 from unnest(array['anon','authenticated','service_role']) r cross join
 unnest(array['ingest.zoning_feature','ingest.zoning_screening','ingest.zoning_screening_current']) t)
) as verification;
