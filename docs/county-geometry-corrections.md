# County geometry corrections

For county analysis, default to `ingest.effective_county_inventory`, **filtered to
the intended source audit**. Accepted interpretations apply only to the exact
source audit, source ID, OBJECTID and serialized input checksum reviewed. A new
capture or reused OBJECTID does not inherit acceptance. Original county records,
geometry, holds, attributes and provenance remain unchanged and inspectable.
Using an original representation instead of an accepted interpretation in analysis
requires a recorded evidentiary reason and source/correction versions.

## Bounded acceptance

The layer supports twenty-eight exact Piscataquis versions: Blanchard 27334504 and
Atkinson 27249007 / 27291625 (reviewed in PR #30), plus Moosehead Junction
27208875 and Spencer Bay 27336229 (reviewed in PR #33), plus East Middlesex Canal Grant
27304757, T7 R11 WELS 27270812 and T4 R11 WELS 27207268 (PR #36), plus
T4 R13 WELS 27224591, T7 R9 WELS 27320676 and T6 R15 WELS 27243652 (PR #39), plus
T10 R15 WELS 27233351, Chesuncook Township 27314083 and T1 R11 WELS 27316137 (PR #41), plus
Big Moose Township 27257109, T2 R12 WELS 27321193 and Barnard Township 27303187 (PR #43), plus the eleven exact versions in
[PR #46](../research/ten-case-zoning-review/README.md): Beaver Cove 27342226, T7 R10 WELS
27365331, Orneville 27364426, Bowdoin College Grant West 27339379, T5 R14 WELS
27364538, T1 R13 WELS 27324664, T4 R9 NWP 27321394, Shawtown 27366878,
T3 R13 WELS 27261431, T4 R12 WELS 27304932 and Katahdin Iron Works 27358396.
Each group retains pinned audits and an explicit source-hash field. The PR #36, PR #39, PR #41, PR #43 and PR #46 groups
bind both audit references to their respective exact combined investigation,
which contains proposals and separate fixed-candidate cycle/fill checks. This
exception applies only to these listed groups and their pinned audit hashes; the earlier groups
still require their distinct proposal and review audits. The latter twenty-five
corrections also require reviewed source-cycle roles. The database verifies the
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

The [twenty-eight-correction zoning-hold ranking](../research/twenty-eight-correction-ranking/README.md)
is refreshed after activation of the PR #46 proposals. It is bound to the new
snapshot and remains an investigation priority list, not a county screening result.
The historical seventeen-correction ranking is stale and preserved for comparison.
Consumers must integrate this protocol before persisting or using county results:

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

The [three-priority activation](../research/three-zoning-acceptance/README.md)
requires the reviewed five-correction snapshot for its initial atomic load.
A changed baseline or a partially present cohort requires review. Exact historical
full-load replay preserves later correction events and cannot restore an earlier
acceptance after withdrawal.

The [next three ranked proposals](../research/next-three-zoning-priorities/README.md)
retain the eight-correction baseline. T4 R13 and T6 R15 require innermost hole
ownership; T7 R9 also requires a split at an existing hole contact. Their original
proposal status and fixed-source cycle/fill evidence remain preserved; the
subsequent activation is recorded separately below.

The [PR #39 activation](../research/next-three-zoning-acceptance/README.md) requires
the reviewed eight-correction baseline, retains all original evidence and earlier
acceptance versions, and clears only the three reviewed geometry holds.

The [PR #41 activation](../research/latest-three-zoning-acceptance/README.md)
requires the reviewed eleven-correction baseline and clears only the three reviewed
geometry holds. T1 R11's map-index/PDF amendment-date discrepancy remains an
explicit legal-currency follow-up; accepting geometry does not resolve it.

The [PR #43 activation](../research/big-moose-t2-barnard-acceptance/README.md)
requires the reviewed fourteen-correction baseline. It clears only geometry holds;
Big Moose and T1 R11 map-index/PDF amendment discrepancies remain open and do not
inherit legal-currency approval from geometry acceptance.

## Backlog assessment after PR #44

The [county backlog assessment](../research/county-backlog-assessment/README.md)
checks archived-source computational feasibility and conditional coverage gains.
Its batch sizes and stopping criteria are recommendations, not adopted acceptance
policy. Passing those checks does not create a correction proposal or authorize
acceptance. Native/service comparison, official map review and exact-version
acceptance controls remain required; parcel geometry needs its own review.

The [ten-case evidence review](../research/ten-case-zoning-review/README.md) includes
a separately tested two-contact interpretation for Katahdin Iron Works. Its original proposal status is preserved. The
[PR #46 activation](../research/ten-case-acceptance/README.md) now accepts those eleven
exact versions through a tested bounded extension, preserving all seventeen prior
acceptances and all original source records. All seven map-date follow-ups remain
separate from geometry acceptance; later document review cannot establish current
legal zoning without the required supporting evidence.

The [map-date investigation](../research/map-date-investigation/README.md) records
corroborated historical amendments separately from conflicting official dates.
Do not use map-index amendment dates or document edit timestamps as proof of
current legal zoning. Geometry acceptance and date evidence remain independent.

For ZP750 and ZP770, the [signed-decision reconciliation](../research/zp750-zp770-dates/README.md)
now supplies explicit historical `decision_stated_effective_date` values with
source checksum and page provenance. Carry the open filing variance and UNKNOWN
current legal applicability; do not overwrite index dates or clear geometry,
legal or qualification holds from this evidence.
