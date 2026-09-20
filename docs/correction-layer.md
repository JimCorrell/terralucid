# Reviewed source corrections

The user authorized implementing the correction layer after merging PR #7. This
bounded layer accepts its historical municipality and identifier interpretations
in private Supabase staging. Acceptance is a workflow decision: the corrections
remain **INFERRED**. It does not establish current property information, legal
boundaries, title, or canonical parcel identity.

## Contents

- `ingest.correction_source`: 2,325 immutable Sweden/Alfred source features from
  the conflict investigation, exact feature checksums, snapshot identity, archived
  response references, original proposals and exception holds.
- `ingest.correction_event`: append-only acceptance/withdrawal history. Initially
  2,324 proposals are accepted, covering 2,324 GEOCODE changes and 1,595 STATE_ID
  changes. Each event records its actor and reason.
- `ingest.corrected_source`: original feature alongside effective properties,
  current correction status, evidence, candidate links, holds and related finding
  IDs. A withdrawal restores the original properties in this view.

Alfred's audit records do not need to exist in the earlier `source_record` load.
Their archived observations provide provenance directly. The earlier 2,058 source
records and 737 assessment candidates are untouched. All geometries stay in their
original source form; the alternate interpretation for Alfred OBJECTID 439584 is
still pending. That record has no accepted field correction.

All **119 records with holds** stay visible: 75 Sweden assessment mismatches,
5 Sweden shared assessment candidates, 38 Alfred records lacking a unique
identifier candidate, and the one invalid original geometry. The first 118 retain
accepted municipality corrections. An accepted correction does not clear a hold.
Assessment relationships remain `candidate_only`, even with a corrected identifier.

Related findings remain in their existing states. Follow `related_finding_ids` to
`ingest.finding_current` for current status and next action; these are shared
investigation references, not a claim that every issue applies to every record.
The source-freshness finding TL-F-0024 remains open. The stored hold list covers this
review's exceptions; an empty list does not certify a clean or offer-ready parcel.

## Default for downstream analysis

Use `ingest.corrected_source.effective_properties` as the default interpretation
for records in this layer. Wherever an accepted correction applies, downstream
filters, jurisdiction groupings, candidate matching and derived analyses must use
that corrected value. Unchanged fields retain their source values. Raw evidence
remains available for provenance, comparison and evidentiary review.

A deliberate analytical override to a raw value requires a recorded evidentiary
reason, supporting references, affected fields and exact source/correction
versions. Merely inspecting the original for audit does not constitute an override.
If new evidence warrants withdrawing a correction generally, append a review event;
do not silently bypass acceptance or overwrite the source.

Every derived result must retain the source snapshot and feature checksum, audit
and correction IDs, and the acceptance event ID used, along with applicable
provenance, evidence classification, holds and findings. Accepted corrections
remain INFERRED. A later review does not rewrite prior analytical results: dependent
results need explicit recomputation or review when their interpretation changes.

When no accepted correction exists, the effective view retains the raw properties
and exposes its proposed, held or revoked status. Records outside this layer use
their versioned source interpretation and existing quality flags. Neither case
implies that the raw values are verified or suitable for every calculation; a
blocking unknown must propagate as unknown or prevent the affected calculation.
New source snapshots never inherit these corrections automatically.

This is the required policy for downstream consumers as they are implemented.
The current database view provides the effective values and history; it does not
yet enforce consumer routing, record analytical overrides or invalidate derived
results automatically. Those controls belong with the downstream analysis work.

## Safe use

Query this view explicitly for the intended `audit_sha256`, `source_id`,
`source_snapshot_sha256`, and `source_feature_sha256`. Do not join by OBJECTID,
STATE_ID, or GlobalID alone. Do not transfer a correction to another delivery or
use this historical view as a current-source feed. A new snapshot needs a fresh
review, even when business identifiers are unchanged.

