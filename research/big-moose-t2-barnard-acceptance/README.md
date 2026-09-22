# Accept the three PR #43 proposals

Activate the exact reviewed Big Moose Township **27257109**, T2 R12 WELS
**27321193**, and Barnard Township **27303187** candidate bytes from
[the investigation](../big-moose-t2-barnard/README.md). Big Moose and Barnard separate
shell/hole contacts at existing vertices; T2 R12 separates two touching-hole pairs.
Nested hole ownership is retained. No coordinates move; originals and holds remain
inspectable.

The migration adds only these three IDs and the pinned PR #43 combined audit to
the bounded validator. Earlier cohorts retain their exact requirements. The database
verifies original input/feature hashes, candidate bytes, CRS, DERIVED classification,
recorded cycle/fill evidence, complete validity and source segment multiplicity.

The prepared load locks the county batch and requires the reviewed fourteen-correction
baseline. Three corrections, initial acceptance events, a dependency snapshot and
TL-F-0029 occurrence/review commit atomically. Changed baseline and partial cohort
states fail. Historical replay cannot replace a later withdrawal or review.

## Scope and retained unknowns

After activation: **17 accepted versions, 145 zoning holds and 21 parcel holds**
(166 total). Original holds remain 162 zoning / 183 total. All 120,449 original
records and fourteen earlier acceptances are preserved. Geometry remains DERIVED;
no county records qualify for parcel screening.

Both amendment metadata discrepancies remain open: **Big Moose index 2016-01-30
versus PDF amendments through 2022-12-30**, and **T1 R11 index 2005-08-18 versus
PDF ZP770 effective 2018-04-26**. Geometry acceptance does not establish legal currency.
Municipal applicability, parcel identity, wetland age, legal access/title, septic
suitability and buildability remain due-diligence matters.

## Tests and history

The disposable PostGIS fixture restores all original county records and the audit
chain through PR #43. [Tests](test-results.json) cover previous-validator rejection,
changed baseline rejection, source/audit/candidate binding, altered review evidence,
invalid geometry and changed segments; authentic activation/replay; withdrawal and
reacceptance; immutable history, stale review/snapshot rejection, privacy and
qualification; concurrent review serialization and snapshot capture. Synthetic
events and corrupted fixtures stay in the disposable database.

See [report](report.json), [baseline](baseline.json), [archive manifest](archive-manifest.json)
and [finding review](finding-review.json). The fourteen-correction ranking becomes
stale; the [seventeen-correction ranking](../seventeen-correction-ranking/README.md)
records new priorities. Historical reports remain intact.

## Reproduce

Restore private proposals and the checksum-matched county transfer:

```sh
python scripts/prepare_big_moose_t2_barnard_acceptance.py \
  --output .local/new-bmt-acceptance-load \
  --county-transfer .local/county-copy-load/load.sql
```

Restore migrations through `20260922020000` and the archived county/review/activation
loads through PR #43 in a disposable database. The runner checks old-validator
rejection before applying the new migration:

```sh
python tests/run_big_moose_t2_barnard_acceptance.py \
  --container DISPOSABLE_CONTAINER --database county_test \
  --prepared .local/new-bmt-acceptance-load \
  --report research/big-moose-t2-barnard-acceptance/test-results.json
```

Independently verify archive bytes, apply the tested migration and exact guarded
load, then verify using `scripts/check_big_moose_t2_barnard_acceptance.sql`.
Administrative access can bypass controls; this protects application review history.

## Live checkpoint

Migration `20260922030000` and all three acceptances are applied in Supabase.
All 14 archive objects passed checksum verification (eight new independent downloads,
six reverified earlier downloads). [Live verification](live-verification.json)
confirms seventeen acceptances, 145 zoning / 166 total effective holds, all original
fingerprints and fourteen prior acceptance versions unchanged, and zero qualified
rows. TL-F-0029 occurrence 19 records activation and retains both amendment follow-ups;
unrelated findings are unchanged. See [checkpoint](checkpoint.json).
