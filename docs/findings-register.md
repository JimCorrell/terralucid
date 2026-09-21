# Findings register

The register is in the existing private Supabase `ingest` schema. It tracks source
and ingestion deficiencies so they can be revisited without losing the original
evidence. These are operational data-quality findings, separate from future parcel
suitability findings and offer readiness.

## What is tracked

- `finding`: stable `TL-F-0001` style ID, title, description, affected sources,
  scope and evidence state. IDs must never be recycled.
- `finding_occurrence`: supporting audit/registry evidence or an affected record
  in a particular load. A new delivery adds evidence without replacing old evidence.
- `finding_event`: append-only status, priority, next action, reviewer, explanation,
  supporting references and timestamp.
- `finding_current`: the latest review, occurrence count and `needs_revisit` flag.

The [initial catalog](../research/findings/catalog.json) seeds **40 open findings**:
23 coverage/identity/geometry follow-ups and 17 remaining source-qualification
follow-ups from the original source audit. It is a seed definition, not a second
live status tracker. Status changes belong in Supabase history.

Priority is an operational review choice, not a parcel score: **high** blocks trusted
identity/coverage/geometry interpretation; **medium** needs source qualification
before a dependent use; **low** is a nonblocking documentation follow-up. Evidence
state (`VERIFIED`, `DERIVED`, `INFERRED`, `UNKNOWN`) is independent of workflow status.
No findings are automatically declared resolved by a successful import.

## Review and return to a finding

Read the current queue through an authorized administrative connection:

```sql
select finding_id,title,status,priority,next_action,occurrence_count,needs_revisit,event_id
from ingest.finding_current
where status <> 'resolved' or needs_revisit
order by case priority when 'high' then 0 when 'medium' then 1 else 2 end,finding_id;
```

Inspect evidence and history using the stable ID:

```sql
select * from ingest.finding_occurrence where finding_id='TL-F-0002' order by created_at;
select * from ingest.finding_event where finding_id='TL-F-0002' order by event_seq;
```

Record the next review using `scripts/prepare_finding_event.py`. It writes SQL for
inspection and does not connect or change the database itself. For example, replace
the placeholders with the current event ID and actual review information:

```sh
python3 scripts/prepare_finding_event.py \
  --finding-id TL-F-0002 --expected-event CURRENT_EVENT_ID \
  --status in_progress --priority high \
  --next-action "Compare the source record with municipal evidence" \
  --actor REVIEWER_NAME --note "Investigation started; no correction accepted yet" \
  --evidence "audit:REPORT_CHECKSUM#/code_name_conflicts" \
  --output .local/finding-review.sql
npx --yes supabase@2.117.0 db query --linked --file .local/finding-review.sql
```

Statuses are `open`, `in_progress`, `blocked`, `deferred` and `resolved`. Every review
requires an explanation and next action. Resolution additionally requires supporting
evidence references; a status change does not establish that a factual conclusion
is correct. Use `open` or `in_progress` with an explanation to reopen a finding.

The administrative function locks the finding and checks the expected event ID.
If someone reviewed it meanwhile, reread the latest state before submitting a new
event. Replaying the **same prepared SQL file** is safe. Earlier definitions, events
and occurrences reject updates/deletes; administrators could disable these controls,
so this is history preservation rather than tamper-proof storage.

New evidence after a resolution sets `needs_revisit=true`. It does not silently
rewrite the reviewer's status. Repeated identical ingestion adds no new occurrences
and does not reset statuses or next actions.

## Connecting new ingestion issues

Every record-level occurrence references the load and source record. From that
record, follow its response observation to the exact archived request/response.
The batch records source selection, method checksums and the reference audit used
for classification. Geometry defects also retain the PostGIS explanation.

The first load links code/name differences, overlap, repeated IDs, dates, missing
assessment matches, candidate code disagreements and geometry defects to existing
finding IDs. Existing issues outside the small load remain in the queue.

For a new issue category, add a new catalog ID and its evidence/next action, then
add the appropriate detection and occurrence mapping in the importer. Do not edit
old definitions to hide a previous conclusion or use the seed file to change status.
No refresh scheduler, notification policy or automatic resolution is configured.

The [Piscataquis County inventory](../research/piscataquis-ingestion/README.md)
adds **TL-F-0029** for county qualification and appends audit evidence to existing
coverage, identifier/date, overlap, geometry, zoning and NWI categories. Prior review
states are preserved. Holds and coverage gaps remain actionable after successful
loading; source retention does not resolve them.

The [county zoning hold investigation](../research/piscataquis-zoning-holds/README.md)
ranks the 162 zoning holds and investigates five cases. Three exact-version
interpretations are proposed, with acceptance still pending; all original holds
remain. TL-F-0029 tracks review/activation and remaining county qualification.

The [county proposal review](../research/piscataquis-zoning-review/README.md)
independently corroborates the three proposed interpretations. TL-F-0029 remains
in progress for a county correction layer and the remaining qualification work;
a favorable review does not activate geometry or remove original holds.

County geometry activation is recorded in the
[county correction evidence](../research/county-corrections/README.md). TL-F-0029
remains in progress: three reviewed representations can clear their effective
geometry holds while original holds and remaining county deficiencies persist.
No other finding is closed by this activation.

The [Moosehead Junction / Spencer Bay investigation](../research/moosehead-spencer/README.md)
identifies point-touching hole pairs and records two complete-feature proposals.
TL-F-0029 remains in progress pending their review; neither source hold is cleared
and no existing county acceptance is changed by this investigation.

The [fixed-candidate review](../research/moosehead-spencer-review/README.md) supports
both Moosehead Junction and Spencer Bay proposals for exact-version acceptance.
TL-F-0029 remains in progress pending the tested validator extension and activation;
current effective holds and the existing three corrections are unchanged.

The [Moosehead Junction / Spencer Bay activation](../research/moosehead-spencer-acceptance/README.md)
adds the two reviewed interpretations to the effective layer. TL-F-0029 remains
in progress for the remaining 157 zoning and 21 parcel geometry holds and other
county deficiencies. Refresh the prioritization against all five corrections
before selecting the next investigation group.
