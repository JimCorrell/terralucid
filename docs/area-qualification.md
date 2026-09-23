# Area and source-parcel evidence qualification

The first implementation is a **read-only evidence packet**, produced by
`scripts/qualify_area.py`. It consumes the private county inventory in Supabase.
It does not create canonical parcels, change qualification flags, clear findings,
rank land, or determine offer readiness.

## Inputs and use

Use Python with Shapely 2.0.7 and the existing project environment. The live
adapter also requires the authenticated Supabase CLI and Docker PostgreSQL client.
Temporary database credentials remain in process memory/environment and are never
written to packet files. The optional `TERRALUCID_SUPABASE_CLI` environment variable
selects an installed CLI binary; otherwise the established pinned CLI is used.

Create a private JSON request containing:

- `audit`: the intended county inventory audit SHA-256.
- `snapshot`: the intended existing county geometry snapshot SHA-256.
- `purchase_candidate`: explicit `true` or `false`.
- Either `geometry`: a valid, nonempty, two-dimensional Polygon/MultiPolygon
  GeoJSON geometry in longitude/latitude EPSG:4326 (not a Feature), or
  `source_id` (`ut-parcels` or `organized-parcels`) and integer `object_id`.

An assessment record is a source reference, not a canonical parcel identity.
The source-parcel option defaults to its accepted effective geometry. If that
record is absent or held, extraction fails: provide an independent valid AOI to
investigate its vicinity without interpreting the invalid source geometry.

```sh
python3 scripts/qualify_area.py capture \
  --request .local/request.json --output .local/new-area-packet
python3 scripts/qualify_area.py check \
  --packet .local/new-area-packet/packet.json
```

The output directory must be new. `capture.json` and `packet.json` are written
with owner-only file permissions; keep them in ignored/private storage. They may
contain assessment attributes and private findings. Do not commit raw packets.
The check returns exit code 2 when recomputation/review is needed, and zero only
when its tracked dependencies are unchanged. Database/query failures also fail
rather than produce an empty/qualified result. Credential retrieval has a
60-second deadline, libpq connection attempts a 20-second timeout, statements a
five-minute timeout and the disposable client a six-minute deadline. Query errors
are saved in owner-only diagnostic files under `.local/qualification-errors/`. No new database migration or write
privilege is required; use existing administrative access, not a public API.

## Existing dashboard session (no credential lookup)

When the CLI connection fails, use the already authenticated Supabase SQL Editor.
Do not repeatedly retrieve Keychain credentials or rotate temporary login roles.
Generate the same read-only query locally:

```sh
python3 scripts/qualify_area.py sql --request .local/request.json
python3 scripts/qualify_area.py sql --request .local/request.json --context-only
```

Run the first query in the intended project's SQL Editor as its existing
administrative user. Export the result using **Copy as JSON** into a private file.
Generate the packet without any connection or authentication:

```sh
python3 scripts/qualify_area.py capture --request .local/request.json \
  --from-export .local/capture-export.json --output .local/new-area-packet
```

Then run the context-only query anew and export its result separately:

```sh
python3 scripts/qualify_area.py check --packet .local/new-area-packet/packet.json \
  --from-export .local/context-export.json
```

Both exports must contain exactly one JSON result row. The capture must match
the requested area, audit, snapshot and purchase-candidate flag. Import rejects
missing, malformed or mismatched results; it never falls back to authentication.
An export comparison establishes currency only as of that query. Reusing an old
context export does not establish present currency. Run generated SQL unchanged;
export files are trusted operator-supplied evidence, not authenticated attestations.
Keep exported source evidence private just like directly captured packets.

## Results and limits

Each topic has a status, evidence classification, reasons and relevant source
references. Statuses in this version are `review_required`, `missing`, `stale`,
and `not_requested`. There is deliberately no automatic suitability approval.

| Topic | Implemented checks | Interpretation limit |
| --- | --- | --- |
| Identity | Preserve intersecting records, source hashes, parsed dates, quality flags and cross-source positive-area overlap candidates | Overlap does not merge identities; currentness and legal boundaries remain unresolved |
| Zoning | Effective LUPC intersections, geometric coverage, held envelopes and missing municipal-source warning | Geometric coverage is not legal jurisdiction, applicable rules or current legal zoning |
| Wetlands | Package feature intersections and union coverage of project footprints | Footprint coverage is not wetland completeness; imagery age and site/legal status require review |
| Flood | Route intersecting Orneville civil-boundary evidence to archived county-readiness audits, including scanned FIRM and catalog letters | No digital flood overlay qualified; letters not adjudicated. Other communities remain missing in this adapter |
| Soils and terrain | Explicit source-adapter availability status | No qualified adapter is implemented yet; keep these missing-data tasks separate from suitability |
| Septic and buildability | `not_requested` for discovery, `review_required` for purchase candidates | Neither state establishes suitability; missing site investigations do not block general discovery |
| Access/title | Explicit unknown and purchase-candidate review requirement | Mapped access does not establish rights |

`inventory_intersections_usable` permits only the listed valid-source inventory
intersections when the geometry snapshot is current, the AOI is fully within
county scope and no relevant geometry hold affects it. It does **not** qualify
parcel screening, identity, legal conclusions or an absence claim. Partial
coverage and open findings remain visible even when some intersections are usable.
No arbitrary overlap tolerance, age cutoff, buildability threshold or score is
introduced. Coverage areas use EPSG:26919; full geometric coverage requires zero
computed uncovered area. Mere boundary touches remain distinct from positive area.

## Geometry and findings

Read `ingest.effective_county_inventory` for the exact audit, retaining acceptance
IDs, candidate hashes and event versions. For held native Esri geometry, form
only a bounding rectangle over every finite vertex in EPSG:26919. The SQL returns
compact `held_bounds` derived from those vertices; it does not transmit every
county-wide held ring. Malformed or unsupported extent evidence remains unknown.
Original geometry stays in Supabase with its source hash and provenance. A touching or
intersecting envelope withholds the affected topic's inventory intersections.
A missing/malformed/unsupported extent is conservatively a possible county-wide
block for that source. An outside envelope is not an AOI blocker. No polygon is
repaired, clipped in storage, or accepted by this process.

All unresolved or reopened register findings are carried as **unassessed scope
candidates**, preserving their scope and next action. Source-related findings
and the county finding are linked to individual inventory topics. This first
version does not automate authoritative finding-to-parcel applicability; a
reviewer must determine relevance. It cannot silently clear a finding.

## Dependency currency

Extraction uses one REPEATABLE READ READ ONLY database transaction. The packet
pins its request, capture hash, method hash, geometry snapshot/dependencies, all
county batch IDs, audit/source-observation catalog hashes, and finding event IDs
plus occurrence counts/revisit flags. New evidence or reviews invalidate the
saved packet conservatively, even if later judged unrelated to the AOI. Changes
to the Python method, either SQL file, Shapely/GEOS runtime or the captured
PostGIS runtime also require regeneration.

Check currency before every reuse. The check detects changes to this explicitly
selected audit and registered evidence; it cannot detect an unpublished source
change or certify real-world currency. It does not silently switch to a newer
county batch. If the requested geometry snapshot is stale, capture can retain
an explanatory packet, but affected intersection permissions are false; choose
or record a reviewed current snapshot before recomputing. No saved packet grants
a durable permission after a freshness check; a later check is needed when used
again.

Tests: `python3 -m unittest discover -s tests -p test_area_qualification.py`.
See [validation evidence](../research/area-qualification/README.md).
