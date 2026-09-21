# Bounded Maine package load

The user authorized this load after merged PR #25. It stores the **669 package
features** qualified by the Osborn comparison separately from the existing service
inventory. All original package attributes and exact GeoPackage geometry blobs are
retained, including OBJECTID, NWI_ID, ATTRIBUTE, WETLAND_TYPE, QAQC_CODE and ACRES.
Reported source ACRES is preserved as supplied, not independently certified acreage.

Each record has one **INFERRED candidate link** to its reviewed service feature,
with the comparison audit, service feature checksum and original distance/overlap
metrics. This is not an accepted identity crosswalk. The measured 1.024–1.026 metre
displacement is not corrected. Existing service defaults and geometries are unchanged.
The full 587,644-row Maine package has not been ingested or qualified statewide.

## Native geometry and CRS

The exact 437,448,614-byte ZIP and extracted GeoPackage hashes are checked before
reading SQLite in read-only mode. Package SRS ID 300001 is local to that GeoPackage.
Its recorded WKT is equivalent to EPSG:5070 under the pinned pyproj/PROJ runtime.
PostGIS assigns EPSG:5070 to the original WKB coordinates without transforming them.
The original header/blob and WKT remain available, preserving that source context.

The bounded database decoder checks the expected GeoPackage header, original
blob checksum, valid/nonempty MultiPolygon and row identity. It fails on another
header representation or unreviewed candidate instead of repairing geometry.
The load manifest pins each complete input, including attributes and candidate
metrics. Deferred completeness checks prevent a partial 669-record batch from
committing. Tables are immutable; exact replays are no-ops and altered replays fail.

## Query contract

Use `ingest.wetlands_package_current`, filtered to the intended package load audit.
The view exposes native package geometry, raw attributes, comparison metrics,
`identity_state=INFERRED`, source/service/comparison versions and limitations.
`candidate_service_effective_lookup` is explicitly the candidate service's effective
interpretation, not an independently verified package definition. Read
`needs_revisit` before using that linkage: it inherits classification and accepted
availability dependency status from the service feature. Classification reopening
flags the eight reviewed definitions; availability withdrawal/reacceptance flags
all 669. Raw package geometry remains available for audit.

No default union, deduplication, replacement or parcel join is introduced. Consumers
must choose and record their source version and preserve boundary differences.
Later upstream snapshots and contradictory comparison evidence require a new
review; there is no automatic refresh or generic identity acceptance mechanism.
The current view tracks existing service review dependencies, not every possible
future source publication or change to TL-F-0117. Administrative users can bypass
normal database controls; downstream users must honor the documented qualifiers.

TL-F-0117 remains in progress for projection cause, persistent identity, wider
package geometry/project coverage, imagery refresh, completeness and legal
applicability. The comparison inherits the service's May 1983 imagery qualification;
this load does not independently associate package project metadata to each feature
or establish newer imagery. Release dates are not imagery dates. Inventory evidence
does not establish wetland absence, P-WL, jurisdiction, septic suitability or buildability.

## Reproduction

Restore the report's `inputs` from their private SHA-256 archive keys. Reconstruct
`package.parts` in offset order and verify the original ZIP checksum, then extract
the specified member to `research/wetlands-classification/package/maine.gpkg` and
verify its checksum. Preserve original sources and use a separate extracted copy.

```sh
.local/conflict-venv/bin/python scripts/prepare_wetlands_package_load.py \
  --output .local/bounded-package-final-load --current .local/package-load-current.json
.local/conflict-venv/bin/python scripts/prepare_wetlands_package_load.py \
  --output .local/bounded-package-final-load --verify-download .local/bounded-package-download
.local/conflict-venv/bin/python scripts/apply_prepared_load.py \
  --prepared .local/bounded-package-final-load --download .local/bounded-package-download \
  --project-ref yytsjlmbyqhcqfalbjca
```

Read the current TL-F-0117 event before preparing. Independently download/hash-verify
the manifest and reconstructed original ZIP before applying the migration and atomic
load. The database requires current service dependencies for a new batch. Run SQL
lifecycle tests only in a disposable fixture; synthetic reviews must never run live.

## Applied checkpoint

Audit `6703cb4fd92661c09a4baadc1daee77b86ef1f20dff2155bdae2dfcf74ccce02`
is loaded in Supabase project `yytsjlmbyqhcqfalbjca`. Migration
`20260921030000_wetlands_package_load.sql` and the atomic data/review transaction
are applied. All **20 archive objects** passed independent download/SHA-256 checks,
including reconstruction of the original 437,448,614-byte ZIP.

Live readback confirms **669 valid native EPSG:5070 geometries**, **669 exact blob
checksums**, **669 INFERRED links** and zero stale dependencies. Tables have RLS,
client roles cannot read the tables/view, and the archive bucket remains private.
Use `scripts/check_wetlands_package_load.sql` for the read-only checkpoint.

TL-F-0117 remains **in_progress**, with eight occurrences, under review event
`05cc04f04194f3e7fb4ea0c265340828ced3759ffeaa803d5eeb07bd1995d0b2`.
TL-F-0027/0028 resolution events are unchanged. Before/after fingerprints match
for existing service batches/features, availability geometry/events/results,
zoning geometry/events/screenings/revisions and other finding events.

The report reproduces byte-for-byte. **92 Python tests pass.** Disposable PostGIS
checks passed for all migrations, authentic fixtures, package load/replay, exact
blobs/native CRS, inferred identities, privacy, immutability, incomplete-batch
rejection, classification reopening and availability withdrawal. Synthetic review
changes were tested only in the disposable database.
