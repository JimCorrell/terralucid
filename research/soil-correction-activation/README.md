# Prepared soil correction activation

**Not deployed or activated.** PR #60 is merged. Automatic approval review blocked
production execution because merge confirmation was not considered explicit
permission to deploy the migration, activate corrections, clear effective holds
and append audit findings. Explicit user authorization is pending.

The 15 private investigation archive objects were downloaded again and hash-verified
([readback](archive-verification.json)). No database credential lookup or database
session occurred during this activation attempt. The source fingerprint, pending
PR #59 finding event and live correction state still require fresh verification.

The prepared runner, `scripts/activate_soil_corrections.py`, performs:

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
exactly zero. The runtime and actual result will be retained.

The merged layer passed full-bundle integration testing in PR #60. This runner is
prepared and syntax-checked; it has not been executed against production. Upon
explicit approval, preserve its live result here and update this status.
