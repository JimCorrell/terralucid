# Piscataquis County source inventory

Scope: parcels, zoning, and wetlands across Piscataquis County, Maine, following
PR #27. This is a bounded data inventory and coverage evaluation; source features
are not canonical parcels or offer-ready properties.

## Evaluation

| Source | Valid positive-area county intersections | Held geometries in broader capture |
| --- | ---: | ---: |
| UT assessment parcels | 5,975 | 18 |
| Organized assessment parcels | 7,680 | 3 |
| LUPC zoning | 33,673 | 162 |
| NWI package wetlands | 58,584 | 0 |

The full inventory has **120,449 rows**, including boundary parts, project metadata,
outside capture candidates, touches and holds. Counts are source features, not
unique legal parcels. Every one of the 113 civil codes has some valid parcel-source
intersection; this does not prove complete coverage. **24 jurisdictions** intersect
both parcel sources, requiring identity/overlap review before deduplication.

**Wetlands:** 107 valid project footprints cover the county study boundary with
zero computed gap. All loaded wetland features have at least one positive-area
project candidate. Recorded imagery dates range from **May 1984 to May 1986**,
with April/October/November 1985 also represented. This resolves the bounded project
footprint check, not wetland completeness, currency or regulatory applicability.

**Parcel freshness:** among positive-area county intersections, 1,275 UT-source and
3,138 organized-source records have unknown parsed source dates. Many interpretable
dates are historical: the UT field ranges back to 1956, and 3,282 organized features
report April 2012. Map/update fields are evidence about their source, not current title.

**Zoning:** 162 original geometries are held (142 ring self-intersections and 20
ambiguous/uncontained holes). Missing usable overlay area must not be read as no
zoning; it can reflect held base-zone geometry, municipal coverage, different
jurisdiction applicability or source limitations. For example, valid LUPC polygons
cover only about 30.1% of Atkinson's study geometry in this capture. That is a
qualification warning, not a regulatory conclusion.

### Recommended next work

1. Investigate the held zoning geometries with the greatest potential coverage
   effect; distinguish decoding defects from actual source topology, comparing
   native representation and official maps before proposing any correction.
2. Review parcel identifier repeats, overlap and the 21 parcel geometry holds;
   prioritize records relevant to candidate areas. Preserve both source versions.
3. Inventory official municipal zoning routes where LUPC coverage is absent or
   insufficient; confirm applicability rather than inferring it from a town label.
4. Carry 1984–1986 wetland imagery qualification into candidate investigations;
   use newer evidence and field/regulatory review where a proposed use depends on it.

## Scope and evidence

- **Boundary:** DERIVED union of all 386 current Maine civil features whose
  `COUNTY` is `Piscataquis`, including water parts, across 113 source GEOCODEs.
  No organization-status filter. Civil `TYPE` values are preserved literally;
  they do not classify a jurisdiction as organized/unorganized. Archived GEOCODES
  status/notes are dated reference evidence with unresolved currency.
- **Parcels:** union of county attribute selection and county-envelope spatial
  selection from both UT and organized sources. Selected assessment identifiers
  and date fields are retained. Full native EPSG:26919 geometry is preserved,
  including outside/touching candidates. No cross-source identity merge, owner/title
  join, or assessment-table/valuation-book expansion is performed.
- **Zoning:** LUPC source features intersecting a 4×4 tiled county envelope, with
  all source dates/flags retained. The first whole-envelope count returned HTTP 504;
  bounded tile queries succeeded. IDs are reconciled per tile and deduplicated by
  exact source OBJECTID. This is not a legal-current filter or municipal zoning load.
- **Wetlands:** intersecting features from the previously archived Maine GeoPackage,
  with native EPSG:5070 coordinates and package project metadata. Original ZIP parts,
  extracted-file checksum, feature/blob hashes and table/OBJECTID provenance remain
  available. Spatial-index row membership is checked before extraction. No county
  service identity mapping or automatic transfer of Osborn acceptance is asserted.

Captures reconcile start counts/IDs, requested page IDs, end membership and metadata.
They are not atomic snapshots. Ambiguous, invalid, missing or unsupported native
geometry is retained under a hold. Held package envelope candidates may lie outside
the county; exact scope remains unknown until their geometry is interpretable.
No repair, snapping, clipping, geometry replacement or new correction acceptance.

## Storage and use

`ingest.county_inventory_batch` pins the private audit and study boundary.
`ingest.county_inventory_feature` preserves exact serialized inputs, per-feature
checksums, source properties/provenance, and usable native geometry.
`ingest.county_inventory` exposes explicit `scope_relation` and `geometry_hold`.
Filter by the intended audit. `interior`, `touch`, `outside`, and `held` have distinct
meanings; every row is marked `qualified_for_parcel_screening=false`.

Batches are immutable and sealed after their original transaction. A deferred check
reconciles counts and ordered source-ID/input-checksum fingerprints against the
audit, preventing incomplete or altered loads. Exact replay is safe; changed replay
is rejected. Tables have RLS and no client access. Original responses and the full
audit (including boundary coordinates) stay in the private checksum archive.

