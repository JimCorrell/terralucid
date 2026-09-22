# Activation of the eleven PR #46 proposals

Activate only the eleven exact source/candidate versions reviewed in
[PR #46 evidence](../ten-case-zoning-review/README.md). This includes the ten
high-value cases selected by the backlog assessment and the bounded two-contact
Katahdin Iron Works interpretation. Preserve all original source data and seventeen
previous acceptance/event versions.

The extension pins the combined proposal/review audit and explicit source checksum.
It retains independent cycle/fill evidence, complete segment multiplicity, runtime
validity and EPSG:26919 checks. It does not add a general geometry repair or extend
acceptance to other multiple-contact source rings.

The initial atomic load requires the reviewed seventeen-correction snapshot under
the county writer lock. Historical replay verifies immutable payloads without
resetting later review events. The resulting 28 acceptances leave **134 zoning and
21 parcel holds**. Geometry is DERIVED; no county rows are qualified for parcel
screening.

All seven map-date follow-ups remain separate from geometry acceptance: Beaver Cove,
Orneville, Bowdoin College Grant West, T1 R13, Shawtown, Big Moose and T1 R11.
Municipal applicability, parcel identity, legal boundaries/access and wetland age
also remain unresolved. The later map-date investigation may clarify particular
document dates without certifying current legal zoning.

## Evidence and verification

- [Report](report.json): exact correction and acceptance identities.
- [Baseline](baseline.json): pinned previous corrections and finding versions.
- [Tests](test-results.json): full archived county fixture, old-validator rejection,
  changed evidence/bytes/segments, atomic baseline guards, exact replay, withdrawal,
  reacceptance, concurrent reviewers/snapshots, scope and privacy.
- [Archive](archive-manifest.json): private byte-identical evidence objects.
- [Finding review](finding-review.json): append-only TL-F-0029 activation event.

## Reproduce

Restore all migrations before `20260922040000` and the archived county, review,
acceptance and ranking loads through PR #46 into a disposable PostGIS database.
Prepare from the verified original county COPY transport:

```sh
python scripts/prepare_ten_case_acceptance.py \
  --output .local/new-ten-acceptance-load --county-transfer PATH_TO_ORIGINAL_COPY
python tests/run_ten_case_acceptance.py \
  --container DISPOSABLE_CONTAINER --database county_test \
  --prepared .local/new-ten-acceptance-load \
  --report research/ten-case-acceptance/test-results.json
```

Independently verify private archive bytes before applying the migration and guarded
load. Run `scripts/check_ten_case_acceptance.sql` read-only afterward. Administrative
access can bypass controls; this is application history protection.

## Live checkpoint

The tested migration and eleven acceptances are applied in Supabase. All 30 private
archive objects were verified (16 new downloads, 14 reverified earlier downloads).
[Live verification](live-verification.json) and [checkpoint](checkpoint.json) confirm
28 accepted versions, 134 zoning/21 parcel holds, unchanged original fingerprints
and seventeen previous acceptance/event versions, and zero qualified rows.
TL-F-0029 occurrence 22 records activation; unrelated findings remain unchanged.
