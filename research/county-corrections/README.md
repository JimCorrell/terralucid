# County correction activation

Following merged PR #30 and authorization to implement the correction layer, this
step activates three exact-version DERIVED interpretations through a separate
private interface. It preserves the original 120,449 county records and all source
holds. See [the downstream policy](../../docs/county-geometry-corrections.md).

| Feature | Accepted interpretation |
| --- | --- |
| Blanchard P-SL2, 27334504 | Existing self-touching shell and hole represented separately |
| Atkinson M-GN, 27249007 | Existing self-touching shell and hole represented separately |
| Atkinson P-SL2, 27291625 | Nested holes assigned to innermost containing shells |

The exact candidate checksums and source/proposal/review dependencies are in
`report.json`. The prior independent review checked all 1,199 original faces with
zero symmetric-difference area. This activation adds database validation of the
same reviewed bytes, validity and source segment multiplicity; it does not create
new source evidence or infer legal zoning boundaries.

## Live outcome and limits

Original holds remain **183 total / 162 zoning**; accepted interpretations reduce
effective holds to **180 total / 159 zoning**. The 21 parcel holds are unchanged.
All three effective geometries intersect the county interior. Every county row
remains unqualified for parcel screening. TL-F-0029 stays in progress, with
unsupported Moosehead Junction / Spencer Bay interpretations and other prioritized
holds next. Municipal zoning, parcel identity and wetlands age follow-ups persist.

Acceptance/withdrawal history and correction dependency snapshots are append-only.
Exact replay does not duplicate history or undo withdrawal. Fresh captures cannot
inherit an older acceptance. Future county results must retain and validate these
dependencies; there are no existing county screening results to recompute.

## Reproduction and verification

Restore the exact archived county COPY transfer identified by
`research/piscataquis-ingestion/transport-verification.json`, plus the proposal and
review reports and three candidate files from their private archive manifests.
The preparation script checks the entire transfer checksum before extracting the
three serialized inputs. No full source geometry is committed to Git.

```sh
python scripts/prepare_county_corrections.py \
  --county-transfer .local/county-copy-load/load.sql \
  --output .local/county-corrections-load
```

In an isolated PostGIS 17 / 3.5 database, apply migrations, seed the finding catalog,
and load the archived county, proposal and independent-review transactions in
order. Then run:

```sh
python tests/run_county_corrections.py --container DISPOSABLE_CONTAINER \
  --database DISPOSABLE_DATABASE --prepared .local/county-corrections-load \
  --report research/county-corrections/test-results.json
```

This suite includes full activation replay, original/effective counts, provenance
rejection, withdrawal/reacceptance, stale snapshots and reviews, immutable history,
privacy, and concurrent review/snapshot locking. It intentionally appends synthetic
review events only in the disposable database; never run it on Supabase.

For deployment, verify the expected TL-F-0029 event, apply the migration, upload
all prepared objects to the existing private archive, independently download and
hash-verify them, then use `scripts/apply_prepared_load.py`. Run
`scripts/check_county_corrections.sql` for read-only live verification. Checkpoint,
test results, archive manifest and live readback accompany the completed load.

## Deployment checkpoint

Migration `20260921050000` and the atomic three-acceptance load are applied to the
configured Supabase project. All **14 archive objects** passed independent
download/checksum verification. Live readback confirms unchanged fingerprints for
all **120,449 original rows**, the hold counts above, three valid native-CRS
accepted geometries and a current dependency snapshot. Other finding events are
unchanged. `checkpoint.json` and `live-verification.json` record the evidence.

The final isolated integration suite passed, including a snapshot waiting for a
concurrent committed withdrawal and rejection of a competing stale review.
`test-results.json` pins the tested load and test files. No synthetic test events
were written to Supabase.
