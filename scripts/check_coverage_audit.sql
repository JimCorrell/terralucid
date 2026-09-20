-- One row per versioned report, without returning the full evidence document.
select a.sha256, a.registry_sha256, a.evidence_state,
       a.document->'summary' as summary,
       a.document->'join_sample'->'cardinalities' as sample_cardinalities,
       (select count(*) from ingest.source_response r where r.registry_sha256=a.registry_sha256) as source_responses,
       jsonb_array_length(a.document->'jurisdictions') as reference_rows,
       (select relrowsecurity from pg_class where oid='ingest.audit_result'::regclass) as rls_enabled,
       (select bool_and(not has_table_privilege(r,'ingest.audit_result','SELECT,INSERT,UPDATE,DELETE'))
        from unnest(array['anon','authenticated','service_role']) r) as client_table_access_denied
from ingest.audit_result a;
