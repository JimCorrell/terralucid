# County soil staging load

This step follows merged PR #57 (`a6c5d4e`) and implements the authorized private
Supabase soil load. The source version is pinned to report
`b31e3034caee9f70361bb9c769b936b8709fcab38706f89cdee22c9265aad512`.
See [soil staging](../../docs/soil-staging.md) for table locations, guarantees,
reproduction commands and qualification limits.

## Deployment result — verified 2026-09-23

**Loaded and verified in Supabase.** The resumed record transaction completed in
175 seconds. Readback confirms 38,237 matching records, seven holds, 29,361 valid
geometry rows and zero geometry mismatches. All 82 database archive references
exist. Three tables have RLS, with zero client grants and zero client policies.
The existing county inventory still has 120,449 records. The soil record table and
indexes occupy 326,320,128 bytes; total database size at verification was
1,679,985,811 bytes. These sizes are observations, not future capacity guarantees.

## Preserved source inventory

| Source kind | Rows |
| --- | ---: |
| Legend | 7 |
| Map unit | 601 |
| Component | 1,572 |
| Horizon | 6,689 |
| Polygon | 29,368 |
| **Total** | **38,237** |

Among polygons, 20,571 are positive-area county intersections, 8,790 are outside
candidates and seven are held. Valid native geometry is retained on 29,361 rows;
held rows retain original WKT but have null analytical geometry. The pinned
preparation report's 99.627% valid coverage and 41.13 km² residual are unchanged;
loading does not determine the gap's cause or recalculate it as a new qualification.
No source repair, field suitability assessment, canonical parcel match, slope
calculation or availability-adapter activation occurs.

## Archive and database checks

- [Archive readback](archive-verification.json): all 84 objects (82 original bundle
  objects plus report and manifest), 160,604,821 bytes, downloaded and matched by
  SHA-256 and length. Existing objects are verified rather than overwritten.
- [Deployment inputs](deployment.json): pins batch, migration, generated SQL and
  ordered record fingerprint. Original private inputs remain outside Git.
- [Isolated integration tests](integration-tests.json): full-bundle load/readback,
  mutation/late-append rejection, duplicate rejection, client denial/RLS, and
  rollback on invalid geometry, hold, CRS and missing-parent cases. The corrected
  empty-batch response is checked as JSON as well. Six soil evidence tests pass.
- [Live verification](live-verification.json): records actual server readback,
  privacy and archive-reference checks, timings and continuing finding history.

Server readback recomputes every input hash from stored text and compares their
ordered fingerprint to the local bundle. It also compares every stored analytical
geometry to its pinned WKB. Parent foreign keys are checked before commit. Archive
hash downloads precede the transaction; their continued immutability is not
assumed. Tables and their source records are append-only through the provided
schema, with each batch sealed against additions in later transactions.

## Interrupted first attempt

[The first attempt](initial-attempt.json) applied the migration and stopped at
batch lookup before starting the record load: a plain PostgreSQL boolean was
incorrectly parsed as JSON. This was a client response-format bug, not an
authentication or source-data failure. The query now explicitly returns JSON;
the integration test was repeated. The resumed run checks the installed migration
hash and whether the batch already exists before loading or taking a readback-only
path. Neither the archive transfer nor the migration is repeated unnecessarily.

Archive transfer used one credential lookup. Each of the two database invocations
used one temporary credential lookup and one backend; there was no authentication
retry loop or direct Keychain access. Source originals and prior county records
were preserved. TL-F-0113 remains in progress, with the staging result appended
rather than resolving its seven holds or coverage/metadata questions.

## Next evidence work

Investigate the seven held soil polygons and the residual county gap, comparing
source representations without automatic repair. Qualify field dates, mapping
scale, attribute units and meaningful missing values before a soil availability
adapter is enabled. Terrain header/valid-pixel and project-overlap work remains
separate. Site-specific septic/buildability investigation stays purchase-triggered.
