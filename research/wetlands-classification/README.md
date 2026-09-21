# TL-F-0027: eight NWI classification conflicts

**Resolution:** the exact eight-record interpretation hold is resolved. Use the
complete reference-matched definitions for PUBFh and PUBFx. Original service rows
remain preserved. The publisher's duplicate lookup rows still exist; this review
does not claim the upstream defect was repaired or explain its origin.

## What the evidence establishes

| Raw code | Reviewed meaning | Matching service lookup | Incomplete alternative |
|---|---|---:|---:|
| PUBFh | Palustrine, unconsolidated bottom, semipermanently flooded, diked/impounded | 5448 | 6186 |
| PUBFx | Palustrine, unconsolidated bottom, semipermanently flooded, excavated | 5453 | 6187 |

The [official classification page](https://www.fws.gov/program/national-wetlands-inventory/classification-codes)
links the code-definition package and interpreter. Its **October 2024 CSV** has one
row for each code. Every reference field matches the complete service variant;
only empty CSV fields are normalized to service nulls. The competing variants have
eight missing water-regime/modifier fields, not alternative populated definitions.
The **October 2023 interpreter** separately corroborates the five component labels
P, UB, F, h and x. We read its literal dictionaries without executing downloaded code.

The CSV metadata specifies normalized NWI Version 2.0 data, published May 2016 or
later. The prior capture's project metadata identifies NWI Version 2 stream
supplementation. This concerns code compatibility, not the age of the imagery.
The **May 1983** imagery qualification remains in force.

A fresh service request returns the same sixteen variants for the eight source
records; native core attributes, coordinates and joined variants match the prior
capture exactly. This allows a narrowly versioned interpretation rather than a
correction to the wetland code or geometry itself.

## Maine package comparison

The original **437,448,614-byte** Maine GeoPackage ZIP is archived intact in eleven
ordered checksum-addressed parts. Its extracted database has 587,644 wetland rows.
This is source archiving and an eight-record comparison, **not statewide ingestion**.
The source ZIP remains unmodified; extraction uses a separate working copy and
read-only database access.

| Service OBJECTID | Code | Nearby package OBJECTID |
|---|---|---:|
| 2274990 | PUBFh | 126421 |
| 2275013 | PUBFh | 126423 |
| 2275026 | PUBFh | 126424 |
| 2275028 | PUBFh | 126425 |
| 2275040 | PUBFh | 126428 |
| 2279189 | PUBFx | 126505 |
| 2279269 | PUBFx | 126508 |
| 2279274 | PUBFx | 126509 |

After transforming the service geometry into the package's declared NAD83 Albers
CRS, each has one candidate within a 2-metre Hausdorff-distance gate, with the same
code. Distances are about 1.024–1.026 metres. The selected operation reports
4-metre accuracy; the gate is an investigative parameter, not an accuracy guarantee.
All spatial candidates and comparison metrics are preserved, not just the selected
nearby candidate. Package NWI_ID and service GlobalID differ. Thus the counterparts
remain **INFERRED** and their boundaries are not claimed identical. No general ID
crosswalk, projection correction or geometry replacement is accepted.

The package corroborates the codes; the official reference table and interpreter
establish their meaning. Neither establishes present-day site conditions or legal
wetland boundaries.

## Versioned downstream use

The report's `records` carry the source OBJECTID, GlobalID, native-core hash,
original geometry hash, selected lookup hash and reference-row hash. `reference_rows`
contains the reviewed code definitions. Use these only with:

1. Prior audit `e1449e8384d5d712dfdae9df26814330d1b9f7dc31ae82fc8765bce565b61906`.
2. This review audit and its TL-F-0027 resolution event.
3. Matching native-core, lookup and reference versions.

Preserve DERIVED evidence and the unresolved source/ground/legal qualifications.
New snapshots need review; lookup OBJECTID or code alone does not transfer this
resolution. Later contradictory evidence should reopen the finding. A raw variant
remains available for audit, but downstream interpretation should use the reviewed
reference match for these exact records. Do not count joined rows as separate
wetlands.

This small review is stored in `ingest.audit_result.document`, linked through
finding history. It does not insert wetlands into the municipal correction view,
introduce a generic correction schema, or recompute any parcel screening. Future
wetlands consumers must implement the version checks before using these values.

## Findings and remaining work

- **TL-F-0027: resolved**, limited to interpretation of the eight reviewed records.
  The duplicate service-join behavior remains a capture hazard; preserve/reconcile
  it on refresh rather than assuming the publisher repaired it.
- **TL-F-0117: in progress.** Package/service identity, projection differences,
  package-wide coverage and refresh behavior, old imagery and applicability remain.
- **TL-F-0028: unchanged/open.** Availability-layer native ring structure needs its
  own investigation; no conclusion about that geometry is introduced here.

## Reproduction

Start with `review.json` and the derived `report.json`. Request URLs, retrieval times,
response hashes, source ZIP version headers and multipart offsets are preserved in
the capture logs and `package-capture.json`. Original references remain private.

Restore response bytes using `report.json#/evidence`, and dependencies using
`report.json#/inputs`, from the private `terralucid-source-snapshots` bucket. Concatenate
package parts in offset order and verify the original ZIP hash before extraction:
`ae1332336dbe5b6d255c29d75134c2959370ce9aa43c94fc2abb413475f1dcd1`.
The report also records the extracted GeoPackage member hash and runtime.

```sh
.local/conflict-venv/bin/python scripts/investigate_wetlands_classification.py
.local/conflict-venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.local/conflict-venv/bin/python scripts/investigate_wetlands_classification.py \
  --prepare .local/wetlands-classification-load \
  --current .local/wetlands-conflict-current.json
.local/conflict-venv/bin/python scripts/investigate_wetlands_classification.py \
  --verify-download .local/wetlands-classification-download \
  --prepared .local/wetlands-classification-load
```

Fresh preparation requires current review tokens for TL-F-0027 and TL-F-0117.
Upload, independently download and verify all manifest objects and the reconstructed
ZIP hash before applying the atomic `load.sql`. An identical SQL replay is safe;
later reviews need fresh tokens. Reproduce from archived bytes; a live recapture
is a different source version. `collect_maine_wetlands_package.py` refuses to
replace an existing capture.

## Applied checkpoint

Audit `a1fd940a039662c703ec254963e70cd245f0632c970a62748591e5136f261c12`
and registry `560c23e6ba22cc0e7444fb15774c65a6fe2dc19d2cf7f16a5f011827bcec10e9`
are loaded in Supabase after **33 archive objects** passed independent download/hash
verification, including reconstruction of the complete 437,448,614-byte source ZIP.
The atomic load recorded four ordinary response observations, one audit and two
append-only finding reviews/occurrences; the ZIP is additional audit-linked evidence.

Readback confirms TL-F-0027 **resolved/medium**, two occurrences, under resolution
event `560e8844f3aef6c1b716524080d285790510924422df5db0ba3ae94de7019f48`.
TL-F-0117 remains **in_progress/medium**, three occurrences. TL-F-0028 remains
**open/medium**, with its prior event unchanged. All have `needs_revisit=false`
after these reviews; that flag does not remove unresolved qualifications.

The bucket remains private. Complete before/after fingerprints of accepted geometry,
geometry events, zoning screenings and screening revisions match. The report
reproduces byte-for-byte and all **68 tests** pass. No schema change was made.
