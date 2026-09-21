# Piscataquis zoning-hold ranking refresh

## Result

After the five accepted exact-version geometry corrections, **157 zoning holds** remain (162 originally). The 21 parcel holds also remain: 178 effective holds across the county inventory. This is a ranking of geometry investigations; the county inventory remains unqualified for parcel screening.

| Priority | Original rank | OBJECTID | Source map | Upper bound (km²) | Reduction (km²) |
| --- | --- | --- | --- | ---: | ---: |
| 1 | 4 | 27304757 | east-middlesex-canal-grant-twp | 91.974 | 0.870 |
| 2 | 5 | 27270812 | t7-r11-wels | 90.986 | 0.000 |
| 3 | 6 | 27207268 | t4-r11-wels | 90.854 | 0.000 |
| 4 | 9 | 27224591 | t4-r13-wels | 89.476 | 0.000 |
| 5 | 10 | 27320676 | t7-r9-wels | 86.694 | 0.000 |
| 6 | 11 | 27243652 | t6-r15-wels | 83.563 | 0.000 |
| 7 | 12 | 27233351 | t10-r15-wels | 82.734 | 0.000 |
| 8 | 13 | 27314083 | chesuncook-twp | 79.145 | 0.000 |
| 9 | 14 | 27316137 | t1-r11-wels | 78.251 | 0.000 |
| 10 | 15 | 27257109 | big-moose-twp | 76.978 | 0.646 |

**Recommended next case:** East Middlesex Canal Grant 27304757, then T7 R11 WELS 27270812 and T4 R11 WELS 27207268. These three source records are P-SL2 shoreland geometry. Investigate each against the native representation and official map evidence; ranking alone does not support a correction.

## Calculation and limits

The metric is unchanged from the [historical ranking](../piscataquis-zoning-holds/ranking.json): area of each held feature’s bounding box intersected with the county area outside usable zoning geometry. The new calculation subtracts the union of all five accepted candidates from that historical gap, then removes those five accepted features from the held cohort. Overlapping candidate areas count once. Thirteen remaining upper bounds shrink; several lower-ranked cases change relative order. Spatial indexing limits intersections to relevant polygon parts; no source geometry is repaired or edited.

The accepted geometries add **89.457349 km²** beyond the original valid-geometry union. The corresponding inventory gap changes from **6,721.457329 km² to 6,631.999980 km²**. This includes the original inventory’s retained source flags. It is not a measurement of land without applicable zoning. Bounding boxes can greatly overstate a held polygon’s actual coverage, and overlapping priority estimates must not be summed. Remoteness, access, parcel suitability and legal applicability are not scored here.

Municipal zoning applicability, the 21 parcel holds, wetland imagery age, and other acquisition due diligence remain unresolved. Original geometries, holds, captures and the earlier ranking are preserved.

## Provenance and currency

- Source audit: `fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259`.
- Ranking audit: `07efac22afa8829de039ada598fa06533f378c33edc720f40a255b67c75d0136`.
- Correction snapshot: `6953a46ca94beb0c5fa74bac958926d015afb78c65ccfe28c35b08fc10f9d048`.
- [Report](report.json) contains all 157 rows, prior ranks and areas, source hashes, correction/event dependencies and method/runtime versions.
- [Dependencies](dependencies.json) were captured from the effective county inventory under the county batch lock. [Capture SQL](../../scripts/capture_county_ranking.sql) uses separate statements in one READ COMMITTED transaction.
- [Finding review](finding-review.json) appends TL-F-0029 history. TL-F-0022 and TL-F-0109 remain unchanged.
- [Archive manifest](archive-manifest.json) records private content-addressed evidence, including the historical gap WKB. No new source capture or correction acceptance.

Before using this ranking, require `ingest.county_geometry_snapshot_is_current(report.geometry_snapshot_id, intended_source_audit)`. A correction withdrawal, reacceptance or changed dependency requires recomputation. The staging script acquires the county batch lock, then checks snapshot currency and exact dependencies in a fresh statement before atomically recording the audit and finding review. A stale result cannot be promoted by that load.

## Reproduction and checks

Restore the manifest objects to their paths in `report.inputs` (including `.local/piscataquis-held-zoning-gap.wkb`) and use Shapely 2.0.7 / GEOS 3.11.4. The raw sources and candidate geometries remain private; Git alone is not a full data checkout.

```sh
python scripts/refresh_county_ranking.py
python -m unittest discover -s tests -p test_county_ranking_refresh.py -v
python tests/check_county_ranking_direct.py
python scripts/prepare_county_ranking_refresh.py --output .local/new-ranking-load
```

[Tests](test-results.json) cover overlapping candidates, holes, disjoint parts, boundary touches, changed dependencies and held cohorts. Three real feature envelopes were independently clipped against the original gap and sequentially subtracted by each accepted candidate; their areas agree within 0.01 m². The refreshed coverage also agrees with the two prior activation analyses within 0.01 m². All 157 bounds are non-increasing.

## Recorded state

The refreshed audit and eighth TL-F-0029 occurrence are recorded in Supabase.
[Live verification](live-verification.json) confirms the ranking snapshot is current,
all 120,449 original row fingerprints and five accepted corrections are unchanged,
and TL-F-0022 / TL-F-0109 are unchanged. The old three-correction snapshot and a
wrong source audit are rejected. All 152 archive objects passed independent
download/hash verification. See the [checkpoint](checkpoint.json).
