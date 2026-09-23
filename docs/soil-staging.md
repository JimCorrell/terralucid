# Private soil source staging

The initial county soil bundle is versioned by report SHA-256:
`b31e3034caee9f70361bb9c769b936b8709fcab38706f89cdee22c9265aad512`.
Its [preparation evidence](../research/county-soils-preparation/README.md) retains
originals, source geometry holds, boundary dependencies and coverage limits.
See [deployment verification](../research/soil-staging-load/README.md) for the
actual load status and readback results.

## Locations and contract

| Location | Contents |
| --- | --- |
| Private Storage bucket `terralucid-source-snapshots`, `sha256/<hash>.response` | Exact source responses, request history, captured county boundary, methods, report and manifest |
| `ingest.soil_batch` | Exact report text/hash, source manifest, ordered record fingerprint and load time |
| `ingest.soil_archive_object` | The batch's 82 source-object hashes, byte counts and private Storage references |
| `ingest.soil_record` | Original prepared text/hash, source keys and parent links, response hash/row ordinal, scope/hold state and valid source geometry |

Records remain source entities. Map units link to legends, components to map units,
horizons to components, and polygons to map units. All keys stay strings. The
record's `input_text::jsonb->'raw'` exposes the original returned attribute values;
`provenance` pins the source response and zero-based row ordinal. Full original
WKT remains in the raw polygon attributes. No soil/canonical-parcel identity
merge or interpretation rating is created.

Usable geometry is decoded in EPSG:4326 and must match the source WKT in coordinate
order. Held rows have null analytical geometry and retain their original WKT and
reason. The county relation and coverage report remain derived by the pinned
preparation method in EPSG:26919; they are not reclassified by the load. All 8,790
outside-county candidate records remain distinguishable from county intersections.

The schema is private: RLS enabled, no client policies, and no table privileges
for `anon`, `authenticated`, or `service_role`. Administrative PostgreSQL access
is required. Storage remains private; the existing service credential is used
only for authorized archive transport, never saved or printed.

## Load and integrity

1. Verify the prepared bundle, including every raw record against its archived
   source response. Prepare a streamed COPY transaction with expected counts,
   row fingerprint, parent constraints and geometry checks.
2. Upload objects without overwrite. Download every object and verify its exact
   SHA-256 and byte count before inserting database references. Include the report
   and manifest in Storage as well as the 82 original bundle objects.
3. Apply the tested migration with migration-history registration. Insert the
   batch, archive references and records in one transaction. Force parent checks
   and verify counts, holds, county relations, row fingerprint and geometry before
   commit. Any failure rolls back that load transaction.
4. Read back all-row fingerprints, geometry state, archive presence and privacy.
   The ordered fingerprint hashes each exact stored input text and then hashes
   the ordered sequence of those hashes. It complements the bundle's whole-file
   hash. Server checks compute hashes from actual stored text, not supplied hashes.

The database also rejects updates/deletes and additions to a batch in a later
transaction. A new source version requires a new report/batch. Reusing an existing
batch follows a verification-only path, and an installed migration must match its
recorded hash. The staging tables do not independently authenticate an administrator's
new evidence; the verified bundle and tested loader are the ingestion boundary.

Storage and PostgreSQL do not share a transaction. A failed load may leave valid
archived objects or an applied empty schema. Readback must establish state before
retry; no automatic write or authentication retries are implemented. Administrators
can still alter Storage objects, so reverify archived evidence before reuse.

## Reproduction

Use the project Python/Shapely environment, Docker, and the installed authenticated
Supabase CLI. Private source-bundle paths must be available locally.

```sh
python3 scripts/prepare_soil_staging.py \
  --bundle .local/county-soils-prepared-final --output .local/new-soil-deployment
python3 tests/check_soil_staging_sql.py \
  --deployment .local/new-soil-deployment --output .local/new-soil-tests.json
python3 scripts/transfer_soil_archive.py \
  --bundle .local/county-soils-prepared-final --output .local/new-soil-archive \
  --cli /path/to/supabase
python3 scripts/apply_soil_staging.py \
  --bundle .local/county-soils-prepared-final --deployment .local/new-soil-deployment \
  --archive .local/new-soil-archive --cli /path/to/supabase --output .local/new-soil-live
```

Each script requires a new output directory. Archive transfer uses one CLI key
lookup; database loading uses one temporary database-credential lookup and one
backend per invocation. No direct Keychain lookup is performed.

## Qualification remains separate

Seven source polygons remain held. Valid, unheld polygon coverage is approximately
99.627%, with a 41.13 km² residual. The
[held-polygon investigation](../research/soil-holds-investigation/README.md)
accounts for that gap through three of seven exact-source correction proposals,
leaving only a microscopic positive numerical remainder in a hypothetical replay.
The [authorized activation](../research/soil-correction-activation/README.md)
now accepts all seven proposals. Live effective coverage reports zero uncovered
area and zero effective holds; all seven original source holds remain unchanged. Null attributes,
component variability, source dates, scale and units retain their qualifications.
TL-F-0113 remains in progress. The qualification adapter still reports soils as
missing because it has no qualified source adapter; loading does not silently
change that status. No septic/buildability assessment or slope calculation occurs.
Terrain tiles were not loaded by this soil staging step.

The [soil geometry acceptance layer](soil-geometry-acceptance.md) provides explicit
review events and effective geometry without rewriting these original source rows.
The reviewed proposals are now activated in Supabase; use the current dependency
snapshot and retain all qualification limits.

The [soil metadata audit](../research/soil-metadata-qualification/README.md) now
qualifies a bounded unit dictionary, publication scales and version-date meanings,
and separates whole-survey from county-linked missingness. It proposes a limited
inventory availability adapter; no adapter is enabled by that audit. Preserve
component percentage deficits and exclude Vermont-specific septic interpretation
from Maine qualification.

The [soil availability adapter](../research/soil-availability/README.md) implements
those bounded checks for explicitly requested source/snapshot versions. It reports
inventory usability with limitations, not parcel qualification. A direct USDA
comparison corroborates the component deficits as source representation; unknown
minor components are neither invented nor normalized away.
