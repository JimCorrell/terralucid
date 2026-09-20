# Municipal corroboration and proposed corrections — 2026-09-20 UTC

## Result and review decision

Municipal publication chains and map context corroborate the Sweden/Alfred
jurisdiction diagnoses from [PR #6's investigation](../conflict-investigation/README.md).
The [structured report](report.json) now contains **proposed**, source-version-specific
corrections. They are stored as audit evidence in Supabase, not applied to source
records or canonical parcels.

| Proposed field change | Records | Evidence and limit |
| --- | ---: | --- |
| Sweden GEOCODE: 17290 → 17310 | 691 | Prior spatial/identifier agreement, plus town-linked municipal map context. |
| Alfred GEOCODE: 31030 → 31020 | 1,633 | Prior spatial agreement, plus town-published municipal map context; original invalid geometry excluded. |
| Alfred STATE_ID prefix: 31030_ → 31020_ | 1,595 | Above conditions plus a unique assessment candidate with equal nonblank map/lot and target code/key agreement. |

These are **2,324 jurisdiction proposals and 1,595 identifier proposals**, not
independent municipal verification of every record. The correction conclusions
remain **INFERRED**; their counts and checks are **DERIVED**. `VERIFIED` in the
[document review](document-review.json) refers narrowly to what a cited document
visibly says or depicts, not legal boundary accuracy or current parcel identity.

**Review requested by this PR:** assess the proposed changes, scope and exclusions.
A later explicit acceptance/projection step is required before operational use.
This implementation does not add an activation rule, rewrite source values, accept
assessment joins, or silently apply changes when new data arrives.

## Municipal corroboration and dates

- [Sweden's town website](https://swedenmaine.org/access-tax-records/) identifies its
  assessing provider and links to its [Sweden records/maps page](https://jeodonnell.com/cama/sweden/).
- [Alfred's town tax-map page](https://www.alfredme.gov/forms_and_documents/assessors_data/tax_maps.php)
  links its own maps and the [Alfred assessor page](https://jeodonnell.com/cama/alfred/).
  The town page declares a root `base` URL. Preserving and honoring that base resolves
  its relative links correctly.
- All eight selected PDFs were visually inspected, including complete pages and
  enlarged revision blocks. Seven had sparse/empty extractable text; text extraction
  or OCR was not used as parcel-matching evidence.

| Evidence | Printed date / observed source date | Meaning |
| --- | --- | --- |
| Captured Sweden GIS, 691 rows | FMUPDAT `4/1/2011` | Retained source field; no claim of current data. |
| Captured Alfred GIS, 1,634 rows | FMUPDAT `2013` | Year precision only. |
| Alfred town Index, map 4, map 10 ([source 1](https://www.alfredme.gov/document_center/assessors_data/Index.pdf?t=202608121313370), [source 2](https://www.alfredme.gov/document_center/assessors_data/TAX%20MAPS%202026%208.pdf?t=202608121318330), [source 3](https://www.alfredme.gov/document_center/assessors_data/TAX%20MAPS%202026%2014.pdf?t=202608121321210)) | Revised April 1, 2026 | Explicit printed revision on each reviewed sheet. |
| Provider file `Alfred 2025 Index.pdf` ([source 1](https://jeo-cama-files.s3.amazonaws.com/alfred/Alfred%202025%20Index.pdf)) | Revised April 1, 2024 | Filename year and printed revision differ. |
| Provider file `Sweden 2025 Overall.pdf` ([source 1](https://jeo-cama-files.s3.amazonaws.com/sweden/Sweden%202025%20Overall.pdf)) | Revised April 2021 | Month precision; no invented day. |
| Sweden Index, R-1 and U-8 ([source 1](https://jeo-cama-files.s3.amazonaws.com/sweden/Sweden%202025%20Index.pdf), [source 2](https://jeo-cama-files.s3.amazonaws.com/sweden/Sweden%202025%20R01.pdf), [source 3](https://jeo-cama-files.s3.amazonaws.com/sweden/Sweden%202025%20U08.pdf)) | Publisher/base label 1972; current revision unknown | Neither that label nor filename 2025 proves current parcel currency. |

The town-linked assessor may share data lineage with state GIS. These maps are
additional municipal context, not independent surveys. **TL-F-0024** now tracks
freshness and snapshot applicability separately from identifier correctness.

## Exceptions remain explicit

There are **119 distinct records with holds**:

| Hold | Records | Effect |
| --- | ---: | --- |
| Sweden has no exact assessment candidate | 75 | Jurisdiction proposal retained; assessment identity unresolved. |
| Sweden shares an assessment candidate across geometries | 5 | Jurisdiction proposal retained; no one-to-one identity or merge inferred. |
| Alfred has no unique prefix-trial candidate | 38 | Jurisdiction proposal retained; STATE_ID change withheld. |
| Alfred original GeoJSON is invalid | 1 | Both field proposals withheld pending geometry review. |

The 1,596 Alfred trial matches from PR #6 include the original invalid-geometry
record; excluding it leaves 1,595 identifier proposals. The 119 holds do not mean
119 records are excluded from all jurisdiction proposals.

Sweden R-1 labels lot 24, while U-8 visibly labels both 18 and 18A. These observations
do not establish why three GIS records share R01-24-0 or two share U08-18-A.
Those relationships remain open under TL-F-0010. This pass does not resolve all
38 Alfred or 75 Sweden unmatched cases.

## Alfred geometry: format interpretation, not silent repair

For Alfred OBJECTID **439584** (`31030_4-25`), the original and freshly requested
GeoJSON have the same geometry and are invalid because of nested shells. A native
ArcGIS JSON request for the same record shows:

- Two clockwise exterior rings and one counterclockwise interior ring.
- The interior ring exactly matches the geometry of OBJECTID **439585**, map/lot
  `4-25-2`.
- The municipal map 4 depicts an inset lot 25-2 inside lot 25.

[Esri's geometry specification](https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects/)
distinguishes exterior and hole rings by winding direction. The GeoJSON output
instead represents the interior ring as another filled component. Explicitly
interpreting the native ring roles produces a valid two-part geometry with one
hole and **zero area overlap** with the inset lot.

The report stores this **proposed alternate decoding**, its complete derived
GeoJSON, exact native/GeoJSON responses and method. Output ring winding follows
GeoJSON convention. No coordinates are snapped, generalized or repaired; no
`make_valid` operation is used. Unsupported or ambiguous rings fail rather than
being guessed. The original invalid geometry remains preserved and excluded from
the correction proposals. Other invalid geometries require separate checks; this
single case does not prove a service-wide export defect or legal boundary accuracy.

## Proposal identity and storage

Each proposed row records:

- Source snapshot checksum, source URL, OBJECTID, GlobalID and full selected-feature
  checksum, including geometry and raw attributes.
- Raw and proposed field values, original source-date value, evidence references,
  candidate target checksum/version where applicable, and remaining holds.
- `status=proposed`, `evidence_state=INFERRED` and a deterministic proposal ID.

A changed source feature or snapshot fails the proposal guard. No proposal is a
rule that can be applied to every record carrying the same GEOCODE. Assessment
targets remain candidates, and there is no canonical parcel merge.

The private `ingest.audit_result.document` stores the report and its
`crosswalk.proposals`, `crosswalk.exceptions`, `document_review` and
`geometry_format_evidence` sections. Original PDFs, web pages, format responses,
method and review artifacts are retained in the private checksum-addressed archive.
No new schema or migration is required.

## Reproduce and review

This repository is public. Captured documents and web pages remain in the private
Supabase archive; the committed retrieval logs contain their URLs, timestamps and
checksums. After downloading the private archive, restore the exact evidence into
ignored local paths before running the calculation:

```sh
npx --yes supabase@2.117.0 storage cp --experimental --linked --recursive --jobs 4 ss:///terralucid-source-snapshots/sha256 .local/municipal-download/sha256
python3 scripts/restore_private_evidence.py --audit research/municipal-corroboration --download .local/municipal-download
```

Restoration verifies every checksum and refuses to overwrite differing evidence.
It makes no web requests and avoids treating a changed live PDF as the old snapshot.

```sh
.local/conflict-venv/bin/python -m pip install -r research/municipal-corroboration/requirements.txt
.local/conflict-venv/bin/python -m unittest discover -s tests
.local/conflict-venv/bin/python scripts/prepare_municipal_crosswalk.py --output /tmp/municipal-report.json --prepare .local/new-municipal-load
```

Create an isolated environment first if needed. The calculation validates captured
checksums, municipal publication links, PDF signatures, visual-review references,
prior report methods/inputs, and native-vs-GeoJSON record/geometry consistency.
All **26 tests pass**, including hole preservation, rejection of unsupported rings,
changed-source guards, missing/multiple assessment candidates and all captured
proposal/exception counts. Archive restoration checks reject corrupt data and preserve existing files. The captured-fixture test is skipped until private evidence is restored; the complete verification reported here includes that test.

Use the existing [archive verification and atomic load workflow](../maine-ingestion/README.md)
for the prepared audit. For finding reviews, read current administrative queue rows
for TL-F-0002, 0003, 0010, 0022, 0023 and 0024 into the CLI JSON `rows` format, then:

```sh
python3 scripts/prepare_municipal_reviews.py --current .local/current-findings.json --output .local/municipal-reviews.sql
```

Review the prepared SQL; archive `reviews.json` and `new-findings.json` by checksum
before applying it. The report must already be loaded. Existing reviews require
current event tokens. New finding TL-F-0024 rejects a conflicting existing definition.
Replaying the same prepared review does not duplicate events or evidence.

## Deployment verification

Stored in Supabase project `yytsjlmbyqhcqfalbjca` on 2026-09-20 UTC. All **44**
expected archive objects were downloaded and verified before database loading.
Report SHA-256:
`6e08cd827867fbf816d94c82bd22b44d6889caf8936726f144bd00307de52e8f`.

Live checks confirmed three audit reports, five registry versions and 525 response
observations. The register contains 41 findings, 54 history events and 3,367 evidence
occurrences. Five existing findings remain in progress; TL-F-0024 is open. Every
mapping row remains `proposed`. All 2,058 original source records and 737 candidate
links remain intact. Staging RLS, denied client access and private archive storage
were verified.

## Next step

After proposal review, implement an explicit accepted correction layer that retains
raw values, gates by source version/checksum, and carries holds into downstream
analysis. Separately review native ring decoding for ingestion and seek appropriately
dated source data. Code normalization alone does not establish current parcel identity.
