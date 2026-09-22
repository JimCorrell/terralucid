# Acceptance of the three PR #36 zoning proposals

Extend the county validator for exactly these reviewed versions:

| Feature | OBJECTID | Reviewed interpretation |
| --- | --- | --- |
| East Middlesex Canal Grant | 27304757 | Two holes touching at one existing vertex; preserve the separate nested hole's innermost owner. |
| T7 R11 WELS | 27270812 | Shell/hole contact at one existing vertex. |
| T4 R11 WELS | 27207268 | Two separate pairs of holes touching at existing vertices. |

The candidate bytes come unchanged from the [combined investigation](../three-zoning-priorities/README.md). No geometry is regenerated or automatically repaired by this activation. Original source records, holds, coordinates, attributes and provenance remain available.

## Bounded validation

The migration adds only the three OBJECTIDs with the pinned PR #36 audit
`a4b734b5498166be9a802b3cdc4dd08c24567ac10bb9f6764962f187e346d797`.
That combined audit contains both the proposals and separate checks of the fixed
candidates' cycles, hole ownership and even-odd fill. Both audit references point
to that same document for this cohort. Earlier cohorts retain their existing
requirements for distinct proposal/review audits; this is not a general permission
to substitute a proposal for a review.

The validator checks the exact county audit, serialized source input and raw
feature hashes, candidate bytes/properties/CRS, recommendation and recorded
cycle/fill evidence. PostGIS then verifies complete geometry validity and every
original boundary segment with multiplicity. The candidate must remain a DERIVED
EPSG:26919 MultiPolygon. Unsupported IDs or versions are rejected.

## Activation and history

The prepared load acquires the county writer lock before checking the reviewed
five-correction baseline. A changed initial baseline or partial cohort requires
review. The three correction records, initial acceptance events, new dependency
snapshot and TL-F-0029 occurrence/review are committed atomically.

Exact full-load replay is harmless. It verifies immutable correction/event
payloads and cannot restore an older acceptance over a later withdrawal.
Withdrawal restores the original geometry hold; reacceptance creates a new
acceptance-event dependency rather than reviving the old snapshot.

After activation there are **eight accepted exact versions**, **154 effective
zoning holds** and **21 parcel holds** (175 total). Original holds remain 162 zoning
and 183 total. All 120,449 original county rows and the five earlier approvals are
preserved. No county record is qualified for parcel screening.

The five-correction snapshot used by PR #35's ranking and PR #36's coverage scenario
becomes stale. Those historical results remain archived; refresh the ranking
against the new eight-correction snapshot before selecting further priorities.
Do not treat a historical scenario as current coverage without checking its
intended source audit and dependency snapshot.

## Tests and evidence

The disposable PostGIS fixture restores all 120,449 original records and the
audit/event chain through PR #36. The integration runner checks:

- The previous validator rejects all three new versions.
- Fresh inserts reject changed source input, audit or candidate bytes, missing or
  altered cycle/fill evidence, invalid geometry, and changed boundary segments.
- A changed initial baseline blocks the complete activation without leaking writes.
- All three authentic candidates activate and exact full-load replay adds no events.
- The five existing approvals are unchanged; the previous ranking snapshot is stale.
- Withdrawal/reacceptance, immutable history, stale review/snapshot rejection,
  source-scope binding, privacy and qualification controls remain effective.
- Concurrent snapshot capture waits for a pending correction review and sees its
  committed result; a concurrent stale reviewer is rejected.
- Historical replay after newer reviews preserves the later events.

Corrupted audit/candidate fixtures and synthetic events are used only in the
disposable database, never in Supabase. See `test-results.json` for executed checks,
runtime versions, test hashes and the exact prepared-load checksum.

The [activation report](report.json), [archive manifest](archive-manifest.json),
[baseline](baseline.json) and [finding review](finding-review.json) preserve the
version chain. Candidate and original input bytes remain in the private archive.
The investigation's evidence and map limitations remain applicable: valid geometry
does not establish legal boundaries, applicable zoning, access, septic suitability
or buildability. TL-F-0029 remains in progress for the remaining county deficiencies.

## Reproduction

Restore the original checksum-matched county transfer and proposal artifacts.
Prepare the load with:

```sh
python scripts/prepare_three_zoning_acceptance.py \
  --output .local/new-three-acceptance-load \
  --county-transfer .local/county-copy-load/load.sql
```

In a **disposable** PostGIS database, restore migrations through `20260921060000`
and the archived county/review/activation loads through PR #36. The runner applies
the new migration itself, after confirming the previous validator rejects the
new cohort:

```sh
python tests/run_three_zoning_acceptance.py \
  --container DISPOSABLE_CONTAINER --database county_test \
  --prepared .local/new-three-acceptance-load \
  --report research/three-zoning-acceptance/test-results.json
```

Upload prepared objects, independently download/hash-verify them, apply the tested
migration and then the exact prepared load. Verify with
`scripts/check_three_zoning_acceptance.sql`. Schema administrators can bypass
controls; this is application history protection, not tamper-proof storage.

## Live checkpoint

Migration `20260921070000` and all three exact acceptances are applied in Supabase.
All 14 private archive objects passed independent download/hash verification.
[Live verification](live-verification.json) confirms the eight acceptances,
154 zoning / 175 total effective holds, unchanged original fingerprints and prior
five approvals, and zero qualified rows. The tenth TL-F-0029 occurrence/review
records this activation; other finding events are unchanged. The old five-correction
snapshot is stale and the new snapshot is current. No synthetic test events were
sent to Supabase. See the [checkpoint](checkpoint.json).
