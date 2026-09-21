# Review of the three county zoning proposals

Review following merged PR #29, for the exact county and proposal versions pinned
in `report.json`. **All three proposals are supported for exact-version acceptance
as DERIVED geometry interpretations. None is activated by this review.**

| Feature | Interpretation reviewed | Independent source faces checked | Conclusion |
| --- | --- | ---: | --- |
| Blanchard 27334504, P-SL2 | Existing self-touching shell and hole expressed separately | 323 | Supported |
| Atkinson 27249007, M-GN | Existing self-touching shell and hole expressed separately | 480 | Supported |
| Atkinson 27291625, P-SL2 | Nested holes assigned to innermost containing shells | 396 | Supported; also equals valid service GeoJSON |

## Evidence and independent check

The review verifies the proposal audit checksum, method dependencies, all archived
source/document checksums and each candidate's exact bytes, source identity and
native EPSG:26919 coordinates. Original county pages are checked directly against
the pinned county audit and compared in full with the reviewed native features.
It then compares the complete boundary-segment
multisets, including multiplicity.

A separate algorithm nodes the **original** ring linework and enumerates its
bounded faces. A horizontal ray-crossing calculation applies the source's even-odd
fill rule to an interior point of every face, without using the proposal's
shell/hole assignment method. The union of filled faces must equal the candidate,
with zero symmetric-difference area. All **1,199 faces** agree; the three candidate
geometries are valid and unchanged. Polygonization is a review diagnostic only;
it produces no replacement candidate or stored correction.

This is an independent algorithm, **not an independent geometry engine**: topology
operations still use GEOS. Four targeted tests cover ray crossing and vertex-height
rules, touching holes, nested islands, and rejection of removed or moved linework.
The authentic three-feature checks pass as well.

The review retains the earlier numerical area agreement and official-map context.
It does not re-establish map currency or make a new legal determination. No map
boundary was traced. Same-segment representation does not prove survey accuracy,
legal zoning, septic suitability or buildability. The roughly 79.23 km² scenario
from PR #29 remains a potential analytical coverage contribution, not active
coverage or permission to develop.

## What remains before activation

The existing Osborn correction tables and importer are explicitly bounded to that
source cohort. The county inventory has no accepted-correction interface. These
are the proposed requirements for the next implementation, applying the established
correction policy to this cohort:

1. Pin each proposal to the original county audit, source ID, OBJECTID, original
   serialized input checksum, reviewed proposal/review audits and candidate bytes.
   Reused OBJECTIDs or fresh captures must not inherit acceptance.
2. Keep proposals and acceptance/withdrawal events immutable. Use expected-event
   checks and locking to reject stale reviews; exact replay must not undo a later
   withdrawal or duplicate history.
3. Validate candidate provenance, native CRS, validity, exact source segments and
   the supported reviewed interpretation before an acceptance can take effect.
   Valid geometry alone is insufficient; altered candidates must fail.
4. Expose an effective county view retaining both original and effective geometry,
   original hold, effective hold, evidence state, source/candidate versions and
   review event. Accepted geometry becomes the default for its exact version;
   withdrawal restores the original held state. Unreviewed features remain held.
   Using original geometry instead of an accepted interpretation in analysis
   requires a recorded evidentiary reason and the source/correction versions.
5. Keep `qualified_for_parcel_screening=false`. Geometry acceptance alone cannot
   remove municipal applicability, source-age, parcel, legal or other holds.
   Any later overlay/result must retain correction-event dependencies and become
   stale when a dependency changes. There are no existing county screening results
   to silently recompute or relabel.
6. Test acceptance, withdrawal, stale review, changed replay, changed source,
   unsupported candidate, private access and immutable history in a disposable
   database. Verify unchanged original county fingerprints and the intended
   effective hold count before deployment.

If all three were subsequently accepted, the exact original cohort would retain
**162 original zoning holds**, with **159 effective zoning holds**. The 21 parcel
holds are unaffected. This is an expected future check, not current state.

## Tracking and deployment

TL-F-0029 remains **in progress**. The append-only review records support for the
three proposals and makes the correction-layer implementation the next action.
Other zoning, parcel, municipal-zoning and wetland-imagery work remains open.
The review is loaded in Supabase; **38 archived objects** passed independent
download/checksum verification. Live readback confirms unchanged fingerprints
for all 120,449 county rows, 183 total geometry holds and 162 zoning holds.
`checkpoint.json` and `live-verification.json` record deployment evidence.
No new source capture, geometry acceptance, schema migration, default change or
screening computation is part of this review.

## Reproduce

Restore the checksum-pinned PR #29 inputs and candidate files using its private
archive manifest. Use Shapely 2.0.7 / GEOS 3.11.4 and the NumPy version recorded in
this report. The prior source observations and registry are reused explicitly;
this review does not represent them as a new retrieval.

```sh
python scripts/review_county_zoning_proposals.py
python -m unittest discover -s tests -p 'test_county_zoning_review.py'
python scripts/prepare_county_proposal_review.py --output .local/county-proposal-review-load
python scripts/prepare_source_staging.py verify \
  --output .local/county-proposal-review-load --download .local/county-proposal-review-download
python scripts/apply_prepared_load.py --prepared .local/county-proposal-review-load \
  --download .local/county-proposal-review-download --project-ref yytsjlmbyqhcqfalbjca
```

Archive and independently download/hash-verify all prepared objects before loading
the review. Check the expected finding event before first apply. Use
`scripts/check_county_proposal_review.sql` for read-only deployment verification.
