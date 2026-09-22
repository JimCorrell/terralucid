# Latest three Piscataquis zoning priorities

Investigate the first three remaining cases from merged PR #40. **All three support
exact-source proposals that equal the current service's valid GeoJSON.** They remain
proposals pending acceptance. Eleven accepted corrections and **151 zoning / 172
total effective holds** are unchanged.

## Results

| OBJECTID / map | Interpretation | Source rings → candidate shells / holes | Potential added geometry |
| --- | --- | --- | ---: |
| 27233351 / T10 R15 WELS | One nested hole belongs to the innermost shell. | 96 → 52 / 44 | 1.9796 km² |
| 27314083 / Chesuncook Township | One nested hole belongs to the innermost shell. | 74 → 51 / 23 | 1.2942 km² |
| 27316137 / T1 R11 WELS | One nested hole belongs to the innermost shell. | 75 → 31 / 44 | 2.0740 km² |

All are P-SL2 records. The combined scenario is **5.3478 km²** beyond original valid
zoning and eleven accepted corrections, with overlapping contributions counted
once. These are potential inventory gains, not legal coverage, buildable area or
parcel scores. The ranking's larger values were bounding-box upper bounds.

## Source and interpretation checks

Fresh native EPSG:26919 records exactly match the archived county features,
including attributes and coordinates. All individual source rings are valid. The
holds arose from conservative decoding of ambiguous enclosing shells. The existing
method assigns each hole to the innermost containing shell; no rings are split and
no coordinates are moved, snapped, simplified or generally repaired.

Each complete candidate is valid, retains every source segment with multiplicity,
and equals the corresponding valid service GeoJSON. Publisher area agreement is
within 0.000001 m², a numeric cross-check rather than survey precision. Separate
routines check fixed candidate cycle roles and classify all **245 linework faces**
by ray crossing; all agree with zero fill difference. The algorithms share GEOS,
so this is not independent survey or publisher approval.

[Report](report.json) records exact ownership, source comparisons, candidate hashes,
checks and scenario calculations. [Test results](test-results.json) record 23 passing
tests, including authentic candidates, wrong hole ownership, missing enclosing holes,
changed sources/segments, wrong CRS, incomplete responses and overlapping coverage.

## Official maps and retained discrepancy

Full-page maps and enlarged notes were visually reviewed using URLs obtained from
the publisher index. All state adoption August 3, 2005, effectiveness August 18,
2005, and adoption of digital NWI wetlands on August 18, 2005.

| Official map | Additional amendment evidence |
| --- | --- |
| [T10 R15 WELS](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/t10-r15-wels.pdf) | No later amendment listed in the captured PDF table. |
| [Chesuncook Township](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/chesuncook-twp.pdf) | ZP774, location 1, effective January 25, 2019. |
| [T1 R11 WELS](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/t1-r11-wels.pdf) | ZP770, location 1, effective April 26, 2018. |

**T1 R11 metadata discrepancy:** map-index `AMEND_DATE` corresponds to August 18,
2005, while the PDF lists the 2018 amendment. Both versions are preserved; this
remains a TL-F-0029 follow-up before using index amendment metadata to claim legal
currency. It does not contradict the exact source-geometry comparison above.

The initial name query omitted Chesuncook because the index uses `Chesuncook Twp.`
with a terminal period. A follow-up query on the observed `MAP` value located its
record and PDF URL. This is a retrieval-name issue, not absent map coverage.

All maps show P-SL2 and wetland/lake context. Notes defer to Chapter 10 for conflicting
descriptions, retain protections omitted from the drawing and describe water-dependent
boundaries following water on the ground. No tracing was used. Maps do not certify
exact ownership topology, legal boundaries, access, septic suitability or buildability.
Document dates do not establish legal currency. See [map review](map-review.json).

## Audit and next step

- Audit: `33259813dfcc2b5fa814d0f49547df52c71e5bab9f3a5e3de1e60106efe86673`.
- Ranking: `5510a6d2d39e371d8456d68201970f047b6e8893c8fca0dfffc8b21ddf1a6e27`.
- Snapshot: `bcd341fe5cd1d7afe0a2d79a1e58991c5e4c954f6f8f64add9592a8cfca89eed`.
- [Dependencies](dependencies.json) pin all eleven accepted correction/event versions.
  The metadata load locks the county batch and rejects stale dependencies.
- [Archive manifest](archive-manifest.json) identifies private source responses,
  PDFs, candidates, methods and tests. Geometry/PDF bytes are excluded from Git.
- Thirteen requests succeeded; no failed retrievals. The document collector's
  generic `NON_JSON_RESPONSE` label is preserved; service JSON is separately parsed
  and validated by the investigation.
- [Finding review](finding-review.json) keeps TL-F-0029 in progress, including the
  map-index discrepancy. Review exact proposal hashes, extend/test bounded acceptance,
  activate supported versions, then refresh ranking. Retain the 21 parcel holds and
  all other county qualification follow-ups.

## Reproduce

Restore manifest objects to `report.inputs` paths using the recorded runtime:

```sh
python scripts/investigate_latest_three_zoning_priorities.py
python -m unittest discover -s tests -p 'test_latest_three_zoning_priorities.py' -v
python -m unittest discover -s tests -p 'test_moosehead_spencer*.py' -v
python scripts/prepare_latest_three_zoning_priorities.py --output .local/new-latest-three-load
```

Independently verify archive bytes before applying the guarded metadata load.
No migration, activation or original source-feature write is included. Replaying
archived observations does not establish freshness; changed sources or dependencies
require a new audit.

## Recorded state

All **70 private archive objects** passed checksum verification: 31 newly downloaded
objects and 39 reverified copies from earlier independent downloads. Supabase
contains the audit, thirteen new observations and fifteenth TL-F-0029 occurrence/review.
[Live verification](live-verification.json) confirms all 120,449 original row
fingerprints, eleven acceptance versions and unrelated finding events unchanged.
The three investigated features remain held; the baseline snapshot is current and
qualified parcel screenings remain zero. See [checkpoint](checkpoint.json).
