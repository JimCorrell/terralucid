# Accepted NWI availability interpretation

The user approved activation after merged PR #22. The original national Digital
availability response and proposed decode remain archived unchanged. Acceptance
applies only to that exact source/candidate combination, with DERIVED evidence.

The accepted MultiPolygon has 93 exteriors and 74 holes, preserving every directed
source segment. See the [original investigation](../wetlands-availability/README.md)
for the diagnosis, official map comparison and decomposition evidence. That report
is a historical proposal checkpoint; current acceptance is recorded separately.

## What this enables

One PostGIS `ST_Covers` result for the exact archived FEMA Osborn study boundary,
CID 230595. This is inventory availability coverage, not a wetlands absence claim.
The national availability geometry is stored, but no statewide wetlands feature
load or parcel screening is introduced. May 1983 imagery, completeness, current
conditions and legal applicability remain qualified or UNKNOWN.

Use the [effective-geometry and coverage policy](../../docs/availability-geometry-corrections.md).
Withdrawal blocks new results and marks earlier coverage stale. Reacceptance
requires a new computation audit/result. Source changes require separate review;
no automatic upstream refresh is configured.

## Reproduction and verification

Restore the files identified by `report.json.inputs` from their SHA-256 keys in
the private `terralucid-source-snapshots` bucket. Fetch fresh finding event tokens
for TL-F-0028 and TL-F-0117 before preparing a new application:

```sh
.local/conflict-venv/bin/python scripts/prepare_availability_acceptance.py \
  --output .local/availability-activation-load \
  --current .local/availability-activation-current.json
.local/conflict-venv/bin/python scripts/prepare_availability_acceptance.py \
  --output .local/availability-activation-load \
  --verify-download .local/availability-activation-download
```

Independently download every manifest object and verify checksums before applying
the migration and atomic `load.sql`. The candidate is about 13 MB: the management
API rejected the single request with HTTP 413. For that transport, use a private,
RLS-enabled administrative transfer table with numbered text chunks (700,000
characters per request). Substitute ordered `string_agg` for the candidate literal
in the final transaction and drop the transfer table in that transaction. The
normal trigger checks the assembled candidate SHA-256 before acceptance; partial
transfers cannot create an accepted geometry. A failed transfer can leave only
private temporary staging data, which the operator must remove. Direct database
connections can execute the original prepared transaction without this workaround.

Lifecycle tests in `tests/availability_acceptance.sql` require a **disposable**
PostGIS database with the migrations, authentic prior audits/source response,
findings and acceptance load. Never run synthetic withdrawal tests against live
data. Tests exercise version rejection, access restrictions, immutability, stale
review tokens, withdrawal, exact/conflicting replay and reacceptance. The prepared
load was also applied twice in isolation to verify replay behavior.

## Applied checkpoint

All **10 archive objects** passed independent download/checksum verification before
activation. Migration `20260921010000_availability_acceptance.sql` is applied in
Supabase project `yytsjlmbyqhcqfalbjca`. The acceptance transaction committed one
geometry, one acceptance event, one computed coverage result and two finding reviews.
The transport staging table was dropped in that same transaction.

- Audit: `72c1e0f8114cc0f8c8cae6be84c3f575ca80758e1c640ecfa98704835dae56a2`
- Correction: `b8aa7aa5f0426c839d5b3b6ac5ce5dd596f369a25d96f3e09e8aa3d224b7808d`
- Acceptance event: `09edfbb9b213737aa6fdaedc5626b40dc51515401a3019408ffd72e2ef189b51`
- Coverage result: `9874844cb3788a81be34652585b6ffb70c57286d56b7959741dc660bca5ac07b`

Live readback confirms accepted/valid geometry, `geometry_hold=false`,
`digital_coverage=true` and `needs_revisit=false`. Runtime is PostGIS 3.3.7,
GEOS 3.14.1 and PROJ 9.7.1; the full runtime string is retained with the result.
TL-F-0028 is **resolved**, three occurrences; TL-F-0117 remains **in_progress**,
five occurrences. TL-F-0027's resolved event remains unchanged. None of these
finding reviews currently needs revisiting; their stated qualifications persist.

The archive remains private, all three tables have RLS, and client roles have no
read access to the new tables/views. Before/after fingerprints of zoning geometry,
geometry events, screenings and revisions match. The report reproduces exactly.
All **74 Python tests** and the isolated SQL lifecycle checks passed. No synthetic
withdrawal/reacceptance tests were performed on the live project.
