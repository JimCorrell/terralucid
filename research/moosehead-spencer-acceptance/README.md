# Moosehead Junction and Spencer Bay acceptance

Following merged PR #33 and authorization to proceed, add the two reviewed
exact-version interpretations to the county correction layer. Preserve the
original three approvals, source records, original holds and review history.

| Feature | Reviewed interpretation |
| --- | --- |
| Moosehead Junction P-SL2, 27208875 | Separate two point-touching hole loops plus the reviewed nested shell/hole contacts |
| Spencer Bay P-SL2, 27336229 | Separate two point-touching hole loops plus the reviewed nested shell/hole contact |

The candidates are unchanged from PR #32. PR #33 verified all 560 source cycles,
shell/hole roles, common owners, complete segment multiplicity and independent
filled area. This step does not create new geometry or new source observations.

## Bounded validator extension

Migration `20260921060000` replaces only the correction validation function. The
original three features retain their original proposal/review audit pins. The new
two require their own pinned audits and reviewed cycle-role evidence. The old
proposal report's `county_feature_sha256` and new report's `source_feature_sha256`
are explicitly selected per cohort. Mixing cohort IDs, audits or source/candidate
versions fails. Existing validity, segment, source input, CRS and replay checks
remain, as do private access and immutable review history.

The same effective view and acceptance/withdrawal protocol apply to all five.
Accepted geometry is the default for the exact source version; using original
geometry in analysis requires an evidentiary reason. No unreviewed feature is
implicitly repaired. See [county policy](../../docs/county-geometry-corrections.md).

## Dependencies and remaining limits

The activation transaction appends two corrections and acceptance events, records
a new dependency snapshot and appends the TL-F-0029 review. The prior snapshot
remains historical and becomes `needs_revisit=true`. A consumer must use the new
snapshot or recompute/review any result tied to the old one; it must not overwrite
old dependencies or silently mark old results current.

Verified effective holds are **157 zoning / 178 total**, down from 159 / 180.
Original holds remain **162 zoning / 183 total**. All 120,449 original county rows
remain unchanged. The 21 parcel holds and municipal applicability, source age,
legal access, septic/buildability and other qualifications persist. Every row
remains unqualified for parcel screening. TL-F-0029 stays in progress; refresh
prioritization against the five accepted geometries before choosing the next group.

## Validation and reproduction

Restore the archived original county COPY transfer and pinned PR #32/#33 reports
and candidate bytes. Preparation checks the complete transfer checksum before
extracting the two exact serialized source records:

```sh
python scripts/prepare_moosehead_spencer_acceptance.py \
  --county-transfer .local/county-copy-load/load.sql \
  --output .local/moosehead-spencer-acceptance-load
```

For tests, create a disposable PostGIS database, apply migrations, seed the finding
catalog, and load the archived county, first proposal/review/activation, and new
proposal/review transactions in order. All three original corrections must be
present with their original current snapshot before running:

```sh
python tests/run_moosehead_spencer_acceptance.py \
  --container DISPOSABLE_CONTAINER --database DISPOSABLE_DATABASE \
  --prepared .local/moosehead-spencer-acceptance-load \
  --report research/moosehead-spencer-acceptance/test-results.json
```

Tests check all five valid/scope-correct acceptances, unchanged original approvals,
both new features' withdrawal/reacceptance, altered source/candidate rejection,
mixed audit cohorts, historical replay, stale reviews/snapshots, immutable history,
private access and concurrent review/snapshot locking. Synthetic reviews are
confined to the disposable database.

Archive and independently download/hash-verify the prepared evidence, check the
expected finding event, apply the tested migration and use `apply_prepared_load.py`
for the atomic activation. Read-only verification is in
`scripts/check_moosehead_spencer_acceptance.sql`; checkpoint and live readback
record the completed deployment. No full source geometry is committed to Git.

## Deployment checkpoint

The migration and atomic two-acceptance load are applied in Supabase. All **12
archive objects** passed independent download/checksum verification. Live readback
confirms all **120,449 original fingerprints unchanged**, five valid native-CRS
accepted geometries with interior county intersections, and the hold counts above.
The original three acceptance records and other finding events are unchanged.

The prior three-correction snapshot is retained with `needs_revisit=true`; one new
five-correction snapshot is current. `checkpoint.json` records both IDs. The full
isolated integration suite passed, including both new features' lifecycle and
concurrent review/snapshot checks. `test-results.json` pins the executed tests and
prepared load. No synthetic test events were written to Supabase.
