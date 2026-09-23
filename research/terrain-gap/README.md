# Alternative terrain sources for the pilot gap

**Both inspected alternatives cover the entire 76,788 m² missing area from the
PR #66 pilot.** Either alternative plus the original Eastern B2 valid footprint
covers the diagnostic square geometrically. No elevations were merged and no
source preference or terrain qualification was activated.

## Discovery and bounded retrieval

The pinned county catalog returns three candidates intersecting the original
512 × 512 m AOI: Eastern B2 (the preserved base), Western Maine 2016 and Western
Mountains 2024. This is a search of the retained catalog, not a fresh exhaustive
publisher search. Fresh ScienceBase items, product XML, linked original project
XML and native TIFF headers were captured for the two alternatives.

Both alternative native extents enclose the AOI. Their one-meter EPSG:26919 grids
are offset from the original grid by approximately +0.000277 m east and
−0.000354 m north. These small offsets are preserved. A 513 × 513 native-pixel
window encloses the original square for each source; no resampling, snapping,
reprojection, datum conversion, interpolation or averaging was performed.

| Source | Source ID | Raster bytes retrieved, including header inspection |
| --- | --- | ---: |
| Western Maine 2016 | `6635c4e3d34edc29f40a1058` | 2,829,582 |
| Western Mountains 2024 | `6a753eb51ba49b79d0c34402` | 2,811,116 |
| **Total** | | **5,640,698 (5.64 MB)** |

The two independent preserved subsets are 776,095 and 778,103 bytes. Original
source rasters were not downloaded in full. The maximum raster budget was 32 MiB:
8 MiB per header inspection and 8 MiB per bounded pixel retrieval, for at most two
alternatives. Metadata and private archive upload/readback are accounted separately
in [the archive verification](archive-verification.json).

## Coverage comparison

The [comparison](comparison.json) converts each native valid-pixel mask into
pixel footprints and intersects them with the exact original AOI. It never aligns
arrays by index. All areas below are DERIVED square meters in EPSG:26919.

| Measure within original AOI | Western 2016 | Western 2024 |
| --- | ---: | ---: |
| Alternative valid area | 249,344.141778 | 249,344.141778 |
| Alternative missing area | 12,799.858222 | 12,799.858222 |
| Original gap covered | **76,788** | **76,788** |
| Original gap remaining | **0** | **0** |
| Area valid in both base and alternative | 172,556.141778 | 172,556.141778 |
| Alternative covers whole AOI alone | No | No |
| Base plus alternative covers whole AOI | **Yes** | **Yes** |

Each alternative covers about **95.1%** of the square. The original Eastern B2
source covers each alternative's remaining approximately **4.9%**. This establishes
complementary valid-pixel footprints for this bounded area; it does not establish
compatible elevations, accuracy, regulatory suitability or county-wide coverage.
Full coverage uses exact geometry containment and an empty residual; positive
residuals are not discarded using a tolerance.

## Source quality and remaining qualifications

The [metadata extract](project-metadata.json), [source report](report.json) and
[archive manifest](archive-manifest.json) retain official URLs and exact hashes.

| Evidence | Western Maine 2016 | Western Mountains 2024 |
| --- | --- | --- |
| Acquisition / ground-condition dates | 2016-04-05–2016-05-21 | 2024-10-17–2024-11-15 |
| Tile publication | 2024-05-02 | 2026-07-28 |
| Original horizontal reference | NAD83(2011), UTM 19, meters | NAD83(2011), UTM 19, meters |
| Original vertical reference | NAVD88 / Geoid12B, meters | NAVD88 / Geoid18, meters |
| DEM accuracy evidence captured | Measured NVA 0.113 m at 95% confidence; VVA 0.253 m at 95th percentile, project-wide | 10-cm RMSEz design class; measured DEM accuracy not established by this captured XML |

For each alternative, captured product start/end dates agree with linked DEM
ground-condition dates. Publication is a separate date. Standardized tile headers
still declare NAD83 without the original metadata's realization, and band units
are unset. The Eastern B2 detailed metadata/geoid questions from PR #64 remain
open. Similar filenames, common nominal NAVD88, or a newer acquisition date do
not establish that these elevations can be combined without qualification.

**Recommendation:** retain both alternatives as evidence. The 2024 source is a
candidate for further review because its acquisition is more recent; no default
is selected. Before adopting a source rule or deriving slopes across a source
boundary, qualify Eastern B2's original datum/accuracy evidence, the 2024 measured
DEM accuracy, and the required reference/grid treatment. Preserve source seams
and the original version-specific masks. No merged elevation surface is proposed
as accepted in this PR.

## Verification and retention

- Sixteen terrain tests pass, including native enclosing windows, rejection of
  outside requests, complementary footprints and a subpixel gap that must remain
  partial, alongside existing source-version and transfer controls.
- Both alternative subsets and retrieval reports reproduce exactly from hashed
  range bodies with network access forbidden; see [offline validation](validation.json).
- Raw response bodies, separate subsets, base subset, input versions, boundary,
  metadata and method files are retained in private object storage with verified
  download/readback. Raster contents are not stored as PostgreSQL rows.
- TL-F-0104 receives an append-only finding event: this pilot's original missing
  area has alternative coverage, while source qualification remains in progress.
  The finding is not resolved and existing unrelated date/metadata issues remain.

## Reproduction

Use the GIS runtime from PR #66 and new output directories:

```sh
python scripts/investigate_terrain_gap.py --output .local/new-terrain-gap
python scripts/terrain_project_metadata.py --evidence .local/new-terrain-gap --output .local/new-terrain-gap-metadata
python scripts/compare_terrain_gap.py \
  --base-subset .local/terrain-area-pilot-final/0-subset.tif \
  --alternatives .local/new-terrain-gap --output .local/new-terrain-gap-comparison.json
python tests/replay_terrain_gap.py --evidence .local/new-terrain-gap --output .local/new-terrain-gap-validation.json
python -m unittest discover -s tests -p 'test_terrain*.py'
```

The pilot subset and pinned county report are private inputs; archived equivalents
can be supplied through the relevant arguments. These scripts investigate this
bounded case, not a general multi-tile terrain availability service.
