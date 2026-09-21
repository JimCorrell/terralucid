# Osborn wetlands source qualification

This is a bounded NWI service capture for source qualification. Original responses
and the derived audit are staged privately in Supabase; no statewide Maine package,
canonical parcel layer, legal wetland boundary, or parcel screening is introduced.

## Findings

| Check | Result |
|---|---|
| Search scope | Envelope of the previously captured FEMA Osborn jurisdiction, CID 230595 |
| Identifier response | 677 entries, **669 distinct source IDs**; service count 669 |
| Native inventory geometry | All 669 decode as valid without repair |
| Intersecting study boundary | 499 features with positive area |
| Mapped inventory union in scope | About 16.03 km², including deepwater habitats; not regulated wetland acreage |
| Candidate GLOBALID | Present and unique for 669 core records; cross-release persistence unknown |
| Imagery-source footprints | Four valid polygons cover the study boundary |
| Imagery metadata | **May 1983**, color infrared, 1:58,000; later NHD stream supplementation noted |
| National availability geometry | OBJECTID 3, Digital, fails strict ring decoding; excluded from coverage overlays |

The four source projects are Rocky Pond, Molasses Pond, Eastbrook and Amherst.
Their comments identify NWI Version 2 supplementation from NHD 931v220 or 931v210.
Those strings do not supply an acquisition date for the added streams. The
[state download page](https://www.fws.gov/program/national-wetlands-inventory/download-state-wetlands-data)
labels its release May 2026; release, retrieval and image dates remain separate.
The linked Maine GeoPackage and File Geodatabase have **not** been downloaded or
reconciled against this service snapshot. Statewide ingestion remains open.

### Repeated IDs are an actual lookup problem

Eight IDs have two joined `NWI_Wetland_Codes` rows with differing definitions:
2274990, 2275013, 2275026, 2275028, 2275040, 2279189, 2279269 and 2279274.
The affected raw codes are retained in `report.json#/joined_code_conflicts`.
For example, code PUBFh has one lookup describing water regime and modification,
and another with those values missing. No lookup variant is selected as correct.

Every variant has identical `Wetlands.*` core attributes and native geometry for
its ID. The derived profile groups only those identical core records and preserves
the conflicting lookup values. Exact responses retain all joined rows. The initial
ID-driven page plan includes the repeats; one ID straddles pages, yielding 679
captured rows, 677 distinct joined rows and 669 distinct core records. Membership,
page contents, distinct count and unchanged core values are explicitly checked.
A change in core geometry or attributes stops the audit.

### Coverage and regulatory limits

The inventory represents mapped wetlands **and deepwater habitats**. Source-project
coverage establishes where mapping lineage is described, not exhaustive detection.
The invalid national availability polygon is retained with its failure reason;
its returned Digital attribute does not substitute for a successful coverage overlay.
Esri permits some vertex-touching ring representations; a strict GEOS failure alone
does not establish a wrongly mapped boundary. That distinction needs investigation.

[USFWS limitations](https://www.fws.gov/node/264582) and
[user caution](https://www.fws.gov/node/264583) distinguish biological inventory
mapping from regulatory boundaries. Unmapped space cannot establish wetland
absence. Image interpretation may differ from current site conditions. Cowardin
codes are not automatically LUPC P-WL designations, DEP/NRPA or federal jurisdiction,
septic suitability, or buildability. Field delineation and applicable agency evidence
remain independent due-diligence requirements. Existing LUPC findings remain open.

## Method and evidence

- `probes.json`: official source discovery; the DEP candidate was a parcel product,
  so it is not used as the wetland boundary source.
- `qualification-probes.json`: limitations, service listings and initial IDs.
- `feature-probes.json`: 50-ID requests retaining full native EPSG:3857 geometry
  and joined attributes; service limit is 1,000. Count captured after feature pages.
- `coverage-probes.json` and `followup-probes.json`: imagery/availability features,
  counts and IDs, publisher metadata, native-format documentation, final checks.
- `registry.json`, capture logs, `review.json`, `findings-plan.json`, and `report.json`
  pin provenance, interpretation, findings and method checksums.

The [method](../../scripts/investigate_osborn_wetlands.py) checks source hashes,
HTTP/API outcomes, transfer flags, IDs, counts and start/end metadata. Esri clockwise
shells and counterclockwise holes are decoded only when rings are simple, closed,
and unambiguously associated. No coordinate movement, snapping, repair or geometry
correction is performed. Ambiguous rings are held. Areas use EPSG:26919; the exact
runtime and selected PROJ operations, including reported accuracy, are recorded.
The FEMA jurisdiction is a study boundary, not a surveyed/legal parcel boundary.
All intersection results depend on that exact version.

Start/end membership and metadata agree. These services provide no captured
editingInfo token; same-ID edits during capture are not ruled out. The generic
collector labels successful documents `NON_JSON_RESPONSE`; the investigation
explicitly parses and validates JSON rather than treating that label as validation.

## Tracked deficiencies

- **TL-F-0117 — in progress:** bounded source qualification, with imagery age,
  package reconciliation, wider coverage, identity persistence and legal limits open.
- **TL-F-0027 — open:** eight conflicting classification lookups; preserve variants
  and compare the official classification reference and Maine package.
- **TL-F-0028 — open:** native national availability ring defect; investigate
  representation and alternative official evidence before using that overlay.

These are append-only finding events and evidence occurrences. No previously
accepted correction or zoning screening is changed.

## Reproduction and private staging

Restore raw responses from the private `terralucid-source-snapshots` bucket using
the SHA-256 keys and paths in `report.json#/evidence`. Restore its `inputs` similarly,
including the prior FEMA jurisdiction and audit. Do not recapture live sources to
reproduce this dated snapshot; a new capture requires a new audit.

```sh
.local/conflict-venv/bin/python scripts/investigate_osborn_wetlands.py
.local/conflict-venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.local/conflict-venv/bin/python scripts/investigate_osborn_wetlands.py \
  --prepare .local/wetlands-load --current .local/wetlands-current-final.json
.local/conflict-venv/bin/python scripts/investigate_osborn_wetlands.py \
  --verify-download .local/wetlands-download --prepared .local/wetlands-load
```

Preparation needs fresh `finding_id`/`event_id` rows for TL-F-0117 and an absence
check for new IDs TL-F-0027/0028. Upload and independently download/hash-verify all
manifest objects before applying the atomic `load.sql`. Replay the same SQL safely;
new preparation requires rereading current finding state. Private source-response
staging retains original features inside responses; this is not a new queryable
wetlands feature table. Bulk feature storage/refresh is a later ingestion step.

## Next step

Reconcile the lookup conflict against the official code reference and Maine
package, then investigate the availability ring. Keep old-image uncertainty visible
when expanding coverage or designing a bounded screening layer.

## Applied checkpoint

Audit `e1449e8384d5d712dfdae9df26814330d1b9f7dc31ae82fc8765bce565b61906`
and registry `a0953efb0d78ba3308ad1f10f7142345f20fcf2df6dd6ce82c7992d20441c154`
are loaded in Supabase after **57 objects** passed independent download/hash
verification. The atomic transaction recorded 44 response observations, one audit,
two new finding definitions and three finding reviews/occurrences.

Readback confirms TL-F-0117 **in_progress/medium**, two occurrences; TL-F-0027 and
TL-F-0028 **open/medium**, one occurrence each. All have `needs_revisit=false` after
this review; that flag does not mean resolved. The storage bucket remains private.
Before/after fingerprints of accepted geometry, geometry events, zoning screenings
and screening revisions match exactly. The report reproduces byte-for-byte and
all **62 tests** pass. No schema change was made.
