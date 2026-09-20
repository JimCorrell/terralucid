# Bounded zoning ingestion

This pilot loads observed zoning evidence into private Supabase and produces a
reproducible screening result for **2,648 existing source records**. It uses accepted
corrections by default and retains the exact correction event used. No canonical
parcels, legal zone assignments or buildability conclusions are created.

## Results

| Input scope | Records | Result |
| --- | ---: | --- |
| Osborn, existing UT assessment source | 153 | 152 have observed overlaps; one has invalid source geometry and is excluded from calculation. |
| Kingsbury, existing UT assessment source | 170 | Municipal publication evidence captured; no qualified digital zoning coverage. |
| Sweden, correction layer | 691 | Uses corrected GEOCODE 17310; municipal PDF evidence only. |
| Alfred, correction layer | 1,634 | 1,633 use corrected GEOCODE 31020. One held record retains raw 31030 and its invalid geometry; no qualified municipal polygons. |

Captured **383 Osborn zoning polygons**: 382 valid and one invalid. The valid
polygons produce **651 positive-area intersections** with 152 assessment records.
All **2,495 records without qualified digital coverage** have unknown coverage,
not zero zoning. All **119 preexisting correction holds** remain attached.

Ninety-nine Osborn records are fully covered by the union of valid captured
polygons within a numerical tolerance of 1e-9; other usable records are only
partially covered (minimum about 0.26%). These are geometric coverage observations,
not regulatory completeness or boundary confidence. One record's envelope may
intersect the excluded zoning polygon. All Osborn results retain the source-gap
warning, even when the observed union covers their geometry.

## Source qualification

### Osborn / LUPC

