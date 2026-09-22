-- Appended to qualification_context.sql inside one REPEATABLE READ READ ONLY transaction.
, input_aoi as materialized (
 select case when j ? 'geometry' then ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON((j->'geometry')::text),4326),26919)
 else (select effective_geometry from ingest.effective_county_inventory where audit_sha256=j->>'audit'
 and source_id=j->>'source_id' and object_id=(j->>'object_id')::bigint) end as g from request
), aoi as materialized (
 select g,ST_Transform(g,5070) as g5070 from input_aoi
), eligible as materialized (
 -- Bounding-box operators can use the original geometry GiST index. Include
 -- every held record and every accepted correction so changed extents cannot
 -- be lost by filtering on an original source geometry.
 select f.audit_sha256,f.source_id,f.object_id from ingest.county_inventory_feature f cross join request r cross join aoi a
 where f.audit_sha256=r.j->>'audit' and f.source_id not in ('nwi-package','nwi-project') and f.geometry && a.g
 union
 select f.audit_sha256,f.source_id,f.object_id from ingest.county_inventory_feature f cross join request r cross join aoi a
 where f.audit_sha256=r.j->>'audit' and f.source_id in ('nwi-package','nwi-project') and f.geometry && a.g5070
 union
 select f.audit_sha256,f.source_id,f.object_id from ingest.county_inventory_feature f cross join request r
 where f.audit_sha256=r.j->>'audit' and f.geometry is null
 union
 select c.source_audit_sha256,c.source_id,c.object_id from ingest.county_geometry_current c cross join request r
 where c.source_audit_sha256=r.j->>'audit' and c.correction_status='accepted'
), candidates as materialized (
 -- Project only consumed evidence fields. In particular, do not materialize
 -- the view's county-wide scope-relation calculations for this bounded AOI.
 select e.source_id,e.object_id,e.input_sha256,e.source_attributes,
 e.effective_geometry_hold,e.effective_quality_flags,e.provenance,e.correction_id,
 e.geometry_event_id,e.candidate_sha256,e.correction_status,f.data,
 case when e.effective_geometry is not null then ST_Transform(e.effective_geometry,26919) end as g
 from eligible k join ingest.effective_county_inventory e using(audit_sha256,source_id,object_id)
 join ingest.county_inventory_feature f using(audit_sha256,source_id,object_id)
 cross join request r cross join aoi a
 where e.audit_sha256=r.j->>'audit' and a.g is not null
 and (e.effective_geometry_hold is not null or (e.effective_geometry && case when ST_SRID(e.effective_geometry)=5070 then a.g5070 else a.g end
 and ST_Intersects(e.effective_geometry,case when ST_SRID(e.effective_geometry)=5070 then a.g5070 else a.g end)))
), readiness as (
 select sha256,document from ingest.audit_result
 where document->>'method'='scripts/assess_county_readiness.py'
 and document->>'source_audit_sha256'=(select j->>'audit' from request)
 order by sha256
)
select jsonb_build_object(
 'captured_at',clock_timestamp(),'context',(select document from context),'request',(select j from request),
 'aoi_wkb',(select encode(ST_AsBinary(g),'hex') from aoi),
 'aoi_within_county',(select ST_Covers(b.boundary,a.g) from ingest.county_inventory_batch b cross join aoi a cross join request r where b.audit_sha256=r.j->>'audit'),
 'runtime',jsonb_build_object('postgres',version(),'postgis',postgis_full_version()),
 'features',(select coalesce(jsonb_agg(jsonb_build_object(
 'source_id',source_id,'object_id',object_id,'input_sha256',input_sha256,
 'geometry_wkb',encode(ST_AsBinary(g),'hex'),'hold',effective_geometry_hold,
 'raw_held_geometry',case when effective_geometry_hold is not null then data#>'{raw_feature,geometry}' end,
 'native_srid',data->'srid','attributes',source_attributes,'parsed_date',data->'parsed_date',
 'flags',effective_quality_flags,'provenance',provenance,'correction_id',correction_id,
 'geometry_event_id',geometry_event_id,'candidate_sha256',candidate_sha256,'correction_status',correction_status
 ) order by source_id,object_id),'[]'::jsonb) from candidates),
 'findings',(select coalesce(jsonb_agg(jsonb_build_object('id',finding_id,'title',title,'source_ids',source_ids,'scope',scope,
 'status',status,'priority',priority,'event_id',event_id,'needs_revisit',needs_revisit,'next_action',next_action) order by finding_id),'[]'::jsonb)
 from ingest.finding_current where status<>'resolved' or needs_revisit),
 'readiness_audits',(select coalesce(jsonb_agg(jsonb_build_object('sha256',sha256,'document',document) order by sha256),'[]'::jsonb) from readiness)
);
