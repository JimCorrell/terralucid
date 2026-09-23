# Piscataquis soils and terrain: initial source readiness

Observed 2026-09-23 following PR #55. This is source preparation for the whole
county, including unorganized territories. No parcel was selected for purchase,
no suitability was assessed, and no soil geometry or elevation raster was loaded.
The qualification adapter correctly continues to report soils/terrain as missing.

## Verified catalog observations

### Soils

The live USDA Soil Data Access catalog returned 20 Maine surveys. Two names
explicitly identify Piscataquis coverage candidates:

| Survey | Published name | Map units | Components | Horizons |
| --- | --- | ---: | ---: | ---: |
| ME615 | Piscataquis County, Maine, Southern Part | 82 | 202 | 909 |
| ME620 | Northern Piscataquis and Northern Somerset County Area, Maine | 75 | 235 | 1,076 |

Counts are distinct keys across `legend → mapunit → component → chorizon` for
whole surveys, including their out-of-county portions. They establish that this
bounded join returns data, not that all keys are complete or that every county
location is mapped. ME620 must not be omitted merely because it spans counties.
Other adjoining surveys remain candidates until spatial intersection is checked.
Both catalog restoration dates are August 29, 2025; field dates, mapping scale,
attribute units and interpretation versions remain unverified.

The exact queries, retrieval times and hashes are in [report.json](report.json);
the two small public soil responses are retained beside it. USDA documents the
[query interface](https://sdmdataaccess.sc.egov.usda.gov/WebServiceHelp.aspx) and
[metadata/schema access](https://sdmdataaccess.sc.egov.usda.gov/QueryHelp.aspx).
These are preliminary source relationships, not a canonical parcel schema.

### Terrain

The existing county envelope in EPSG:26919 was transformed with densified edges
to EPSG:4326 for discovery. Its underlying county boundary hash is pinned in the
report. The USGS project-based **1-meter DEM** catalog returned 286 distinct
product IDs in this county-containing rectangle, reconciled to the advertised
286 total. Their advertised sizes total **76,790,982,207 bytes (76.8 GB decimal)**.
This is an upper discovery set, not the county's required download volume.

The returned paths span nine project groups, including Western Mountains B24,
MidCentral B23 and older projects. Complete product IDs, bounding boxes, metadata
links and download URLs are retained in the report. Rectangles do not prove valid
pixels or exact county coverage; overlapping projects cannot be blindly combined.
Publication dates and project names must not substitute for acquisition metadata.

The Maine 2024 DEM service describes the Western Mountains project, 1-meter cells,
NAD83(2011)/UTM19 horizontal reference, NAVD88/Geoid18 elevations in meters, and
spring/fall 2024 acquisition. Its extent and service name do not prove county-wide
coverage. Treat these as publisher statements pending tile/accuracy verification.
See the [Maine service metadata](https://gis.maine.gov/image/rest/services/DEM/Maine_Elevation_DEM_2024/ImageServer).

USGS distinguishes project-based DEMs from its newer seamless 1-meter product.
The latter must be evaluated separately if considered; it was not included in
this query. See [USGS product descriptions](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services)
and [seamless 1-meter product](https://www.usgs.gov/3d-elevation-program/new-product-3d-elevation-program-seamless-1-meter-digital-elevation-model-s1m).
No raster product or resampling/slope method is selected by this assessment.

## Recommended next implementation

1. **Soils first:** capture survey boundaries intersecting the exact pinned county
   boundary, including adjoining surveys. Retrieve source-preserving map-unit
   geometry plus map-unit/component/horizon tables for that verified set. Preserve
   native identifiers as strings and keep originals, units, versions and hashes.
   Evaluate polygon validity, unmapped/NOTCOM areas, county coverage, orphan keys,
   null attributes and component variability. Preserve holds and unresolved gaps.
2. **Terrain in parallel as a data-preparation workstream:** narrow the 286 catalog
   candidates to the actual county, inspect project metadata, acquisition dates,
   datum/units and accuracy, and compare overlaps. Sample raster headers and
   valid-data masks before a full download. Define edge/NoData and source-choice
   rules before deriving slopes. Keep any seamless-product comparison explicit.
3. **Proposed storage:** source metadata, soil vector/tabular data and tile/version
   manifests in private Supabase/PostGIS; evaluate private object storage for DEM
   files after estimating the reduced footprint and storage cost. This is a
   proposal, not an enacted raster storage policy or a capacity commitment.
4. Enable availability in the qualification adapter only after coverage and quality
   evidence is recorded. Attach discovered defects to the private findings register;
   pending checks alone are not defects and receive no invented TL-F identifiers.

Septic feasibility, usable building areas and parcel slope assessments remain
purchase-triggered due diligence. Available soil maps/elevation never establish
site approval. No slope threshold, scoring weight or septic rating is chosen here.

## Reproduction and retained evidence

```sh
python3 scripts/probe_soils_terrain.py \
  --county-capture research/piscataquis-ingestion/capture.json \
  --output .local/new-soils-terrain-probe
```

Use the existing project Python environment with pyproj. The county capture is
private/ignored and must be available on the executing machine. The script uses
public read-only requests, retains exact responses locally and reconciles terrain
pagination/unique IDs. No Supabase credentials are needed. Queries are not an
atomic publisher snapshot; future runs may differ. Full terrain and Maine raw
responses remain in `.local/soils-terrain-readiness-v2/`, pinned by hashes in the
committed report; the product manifest and relevant service fields are public here.