The [LUPC publication page](https://www.maine.gov/dacf/lupc/plans_maps_data/digital_maps_data.html)
links its map table to the state map service. Its notes distinguish digital data
from official maps and warn about publication lag. The inspected
[Osborn map](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/osborn.pdf) shows
initial adoption/effectiveness in August 2005 and amendments through August 1,
2024. The latest listed amendment is a clerical FEMA-reference correction. This
explains the map index's 2024 display date without asserting that every polygon
was updated then.

The map explicitly warns that some wetland, stream-related and FEMA protections
are not drawn. Geographic overlap with displayed polygons cannot establish the
complete applicable zoning. The map and rule/ground-condition relationship remains
a due-diligence dependency.

The GIS capture retains every feature returned by the recorded predicate. All
383 have PUBLISH/DRAW=Yes and null END_DATE. Those values **do not establish an
authoritative current-zone predicate**. All publisher date fields, identifiers,
zone labels and raw geometries are preserved. Legal currency remains UNKNOWN.

Invalid polygon OBJECTID **27232839**, labeled P-WL2, has a ring self-intersection.
It is stored unchanged and excluded, with follow-up **TL-F-0025**. No geometry
repair or alternate decoding is accepted in this step.

### Kingsbury

Name queries found no Kingsbury record in the tested LUPC map index or zone
capture. A follow-up envelope query based on the previously published public Maine
assessment capture returned 95 polygons labeled Blanchard/Mayfield and neighboring
map-index entries. They are discovery evidence, not Kingsbury zoning inputs.

The [municipal resources page](https://kingsburyplantation.com/resources/) publishes
its own map and ordinance. The map's printed date is literally `11/115/2019`;
the ordinance cover has blank enacted/amended lines. A historical LUPC project
page's map link now returns 404. Current authority, adoption dates and authoritative
polygons require confirmation. Presence in a source called “Unorganized Territory
parcels” is not evidence that LUPC regulates the property.

### Sweden

The [municipal map page](https://swedenmaine.org/about-sweden/maps/) and
[code-enforcement page](https://swedenmaine.org/town-office/code-enforcement-officer/)
provide a map amended June 25, 2022 and a 2024 ordinance. The ordinance describes
the official map at the municipal office and its reduced appendix; the map warns
that district locations are approximate and require local/site determination.
No PDF tracing, pixel-based classification or machine-readable zoning polygons
are introduced. Publication does not certify that all subsequent amendments are
incorporated.

### Alfred

The [municipal code-enforcement page](https://www.alfredme.gov/departments/code_enforcement/index.php)
links to eCode360. The direct archive request returned HTTP 403 and its response
is preserved. No access-control bypass was attempted. Usable zoning polygons,
map/text currency and authoritative boundaries remain unqualified.

## Storage and interpretation

- Private Storage: exact GIS responses, publication pages, PDFs, failed HTTP
  responses, retrieval logs, input snapshots, method and report.
- `ingest.audit_result`: DERIVED report, qualification observations, date/currency
  caveats, input/method checksums and all screening results.
- `ingest.zoning_feature`: raw GIS features, archived response references and
  PostGIS geometries with explicit validity diagnostics.
- `ingest.zoning_screening`: immutable source/effective-property inputs, correction
  event references, observed intersections, unknowns and inherited holds.
- `ingest.zoning_screening_current`: flags `needs_revisit` if correction events,
  raw source geometry/properties or relevant source flags change. Historical
  results remain intact. This does not detect new external publications on its own.

The analysis reads `effective_properties` from the recorded correction-layer
export. Raw geometries remain unchanged. The held Alfred record is not silently
assigned a corrected jurisdiction. Municipal scope is retained as source context;
its raw conflicting code is visible in the report's effective-code counts.

Positive-area intersections are calculated in **EPSG:26919** (square metres).
Zero-area touches are recorded separately. Union coverage avoids double-counting;
per-polygon intersections can overlap and must not be summed as exclusive zoning
areas. Fractions are bounded to [0,1] for floating-point roundoff. There is no sliver
suppression, snapping or geometry repair. Every result records assessment-geometry
boundary dependency and UNKNOWN legal zoning. An empty polygon result never means
unregulated land.

Findings TL-F-0109 and TL-F-0110 receive append-only evidence/reviews; TL-F-0025
tracks the excluded zoning geometry. Existing deficiencies are not automatically
resolved by ingestion.

## Reproduce and verify

Use the existing conflict-analysis Python environment (Shapely 2.0.7 and pyproj
3.6.1) or install those pinned dependencies. PyMuPDF 1.24.14 was used for manual PDF
visual review; it is not needed to recompute the GIS report.

Raw new responses/PDFs are ignored by Git and retained privately. After downloading
the private checksum archive, restore both source locations:

```sh
python3 scripts/restore_private_evidence.py --audit research/zoning-ingestion \
  --download .local/zoning-download
python3 scripts/restore_private_evidence.py --audit research/zoning-ingestion/capture \
  --download .local/zoning-download
python3 scripts/prepare_zoning_ingestion.py --prepare .local/zoning-load
```

`analysis-inputs.json` is the versioned administrative export used by this report;
`export_zoning_inputs.sql` defines its bounded query. It contains source evidence
and review metadata, not credentials. A new export or capture produces a new audit
version; do not overwrite the committed historical artifacts. Before applying a
fresh preparation, read current findings and append their review tokens:

```sh
npx --yes supabase@2.117.0 db query --linked \
  "select finding_id,event_id,status from ingest.finding_current where finding_id in ('TL-F-0109','TL-F-0110','TL-F-0025');" \
  > .local/zoning-current-findings.json
python3 scripts/prepare_zoning_reviews.py --prepared .local/zoning-load \
  --current .local/zoning-current-findings.json
```

Upload the prepared `objects/sha256` directory to the private bucket root and
**download/verify it before loading**, as in [source staging](../../docs/supabase-staging.md).
Apply the new migration, then use `apply_prepared_load.py` for the prepared SQL
(the load exceeds the small Management API request limit). Audit, features,
results and reviews commit in one transaction. Replaying the same preparation is
safe; changed inputs/reviews fail and require deliberate recomputation/review.
Never rerun synthetic database tests on the live project.

Run `scripts/check_zoning_ingestion.sql` for acceptance counts and privacy checks.
Python tests exercise missing coverage, invalid geometry, overlapping zones,
boundary touches and correction guards. `tests/zoning_ingestion.sql` uses a
local disposable PostgreSQL/PostGIS database with previous prepared loads and
reviews: it independently checks a calculated area, stale dependency detection,
immutable results, conflicting replay and preservation of unknown coverage.
