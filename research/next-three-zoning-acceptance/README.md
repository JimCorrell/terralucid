# Accept the three PR #39 proposals

Activate the exact reviewed representations for T4 R13 WELS **27224591**, T7 R9
WELS **27320676**, and T6 R15 WELS **27243652**. Candidate bytes are unchanged from
[the investigation](../next-three-zoning-priorities/README.md). Originals, source
holds, attributes and provenance remain available.

The migration extends the bounded validator only for those three IDs and the
pinned PR #39 audit. That combined audit contains proposals and separate checks of
fixed candidate cycles and even-odd fill. Earlier cohorts keep their audit
requirements. The database checks exact source/candidate hashes, CRS, DERIVED
classification, recorded review evidence, complete geometry validity and every
original boundary segment with multiplicity. There is no automatic repair.

The prepared load locks the county batch and requires the reviewed eight-correction
baseline. It atomically inserts three corrections, their initial acceptance events,
a new dependency snapshot and a TL-F-0029 occurrence/review. A changed baseline or
partial cohort fails; exact historical replay cannot overwrite later reviews.

## Verification

The integration test restores the original 120,449-record county fixture and the
audit/event chain through PR #39 in a disposable PostGIS database. It exercises:

- Previous-validator rejection of all three new versions.
- Changed baseline rejection without partial writes.
- Source, audit, candidate, cycle/fill evidence, validity and segment guards.
- Authentic activation and exact replay; all eight previous approvals preserved.
- Withdrawal/reacceptance, stale reviews and snapshots, immutable history,
  source scope, original counts, privacy and qualification controls.
- Concurrent review serialization and snapshot capture; historical replay after
  newer events leaves those events in place.

Synthetic events and deliberately corrupted fixtures exist only in the disposable
database. See [test results](test-results.json), [activation report](report.json),
[baseline](baseline.json), [archive manifest](archive-manifest.json) and
[finding review](finding-review.json).

After activation: **11 accepted versions, 151 zoning holds and 21 parcel holds**
(172 total). Original holds remain 162 zoning / 183 total. All geometry is DERIVED;
legal boundaries, applicability, title/access, septic suitability and buildability
are not established. No county rows are qualified for parcel screening.

The eight-correction ranking and prior coverage scenario become stale. The
[eleven-correction refresh](../eleven-correction-ranking/README.md) records a new
result against the new dependency snapshot; historical results are preserved.

## Reproduce

Restore the original checksum-matched county transfer and private proposal bytes:

```sh
python scripts/prepare_next_three_zoning_acceptance.py \
  --output .local/new-next-acceptance-load \
  --county-transfer .local/county-copy-load/load.sql
```

Restore migrations through `20260921070000` and the archived original county and
audit/activation loads through PR #39 in a disposable database. The test runner
applies the new migration after confirming previous-validator rejection:

```sh
python tests/run_next_three_zoning_acceptance.py \
  --container DISPOSABLE_CONTAINER --database county_test \
  --prepared .local/new-next-acceptance-load \
  --report research/next-three-zoning-acceptance/test-results.json
```

Upload and independently verify prepared archive bytes, apply the tested migration,
then the guarded load. Verify with `scripts/check_next_three_zoning_acceptance.sql`.
Database administrators can bypass controls; this is application history protection.

## Live checkpoint

Migration `20260922010000` and all three acceptances are applied in Supabase.
All 14 archive objects were verified (eight new downloads, six reverified earlier
independent downloads). [Live verification](live-verification.json) confirms eleven
acceptances, 151 zoning / 172 total holds, unchanged original fingerprints and
prior eight acceptance versions, and zero qualified rows. TL-F-0029 occurrence 13
records activation; unrelated finding events are unchanged. The old snapshot is
stale and the new snapshot is current. See [checkpoint](checkpoint.json).
