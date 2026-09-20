# Accepted zoning geometry interpretations

After PR #11, the user authorized activating its reviewed Osborn interpretation
and recomputing dependent screenings. This layer accepts **one exact-version
DERIVED decoding**, not a legal boundary correction. The original source and
historical results remain unchanged. Alfred's separate proposal is unaffected.

## Default geometry and results

Use `ingest.corrected_zoning_feature` for this zoning source's effective geometry.
It retains the original feature/geometry, source audit and observation, proposal
audit, candidate checksum, acceptance/withdrawal event and unresolved limits.
An accepted interpretation supplies `effective_geometry` / `effective_geojson`;
proposed or revoked interpretations retain the original and its validity state.
Always select the intended source audit version. Another capture with the same
OBJECTID does not inherit acceptance.

Use `ingest.zoning_screening_latest` for the default result **per original audit
and subject**. `source_audit_sha256` identifies the source cohort;
`result_audit_sha256` identifies the computation. Review `needs_revisit` before
using a result. A stale latest result remains visible and stale; it never silently
falls back to an older, more favorable result.

`ingest.zoning_screening` preserves all 2,648 original screenings.
`ingest.zoning_screening_revision` adds 153 immutable Osborn revisions. The other
2,495 originals remain the default for their unchanged subjects. All Osborn
results are refreshed because the original invalid-zone warning described the
whole captured collection, even though only one subject gains an intersection.
The existing invalid assessment geometry remains unusable.

An analytical override to accepted geometry needs an explicit evidentiary reason,
versions and dependency history. The current revision importer enforces the
accepted interpretation; it has no override shortcut. Raw inspection for auditing
is always available.

## History and guards

- `zoning_geometry_correction` stores the original feature text/checksum and the
  exact proposed candidate bytes/checksum, with a foreign key to the immutable
  source audit/OBJECTID. Validation compares both to the archived PR #11 report,
  checks validity and unchanged boundary linework, and retains its caveats.
- `zoning_geometry_event` records immutable acceptance or withdrawal, actor and
  reason. `record_zoning_geometry_event(payload, expected_event_id)` locks the
  correction and rejects stale reviews. Exact event replay cannot undo a later
  withdrawal; conflicting reuse of an event ID fails.
- Each revision retains its original source input, parent audit, method report,
  source holds/findings and the complete geometry review-event dependency map.
  Inserts lock the source collection/reviews and reject changed input or geometry
  dependencies. Historical exact replay is a no-op even after withdrawal.
- Source changes and geometry review changes flag dependent revisions. Original
  Osborn screenings lack review dependencies and are conservatively flagged after
  a geometry proposal/review exists, including after withdrawal. They are not
  overwritten or automatically declared current again.

The bounded implementation supports one immutable proposal per original zoning
feature and revisions of the existing Osborn UT screening cohort. Additional
proposal alternatives, other cohorts and new source deliveries require explicit
implementation/review. It does not automatically discover new publications or
recompute results after future review events.

All new tables have RLS, with client-role access revoked on tables, views,
sequences and functions. Administrative access performs these bounded loads.
These are history-preservation controls, not protection against an administrator
who deliberately bypasses them.

## Evidence limits

The exact EPSG:4326 export's vertex locations and boundary segments are retained;
the self-touching ring is expressed as an exterior and a touching hole. Acceptance
keeps the **DERIVED** evidence state. The later [projection investigation](../research/osborn-projection/README.md)
reconciles the approximately one-metre difference: the observed service output
matches inverse ESRI:108190, whereas the local automatic projection used a
different NAD83/WGS84 operation. TL-F-0025 is resolved for this reviewed version.
No coordinates, accepted interpretation or screening metrics are changed.
Historical reports retain their original unresolved-projection caveat; consult
the later finding review for its disposition. Numerical agreement does not
establish survey accuracy. Future native-coordinate or precision-sensitive
analysis must qualify its transformation explicitly. Authoritative currency and
map-omitted protections remain with TL-F-0109. Legal zoning and buildability
remain UNKNOWN.

See [the activation report](../research/zoning-geometry-correction/README.md) for
results, preparation and verification.
