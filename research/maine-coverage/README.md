# Maine coverage and identifier audit — 2026-09-20 UTC

This is a **DERIVED source-quality report**, based on archived official service
responses. It establishes a reproducible reference denominator, reported source
presence, candidate-key quality and a bounded assessment-join test. It does not
certify current legal jurisdiction status, complete parcel coverage or title.

## Findings that affect ingestion

1. Use the GEOCODES table's **STATUS**, not the civil polygon layer's **TYPE**, for
   the reference classification. Observed TYPE values are blank, `coast`, `fresh`
   and `submerged`; publisher metadata describes it as polygon type.
2. Preserve each source record independently. `STATE_ID`, `TPL` and `GPL` are not
   unique. A declared one-to-one assessment relationship is not reliable as a
   database constraint.
3. Keep code/name conflicts unresolved in staging. The official reference identifies code/name conflicts for Sweden and Alfred.
   Identifier prefixes independently support Sweden; Alfred remains ambiguous.
   Raw records have not been reassigned.
4. Treat missing source presence and missing dates as UNKNOWN. Never interpret
   these as no property, no restrictions, or current data.

## Dated reference and source presence

The [official GEOCODES table](https://services1.arcgis.com/RbMX0mRVOFNTdLzd/arcgis/rest/services/Maine_Town_and_Townships_Boundary_Polygons/FeatureServer/1)
contains 933 unique codes. We use its 917 records with C/T/P/U/R status for this
comparison and explicitly exclude 16 county-island codes with blank STATUS. All
917 appear in the civil polygons. The polygon layer's 8,421 features and 924
unique code values (including a blank) are different units of measurement.

The labels below follow the [GeoLibrary geographic-code standard](https://www.maine.gov/geolib/policies/geocodes.html).
That page was available in search indexing but its direct archived request failed;
the live code records and [polygon metadata](https://maine.maps.arcgis.com/sharing/rest/content/items/289a91e826fd4f518debdd824d5dd16d/info/metadata/metadata.xml?format=default&output=html)
were retrieved. STATUS reflects this dated source, whose jurisdiction-by-jurisdiction
legal effective dates have not been established.

| Reference STATUS | Reference codes | UT parcel source | Organized parcel source | Assessment table |
| --- | ---: | ---: | ---: | ---: |
| City (C) | 23 | 0 | 23 | 20 |
| Town (T) | 431 | 9 | 292 | 191 |
| Plantation (P) | 31 | 29 | 3 | 0 |
| Unorganized Township (U) | 429 | 425 | 0 | 0 |
| Reservation (R) | 3 | 0 | 0 | 0 |
| **Total** | **917** | **463** | **318** | **211** |

These columns count **reference codes with at least one reported source record**,
not complete municipalities or legal parcels. Conflicting names still count under
their raw reported code. For example, records named Sweden and Alfred use codes for other towns, so
absence under their reference codes does not establish absence of data.

The parcel-source union is **776** codes; **141** have no records under their codes
in either source. Five codes occur in both: Deer Isle, Osborn, Kingsbury Plt,
Highland Plt and West Forks Plt. This is jurisdiction-level overlap only; no parcel
geometries or legal properties were deduplicated.

Source counts reconcile: **36,688 UT features**, **708,382 organized features** and
**522,253 assessment rows**. Coverage and date aggregates used in the report have
no transfer-limit flag and sum to their control totals. Start/end counts agree;
organized/assessment editing metadata also agree. UT editing metadata were not
provided. These checks reduce drift risk but are not an atomic snapshot guarantee.

## Conflicts and unknown assignments

| Observed group | Rows | Reported code | Reference code for name | Supporting check |
| --- | ---: | --- | --- | --- |
| Sweden | 691 | 17290 (Stow) | 17310 | All 691 STATE_ID values begin with 17310. The sampled assessment match also reports 17310. |
| Alfred | 1,634 | 31030 (Arundel) | 31020 | Zero of the 1,634 STATE_ID values begin with 31020; the sample instead repeats 31030. Which source field is wrong remains unresolved. |

Other name differences include blank names, East Millinocket misspellings and
`Plantation` versus `Plt`. The report records these differences and exact-name
candidate codes; it performs no fuzzy matching or automatic correction.

The UT source also has 3 rows under `59793` and 66 under `65185`, both absent from
the reference and with null town names. Four UT rows and 14 organized rows have
blank jurisdiction codes. These remain outside the reference coverage counts.

## Candidate-key profile

Counts below use the source server's comparison/collation rules with no client
normalization. On these services, comparing a key with `''` also captures observed
space-only values; those counts must not be added twice. Missing STATE_IDs comprise
3,718 null + 91 empty/space organized records, and 173 null assessment records.

| Source / key | Present rows | Distinct values | Missing | Excess rows over distinct values |
| --- | ---: | ---: | ---: | ---: |
| UT / TPL | 36,684 | 35,871 | 4 | 813 |
| UT / GPL | 36,684 | 35,840 | 4 | 844 |
| Organized / STATE_ID | 704,573 | 667,056 | 3,809 | 37,517 |
| Assessment / STATE_ID | 522,080 | 493,670 | 173 | 28,410 |

“Excess” is present rows minus distinct keys, not the number of duplicate groups
or duplicate legal parcels. Repeated identifiers may represent multiple source
features, assessment units or placeholder values; their meaning needs investigation.
Examples include `31040_` on 2,209 organized features and `01020_unknown` on 2,023.
Assessment key `31197_24` occurs 1,743 times. No owner details were requested.

GlobalID is present and distinct for every row in all three sources in this audit.
It can identify a record within a source/version; stability across refreshes and
its relationship to legal parcel identity remain untested. Compound map/lot
uniqueness was not established; an attempted multi-field distinct count was rejected.

## Assessment relationship test

Select the minimum geometry OBJECTID in each of the 327 reported code/name/county
groups. This produces 327 source rows with 321 distinct nonblank STATE_IDs; six
sample rows have missing keys. Query complete per-key counts on both sides:

| Observed cardinality | Sample keys |
| --- | ---: |
| One geometry / one assessment row | 167 |
| No assessment match | 143 |
| Multiple geometry / multiple assessment rows | 6 |
| Multiple geometry / one assessment row | 3 |
| One geometry / multiple assessment rows | 2 |

This is a deterministic geographic/source-group sample, **not a random sample or
statewide match rate**. Even one-to-one matches need consistency checks: the Sweden
sample's geometry and assessment disagree on GEOCODE. Matching identifiers do not
establish ownership or title.

## Date handling

The report retains every raw date bin and its jurisdiction group. Parsing yields:

| Source field | Year precision | Day precision | Missing | Malformed / uninterpreted |
| --- | ---: | ---: | ---: | ---: |
| Organized FMUPDAT | 346,894 | 255,412 | 105,985 | 91 |
| UT MAPYEAR | 28,551 | — | 480 | 7,657 |

FMUPDAT malformed values are `0` (90) and `20` (1). MAPYEAR includes zero (7,654)
and three short numeric values. Years remain years; no January 1 date is invented.
MAPYEAR is a source map-year field, not proof of current survey or ownership status.
Assessment YEAR_CREAT interpretation is still open. Its initial per-code date query
was truncated and is excluded; the later global value distribution is archived.

## Evidence, reproduction and storage

- [registry.json](registry.json): versioned four-source registry for this audit.
- [report.json](report.json): every reference code, source counts, missing-key counts,
  raw/parsed date groups, conflicts, sample joins, controls and response provenance.
- Seven probe manifests and `runs/*/results.json`: exact requests, UTC retrieval
  times, HTTP outcomes, byte counts and SHA-256 checksums for **121 requests**.
- 92 responses returned JSON without API errors; 26 API errors, two HTTP errors
  and one successful HTML metadata response are preserved. Failed queries are
  research evidence, not successful measurements.

The hosted service ignored an attempted `havingClause` filter: the returned rows
included count=1. Those responses are explicitly excluded as duplicate evidence;
subsequent count-sorted examples were inspected. Oversized sample URLs were replaced
with short batches. The analysis rejects corrupt snapshots, truncated complete
aggregates, missing sample IDs and control-total drift.

Reproduce the derived report offline from the repository root:

```sh
python3 -m unittest discover -s tests
python3 scripts/audit_maine_coverage.py --output /tmp/terralucid-coverage-report.json
```

For a new live audit, replay the manifests using `scripts/probe_sources.py` into new
run directories. Regenerate adaptive sample/join requests from the new returned
OBJECTIDs and keys; the committed sample manifests intentionally reproduce the
recorded selection and must not be assumed representative of a later publication.

Prepare this batch for Supabase using a fresh local output directory:

```sh
python3 scripts/prepare_source_staging.py prepare --audit research/maine-coverage --report research/maine-coverage/report.json --output .local/coverage-load
```

The source registry and responses use the existing private staging tables. The new
`ingest.audit_result` table holds the explicitly DERIVED report, linked to its
registry version and archived report/method checksums. Exact artifacts use the
existing private Storage bucket. Repeated identical loads add no rows. Follow the
[upload, download-verification and transaction sequence](../../docs/supabase-staging.md);
use `application/octet-stream` for this mixed JSON/HTML/Python archive.

## Next gate

Proceed with a bounded source-record load designed to tolerate these findings:

- Keep source/version/GlobalID identity and raw identifiers; investigate refresh stability.
- Quarantine code/name conflicts and unrecognized codes before canonical joins.
- Store assessment records separately; represent zero/one/multiple candidate matches explicitly.
- Reconcile object-ID batches, row counts and geometry validity; retain every source geometry.
- Resolve missing-source jurisdictions through municipal/reference research; inspect UT valuation-book linkage.

Full join coverage, repeated-key meanings, compound-key uniqueness, legal-effective
jurisdiction dates, source rights, UT valuation extraction and parcel-level overlap
remain open. These gaps prevent declaring canonical parcel integration complete.

## Deployment verification

Loaded into Supabase project `yytsjlmbyqhcqfalbjca` on 2026-09-20 UTC. All 94 unique
artifacts in this batch were downloaded from private Storage and verified against
the prepared manifest before the database transaction. This includes exact source
responses, logs, registry, report and calculation code; identical response bytes
share an object. The original audit remains preserved.

The live report checksum matches the repository artifact; its 121 observations
and 933 reference rows reconcile. A repeat import left counts unchanged. Row-level
security is enabled and all client table-access checks pass. Eight automated tests
passed, along with local PostgreSQL/PostGIS migration and repeated-import checks.
