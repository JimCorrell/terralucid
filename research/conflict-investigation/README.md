# Code/name conflict investigation — 2026-09-20 UTC

**Result:** the evidence supports source coding defects for Sweden and Alfred,
plus smaller name-quality issues. These diagnoses are **INFERRED** from the
**DERIVED** comparisons below. No source field, canonical parcel assignment or
assessment link has been corrected. Findings remain `in_progress` with evidence
and specific next actions in Supabase.

## What changed in our understanding

| Finding | Evidence | Interpretation / next action |
| --- | --- | --- |
| TL-F-0002: Sweden | All 691 valid geometry interior points fall in civil code **17310**, and all STATE_ID prefixes are 17310. At least 99.995% of each polygon's area overlaps Sweden. The raw geometry GEOCODE is **17290**, the reference code for Stow. | Strong support for a geometry GEOCODE defect. Corroborate with municipal/publisher evidence before accepting a versioned jurisdiction crosswalk. |
| TL-F-0003: Alfred | All 1,633 valid geometry interior points fall in civil code **31020**, with at least 99.7371% area overlap. One invalid geometry is excluded. All 1,634 raw codes and identifier prefixes are **31030**, the reference code for Arundel. | Strong support for defects in both GEOCODE and the identifier prefix. The town name is consistent with the mapped location. |
| TL-F-0004: smaller name differences | All 267 valid geometries agree with the reported code; two additional Kingsbury geometries are invalid. | Plantation abbreviations, three East Millinocket spelling/punctuation variants, two blank names and one `UNK` name are candidates for explicit name-normalization rules. No fuzzy matching or name rewrite was applied. |

These are comparisons between dated state-published layers, **not independent legal
boundary confirmation**. An interior point falling inside a civil polygon does not
mean the entire assessment polygon is inside it. Only 623 Sweden and 1,528 Alfred
polygons are fully covered by their respective civil reference unions; small
boundary differences remain explicit. Invalid geometry is never silently repaired.

## Alfred: test the prefix hypothesis, not a new production join

All 1,634 raw Alfred identifiers have **zero exact assessment matches** in the
complete captured identifier scope. Replacing only `31030_` with `31020_` in a
separate diagnostic value gives:

- **1,596** geometries with one candidate each, reaching 1,596 distinct assessment
  records. Every candidate also has an equal, nonblank `MAP_BK_LOT`.
- **38** geometries still unmatched, with all raw keys retained in the report.
- **No** raw Alfred key shared with the 1,998 captured Arundel geometry identifiers.

The negative collision result is scoped to these snapshots. It does not establish
that geographic-code prefixes are safe global identifiers. Prefix substitution is
a hypothesis, not an accepted source correction or legal parcel crosswalk.

The 38 unmatched rows include a repeated `31030_10-CEM` key and other labels such
as `UNK`; their labels alone do not establish exemptions, ownership or land use.
Municipal map/lot evidence and source dates are the next checks.

## Sweden: code consistency does not solve multiplicity

- 616 geometry rows have one exact assessment candidate; all candidates report
  code 17310. This explains the 616 raw code-disagreement flags from PR #5 as a
  likely geometry coding defect.
- Those 616 links reach **613 distinct assessment records**. Three geometries share
  `17310_R01-24-0`; two share `17310_U08-18-A`. A single candidate per geometry is
  not a global one-to-one join.
- **75** geometries have no exact candidate. Repeated keys include `ISLAND`,
  `CEMETERY`, `R06-CEM` and `R08-CEM`. Their actual meaning remains unverified.
- Across all 691 geometries there are 664 distinct raw keys, with six repeated-key
  groups. Repeated-key and unmatched lists are preserved in full.

## Invalid geometries and boundary dependence

The three invalid geometries in this investigation are Alfred OBJECTID **439584**
and Kingsbury OBJECTIDs **1073761 / 1073853**. Their source geometries and validity
reasons remain in the evidence; none receives a derived spatial assignment. The
Kingsbury defects were already observed in PR #5. The earlier UT geometry defect
is outside this investigation's scope and remains tracked.

## Evidence and method

The two captures retain **112 exact responses** with URLs, retrieval timestamps,
checksums, selected fields, source metadata and completeness checks:

- [Spatial plan](plan.json): all ten conflict groups from the earlier coverage audit,
  totaling 2,594 organized geometries, plus 44 civil features under eight candidate
  jurisdiction codes. The prior group counts reconcile exactly.
