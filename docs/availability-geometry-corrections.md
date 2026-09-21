# Reviewed NWI availability geometry

After PR #22, the user authorized the exact reviewed Digital availability decode.
This is a bounded interpretation of national Wetlands_Status OBJECTID 3, with one
coverage calculation for the archived FEMA Osborn study boundary (CID 230595).
It does not load statewide wetlands features or create canonical parcels.

## Default and dependencies

Use `ingest.effective_availability_geometry` for the exact source audit and payload.
Require `geometry_hold=false`; an unaccepted or revoked interpretation returns
NULL geometry. Use `ingest.availability_coverage_latest` for the intended subject
version and require `needs_revisit=false`. Never treat a stale result as current
or fall back silently to an older result. Raw inspection remains available;
overriding the accepted interpretation requires a recorded evidentiary reason.

The immutable candidate retains its source/proposal audits, raw payload checksum,
exact candidate bytes/checksum, DERIVED classification and original review. The
`limits` field preserves that historical proposal review, including its then-pending
acceptance wording; current acceptance comes from the event and effective view.
The original source response and proposal are preserved in the private archive.

Coverage records retain source/candidate versions, exact study-boundary bytes and
audit, method hash, acceptance event and PostGIS runtime. PostGIS computes
`ST_Covers` after transforming the study boundary from EPSG:4269 to EPSG:3857.
The study boundary is not a legal/surveyed parcel boundary. Coordinate-system
transformation and source accuracy qualifications continue to apply.

## Reviews and stale results

Append accepted/revoked events through `ingest.record_availability_event`, with the
expected current event ID. Withdrawal blocks new coverage and marks existing
results stale. Reacceptance also leaves old results stale: a new computation audit
and result must reference the new event. Exact historical replays preserve later
reviews and do not reactivate geometry. Conflicting replays are rejected.

New source or candidate versions cannot inherit this acceptance. The initial
migration explicitly permits only the reviewed source/proposal and Osborn subject;
expanding that scope requires a reviewed change. No automatic refresh is configured.
Staleness tracks acceptance events, not newly published upstream data discovery.

Tables and views are private to administrative ingestion, with RLS and client-role
privileges revoked. Immutability and validation protect normal ingestion paths;
a database administrator can bypass these controls. SQL lifecycle tests belong
only in a disposable PostGIS database.

## Interpretation limits

Digital availability means mapped inventory availability. Wetland completeness,
present-day conditions and legal applicability remain UNKNOWN. May 1983 source
imagery remains material despite newer package release dates. Availability does
not establish absence of wetlands, P-WL applicability, septic suitability or
buildability. Package/service identity and projection questions remain in TL-F-0117.

See the [acceptance checkpoint](../research/availability-acceptance/README.md) and
[original investigation](../research/wetlands-availability/README.md).
