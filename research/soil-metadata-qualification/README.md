# County soil metadata qualification audit

## Result

**DERIVED:** metadata is sufficient to propose a bounded, limitation-bearing soil
inventory availability adapter. This audit does **not** enable that adapter,
change source records, certify completeness, or assess any parcel for septic or
building suitability. TL-F-0113 remains in progress.

The analysis uses the original verified source bundle and the accepted geometry
snapshot from PR #61. It selects unique map units linked to positive-area county
polygons, including the three accepted county-intersecting corrections. These are
counts of linked records, not area-weighted estimates or separately mapped
component footprints. Snapshot currency must be rechecked before downstream use.

| Scope | Map units | Components | Horizons |
| --- | ---: | ---: | ---: |
| Whole seven-survey tables | 601 | 1,572 | 6,689 |
| Linked to county-intersecting polygons | 278 | 770 | 3,382 |

## Units and interpretation

The bounded dictionary below is corroborated by USDA's November 2025 SDM 4.3
[Tables and Columns report](https://sdmdataaccess.sc.egov.usda.gov/documents/TablesAndColumnsReport.pdf),
printed pages 6 and 30. Other loaded columns remain outside this audit's qualified
unit dictionary.

| Field family | Unit | Consumer rule |
| --- | --- | --- |
| `component.comppct_{l,r,h}` | percent | Preserve source proportions and unrepresented remainder; no silent normalization |
| `component.slope_{l,r,h}` | percent | Component summary, not DEM-derived parcel slope |
| `chorizon.hzdept_{l,r,h}`, `hzdepb_{l,r,h}`, `hzthk_{l,r,h}` | cm | Horizon depths/thickness; do not infer missing values |
| `chorizon.ksat_{l,r,h}` | micrometers/second | Hydraulic conductivity, not a site percolation test |
| `chorizon.awc_{l,r,h}` | cm/cm | Water-capacity ratio |
| `chorizon.sandtotal_{l,r,h}`, `claytotal_{l,r,h}` | percent | Preserve nulls and source ranges |

USDA's [Query Guide](https://sdmdataaccess.sc.egov.usda.gov/documents/SoilDataAccessQueryGuide.pdf),
printed page 35, defines low/representative/high suffixes. Representative values
are typical aggregated component properties, not measurements at every location.
The ranges are not statistical confidence intervals. Retain all three values and
their missingness; do not invent a location for each component inside a polygon.

## Scale and dates

| Survey | Recorded project scale | Survey version | FGDC dataset period beginning |
| --- | --- | ---: | --- |
| ME602 | 1:20,000 | 25 | 2004-03-24 |
| ME612 | 1:24,000 | 11 | 2016-09-19 |
| ME614 | 1:20,000 | 24 | 2004-12-22 |
| ME615 | 1:24,000 | 28 | 1996-08-30 |
| ME619 | 1:24,000 | 30 | 2006-07-17 |
| ME620 | 1:24,000 | 15 | 2012-02-03 |
| ME621 | 1:24,000 | 15 | 2012-02-03 |

All seven FGDC periods end August 29, 2025 and explicitly use **publication date**
as their currentness reference. Their publication and metadata dates also say
August 29, 2025. Fresh catalog versions, version-established timestamps and complete
FGDC text exactly match the archived capture for all seven surveys. This comparison
cannot detect every attribute change that leaves catalog metadata unchanged.

`projectscale` describes publication scale. `saverest` identifies establishment of
a data version. `cordate` is correlation-document signing, and is null in all seven
loaded legends. None is a uniform field-observation date. The FGDC lineage contains
multiple source scales and dates, preserved separately in the report; a source
map's scale is not substituted for project scale. Attribute-specific field age and
current site conditions remain UNKNOWN. Definitions are from USDA's
[Column Descriptions](https://sdmdataaccess.sc.egov.usda.gov/documents/TableColumnDescriptionsReport.pdf),
printed pages 68 and 85; per-survey observations come from the captured FGDC response.

The earlier readiness note called `saverest` a restoration date. Use **version
established** instead. Keep the historical note and this clarification visible.

## Missingness and variability

For the county-linked subset:

- **262/278 map units** have representative component totals below 100%, ranging
  from 75% to 99%; the remaining 16 total 100%. None exceeds 100% and none has a
  missing representative percentage. This is a source representation limitation,
  not evidence that our complete table retrieval dropped rows. No normalization
  or automatic repair is proposed.
- **239 map units** contain multiple components; **213** contain more than one
  nonmissing drainage class. There are no ties for the largest listed component,
  but choosing that component would still hide mixtures and missing proportions.
- **10 components** have no horizon records. All are `Miscellaneous area`: water,
  water bodies, urban land or rubble land. Preserve the absence; do not classify
  it as soil-horizon completeness or automatically as an ingestion failure.
- Component missing values: slope 14, drainage class 15, hydric rating 14,
  hydrologic group 24. Horizon representative values missing: AWC 195, sand 697,
  clay 696. All 3,382 linked horizons have representative top/bottom depths and
  low/representative/high conductivity values.
- Checked numeric families have no inverted available low/representative/high
  values. No nonpositive representative horizon depth intervals or adjacency
  gaps/overlaps were found. Missing bounds remain missing: all 770 county-linked
  component percentage ranges are incomplete despite populated representative
  percentages. Passing these checks does not validate all attributes/domains.

The report retains whole-survey results separately: 19 components lack horizons
and four horizons lack conductivity there. Those whole-survey counts must not be
reported as county-linked deficiencies.

Two interpretation hazards require explicit handling:

1. `vtsepticsyscl` is populated on **10 county-linked map units**, but USDA describes
   it as a Vermont-specific septic interpretation. Preserve it as source data;
   exclude it from Maine septic qualification. No claim is made about whether the
   underlying source values themselves are erroneous.
2. All county-linked map units have null `mustatus` and `mucertstat`. USDA identifies
   these legacy fields as no longer supplied. They cannot establish readiness or
   currentness; null is not by itself a newly discovered source defect. See
   [Column Descriptions](https://sdmdataaccess.sc.egov.usda.gov/documents/TableColumnDescriptionsReport.pdf),
   printed pages 71–72.

## Recommended bounded adapter contract — not activated

The next implementation should report **inventory availability with limitations**,
while keeping site suitability unknown. Map this meaning explicitly onto the
existing qualification model during implementation; this document adds no new enum.

- Require the intended source batch, current accepted-geometry snapshot, pinned
  study boundary and coverage result; never inherit another version's qualification.
- Return source polygon/map-unit identifiers, component/horizon records, documented
  units, project scale, publication/version dates and per-field null/range flags.
- Carry component percentage totals and remainder without renormalizing, and keep
  miscellaneous-area horizon absence distinct from an available soil profile.
- Exclude Vermont septic interpretation from Maine qualification; keep other
  unreviewed attribute definitions and interpretation versions unknown.
- Preserve UNKNOWN field-observation age and parcel/site applicability. Complete
  geometric coverage is insufficient for septic approval or building clearance.

No scoring weights, slope thresholds, soil suitability cutoffs or new canonical
parcel identities are selected. Detailed septic/buildability review remains
triggered only for purchase candidates.

## Evidence and reproduction

[Report](report.json) pins source bundle, method, accepted-geometry evidence and
survey metadata, and lists all percentage exceptions and absent-horizon identities.
[Sources](sources.json) records exact URLs, query, hashes and retrieval times. The
three official PDFs and complete seven-survey FGDC response remain private, with
[archive readback](archive-verification.json). PDFs were inspected visually at the
cited pages as well as extracted for search. The earlier failed metadata-table
query was not retried; publisher reports and `sacatalog.fgdcmetadata` supply evidence.

```sh
python scripts/collect_soil_metadata.py --output .local/new-soil-metadata
python scripts/audit_soil_metadata.py \
  --bundle .local/county-soils-prepared-final \
  --evidence .local/new-soil-metadata --output .local/new-soil-metadata-audit
python -m unittest discover -s tests -p test_soil_metadata.py
```

Fresh capture is a currency check, not byte-for-byte historical reproduction.
Restore archived source bytes by hash to reproduce this exact audit. Four focused
checks test null/range treatment, component mixtures/totals and horizon gaps/overlaps.

The [finding update](finding-update.json) appends this audit to TL-F-0113, keeps it
in progress and verifies the accepted geometry snapshot is still current. No source
or qualification-state writes were performed. Six evidence objects were archived
and read back successfully; the full source-bundle verification also passed.
