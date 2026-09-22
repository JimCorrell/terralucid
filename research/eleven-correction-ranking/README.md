# Ranking after eleven accepted corrections

Refresh all **151 remaining Piscataquis zoning holds** after accepting the three
PR #39 proposals. This ranks geometry investigations, not parcels or buildability.
The 21 parcel geometry holds and other county qualification issues remain open.

## Next priorities

| Rank | OBJECTID | Map | Zone | Envelope overlap with remaining inventory gap |
| --- | --- | --- | --- | ---: |
| 1 | 27233351 | T10 R15 WELS | P-SL2 | 82.7338 km² |
| 2 | 27314083 | Chesuncook Township | P-SL2 | 79.1432 km² |
| 3 | 27316137 | T1 R11 WELS | P-SL2 | 78.2507 km² |
| 4 | 27257109 | Big Moose Township | M-GN | 76.9778 km² |
| 5 | 27321193 | T2 R12 WELS | P-SL2 | 75.6292 km² |

These are bounding-box upper bounds. They overlap and must not be added or treated
as polygon areas, absent legal zoning, suitable land or acquisition scores. The
next three were ranks 4–6 before the latest acceptances. Investigate source/native
representations and official map evidence before proposing any interpretation.

## Coverage and method

The eleven accepted representations add **114.6227 km²** beyond original valid
zoning geometry, including **13.9368 km²** from the latest three. The remaining
inventory geometry gap is **6,606.8347 km²**. This gap includes source-coverage and
applicability limitations; it is not an assertion that land lacks zoning.

The existing spatially indexed method intersects accepted geometries with the
original gap, unions overlapping contributions, and recomputes each remaining
feature envelope and jurisdiction breakdown. Original source pages and rankings
are preserved. Candidate, source, method and dependency hashes are pinned in the
[report](report.json). All eleven accepted IDs are removed from the queue.

[Tests](test-results.json) include five unit checks covering overlaps, holes,
disjoint parts, boundary touches, jurisdiction aggregation and stale/mismatched
dependencies. Direct sequential geometry subtraction independently checks the top
priority and the two most reduced envelopes; each agrees within 0.01 m². All 151
IDs are unique, remaining upper bounds do not increase, and additional coverage
agrees with the reviewed three-proposal scenario within 0.01 m². Both calculation
paths use GEOS; these are computational checks, not independent source authority.

## Version chain and audit

- Activation: [three exact PR #39 versions](../next-three-zoning-acceptance/README.md).
- Ranking audit: `5510a6d2d39e371d8456d68201970f047b6e8893c8fca0dfffc8b21ddf1a6e27`.
- Snapshot: `bcd341fe5cd1d7afe0a2d79a1e58991c5e4c954f6f8f64add9592a8cfca89eed`.
- [Dependencies](dependencies.json) retain all eleven exact correction/event
  versions. The previous eight-correction snapshot is stale; its ranking remains
  historical evidence.
- [Archive manifest](archive-manifest.json) identifies private inputs and methods.
  This refresh reuses existing source observations; it makes no new source-currency
  claim and introduces no new source responses.
- [Finding review](finding-review.json) appends the next three priorities to
  TL-F-0029 without closing county qualification issues.

The guarded metadata load locks the county batch and requires the snapshot to
remain current. Downstream consumers must check the snapshot against the intended
county source audit. Qualified parcel screening remains false.

## Reproduce

Restore private bytes to `report.inputs` paths with the recorded runtime:

```sh
python scripts/refresh_eleven_correction_ranking.py
python -m unittest discover -s tests -p 'test_eleven_correction_ranking.py' -v
python tests/check_eleven_ranking_direct.py
python scripts/prepare_eleven_correction_ranking.py --output .local/new-eleven-ranking-load
```

Capture dependencies in a transaction with `scripts/capture_county_ranking.sql`.
After independently verifying archived bytes, apply the guarded load and verify
with `scripts/check_eleven_correction_ranking.sql`. Changed dependencies require a
new refresh; preserve previous reports.

## Live checkpoint

The ranking audit and fourteenth TL-F-0029 occurrence/review are recorded in
Supabase. All 162 archive objects passed checksum verification (eight new
downloads, 154 reverified earlier independent downloads). [Live verification](live-verification.json)
confirms the ranking snapshot is current, the prior eight-correction snapshot is
stale, all eleven acceptance versions and original fingerprints are unchanged,
and effective holds remain 151 zoning / 172 total. No new source observations or
qualified parcel screenings were introduced. See [checkpoint](checkpoint.json).
