, soil_polygons as materialized (
 select e.source_key,e.input_sha256,e.response_sha256,e.source_attributes->>'mukey' as mukey,
 e.provenance,e.correction_id,e.candidate_sha256,e.geometry_event_id,e.correction_status,
 ST_Transform(e.effective_geometry,26919) as g
 from ingest.effective_soil_geometry e cross join request r cross join aoi a
 where e.report_sha256=r.j#>>'{soils,batch}' and e.effective_geometry_hold is null
 and e.effective_geometry && ST_Transform(a.g,4326)
 and ST_Intersects(ST_Transform(e.effective_geometry,26919),a.g)
), soil_units as materialized (
 select f.* from ingest.soil_record f cross join request r
 where f.report_sha256=r.j#>>'{soils,batch}' and f.kind='mapunit' and f.source_key in (select mukey from soil_polygons)
), soil_components as materialized (
 select f.* from ingest.soil_record f cross join request r
 where f.report_sha256=r.j#>>'{soils,batch}' and f.kind='component' and f.parent_key in (select source_key from soil_units)
), soil_tables as (
 select * from soil_units union all select * from soil_components
 union all select f.* from ingest.soil_record f cross join request r where f.report_sha256=r.j#>>'{soils,batch}' and f.kind='legend' and f.source_key in (select parent_key from soil_units)
 union all select f.* from ingest.soil_record f cross join request r where f.report_sha256=r.j#>>'{soils,batch}' and f.kind='chorizon' and f.parent_key in (select source_key from soil_components)
), soil_capture as (
 select jsonb_build_object(
 'aoi_within_study',coalesce((select ST_Covers(s.boundary,a.g) from ingest.soil_geometry_study s cross join request r cross join aoi a where s.source_batch_sha256=r.j#>>'{soils,batch}'),false),
 'held_keys',(select coalesce(jsonb_agg(source_key order by source_key),'[]'::jsonb) from ingest.effective_soil_geometry e cross join request r where e.report_sha256=r.j#>>'{soils,batch}' and e.effective_geometry_hold is not null),
 'polygons',(select coalesce(jsonb_agg(jsonb_build_object('source_key',source_key,'mukey',mukey,'input_sha256',input_sha256,'response_sha256',response_sha256,'provenance',provenance,'correction_id',correction_id,'candidate_sha256',candidate_sha256,'geometry_event_id',geometry_event_id,'correction_status',correction_status,'geometry_wkb',encode(ST_AsBinary(g),'hex')) order by source_key),'[]'::jsonb) from soil_polygons),
 'tables',(select coalesce(jsonb_agg(jsonb_build_object('kind',kind,'source_key',source_key,'input_sha256',input_sha256,'response_sha256',response_sha256,'provenance',input_text::jsonb->'provenance','raw',input_text::jsonb->'raw') order by kind,source_key),'[]'::jsonb) from soil_tables)
 ) as document
)
