-- Add only the three PR36 exact versions. Its pinned combined audit contains
-- both proposals and separate fixed-candidate cycle/fill checks. Prior cohorts
-- retain their distinct proposal/review requirements and all history controls.
create or replace function ingest.validate_county_geometry_correction() returns trigger language plpgsql
set search_path=pg_catalog,ingest,extensions as $$
declare old ingest.county_geometry_correction%rowtype; f ingest.county_inventory_feature%rowtype;
 p jsonb; r jsonb; pc jsonb; rc jsonb; c jsonb; rings jsonb; feature_sha text; proposal_source_field text; checks jsonb;
 combined_review boolean:=false; audit_source_field text:='county_audit_sha256';
 recommendation text:='supported_for_exact_version_acceptance';
begin
 perform 1 from ingest.county_inventory_batch where audit_sha256=new.source_audit_sha256 for update;
 select * into old from ingest.county_geometry_correction where correction_id=new.correction_id;
 if found then
  if row(old.correction_id,old.source_audit_sha256,old.source_id,old.object_id,old.source_input_sha256,old.source_feature_text,old.proposal_audit_sha256,old.review_audit_sha256,old.candidate_text,old.candidate_sha256,old.evidence_state) is distinct from row(new.correction_id,new.source_audit_sha256,new.source_id,new.object_id,new.source_input_sha256,new.source_feature_text,new.proposal_audit_sha256,new.review_audit_sha256,new.candidate_text,new.candidate_sha256,new.evidence_state) then raise exception 'County correction replay differs';end if;
  new.geometry:=old.geometry;return new;
 end if;
 if new.source_audit_sha256<>'fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259' then raise exception 'Outside reviewed county cohort';end if;
 if new.object_id in (27334504,27249007,27291625)
 and new.proposal_audit_sha256='25f03b37818d1fc5cf25a6fa1e9264d48824c8585dbbf9776574dd6682905b6c'
 and new.review_audit_sha256='b7d02438499be17b55445bb5b2c5cd621cbe6f24182d238569524e0c9ab20cb7' then
  proposal_source_field:='county_feature_sha256';
 elsif new.object_id in (27208875,27336229)
 and new.proposal_audit_sha256='959a971c95dc6e81a1179d26f345eba9dc2fe9b908c40107f43272b27ef5d49a'
 and new.review_audit_sha256='6a649c0cfffedf0fde0d3790a6f44fc8a0990baa9e5e5b7e705f7569e513900a' then
  proposal_source_field:='source_feature_sha256';
 elsif new.object_id in (27304757,27270812,27207268)
 and new.proposal_audit_sha256='a4b734b5498166be9a802b3cdc4dd08c24567ac10bb9f6764962f187e346d797'
 and new.review_audit_sha256='a4b734b5498166be9a802b3cdc4dd08c24567ac10bb9f6764962f187e346d797' then
  proposal_source_field:='source_feature_sha256';combined_review:=true;
  audit_source_field:='source_audit_sha256';
  recommendation:='supported_for_exact_version_acceptance_after_validator_extension';
 else raise exception 'Outside reviewed county cohort';end if;
 select * into strict f from ingest.county_inventory_feature where audit_sha256=new.source_audit_sha256 and source_id=new.source_id and object_id=new.object_id;
 select document into strict p from ingest.audit_result where sha256=new.proposal_audit_sha256;
 select document into strict r from ingest.audit_result where sha256=new.review_audit_sha256;
 select v into strict pc from jsonb_array_elements(p->'cases') v where (v->>'object_id')::bigint=new.object_id;
 select v into strict rc from jsonb_array_elements(r->'cases') v where (v->>'object_id')::bigint=new.object_id;
 checks:=case when combined_review then rc->'independent_fill_check' else rc->'checks' end;
 c:=new.candidate_text::jsonb;feature_sha:=encode(sha256(convert_to(new.source_feature_text,'UTF8')),'hex');
 if f.input_sha256 is distinct from new.source_input_sha256
 or f.input_sha256 is distinct from encode(sha256(convert_to(f.input_text,'UTF8')),'hex')
 or new.source_feature_text::jsonb is distinct from f.data->'raw_feature'
 or f.data->>'hold' is null or f.geometry is not null or f.data->>'srid' is distinct from '26919'
 or p->>audit_source_field is distinct from new.source_audit_sha256
 or r->>audit_source_field is distinct from new.source_audit_sha256
 or (not combined_review and r->>'proposal_audit_sha256' is distinct from new.proposal_audit_sha256)
 or pc->>proposal_source_field is distinct from feature_sha
 or rc->>'source_feature_sha256' is distinct from feature_sha
 or pc->>'status' is distinct from 'proposed_not_accepted'
 or rc->>'recommendation' is distinct from recommendation
 or checks->'equals_independent_even_odd_fill' is distinct from 'true'::jsonb
 or checks->'all_segments_preserved_with_multiplicity' is distinct from 'true'::jsonb
 or checks->'symmetric_difference_m2' is distinct from '0'::jsonb
 or new.candidate_sha256 is distinct from encode(sha256(convert_to(new.candidate_text,'UTF8')),'hex')
 or pc->>'candidate_sha256' is distinct from new.candidate_sha256
 or rc->>'candidate_sha256' is distinct from new.candidate_sha256
 or c#>>'{properties,source_feature_sha256}' is distinct from feature_sha
 or c#>>'{properties,county_audit_sha256}' is distinct from new.source_audit_sha256
 or c#>>'{properties,object_id}' is distinct from new.object_id::text
 or c#>>'{properties,status}' is distinct from 'proposed_not_accepted'
 or c#>>'{properties,evidence_state}' is distinct from 'DERIVED'
 or c#>>'{crs,properties,name}' is distinct from 'EPSG:26919'
 or c#>>'{geometry,type}' is distinct from 'MultiPolygon'
 or new.correction_id is distinct from encode(sha256(convert_to(new.source_audit_sha256||':'||new.source_id||':'||new.object_id::text||':'||new.candidate_sha256,'UTF8')),'hex')
 then raise exception 'County correction differs from exact reviewed source/candidate';end if;
 if proposal_source_field='source_feature_sha256' and rc#>'{cycle_review,source_cycle_roles_preserved}' is distinct from 'true'::jsonb then raise exception 'Missing reviewed cycle roles';end if;
 new.geometry:=ST_SetSRID(ST_GeomFromGeoJSON((c->'geometry')::text),26919);
 if new.geometry is null or ST_IsEmpty(new.geometry) or not ST_IsValid(new.geometry) then raise exception 'Invalid county candidate';end if;
 select jsonb_agg(ring) into rings from jsonb_array_elements(c#>'{geometry,coordinates}') poly,
 lateral jsonb_array_elements(poly) ring;
 if exists((select * from ingest.county_segment_counts(f.data#>'{raw_feature,geometry,rings}') except select * from ingest.county_segment_counts(rings))
 union all (select * from ingest.county_segment_counts(rings) except select * from ingest.county_segment_counts(f.data#>'{raw_feature,geometry,rings}'))) then
 raise exception 'County candidate changes source segments';end if;
 return new;
end $$;
revoke all on function ingest.validate_county_geometry_correction() from public,anon,authenticated,service_role;
