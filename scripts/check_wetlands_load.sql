-- Read-only checkpoint; use the intended audit when more versions are introduced.
select json_build_object(
 'batch_count',(select count(*) from ingest.wetlands_batch),
 'feature_count',(select count(*) from ingest.wetlands_feature),
 'valid_geometries',(select count(*) from ingest.wetlands_feature where extensions.ST_IsValid(geometry) and extensions.ST_SRID(geometry)=3857),
 'page_occurrences',(select sum(jsonb_array_length(data->'source_occurrences')) from ingest.wetlands_feature),
 'lookup_variants',(select count(*) from ingest.wetlands_feature,jsonb_object_keys(data->'lookup_variants')),
 'reviewed_classifications',(select count(*) from ingest.wetlands_feature_current where interpretation='reviewed_reference_match'),
 'stale_features',(select count(*) from ingest.wetlands_feature_current where needs_revisit),
 'missing_effective_lookup',(select count(*) from ingest.wetlands_feature_current where effective_lookup is null),
 'prior_study_intersections',(select count(*) from ingest.wetlands_feature_current where (prior_qualification_profile->>'intersection_area_m2')::numeric>0),
 'limits',(select json_agg(distinct limits) from ingest.wetlands_feature_current),
 'audit',(select json_agg(audit_sha256) from ingest.wetlands_batch),
 'finding',(select json_agg(json_build_object('id',finding_id,'status',status,'occurrences',occurrence_count,'event_id',event_id,'needs_revisit',needs_revisit)) from ingest.finding_current where finding_id in('TL-F-0027','TL-F-0028','TL-F-0117')),
 'bucket_public',(select public from storage.buckets where id='terralucid-source-snapshots'),
 'rls',(select bool_and(relrowsecurity) from pg_class where oid in('ingest.wetlands_batch'::regclass,'ingest.wetlands_feature'::regclass)),
 'client_access',(select bool_or(has_table_privilege(r,t,'SELECT')) from unnest(array['anon','authenticated','service_role'])r cross join unnest(array['ingest.wetlands_batch','ingest.wetlands_feature','ingest.wetlands_feature_current'])t)
) as checkpoint;
