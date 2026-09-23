# Bounded Piscataquis qualification tests

Run from merged PR #53 (`159659e`). These tests exercise source-parcel and small
area qualification against the existing private Supabase county inventory. They
are diagnostic selections, not purchase candidates or a representative county
sample. No source correction, finding resolution or screening promotion occurs.

## Selection and expectations

| Case | Selection | Expected behavior |
| --- | --- | --- |
| Orneville parcel | First valid UT source record by object ID, GEOCODE 21821, area 100–2,000,000 m² | Preserve actual parcel geometry and archived 230465A/27-letter evidence; no flood clearance |
| Overlapping sources | First positive-area UT overlap among the first 1,000 organized source records by object ID with interior county relation and area 100–2,000,000 m² | Retain distinct source records and INFERRED overlap candidates; canonical identity UNKNOWN |
| Parcel near a hold | First valid parcel of 100–10,000,000 m² fully covered by county boundary, intersecting a held zoning extent from the seed capture | Withhold zoning intersections and retain the potentially relevant hold |
| Accepted zoning area | Ten-metre circle around a point inside the first accepted correction by ID, fully within county | Use the accepted exact-version geometry and retain correction provenance |
| Held source parcel | First held assessment source record in the seed capture | Reject as an AOI; never use a repaired or inferred boundary |
| Purchase flag (local simulation) | Copy the Orneville capture in memory and set the workflow flag | Require septic/buildability review, without blocking general discovery or designating a real purchase candidate |

Area limits are test-selection bounds, not user preferences, qualification rules,
or suitability thresholds. Original geometry is used only to find test candidates;
the qualification query always uses the accepted effective view and verifies the
expected condition independently. A held extent is a conservative bound, not an
assertion that the invalid polygon covers the parcel.

Every successful packet must stay within county scope, leave parcel-screening
qualification false and offer readiness NOT_ASSESSED, retain soils/terrain adapter
unknowns, and leave septic/buildability unrequested for discovery. A fresh context
query checks all packets at the end. The backend is checked before and after the
suite to confirm one database session.

## Reproduction

Use the existing Python/Shapely environment and an authenticated Supabase CLI.
The seed is a private compact capture for the intended county audit and geometry
snapshot, containing held source references and conservative extents. Keep raw
captures, parcel identifiers and packets private. The output directory must be new.

```sh
python3 tests/run_county_qualification_live.py \
  --cli /path/to/supabase \
  --seed-capture .local/verified-county-capture.json \
  --output .local/new-county-test-run
```

The explicit live runner obtains temporary credentials once and uses one psql
session. It has no authentication retry or direct Keychain lookup. All database
queries run in read-only transactions with deadlines; the client is closed on
completion or failure. Local purchase-flag simulation makes no database changes.

An initial selection attempt stopped because the first held extent had no valid
parcel within the test size bound. It passed authentication and metadata checks
but produced no qualification test results. The selection now considers all held
zoning extents in the seed; the failed attempt is retained in the report history.

## Results — 2026-09-23

**All six scenario checks passed.** Four live packets passed a final fresh-context
comparison (`needs_revisit=false`). The successful suite used one credential
acquisition and one database session, confirmed by backend identity; it completed
in approximately 61 seconds. The 22 existing qualification unit tests also pass.
The initial no-candidate selection attempt is separately preserved in `report.json`.

| Case | Observed result |
| --- | --- |
| Orneville parcel | Full geometric identity/LUPC/project-footprint coverage; inventory intersections usable with review limits; 230465A and 27 letters retained |
| Overlapping sources | Three cross-source overlap candidates retained; about 1.07% LUPC coverage, with incomplete-coverage and municipal-source warnings; flood adapter missing |
| Parcel near a hold | One zoning hold blocks zoning intersections; identity and wetlands inventory intersections remain usable with their review limits |
| Accepted zoning area | Reviewed correction and provenance used; full geometric coverage; flood adapter missing |
| Held source parcel | Rejected as an AOI before producing a qualification packet |
| Local purchase-flag simulation | Septic/buildability switch to review required; general discovery remains unblocked |

Full geometric project-footprint coverage is not wetland absence or completeness.
Missing flood-adapter evidence is not a conclusion that no flood hazard exists.
All packets preserve source/currentness/legal unknowns, open finding candidates,
false parcel-screening qualification and NOT_ASSESSED offer readiness.

### Numerical precision follow-up

The accepted-area packet reports fractions as high as `1.0000000000000002`.
The overlapping-source identity coverage reports an uncovered area of
`5.426966254162835e-08` m² and therefore `partial_geometric` under the existing
zero-gap rule. Floating-point arithmetic is a plausible explanation; the tests
do not establish a real-world gap. Record this as the open
`qualification-numerical-precision` test follow-up in `report.json`. No tolerance,
rounding rule, repair or qualification relaxation was introduced. This is a local
analysis follow-up, not a new source deficiency or an assigned TL-F register ID.

Review numerical precision with reproducible fixtures next. The missing source
adapters and parcel-specific applicability work remain separate backlog items.
