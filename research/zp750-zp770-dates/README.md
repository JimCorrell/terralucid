# ZP750 / ZP770 signed-decision date reconciliation

## Result

Use these **decision-stated historical effective dates**, with the signed decision
and this audit attached. Both are now supported by final signed documents rather
than only draft packets. Neither establishes current parcel-specific zoning.

| Action | Decision date | Decision-stated effective date | Evidence |
| --- | --- | --- | --- |
| ZP750 — Shawtown and T1 R12 WELS | June 10, 2015 | **June 25, 2015** | Signed decision, p14 of 14 |
| ZP770 — T1 R11 WELS | April 11, 2018 | **April 26, 2018** | Signed decision, p7 of 8 |

The first pages identify the petition, applicant and affected locality. The
signed effective-date pages explicitly state these dates and agree with the
published map amendment rows. All four relevant pages were rendered and visually
inspected. The PDF files are scans; text extraction yielded no text. The source
files were not altered or replaced by OCR output. Signature presence is an
observation; signer identity/authenticity was not independently authenticated.

Sources: [final ZP750](https://www.maine.gov/dacf/lupc/signedpermits/zp750.pdf) and
[final ZP770](https://www.maine.gov/dacf/lupc/signedpermits/zp770.pdf).
These paths were initially inferred from the publisher's observed naming pattern,
then verified against returned document identity and signed pages. Web-search
fetch failures did not imply absent records; direct capture succeeded.

## What remains contradictory

| Action | Other preserved values | Conclusion |
| --- | --- | --- |
| ZP750 | June 24 in map paragraph/index; July 2 in annual detail; July 21 in annual summary, both filing 2015-119 | Prefer June 25 **for the date stated by this signed decision**. Cause and legal significance of the conflicting entries remain unknown. |
| ZP770 | April 13 in annual detail; **April 24 in newly captured annual summary**, filing 2018-067; map-index amendment value remains August 18, 2005 | Prefer April 26 **for the date stated by this signed decision**. The two annual records do not agree with each other or the decision. |

The [2018 annual summary](https://legislature.maine.gov/doc/2687), PDF p4, was
visually inspected. It adds April 24; it does not supersede the signed decision.
The other dates and original bytes remain pinned to the
[PR47 investigation](../map-date-investigation/README.md).

**Historical decision transcription is reconciled; filing variance remains open.**
We have not established that the annual dates mean filing or publication dates,
nor proved that any entry is a typo. No source date is overwritten, no legal hold
is cleared, and TL-F-0029 remains in progress. The separate `decision_date` and
`decision_stated_effective_date` fields avoid conflating the action, its stated
effect, the original map adoption, edits, filings, or current applicability.

## Search limits and next evidence

The current Secretary of State archive did not expose 2015/2018 entries. Two
legacy index candidates and two bounded weekly-notice candidates returned HTTP 404;
their exact URLs, status, bytes and hashes are retained as failed search evidence.
They are not filing documents. Original filings 2015-119 and 2018-067 were **not
obtained**; no officials were contacted.

If exact historical effectiveness becomes material to a parcel or transaction,
obtain those original filings and recorded maps, or an agency reconciliation of
the mismatches. That is the remaining task; repeating draft-map comparison cannot
resolve it. Later amendments/current parcel applicability also need their own
review. Other PR47 follow-ups remain, including Orneville's ZP796 correction record.

## Provenance and validation

`review.json` contains manual observations and signed-document hashes. The
reconciliation method pins all new responses, previous contrary evidence, the
prior date audit and current county baseline. Raw bytes stay in private storage;
Git contains retrieval logs, report, manifest and reviewable methods.

Six checks reject a changed decision date, source replacement, legal promotion,
closing the filing variance, or changed case scope. The load uses the existing
exact geometry-snapshot and predecessor finding-event guards, appends the audit
and eight retrieval observations (four successful; four HTTP 404), and does not
modify geometry, source metadata, ranking, or acceptance events.

### Downstream use

For these two actions, use the explicitly named decision-stated historical date
and carry this audit, signed-document checksum/page, `VERIFIED` document
observation, `DERIVED` evidence selection, open filing variance and `UNKNOWN`
current legal applicability. This is an action-specific evidence reconciliation,
not a new blanket priority rule for all source dates. The original index values
remain available and unchanged.

## Live checkpoint

Published and verified September 22, 2026. All 31 private archive objects were
verified: 10 prior downloads rechecked and 21 new independent downloads.
TL-F-0029 occurrence 25 records this reconciliation. Live readback confirms
all 28 accepted versions and original fingerprints unchanged; the ranking
snapshot remains current, with 134 zoning and 21 parcel holds and zero
qualified rows. See `checkpoint.json` and `live-verification.json`.
