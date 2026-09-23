# Soil geometry acceptance

This private layer supports the **seven exact source versions reviewed in PR #59**.
It does not change original soil staging, qualify soil availability, or determine
septic suitability. Migration installs the layer; proposal loading and acceptance
are separate operations. No acceptance events are seeded by either the migration
or proposal-preparation script.

## Evidence boundary

`soil_geometry_study` pins the investigation's exact text/SHA-256, original soil
batch and county boundary WKB/hash. The initial validator allows only the reviewed
PR #59 investigation and PR #58 soil batch. `soil_geometry_correction` binds each
proposal to the source key, original input hash, archived response and source WKT
hash, plus the reviewed candidate's exact WKB/hash. The database verifies valid
2D MultiPolygon geometry, valid projected geometry, and all directed original
segments with multiplicity. The investigation records the independent native
containment evidence. Validity alone cannot authorize a correction.

Changing a candidate, source version or investigation requires a separately
reviewed extension. One candidate per source polygon is supported. Originals and
source holds remain append-only and available in `soil_record`. Investigation and
candidate bytes remain in private Storage; proposal preparation requires the
verified original bundle and archived candidate bytes.

## Acceptance and withdrawal

Administrative reviewers use
`ingest.record_soil_geometry_event(payload, expected_event_id)` with exactly
`event_id`, `correction_id`, `status` (`accepted` or `withdrawn`), `actor`, and
an evidentiary `note`. Initial review expects NULL; later reviews must supply the
latest event ID. A batch lock serializes changes before allocating event order.
Triggers enforce the same checks on direct inserts. Changed replay or stale review
fails. Exact historical replay does not restore an older acceptance after withdrawal.
No history may be updated or deleted.

`ingest.effective_soil_geometry`, **filtered to the intended report hash**, exposes
original and effective geometry, holds, county relations and provenance together
with correction, candidate and event versions. Accepted geometry is the default
for downstream use. An analytical override to the original requires a recorded
evidentiary reason and both versions. Raw inspection remains available.

Acceptance clears only the effective geometry hold and recomputes interior/touch/
outside relation against the pinned county boundary. Withdrawal restores original
geometry, relation and hold. Unaccepted proposals have no analytical effect.
Geometry remains DERIVED, site suitability UNKNOWN and
`qualified_for_parcel_screening=false`. This view is not an availability adapter.

## Downstream dependencies and coverage

Use READ COMMITTED transactions; the review and snapshot entry points reject other
isolation levels. In the same transaction as reading effective inputs, call
`ingest.record_soil_geometry_snapshot(batch_hash)` and retain its returned ID with
the downstream result. Its shared batch lock blocks review changes until commit.
A dependency snapshot records all proposals, candidates, original input versions,
review statuses and current event IDs. New proposals, withdrawal and reacceptance
invalidate earlier results, even if the same geometry is later reaccepted.

Before reuse, require
`ingest.soil_geometry_snapshot_is_current(snapshot_id, intended_batch_hash)`.
Missing snapshots, different batches and changed dependencies return false.
For atomic use/persistence, acquire the snapshot lock before checking and hold it
through commit. `soil_geometry_snapshot_current.needs_revisit` is useful for review;
it does not choose the intended source version. Consumers must implement this
protocol; unrelated result tables do not become dependency-aware automatically.

`ingest.soil_geometry_coverage(batch_hash)` acquires a snapshot, transforms effective
unheld interior geometry to EPSG:26919, recomputes the union and returns county area,
uncovered area, hold count, runtime and snapshot ID. Persist this returned result
with downstream audit evidence. It is a fresh calculation, not the hypothetical
proposal result from PR #59. The state is `full_geometric` only when the calculated
remaining area is exactly zero; any positive remainder is `partial_geometric`.
No rounding or tolerance clears a coverage gap. Different overlay runtimes may
produce different microscopic residuals; retain the actual result and runtime.
Even zero geometric gap is not a declaration of survey completeness or suitability.

## Operation and privacy

All new tables have RLS with no client policies. Tables, views, sequence and
functions are denied to public, anon, authenticated and service_role. Operations
require administrative database access. These controls protect application history;
a database administrator can still change the controls themselves.

Prepare proposal SQL locally without credentials:

```sh
python scripts/prepare_soil_acceptance.py \
  --bundle .local/county-soils-prepared-final \
  --analysis .local/soil-holds-analysis-final \
  --county research/piscataquis-ingestion/report.json \
  --output .local/new-soil-proposals
```

The output contains private geometry and stays outside Git. Its public preparation
manifest identifies every correction and hashes the migration and proposal SQL.
Proposal SQL is transactional and exact replay is harmless, including after later
withdrawal. It creates **zero acceptance events**.

Before live deployment, confirm the migration hash, source fingerprint and archive
readback; reconcile the unverified TL-F-0113 event from PR #59 by its exact event ID.
Keep diagnostic errors on any failure and stop rather than loop authentication.
Deploy the reviewed migration/proposals and record explicit acceptance events in a
separate controlled operation, then recompute coverage and append findings.
Units, scale, survey dates and attribute limitations remain separate qualification
work. Septic/buildability adjudication remains purchase-triggered.
