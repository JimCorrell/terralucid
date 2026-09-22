# Initial area qualification validation

This implementation adds a read-only consumer over the existing private Supabase
county inventory. It makes no database writes or migrations and does not promote
source rows into qualified parcel screening.

## Coverage of tests

The unit suite exercises:

- Cross-source positive-area overlap preserved as unresolved identity candidates;
  touching records do not become identity matches.
- Intersecting held envelopes, remote holds and unknown extents; affected topics
  withheld independently.
- Accepted effective geometry and exact event provenance.
- Missing zoning, partial coverage and AOIs outside the county.
- Wetlands footprint coverage retained separately from clearance.
- Stale geometry snapshots, changed source evidence and changed finding dependencies.
- Orneville raster evidence retained despite empty digital hazard results, without
  transferring it to another jurisdiction.
- Purchase-candidate-only septic/buildability investigations, with no discovery block.
- Invalid input rejection, preserved finding scopes and exclusive private output files.

A bounded 500 m radius diagnostic AOI, clipped to the archived Orneville civil
boundary around its representative point, exercises the live extractor. This is
an integration-test area, not a selected purchase parcel. Raw AOI/capture/packet
files remain private under `.local/`; only aggregate results are committed.

Initial live attempts were stopped after client stalls; a subsequent connection
probe reported a temporary-credential authentication error. Connection setup is
now bounded to 20 seconds and each database statement to five minutes. The query
also materializes both AOI coordinate representations once and uses envelope
filtering before exact spatial intersections. Final validation is recorded in
`validation.json`; failed attempts are not counted as passing live checks.

Read [the consumer contract](../../docs/area-qualification.md) for use, statuses,
conservative dependency invalidation and remaining applicability limits. This
is a first evidence qualification layer, not a completed county flood inventory,
canonical identity resolver or automated due-diligence clearance.

## Result

**18 unit tests and seven isolated PostGIS integration checks pass.** The archived
Orneville regression uses the actual PR #50 report: product230465A and 27 catalog
letters remain evidence with UNKNOWN parcel applicability and no digital flood
clearance.

**Live validation is blocked.** Supabase returned temporary-login authentication
errors and then a 544 login-role creation connection timeout. No live packet or
live freshness check is claimed. Stalled task clients were stopped. After the
connection recovers, run `capture` for a bounded area and `check` its packet;
inspect topic results before treating live operation as verified. This review
makes no database writes and leaves all existing acceptance/qualification state
unchanged by construction.
