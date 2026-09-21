# Initial findings index

These stable IDs were seeded from the audits. **Current status and next actions live in Supabase**, in `ingest.finding_current`; this index records the initial definitions. See [the review workflow](../../docs/findings-register.md).

| ID | Initial finding | Initial priority |
| --- | --- | --- |
| TL-F-0001 | Source presence gaps | high |
| TL-F-0002 | Sweden code/name conflict | high |
| TL-F-0003 | Alfred code/name conflict | high |
| TL-F-0004 | Other jurisdiction-name discrepancies | medium |
| TL-F-0005 | Unrecognized jurisdiction codes | high |
| TL-F-0006 | Blank jurisdiction identifiers | high |
| TL-F-0007 | Missing candidate parcel identifiers | high |
| TL-F-0008 | Repeated and placeholder identifiers | high |
| TL-F-0009 | Assessment records unmatched by identifier | high |
| TL-F-0010 | Assessment relationship multiplicity | high |
| TL-F-0011 | Missing source dates | medium |
| TL-F-0012 | Malformed or uninterpreted source dates | medium |
| TL-F-0013 | Jurisdiction legal-effective dates unknown | medium |
| TL-F-0014 | Source record identifier stability untested | medium |
| TL-F-0015 | Compound-key uniqueness untested | high |
| TL-F-0016 | UT valuation-book linkage untested | medium |
| TL-F-0017 | Source rights and reuse limits unresolved | medium |
| TL-F-0018 | Parcel-source overlap unresolved | high |
| TL-F-0019 | Assessment YEAR_CREAT semantics unresolved | medium |
| TL-F-0020 | Full assessment join coverage unmeasured | medium |
| TL-F-0021 | Jurisdiction parcel completeness unknown | high |
| TL-F-0022 | Geometry quality and boundary authority unresolved | high |
| TL-F-0023 | Assessment candidate jurisdiction disagreement | high |
| TL-F-0101 | Conserved Lands: source qualification | medium |
| TL-F-0102 | Tree Growth/current-use tax status: source qualification | medium |
| TL-F-0103 | Deeds, recorded plans and easements: source qualification | medium |
| TL-F-0104 | 3DEP elevation product catalog: source qualification | medium |
| TL-F-0105 | NFHL availability index: source qualification | medium |
| TL-F-0106 | 3DHP and legacy NHD: source qualification | medium |
| TL-F-0107 | Land cover and imagery for privacy/remoteness: source qualification | medium |
| TL-F-0108 | Listing and market records: source qualification | medium |
| TL-F-0109 | LUPC zoning polygons and official maps: source qualification | medium |
| TL-F-0110 | Municipal zoning and shoreland records: source qualification | medium |
| TL-F-0111 | MaineDOT public road centerlines: source qualification | medium |
| TL-F-0112 | Wastewater permits and site evaluation: source qualification | medium |
| TL-F-0113 | SSURGO / Soil Data Access: source qualification | medium |
| TL-F-0114 | Building footprint candidate: source qualification | medium |
| TL-F-0115 | ATV and snowmobile route information: source qualification | medium |
| TL-F-0116 | Power, communications and water options: source qualification | medium |
| TL-F-0117 | National Wetlands Inventory: source qualification | medium |

Each definition and its initial next action is in [catalog.json](catalog.json). Reviews and resolutions append evidence-linked events; do not change this catalog to overwrite history.

## Findings introduced after the initial seed

| ID | Finding | Initial priority | Evidence |
| --- | --- | --- | --- |
| TL-F-0024 | Source freshness differs across GIS and municipal maps | medium | [Municipal corroboration](../municipal-corroboration/README.md) |

The initial seed catalog remains unchanged. This subsequent finding is defined in
[its investigation](../municipal-corroboration/new-findings.json); current status lives in Supabase.

The [zoning pilot](../zoning-ingestion/README.md) adds **TL-F-0025** for an invalid
Osborn zoning polygon excluded from calculations, and appends evidence/reviews to
TL-F-0109 (LUPC qualification) and TL-F-0110 (municipal qualification). Its new
finding definition is in `research/zoning-ingestion/findings-plan.json`; the
original seed catalog remains unchanged.

The [Osborn FEMA qualification](../osborn-fema/README.md) adds **TL-F-0026** for two
invalid FEMA flood-zone polygons. Its definition and initial review are in
`research/osborn-fema/findings-plan.json`. TL-F-0105 and TL-F-0109 receive additional
evidence and remain in progress; no geometry correction is accepted in this step.

The [TL-F-0026 geometry investigation](../fema-geometry-investigation/README.md)
proposes exact-version, segment-preserving shell/hole decodings for both FEMA
polygons. They remain unaccepted. TL-F-0026 moves to in progress/high; TL-F-0105
also records a map/service depiction discrepancy for the smaller feature.

The [0443D display follow-up](../fema-map-discrepancy/README.md) explains the apparent
blankness as an opaque PDF MASK layer over existing graphics. TL-F-0105 still
tracks the mask's regulatory purpose and other qualification gaps; TL-F-0026's
proposals remain unaccepted. Earlier map observations are retained in history.

The [FEMA mask-purpose follow-up](../fema-mask-purpose/README.md) appends evidence
for TL-F-0105 and TL-F-0026: a similar blank region predates the revision, and the
Federal Register confirms historical finalization. Both findings remain in progress;
mask intent and the status of specific covered graphics still need clarification.

The [LUPC flood-adoption investigation](../osborn-flood-adoption/README.md) appends
reviews to TL-F-0109 and TL-F-0105. Signed ZP 796 establishes the clerical scope of
the August 2024 amendment. The specific 2024 LOMR's LUPC incorporation remains
unknown, with unsent questions identifying the missing record or interpretation.

The [bounded Osborn wetlands audit](../osborn-wetlands/README.md) advances TL-F-0117
and adds **TL-F-0027** for conflicting joined NWI classification definitions and
**TL-F-0028** for invalid native availability geometry. Exact source variants,
May 1983 imagery metadata and next actions remain visible; neither issue is resolved.

The [NWI classification review](../wetlands-classification/README.md) resolves
**TL-F-0027 for the eight reviewed source records** through exact official-reference
matches. The upstream duplicate join persists; this is not a publisher-repair claim.
TL-F-0117 retains package/identity/projection and applicability work. TL-F-0028 is
unchanged and open. Earlier definitions and findings history remain intact.
