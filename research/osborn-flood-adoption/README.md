# Osborn: LUPC incorporation of the 2024 FEMA revision

## What this investigation establishes

**The August 2024 map amendment was a clerical correction.** The signed
[ZP 796 decision](https://www.maine.gov/dacf/lupc/signedpermits/zp796.pdf), dated
July 17, 2024 and effective August 1, 2024, explicitly includes Osborn. Finding 5
retains existing zoning; the approved action corrects adoption-note wording.
It is not evidence of a new flood-boundary adoption.

The [official Osborn map](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/osborn.pdf)
is byte-identical to the prior review. It still references the July 20, 2016
Hancock FIS and accompanying FIRM. FEMA case 22-01-0871P became final effective
May 31, 2024, as established by the prior FEMA audit, but **LUPC incorporation of
that specific revision remains UNKNOWN**. This review does not establish
non-adoption or inapplicability either.

The unresolved question is whether the existing adoption reference includes the
later LOMR or another LUPC action/interpretation controls. A date mismatch alone
cannot answer that question: FEMA retained the base panel's 2016 date when issuing
the revision.

## Procedure and rule evidence

| Evidence | Observation | Limit |
| --- | --- | --- |
| ZP 796, PDF pp. 1-4, 10 | Signed clerical correction; Osborn included; separate wording for FIRM-only and county FIS/FIRM communities | Does not establish incorporation of case 22-01-0871P |
| [Chapter 4](https://www.maine.gov/dacf/lupc/laws_rules/rule_chapters/Ch04_ver2023_August.pdf), 4.08,B,2,b, PDF p. 49 | Routine proposals to adopt new or amended FEMA maps can be handled by staff | Authority is not evidence of a specific decision; agendas alone cannot establish non-adoption |
| [Chapter 10](https://www.maine.gov/dacf/lupc/laws_rules/rule_chapters/Ch10_ver2026-04-06.pdf), 10.23,C,2, PDF p. 133 | FEMA SFHA Zones A, AE and VE qualify for protection; adopted FEMA boundaries also apply when different from Commission-mapped P-FP | Need the applicable source/adoption version; no automatic Zone X-to-P-FP crosswalk |
| Chapter 10, 10.25,T,1,d, PDF p. 251 | Express provision for LOMA/LOMR determinations placing specified property or structures outside SFHA | Does not establish blanket incorporation of hazard-adding LOMRs; other flood-prone-area provisions remain relevant |
| [2025 flood-rule basis](https://www.maine.gov/dacf/lupc/laws_rules/proposed_rules/chapter10/flood/BasisStatement.pdf), pp. 1-2 | Explains development-standard changes and NFIP consistency | Its stated purpose does not establish this Osborn adoption |
| [Incorporation reference page](https://www.maine.gov/dacf/lupc/laws_rules/materials_incorporated.shtml) | Explains title/version/date identification for incorporated materials | General process context, not an Osborn-specific ruling |

VERIFIED describes these publication contents, not a complete legal conclusion.
[review.json](review.json) records the scope, observations and remaining unknowns;
[report.json](report.json) pins source bytes, dependencies and reviewed-page renders.

## Downstream treatment

Retain FEMA hazard evidence and LUPC applicability as separate facts. The two
pending invalid FEMA polygons are 0.2-percent Zone X features: do not label them
P-FP merely because they are flood-hazard polygons. Independent LUPC designations
and broader flood-prone-area rules can still matter. Absence of an automatic
crosswalk is not an exemption or a flood/buildability clearance.

- **TL-F-0109 remains in progress:** ZP 796's scope is now documented. Current
  adoption, other map-currency questions, wetlands and shoreland dependencies remain.
- **TL-F-0105 remains in progress:** federal revision finalization, LUPC
  incorporation and the PDF mask are separate evidence questions.
- Geometry acceptance, original source records and all screening results are
  unchanged. No legal P-FP overlay or parcel determination is created.

[Unsent LUPC questions](publisher-questions.md) request the controlling record or
written interpretation, its scope and effective date. No inquiry was sent.
These questions complement the separate FEMA mask inquiry.

## Search limits

This was a bounded review of the official map, signed decision, rule indexes and
texts, incorporation page, Commission calendar and August 2024 agenda. It was not
an exhaustive inspection of staff correspondence, all minutes or later amendments.
The `zp796-probe` URL began as a filename probe; the retrieved signed document
confirmed its identity. The five-year report retrieval returned HTTP 502 and is
retained as failed access; its search snippet is not substantive evidence here.
The published Chapter 10 index still identifies April 6, 2026; the exact archived
edition was reused. No current-source completeness claim follows.

## Reproduce and archive

Restore response files and inputs from their private content-addressed archive
objects. With the existing PyMuPDF 1.24.14 environment:

```sh
python3 scripts/investigate_osborn_flood_adoption.py
python3 scripts/investigate_osborn_flood_adoption.py \
  --prepare .local/flood-adoption-load --current .local/flood-adoption-current.json
```

Supply fresh administrative `finding_id`/`event_id` rows for TL-F-0109 and TL-F-0105.
Upload prepared objects to the existing private bucket, download the manifest
objects and verify them before applying `load.sql`:

```sh
python3 scripts/investigate_osborn_flood_adoption.py \
  --verify-download .local/flood-adoption-download --prepared .local/flood-adoption-load
```

The atomic load appends one audit, ten response observations (including the 502),
and two finding occurrences/reviews. It changes no schema or screening data.
Referenced prior audits retain the earlier FEMA evidence chain.

## Applied checkpoint

Audit `8bb2f1efdcfd0c61dd5cc40c7cf97e6727be0481d5a868d3b3ce6d871eff9541`
is recorded in private Supabase staging with ten response observations and two
finding occurrence/review appends. All **34 manifest objects** were downloaded
and hash-verified before loading; 27 objects were new and seven reused.

TL-F-0109 now has five occurrences; TL-F-0105 has six. Both remain
in_progress/medium with `needs_revisit=false` after review; neither unknown is
resolved. Complete geometry correction/event and screening/revision history
fingerprints match before/after. All 54 existing Python tests pass and the report
reproduces byte-for-byte. Original maps, geometry proposals and screening defaults
remain unchanged.
