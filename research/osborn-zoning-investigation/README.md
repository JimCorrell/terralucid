# Osborn zoning geometry investigation — TL-F-0025

## Conclusion

**A narrowly supported alternate decoding is proposed, not accepted.** The
original polygon and PR #10 screenings remain unchanged. The native Esri geometry
contains a permitted vertex self-touch; exporting it as one GeoJSON boundary ring
produces a polygon rejected by our GEOS/PostGIS validity checks. This is evidence
of a representation compatibility problem, not proof of an incorrect wetland
boundary on the ground.

This investigation follows merged PR #10 and examines only LUPC Osborn OBJECTID
**27232839**, P-WL2 (Scrub-shrub Wetlands). Its entire fresh GeoJSON feature is
identical to the original capture, and all attributes match across the three
retrieved representations. Legal zoning and currency remain **UNKNOWN**.

## Evidence and proposed interpretation

| Comparison | Observation |
| --- | --- |
| Original and fresh GeoJSON, EPSG:4326 | Identical feature; one invalid, self-touching ring. |
| Native Esri JSON, EPSG:26919 | One 345-coordinate closed ring; vertex `(555952.7400000002, 4957591.92)` occurs at zero-based positions 1 and 27, excluding the normal closing duplicate. |
| Native geographic response, EPSG:4326 | Same segment multiset as GeoJSON, with reversed winding. |
| Strict split at that vertex | One simple exterior and one simple, contained hole; boundaries meet only at the original vertex. Vertex locations and the boundary segment multiset are preserved; two closed rings require one additional closing-coordinate occurrence. |
| Native ring roles | Exterior clockwise, hole counterclockwise, consistent with Esri semantics. |
| Proposed GeoJSON | Valid Polygon, one hole; correct GeoJSON winding. No vertex movement, snapping, hole deletion, buffering or automatic repair. |
| Native candidate area | 114,022.954443 m²; exterior 115,481.444443 m² minus hole 1,458.49 m². Agreement with the publisher's area is internal consistency, not independent boundary evidence. |

