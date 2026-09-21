-- Run only in a disposable database containing the authentic county + three acceptances.
BEGIN;
CREATE FUNCTION pg_temp.assert_true(ok boolean, message text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'Assertion failed: %', message; END IF; END $$;
CREATE FUNCTION pg_temp.rejects(command text, fragment text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 BEGIN EXECUTE command;
 EXCEPTION WHEN OTHERS THEN
  IF position(fragment in SQLERRM)=0 THEN RAISE EXCEPTION 'Wrong rejection: %',SQLERRM; END IF;
  RETURN;
 END;
 RAISE EXCEPTION 'Expected rejection: %',fragment;
END $$;
SELECT pg_temp.assert_true(count(*)=120449 AND count(*) FILTER(WHERE original_geometry_hold IS NOT NULL)=183
 AND count(*) FILTER(WHERE effective_geometry_hold IS NOT NULL)=180
 AND count(*) FILTER(WHERE source_id='lupc-zoning' AND effective_geometry_hold IS NOT NULL)=159
 AND NOT bool_or(qualified_for_parcel_screening),'inventory counts/qualification') FROM ingest.effective_county_inventory;
SELECT pg_temp.assert_true(count(*)=3 AND bool_and(extensions.ST_IsValid(effective_geometry))
 AND bool_and(extensions.ST_SRID(effective_geometry)=26919)
 AND bool_and(original_geometry IS NULL AND original_geometry_hold IS NOT NULL AND effective_geometry_hold IS NULL)
 AND bool_and(effective_scope_relation='interior')
 AND bool_and(original_quality_flags ? 'geometry_held' AND NOT effective_quality_flags ? 'geometry_held'),
 'accepted geometry, scope and flags') FROM ingest.effective_county_inventory WHERE correction_status='accepted';
CREATE TEMP TABLE fixture AS SELECT c.*,ingest.record_county_geometry_snapshot(c.source_audit_sha256) sid
 FROM ingest.county_geometry_current c WHERE object_id=27334504;
SELECT pg_temp.assert_true(ingest.county_geometry_snapshot_is_current(sid,source_audit_sha256)
 AND NOT ingest.county_geometry_snapshot_is_current(sid,repeat('0',64))
 AND NOT ingest.county_geometry_snapshot_is_current(repeat('0',64),source_audit_sha256),'snapshot source/missing guards') FROM fixture;
-- Segment direction/order is irrelevant; multiplicity is not.
SELECT pg_temp.assert_true((SELECT count(*) FROM ingest.county_segment_counts('[[[0,0],[1,1],[0,0]]]'))=1
 AND (SELECT n FROM ingest.county_segment_counts('[[[0,0],[1,1],[0,0]]]'))=2,'segment multiplicity');
SELECT pg_temp.rejects('UPDATE ingest.county_geometry_correction SET evidence_state=evidence_state','immutable');
SELECT pg_temp.rejects('DELETE FROM ingest.county_geometry_event','immutable');
SELECT pg_temp.rejects('DELETE FROM ingest.county_geometry_snapshot','immutable');
-- Exercise the insert trigger directly, without reserializing PostGIS geometry.
SELECT pg_temp.rejects($q$INSERT INTO ingest.county_geometry_correction(correction_id,source_audit_sha256,source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state)
 SELECT correction_id,source_audit_sha256,source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text||' ',candidate_sha256,evidence_state
 FROM ingest.county_geometry_correction LIMIT 1 ON CONFLICT DO NOTHING$q$,'replay differs');
SELECT pg_temp.rejects($q$INSERT INTO ingest.county_geometry_correction(correction_id,source_audit_sha256,source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state)
 SELECT correction_id,source_audit_sha256,source_id,object_id,repeat('0',64),source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state
 FROM ingest.county_geometry_correction LIMIT 1 ON CONFLICT DO NOTHING$q$,'replay differs');
SELECT pg_temp.rejects($q$INSERT INTO ingest.county_geometry_correction(correction_id,source_audit_sha256,source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state)
 SELECT repeat('0',64),repeat('0',64),source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state
 FROM ingest.county_geometry_correction LIMIT 1 ON CONFLICT DO NOTHING$q$,'Outside reviewed county cohort');
SELECT pg_temp.rejects($q$INSERT INTO ingest.county_geometry_correction(correction_id,source_audit_sha256,source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state)
 SELECT repeat('0',64),source_audit_sha256,source_id,27208875,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state
 FROM ingest.county_geometry_correction LIMIT 1 ON CONFLICT DO NOTHING$q$,'Outside reviewed county cohort');
SELECT pg_temp.rejects($q$INSERT INTO ingest.county_geometry_correction(correction_id,source_audit_sha256,source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,candidate_sha256,evidence_state)
 SELECT repeat('0',64),source_audit_sha256,source_id,object_id,source_input_sha256,source_feature_text,proposal_audit_sha256,review_audit_sha256,candidate_text,repeat('0',64),evidence_state
 FROM ingest.county_geometry_correction LIMIT 1 ON CONFLICT DO NOTHING$q$,'differs from exact reviewed source/candidate');
SELECT ingest.record_county_geometry_event(jsonb_build_object('event_id',repeat('a',64),'correction_id',correction_id,'status','withdrawn','actor','isolated test','note','withdrawal'),geometry_event_id) FROM fixture;
SELECT pg_temp.assert_true(c.correction_status='withdrawn' AND e.effective_geometry IS NULL AND e.effective_geometry_hold=e.original_geometry_hold
 AND e.effective_scope_relation=e.original_scope_relation AND e.effective_quality_flags=e.original_quality_flags
 AND NOT ingest.county_geometry_snapshot_is_current(f.sid,f.source_audit_sha256),'withdrawal restores source and stales snapshot')
 FROM fixture f JOIN ingest.county_geometry_current c USING(correction_id) JOIN ingest.effective_county_inventory e USING(correction_id);
-- Exact historical acceptance replay must not overwrite a later withdrawal.
INSERT INTO ingest.county_geometry_event(event_id,correction_id,expected_event_id,status,actor,note)
 SELECT e.event_id,e.correction_id,e.expected_event_id,e.status,e.actor,e.note FROM ingest.county_geometry_event e JOIN fixture f ON e.event_id=f.geometry_event_id ON CONFLICT DO NOTHING;
SELECT pg_temp.assert_true(correction_status='withdrawn','historical replay does not reactivate') FROM ingest.county_geometry_current WHERE object_id=27334504;
SELECT pg_temp.rejects($q$INSERT INTO ingest.county_geometry_event(event_id,correction_id,status,actor,note)
 SELECT repeat('b',64),correction_id,'accepted','test','stale' FROM fixture$q$,'review changed');
SELECT pg_temp.rejects($q$SELECT ingest.record_county_geometry_event(jsonb_build_object('event_id',repeat('a',64),'correction_id',correction_id,'status','accepted','actor','test','note','changed'),geometry_event_id) FROM fixture$q$,'ID reused');
SELECT pg_temp.rejects($q$INSERT INTO ingest.county_geometry_snapshot(snapshot_id,source_audit_sha256,dependencies)
 SELECT repeat('0',64),source_audit_sha256,'{}'::jsonb FROM fixture$q$,'dependencies changed');
INSERT INTO ingest.county_geometry_snapshot SELECT s.* FROM ingest.county_geometry_snapshot s JOIN fixture f ON f.sid=s.snapshot_id ON CONFLICT DO NOTHING;
SELECT pg_temp.assert_true(NOT ingest.county_geometry_snapshot_is_current(sid,source_audit_sha256),'historical snapshot replay stays stale') FROM fixture;
SELECT ingest.record_county_geometry_event(jsonb_build_object('event_id',repeat('c',64),'correction_id',correction_id,'status','accepted','actor','isolated test','note','reaccept'),repeat('a',64)) FROM fixture;
CREATE TEMP TABLE fresh_snapshot AS SELECT ingest.record_county_geometry_snapshot(source_audit_sha256) new_sid FROM fixture;
SELECT pg_temp.assert_true(NOT ingest.county_geometry_snapshot_is_current(sid,source_audit_sha256)
 AND ingest.county_geometry_snapshot_is_current(new_sid,source_audit_sha256),'reacceptance has new dependency') FROM fixture CROSS JOIN fresh_snapshot;
SELECT pg_temp.assert_true(bool_and(c.relrowsecurity),'private tables RLS') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='ingest' AND c.relname IN('county_geometry_correction','county_geometry_event','county_geometry_snapshot');
SELECT pg_temp.assert_true(NOT has_table_privilege(r,t,'SELECT,INSERT,UPDATE,DELETE'),'private relation '||t||'/'||r)
 FROM unnest(ARRAY['anon','authenticated','service_role']) r CROSS JOIN unnest(ARRAY['ingest.county_geometry_correction','ingest.county_geometry_event','ingest.county_geometry_snapshot','ingest.effective_county_inventory','ingest.county_geometry_current','ingest.county_geometry_snapshot_current']) t;
SELECT pg_temp.assert_true(NOT has_function_privilege(r,p.oid,'EXECUTE'),'private function '||p.proname||'/'||r)
 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN unnest(ARRAY['anon','authenticated','service_role']) r
 WHERE n.nspname='ingest' AND p.proname LIKE '%county%' AND p.proname NOT LIKE '%inventory%';
ROLLBACK;
