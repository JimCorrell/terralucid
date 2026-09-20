# TL-F-0109: LUPC currency and omitted protections

**Disposition: in progress.** This investigation narrows the outstanding evidence
requirements for Osborn. It does not establish current legal zoning, complete
regulatory coverage or redistribution permission. Original sources, accepted
geometry and screening results remain unchanged.

## What the data establishes

The published MapServer and previously ingested offline FeatureServer each return
383 Osborn records. Each response reconciles against its separate ID query.
GlobalIDs match one-to-one; all common attributes except OBJECTID match. **All 383
OBJECTIDs differ between services.** Service identity must remain part of a source
record's identity. This observed GlobalID correspondence is not a universal key
policy. Area/length fields have different names and are excluded from the common
attribute comparison. Geometry equality was not tested in these attribute queries.

The offline attributes exactly match all eight pages of the original ingestion.
All PUBLISH/DRAW flags remain Yes and END_DATE is null. Captured metadata only
supplies Yes/No domains, with no verified legal-current meaning. Agreement between
services and unchanged attributes do not establish current legal applicability.

The [publisher page](https://www.maine.gov/dacf/lupc/plans_maps_data/digital_maps_data.html)
warns of digital/map lag and directs users to compare official maps. Its town
Update Date column reads `last_edited_date_text`. The hosted download endpoint
linked on that page returns HTTP 200 with **application error 499, Token Required**.
It is an access failure, not zero features. No access-control bypass was attempted.
Raw third-party documents remain private; free download wording does not settle
redistribution rights.

## Separate the dates

| Evidence | Observed date | Meaning/limit |
| --- | --- | --- |
| Osborn official map | Adopted 2005-08-03; effective 2005-08-18 | Initial map dates |
| Map amendment table | Latest entry 2024-08-01, ZP796 | Clerical correction to FEMA adoption text |
| Public town Update Date | 8/1/2024 | Display field, not a current-zone selection rule |
| Map AMEND_DATE field | 2005-08-18 | Does not encode the latest printed amendment; retain raw value |
| Service update table | 2026-09-15 | Service-wide label; not proof Osborn changed or every amendment is incorporated |
| Published Chapter 10 edition | 2026-04-06 | Rule edition; not the Osborn map's effective date |
| Osborn flood-adoption note | Hancock County FIS 2016-07-20 and accompanying FIRM | Requires panel/revision and adoption reconciliation |

The downloaded Osborn map is byte-identical to the earlier ingestion. Its signed
certification block and printed amendments were visually inspected. Neither
unchanged bytes nor the latest visible amendment proves no later amendments exist.
All raw millisecond dates and derived UTC values remain in the report/archive.

## Protections a polygon-only screen misses

The [Osborn map](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/osborn.pdf)
notes explicitly omit certain P-WL wetland/waterbody areas, P-SL2 along streams
through wetlands, and FEMA special flood hazard areas adopted as P-FP. It also
identifies dependence on water locations on the ground.

The publisher's [Chapter 10 edition](https://www.maine.gov/dacf/lupc/laws_rules/rule_chapters/Ch10_ver2026-04-06.pdf)
was reviewed at PDF pages 1, 14–15, 133, 170 and 178–179 (printed pages 6–7, 125,
162 and 170–171 for substantive sections):

- **10.04–10.05:** official maps/amendments and boundary interpretation are separate
  from GIS display. [12 M.R.S. 685-A(2)](https://www.legislature.maine.gov/statutes/12/title12sec685-A.html)
  addresses physical boundaries and Commission interpretation of discrepancies.
- **10.23,C,2:** FEMA boundaries can apply in addition to Commission-mapped P-FP.
- **10.23,L,2:** shoreland distances depend on appropriate watermarks/wetland edges
  and waterbody/drainage characteristics. An approximate centerline buffer is not
  an authoritative zone determination.
- **10.23,N,2:** wetland classification depends on relevant evidence, including NWI
  and required site delineation. Small mapped inclusions and development-subdistrict
  exceptions mean an inventory cannot be mechanically substituted for legal zoning.

These are verified observations of selected publications, not a complete legal or
permit review. The detailed source references and qualification limits are in
[review.json](review.json), incorporated into the DERIVED [report](report.json).

## Outstanding evidence and downstream use

| Dependency | Evidence needed | Until then |
| --- | --- | --- |
| Current map and amendments | LUPC confirmation of current Osborn map, effective amendments and GIS flag/date semantics | Legal-current selection UNKNOWN |
| Flood protections | Adopted FIS/FIRM panels, revisions and relationship to LUPC adoption | No mapped P-FP does not clear flood protection |
| Wetlands/waterbodies | Qualified inventory/hydrography and site evidence where needed | No mapped wetland does not clear wetlands |
| Shoreland/physical boundaries | Watermarks, wetland edges, drainage attributes and interpretation where uncertain | No authoritative buffers or boundary-sensitive approvals |
| Rights/download route | Publisher terms and accessible official delivery route | Keep raw evidence private |

These dependencies remain attached to TL-F-0109; they are not five new parcel
claims or new clearance flags. Existing `related_finding_ids` already carry
TL-F-0109 in Osborn screenings. Consumers should inspect its current review and
this audit, while retaining historical screening caveats. No database view or
staleness mechanism is changed in this investigation.

The next bounded data step is **FEMA source qualification for Osborn**: identify
published effective panels/revisions and reconcile them to the map's adoption
reference before proposing an overlay. [Publisher questions](publisher-questions.md)
are ready for review but have not been sent. Wetland/hydrography qualification
follows; neither layer can independently establish a buildable site.

## Reproduction and loading

Exact responses remain ignored locally and in the private source archive. Restore
files to the paths in the retrieval logs and report input references, then run:

```sh
python3 scripts/investigate_lupc_currency.py
python3 scripts/investigate_lupc_currency.py \
  --prepare .local/currency-load --current .local/currency-current-finding.json
```

The current finding file must come from a fresh administrative read of TL-F-0109's
`event_id`. The preparer validates capture checksums, membership/duplicates, source
attributes, document review hashes and evidence links. It archives the report,
method, review and original input dependencies. The collector's generic document
label is not interpreted as JSON success; application errors are inspected.

Upload prepared objects to the existing private bucket, download just the manifest
objects and verify all checksums before applying `load.sql`. The transaction adds
one audit, one occurrence and one optimistic-lock review; it contains no geometry,
screening or schema changes. Historical reviews remain intact.

## Applied checkpoint

Audit `027c4170c9fc7748d5f40b64ed45cca8c11ec09a90a1bca473f1333a9fc28b9e`
is archived and recorded in Supabase. All 35 manifest objects were downloaded and
checksum-verified before loading. TL-F-0109 remains **in_progress**, now with three
evidence occurrences and `needs_revisit=false` after this review. TL-F-0025 remains
resolved. No publisher inquiry has been sent.

Before/after fingerprints of the complete geometry correction/event tables and
both screening-history tables match. There are still 2,648 default screenings,
153 revisions and zero stale defaults. Private bucket, RLS and client access
denials remain intact. The investigation reproduces byte-for-byte; all 45 Python
tests pass, including the four new source-response validation tests.

## Later flood-adoption review

The [Osborn adoption investigation](../osborn-flood-adoption/README.md) obtains
signed ZP 796 and confirms its clerical scope. It also documents staff adoption
authority and relevant Chapter 10 provisions. Incorporation of case 22-01-0871P
remains unknown; existing map dates do not establish non-adoption. The broader
TL-F-0109 qualifications above remain in force.
