# Ranking after twenty-eight accepted corrections

The eleven PR #46 versions are active. This refresh covers **134 remaining zoning holds**, with 21 parcel holds unchanged. It ranks geometry investigations, not properties or legal suitability.

| Rank | OBJECTID | Source map | Envelope/gap upper bound |
| --- | --- | --- | ---: |
| 1 | 27213354 | t7-r12-wels | 59.3153 km² |
| 2 | 27313589 | rainbow-twp | 52.8696 km² |
| 3 | 27278243 | t9-r10-wels | 42.0754 km² |
| 4 | 27207113 | t1-r10-wels | 26.6665 km² |
| 5 | 27369210 | t7-r13-wels | 17.5688 km² |

These overlapping bounds are not expected recovered areas and must not be added. The earlier backlog assessment demonstrated substantial diminishing returns; investigate map dates and reassess before automatically processing more geometry batches.

## Coverage and calculation order

The eleven acceptances add **87.0005 km²**, for **278.2856 km²** cumulative coverage beyond original valid zoning geometry. Remaining inventory gap: **6,443.1717 km²**. A gap does not establish absence of legal zoning.

The method preserves the reviewed seventeen-correction coverage partition and appends the new cohort’s residual contributions after subtracting accepted geometry. This agrees with the reviewed eleven-proposal scenario within 0.01 m².

A separate global union of all 28 candidates differs by **0.671496 m²**. This is an observed calculation-order sensitivity in the overlay engine; the exact contributing segments have not been localized. The report retains both values. No source geometry is snapped or altered, and no tolerance was relaxed to pass the scenario check. The baseline-preserving result is used in this refresh.

Five unit tests pass. Direct sequential geometry subtraction for three remaining features (the leading priority and the two most reduced bounds) agrees within 0.01 m². All 134 IDs are unique, accepted IDs are excluded, and bounds are monotonic. These checks share GEOS and do not constitute independent source authority.

## Evidence and limits

- [Report](report.json) pins inputs, methods, versions, numerical comparison and all remaining features.
- [Dependencies](dependencies.json) captures the 28 accepted correction/event versions.
- [Tests](test-results.json), [archive](archive-manifest.json) and [finding review](finding-review.json) retain the verification and audit trail.
- The historical seventeen-correction ranking and PR #45 assessment remain preserved but their old dependency snapshot is stale. Do not use their conditional percentages as refreshed results.
- All seven map-date follow-ups remain separate from geometry acceptance. Legal boundaries/access, applicability, parcel identity, wetland age and buildability are unresolved; no inventory rows qualify for parcel screening.

## Reproduce

Restore the private archived bytes and use the recorded Shapely/GEOS runtime:

```sh
python scripts/refresh_twenty_eight_correction_ranking.py
python -m unittest discover -s tests -p 'test_twenty_eight_correction_ranking.py' -v
python tests/check_twenty_eight_ranking_direct.py
python scripts/prepare_twenty_eight_correction_ranking.py --output .local/new-twenty-eight-ranking-load
```

Capture a current dependency set before recomputation. The guarded metadata load checks snapshot currency under the county batch lock. Independently verify archived bytes before publication and run `scripts/check_twenty_eight_correction_ranking.sql` afterward.

## Live checkpoint

Published and read back on September 22, 2026. All 172 archive objects verified
(164 prior downloads rechecked; eight new independent downloads). TL-F-0029
occurrence 23 records this ranking. The current snapshot has 28 acceptances,
134 zoning and 21 parcel holds, and zero qualified rows. Original fingerprints,
previous acceptance versions and other finding states are unchanged. See
`checkpoint.json` and `live-verification.json`.
