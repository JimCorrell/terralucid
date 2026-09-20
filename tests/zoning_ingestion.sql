-- LOCAL DISPOSABLE DATABASE ONLY. Synthetic changes are rolled back.
BEGIN;
DO $$
declare s ingest.zoning_screening%rowtype; failed boolean; current_event text; payload jsonb; h jsonb; actual_area double precision;
begin
  if (select count(*) from ingest.zoning_feature)<>383 or
     (select count(*) from ingest.zoning_feature where geometry_state='invalid')<>1 or
     (select count(*) from ingest.zoning_screening)<>2648 or
     (select count(*) from ingest.zoning_screening where input->'holds'<>'[]'::jsonb)<>119 or
     (select sum(jsonb_array_length(result->'intersections')) from ingest.zoning_screening)<>651 or
     exists(select 1 from ingest.zoning_screening_current where needs_revisit) then raise exception 'Fixture scope or version differs'; end if;
  if exists(select 1 from ingest.zoning_screening where result->>'status'='no_qualified_digital_coverage' and result->'covered_fraction'<>'null'::jsonb) then raise exception 'Missing coverage was converted to zero'; end if;
  if exists(select 1 from ingest.zoning_screening zs cross join lateral jsonb_array_elements(zs.result->'intersections') hit where (hit->>'object_id')::bigint=27232839) then raise exception 'Invalid zoning geometry used'; end if;
  if exists(select 1 from ingest.zoning_screening zs join ingest.finding_occurrence f on f.record_id=zs.source_record_id where not ((zs.result->'related_finding_ids') ? f.finding_id)) then raise exception 'Original source finding lost'; end if;
  select * into s from ingest.zoning_screening where jsonb_array_length(result->'intersections')>1 limit 1;
  h=s.result->'intersections'->0;
  select extensions.ST_Area(extensions.ST_Intersection(
    extensions.ST_Transform(extensions.ST_GeomFromGeoJSON((s.input#>'{raw_feature,geometry}')::text),26919),
    extensions.ST_Transform(z.geometry,26919))) into actual_area
  from ingest.zoning_feature z where z.audit_sha256=s.audit_sha256 and z.object_id=(h->>'object_id')::bigint;
  if abs(actual_area-(h->>'area_m2')::double precision)>0.1 then raise exception 'Independent PostGIS area differs'; end if;
  select * into s from ingest.zoning_screening where correction_event_id is not null limit 1;
  payload=jsonb_build_object('event_id',repeat('e',64),'correction_id',s.correction_id,'status','revoked','actor','Local test','note','Synthetic dependency invalidation');
  perform ingest.record_correction_event(payload,s.correction_event_id);
  if not (select needs_revisit from ingest.zoning_screening_current where audit_sha256=s.audit_sha256 and subject_id=s.subject_id) then raise exception 'Changed correction not flagged'; end if;
  failed=false;
  begin insert into ingest.zoning_screening(audit_sha256,subject_id,source_record_id,correction_id,correction_event_id,input,result)
    values(s.audit_sha256,s.subject_id,s.source_record_id,s.correction_id,s.correction_event_id,s.input,s.result) on conflict do nothing;
  exception when raise_exception then if SQLERRM<>'Correction input changed; export and recompute' then raise; end if;failed=true;end;
  if not failed then raise exception 'Stale correction input accepted'; end if;
  select * into s from ingest.zoning_screening where source_record_id is not null limit 1;
  update ingest.source_record set quality_flags=array_append(quality_flags,'synthetic_test') where record_id=s.source_record_id;
  if not (select needs_revisit from ingest.zoning_screening_current where audit_sha256=s.audit_sha256 and subject_id=s.subject_id) then raise exception 'Changed source flags not flagged'; end if;
  failed=false;
  begin update ingest.zoning_screening set result='{}' where subject_id=s.subject_id;
  exception when raise_exception then failed=true;end;
  if not failed then raise exception 'Analysis history overwritten'; end if;
  failed=false;
  begin insert into ingest.zoning_screening(audit_sha256,subject_id,source_record_id,correction_id,correction_event_id,input,result)
    values(s.audit_sha256,s.subject_id,s.source_record_id,s.correction_id,s.correction_event_id,s.input,s.result||'{"covered_fraction":0}'::jsonb) on conflict do nothing;
  exception when raise_exception then if SQLERRM<>'Zoning screening replay differs' then raise; end if;failed=true;end;
  if not failed then raise exception 'Conflicting result replay ignored'; end if;
end $$;
ROLLBACK;