```sql
select object_id, raw_feature->'properties' as original_properties,
       effective_properties, correction_status, correction_evidence_state,
       holds, proposal->'assessment_candidate' as candidate, related_finding_ids
from ingest.corrected_source
where audit_sha256 = '6e08cd827867fbf816d94c82bd22b44d6889caf8936726f144bd00307de52e8f'
  and source_snapshot_sha256 = '2f1e07f265bb13f2584ccbd0e8dc1f9a80192d56dc28910b0e9980bfc126a5bb'
  and source_id = 'organized-parcels';
```

For later reviews, call `ingest.record_correction_event(payload, expected_event_id)`
through an authorized administrative connection. Payload keys are `event_id`
(a new SHA-256 identifier), `correction_id`, `status` (`accepted` or `revoked`),
`actor`, and `note`. Supply the current view's event ID as the expected value.
Concurrent stale reviews fail; exact event replays are no-ops. Replaying the initial
load after withdrawal does **not** reactivate the old acceptance. Original records
and events reject updates/deletes. Administrators can bypass database controls;
this preserves history rather than making it tamper-proof.

## Prepare, validate, apply

Use the existing municipal archive preparation and verified download described in
[the municipal report](../research/municipal-corroboration/README.md). Fresh clones
must restore private evidence first. These example paths refer to that preparation:

```sh
python3 scripts/prepare_correction_layer.py --output .local/correction-load \
  --archive-prepared .local/municipal-load-final
npx --yes supabase@2.117.0 db push --linked --dry-run
npx --yes supabase@2.117.0 db push --linked
python3 scripts/apply_prepared_load.py --prepared .local/correction-load \
  --download .local/municipal-download --project-ref yytsjlmbyqhcqfalbjca
npx --yes supabase@2.117.0 db query --linked --file scripts/check_correction_layer.sql
```

The preparation pins the reviewed report checksum, validates captured source and
assessment bytes, checks source and candidate versions, and prepares one atomic
transaction. No new source download is performed. SQL also verifies proposals
against the stored audit, field preconditions, feature checksums and exception
holds. Replays compare existing contents and preserve later review history.

All new tables use RLS; tables, view, sequence and review function deny client-role
access. No public API, scheduler, canonical parcel model or geometry repair is added.

For local integration testing, use a disposable PostgreSQL 17/PostGIS 3.5 database
with Supabase client roles and PostGIS in `extensions`. Apply the migrations and
existing prepared source, coverage, bounded, conflict, municipal and correction
loads in that order. Replay the correction load, then run
`tests/correction_layer.sql`; its synthetic reviews roll back. Never run that test
against the live project. Run the Python suite with the existing conflict-analysis
requirements installed.

## Deployment verification

Verified in the selected Supabase project on 2026-09-20 UTC:

- Migration `20260920040000` applied; the correction load committed atomically.
- 2,325 snapshot records, 2,324 accepted proposals/events, and one entirely held
  record. Effective properties contain 2,324 municipality-code changes and 1,595
  identifier changes; all 119 records with holds retain them.
- Original staging remains at 2,058 source records and 737 assessment candidates.
  The findings register remains at 41 findings and 54 review events.
- New tables have RLS enabled; client access to tables/view and the review function
  is denied. The previously downloaded 44-object municipal archive passed checksum
  verification before loading.
- 29 Python tests passed. Disposable PostgreSQL tests passed the repeated loads,
  withdrawal/reacceptance, replay-after-withdrawal, stale review, changed snapshot
  and feature, preserved holds, excluded invalid geometry and immutable-history
  checks. Synthetic reviews were not run against the live project.

These observations describe this deployment, not ongoing monitoring or evidence
that source information is current.

## Separate zoning geometry interpretation

The [zoning geometry layer](zoning-geometry-corrections.md) now provides accepted
geometry defaults and immutable dependent screening revisions for the reviewed
Osborn source version. This is separate from the property correction tables
described above; Alfred's geometry proposal is still pending.
