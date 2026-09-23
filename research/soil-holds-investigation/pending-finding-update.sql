SET ROLE postgres; BEGIN; SET LOCAL statement_timeout='30s';
DO $check$ DECLARE v jsonb; r jsonb; b ingest.soil_batch%rowtype; k text; n integer; BEGIN
    select * into strict b from ingest.soil_batch where report_sha256='b31e3034caee9f70361bb9c769b936b8709fcab38706f89cdee22c9265aad512';r:=b.report_text::jsonb;
    select jsonb_build_object(
      'records',count(*),'row_fingerprint',encode(sha256(convert_to(string_agg(encode(sha256(convert_to(input_text,'UTF8')),'hex')||E'\n','' order by load_ordinal),'UTF8')),'hex'),
      'holds',count(*) filter(where hold is not null),'geometry_rows',count(geometry),
      'geometry_mismatches',count(*) filter(where geometry is not null and not extensions.ST_OrderingEquals(geometry,extensions.ST_GeomFromWKB(decode(input_text::jsonb->>'geometry_wkb','hex'),4326))))
      into v from ingest.soil_record where report_sha256='b31e3034caee9f70361bb9c769b936b8709fcab38706f89cdee22c9265aad512';
    if (v->>'records')::integer<>38237 or v->>'row_fingerprint'<>'ebc2f65c4dd137613517bfb6dbb0ea6ab5b4c1db4f6b2ab6e6a61739cf18661d' or (v->>'geometry_mismatches')::integer<>0
      or (v->>'holds')::integer<>jsonb_array_length(r->'geometry_holds') then raise exception 'Soil load fingerprint/state mismatch';end if;
    for k,n in select key,value::text::integer from jsonb_each(r->'counts') where key<>'prepared_records' loop
      if (select count(*) from ingest.soil_record where report_sha256=b.report_sha256 and kind=k)<>n then raise exception 'Soil kind count mismatch';end if;
    end loop;
    for k,n in select key,value::text::integer from jsonb_each(r->'polygon_relations') loop
      if (select count(*) from ingest.soil_record where report_sha256=b.report_sha256 and scope_relation=k)<>n then raise exception 'Soil scope count mismatch';end if;
    end loop;
    END $check$;
SELECT ingest.record_finding_event('{"actor":"Codex","event_id":"15341bf01555066e4fe0dd50479c8562db2dc0eefa06e0f68bbc9310fbc2a276","evidence_refs":["sha256:ddda7a3674c616b1eda8921cdf7581fe58aecfffd6e8c32bbebd49ed8ca6df8a; research/soil-holds-investigation/report.json"],"finding_id":"TL-F-0113","next_action":"Review seven exact-version proposals; implement a soil correction/acceptance layer before activation and recompute coverage. Retain strict partial coverage for any positive residual. Qualify units, scale, survey/source dates and missing attributes before enabling availability.","note":"Seven exact-version ring-touch proposals investigated. Official native geometry is valid for all seven; live WKT matches archived originals. All 28 native interior/hole containment controls agree. Every directed original segment is preserved. Three county-intersecting proposals account for the 41,125,705.83461925 m2 gap, leaving 3.2899763023218256e-9 m2 in a hypothetical overlay; four proposals lie outside county. Native WKB precision differences documented. Fifteen investigation objects archived privately and downloaded/hash verified. No proposals accepted, no geometry holds cleared, no availability or suitability promotion.","status":"in_progress"}'::jsonb || jsonb_build_object('priority',f.priority),f.event_id) FROM ingest.finding_current f WHERE f.finding_id='TL-F-0113';
SELECT jsonb_agg(jsonb_build_object('finding_id',finding_id,'event_id',event_id,'status',status,'next_action',next_action)) FROM ingest.finding_current WHERE finding_id = 'TL-F-0113';
select jsonb_build_object(
      'records',count(*),'row_fingerprint',encode(sha256(convert_to(string_agg(encode(sha256(convert_to(input_text,'UTF8')),'hex')||E'\n','' order by load_ordinal),'UTF8')),'hex'),
      'holds',count(*) filter(where hold is not null),'geometry_rows',count(geometry),
      'geometry_mismatches',count(*) filter(where geometry is not null and not extensions.ST_OrderingEquals(geometry,extensions.ST_GeomFromWKB(decode(input_text::jsonb->>'geometry_wkb','hex'),4326))))
      from ingest.soil_record where report_sha256='b31e3034caee9f70361bb9c769b936b8709fcab38706f89cdee22c9265aad512';

COMMIT;
