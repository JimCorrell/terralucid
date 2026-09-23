# Piscataquis terrain readiness

**Readiness: proceed to a bounded raster pilot, not county availability or slope
qualification.** This review uses the pinned PR #57 county candidate selection.
No full DEM was downloaded or loaded, no source priority was activated, and no
parcel was assessed. TL-F-0104 remains in progress.

## What was checked

The 248 retained catalog products span **eight projects** and advertise
**66,582,755,487 bytes** (66.6 GB). There are 168 exactly distinct catalog
rectangles: 105 listed once, 54 twice, one three times and eight four times.
These are exact floating-coordinate comparisons, not a count of unique ground
coverage or a deduplication rule. Near-equal rectangles and partial overlaps remain.

One representative per project (the first retained product in pinned catalog order)
was inspected. Each had nine native blocks sampled at the corners, edge midpoints
and center block positions. The total raster transfer was **14,384,382 bytes**.
Requests require exact HTTP ranges, an unchanged ETag and an 8 MiB per-raster cap.
Sparse reconstructions are temporary diagnostics, never archived as source DEMs.

All eight sampled headers report 10,012 × 10,012 Float32 cells, 1-meter spacing,
EPSG:26919 and NoData = -999999. Band units are unset; vertical units/datum must
come from the linked source metadata. Original project metadata commonly specifies
NAD83(2011), while standardized tile headers specify NAD83 without that realization.
Do not silently replace one CRS declaration with the other.

Five of eight samples contain NoData. Samples were not clipped to the county and
are not statistically representative: neither the masked percentage nor an entirely
valid sample establishes county coverage. Full native masks remain a load gate.

## Dates, datum and accuracy evidence

Dates below describe the sampled product/linked work unit only. Publication dates
are separate in [the report](report.json). Original links, field values and hashes
are in [project metadata](project-metadata.json) and [the evidence manifest](sources.json).

| Project | Retained tiles | Date evidence | Original vertical-reference evidence / qualification |
| --- | ---: | --- | --- |
| Western Mountains B24 | 42 | Tile and linked DEM: 2024-10-17–2024-11-15 | NAVD88 / Geoid18, meters; 10-cm RMSEz design class, not a measured accuracy result. Broader Maine service spring/fall description is not this work unit's exact dates. |
| Western Maine B16 | 41 | Tile and DEM: 2016-04-05–2016-05-21 | NAVD88 / Geoid12B, meters; DEM metadata reports measured NVA 0.113 m at 95% confidence and VVA 0.253 m at 95th percentile. These are project results, not parcel accuracy. |
| MidCentral B23 | 26 | **Conflict:** tile start/end 2023-04-28–2023-05-18; original DEM ground-condition fields 2024-04-28–2024-05-18 | NAVD88 / Geoid18, meters; 10-cm RMSEz design class. Preserve both years; no date correction proposed. |
| Crown of Maine A18 | 28 | Tile 2018-05-12–2019-06-08; linked deliveries have both 2018-only and 2018–2019 ranges | NAVD88 / Geoid12B, meters; 10-cm RMSEz design class. Map delivery footprints to tiles before assigning precise acquisition dates. |
| Eastern Maine A17 | 2 | Tile ends 2017-11-21; linked DEM ground-condition range ends 2017-12-04 (both start 2017-04-30) | NAVD88 / Geoid12B, meters; 10-cm RMSEz design class. Scope/date relationship unresolved; another linked project XML is malformed and preserved. |
| Eastern B1 2017 | 65 | Tile start/end 2017-04-30–2017-12-04 | Representative item lacks original product/project metadata links; project geoid and measured accuracy remain unqualified. Do not inherit A17 metadata solely from similar names. |
| Eastern B2 2017 | 19 | Tile start/end 2017-04-30–2017-12-04 | Same metadata-link limitation as B1. |
| Maine/Massachusetts BAA | 25 | Tile 2015-04-26–2015-12-05; linked work-unit/delivery dates vary | NAVD88 / Geoid12A, meters. Linked materials include provisional point-cloud statistics; do not substitute them for final DEM accuracy. |

**Catalog/file discrepancy:** sampled Eastern B1 file is 110,387,477 bytes versus
110,383,596 in the catalog; B2 is 139,306,764 versus 139,303,322. These differences
establish catalog-size mismatch, not its cause or a change in elevations. Current
ETags and exact sampled bytes are retained; no complete-file checksum was calculated.

