# Osborn service/package comparison

This investigation compares all 669 features from the accepted bounded service
load against the archived Maine wetlands GeoPackage. Both sources remain separate.
No identity crosswalk, geometry replacement, statewide feature load or parcel
screening is accepted by this investigation.

## Results and recommendation

| Check | Result |
|---|---|
| Service features compared | 669 |
| Bounding-box candidate pairs retained | 4,692 |
| Distinct package candidates inspected | 1,299; no geometry holds |
| Candidates at 1 metre | None for all 669 service records |
| Candidates at 2, 5 and 10 metres | Exactly one per service record at each gate |
| Code / wetland-type disagreements among those candidates | None |
| Package candidates shared by multiple service records | None |
| Reverse-scope package records | 669; same candidate IDs; no unmatched/multiple records |
| Primary full-shape Hausdorff distance | 1.0239277–1.0264538 metres |
| Geometrically equal primary pairs | None |

This is consistent one-to-one **spatial candidate agreement within this bounded
scope**, sensitive to the threshold between 1 and 2 metres. It supports proposing a
separate, versioned package load for these 669 records, with original identifiers
and geometries intact. Candidate links remain INFERRED. The consistent displacement
is measured; its cause is not established, and no translation/datum correction is
accepted. The selected transformation reports 4-metre accuracy, which is not a
per-feature accuracy guarantee or justification to treat boundaries as identical.

The comparison does **not** qualify all 587,644 package rows. Only 1,299 candidate
geometries were inspected. Package-wide geometry/project coverage, cross-release
identity, source refresh and legal applicability remain open. TL-F-0117 is the
continuing deficiency; there are no newly observed bounded unmatched/classification
conflicts needing separate finding IDs. TL-F-0027/0028 resolutions remain unchanged.

## Reproducible method

The method checks the exact source-load audit and reconstructs its feature inputs,
including all original joined variants and the eight reviewed classification
interpretations. It checks the original ZIP and extracted working-copy hashes,
opens SQLite read-only and verifies package row count and spatial-index membership.
Service geometry is transformed from EPSG:3857 into the package's declared NAD83
Albers CRS; the selected operation and its reported accuracy are retained.

For each full service polygon, all package bounding boxes intersecting its bounds
expanded by 10 metres are retained, without filtering by identifier or code.
Metrics include full-geometry discrete Hausdorff distance, intersection area,
overlap fractions, symmetric difference, signed area difference and code/type
agreement. When the difference in an extremal x/y coordinate already exceeds
10 metres, that lower bound proves exclusion at every tested gate; the candidate
and overlap metrics are retained while the expensive exact distance is skipped.
The GEOS Hausdorff calculation is vertex-based and not densified;
it is an investigative metric, not a guarantee about every boundary point.

The primary 2-metre gate preserves continuity with the previous eight-record
comparison. Results at 1, 5 and 10 metres reveal threshold sensitivity. Zero, one
and multiple candidates remain distinct. A sole candidate with different code/type
is a conflict, not discarded. No nearest-neighbor winner is selected. Package IDs
shared by multiple service candidates are listed separately. Geometry decode holds
remain visible and cannot count as zero-distance candidates.

The reverse coverage check selects package geometries intersecting the original
geographic search envelope, including touches, after densifying its edges every
0.001 degrees and projecting it. This is the search envelope, not the jurisdiction
polygon or a legal boundary. Package records with no 2-metre service candidate,
multiple candidates or geometry holds are retained. This reverse check does not
assert statewide completeness or exact equivalence of source query semantics.

Metrics are DERIVED; possible identity links are INFERRED. Identical codes and
close shapes alone do not establish persistent cross-release identity. The package
and service keep their original geometry and identifiers. Coordinate transformation
accuracy, source imagery age, inventory completeness and legal applicability remain
qualified. A package release date does not update the May 1983 image lineage.

## Evidence and reproduction

`report.json` contains summary/sensitivity results, exact hashes and method/runtime
details. Its `details` entry pins the privately archived `detailed-results.response`,
which retains all per-feature candidate metrics and reverse-scope records. It links the
existing accepted classification event and availability result without changing
them. Original evidence and ZIP parts remain in the private source archive. The
`package` metadata block is retained from the earlier classification audit, including
its historical eight-record scope description; this investigation’s current scope
and counts are in `parameters` and `summary`.

Restore `inputs` by SHA-256 key/path. Restore and concatenate `package.parts` in
recorded offset order; verify the full ZIP hash. Extract its GeoPackage into the
separate working path `research/wetlands-classification/package/maine.gpkg` and
verify the extracted hash. The method never edits either source.

```sh
.local/conflict-venv/bin/python scripts/compare_wetlands_package.py
.local/conflict-venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.local/conflict-venv/bin/python scripts/compare_wetlands_package.py \
  --prepare .local/package-comparison-final-load \
  --current .local/package-comparison-current.json
.local/conflict-venv/bin/python scripts/compare_wetlands_package.py \
  --prepared .local/package-comparison-final-load \
  --verify-download .local/package-comparison-download
```

Preparation requires the current TL-F-0117 review event. Independently download
and verify manifest objects and the reconstructed package before applying the
atomic audit/review transaction through `scripts/apply_prepared_load.py`. Exact
replays preserve later reviews. New captures require a new investigation. No
schema migration is needed for this audit and append-only findings update.

## Applied checkpoint

Audit `076cb7321ad0b8cad052a4bf51a18028413b88e788082ddbc347158919ec18ed`
is stored in Supabase after **39 archive objects** passed independent
download/checksum verification. The ordered package parts also reconstructed the
original **437,448,614-byte** ZIP hash. The detailed results object is
`07dd03febb6368257f3437b429bcad8b9b1a67e541ab98776614155ea5265585`
(6,728,474 bytes), retained privately rather than adding 129,000 lines of metrics
to the PR.

The transaction added the comparison audit and one append-only TL-F-0117
occurrence/review. It remains **in_progress**, with seven occurrences, under event
`5d66ad562d4db62a17cdbb8a03eb41d9d6be347ca88cd3b64a0ecc672f45bb3f`.
The existing TL-F-0027/0028 resolved events are unchanged. All 669 loaded service
features remain current, with no stale dependencies.

Before/after fingerprints match for wetlands batches/features, availability
geometry/events/results, zoning geometry/events/screenings/revisions and all
finding events outside TL-F-0117. The bucket remains private. There is no schema
migration or package feature ingestion in this change.

The report and detailed results reproduce byte-for-byte. **88 Python tests pass**,
including candidate ambiguity, classification disagreement, threshold sensitivity,
invalid geometry holds and proven-distant-candidate handling.
