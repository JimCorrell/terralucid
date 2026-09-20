-- Read-only acceptance report for the first research audit load.
select
  (select count(*) from ingest.registry_snapshot) as registry_snapshots,
  (select sum(jsonb_array_length(document->'sources')) from ingest.registry_snapshot) as source_descriptions,
  (select count(*) from ingest.source_response) as recorded_responses,
  (select count(*) from ingest.source_response where outcome = 'API_ERROR') as recorded_api_errors,
  (select count(*) from ingest.geometry_sample) as geometry_samples,
  (select count(*) from ingest.geometry_sample where extensions.ST_SRID(geometry) = 4326
     and extensions.ST_IsValid(geometry)) as valid_4326_samples,
  (select bool_and(relrowsecurity) from pg_class where relnamespace = 'ingest'::regnamespace
     and relkind = 'r') as all_tables_have_rls,
  (select bool_and(not has_schema_privilege(r, 'ingest', 'USAGE'))
     from unnest(array['anon','authenticated','service_role']) r) as client_schema_access_denied,
  (select bool_and(not has_table_privilege(r, t, 'SELECT,INSERT,UPDATE,DELETE'))
     from unnest(array['anon','authenticated','service_role']) r
     cross join unnest(array['ingest.registry_snapshot','ingest.source_response','ingest.geometry_sample']) t
  ) as client_table_access_denied;
