# County soils source bundle and terrain filtering

Prepared from merged PR #56 (`8142f13`) on 2026-09-23. This step captures and
validates source evidence and produces a private ingestion bundle. **The bundle
has not been loaded to Supabase and the soils qualification adapter remains
missing.** No source geometry was repaired and no septic/buildability assessment
was performed. Only the existing findings history was updated in Supabase.

## Soil coverage and source scope

The pinned county civil-boundary union is the study boundary, not an independently
verified legal county boundary. A USDA spatial query finds seven survey candidates
in its surrounding rectangle. All seven survey outlines have positive-area
intersections with the county, including narrow strips from adjoining surveys.
No area tolerance was used to remove those strips.

| Survey | Valid soil polygons with positive-area county intersection |
| --- | ---: |
| ME602 | 78 |
| ME612 | 166 |
| ME614 | 193 |
| ME615 | 6,277 |
| ME619 | 104 |
| ME620 | 13,715 |
| ME621 | 38 |

29,368 complete source polygons were captured in the surrounding rectangle:
**20,571** have positive-area county intersections, **8,790** are outside the
county and **seven are held** for source ring self-intersections. Held geometry
is excluded from analytical coverage; its original WKT and response remain intact.
A hold does not establish that the feature lies inside the county or identify
which part of the residual gap it might explain.

The union of valid, unheld county-intersecting polygons covers **99.62703%** of
the study boundary. The residual is **41,125,705.83 m² (41.13 km²)**. Its cause
has not been established; possible held-feature and boundary effects require
investigation. This is neither an unmapped-soil conclusion nor a suitability
result. No literal NOTCOM symbol/name match was found among valid intersecting
polygons; that check does not establish complete mapping or resolve the gap.

## Tables and limitations

The bundle preserves full returned rows for the seven candidate surveys:

- 7 legend rows, 601 map units, 1,572 components and 6,689 horizons.
- Keys are preserved as source strings, not converted to parcel identities.
- Counts reconcile to query controls; no duplicate primary keys or missing parent
  keys were found. All 601 map units have at least one component.
- 19 components have no horizon rows. Some attributes are null: 16 component slope
  values, 30 drainage classes and four horizon conductivity values, among others
  listed in the report. Water/miscellaneous units may legitimately lack some soil
  attributes; these are review observations, not automatic defects or rejection.
- Whole-survey tabular rows include out-of-county map units. Counts are not county
  soil-area statistics. Components are not separately mapped site boundaries.

An optional `mdstattabcols` query returned HTTP 400 after the feature/table
capture. The reason was not established. The capture resumed from checksum-verified
responses to complete catalog and polygon-membership drift checks; no source
responses were overwritten. Attribute units, mapping scale, field dates and
interpretation versions remain unqualified. Consult the publisher's separate
[Tables and Columns metadata](https://sdmdataaccess.sc.egov.usda.gov/QueryHelp.aspx)
before using these fields analytically.

USDA documents the [spatial query functions](https://sdmdataaccess.sc.egov.usda.gov/documents/AdvancedQueries.html)
and [JSON column-name response format](https://sdmdataaccess.sc.egov.usda.gov/WebServiceHelp.aspx).
The service-delivered WGS84 WKT is retained as received. Coverage uses an explicit
EPSG:4326 to EPSG:26919 transform; the original county geometry remains unchanged.
Catalog rows and polygon IDs agree before and after the capture. Sequential
requests are not an atomic publisher snapshot and cannot detect all in-place
attribute or geometry changes with unchanged IDs/catalog versions.

## Terrain narrowing

Of the 286 PR #56 catalog candidates, **248** rectangles have positive-area
intersection with the county and **38** do not. The retained advertised size is
**66,582,755,487 bytes (66.6 GB decimal)**, before resolving duplicate coverage and
project overlaps. Retained/excluded IDs and the input manifest hash are recorded.
This filters catalog rectangles, not actual valid pixels. No raster was downloaded,
no project was preferred, and no slope was derived. Header, acquisition-date,
accuracy, datum, NoData, overlap and storage checks remain next steps.

## Evidence and findings

[Report](report.json) records geometry holds, counts, null observations, projection,
method/runtime hashes, coverage and terrain membership. [Bundle manifest](bundle-manifest.json)
pins original response objects, prepared-record hash and report hash. Raw source
responses, source records and the private county boundary remain outside Git.

[Finding updates](finding-updates.json) records appended events to existing
**TL-F-0113** (soil qualification) and **TL-F-0104** (elevation qualification).
The soil event tracks the seven held polygon keys through this report and the
unresolved residual gap. Both remain in progress; neither was resolved. One
credential acquisition and one database session were used, with no source-data
writes or qualification promotion. The original seed catalog is not a live status
store and was not edited.

## Reproduce and deploy next

```sh
python3 scripts/collect_county_soils.py \
  --county-report research/piscataquis-ingestion/report.json \
  --output .local/new-soil-capture
python3 scripts/prepare_county_soils.py \
  --capture .local/new-soil-capture \
  --terrain research/soils-terrain-readiness/report.json \
  --output .local/new-soil-bundle
python3 scripts/verify_county_soil_bundle.py .local/new-soil-bundle
python3 -m unittest discover -s tests -p test_county_soils.py
```

The private county report must be available on the executing machine. A failed
capture can use `--resume`; cached queries and response hashes must match exactly.
A successful bundle has `objects/` keyed by SHA-256, `records.jsonl` (38,237 rows),
`report.json` and `manifest.json`. Each prepared row retains original source values,
response hash, source row ordinal, source key and relevant hold/scope state.
Survey outlines and catalogs remain in exact response objects. Local paths for
this run are `.local/county-soils-capture/` and `.local/county-soils-prepared-final/`.

**Next deployment:** add and test private source-staging tables plus a transactional
loader/archive transfer for this bundle. Reconcile every record and object hash
on readback and retain outside candidates/holds explicitly. This PR does not add
those tables or a loader and makes no live-availability claim. Investigation of
held polygons and the gap can proceed against these preserved originals. Enable
a county soils availability adapter only when its coverage/quality conditions are
explicit. Septic suitability remains purchase-triggered field due diligence.

Verification: six focused tests pass; a second preparation reproduced identical
record/report bytes. The [bundle verification](bundle-verification.json) checks
all archived object hashes and all 38,237 prepared rows against their exact source
response rows, plus identity/count/hold consistency.


Subsequent deployment: the [soil staging load](../soil-staging-load/README.md)
loads this exact bundle and verifies archive/record readback. The preparation-only
status above is historical; its holds, source qualifications and coverage result
remain unchanged.
