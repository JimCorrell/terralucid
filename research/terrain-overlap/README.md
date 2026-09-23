# Pilot overlap heights and prospective source boundary

**Both Western alternatives fill the pilot gap, but a source switch introduces
about an 11 cm mean height difference at the boundary.** No merged surface,
height correction, preferred source or slope qualification is activated.
TL-F-0104 remains in progress.

## Scope and method

This is a DERIVED diagnostic of the same 512 m square retained by the
[retrieval pilot](../terrain-area-pilot/README.md), not a parcel assessment or
county-wide result. Original raster bytes are unchanged. No new elevation data
was downloaded. [Results](report.json) pin the three subset hashes and method.
Source identity, retrieval provenance and exact raw ranges remain in the
[pilot](../terrain-area-pilot/sources.json) and
[alternative investigation](../terrain-gap/sources.json).

The Western native grids coincide with each other but differ from Eastern by
approximately +0.000277 m east and -0.000354 m north. For comparison only, sample
Western elevations at Eastern pixel centers using float64 bilinear interpolation.
Require all four native stencil pixels valid and finite, even when a weight is
zero; reject unsupported centers, never extrapolate or interpolate across NoData.
This conservative diagnostic is not a production resampling policy. Compare
nearest-center sampling on the identical supported overlap as a sensitivity check.
Western-to-Western comparison uses their identical native grid, restricted to
centers inside the original AOI. Area coverage from PR67 and sampled center counts
here are distinct quantities.

## Shared-area differences

Signs below mean **Western minus Eastern 2017**, in meters. Each Eastern comparison
has 172,556 shared supported centers. RMS differences are inter-source differences,
not ground-truth accuracy measurements or independent checkpoint statistics.

| Comparison | Mean | Median | RMS difference | 95th percentile absolute difference | Maximum absolute |
| --- | ---: | ---: | ---: | ---: | ---: |
| Western 2016 − Eastern 2017 | -0.1117 | -0.1176 | 0.1651 | 0.2881 | 2.1277 |
| Western 2024 − Eastern 2017 | -0.0962 | -0.0986 | 0.1638 | 0.2854 | 2.2666 |
| Western 2024 − Western 2016 (249,344 native centers) | +0.0010 | +0.0148 | 0.1443 | 0.2715 | 1.6460 |

The four 256×256 quadrants have mean differences ranging from -0.1202 to
-0.0874 m for 2016 and -0.1059 to -0.0789 m for 2024. Both alternatives' largest
absolute differences cluster near EPSG:26919 **475530.5 E, 5024802.5 N**, away
from the prospective seam. Their shared location suggests a useful follow-up
inspection, but does not identify which source is wrong or establish terrain
change. Preserve those locations; do not erase them through a blanket offset.

Bilinear versus nearest-center maximum absolute differences in the shared area
are **0.000749 m** (2016) and **0.000792 m** (2024). Thus this observed submillimeter
grid phase is not an explanation for the roughly decimeter source differences.
These results do not exclude other horizontal registration differences.

## Prospective boundary

The diagnostic hypothesis retains Eastern wherever valid and fills only its
NoData with an alternative. Its boundary is the **internal Eastern valid/NoData
pixel edge**, not a surveyed boundary or an official acquisition-project boundary.
The AOI perimeter is excluded. Retained cell centers beside the seam run from
northing 5024374.5 to 5024885.5, within eastings 475263.5–475265.5: a nearly
north–south line with pixel-scale jogs. The report retains this extent.

All **76,788** Eastern gap centers have strict interpolation support in either
alternative. All **514** four-neighbor source-switch edges have support on both
sides. Edge statistics weight edges equally, so a cell at a jog can contribute
to more than one edge; they are not independent observations.

For each edge oriented from retained Eastern cell A to fill cell B:

- Cross-source step = Western(B) − Eastern(A).
- Within-source terrain step = Western(B) − Western(A).
- Source-switch contribution = Western(A) − Eastern(A).

This exact decomposition avoids attributing the natural terrain gradient to the
source switch. It is a difference diagnostic, not proof of a physical discontinuity.

| Alternative | Mean cross-source step | Mean within-source terrain step | Mean source contribution | Source contribution absolute p95 / max |
| --- | ---: | ---: | ---: | ---: |
| 2016 | -0.1668 m | -0.0589 m | -0.1079 m | 0.3171 / 0.6193 m |
| 2024 | -0.1717 m | -0.0607 m | -0.1110 m | 0.2965 / 0.4625 m |

## Recommendation for review

Advance to a **source-aware slope diagnostic**: calculate slope only where the
entire chosen neighborhood has valid support from one source; explicitly hold
neighborhoods crossing a source switch. Compare independently calculated slopes
in overlap before proposing a preferred source or a seam treatment. The hold
width must follow the selected slope operator's footprint, not an arbitrary
county-wide buffer. This is a proposal; no qualification rule is changed here.

Do not add 10–12 cm to either raster or blend the seam based on this one square.
Residuals vary spatially, local extremes exceed 2 m, and no independent local
control establishes their cause. As established in the
[accuracy review](../terrain-accuracy/README.md), both sources declare NAVD88;
different geoid-model labels alone do not justify a height correction. Project
accuracy statistics are not adopted as local acceptance thresholds.

## Reproduction and validation

```sh
python scripts/compare_terrain_heights.py \
  --base .local/terrain-area-pilot-final/0-subset.tif \
  --western2016 .local/terrain-gap/0-subset.tif \
  --western2024 .local/terrain-gap/1-subset.tif \
  --output .local/replayed-terrain-overlap.json
python -m unittest discover -s tests -p 'test_terrain*.py'
```

Requires NumPy and rasterio plus the preserved private subsets. Tests cover an
analytical plane on shifted grids, strict invalid-stencil/edge rejection,
signed source differences, both edge orientations, unsupported seams and the
separation of terrain gradient from a known source offset. All 20 terrain tests
pass. The original subsets already have private archive verification in the preceding
pilot investigations. Archival of this new comparison and the TL-F-0104 event
append are pending explicit approval after automatic approval review blocked the
archive operation. No production raster, source geometry or schema is changed.
