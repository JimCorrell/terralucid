# First bounded source-record load

This load tests the ingestion workflow against known source-quality problems.
Its small scopes are implementation test cases, not property recommendations:

- UT parcel source: reported GEOCODE 09230 (Osborn) or 21110 (Kingsbury Plt).
- Organized parcel source: those reported codes, plus records labeled `Sweden`.
- Assessment source: every record returned by queries for the selected organized
  records' nonblank raw STATE_IDs, across the full assessment table.

The assessment projection contains identifiers and source/date fields, not owner
names or addresses. Exact selected attributes and source geometry are preserved;
this is not an extraction of every available source field.

## Results

| Source | Records |
| --- | ---: |
| UT assessment geometries | 323 |
| Organized assessment geometries | 1,001 |
| Assessment records | 734 |
| **Total** | **2,058** |

There are 737 exact-identifier candidate links and 264 organized records without a
candidate. Some geometries share an assessment candidate, so a single candidate per
geometry does not establish a global one-to-one relationship. All links remain
candidates; they do not establish title or canonical parcel identity.

PostGIS validation found 1,321 valid and three invalid geometries. The invalid
geometries remain unchanged, with validation reasons and linked findings. No geometry
was repaired or promoted to a surveyed/legal boundary. Assessment rows correctly
have no geometry.

The [findings register](../../docs/findings-register.md) seeds 40 open follow-ups and
links 3,313 record-level occurrences from this load, plus 40 initial audit/registry
occurrences. Repeated ingestion preserves the queue and any subsequent reviews.

## Source preservation and completeness controls

[plan.json](plan.json) fixes the scopes, selected fields, 25-record page size and
2,000-record cap per source. [The captured batch](2026-09-20/batch.json) records the
actual queries, selected object IDs and pages. Its 243 responses are archived with
retrieval time, exact URL, HTTP status, byte length and SHA-256.

For each scope the collector reconciles the service count with unique object IDs,
fetches by those IDs, checks every page for omitted/unexpected/duplicate IDs and
transfer-limit flags, then rechecks ID membership and available editing metadata.
It stops on an incomplete or changing result. No offsets or arbitrary first-page
cutoffs are used. The offline preparer repeats these controls and checksum checks.

These checks establish completeness **within the recorded source predicates**.
They do not establish municipality completeness, legal parcel completeness or an
atomic service snapshot; UT does not supply editing timestamps. Whitespace-only
keys are excluded from candidate queries; retained keys are matched exactly without
trimming, case folding or heuristic repair. Alternative identifier matches remain
open findings.

Each database record keeps source ID, batch/version, source OBJECTID, raw GlobalID,
raw identifiers, selected feature bytes in the archive, parsed date/precision and
quality flags. The batch-scoped row identity preserves records even when business
keys are missing or repeated. GlobalID refresh stability is still an open finding.

Quality flags quarantine issues for identity review: source records and candidate
links remain inspectable, but neither is a trusted canonical parcel crosswalk.
The civil reference is the dated audit from PR #4; its legal-effective dates remain
unknown. Reclassifying against a newer reference creates a new batch/version.

## Where the data lives

- Private Supabase Storage: exact responses, retrieval log, registry, batch plan,
  findings catalog, preparation summary and method/schema files named by checksum.
- `ingest.load_batch`: scope, controls, reference audit and method versions.
- `ingest.source_record`: independent source records, geometry and quality flags.
- `ingest.assessment_candidate` / `assessment_match_summary`: candidates and unmatched records.
- `ingest.finding*`: stable deficiencies, linked occurrences and append-only reviews.

All remain private, with RLS and no client grants. Source identity is not parcel
identity. No canonical parcels, ranking, AI adjudication or offer-readiness logic
is introduced.

## Reproduce and review

Offline, using fresh output directories:

```sh
python3 -m unittest discover -s tests
python3 scripts/prepare_bounded_ingestion.py \
  --capture research/maine-ingestion/2026-09-20 --output .local/bounded-load
```

Review the generated summary, SQL and object manifest. Then apply pending migrations,
upload artifacts to the **bucket root**, download to a fresh location and verify
before inserting database references:

```sh
npx --yes supabase@2.117.0 db push --linked --dry-run
npx --yes supabase@2.117.0 db push --linked
npx --yes supabase@2.117.0 storage cp --experimental --linked --recursive --jobs 4 --content-type application/octet-stream .local/bounded-load/objects/sha256 ss:///terralucid-source-snapshots/
npx --yes supabase@2.117.0 storage cp --experimental --linked --recursive --jobs 4 ss:///terralucid-source-snapshots/sha256 .local/bounded-download/sha256
python3 scripts/prepare_source_staging.py verify --output .local/bounded-load --download .local/bounded-download
python3 scripts/apply_prepared_load.py --prepared .local/bounded-load --download .local/bounded-download --project-ref yytsjlmbyqhcqfalbjca
npx --yes supabase@2.117.0 db query --linked --file scripts/check_bounded_ingestion.sql
```

The load helper requires Docker and an authenticated, linked Supabase CLI. It uses
a temporary direct database connection with credentials held in memory. The SQL
executes as one transaction; the HTTP query API rejects this 6.2 MB load with a
request-size error. The helper verifies the downloaded archive again before loading.

Run each command separately and stop on an error. A fresh database needs the prior
audit loads first; their registry and report foreign keys deliberately prevent an
unproven reference audit from being substituted. The original source audit and
coverage report remain unchanged.

For a new capture, run `scripts/collect_bounded_sources.py --plan
research/maine-ingestion/plan.json --output NEW_DIRECTORY`. A new capture or changed
preparation method is a new version. Retain the recorded collector version when
reproducing an older capture; do not replace files in an earlier run.

Fourteen Python tests cover membership, truncation, CRS, evidence integrity, date
precision, candidate multiplicity, review validation and connection targeting. `tests/finding_history.sql`
is for a **disposable local PostGIS database only**: it exercises immutable history,
resolution evidence, stale-review rejection, replay, new evidence after resolution,
reopening and geometry-error retention. Synthetic changes roll back. An additional
local replay confirmed that a saved review's status/next action survives ingestion.

## Live verification

Applied to Supabase project `yytsjlmbyqhcqfalbjca` on 2026-09-20 UTC. Batch
`53583bba4ab54f4774893ce9004b33a73302f9609f791d46f69506bfecd08816`
committed atomically. The live checks returned:

- 2,058 source records, 737 assessment candidate links and 264 unmatched records.
- 1,321 valid geometries, three invalid geometries and 734 assessment-only rows.
- 40 open findings, 40 initial history events and 3,353 evidence occurrences.
- RLS enabled on all staging tables; client access denied on the new tables/views.
- Private archive bucket; all 191 expected batch objects downloaded and verified.
- Earlier evidence retained: three registry versions, 398 response observations,
  three original geometry samples and one coverage report; 313 unique archived objects.

Replay and preservation of subsequent reviews were tested in the disposable local
database. Synthetic review events were not inserted into the live project.

## Remaining work

Use the findings queue to choose the next source-quality investigation. The first
load does not resolve code conflicts, source overlap, missing assessments, legal
boundary authority, source rights or statewide completeness. Larger loads should
retain the same controls and explicit unknowns.
