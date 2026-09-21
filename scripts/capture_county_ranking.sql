-- Run in one READ COMMITTED transaction. Separate statements retain the batch
-- lock while giving the effective-input query a fresh statement snapshot.
do $$ begin
 perform ingest.record_county_geometry_snapshot('fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259');
end $$;
select jsonb_build_object(
 'source_audit_sha256','fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259',
 'snapshot',(select to_jsonb(s)-'created_at' from ingest.county_geometry_snapshot_current s where source_audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259' and not needs_revisit),
 'held_object_ids',(select jsonb_agg(object_id order by object_id) from ingest.effective_county_inventory where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259' and source_id='lupc-zoning' and original_geometry is null and effective_geometry_hold is not null),
 'accepted',(select jsonb_agg(to_jsonb(t) order by object_id) from (select object_id,correction_id,candidate_sha256,geometry_event_id,input_sha256 as source_input_sha256 from ingest.effective_county_inventory where audit_sha256='fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259' and correction_status='accepted') t),
 'finding_reviews',(select jsonb_agg(to_jsonb(t) order by finding_id) from (select finding_id,event_id,status,priority,next_action,occurrence_count from ingest.finding_current where finding_id in ('TL-F-0029','TL-F-0022','TL-F-0109'))t)
);
