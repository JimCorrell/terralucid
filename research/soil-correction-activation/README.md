# Soil correction activation

**Activated and verified in Supabase after explicit user authorization.**
The [live verification](live-verification.json) records seven accepted corrections,
zero effective holds, a current dependency snapshot and **0 m² uncovered county
area** (`full_geometric`) in the live PostGIS runtime. No rounding/tolerance was
used. This establishes geometric coverage of the pinned county boundary, not soil
completeness, site suitability or parcel qualification.

All 38,237 original records retain the same full-row fingerprint. The seven
original holds and 29,361 original analytical geometries remain unchanged. The
county inventory count remains 120,449. Four new tables have RLS enabled and no
client-role grants were found in the checked tables/view.

The 15 private investigation archive objects were downloaded and hash-verified
([readback](archive-verification.json)). The pending PR #59 finding event was
confirmed absent, then appended in the same transaction as acceptance and the
new TL-F-0113 update. TL-F-0113 remains in progress: units, scale, survey/source
dates and attribute limitations still need qualification before soil availability
is enabled. Septic/buildability evaluation remains purchase-triggered.

## Execution history

Automatic approval review initially blocked production execution. The user then
explicitly authorized deployment, activation and finding updates. The first
[authorized attempt](initial-attempt.json) installed the migration but encountered
a local queue/list variable-name collision before activation commit. Closing the
backend rolled back that transaction. The runner now uses a distinct output queue.

A fresh bounded attempt checked the installed migration hash, unchanged source
fingerprint and absence of existing corrections before proceeding. It succeeded
and read back the committed state. There were two credential acquisitions and two
database sessions across these diagnosed attempts, one per invocation, with no
authentication retry loop. The successful invocation used the same backend for all
stages. Historical failure evidence is preserved; the original PR #59 diagnostic
cause remains unknown, but its missing-event outcome is now reconciled.

## Procedure

The runner, `scripts/activate_soil_corrections.py`, performs:

1. Verify local source bundle, tested migration/proposal hashes and archive bytes.
2. Acquire database credentials once, keep them in memory, open one persistent
   backend, and retain redacted private diagnostics on failure. No automatic retry.
3. Read the exact pending TL-F-0113 event ID and current finding. Require the
   original source fingerprint and expected finding state before deployment.
4. Install the tested PR #60 migration with matching migration-history evidence.
5. In one transaction, require no existing corrections, load the seven pinned
   proposals, reconcile the absent investigation event if necessary, append seven
   acceptance events, recompute dependency-bound coverage, and append a findings
   update. Existing correction state stops the runner for review.
6. Commit and read back source fingerprint, original holds, accepted count,
   effective holds, snapshot currency, county record count and privacy.

Migration deployment is separate from the activation transaction. A failed run
may leave the empty installed layer. A disconnect near commit requires readback,
not blind replay. No existing source geometry or original holds are rewritten.
Qualification remains false; coverage is full only if live computed residual is
exactly zero. The runtime and actual result are retained in the live report.

The merged layer passed full-bundle integration testing in PR #60. This runner
has now executed successfully against production with source, snapshot, finding
and privacy readback. Rerunning it on this accepted cohort deliberately stops;
it is not a mechanism to restore acceptance after later withdrawal.
