# Soil acceptance layer implementation

Implements the [acceptance policy](../../docs/soil-geometry-acceptance.md) for the
seven exact [PR #59 proposals](../soil-holds-investigation/README.md).

This PR adds the migration, credential-free proposal preparation and full-bundle
PostGIS integration tests. No live migration, proposal load or acceptance was
performed. The PR #59 finding-update outcome remains unverified and must be checked
by event ID before replay; this work does not repeat that access attempt.

The isolated test loads all 38,237 original records, stages seven proposals without
activation, then exercises acceptance, withdrawal and reacceptance. It verifies
source fingerprints, dependency invalidation, changed-replay rejection, strict
coverage calculation and private access. Acceptance events in the test are fixtures
inside a disposable local database, not live approvals.

- [Prepared proposal identities](preparation.json)
- [Integration results and recomputed test coverage](integration-tests.json)

```sh
python tests/check_soil_acceptance_sql.py \
  --deployment .local/soil-staging-deployment \
  --proposals .local/soil-acceptance-prepared \
  --output .local/new-soil-acceptance-tests.json
```

The full source bundle and pinned boundary are required. The test uses a local
Docker PostGIS database, not Supabase or Keychain. Outputs distinguish test events
and coverage from production state.

## Observed test result

All seven integration check groups passed. The isolated PostGIS/GEOS runtime
returned **0 m² uncovered** after test acceptance of all seven proposals, so its
strict result is `full_geometric`. PR #59's Python overlay returned microscopic
positive slivers; the algorithms/overlay order and runtimes differ. Neither result
is substituted for the other. Live activation must recompute and retain its own
runtime/result; geometric coverage never establishes completeness or suitability.
The original 38,237-row fingerprint, seven original holds and original analytical
geometries were unchanged throughout the tests.
