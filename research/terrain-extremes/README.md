# Native terrain neighborhoods at recorded extremes

**Eastern 2017 is locally smoother than both Western surfaces at the recorded
extremes. Their correctness and the cause of the differences remain unknown.**
No correction, source preference or buildability qualification is activated.

## Scope and evidence

Inspect an 11×11 native-cell window around every unique top-five location recorded
in the height and slope comparisons: **13 centers in three spatial groups**.
These deliberately selected extremes are not a random or representative sample.
Several windows overlap heavily; they are not independent observations.

[Structured results](report.json) retain exact native center coordinates, source
hashes, prior-report hashes, center-row/column elevation profiles, valid-cell
counts, adjacent-cell steps and least-squares plane residuals. No resampling,
filtering or source edits are performed. Pair differences compare corresponding
native cells; Western centers have the previously documented submillimeter phase
relative to Eastern. Plane residuals describe local shape, not measurement error.
Missing samples are excluded explicitly, never filled, and profiles retain nulls.

## Observations (DERIVED)

Representative center coordinates below are EPSG:26919, in meters. Plane residual
RMS is calculated after fitting a plane to each source's valid neighborhood.

| Center E / N | Eastern RMS | Western 2016 RMS | Western 2024 RMS | Western 2024 − 2016 height RMS |
| --- | ---: | ---: | ---: | ---: |
| 475530.5 / 5024802.5 | 0.115 m | 0.674 m | 0.710 m | 0.149 m |
| 475541.5 / 5024756.5 | 0.123 m | 0.417 m | 0.396 m | 0.103 m |
| 475599.5 / 5024827.5 | 0.088 m | 0.648 m | 0.480 m | 0.324 m |

The first two groups have 121 valid cells in every inspected native window.
At the representative first-group center, maximum adjacent-cell steps are
0.368 m (Eastern), 1.077 m (Western 2016), and 1.530 m (Western 2024).
The large slope differences therefore coincide with different local surface
shapes, not simply a uniform vertical shift. A constant height offset cannot
explain differences in independently calculated slopes.

The easternmost group is close to the Western valid-data edge: both inspected
Western neighborhoods have **77 valid and 44 missing cells**, versus all 121
in Eastern. Source-specific plane fits there use different footprints and are
not directly comparable as equal-support roughness estimates. Western-to-Western
paired statistics use only their shared finite cells. The original slope centers
had the required small stencil support, but the wider inspection reveals this
nearby data limitation. This is not evidence that the earlier calculation crossed
NoData, nor proof that the observed feature was caused by the data edge.

## Interpretation and next step

Both Western dates show sharper local features than Eastern. This is consistent
with differences in captured surface shape or processing, but does **not** prove
Eastern smoothing, Western artifacts, or a terrain-change event. Similar features
in the two Western products are not independent ground-truth corroboration;
shared processing or inputs have not been ruled out. Acquisition labels alone
cannot establish feature history.

Next seek bounded independent evidence at these three groups: original classified
ground points and processing/breakline evidence if available, and appropriately
dated imagery for context. Verify availability and provenance before downloading.
Imagery alone may not establish bare-earth elevation beneath vegetation. If such
evidence is unavailable, retain the discrepancy and source-specific outputs;
do not choose a source merely because it is smoother or newer. Keep county
catalog availability separate from purchase-triggered site qualification.

## Validation and tracking

27 terrain tests pass. New tests check native-cell location, mask preservation,
known planes, local features, subset bounds and insufficient support. Offline
replay reproduces the report byte-for-byte. Original subset archives remain
unchanged; new private archival is still pending separate approval. The approved
TL-F-0104 append records both PR70's slope results and this investigation.

```sh
python scripts/inspect_terrain_extremes.py \
  --base .local/terrain-area-pilot-final/0-subset.tif \
  --western2016 .local/terrain-gap/0-subset.tif \
  --western2024 .local/terrain-gap/1-subset.tif \
  --output .local/replayed-terrain-extremes.json
```
