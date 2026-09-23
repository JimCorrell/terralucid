# Terrain elevation reference and measured accuracy

**The missing project metadata is now located, and measured DEM accuracy is
available for both Eastern B2 2017 and Western Mountains 2024.** This advances
source qualification; it does not establish local seam compatibility or activate
a merged terrain surface. TL-F-0104 remains in progress.

## Eastern B2: an explicit publisher link, not a name-based substitution

The exact pilot tile's legacy metadata is in the official
[one-meter project metadata directory](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Elevation/1m/Projects/ME_Eastern_B2_2017/metadata/).
Its tile identity, 10,012-cell dimensions and download filename agree with the
pilot source. That XML still delegates accuracy to original metadata.

The official [original-product index](https://thor-f5.er.usgs.gov/ngtoc/metadata/waf/elevation/opr_dem/geotiff/ME_Eastern_B2_2017/)
provides an explicit metadata link to
`ME_EasternME_2017_A17/ME_Eastern_B2_2017`. The official archive lists distinct B1,
B2 and TL work units under that parent. The B2 work unit's own DEM and project XML
were captured. This establishes the publisher's project linkage; no accuracy was
borrowed from B1 or inferred solely from similar project names.

The B2 DEM XML reports acquisition/ground-condition dates **2017-04-30 through
2017-12-04**, horizontal **NAD83(2011)**, and elevations in **meters referenced to
NAVD88 using GEOID12B**. The standardized tile header's generic NAD83 remains
preserved separately from original-project realization metadata.

## Measured DEM accuracy

These are **publisher-reported, project-level measurements**, not independent
remeasurement or accuracy guarantees at a candidate parcel.

| Source | Nonvegetated result | Checkpoints | Vegetated result | Checkpoints |
| --- | --- | ---: | --- | ---: |
| Eastern B2 2017 | Numeric XML NVA **0.099 m**; prose gives RMSEz **0.051 m** and **0.100 m at 95% confidence** | 176 | **0.255 m at the 95th percentile** | 123 |
| Western Mountains 2024 | DEM NVA **0.0647 m at 95% confidence** | 122 | **0.2023 m at the 95th percentile** | 31 |

Preserve the Eastern numeric/prose difference (0.099 versus 0.100 m) without
silently normalizing it. The Eastern vegetated tests include forested, shrub and
tall-weed categories. The 2024 report describes brushland/low-tree and tall-weed/
crop checkpoints; do not extrapolate these results to every forest condition.

For 2024, the January 5, 2026 contractor processing report, printed pages **19–20**
(PDF pages 22–23), describes DEM testing and Table 4. The table separately gives
**raw point-cloud NVA 0.0652 m**; that is not the DEM result. Acquisition remains
2024-10-17 through 2024-11-15; the report date is not an acquisition date.

The February 24, 2026
[USGS summary](https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/metadata/ME_WesternMtns_B24/ME_WesternMtns_1_B24/reports/USGS_ME_WesternMtns_1_B24_Summary_Report.pdf)
accepts the DEM and identifies work unit 301127, QL2, horizontal EPSG:6348,
vertical EPSG:5703 and GEOID18. Its generic accuracy paragraph states 9.8 cm at
95% confidence, whereas the contractor report uses a 19.6 cm NVA target and the
original XML gives a 10 cm RMSEz design class. Keep those publisher descriptions
separate; use the explicitly labeled measured table values above, not an invented
conversion that reconciles every label. This discrepancy is carried under TL-F-0104.

The final DEM review text inventories **6,115 original delivery tiles**, including
EPSG:6348 / NAVD88 / GEOID18 and one-meter cells. It is a raster-property review,
not the source of the measured checkpoint statistics. These original-delivery
headers are distinct from the standardized 10 km tile headers previously sampled.

## What this establishes about compatibility

Both projects declare **NAVD88 orthometric elevations in meters** and original
NAD83(2011) horizontal references. Eastern uses GEOID12B; Western 2024 uses GEOID18.
NOAA documents both models as connecting NAD83(2011) ellipsoid heights with NAVD88
orthometric heights. See [GEOID12B FAQ](https://www.ngs.noaa.gov/GEOID/GEOID12B/GEOID12B_FAQ.shtml)
and [GEOID18 technical details](https://www.ngs.noaa.gov/GEOID/GEOID18/geoid18_tech_details.shtml).

**Interpretation:** different geoid-model labels do not mean these stored DEMs
are in two different named vertical datums. Do not subtract a geoid-model difference
from already orthometric elevations merely to make labels match. A local offset,
if observed, can also reflect survey control, processing, acquisition differences
or actual terrain change. Its cause must be supported before correction.

**Recommended next check:** compare elevation residuals in the pilot's shared
valid area and inspect the prospective source seam. Record any diagnostic grid
alignment/resampling explicitly and keep originals intact. Evaluate bias, spread
and spatial structure; do not invent an acceptance threshold from the project
accuracy numbers. Then propose a source-selection and seam policy for review.
Slope calculation still needs documented grid, neighborhood, edge/NoData and
source-seam treatment. No source is activated by this metadata investigation.

## Evidence and retrieval limits

[Structured results](report.json) retain the XML fields, measured values, sample
sizes, page locators and verification limits. The [source manifest](sources.json)
records exact URLs, timestamps and hashes; original bytes and diagnostic renders
are retained privately with [archive readback verification](archive-verification.json).

The 2024 contractor PDF is **199,481,708 bytes**. Two capped partial-read attempts
were made; the first exhausted its budget and the second retained **8,378,732
bytes**. A full PDF parse did not succeed within that cap. A temporary sparse
reconstruction allowed the relevant printed pages 19–20 to be read and rendered;
unfetched page-tree branches produce a non-page-object warning. The complete table,
its heading, surrounding testing definitions, work-unit identification and footer
were visually inspected. We make no completeness claim for unavailable pages or
attachments. The sparse file is not archived as a complete source PDF.

The failed first attempt retained 8,368,099 bytes locally and is not part of the
analytical evidence archive. No further full-document fallback was used. Exact
successful ranges, their ETag and the derived page renders are archived; the small
USGS summary and Eastern XML were retrieved in full. No elevation raster was fetched
or modified in this investigation.

Replay the source-hash, XML-field and PDF table/context checks from retained bytes:

```sh
python scripts/review_terrain_accuracy.py \
  --evidence .local/terrain-accuracy \
  --ranges .local/western-report-ranges-v2 \
  --output .local/new-terrain-accuracy-review
```

This requires PyMuPDF and the archived private evidence folders, with a new output
directory. Review rendered pages visually; successful text extraction alone is not
a complete PDF integrity check. This is a research/replay helper, not a production
PDF downloader or a change to the terrain qualification adapter.
