# Supabase source staging

Supabase is the selected PostgreSQL/PostGIS host. The initial project is
[`yytsjlmbyqhcqfalbjca`](https://supabase.com/dashboard/project/yytsjlmbyqhcqfalbjca).
The project reference and API URL are public identifiers, not credentials.

## What is loaded, and where

| Location | Contents |
| --- | --- |
| Private Storage bucket `terralucid-source-snapshots` | Exact bytes of the registry, 34 source responses and three retrieval logs: 38 objects, named by SHA-256. |
| `ingest.registry_snapshot` | One versioned registry document containing 22 source descriptions, caveats and outstanding checks. |
| `ingest.source_response` | 34 retrieval observations: source IDs, exact request/log, retrieval time, HTTP status, outcome, checksum and Storage reference. The API error is retained. |
| `ingest.geometry_sample` | Three existing bounded GeoJSON samples decoded into PostGIS, with original features preserved. Two assessment samples and one zoning sample. |

This is the source audit loaded into the database. A statewide parcel load, identity
crosswalk, coverage denominator, canonical parcel schema, scoring and AI are later
work. An HTTP success or checksum match does not establish a property fact as VERIFIED.
Publisher dates remain in source metadata; retrieval and database load times are separate.

`ingest` is private and is not included in the configured Data API schemas. Client
roles have no schema/table privileges and every table has row-level security with
no client policies. Administrative CLI access performs this pilot import. Storage
has no public access or client policies. Do not add broad Storage policies or expose
`ingest` when building a future interface.

The importer preserves source identifiers and dates as received. It accepts the
existing geometry probes only when the request specifies `outSR=4326` and the response
has no conflicting CRS. It performs no geometry repair, parcel matching or boundary
promotion. Source geometry validity is reported separately.

## Repeat the bounded load

Requires Python 3.9+, Node/npm, an authorized Supabase CLI sign-in and project access.
Commands below use CLI 2.117.0. Keep credentials in the CLI credential store; never
put tokens, passwords or service keys in the repository. `.local/` is ignored.
Run commands individually and stop if any fails.

```sh
npx --yes supabase@2.117.0 login
npx --yes supabase@2.117.0 link --project-ref yytsjlmbyqhcqfalbjca
npx --yes supabase@2.117.0 db push --linked --dry-run
npx --yes supabase@2.117.0 db push --linked
npx --yes supabase@2.117.0 seed buckets --linked
python3 -m unittest discover -s tests
python3 scripts/prepare_source_staging.py prepare --output .local/source-load
npx --yes supabase@2.117.0 storage cp --experimental --linked --recursive --jobs 4 --content-type application/json .local/source-load/objects/sha256 ss:///terralucid-source-snapshots/sha256
```

Use a fresh output directory for a fresh preparation; an existing directory is
rejected to prevent stale upload files. Reuse a prepared directory for retries.
The preparation validates every response checksum and byte count before producing
SQL. The manifest specifies expected objects and counts. Storage filenames depend
on content; database observation identities depend on registry version, run and
retrieval log. Repeating the same import creates no additional rows.

**Before loading database references**, download the archive to a fresh directory
and compare every object with the prepared manifest:

```sh
npx --yes supabase@2.117.0 storage cp --experimental --linked --recursive --jobs 4 ss:///terralucid-source-snapshots/sha256 .local/source-download/sha256
python3 scripts/prepare_source_staging.py verify --output .local/source-load --download .local/source-download
npx --yes supabase@2.117.0 db query --linked --file .local/source-load/load.sql
npx --yes supabase@2.117.0 db query --linked --file scripts/check_source_staging.sql
```

Expected first-load report: 1 registry, 22 source descriptions, 34 responses,
1 API error, 3 valid geometry samples with SRID 4326, and all privacy checks true.
Repeat the load and report to check idempotence. The counts are acceptance controls
for this committed research batch, not statewide completeness measures.

Storage and PostgreSQL do not share a transaction: upload and verify first, then
load references in one database transaction. A failed SQL import can leave archived
objects without rows; retrying the same prepared load is safe. The bucket is private,
but not write-once: administrators can replace/delete objects. Reverify hashes when
reusing evidence. Never overwrite a mismatched object to conceal corruption.

## Initial deployment verification

Verified on 2026-09-20 UTC (September 19 in Maine) in the project above:

- Migration `20260920010000` appears in both local and remote migration history.
- All 38 uploaded objects were downloaded and matched their original SHA-256 and byte counts.
- The live acceptance report returned the expected 1 / 22 / 34 / 1 / 3 counts above.
- A second import left those counts unchanged; all three privacy checks passed.
- The Storage bucket is private, contains 38 objects and has no client object policies.
- Three offline integrity tests passed; the migration and repeated import also passed
  in an isolated PostgreSQL 17/PostGIS 3.5 database.

These are initial observations, not ongoing monitoring or guarantees about later changes.

## Scope and next gate

The migration and source data are versioned in Git. The PostGIS extension is installed
in `extensions`; an installation in another schema causes a stop for review. No
existing extension is moved. Local validation uses PostgreSQL 17/PostGIS 3.5 and
Supabase-equivalent client roles; live project checks also verify Storage privacy.

Before a larger load, finish the civil-code/coverage and candidate-key audit in
[the ingestion plan](ingestion-plan.md), validate publisher terms, and implement
pagination with count reconciliation and explicit failure handling. Bulk retention,
refresh scheduling, canonical identity and production access roles remain open.

References: [PostGIS](https://supabase.com/docs/guides/database/extensions/postgis),
[migrations](https://supabase.com/docs/guides/deployment/database-migrations),
[private buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals),
[API schema exposure](https://supabase.com/docs/guides/api/using-custom-schemas).
