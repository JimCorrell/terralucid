# Bounded wetlands displacement and package imagery lineage

## Findings

The approximately one-metre service/package difference is **numerically reconciled
for all 669 reviewed pairs** by explicitly applying ESRI:108190
(`WGS_1984_(ITRF00)_To_NAD_1983`) between Web Mercator inverse projection and
NAD83 Albers projection. No coordinates were fitted, snapped or translated to force
agreement. All original source bytes, geometries and stored comparisons remain intact.

| Datum-operation control | Hausdorff distance to native package geometry |
|---|---|
| Automatic comparison / inverse EPSG:1188 | 1.023928–1.026454 m |
| Inverse EPSG:1515 | 0.013475–0.013559 m |
| Forward ESRI:108190 | 0.0000285–0.0000502 m (0.029–0.050 mm) |

Four live controls—service IDs 1886218, 2274990, 2320442 and 9415660—retain exactly
the archived native core attributes and rings. They include an earlier classification
conflict and the two largest vertex-count records in the bounded service load.
The complete default Albers response is identical to explicit `datumTransformation=108190`.
Local explicit 108190 results match the service's explicit results within
0.000000028 m. The 1188 and 1515 alternatives remain distinguishable; all control
metrics are retained rather than reduced to a pass/fail statement.

This supports an **operation-choice explanation** for the bounded displacement.
Captured metadata exposes transformation support but does not declare the selected
default operation. Numerical equivalence does not prove the publisher's hidden
production history, absolute positional accuracy, survey accuracy or legal validity.
Sub-millimetre closure is agreement between these representations, not ground accuracy.

## Package imagery/project coverage

The native package project layer supplies four footprints covering every loaded
package feature and the entire pinned FEMA Osborn study boundary, with zero computed
uncovered area. These are lineage footprints, not proof of exhaustive wetland mapping.

| Package project | Image date | Scale | Source | Supplement |
|---|---|---|---|---|
| Rocky Pond | May 1983 | 1:58,000 | CIR | NHD 931v220 |
| Molasses Pond | May 1983 | 1:58,000 | CIR | NHD 931v220 |
| Eastbrook | May 1983 | 1:58,000 | CIR | NHD 931v220 |
| Amherst | May 1983 | 1:58,000 | CIR | NHD 931v210; source comment also says `COMP` |

All nine compared lineage attributes agree with the corresponding archived service
project records. Explicit 108190 also reconciles their footprint geometry to within
0.0000445 m. **638 features overlap one project, 29 overlap two, and 2 overlap three.**
Per-feature positive-area associations, boundary touches and uncovered area remain
in private detailed evidence. No single project is arbitrarily selected for features
that cross footprints. These are spatial associations, not direct provenance keys.

This establishes package-specific spatial lineage for the bounded load. It does
**not** establish newer imagery: the May 1983 qualification persists. NHD version
strings do not identify acquisition dates for the supplemental stream features.
Release/retrieval dates remain separate from source imagery dates.

## Downstream implications and findings

TL-F-0117 remains **in progress**, with the bounded displacement numerically
explained and package lineage coverage qualified. Remaining work includes statewide
geometry/project coverage, cross-release identity and refresh behavior, newer imagery
or field evidence, and legal applicability. No additional finding ID is needed for
a newly observed conflict: this investigation narrows the existing deficiency.

No accepted source, geometry, candidate identity, preference or stored metric is
changed. Candidate identities remain INFERRED. Earlier one-metre comparison metrics
and unresolved-projection wording are retained as historical evidence; consult this
later audit to interpret them. Any future precision-sensitive comparison must pin
its qualified operation and source versions. This is not a global CRS policy or an
instruction to replace source geometry. Existing review-dependency flags stay intact.

## Method and controls

The method verifies the native package ZIP/GeoPackage, both bounded load reports,
original service pages, prior project footprints and newly captured control bytes.
Service metadata is equal at capture start/end. Each query is explicitly checked for
API errors, transfer truncation, feature membership, CRS and native-core drift.
The generic capture log's `NON_JSON_RESPONSE` label is not used as JSON validation.

[Esri's query documentation](https://developers.arcgis.com/rest/services-reference/enterprise/query-map-service-layer/)
defines the explicit datum-transformation parameter. [PROJ's operation-selection
documentation](https://proj.org/en/stable/operations/operations_computation.html)
describes how automatic operation choice is determined; automatic selection must
not be assumed equivalent to a particular service output. Both pages are archived.
The exact runtime, PROJ database checksum, operation pipelines/directions and
selected study-boundary conversion are recorded. Authority transformations use
latitude/longitude axes; conversion wrappers explicitly handle axis order.

Package project geometry is read natively from the read-only working GeoPackage.
Coverage uses unions to avoid counting overlapping footprints twice, records all
positive-area project associations, and separates boundary-only touches. The study
boundary remains the exact archived FEMA jurisdiction, not a surveyed parcel.

`report.json` is the compact reviewable audit. Its `details` entry pins private
per-feature projection and lineage results. The inherited `package` metadata block
comes from the earlier eight-record classification audit; this investigation's
current scope is 669 pairs, four controls and four project footprints.

## Reproduction and staging

Restore every report `inputs` entry by its SHA-256 key and path. Restore `evidence`
responses to their recorded paths. Reconstruct `package.parts` in order and verify
the original ZIP and extracted working-copy hashes. Keep original sources unchanged.

```sh
.local/conflict-venv/bin/python scripts/investigate_wetlands_lineage.py
.local/conflict-venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.local/conflict-venv/bin/python scripts/investigate_wetlands_lineage.py \
  --prepare .local/wetlands-lineage-load --current .local/lineage-current.json
.local/conflict-venv/bin/python scripts/investigate_wetlands_lineage.py \
  --prepared .local/wetlands-lineage-load --verify-download .local/wetlands-lineage-download
```

Fresh preparation requires the current TL-F-0117 event. Independently download and
verify the manifest and reconstructed package before applying the atomic audit/review
transaction. An exact replay preserves later reviews. Live recapture is new evidence
and must pass source-drift checks; it does not overwrite the archived controls.

## Applied checkpoint

Audit `2cf24a3a651fd84b1fa5e42840083fcebc90d7629c9986a1bd67f06b0cd2458f`
is recorded in Supabase after **60 archive objects** passed independent download/
SHA-256 verification, including reconstruction of the original 437,448,614-byte
package ZIP. The transaction recorded ten source observations, the audit and one
append-only TL-F-0117 occurrence/review. No schema change was made.

The private per-feature evidence is 477,940 bytes, checksum
`cd2d28164a8f608227efe59f0429061d0ce9b839f9f91bf46fea9e20d6194147`.
The report and detail bytes reproduce exactly. **96 Python tests pass**, including
explicit operation direction/axis order, overlapping project footprints, empty
coverage and boundary-only touches.

TL-F-0117 remains **in_progress**, nine occurrences, under review event
`f1d101d4448daacb287ce7fcb00c03fcbb54ed26cdbd61943fd21f8f21438595`.
TL-F-0027/0028 resolution events are unchanged. Both 669-feature loads remain current
with zero stale dependencies. Before/after fingerprints match for package and
service batches/features, availability geometry/events/results, zoning geometry/
events/screenings/revisions and all other finding events. The bucket remains private.
