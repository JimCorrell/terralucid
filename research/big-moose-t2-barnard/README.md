# Big Moose, T2 R12 WELS and Barnard zoning proposals

Investigate the first three priorities from merged PR #42. **All three have supported
exact-source interpretations**, pending acceptance. Fourteen accepted versions and
**148 zoning / 169 total effective holds** remain unchanged.

## Results

| OBJECTID / map | Zone | Interpretation | Source rings → candidate shells / holes | Potential added geometry |
| --- | --- | --- | --- | ---: |
| 27257109 / Big Moose Township | M-GN | Ring 30 separates a shell and its hole at an existing contact vertex. | 74 → 41 / 34 | 64.0876 km² |
| 27321193 / T2 R12 WELS | P-SL2 | Rings 9 and 62 each separate two holes touching at one existing vertex; two separate nested holes retain innermost owners. | 221 → 116 / 107 | 3.2609 km² |
| 27303187 / Barnard Township | P-SL2 | Ring 23 separates a shell and its hole at an existing contact vertex; two nested holes retain innermost owners. | 212 → 107 / 106 | 3.9662 km² |

Ring indices are zero based. Combined potential gain is **71.3147 km²** beyond
original valid zoning geometry and all fourteen accepted corrections, counting
overlap once. Big Moose's large M-GN feature contributes most of this gain. This
measures usable inventory geometry, not legal coverage, available building area or
parcel quality. Ranking estimates were overlapping bounding-box upper bounds.

## Evidence and checks

Fresh native EPSG:26919 records exactly match preserved county features, including
coordinates and attributes. All three service GeoJSON representations retain the
same source segments but remain invalid at source contacts. Format conversion
alone does not resolve these holds.

Existing bounded interpretation methods split only at repeated source vertices,
with no coordinate moves, snapping or general repair. Every source segment and its
multiplicity is preserved. Complete candidates are valid and agree with publisher
area values within 0.000002 m²; this is a numerical check, not survey precision.
Separate routines check fixed candidate cycle roles and touching-hole ownership.
Ray crossing agrees on all **511 linework faces**, with zero fill difference.
Different algorithms share GEOS and do not constitute independent publisher approval.

The [report](report.json) pins source versions, contact coordinates, candidate hashes,
checks and coverage calculations. [Test results](test-results.json) record 23 passing
tests covering authentic contact patterns, nested ownership, altered sources,
missing holes, unsupported contacts, wrong CRS, incomplete responses and overlap
calculations. Original records and source holds remain preserved.

## Official maps and amendment metadata

Publisher index URLs led to the official [Big Moose](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/big-moose-twp.pdf),
[T2 R12 WELS](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/t2-r12-wels.pdf)
and [Barnard](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/barnard-twp.pdf)
PDFs. Full pages and enlarged notes were visually reviewed. All state adoption
August 3, 2005, effectiveness August 18, 2005, and adoption of digital NWI wetlands
on August 18, 2005. T2 R12 and Barnard list no later amendments in their captured tables.

Big Moose lists ZP707 (2009-10-08), ZP707A (2010-08-19), ZP744 (2014-05-29), ZP758
(2015-12-24), ZP757 (2016-01-30), ZP707B (2020-07-30) and ZP791 (2022-12-30).
The first two rows describe a P-RP 014 expiration in 2039; the later ZP707B row
records its termination. These are document statements, not a legal determination.

**Big Moose's map-index AMEND_DATE remains 2016-01-30**, despite the PDF's later
2020 and 2022 rows. Both sources are retained and the discrepancy is tracked in
TL-F-0029 alongside the existing T1 R11 discrepancy. Resolve amendment metadata
before relying on it for legal currency. The Big Moose map also directs island
zoning to separate Moosehead Lake Islands maps; this review does not establish
island applicability.

Maps provide broad district context, not exact contact topology. Their notes defer
to Chapter 10 for conflicting descriptions, retain protections omitted from the
map and describe water-dependent boundaries following water on the ground. No map
tracing was used. Legal boundaries, access/title, septic suitability, buildability
and current applicability remain unknown. See [map review](map-review.json).

## Audit and next step

- Audit: `eca57f7cce399a9f4de70d6096c4adf002f79d5528927983374e19d51c5d6a50`.
- Ranking: `3dd7c8ccf884b20e49fae2f0949b047cf7635cea978ea287053b5a6ab96ef10d`.
- Snapshot: `7d750c5646a7e6368835db664092e4941e14908f35369a19d90863bacbddd492`.
- [Dependencies](dependencies.json) pin fourteen acceptance versions. The metadata
  load locks the county batch and rejects stale dependencies.
- [Archive manifest](archive-manifest.json) identifies private sources, PDFs,
  candidates, methods and tests. Geometry and PDF bytes are excluded from Git.
- Twelve retrievals succeeded; no failed requests. The document collector's generic
  `NON_JSON_RESPONSE` label is preserved, with JSON separately parsed and validated.
- [Finding review](finding-review.json) keeps TL-F-0029 in progress. Next: review exact
  proposal hashes, extend/test bounded acceptance, activate supported versions, then
  refresh ranking. Retain both amendment discrepancies, 21 parcel holds and other
  county qualification issues.

## Reproduce

Restore manifest bytes to `report.inputs` paths using the recorded runtime:

```sh
python scripts/investigate_big_moose_t2_barnard.py
python -m unittest discover -s tests -p 'test_big_moose_t2_barnard.py' -v
python -m unittest discover -s tests -p 'test_moosehead_spencer*.py' -v
python scripts/prepare_big_moose_t2_barnard.py --output .local/new-bmt-load
```

Independently verify archive bytes before the guarded metadata load. This proposal
step contains no migration, activation or original-feature write. Replaying archived
observations does not establish freshness; changed sources/dependencies require review.

## Recorded state

All **69 private archive objects** passed checksum verification: 26 newly downloaded
objects and 43 reverified earlier independent downloads. Supabase contains the audit,
twelve new observations and eighteenth TL-F-0029 occurrence/review.
[Live verification](live-verification.json) confirms all 120,449 original row
fingerprints, fourteen acceptance versions and unrelated finding events unchanged.
The three proposals remain held, the baseline snapshot is current, and qualified
screenings remain zero. Both amendment-metadata follow-ups remain in the finding's
next action. See [checkpoint](checkpoint.json).
