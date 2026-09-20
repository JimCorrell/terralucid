# Osborn geometry acceptance and screening revision

This implements the user-authorized next step after merged PR #11. The reviewed
shell/hole decoding becomes the default **only for the original Osborn zoning
feature version**. No vertex locations change. Evidence remains DERIVED; legal
zoning remains UNKNOWN. See [the layer policy](../../docs/zoning-geometry-corrections.md).

## Results

- **1** reviewed geometry interpretation accepted with immutable event history.
- **153** Osborn screenings recomputed from the effective-geometry view: 152 usable
  assessment geometries and one still unusable assessment geometry.
- **652** positive-area intersections, up from 651. Only one subject has changed
  overlap/coverage metrics; other revisions refresh collection-wide caveats and
  retain geometry dependency provenance.
- **2,495** other screenings remain the default without recomputation. All 119
  preexisting property-correction holds remain in the combined default results.
- All 2,648 historical screenings and all 383 raw zoning features remain intact.

The affected assessment subject is
`9b1ae8c797c956163c5951a71713f7dbb8518d159a03907d001cd6841e201307`.
It gains a P-WL2 intersection of **114,022.995606 m²** (about 11.4 hectares).
Union coverage changes from **0.9895469806502204** to **0.9902479042493062**.
The increase is smaller than the new intersection area because captured zone
polygons can overlap. Coverage is a geometric observation, not a finding of
regulatory completeness, legal boundary accuracy or buildability.

The unresolved native/export projection difference remains explicit in all
revisions' correction limits and in the affected result's flags. The revised
analysis uses the exact original geographic export with the accepted ring roles;
it does not substitute native-coordinate vertices. TL-F-0025 remains in progress
for the projection question rather than being marked wholly resolved.

## Provenance

- Original zoning audit:
  `4c2fb616dbc8ab23c9fe1d04df8ec16cbafbce24fe30543df32269e5e2f0a63c`.
- Reviewed proposal audit:
  `1c37372f5957128a95b3a9d25a7a43286423cbf1ed8831d70bd305b90d933067`.
- Candidate archive checksum:
  `95a8e3fe2fc8b4150bbcc8dee8ae1308afd198debfe40091673a8018335aabb2`.
- Geometry correction:
  `75bedc0deb4d356d66408a2a717d1797c4d2b5112e52dec8f1d12a680a88266f`.
- Initial acceptance event:
  `0be969d74885f4d9ecd70861f198677139477fa8e702880c311a34046c76e3bc`.

`report.json` records method/dependency hashes, runtime versions, all revised
results and the acceptance event used. The administrative export is ignored by
Git and archived privately as `analysis-inputs.json` bytes under its SHA-256 name.
The report pins that checksum, so reproduction does not depend on a future live
view state. Raw third-party sources remain in the existing private archive.

## Prepare and apply

Restore PR #11 evidence and its candidate from the private archive as described
in its investigation README. To restore this step's private export, copy the
checksum object named by `report.json` → `inputs` →
`research/zoning-geometry-correction/analysis-inputs.json` into that ignored path,
verifying its hash first. Never replace an archived export with a newly queried
state and treat it as the same computation.

Use Python with Shapely 2.0.7 / GEOS 3.11.4 and pyproj 3.6.1 / PROJ 9.3.0.
The preparation scripts do not connect to the database.

1. Test migration `20260920060000_zoning_geometry_corrections.sql` in an isolated
   database, then apply it through the linked Supabase migration workflow.
2. Prepare the initial acceptance with
   `scripts/prepare_zoning_geometry.py accept --output NEW_DIRECTORY`.
   Verify its existing private archive objects before applying its atomic SQL.
3. Export the now-accepted view with `scripts/export_zoning_geometry.sql` through
   the authorized administrative connection, retaining the JSON response privately.
4. Read TL-F-0025's current event ID into a private JSON response file.
5. Prepare the recomputation with:

```sh
.local/conflict-venv/bin/python scripts/prepare_zoning_geometry.py recompute \
  --export .local/geometry-live-export.json \
  --current .local/geometry-current-finding.json \
  --output .local/geometry-recompute-live
```

6. Upload the prepared `objects/sha256` directory to the private bucket root;
   download and verify every manifest object before loading database references.
7. Apply the prepared SQL using `apply_prepared_load.py`, or the linked
   administrative `db query --file` route for this approximately 1 MB load. Audit,
   revisions and finding review commit together. Run `check_zoning_geometry.sql`
   afterward.

Acceptance and recomputation are two explicit transactions. Between them the old
Osborn results are visibly stale. If computation fails, they stay stale; the
system does not silently treat old exclusions as current accepted-geometry results.
Exact load replay is safe. A new export after another acceptance/withdrawal needs
a new reviewed computation; this bounded preparer rejects such a state.

For offline reproduction, run the same `recompute` action with the archived input
path and omit `--output` / `--current`. It must reproduce the report checksum.
Historical scripts and migrations have not been edited.

## Tests

- Existing 41 Python tests pass.
- All migrations, historical fixtures, acceptance and 153 revisions were loaded
  into a disposable PostgreSQL 17 / PostGIS 3.5 database. Repeated loads preserve
  counts and history.
- `tests/zoning_geometry_corrections.sql` checks original preservation, candidate
  validity/linework, independent overlap area, private permissions, unchanged
  holds/findings, immutable history, changed candidate/source rejection, stale
  review rejection, withdrawal, dependency invalidation and replay after withdrawal.
- Synthetic mutations run only in the disposable database and roll back.

## Live checkpoint

Verified on 2026-09-20 UTC in Supabase project `yytsjlmbyqhcqfalbjca`:

- Migration `20260920060000` applied. One geometry proposal and one acceptance
  event are stored; original geometry remains invalid, effective geometry valid.
- The two existing acceptance artifacts were checksum-verified before activation.
  All 12 recomputation archive objects were uploaded, downloaded and verified
  before loading revisions.
- Recomputed audit:
  `2bd8bde074188202a176c351d9c225ca0baa083361f10dbd5d0cd0fc3996f6eb`.
  It reproduces byte-for-byte from the archived live export.
- 153 new revisions, zero stale revisions; the 153 historical Osborn results are
  flagged for review. The default view has 2,648 results, zero stale results,
  652 intersections and all 119 existing holds. All legal zoning states are UNKNOWN.
- The original 383 zoning features and 2,648 screenings remain intact, as do
  2,058 source records and 737 assessment candidates.
- TL-F-0025 remains in progress with three evidence occurrences. The findings
  register has 42 findings and 59 review events. Its next action tracks the
  unresolved projection difference.
- RLS is enabled, checked client access is denied, and the source bucket is private.
- The final live-derived prepared SQL passed isolated load/replay and integration
  tests before deployment. The owned test container was removed.

This checkpoint is not ongoing source monitoring or a certification of legal
zoning. Later review changes can make the current default results stale.
