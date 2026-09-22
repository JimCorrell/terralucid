# Ranking after fourteen accepted corrections

Refresh all **148 remaining Piscataquis zoning holds** after accepting the three
PR #41 proposals. This ranks geometry investigations, not parcels or buildability.
The 21 parcel geometry holds and other county qualification issues remain open.

## Next priorities

| Rank | OBJECTID | Map | Zone | Envelope overlap with remaining inventory gap |
| --- | --- | --- | --- | ---: |
| 1 | 27257109 | Big Moose Township | M-GN | 76.9778 km² |
| 2 | 27321193 | T2 R12 WELS | P-SL2 | 75.6292 km² |
| 3 | 27303187 | Barnard Township | P-SL2 | 73.3846 km² |
| 4 | 27213354 | T7 R12 WELS | P-SL2 | 59.3153 km² |
| 5 | 27313589 | Rainbow Township | P-SL2 | 52.9028 km² |

These are overlapping bounding-box upper bounds, not polygon areas, absent legal
zoning or parcel scores. Do not add them together. The next three were ranks 4–6
before the latest acceptances. Compare preserved/native geometry and official maps
before proposing further interpretations.

## Coverage and checks

Fourteen accepted representations add **119.9704 km²** beyond original valid
zoning geometry, including **5.3478 km²** from the latest three. The remaining
inventory geometry gap is **6,601.4869 km²**. Source coverage and applicability
limitations remain; the gap is not an assertion that land lacks zoning.

The existing spatially indexed method unions accepted contributions inside the
original gap, then recomputes each remaining feature envelope and jurisdiction
breakdown without double counting. [Report](report.json) pins source, candidate,
method and dependency hashes. All fourteen accepted IDs are removed from the queue.

[Tests](test-results.json) record five unit checks for overlap, holes, disjoint
parts, boundary touches, jurisdiction aggregation and changed/stale dependencies.
Separate sequential geometry subtraction checks the top priority and the two most
reduced envelopes. Maximum difference is 0.000292 m², below the 0.01 m² threshold.
All 148 IDs are unique and remaining bounds do not increase. The latest coverage
gain agrees with the reviewed proposal scenario within 0.01 m² (difference about
0.00326 m² from overlay order). Both calculation paths use GEOS, not independent
publisher or survey evidence.

## Retained finding and version chain

**T1 R11's amendment metadata discrepancy remains unresolved:** index AMEND_DATE
2005-08-18 versus PDF ZP770 effective 2018-04-26. Geometry acceptance does not settle
legal currency. The report limits and TL-F-0029 next action retain this follow-up,
alongside parcel holds, municipal applicability and wetland imagery concerns.

- [Activation](../latest-three-zoning-acceptance/README.md) records the three exact
  PR #41 candidate versions with original source evidence preserved.
- Ranking audit: `3dd7c8ccf884b20e49fae2f0949b047cf7635cea978ea287053b5a6ab96ef10d`.
- Snapshot: `7d750c5646a7e6368835db664092e4941e14908f35369a19d90863bacbddd492`.
- [Dependencies](dependencies.json) bind fourteen exact correction/event versions.
  The eleven-correction snapshot is stale; its historical ranking remains intact.
- [Archive manifest](archive-manifest.json) identifies private inputs and methods.
  This refresh reuses existing observations and makes no source-freshness claim.
- [Finding review](finding-review.json) records next priorities and retains the
  unresolved amendment discrepancy; no county qualification finding is closed.

The metadata load locks the county batch and rejects stale snapshots. Downstream
consumers must check snapshot currency against the intended county audit. No county
rows are qualified for parcel screening.

## Reproduce

Restore private bytes to `report.inputs` paths using the recorded runtime:

```sh
python scripts/refresh_fourteen_correction_ranking.py
python -m unittest discover -s tests -p 'test_fourteen_correction_ranking.py' -v
python tests/check_fourteen_ranking_direct.py
python scripts/prepare_fourteen_correction_ranking.py --output .local/new-fourteen-ranking-load
```

Capture dependencies transactionally with `scripts/capture_county_ranking.sql`.
Independently verify archive bytes before applying the guarded load, then use
`scripts/check_fourteen_correction_ranking.sql` for live verification. Changed
dependencies require a new refresh; preserve previous reports.

## Live checkpoint

The ranking audit and seventeenth TL-F-0029 occurrence/review are recorded in
Supabase. All 163 archive objects passed checksum verification (eight new
independent downloads, 155 reverified earlier downloads). [Live verification](live-verification.json)
confirms the new snapshot is current and the previous ranking is stale, with all
fourteen accepted versions and original fingerprints preserved. Holds remain 148
zoning / 169 total; no source observations or qualified screenings were added.
The amendment discrepancy remains in TL-F-0029's next action. See [checkpoint](checkpoint.json).