The public `evaluation.json` omits boundary coordinates and raw response contents.
Per-jurisdiction counts are spatial observations: crossing features can appear in
more than one jurisdiction. The valid LUPC union fraction is a geometric measurement,
not legal coverage, currency or completeness. Held geometry is excluded from that
fraction and remains a separate qualification. Project footprints do not establish
wetland absence, field delineation, legal jurisdiction, septic suitability or buildability.

## Follow-up tracking

TL-F-0029 tracks this county qualification. New audit occurrences link to existing
coverage, identifiers, dates, parcel overlap, geometry, LUPC, municipal zoning and
NWI findings. Prior reviews are preserved. County-wide manual reconciliation is not
a prerequisite for retaining evidence; dependent screening remains gated by its
specific source limitations and critical unknowns.

## Reproduction

Restore `capture.json` from the checksum in `evaluation.json` → `inputs`; the
large ID/page manifest remains in the private archive. Restore original captures
by first restoring the capture logs listed in `checkpoint.json` to
`runs/*/results.json`, then using those logs and private
`sha256/<hash>.response` objects with `scripts/restore_private_evidence.py`.
Reconstruct the original wetland ZIP from `package.parts`, verify its full checksum,
extract the recorded member, and verify the GeoPackage checksum. Use Python with
Shapely 2.0.7/GEOS 3.11.4 and pyproj 3.6.1/PROJ 9.3.0.

```sh
python scripts/prepare_piscataquis.py --output .local/county-load
python scripts/prepare_source_staging.py verify \
  --output .local/county-load --download .local/county-download
python scripts/apply_prepared_load.py --prepared .local/county-load \
  --download .local/county-download --project-ref yytsjlmbyqhcqfalbjca
```

Archive and independently download/hash-verify every manifest object before applying
migration `20260921040000_county_source_inventory.sql` and the atomic load. Run
`tests/county_inventory.sql` only in a disposable database after loading the authentic
fixture; it deliberately attempts changed replay, extra rows, deletion and a partial
batch. Never run synthetic mutation tests on the live project.

## Streamed first-load transport

For the larger county transfer, `scripts/repack_county_transfer.py` converts the
prepared feature INSERTs into COPY groups of 25. It checks every source ID and
input-text checksum against the same audit before producing a usable transfer.
`transport-verification.json` pins both SQL files and the transport method.
Source data and the audit are unchanged. The transaction's statement timeout is
disabled for this bounded administrative load; normal session settings resume at
transaction end.

```sh
python scripts/repack_county_transfer.py --prepared .local/county-load \
  --report research/piscataquis-ingestion/report.json --output .local/county-copy-load
python scripts/apply_prepared_load.py --prepared .local/county-copy-load \
  --download .local/county-download --project-ref yytsjlmbyqhcqfalbjca
```

COPY requires an empty county batch and rejects an already loaded audit before
mutation. Use the original prepared INSERT file for replay; do not partially append
or disable batch completeness checks. The full streamed load, empty-batch guard,
existing integrity checks and transport escaping tests passed in isolation.

## Validation and deployment checkpoint

Final private audit:
`fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259`.
All **694 archive objects** passed independent download/checksum verification,
including the reconstructed **437,448,614-byte** original Maine wetlands ZIP.
Raw captures and the complete audit are in the existing private source bucket.
`archive-manifest.json` lists the verified objects; `checkpoint.json` identifies
the archived retrieval logs. Large request/page manifests remain private to keep
the PR focused on methods and evaluation.

**105 Python tests pass.** The disposable PostGIS database passed every migration,
the full **120,449-row** load, exact replay, completeness rejection, altered-replay
rejection, batch sealing, geometry holds, privacy and immutable-history checks.
The original and optimized transfer reproduce identical per-feature fingerprints,
coverage evaluation and project lineage.

The user confirmed capacity and authorized the feature load before merging PR #28.
Migration `20260921040000_county_source_inventory.sql` and the full atomic load are
**applied in Supabase**. The first attempt rolled back during a server interruption;
a readback confirmed zero batches and features before retry. The cause of the
interruption was not established. A streamed COPY retry preserved every original
input fingerprint. See `transport-verification.json`. Readback confirms **120,449 feature rows**, all source
counts/checksum fingerprints matching the audit, **183 retained geometry holds**,
and zero unexpected geometry states or native CRS values.

During the retry, the server remained active while transfer slowed. Refreshing
planner statistics on the county feature table completed successfully and was
followed by faster transfer. A stale cached plan is a possible explanation, not a
verified cause. The full read-only verification exceeded the query service timeout
and passed in a separate read-only session with a ten-minute local timeout.

Live database size at verification: **1237 MB**; county feature table and
indexes: **1148 MB**. Tables/view remain private, RLS is enabled,
and the archive bucket remains private. The 694 source observations, 11 finding
occurrences and TL-F-0029 review were replayed without duplication. Prior accepted
geometry, screenings and review fingerprints are unchanged.

See `checkpoint.json` and `live-verification.json` for the deployment evidence.
`scripts/verify_county_load.sql` reproduces the full read-only load verification.
County geometry is now queryable through `ingest.county_inventory`, scoped to the
exact audit. It remains a source inventory, **not qualified parcel screening**;
geometry holds, source age, coverage gaps and legal unknowns remain unresolved.
Use `scripts/check_county_inventory.sql` for read-only follow-up checks.
