-- Private, bounded analysis input: corrected Sweden/Alfred and original UT records.
select jsonb_build_object(
 'corrections',(select jsonb_agg(jsonb_build_object(
   'correction_id',correction_id,'audit_sha256',audit_sha256,
   'source_id',source_id,'source_snapshot_sha256',source_snapshot_sha256,
   'source_feature_sha256',source_feature_sha256,'object_id',object_id,
   'event_id',event_id,'correction_status',correction_status,
   'effective_properties',effective_properties,'holds',holds,
   'related_finding_ids',related_finding_ids) order by object_id)
 from ingest.corrected_source where audit_sha256='6e08cd827867fbf816d94c82bd22b44d6889caf8936726f144bd00307de52e8f'),
 'ut_records',(select jsonb_agg(jsonb_build_object('record_id',record_id,
   'batch_id',batch_id,'source_id',source_id,'object_id',object_id,
   'raw_feature',raw_feature,'quality_flags',quality_flags,'parsed_date',parsed_date,
   'geometry_state',geometry_state,'observation_sha256',observation_sha256,
   'related_finding_ids',coalesce((select jsonb_agg(fid order by fid) from
      (select distinct finding_id fid from ingest.finding_occurrence f where f.record_id=r.record_id) ids),'[]'::jsonb)) order by object_id)
 from ingest.source_record r where source_id='ut-parcels'
 and batch_id='53583bba4ab54f4774893ce9004b33a73302f9609f791d46f69506bfecd08816')
) as inputs;
