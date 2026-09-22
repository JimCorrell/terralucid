# Accept the three PR #41 proposals

Activate the exact reviewed T10 R15 WELS **27233351**, Chesuncook Township
**27314083**, and T1 R11 WELS **27316137** representations. Candidate bytes are
unchanged from [the investigation](../latest-three-zoning-priorities/README.md).
Each assigns a nested hole to its innermost shell and equals valid service GeoJSON.
No coordinates move and no rings split. Original records and holds remain available.

The migration adds only these three IDs and the pinned PR #41 audit to the bounded
validator. Its combined audit contains proposals and separate fixed-candidate
cycle/fill checks. Earlier cohorts retain their exact audit requirements. The
database verifies source/candidate bytes, CRS, DERIVED classification, review
evidence, complete geometry validity and every original segment with multiplicity.

The prepared load locks the county batch and requires the reviewed eleven-correction
baseline. Three corrections, initial acceptance events, a dependency snapshot and
TL-F-0029 occurrence/review commit atomically. Changed baselines or partial cohorts
fail; historical replay cannot overwrite later reviews.

## Retained unknowns

**T1 R11's amendment-date discrepancy remains open:** the map index reports
2005-08-18 while the PDF lists ZP770 effective 2018-04-26. Acceptance of this exact
geometry does not resolve legal currency. Both source versions and the follow-up
are retained in TL-F-0029 and the ranking review.

After activation: **14 accepted versions, 148 zoning holds and 21 parcel holds**
(169 total). Original holds remain 162 zoning / 183 total. All 120,449 original
county records and prior eleven approvals are preserved. Municipal applicability,
parcel identity, wetland age, legal access/title, septic suitability and buildability
remain due-diligence matters; no county rows qualify for parcel screening.

## Verification and version chain

The disposable PostGIS fixture restores all original records and the review history
through PR #41. [Tests](test-results.json) cover previous-validator rejection,
changed baselines, source/audit/candidate binding, altered review evidence, invalid
geometry and segment changes; authentic activation and replay; withdrawal and
reacceptance; immutable history, stale reviews/snapshots, privacy and qualification;
and concurrent reviews and snapshot capture. Synthetic events and corrupted
fixtures stay in the disposable database.

See [report](report.json), [baseline](baseline.json), [archive manifest](archive-manifest.json)
and [finding review](finding-review.json). The eleven-correction ranking becomes
stale; the [fourteen-correction refresh](../fourteen-correction-ranking/README.md)
records new priorities against a new snapshot. Historical reports remain intact.

## Reproduce

Restore checksum-matched original county transfer and private proposal artifacts:

```sh
python scripts/prepare_latest_three_zoning_acceptance.py \
  --output .local/new-latest-acceptance-load \
  --county-transfer .local/county-copy-load/load.sql
```

Restore migrations through `20260922010000` and archived county/audit/activation
loads through PR #41 in a disposable database. The runner first confirms that the
old validator rejects the cohort, then applies the new migration:

```sh
python tests/run_latest_three_zoning_acceptance.py \
  --container DISPOSABLE_CONTAINER --database county_test \
  --prepared .local/new-latest-acceptance-load \
  --report research/latest-three-zoning-acceptance/test-results.json
```

Independently verify archived bytes, apply the tested migration and exact guarded
load, then run `scripts/check_latest_three_zoning_acceptance.sql`. Administrators
can bypass controls; this is application history protection.

## Live checkpoint

Migration `20260922020000` and all three acceptances are applied in Supabase.
All 14 private archive objects were checksum-verified (eight new independent
downloads and six reverified earlier downloads). [Live verification](live-verification.json)
confirms fourteen acceptances, 148 zoning / 169 total effective holds, original
fingerprints and all eleven previous versions unchanged, and zero qualified rows.
TL-F-0029 occurrence 16 records activation and retains the amendment discrepancy;
unrelated findings are unchanged. The previous ranking snapshot is stale and the
new snapshot is current. See [checkpoint](checkpoint.json).
