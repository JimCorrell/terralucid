# Osborn FEMA mask purpose follow-up

## Result

**The white area predates the 2024 revision.** The original July 20, 2016
panel 23009C0443D already displays a similar large blank region over labeled
Osborn, with imagery along the west and south. The 2024 annotated enclosure
retains a similar presentation, while its PDF contains revised hazard graphics
under the mask established in PR #17.

A legacy blanking treatment carried into the revised map is therefore a plausible
**INFERRED** explanation. It is not proof of an editing mistake or FEMA intent.
The earlier FIS's historical no-SFHA statement provides context, not an explanation
of the mask. The base panel is a raster: no claim of identical PDF objects or
exact geographic alignment is made.

The [June 14, 2024 final notice](https://www.govinfo.gov/content/pkg/FR-2024-06-14/pdf/2024-13142.pdf)
independently confirms finalization of Osborn case 22-01-0871P, CID 230595,
effective **May 31, 2024** (printed pages 50604 and 50606). This establishes the
historical revision's finalization, not the legal status of each covered graphic,
current legal currency, parcel applicability or LUPC adoption.

The original determination directs use of its annotated enclosures for floodplain
management and insurance, describes added Zone A and shaded Zone X, and retains
stricter state/local requirements. It does not explain the mask. Its legal effect
cannot be inferred away because the published display is white; equally, hidden
PDF graphics cannot be promoted to an authoritative replacement map.

## Evidence retained

| Source | Review and limit |
| --- | --- |
| [2016 base panel](https://msc.fema.gov/portal/downloadProduct?productTypeID=FINAL_PRODUCT&productSubTypeID=FIRM_PANEL&productID=23009C0443D) | Original ZIP, including PNG, world file and README, preserved exactly. Whole-panel visual comparison; no georeferencing or tracing. |
| [2024 Osborn determination](https://msc.fema.gov/portal/downloadProduct?productTypeID=LOMC&productSubTypeID=LOMR&productID=22-01-0871P-230595) | Reused checksum-pinned original and prior controlled mask audit. No new revision copy or modified PDF. |
| Final Federal Register notice | Original PDF and default renders of relevant pages; Osborn row and notice scope visually checked. |
| Generic NFHL guidance request | HTTP 403 retained as an access failure, not substantive guidance or absence evidence. |

[review.json](review.json) separates direct observations, inference and unknowns.
[report.json](report.json) records source/method hashes, exact ZIP member hashes,
original PDF archive parts and deterministic default-display renderings.
All captured bytes and diagnostic images remain in private storage; Git contains
metadata and the review. The comparison does not depend on a layer-hidden view.

This bounded review did not fetch Waltham's separate determination copy or the
large neighboring 22-01-0873P determination. It does not certify all later map
changes. The white area's purpose and the controlling depiction at the smaller
invalid feature still require authoritative clarification.

## Findings and downstream use

- **TL-F-0105 remains in progress/medium.** New base-map evidence supports the
  legacy-mask hypothesis and the final notice corroborates historical finalization.
  Mask intent, specific covered graphics, subsequent actions and adoption remain open.
- **TL-F-0026 remains in progress/high.** Neither structural geometry proposal is
  accepted. Exact source versions, original exclusions and all screenings are retained.
- Do not treat white display as no hazard, substitute the diagnostic view for an
  official map, or turn this research into parcel flood clearance.

[Publisher questions](publisher-questions.md) identify the case, panel, feature and
specific evidence needed. **Unsent**: this review has not contacted FEMA or others.
An authoritative answer or corrected enclosure is the next direct path to resolving
the mask question. LUPC adoption requires its own evidence.

## Reproduce and archive

Restore report inputs and captured responses from their private SHA-256 objects;
reassemble the original determination using its recorded three byte parts and
verify the full hash. With the existing PyMuPDF 1.24.14 environment:

```sh
python3 scripts/investigate_fema_mask_purpose.py
python3 scripts/investigate_fema_mask_purpose.py \
  --prepare .local/fema-purpose-load --current .local/fema-purpose-current.json
```

The current input must contain fresh `finding_id`/`event_id` rows for TL-F-0105
and TL-F-0026. Upload prepared objects to the existing private bucket, download
all manifest objects and verify before applying the atomic append-only `load.sql`:

```sh
python3 scripts/investigate_fema_mask_purpose.py \
  --verify-download .local/fema-purpose-download --prepared .local/fema-purpose-load
```

The load adds one audit, three response observations (including the 403), and two
finding occurrence/review appends. It contains no schema, geometry acceptance or
screening changes. Prior reports and source bytes are preserved.

## Applied checkpoint

Audit `769cff43b96b0c5fc909e6dd7821bf9d96e5ac1cf21c2170c718c36f183d95e1`
is recorded in private Supabase staging with three response observations and two
finding review/occurrence appends. All **24 archive objects** were downloaded and
verified, including reconstruction of the unchanged original determination PDF.
Fourteen objects were new; ten existing content-addressed objects were reused and
freshly verified.

TL-F-0105 has five occurrences and remains in_progress/medium; TL-F-0026 has four
and remains in_progress/high. Both have `needs_revisit=false`, indicating the
latest evidence was reviewed, not that the underlying uncertainty is resolved.
Complete geometry correction/event and screening/revision history fingerprints
match before and after; the two proposed FEMA candidate hashes are unchanged.
All 54 existing Python tests pass and the final report reproduces byte-for-byte.
