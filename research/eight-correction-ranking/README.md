# Piscataquis zoning ranking after eight corrections

**154 zoning geometry holds remain**, plus 21 parcel holds (175 total). This refresh uses all eight accepted exact-source versions from merged PR #37. It preserves the original ranking and the five-correction ranking. No new geometry is accepted or changed.

## Next priorities

| Priority | Prior five-correction rank | OBJECTID | Source map | Envelope upper bound (km²) | Reduction since prior ranking (km²) |
| --- | --- | --- | --- | ---: | ---: |
| 1 | 4 | 27224591 | t4-r13-wels | 89.476 | 0.000 |
| 2 | 5 | 27320676 | t7-r9-wels | 86.694 | 0.000 |
| 3 | 6 | 27243652 | t6-r15-wels | 83.563 | 0.000 |
| 4 | 7 | 27233351 | t10-r15-wels | 82.734 | 0.000 |
| 5 | 8 | 27314083 | chesuncook-twp | 79.145 | 0.000 |
| 6 | 9 | 27316137 | t1-r11-wels | 78.251 | 0.000 |
| 7 | 10 | 27257109 | big-moose-twp | 76.978 | 0.000 |
| 8 | 11 | 27321193 | t2-r12-wels | 75.629 | 0.000 |
| 9 | 12 | 27303187 | barnard-twp | 73.385 | 0.000 |
| 10 | 13 | 27213354 | t7-r12-wels | 59.315 | 0.027 |

The next bounded group is **T4 R13 WELS 27224591, T7 R9 WELS 27320676, and T6 R15 WELS 27243652**. Compare original/native geometry and official map evidence before proposing interpretations. Ranking alone does not support a correction.

## Method and changes

The metric remains each held feature’s bounding-box overlap with the county area outside usable inventory zoning geometry. Starting with the checksum-pinned original valid-geometry gap, the calculation unions all eight accepted candidates before subtracting their contribution. It removes their eight IDs from the held cohort and checks the remaining 154 IDs against the effective Supabase inventory. Overlapping corrections count once; repeated civil-jurisdiction records are aggregated.

The three latest acceptances add **11.228539 km²** beyond the five-correction baseline. All eight together contribute **100.685888 km²** beyond the original valid-geometry union. The inventory geometry gap is now **6,620.771441 km²**. Six remaining envelope estimates shrink compared with the five-correction ranking. All 154 bounds are non-increasing.

These are investigation upper bounds, not actual held-polygon areas. They overlap and must not be added. The gap includes the original inventory’s retained source flags and does not establish absent applicable zoning, available land or buildability. Parcel suitability, remoteness/access scoring and offer readiness are not evaluated. All county rows remain unqualified for parcel screening; municipal applicability, parcel holds, wetland imagery age and other due diligence remain open.

## Versioned evidence

- Ranking audit: `6b8896283cc6637d5d2dc77c51fe1fe28f2600f64c76ef25649f05893ad418eb`.
- Source audit: `fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259`.
- Eight-correction snapshot: `7a862e0e28a8d54afd6c5a58c0964a5482393836fc2af767cad80b42e26a20f8`.
- [Report](report.json) contains all 154 cases and full input/correction/event hashes. `previous_rank` and `previous_envelope_uncovered_county_m2` retain the original 162-hold reference; `five_correction_*` fields compare directly with PR #35.
- [Dependency capture](dependencies.json) reads the effective county inputs under the county batch lock, with separate statements in a READ COMMITTED transaction.
- The load holds that same lock and checks snapshot currency and exact dependencies before atomically recording the audit and [TL-F-0029 review](finding-review.json).
- Before using this result, require `ingest.county_geometry_snapshot_is_current(report.geometry_snapshot_id, intended_source_audit)`. Withdrawal, reacceptance or any changed dependency requires a new refresh. Historical snapshots and results remain preserved.
- [Archive manifest](archive-manifest.json) covers 161 private objects. For verification, 151 exact checksum-matched files were reused from prior independent archive downloads; ten new objects were uploaded and downloaded. Every object is rechecked for byte count and SHA-256 before loading. No new source observation or schema migration is created.

## Verification and reproduction

Five unit tests cover overlapping candidates, holes, boundary contacts, disjoint parts, repeated civil names, changed dependencies and held-cohort rejection. Independent direct overlays check the top-ranked feature and the two largest newly reduced estimates, agreeing within 0.01 m². The additional coverage agrees with the prior three-proposal scenario within that tolerance. See [test results](test-results.json).

Restore private inputs to the exact paths in `report.inputs`, including the original gap cache and accepted candidates. Use the runtime versions in the report.

```sh
python scripts/refresh_eight_correction_ranking.py
python -m unittest discover -s tests -p test_eight_correction_ranking.py -v
python tests/check_eight_ranking_direct.py
python scripts/prepare_eight_correction_ranking.py --output .local/new-eight-ranking-load
```

The original and five-correction methods/reports are unchanged. A new live dependency capture belongs to a new versioned audit, not an overwrite of this result.

## Recorded state

The refreshed audit and eleventh TL-F-0029 occurrence/review are recorded in
Supabase. [Live verification](live-verification.json) confirms the new ranking
snapshot is current, all 120,449 original row fingerprints and eight accepted
correction versions are unchanged, and other finding reviews are unchanged.
Effective holds remain 154 zoning / 175 total; no rows qualify for parcel screening.
See the [checkpoint](checkpoint.json).