- [Relationship plan](relationships-plan.json): 4,425 assessment records selected
  by GEOCODE or identifier prefix, and 1,998 Arundel geometry identifier records.
  No owner names or addresses were requested.
- [Report](report.json): per-record spatial evidence, exact/trial candidate IDs,
  unmatched/repeated keys, calculation versions and complete request provenance.
- [Review plan](reviews.json): eight findings updated with scoped evidence and next actions.

Both captures reconcile start counts, unique object IDs, every requested page,
end membership and available metadata. All 44 civil features are valid. Their
geometries are grouped by raw code and unioned for calculation. Valid assessment
polygons are compared using interior-point coverage, whole-polygon coverage and
area-intersection fractions in **EPSG:26919**. No geometry repair, snapping or
assignment threshold is used. Polygon slivers are reported rather than rounded
away into a containment claim.

The assessment query includes both geographic codes and every possible exact
prefix match for the retained Sweden/Alfred keys. The analysis refuses keys outside
that captured scope. A prefix trial changes only the diagnostic prefix; raw values
remain unchanged. Matching is exact and preserves zero/one/multiple candidates.

Reproducibility is scoped to these dated snapshots. Capture controls do not create
an atomic cross-service snapshot or establish legal-effective boundary dates.
The [prior reference audit](../maine-coverage/README.md) remains unchanged.

## Reproduce and review

Use an isolated Python environment and the pinned calculation dependencies:

```sh
python3 -m venv .local/conflict-venv
.local/conflict-venv/bin/python -m pip install -r research/conflict-investigation/requirements.txt
.local/conflict-venv/bin/python -m unittest discover -s tests
.local/conflict-venv/bin/python scripts/investigate_source_conflicts.py --output /tmp/conflict-report.json --prepare .local/new-conflict-load
```

The preparer validates captured checksums/membership and assembles the existing
private staging format. It archives the report, calculation method, dependency
versions, capture manifests and reference inputs. Upload its `objects/sha256` to
the existing private bucket root, download into a fresh directory, verify and apply
with `scripts/apply_prepared_load.py` as described in the
[bounded ingestion instructions](../maine-ingestion/README.md). No migration is needed.

For findings updates, read the current eight findings using the administrative
queue query in [the findings workflow](../../docs/findings-register.md), saving the
CLI JSON output with its `rows` array. Then prepare a reviewable transaction:

```sh
python3 scripts/prepare_conflict_reviews.py --current .local/current-findings.json --output .local/conflict-reviews.sql
```

Review the SQL and upload the exact `reviews.json` artifact by checksum before
applying it. The report must already exist in `ingest.audit_result`. The update adds
one report occurrence per finding and calls the existing append-only review
function. Expected event IDs prevent stale reviews; replaying the same transaction
adds no duplicate history. It changes no original finding definitions or source rows.

Eighteen tests pass with the pinned dependencies. New cases cover false containment
from an interior point, invalid geometry exclusion, multiple prefix-trial candidates,
source-value preservation and rejection of keys outside the captured match scope.

## Deployment verification

Applied to Supabase project `yytsjlmbyqhcqfalbjca` on 2026-09-20 UTC. All **121**
expected archive objects were downloaded and checksum-verified before loading.
The report is stored in `ingest.audit_result` under SHA-256
`1b811f9eab6000727b887986e27acbbb989a622d24f7439b031f033c385398bb`.

Live checks confirmed:

- Two audit reports, four registry versions and 510 response observations.
- All 2,058 existing source records and 737 assessment candidate links preserved.
- Forty findings with 48 history events and 3,361 evidence occurrences: eight new
  reviews and eight report occurrences; those eight findings are `in_progress`.
- Staging RLS enabled, client access denied and the archive bucket still private.

The new captures are audit evidence, not additional canonical parcel rows. Current
status lives in Supabase and can change after this dated verification.

## Next investigation

1. Corroborate the Sweden/Alfred diagnosis against municipal or publisher evidence
   and propose a source/version-specific correction crosswalk for explicit review.
2. Reconcile the 38 remaining Alfred prefix trials and 75 Sweden unmatched records.
3. Explain shared geometry/assessment keys and review the three invalid geometries.

These steps do not require a user interface or property ranking. The authoritative
follow-up queue remains in Supabase; this report records one investigation version.