[Esri's geometry specification](https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects/)
permits vertex touches and self-touches, describes exterior/hole winding and the
even-odd rendering rule. The narrowly constrained split expresses that same ring
linework as an explicit shell and hole. The algorithm rejects other arrangements;
it is not an ingestion fallback or a general repair policy.

There is an additional, unresolved **approximately 1.02 m projection difference**
between the service-native geometry and our locally projected geographic export.
The local operation and measured residual are recorded in `report.json`. The
service datum transformation has not been reconciled. The candidate preserves
the original EPSG:4326 coordinates exactly; native coordinates are corroborating
evidence, not replacement vertices. Cross-CRS coordinate equivalence is not claimed.

## Official map review

The newly captured [official Osborn map](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/osborn.pdf)
is byte-for-byte identical to the PR #10 map. Full-page, local-detail and notes
review corroborates the general P-WL2 wetland context. Embedded map coordinates
were used only to locate a visual crop; no boundary was digitized. The drawing
cannot independently certify the exact point contact or legal boundary.

The notes retain the Chapter 10/rule and ground-water-location dependencies and
protections omitted from the drawing. The latest listed 2024 amendment concerns
a clerical FEMA-reference correction. Those facts do not establish current
applicability for a parcel. `map-review.json` records the page, document checksum,
visual locator, observations and limits.

## Disposition and downstream use

- TL-F-0025 receives a new evidence occurrence and an **in_progress**, high-priority
  review. The original definition and prior events remain intact.
- The proposed geometry is an exact-version **DERIVED** interpretation, retained
  as a private checksum-addressed artifact. It has no acceptance event and is not
  part of the existing accepted property correction view.
- Original audit: `4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c`.
  Original feature: `814115b0ee3e4da18f393a9e163f71ac0072807fe307bb0d522a8684f30d4731`.
- The prior report identifies one assessment envelope candidate:
  `9b1ae8c797c956163c5951a71713f7dbb8518d159a03907d001cd6841e201307`.
  This is a possible dependency, not an adopted parcel overlap result.
- No geometry correction is activated, no prior result is rewritten and no
  canonical parcel or legal boundary is established. The original exclusion and
  incomplete-coverage warnings continue to apply.

**Next gate:** explicitly review and accept the exact-version interpretation in
an append-only geometry correction mechanism, then recompute dependent screening
as a new result version. Reconcile the projection difference before substituting
native-coordinate geometry or relying on cross-CRS boundary precision. Broader
LUPC currency/coverage questions remain with TL-F-0109.

## Reproduce

Use the existing Shapely 2.0.7 / GEOS 3.11.4 and pyproj 3.6.1 / PROJ 9.3.0
environment. New raw responses and `candidate.geojson` are ignored by Git and
archived privately. Plans, retrieval logs, map review, method and report are
reviewable in this repository. Historical PR #10 files are not changed.

Restore the new responses and the two original source locations from a verified
private archive download; the standard restore helper uses each response log:

```sh
python3 scripts/restore_private_evidence.py --audit research/osborn-zoning-investigation --download .local/osborn-investigation-download
python3 scripts/restore_private_evidence.py --audit research/zoning-ingestion --download .local/osborn-investigation-download
python3 scripts/restore_private_evidence.py --audit research/zoning-ingestion/capture --download .local/osborn-investigation-download
.local/conflict-venv/bin/python scripts/investigate_osborn_zoning.py
.local/conflict-venv/bin/python -m unittest discover -s tests
```

The method checks response hashes, exact original-feature identity, response CRS,
native ring roles, geometry validity, point-only contact, segment multiplicities
and the map-review checksum. Changed source values cause a stop for new review.
It reproduces the ignored candidate and the public report without network access.

To prepare a findings load, read the current review token through the authorized
Supabase administrative connection, then use a **fresh** preparation directory:

```sh
npx --yes supabase@2.117.0 db query --linked "select finding_id,event_id,status,priority,next_action from ingest.finding_current where finding_id='TL-F-0025';" > .local/osborn-current-finding.json
.local/conflict-venv/bin/python scripts/investigate_osborn_zoning.py --prepare .local/osborn-investigation-load --current .local/osborn-current-finding.json
```

Upload `objects/sha256` to the existing private bucket root. Download and verify
all manifest objects before applying `load.sql`, following
[source staging](../../docs/supabase-staging.md). This bounded SQL load fits the
administrative query route. It atomically adds a registry, six observations, an
audit report, one occurrence and one review event; no migration is required.
Replaying the exact prepared load preserves later review history. Stale review
tokens fail; reread the current state rather than replacing history.

## Verification

- 41 Python tests passed, including six new tests for the constrained split,
  rotation/reversal, exact segment preservation and rejection of unsafe patterns.
- An isolated PostgreSQL 17 / PostGIS 3.5.2 database confirmed the original is
  invalid and the candidate valid with one hole, with equal boundary linework.
- The isolated load/replay retained exactly six observations, one audit, one
  occurrence and one new review. A later synthetic review survived replay.
  No zoning feature or screening rows were inserted by this load.
- Synthetic checks were confined to the disposable database.

## Live audit checkpoint

Verified on 2026-09-20 UTC in Supabase project `yytsjlmbyqhcqfalbjca`:

- All 18 manifest objects were downloaded and checksum-verified before loading.
- Audit `1c37372f5957128a95b3a9d25a7a43286423cbf1ed8831d70bd305b90d933067`
  and six source observations are recorded. The candidate remains
  `proposed_not_accepted`.
- TL-F-0025 is **in_progress**, high priority, with two evidence occurrences.
  The register now has 42 findings and 58 review events.
- Original staging remains 2,058 source records and 737 assessment candidates;
  zoning remains 383 features and 2,648 screenings. The original target geometry
  is still marked invalid. The archive bucket remains private.

Use `scripts/check_osborn_investigation.sql` to inspect this checkpoint. These are
deployment observations, not ongoing monitoring or acceptance of the proposal.
