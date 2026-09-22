# Ranking after seventeen accepted corrections

Refresh all **145 remaining Piscataquis zoning holds** after accepting PR #43's
Big Moose, T2 R12 and Barnard versions. This ranks geometry investigations, not
parcels or buildability. The 21 parcel geometry holds and other qualification
issues remain open.

## Next priorities

| Rank | OBJECTID | Map | Zone | Envelope overlap with remaining inventory gap |
| --- | --- | --- | --- | ---: |
| 1 | 27213354 | T7 R12 WELS | P-SL2 | 59.3153 km² |
| 2 | 27313589 | Rainbow Township | P-SL2 | 52.8696 km² |
| 3 | 27278243 | T9 R10 WELS | P-SL2 | 42.0754 km² |
| 4 | 27342226 | Beaver Cove | M-GN | 41.6482 km² |
| 5 | 27321394 | T4 R9 NWP | P-SL2 | 36.1519 km² |

These are overlapping bounding-box upper bounds, not polygon areas, absent zoning
or parcel scores. Do not add them together. The next three were ranks 4–6 in the
previous ranking. Compare preserved/native geometry and official map evidence before
proposing additional interpretations.

## Coverage and tests

Seventeen accepted representations add **191.2851 km²** beyond original valid zoning
geometry, including **71.3147 km²** from the latest three. Remaining inventory gap:
**6,530.1722 km²**. Source coverage and applicability limitations remain; a geometry
gap does not establish absence of legal zoning.

The existing spatially indexed method unions accepted contributions inside the
original gap, then recomputes remaining feature envelopes and jurisdiction breakdowns
without double counting. [Report](report.json) pins source, candidate, method and
dependency hashes. All seventeen accepted IDs are removed from the queue.

[Tests](test-results.json) include five unit checks for overlap, holes, disjoint
parts, boundary touches, jurisdiction aggregation and changed/stale dependencies.
Separate sequential geometry subtraction checks the top priority and the two most
reduced envelopes; maximum difference is 0.0000167 m², below 0.01 m². All 145 IDs
are unique and bounds do not increase. New coverage agrees with the reviewed
proposal scenario within 0.01 m². Both calculation paths use GEOS and do not
constitute independent publisher or survey evidence.

## Retained findings and version chain

Both amendment discrepancies remain open: **Big Moose index 2016-01-30 versus PDF
amendments through 2022-12-30**, and **T1 R11 index 2005-08-18 versus PDF ZP770
2018-04-26**. Geometry acceptance does not settle legal currency. Report limits
and TL-F-0029's next action retain both, alongside parcel holds, municipal
applicability and wetland imagery concerns.

- [Activation](../big-moose-t2-barnard-acceptance/README.md) records the three exact
  PR #43 candidates with originals preserved.
- Ranking audit: `8b5f2fb7041826aea92ac697489fc8dea3308df3ffffd3384e31ff6e27f5b6e7`.
- Snapshot: `9c6eaf3da53ce57b66ecdb200d3abf72d11d38bd3fcdd8db5fe41a7cde62151c`.
- [Dependencies](dependencies.json) bind all seventeen correction/event versions.
  The fourteen-correction snapshot is stale and its historical report preserved.
- [Archive manifest](archive-manifest.json) identifies private inputs and methods;
  this refresh reuses observations and makes no source-freshness claim.
- [Finding review](finding-review.json) records next priorities without closing
  county qualification issues or amendment metadata follow-ups.

The metadata load locks the county batch and rejects stale snapshots. Downstream
consumers must verify currency against the intended source audit. No county rows
are qualified for parcel screening.

## Reproduce

Restore private bytes to `report.inputs` paths using the recorded runtime:

```sh
python scripts/refresh_seventeen_correction_ranking.py
python -m unittest discover -s tests -p 'test_seventeen_correction_ranking.py' -v
python tests/check_seventeen_ranking_direct.py
python scripts/prepare_seventeen_correction_ranking.py --output .local/new-seventeen-ranking-load
```

Capture dependencies transactionally with `scripts/capture_county_ranking.sql`.
Independently verify archive bytes before the guarded metadata load, then verify
with `scripts/check_seventeen_correction_ranking.sql`. Changed dependencies require
a new refresh; preserve previous reports.

## Live checkpoint

Published in Supabase after checksum verification of all 166 archive objects
(eight new independent downloads and 158 reverified earlier downloads).
[Live verification](live-verification.json) confirms the new ranking snapshot is
current, the previous ranking is stale, all seventeen acceptances remain valid,
and original fingerprints and unrelated findings are unchanged. TL-F-0029
occurrence 20 records the new priorities and retains both amendment discrepancies.
The inventory still has 145 zoning and 21 parcel holds and zero rows qualified
for parcel screening. See [checkpoint](checkpoint.json).
