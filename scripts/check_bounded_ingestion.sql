with batches as (
select b.batch_id,
       (select count(*) from ingest.source_record r where r.batch_id=b.batch_id) as source_records,
       (select count(*) from ingest.assessment_candidate c where c.batch_id=b.batch_id) as candidate_links,
       (select jsonb_object_agg(source_id,n) from
          (select source_id,count(*) n from ingest.source_record where batch_id=b.batch_id group by source_id) s) as source_counts,
       (select jsonb_object_agg(geometry_state,n) from
          (select geometry_state,count(*) n from ingest.source_record where batch_id=b.batch_id group by geometry_state) s) as geometry_states,
       (select jsonb_object_agg(match_state,n) from
          (select match_state,count(*) n from ingest.assessment_match_summary where batch_id=b.batch_id group by match_state) s) as assessment_matches,
       (select count(*) from ingest.finding_occurrence where batch_id=b.batch_id) as record_occurrences
from ingest.load_batch b
), findings as (
select count(*) findings,count(*) filter(where status='open') open_findings,
       count(*) filter(where needs_revisit) needs_revisit,
       (select count(*) from ingest.finding_event) history_events,
       (select count(*) from ingest.finding_occurrence) evidence_occurrences
from ingest.finding_current
), security as (
select bool_and(relrowsecurity) as all_tables_have_rls from pg_class
where relnamespace='ingest'::regnamespace and relkind='r'
), access as (
select bool_and(not has_table_privilege(r,t,'SELECT,INSERT,UPDATE,DELETE')) as client_access_denied
from unnest(array['anon','authenticated','service_role']) r
cross join unnest(array['ingest.load_batch','ingest.source_record','ingest.assessment_candidate',
 'ingest.finding','ingest.finding_event','ingest.finding_occurrence','ingest.finding_current','ingest.assessment_match_summary']) t
) select jsonb_build_object('batches',(select jsonb_agg(batches) from batches),
 'findings',(select to_jsonb(f) from findings f),
 'security',(select to_jsonb(security) from security),
 'access',(select to_jsonb(access) from access)) as verification;
