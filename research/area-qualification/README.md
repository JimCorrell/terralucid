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

## Current result — verified through dashboard export

**22 unit tests and eight isolated PostGIS integration checks pass.** Tests include
malformed/empty/unsupported held geometry, compact extrema, export-only operation
without authentication, mismatched exports and changed dependency detection.

A live read-only capture succeeded through the existing authenticated Supabase
SQL Editor session on 2026-09-23 UTC. The successful test uses a small diagnostic
rectangle inside Orneville, rather than the initial 500 m circle. Its request hash,
capture hash, runtime and aggregate results are recorded in `validation.json`.
The executed SELECT was checked against the repository SQL. Raw exports and the
resulting packet remain private. A separate fresh context query on 2026-09-23
matched the packet: `needs_revisit=false`. This certifies unchanged registered
dependencies as of that query, not real-world currentness.

The capture retains 159 source records, including all 155 held records as
conservative extent evidence. Orneville product 230465A and 27 catalog letters
remain available with UNKNOWN parcel applicability. Identity and wetlands allow
bounded inventory intersections with review requirements. Zoning is missing at
this diagnostic AOI; no absence-based clearance is granted. Soils/terrain remain
missing adapters; septic/buildability remain `not_requested` for discovery.
Parcel-screening qualification stays false and offer readiness is not assessed.

## Extraction correction

The original query returned 53,457,544 bytes of held raw geometry even for this
small area. A compact diagnostic query succeeded while the full fetch failed.
Returning conservative coordinate extrema instead of all held rings reduced the
successful browser export to 502,912 characters. This is evidence of an oversized
payload problem; it does not explain every earlier authentication failure.

The SQL examines every raw vertex, rejects malformed or unsupported extent
evidence, and returns only bounds or UNKNOWN. This does not decode or repair the
invalid polygons. Original source records, input hashes, holds and provenance
remain intact in Supabase. Degenerate point/line extents are retained. Tests cover
empty rings, invalid vertices, booleans, numeric overflow and unsupported CRS.

## Earlier failed attempts and remaining connection limit

Earlier direct connections returned EAUTHQUERY errors and a 544 login-role
creation timeout. Subsequent API attempts encountered private-function permission
failure and a 524 gateway timeout. Repeated Keychain requests were stopped at the
user's request. Their history remains in `validation.json`; none counts as a
successful live check.

The verified alternative generates SQL locally and imports the SQL Editor's
**Copy as JSON** results. It does not request credentials, create login roles or
retry authentication. The direct CLI/pooler adapter has not been revalidated.
Use the documented dashboard workflow when that connection is unavailable.

No production database writes, migrations, source repairs, finding resolutions,
acceptance changes or qualification promotions were performed.
