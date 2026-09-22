# Seven map-date investigations — 2026-09-22

## Result

Four maps have independently corroborated amendment histories that postdate their
map-index `AMEND_DATE`. Two have additional conflicts among official records.
Orneville documents a clerical FEMA-text correction. **No date replacement is
proposed, and current legal applicability remains UNKNOWN for all seven.**

| Map | Index AMEND_DATE | PDF amendment | Independent evidence / outcome |
| --- | --- | --- | --- |
| Big Moose | 2016-01-30 | ZP791, 2022-12-30 | Completed regional project page confirms 2022 effective date; signed ZP707B also confirms 2020-07-30. |
| Beaver Cove | 2012-09-04 | ZP791, 2022-12-30 | Same two corroborated regional actions. |
| Bowdoin College Grant West | 2005-08-18 | ZP707B, 2020-07-30 | Signed decision identifies locality (p1) and effective date (p19). |
| T1 R13 WELS | 2005-08-18 | ZP707B, 2020-07-30 | Signed decision identifies locality (p2) and effective date (p19). |
| T1 R11 WELS | 2005-08-18 | ZP770, 2018-04-26 | Draft packet agrees; annual rulemaking report labels **2018-04-13** effective. Conflict remains. |
| Orneville | 2005-08-18 | ZP796, 2024-08-01 | Map describes clerical FEMA-adoption-text correction; index edit text agrees with 2024 date. Final correction record not located. |
| Shawtown | 2015-06-24 | ZP750, 2015-06-25 | Map effective paragraph also says June 24; draft agrees with June 25; two annual records list **July 2 and July 21**. Conflict remains. |

These are VERIFIED observations of document contents. The comparison and
classification are DERIVED. Whether a difference reflects a transcription error,
a distinct filing process, or another cause remains UNKNOWN. No unsigned draft
is treated as a final decision. The date of a retrieved page or a search engine's
publication estimate is not an amendment date.

## Official corroboration and conflicts

- [Signed ZP707B decision](https://www.maine.gov/dacf/lupc/plans_maps_data/resourceplans/moosehead/zp707B_WeyerhaeuserPetition/decision/zp707b.pdf), pp 1–2 and 19: action July15, effective July 30, 2020. The signature page is scanned; it was rendered and visually inspected. The [publisher page](https://www.maine.gov/dacf/lupc/plans_maps_data/resourceplans/moosehead_prp014.html) independently agrees. Its older paragraph saying consideration is ongoing is retained, not used to override its dated termination entry.
- [Completed Moosehead planning project](https://www.maine.gov/dacf/lupc/projects/moosehead_region_planning_project/moosehead_regional_planning.html): approval December 14, 2022; new zones/rules effective December30. The linked December 7 agenda package labels its decision **draft**; that packet alone would not establish approval.
- [ZP770 draft packet](https://www.maine.gov/dacf/lupc/agenda_items/041118/zp770_ThirdMusquashPond_CommPkt.pdf), PDF p11, agrees with April 26, 2018. [Annual report](https://legislature.maine.gov/doc/2688), PDF p26, identifies filing 2018-067 with April 13. Its original host failed; the successful canonical-host retry and failed request log are preserved.
- [ZP750 draft packet](https://www.maine.gov/dacf/lupc/agenda_items/061015/CommMemo_ZP750_Medawisla.pdf), PDF p17, says June 25, 2015. [Annual detail](https://www.legislature.maine.gov/doc/988), PDF p33, says July 2; [annual summary](https://legislature.maine.gov/doc/1011), PDF p4, says July 21. Both identify filing 2015-119. These conflicting rows were visually inspected. Meeting-record links lead to audio; they are not signed decisions and were not transcribed.
- [Orneville map](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/orneville-twp.pdf), p1: the 2024 entry concerns adoption text. Its referenced FIRM date is April 17, 1987 and matches the index's separate FEMA date. Neither a later edit timestamp nor this statement proves newer flood geometry or parcel-specific applicability.

## Downstream use and next actions

Use separately named, source-linked **documented amendment history** for the four
corroborated histories. Do not silently replace source `AMEND_DATE`, infer the
latest legally operative zoning, or use the maximum of unlike dates. The service
metadata describes map extents and supplies field names, without a definition
promising that `AMEND_DATE` represents the latest published amendment.

1. Obtain final signed ZP750 and original filing 2015-119 to reconcile four dates.
2. Obtain final signed ZP770 and original filing 2018-067 to reconcile April 13/26.
3. For a relevant parcel, obtain ZP796's correction record and earlier Orneville
   text; confirm applicable flood evidence separately.
4. For all seven, check later actions and current parcel-specific applicability
   when due diligence is triggered. Corroborating a historical date is not a
   completeness audit of zoning history.

No officials were contacted. Public searches and linked meeting/project records
are bounded research, not proof that unlocated documents do not exist. All seven
follow-ups remain tracked under TL-F-0029, with narrower next actions.

## Reproduction and provenance

`probes.json` and subsequent probe manifests identify requests; `runs/*/results.json`
retain URLs, response hashes, retrieval times and failures. Original response
bytes are held in the private source bucket, excluded from Git. `review.json`
records manual observations; `scripts/investigate_map_dates.py` validates the
seven-map scope, converts epoch values in UTC, pins all evidence and the current
28-correction ranking, and creates `report.json`. The reported date values here
are unchanged by UTC versus Maine local calendar conversion for these records.

`prepare_map_date_review.py` preserves evidence in source observations, appends an
audit and TL-F-0029 event, and checks exact geometry dependencies and the previous
finding event in one transaction. It changes no source dates, geometries,
correction acceptances, qualification flags or ranking. The prior ranking's
geometry snapshot remains current; this later finding review supersedes its
map-date next-action text.

## Live checkpoint and tests

Published and verified September 22, 2026: 25 source observations, one byte-less
request failure preserved in logs, 43 private archive objects verified (11 prior
downloads rechecked and 32 new independent downloads). TL-F-0029 occurrence 24
records the investigation. All 28 acceptance versions and original county
fingerprints are unchanged; the ranking snapshot remains current. The county
still has 134 zoning and 21 parcel holds and zero qualified rows.

`test-results.json` records stale-review rollback and idempotent replay checks in
the disposable full county fixture. Earlier lifecycle tests leave different
local review-event versions, so only fixture snapshot/dependency and predecessor
event bindings were adapted for that test; the production load was unchanged.
`live-verification.json` and `checkpoint.json` record the unmodified production
load readback. Report, method and input hashes were checked before publication.