## Overlap evidence

Two pairs have exactly matching header CRS, bounds, resolution and sampled windows.
[Replayed block comparisons](overlap-samples.json) exclude masked/nonfinite values:

| Pair | Common valid sampled pixels | Median older minus newer | 95th percentile absolute difference | Maximum absolute difference |
| --- | ---: | ---: | ---: | ---: |
| BAA / MidCentral | 369,804 | 0.0290 | 0.2013 | 1.5563 |
| Western B16 / B24 | 1,710,864 | 0.0275 | 0.6300 | 7.1705 |

These are raw elevation-value differences, with source metadata describing meters.
They are **not** accuracy tests: acquisition dates, geoid models, terrain changes,
processing and coverage differ; no datum adjustment was applied. Large differences
need spatial inspection before any blending or slope calculation. Do not average
projects or automatically discard the older source.

## Proposed next load: eight-tile pilot

Use the **eight exact representative source IDs** in the report: they cover all
retained project groups and two aligned overlap pairs already sampled. This is a
technical storage/coverage pilot, not representative county or parcel qualification.
The eight current objects total **1,361,113,169 bytes** (1.36 GB), before metadata, masks, derived products or copies. Refresh file lengths/versions first; pin full hashes on download. Reuse no catalog
size as an integrity check where it already conflicts with the publisher object.

1. Retain each original file and its metadata separately in private object storage.
   Keep manifests, dates with scope, CRS/units, hashes, acquisition uncertainty and
   lineage in Supabase/PostGIS. Confirm available storage and transfer allowance
   before loading; no raster storage policy or capacity commitment is enacted here.
2. Scan complete native masks, distinguish raster extent from valid pixels and
   intersect coverage with the exact pinned county boundary. Preserve voids,
   nonfinite values and edge halos. A pilot cannot qualify unsampled county tiles.
3. Investigate both date discrepancies, malformed/missing metadata and size drift.
   Locate final DEM accuracy evidence and work-unit footprints. Track these under
   TL-F-0104; do not guess geoid compatibility or silently rewrite publisher dates.
4. Inspect aligned overlap differences spatially. **Proposed rule:** choose only
   among qualified sources, using actual acquisition evidence and accuracy/coverage;
   retain older coverage where newer pixels are missing. Record the selected source
   per region. Newest publication date alone must not choose the default.
5. Measure pilot compressed size, valid footprint and object overhead before
   estimating a reduced county mosaic. Original objects, alternate versions and
   derived masks all consume space. The 66.6 GB catalog sum is not final storage cost.
6. After source selection and county coverage are evidenced, implement terrain
   availability with exact source/coverage dependencies. Slope requires a separately
   recorded algorithm, unit treatment, edge/NoData handling and source-seam policy.
   No slope threshold, score, septic suitability or buildability decision is selected.

The seamless USGS 1-meter product is not evaluated here and must not be substituted
for these project-based sources without its own provenance/coverage review.
Site-specific septic/buildability adjudication remains purchase-triggered.

## Reproduction and verification

Use an environment with `numpy`, `rasterio 1.4.3` (GDAL 3.9.3) and
`tifffile 2024.8.30`. New output directories are required; captures are not overwritten.

```sh
python scripts/investigate_terrain_readiness.py --output .local/new-terrain
python scripts/terrain_project_metadata.py --evidence .local/new-terrain --output .local/new-terrain-projects
python scripts/compare_terrain_samples.py --evidence .local/new-terrain --output .local/new-overlap.json
python -m unittest discover -s tests -p test_terrain_readiness.py
```

Offline replay reproduced all eight raster reports exactly and confirmed NoData-only
internal mask flags for these sources (no unpopulated internal mask blocks).
All 124 unique private archive objects were downloaded back and hash-verified.
Six tests cover refused full-file responses, wrong ranges, truncated/oversized
responses, bounded successful capture, transfer budget and ETag changes. Local
replay verifies captured hashes, versions and sample masks before comparison.
Public reports contain derived results and publisher links; raw XML/JSON/range
bytes are content-addressed private evidence. See archive and finding-update files
for durable retention and the appended TL-F-0104 event.
