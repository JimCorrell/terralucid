# County geometry corrections

For county analysis, default to `ingest.effective_county_inventory`, **filtered to
the intended source audit**. Accepted interpretations apply only to the exact
source audit, source ID, OBJECTID and serialized input checksum reviewed. A new
capture or reused OBJECTID does not inherit acceptance. Original county records,
geometry, holds, attributes and provenance remain unchanged and inspectable.
Using an original representation instead of an accepted interpretation in analysis
requires a recorded evidentiary reason and source/correction versions.

## Bounded acceptance

The initial layer supports only the three Piscataquis proposals reviewed in PR #30:
Blanchard 27334504 and Atkinson 27249007 / 27291625. The database verifies the
pinned proposal and review audits, source and candidate bytes, native EPSG:26919,
validity and complete original segment multiplicity. Validity alone cannot qualify
a candidate. Additional sources or interpretations require explicit review and an
extension of this bounded validator. There is no automatic repair.

The effective view exposes original/effective geometry, holds, scope and quality
flags together with source input, candidate, proposal/review and event versions.
Acceptance removes only the geometry hold and `geometry_held` flag, and recomputes
county intersection status. Withdrawal restores the original representation and
hold. All geometry remains DERIVED; legal boundaries remain UNKNOWN and
`qualified_for_parcel_screening=false`. Municipal applicability, parcel identity,
source age, access, septic/buildability and other due-diligence limits remain.

## Review history

Corrections and accepted/withdrawn events are append-only. Administrative reviewers
call `ingest.record_county_geometry_event(payload, expected_event_id)` with a
unique event ID, correction ID, status, actor and evidentiary note. Initial review
expects NULL; subsequent review expects the current event ID. The trigger also
protects direct inserts. The county batch lock serializes reviews and event order;
a stale review fails. Exact historical replay is harmless and does not restore an
older acceptance after withdrawal. Changed replay fails.

There is at most one reviewed candidate per feature in this bounded layer. To
replace one with a different interpretation, withdraw it and design/review an
explicit extension; do not update immutable history.

## Dependencies for downstream analysis

There are no existing county screening results to recompute. Future consumers
must integrate this protocol before persisting or using county results:

1. Use PostgreSQL’s default READ COMMITTED isolation. In the same transaction
   as reading effective inputs, call
   `ingest.record_county_geometry_snapshot(source_audit)`. It locks that county
   batch against correction changes until transaction end. Read/filter the
   effective view for that audit and retain the returned snapshot ID with results.
2. A snapshot records every correction's input/candidate checksum, status and
   latest event ID, including proposals and withdrawals. Historical snapshots
   cannot be rewritten. This conservatively invalidates the county dependency
   set even when a changed feature does not intersect a particular parcel.
3. Before using a result, require
   `ingest.county_geometry_snapshot_is_current(snapshot_id, intended_source_audit)`.
   Missing snapshots, a different source audit, or changed dependencies return
   false. `county_geometry_snapshot_current.needs_revisit` exposes changes within
   the original audit; it cannot choose a new intended audit for the caller.
4. Withdrawal and reacceptance both require review/recomputation. The same candidate
   reaccepted under a new event does not revive an old snapshot. Store new results
   and dependencies without overwriting historical results. For an atomic use or
   publish operation, hold the same batch lock through validation and persistence.

Snapshots do not automatically make an unrelated result table safe; the consumer
must implement these checks. They track geometry review dependencies, not every
future source/analysis dependency. All tables, views and functions are private to
administrative database access; public, anonymous, authenticated and service-role
access is revoked. Database administrators can change database controls, so this
is application history protection, not tamper-proof storage.

See [activation evidence](../research/county-corrections/README.md) and the
[original county evaluation](../research/piscataquis-ingestion/README.md).
