# Moosehead Junction and Spencer Bay zoning investigation

Following merged PR #31, investigate held P-SL2 features **27208875** (Moosehead
Junction) and **27336229** (Spencer Bay). This is an exact-version investigation of
the preserved county capture and PR #29 native service, GeoJSON and official map
observations. It makes no new retrieval or legal-currency claim.

## Why the previous method stopped

Each feature combines supported shell/hole contacts with a different pattern:
**two counterclockwise hole loops touch at one existing vertex**. Neither loop
contains the other. The prior method deliberately required a nested shell and
hole with opposite winding, so it correctly withheld these cases.

| Feature | Previously unsupported source ring (zero based) | Touching hole areas |
| --- | ---: | --- |
| Moosehead Junction 27208875 | 163 | 4,226.690125 and 2,185.806025 m² |
| Spencer Bay 27336229 | 44 | 4,218.008974 and 2,988.456945 m² |

Moosehead rings 18 and 44 and Spencer ring 22 use the already supported nested
shell/hole interpretation. The new bounded method splits the two-hole rings only
at their existing repeated vertex. Both resulting loops must be valid, nonzero,
counterclockwise, and intersect **only at that point**. Complete-feature assembly
must establish valid shell ownership and preserve every original segment with
multiplicity. No coordinates are moved, added or deleted, aside from the necessary
repeated closure of separately represented rings. No snapping, smoothing,
`make_valid`, or guessed hole removal is used.

## Proposals and checks

Both complete candidates are valid and preserve all original boundary segments.
Their areas agree with the publisher's numeric field to within 0.000002 m², a
numerical cross-check rather than survey precision. Native service features match
the original county records exactly. The archived service GeoJSON variants have
the same segments and attributes but remain invalid; a format conversion alone
cannot clear these holds.

A separate ray-crossing algorithm classifies every face of the original linework
and compares its even-odd fill against the candidate. Both candidates agree across **560 faces** (272 Moosehead Junction, 288 Spencer
Bay), with zero symmetric-difference area. This uses a different interpretation algorithm,
but the same GEOS engine, and is not independent publisher or survey evidence.
`report.json` records face counts, exact candidates, checksums and diagnostics.

Eight targeted tests cover the valid two-hole interpretation and whole-feature
fill, and reject unsupported winding, shared edges, overlap, missing shell
ownership, altered coordinates, invalid dimensions and duplicate vertices. The
authentic complete-feature checks run in addition to these synthetic tests.

These are **DERIVED proposals, not acceptances**. Both original holds remain.
The existing three accepted county interpretations and their dependency snapshot
are unchanged. Extending acceptance requires review of these exact candidates and
a separately tested extension of the bounded county validator.

## Official map evidence

Both archived full-page maps and their notes were visually reviewed again:
[Moosehead Junction](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/moosehead-junction-twp.pdf)
and [Spencer Bay](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/spencer-bay-twp.pdf).
They show the P-SL2 and wetland context. Spencer Bay includes a western inset;
the township-wide document is not restricted to the feature's western PANEL label.
Recorded map adoption/effectiveness and amendments are carried from the pinned
prior map review. No map boundary was traced or used to certify the precise contact.

The map notes retain rule-dependent and omitted protections and the dependence of
some boundaries on water locations on the ground. Legal currency, applicability,
septic suitability and buildability remain UNKNOWN. The
[Esri geometry specification](https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects/)
provides winding and vertex-contact context; complete-feature validity and source
fill checks remain mandatory.

## Coverage scenario and findings

The scenario contribution is **5.4136 km²** for Moosehead Junction and
**4.8111 km²** for Spencer Bay, **10.2247 km²** combined.
Scenario areas in `report.json` use the original county gap **after subtracting the
three PR #31 accepted geometries**, pinned to that activation audit and dependency
snapshot. They are additional potentially usable geometry, not legal coverage.
The candidates are verified disjoint, so their gap intersections are disjoint too;
the combined number sums those intersections, equivalent to intersecting the union.
This addition is specific to this verified disjoint pair.
The effective baseline remains **159 zoning / 180 total holds**, with all 120,449
county records unchanged and no qualified parcel screenings.

TL-F-0029 stays in progress. Its next action is review of these two proposals;
remaining zoning, parcel, municipal-applicability and wetlands-age follow-ups
remain open. The private evidence archive and append-only finding event record
this investigation without changing source geometry or correction history.

## Reproduce

Restore the checksum-addressed inputs listed in `report.json` from the private
archive, including the original county report/pages, original gap cache and three
accepted candidates. Use the Shapely 2.0.7 / GEOS 3.11.4 investigation environment.
The prior independent-review report records the NumPy environment for its reused
ray-crossing method. Candidate geometries and PDFs remain outside Git.

```sh
python scripts/investigate_moosehead_spencer.py
python -m unittest discover -s tests -p 'test_moosehead_spencer.py'
python scripts/prepare_moosehead_spencer.py --output .local/moosehead-spencer-load
```

Upload prepared objects to the existing private archive, independently download
and checksum-verify them with `prepare_source_staging.py verify`, check the expected
finding event, then apply with `apply_prepared_load.py`. This metadata transaction
creates no geometry acceptance or schema change. Deployment evidence is recorded
in `checkpoint.json` and `live-verification.json` when complete.

## Deployment checkpoint

All **32 private archive objects** passed independent download/checksum verification.
The audit and append-only TL-F-0029 occurrence/review are loaded in Supabase, with
no new source observations. Live readback confirms both investigated features are
still held, all 120,449 original fingerprints are unchanged, and all three existing
acceptances and their dependency snapshot are unchanged. Effective holds remain
159 zoning / 180 total; other finding events are unchanged.
`checkpoint.json`, `live-verification.json`, and
`../../scripts/check_moosehead_spencer.sql` record these checks.
