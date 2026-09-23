# Source-aware pilot slope diagnostic

**Source boundaries can be explicitly held, but independently calculated slopes
still have meaningful local differences.** This is a DERIVED diagnostic of the
preserved 512 m pilot square, not a county qualification or buildability result.
No raster, source preference, height correction or acceptance policy is activated.

## Method

Compute each source's slopes on its own native 1 m grid. For a 3×3 neighborhood
with rows `a b c / d e f / g h i`, use:

```
dx = (c + 2f + i - a - 2d - g) / (8 * cell_size)
dy = (g + 2h + i - a - 2b - c) / (8 * cell_size)
slope_degrees = degrees(atan(sqrt(dx*dx + dy*dy)))
```

Horizontal and vertical units are meters. All nine samples must be valid and
finite. The captured raster edge is unsupported; no padding or NoData filling.
This explicitly defined operator is a diagnostic choice, not an adopted production
slope scale or threshold. A different footprint would require different holds.

For overlap comparison only, bilinearly sample the already calculated Western
slope angles at Eastern centers using the strict four-valid-sample method from
PR69. This is **not** slope calculated from resampled elevations. Its full native
support includes the four slope neighborhoods. Keep the submillimeter grid phase
and original input hashes from the [height diagnostic](../terrain-overlap/README.md).
Nearest-center sampling provides a sensitivity check on identical supported cells.

The hypothetical assignment retains Eastern where its elevation is valid and
uses Western elsewhere. Hold every internal target-grid 3×3 neighborhood containing
both source labels. Separately require native slope support and hold the AOI's
outermost row/column. These are diagnostic flags, not database geometry holds.
No merged elevation or slope raster is written.

## Results

Each comparison has **170,860** jointly supported centers. Differences below are
Western minus Eastern, in **degrees**, not percent slope or accuracy against truth.

| Alternative | Mean difference | Median difference | Absolute difference p95 | Maximum absolute difference |
| --- | ---: | ---: | ---: | ---: |
| Western 2016 | +0.257° | +0.208° | 5.674° | 39.770° |
| Western 2024 | +0.128° | +0.088° | 5.602° | 41.235° |

Maximum bilinear-versus-nearest sensitivity is 0.0151° and 0.0116°, respectively;
the observed grid phase does not explain the much larger inter-source differences.
This does not rule out other registration or processing differences. The
[structured report](report.json) records the five largest absolute differences
per comparison, including coordinates and both slope values, for inspection.
No cause or source correctness is inferred from those differences alone.

For either alternative, the hypothetical assignment partitions all 262,144 centers:

| Diagnostic status | Centers |
| --- | ---: |
| Supported, single-source neighborhood | 259,076 |
| Source-boundary neighborhood held | 1,024 |
| AOI edge held | 2,044 |
| Other missing support | 0 |

These are disjoint counts on the Eastern grid. The source boundary derives from
Eastern's valid/NoData footprint, not a legal or official acquisition boundary.
No Eastern slope is supported in the held seam neighborhoods, so the report's
seam-adjacent comparison count is zero; this is unavailable evidence, not zero
difference. A constant source offset cancels in an independently computed slope,
but can create an artificial gradient if elevations are spliced first.

## Next step

Inspect small native elevation neighborhoods at the recorded slope extremes and
PR69's height extremes. Determine whether differences are localized and examine
available evidence for terrain change, surface artifacts or processing differences.
Do not average sources or choose a correction based only on smaller residuals.
Then review a source-selection policy and slope scale. Parcel suitability and
acceptance thresholds remain purchase-triggered decisions; TL-F-0104 stays open.

## Validation and reproduction

24 terrain tests pass, including analytical-plane slopes, constant-offset
invariance, strict NoData/nonfinite propagation, edge exclusion, diagonal and
straight source boundaries, and an artificial step entirely contained in the
hold mask. Offline replay produces a byte-identical report.

```sh
python scripts/compare_terrain_slopes.py \
  --base .local/terrain-area-pilot-final/0-subset.tif \
  --western2016 .local/terrain-gap/0-subset.tif \
  --western2024 .local/terrain-gap/1-subset.tif \
  --output .local/replayed-terrain-slopes.json
python -m unittest discover -s tests -p 'test_terrain*.py'
```

Original subsets remain immutable and privately archived. This investigation
requires NumPy and rasterio; it downloads no new raster data.
