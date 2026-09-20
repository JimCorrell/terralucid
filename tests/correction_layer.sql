-- Disposable database only; all synthetic review changes roll back.
BEGIN;
DO $$
declare s ingest.correction_source%rowtype; held text; eid text; payload jsonb; original_event jsonb; failed boolean; props jsonb;
begin
  if (select count(*) from ingest.corrected_source)<>2325 or
     (select count(*) from ingest.corrected_source where correction_status='accepted')<>2324 or
     (select count(*) from ingest.corrected_source where holds<>'[]'::jsonb)<>119 or
     (select count(*) from ingest.corrected_source where effective_properties->'STATE_ID' is distinct from raw_feature#>'{properties,STATE_ID}')<>1595 then
    raise exception 'Unexpected correction scope';
  end if;
  select * into s from ingest.correction_source where proposal->'changes' ? 'STATE_ID' limit 1;
  select event_id into eid from ingest.corrected_source where correction_id=s.correction_id;
  select to_jsonb(e)-'event_seq'-'created_at' into original_event from ingest.correction_event e where event_id=eid;
  payload=jsonb_build_object('event_id',repeat('a',64),'correction_id',s.correction_id,'status','revoked','actor','Local test','note','Synthetic withdrawal');
  perform ingest.record_correction_event(payload,eid);
  perform ingest.record_correction_event(payload,eid);
  perform ingest.record_correction_event(original_event,NULL); -- Initial load replay must not undo withdrawal.
  select effective_properties into props from ingest.corrected_source where correction_id=s.correction_id;
  if props<>s.source_feature_text::jsonb->'properties' then raise exception 'Revocation did not restore raw properties'; end if;
  failed=false;
  begin perform ingest.record_correction_event(payload||jsonb_build_object('event_id',repeat('b',64),'status','accepted'),eid);
  exception when raise_exception then if SQLERRM<>'Correction changed since review' then raise; end if; failed=true; end;
  if not failed then raise exception 'Stale review accepted'; end if;
  perform ingest.record_correction_event(payload||jsonb_build_object('event_id',repeat('b',64),'status','accepted'),repeat('a',64));
  if (select effective_properties->>'GEOCODE' from ingest.corrected_source where correction_id=s.correction_id)<>'31020' then raise exception 'Reacceptance failed'; end if;
  failed=false;
  begin perform ingest.record_correction_event(payload||'{"note":"changed"}'::jsonb,eid);
  exception when raise_exception then if SQLERRM<>'Event ID reused with different content' then raise; end if; failed=true; end;
  if not failed then raise exception 'Conflicting replay accepted'; end if;
  select correction_id into held from ingest.corrected_source where correction_status='held';
  failed=false;
  begin perform ingest.record_correction_event(payload||jsonb_build_object('event_id',repeat('c',64),'correction_id',held,'status','accepted'),null);
  exception when raise_exception then if SQLERRM<>'No eligible correction proposal' then raise; end if; failed=true; end;
  if not failed then raise exception 'Invalid original accepted'; end if;
  failed=false;
  begin update ingest.correction_source set holds='[]' where correction_id=s.correction_id;
  exception when raise_exception then failed=true; end;
  if not failed then raise exception 'Source overwritten'; end if;
  failed=false;
  begin delete from ingest.correction_event where correction_id=s.correction_id;
  exception when raise_exception then failed=true; end;
  if not failed then raise exception 'History deleted'; end if;
  -- Trigger validation runs before unique-conflict handling.
  failed=false;
  begin insert into ingest.correction_source(correction_id,audit_sha256,source_id,source_snapshot_sha256,object_id,observation_sha256,source_feature_text,proposal,holds)
    values(repeat('d',64),s.audit_sha256,s.source_id,repeat('e',64),s.object_id,s.observation_sha256,s.source_feature_text,s.proposal,s.holds);
  exception when raise_exception then if SQLERRM<>'Correction source identity differs' then raise; end if; failed=true; end;
  if not failed then raise exception 'Different snapshot accepted'; end if;
  failed=false;
  begin insert into ingest.correction_source(correction_id,audit_sha256,source_id,source_snapshot_sha256,object_id,observation_sha256,source_feature_text,proposal,holds)
    values(repeat('d',64),s.audit_sha256,s.source_id,s.source_snapshot_sha256,s.object_id,s.observation_sha256,s.source_feature_text||' ',s.proposal,s.holds);
  exception when raise_exception then if SQLERRM<>'Stale or malformed proposal' then raise; end if; failed=true; end;
  if not failed then raise exception 'Changed feature accepted'; end if;
  select * into s from ingest.correction_source where holds<>'[]'::jsonb and proposal is not null limit 1;
  failed=false;
  begin insert into ingest.correction_source(correction_id,audit_sha256,source_id,source_snapshot_sha256,object_id,observation_sha256,source_feature_text,proposal,holds)
    values(repeat('d',64),s.audit_sha256,s.source_id,s.source_snapshot_sha256,s.object_id,s.observation_sha256,s.source_feature_text,s.proposal,'[]');
  exception when raise_exception then if SQLERRM<>'Exception holds differ' then raise; end if; failed=true; end;
  if not failed then raise exception 'Dropped holds accepted'; end if;
  if exists(select 1 from ingest.corrected_source where correction_status='accepted' and correction_evidence_state<>'INFERRED') or
     exists(select 1 from ingest.corrected_source where proposal#>>'{assessment_candidate,relationship_status}'<>'candidate_only') then
    raise exception 'Acceptance promoted evidence or candidate identity';
  end if;
  if (select count(*) from ingest.source_record)<>2058 or (select count(*) from ingest.assessment_candidate)<>737 then raise exception 'Raw staging changed'; end if;
end $$;
ROLLBACK;
