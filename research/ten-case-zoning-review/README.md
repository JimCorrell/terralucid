# Ten priority cases and the Katahdin Iron Works exception

## Result

The ten cases recommended by the [backlog assessment](../county-backlog-assessment/README.md), plus Katahdin Iron Works OBJECTID 27358396, support **eleven exact-version geometry proposals**. Original features and all seventeen accepted corrections are preserved. **No activation:** 145 zoning and 21 parcel holds remain.

The combined additional usable inventory geometry scenario is **87.0005 km²**, counting overlap once against the seventeen-correction baseline. Katahdin contributes 6.0521 km² individually. This is conditional inventory coverage, not legal zoning coverage, buildability or parcel qualification.

| OBJECTID | Map | Service GeoJSON | Individual conditional gain |
| --- | --- | --- | ---: |
| 27342226 | beaver-cove | Invalid | 32.4023 km² |
| 27365331 | t7-r10-wels | Valid; equals proposal | 7.1264 km² |
| 27364426 | orneville-twp | Invalid | 6.7297 km² |
| 27339379 | bowdoin-college-grant-west-twp | Valid; equals proposal | 5.7875 km² |
| 27364538 | t5-r14-wels | Valid; equals proposal | 5.2336 km² |
| 27324664 | t1-r13-wels | Invalid | 4.9661 km² |
| 27321394 | t4-r9-nwp | Invalid | 4.9646 km² |
| 27366878 | shawtown-twp | Invalid | 4.6951 km² |
| 27261431 | t3-r13-wels | Valid; equals proposal | 4.5692 km² |
| 27304932 | t4-r12-wels | Invalid | 4.4738 km² |
| 27358396 | katahdin-iron-works-twp | Invalid | 6.0521 km² |

Do not sum individual gains: their footprints can overlap. Four service GeoJSON representations are valid and exactly equal the proposals; seven remain invalid. All eleven freshly retrieved native features match the original capture, including attributes and coordinates. Service variants preserve the same attributes and segment multiplicity.

## Katahdin exception

The original first ring visits **two distinct coordinates twice**. The existing one-contact method correctly refused it. A bounded new method cuts that traversal into one clockwise shell and two counterclockwise holes; it does not snap, simplify, move coordinates, or invoke a general repair.

The 3,204-coordinate ring separates into cycles with 3,133, 61 and 12 coordinates (closure coordinates repeat by design). Source-cycle areas are approximately 3,191,414.126, 19,426.250 and 1,978.288 m². Both holes remain owned by the original shell. Other source rings retain their roles.

The proposal algorithm uses recursive coordinate slicing. A separate stack-based source walk checks the fixed serialized result, and an independent ray-crossing/polygonized-face diagnostic checks its complete fill. All 304 Katahdin source faces agree, and every segment with its multiplicity is preserved. The full candidate area differs from the publisher area by less than 0.000002 m²; numeric agreement alone is not authority. The same GEOS engine underlies these checks, so they are not independent publisher evidence.

This is support for this exact source version only. The correction validator has not been extended, and the method is not an ingestion fallback for other multiple-contact rings.

## Official map evidence and retained deficiencies

All eleven official map URLs came from the retrieved LUPC map index. Full-page renders, enlarged notes and extracted text were inspected. The maps corroborate district context and limitations; no PDF boundary was traced and no exact vertex location was inferred from a printed map.

Five additional date follow-ups remain open:

| Map | Index AMEND_DATE | Latest PDF amendment |
| --- | --- | --- |
| beaver-cove | 2012-09-04 | 2022-12-30 |
| orneville-twp | 2005-08-18 | 2024-08-01 |
| bowdoin-college-grant-west-twp | 2005-08-18 | 2020-07-30 |
| t1-r13-wels | 2005-08-18 | 2020-07-30 |
| shawtown-twp | 2015-06-24 | 2015-06-25 |

Shawtown also has an internal one-day difference: its effective-date paragraph says June 24, 2015, while the ZP750 amendment row says June 25. Orneville identifies ZP796 as a clerical correction to FEMA-adoption text; this review makes no flood-zone or legal-applicability determination.

The previous **Big Moose (2016-01-30 / 2022-12-30)** and **T1 R11 (2005-08-18 / ZP770 2018-04-26)** follow-ups remain open. Geometry support does not settle any of these seven date questions.

The maps warn that Chapter 10 descriptions govern conflicts, some stream/wetland protections are omitted from drawings, and water-dependent boundaries may follow actual water locations. These are retained as map statements, not a fresh legal opinion. Access/title, surveyed boundaries, septic/buildability, municipal applicability and wetland imagery age remain unresolved.

## Evidence and tests

- [Report](report.json) pins original, native, GeoJSON, proposal, map and method versions for every case.
- [Map review](map-review.json) records official PDF URLs, hashes, document dates and caveats.
- [Dependencies](dependencies.json) binds the current seventeen-correction snapshot and finding versions.
- [Tests](test-results.json): **31 tests pass**, including changed sources/CRS/segments, nested ownership, overlapping scenarios and the new bounded-contact cases. Fixed candidates pass checks across **3,110 source faces**.
- [Finding review](finding-review.json) carries all seven date follow-ups and remaining county issues under TL-F-0029.
- [Archive manifest](archive-manifest.json) records private original bytes and proposals. Six initial 2 MB size-limit failures are preserved; complete larger responses were captured with the existing 25 MB collector.

## Reproduce and review

Restore private source/candidate bytes at the report paths, using the recorded runtime:

```sh
python scripts/investigate_ten_case_zoning.py
python -m unittest discover -s tests -p 'test_ten_case_zoning.py' -v
python -m unittest discover -s tests -p 'test_moosehead_spencer*.py' -v
python scripts/prepare_ten_case_zoning.py --output .local/new-ten-load
```

The guarded audit load checks the exact correction snapshot and finding event. Source responses, the investigation and the review event are appended atomically. Check `scripts/check_ten_case_zoning.sql` after publication.

Next: review this evidence, extend/test bounded acceptance for supported exact versions, activate and refresh the ranking and coverage-return assessment. Then revisit the county cleanup stopping point. No parcel screening should inherit these unaccepted proposals.

## Live checkpoint

The investigation audit, 36 source observations and TL-F-0029 occurrence 21 are
recorded in Supabase. All 116 archive objects passed checksum verification
(62 new independent downloads and 54 reverified earlier downloads). Six initial
size-limit failures remain in the archived logs.

[Live verification](live-verification.json) and [checkpoint](checkpoint.json) confirm
all eleven cases still held, 17 accepted correction/event versions unchanged,
145 zoning and 21 parcel holds, unchanged original fingerprints, current ranking
dependencies and zero county rows qualified for parcel screening. Unrelated
findings are unchanged; all seven map-date follow-ups remain tracked.
