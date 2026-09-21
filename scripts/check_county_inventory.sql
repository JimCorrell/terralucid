-- Read-only. Feature queries require the county migration and full load.
select sha256,document->>'scope' as scope,document->'record_manifest' as expected
from ingest.audit_result
where sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259';
select source_id,scope_relation,count(*) from ingest.county_inventory
where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
group by source_id,scope_relation order by source_id,scope_relation;
select source_id,extensions.ST_SRID(geometry) as srid,count(*)
from ingest.county_inventory_feature
where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259'
group by source_id,extensions.ST_SRID(geometry) order by source_id,srid;
select finding_id,status,priority,next_action,occurrence_count,needs_revisit,event_id
from ingest.finding_current where finding_id in ('TL-F-0029','TL-F-0117');
select relname,relrowsecurity,has_table_privilege('anon',oid,'select') as anon_select,
 has_table_privilege('authenticated',oid,'select') as authenticated_select
from pg_class where oid in ('ingest.county_inventory_batch'::regclass,'ingest.county_inventory_feature'::regclass);
