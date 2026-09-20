-- Administrative export from the default effective-geometry view after acceptance.
select jsonb_build_object(
 'source_audit_sha256','4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c',
 'geometry_dependencies',ingest.zoning_geometry_dependencies('4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c'),
 'zones',(select jsonb_agg(jsonb_build_object('object_id',object_id,'raw_feature',raw_feature,
   'effective_geojson',effective_geojson,'effective_geometry_state',effective_geometry_state,
   'correction_id',correction_id,'geometry_event_id',geometry_event_id,'correction_status',correction_status,
   'candidate_sha256',candidate_sha256,'limits',limits) order by object_id)
   from ingest.corrected_zoning_feature where audit_sha256='4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c'),
 'subjects',(select jsonb_agg(jsonb_build_object('subject_id',subject_id,'input',input,'previous_result',result) order by subject_id)
   from ingest.zoning_screening where audit_sha256='4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c' and result->>'jurisdiction_code'='09230')
) as inputs;
