# Small-area terrain retrieval pilot

**Result: bounded retrieval works; this area has partial source coverage and is
not qualified for terrain analysis.** No full source tile or county raster was
loaded into PostgreSQL. The [report](report.json) records the measured result.

## Scope and selection

The [request](request.json) selects a **512 × 512 meter diagnostic square** wholly
inside the pinned Piscataquis study boundary, in native EPSG:26919 coordinates.
This is not a parcel or a purchase recommendation. It expands the previously
sampled Eastern B2 center block, deliberately exercising known mixed valid/NoData
coverage. The selected source is `5eacf6f382cefae35a24ebc7`
(`ME_Eastern_B2_2017`). This choice tests retrieval; it establishes no preference
for that older source over other county candidates.

The request pins the prior readiness report, source ETag and file size, county
boundary hash, native pixel window and resulting bounds. No reprojection,
resampling, interpolation, gap filling, blending or slope calculation occurs.
No context buffer is chosen because this pilot computes no neighborhood metrics.

## Measured result

| Measure | Result |
| --- | ---: |
| Requested area / native pixels | 262,144 m² / 262,144 pixels |
| Valid finite elevation pixels | 185,356 (70.7077%) |
| NoData pixels | 76,788 (29.2923%) |
| Unmasked nonfinite pixels | 0 |
| Source raster bytes transferred per run | 748,611 bytes (0.75 MB) |
| Preserved lossless subset | 582,224 bytes (0.58 MB) |
| Complete source file size, not downloaded | 139,306,764 bytes |
| Raster transfer cap per source/run | 8 MiB |

Five exact range responses contain the TIFF metadata and four compressed native
blocks. The subset is a **DERIVED** lossless native window; the range bodies are
exact original source bytes. Neither is misrepresented as a complete original
GeoTIFF. Sparse reconstructions are temporary local diagnostics and are not
archived or used outside the explicitly populated window.

The finalized implementation and an earlier development run each transferred
748,611 raster bytes (1,497,222 total). These figures exclude private archive
upload/readback and metadata. Archive size and verified object counts are recorded
separately in [archive verification](archive-verification.json); this pilot does
not establish available account capacity for a larger workload.

## Coverage and source qualifications

The entire requested native pixel window is inspected. Missing pixels remain
missing, and `analysis_qualified` stays false even for a fully valid diagnostic
window. Eastern B2's missing original metadata links, acquisition/accuracy/datum
qualifications and catalog-size discrepancy from PR #64 remain open under
TL-F-0104. Matching the pinned ETag confirms this retrieval's version continuity;
it does not prove the source is the latest or best available.

The [native extent check](native-extents.json) also shows why catalog rectangles
must remain discovery evidence: the previously sampled MidCentral and BAA tiles
have zero positive-area county intersection in their native header rectangles.
Both were retained by the earlier geographic catalog-envelope filter. This is
not a correction to either geometry or proof of a county terrain gap. The two
sampled Western tiles intersect only about 68,538 m² of county area. Results cover
only the eight prior representative headers, not all 248 candidates.

## Implemented safeguards and evidence

- Explicitly selected one or two pinned sources; at most 1,048,576 requested pixels
  per source and 8 MiB source transfer each. This pilot uses one source.
- Require native one-meter EPSG:26919, an exact grid-aligned window within the
  pinned county, matching source headers and a north-up unrotated grid.
- Require exact partial HTTP responses and stable ETags; reject full-file fallback,
  changed versions, mismatched headers and unsupported separate/internal masks.
- Inspect every requested native pixel, preserve NoData/nonfinite values, and
  verify the written subset against the decoded array.
- Archive original range bytes, subset, request, source manifest, boundary input,
  readiness evidence and method versions in private object storage. Store hashes
  and the follow-up in TL-F-0104; no new terrain SQL schema or availability adapter
  is introduced in this pilot.

Eleven tests pass, covering multi-block window identity, missing/nonfinite pixels,
full-valid windows that remain unqualified, ETag/header mismatches, window bounds,
range protocol and transfer limits. [Offline replay](validation.json) verifies all
five source-body hashes and reproduces the subset and coverage result exactly,
with network access forbidden. Archive download/readback additionally verifies
object retention. Raster contents occupy object storage, not database rows.

## Next step

Use this area to investigate whether another catalog candidate supplies the
missing pixels. First verify its native extent, source version, metadata and
compatibility; retrieve only a bounded overlapping window. Preserve alternatives
separately and compare valid-pixel masks before proposing any source-selection
rule. Do not mosaic automatically, assume missing pixels are flat, or interpret
them as unsuitable land. Native extent checks should precede later requests.

Broader discovery, source qualification and a persisted terrain catalog/results
schema remain future work. Site-specific slope/buildability review stays
purchase-triggered; this technical pilot does not enable it.

## Reproduction

Requires the prior pinned private county report plus the GIS environment used by
PR #64 (Shapely, NumPy, Rasterio 1.4.3 / GDAL 3.9.3, tifffile 2024.8.30).
Choose a new output directory; existing captures are never overwritten.

```sh
python scripts/retrieve_terrain_area.py \
  --request research/terrain-area-pilot/request.json \
  --output .local/new-terrain-area
python tests/replay_terrain_area.py \
  --evidence .local/new-terrain-area \
  --output .local/new-terrain-area-validation.json
python -m unittest discover -s tests -p 'test_terrain*.py'
```

Archived `county-boundary.json` can supply `--boundary`. Source links/hashes are
in [range sources](sources.json) and the [archive manifest](archive-manifest.json).
