select json_build_object(
 'audits',(select json_agg(audit_sha256) from ingest.wetlands_package_batch),
 'features',(select count(*) from ingest.wetlands_package_feature),
 'valid_native',(select count(*) from ingest.wetlands_package_feature where extensions.ST_IsValid(geometry) and extensions.ST_SRID(geometry)=5070),
 'exact_blob_checksums',(select count(*) from ingest.wetlands_package_feature where encode(sha256(geometry_blob),'hex')=data->>'geometry_blob_sha256'),
 'inferred_links',(select count(*) from ingest.wetlands_package_current where identity_state='INFERRED'),
 'stale',(select count(*) from ingest.wetlands_package_current where needs_revisit),
 'findings',(select json_agg(json_build_object('id',finding_id,'status',status,'event',event_id,'occurrences',occurrence_count,'needs_revisit',needs_revisit)) from ingest.finding_current where finding_id in('TL-F-0117','TL-F-0027','TL-F-0028')),
 'bucket_public',(select public from storage.buckets where id='terralucid-source-snapshots'),
 'rls',(select bool_and(relrowsecurity) from pg_class where oid in('ingest.wetlands_package_batch'::regclass,'ingest.wetlands_package_feature'::regclass)),
 'client_access',(select bool_or(has_table_privilege(r,t,'SELECT')) from unnest(array['anon','authenticated','service_role'])r cross join unnest(array['ingest.wetlands_package_batch','ingest.wetlands_package_feature','ingest.wetlands_package_current'])t)
) as checkpoint;
