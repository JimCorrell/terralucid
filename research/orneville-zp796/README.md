# Orneville — ZP796 clerical correction

## Result

The [signed ZP796 decision](https://www.maine.gov/dacf/lupc/signedpermits/zp796.pdf)
establishes a **map-text correction**, approved July 17, 2024 and effective
**August 1, 2024**. Page 1 explicitly preserves existing zoning; p4 includes
Orneville in the FIRM-only group. The signed approval and effective date are on
p10. This establishes the historical correction's scope/date, completing the
previously outstanding search for its decision record.

The [published Orneville map](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/orneville-twp.pdf)
implements the approved FIRM-only template from decision p2. A deterministic
comparison substitutes the index's FIRM name/date and normalizes whitespace;
the text matches exactly. Fresh map bytes also match the PR47 capture.

| Date | Meaning | Evidence |
| --- | --- | --- |
| April 17, 1987 | Referenced Orneville FIRM date | Map FEMA note and fresh index FEMA field |
| August 3 / August 18, 2005 | Initial map adoption / effective dates | Map paragraph and index |
| July 17, 2024 | ZP796 staff decision | Signed decision p10 |
| August 1, 2024 | Text-correction effective date | Signed decision p10; map amendment row |

The index `AMEND_DATE` remains August 18, 2005 while its edit text says August 1, 2024.
Preserve both; neither edit timestamps nor initial dates substitute for amendment
history. No index value has been overwritten.

## What the action does and does not establish

The decision distinguishes FIRM-only communities from those with county-wide
FIS/FIRM products, approving different note templates. Its action covers multiple
communities; Orneville was not an isolated correction. A later official **draft**
five-year report (PDF p53, printed 52) summarizes 111 MCDs. That is corroborating
context, not an audit of the other 110 communities or evidence of current coverage.

The revised note says referenced FIRM flood areas can fall under P-FP regulation
whether or not displayed on this zoning map. Downstream analysis must not infer
absence of flood constraints from absent P-FP display or digital NFHL availability.
This review verifies documentary statements, not parcel-specific legal effect.

The approved correction is text-only. We did not compare historical geometries,
reconstruct a pre-correction map, or alter any accepted geometry. A targeted
search did not locate an authoritative pre-August 2024 Orneville note; its exact
previous wording remains UNKNOWN. The decision supports the approved wording,
not a reconstruction of every earlier text error.

## Remaining due diligence

For a relevant parcel, confirm applicable FEMA panels and subsequent revisions,
including any site-specific determinations, independently of this clerical update.
The 1987 reference is not proof that it is the complete/current FEMA product set.
Retrieve the earlier map only if the correction's precise change history becomes
material. No officials were contacted. Other map-currentness limits and the
ZP750/ZP770 filing discrepancies remain tracked under TL-F-0029.

## Evidence and checks

`review.json` records visual review of complete decision pages 1, 2, 4, 10 and the
published map note. The signed record was found using the publisher's established
filename pattern, then verified against its contents. Original PDFs, index and
later draft report are privately archived with retrieval dates and SHA256 hashes;
no source bytes are edited. Git holds the structured report and retrieval logs.

The method checks document hashes, Orneville's inclusion, exact template matching,
distinct dates, prior audit and current county snapshot. Six tests cover normal
review, whitespace handling and rejection of wrong dates, geometry promotion and
current-legal-status promotion. The load appends four observations, an audit and
a TL-F-0029 review with existing snapshot and predecessor-event guards. No
migration, geometry activation or ranking refresh is needed.

## Live checkpoint

Published and verified September 22, 2026. Nineteen private archive objects were
verified (four prior downloads rechecked; fifteen new independent downloads).
TL-F-0029 occurrence26 records this review. All28 acceptance versions and original
county fingerprints are unchanged; ranking snapshot remains current. There are
still134 zoning/21 parcel holds and zero qualified rows. See `checkpoint.json`
and `live-verification.json`.
