# Bounded Osborn wetlands feature load

The first queryable wetlands feature load uses the qualified historical NWI service
snapshot. It preserves **669 distinct wetland/deepwater inventory features**, all
**677 distinct joined lookup variants**, and **679 source-page occurrences**.
All 669 native geometries decode validly without repair. The load covers the
Osborn study-boundary envelope, including neighboring records. **499** had
positive-area study-boundary intersections in the original qualification audit.

This is not statewide Maine feature ingestion. The archived GeoPackage remains
separate; its identifiers and projected boundaries do not justify a general
service/package crosswalk. No canonical parcels or parcel screenings are created.

## Interpretations and remaining deficiencies

The eight previously resolved classifications use their exact reference-matched
variants by default. Native-core, geometry, selected-lookup and reference-row hashes
must match the TL-F-0027 review. All alternatives and original observations remain
available. The other 661 records use their sole observed service lookup; their
meanings have not gained an independent reference verification in this load.

Acceptance dependencies reference the existing Osborn Digital availability result.
A later availability withdrawal/reacceptance flags the batch for review. A changed
TL-F-0027 finding review or new occurrence flags the eight affected definitions and
removes their effective lookup until reviewed. Historical data remains intact.
See the [query contract](../../docs/wetlands-ingestion.md).

TL-F-0117 remains **in progress**. May 1983 imagery, later NHD supplementation,
package/service identity and projection differences, refresh, inventory completeness,
present-day conditions and legal applicability remain qualified. Empty inventory
space does not establish absence of wetlands. Inventory classification does not
establish P-WL, regulatory jurisdiction, septic suitability or buildability.

## Reproduction

`report.json` pins source/audit/method inputs, per-feature input checksums, imagery
lineage, runtime, limitations and review dependencies. Restore each input from the
private SHA-256 archive using its listed path/checksum. Captured responses remain
outside Git. The original source audit pins the already reconciled page membership;
this load rechecks exact page bytes, core grouping, lookup conflicts and geometry.
A live recapture is a new version requiring review.

```sh
.local/conflict-venv/bin/python scripts/prepare_wetlands_load.py \
  --output .local/wetlands-feature-load \
  --current .local/wetlands-feature-current.json
.local/conflict-venv/bin/python scripts/prepare_wetlands_load.py \
  --output .local/wetlands-feature-load \
  --verify-download .local/wetlands-feature-download
.local/conflict-venv/bin/python scripts/apply_prepared_load.py \
  --prepared .local/wetlands-feature-load \
  --download .local/wetlands-feature-download \
  --project-ref yytsjlmbyqhcqfalbjca
```

Fresh preparation requires current `finding_id`, `event_id`, `status` and
`needs_revisit` for TL-F-0027 and TL-F-0117. Archive and independently download/hash
verify every manifest object before applying. Apply the migration before the
atomic prepared load. The existing direct database loader avoids the management
API's large-request limit; temporary credentials stay in memory. The transaction
checks all 669 features, 677 variants and 679 occurrences before commitment. The
deferred database check also rejects an incomplete batch when the explicit check
is omitted. Exact SQL replay preserves later reviews.

Run `scripts/check_wetlands_load.sql` for read-only counts, qualifications and access
checks. Python tests cover classification review inheritance; `tests/wetlands_load.sql`
belongs only in a disposable PostGIS fixture with the prior audits, observations,
findings and availability acceptance loaded. Synthetic reviews must never run live.

## Applied checkpoint

Audit `5802819c4376110fcac2a58b3bdf652e82524472ae15ba62913a4375551f3d39`
is loaded in Supabase project `yytsjlmbyqhcqfalbjca`, after all **24 archive objects**
passed independent download/SHA-256 verification. Migration
`20260921020000_bounded_wetlands.sql` and the atomic feature load are applied.

Live readback confirms one batch, 669 valid EPSG:3857 geometries, 677 lookup variants,
679 occurrences and eight reviewed classifications. No feature has a stale
interpretation dependency or missing effective lookup. TL-F-0117 remains
**in_progress**, now six occurrences, with review event
`5d64e043d094f681edcb9b125c1410ac703ddd8295767bfff82093ead0590316`.
TL-F-0027 and TL-F-0028 remain resolved under their unchanged review events.

The bucket remains private; both new tables have RLS and client roles cannot read
the tables/view. Before/after fingerprints match for existing zoning geometry,
events, screenings/revisions, accepted availability geometry/events/results and
all finding events outside TL-F-0117. The audit reproduces byte-for-byte.

**80 Python tests pass.** In disposable PostGIS, all migrations and authentic prior
fixtures load successfully; the wetlands transaction also replays successfully.
SQL checks cover counts, unknown identities, altered replays, immutable history,
privacy, incomplete-batch rejection, classification reopening and availability
withdrawal. No synthetic review mutations were performed live.
