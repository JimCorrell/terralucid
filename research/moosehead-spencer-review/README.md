# Review of the Moosehead Junction and Spencer Bay proposals

Following merged PR #32, review the **fixed candidate bytes** against the original
county source and archived service/map evidence. **Both proposals are supported
for exact-version acceptance as DERIVED interpretations. Neither is activated.**

| Candidate | Exact shell cycles | Exact hole cycles | Original faces checked | Conclusion |
| --- | ---: | ---: | ---: | --- |
| Moosehead Junction 27208875 | 119 | 153 | 272 | Supported |
| Spencer Bay 27336229 | 150 | 138 | 288 | Supported |

## Review method and findings

The review verifies the proposal audit, method and every recorded input checksum,
including original county pages, service responses, maps and candidate bytes.
Original county records equal the native EPSG:26919 service features, including
attributes. Candidate identity, source hash, evidence state, proposed status and
CRS must match exactly. No candidate is regenerated or rewritten.

A separate traversal-stack algorithm extracts closed cycles as source vertices
recur. It does not call the proposal splitter or use its reported cut indices.
Every source cycle must be simple and retain its full segment multiset. Clockwise
source cycles must match candidate exterior rings; counterclockwise source cycles
must match candidate interior rings. The two-hole contacts must retain one common
candidate shell owner. This checks all **560 cycles**, not only the five split
source rings. All checks pass.

The previously tested ray-crossing review is then rerun across all **560 original
faces**. Both fixed candidates preserve the full segment multiset and even-odd
filled area, with zero symmetric-difference area. This rerun is a consistency
check using the existing algorithm; the cycle walk is the new independent check.
Both still use GEOS topology operations, so this is not an independent geometry
engine, publisher confirmation or survey evidence.

Six targeted tests cover complete cycle/owner/fill agreement, a rotated ring
start, and rejection of reversed source roles, a removed hole, changed coordinates
and unsupported walks. The two authentic feature reviews pass separately.

The proposal audit's map review, source dates and legal caveats remain in force.
No fresh source retrieval or map-currency determination is claimed. Service
GeoJSON remains invalid; it does not independently authorize these interpretations.
The prior **10.2247 km²** coverage scenario remains tied to its recorded PR #31
baseline and is not recomputed or promoted to current coverage here.

## Acceptance work still required

The deployed county validator currently accepts only the original three reviewed
features. Extend it narrowly for these two exact source/candidate/proposal/review
versions; do not remove the existing three features' audit pins or broaden the
validator to arbitrary valid geometry. The new proposal report uses
`source_feature_sha256`; the older report uses `county_feature_sha256`. Validate
the correct pinned report structure for each cohort rather than silently relaxing
source checks.

Before activation, test all five features, altered source/candidate rejection,
withdrawal/reacceptance, stale expected-event checks, replay and private access.
Preserve original source rows, holds and existing correction history. Capture a
new dependency snapshot; adding these corrections must make older county snapshots
require revisit. Scope must be recalculated from accepted geometry.

If subsequently accepted, effective zoning holds would change **159 → 157** and
total effective holds **180 → 178**. Original holds remain **162 zoning / 183 total**;
the 21 parcel holds and other county qualifications remain. Geometry acceptance
cannot qualify parcel screening or establish legal zoning, access or buildability.

## Tracking and reproduction

TL-F-0029 remains in progress with the bounded validator extension/activation as
its next action. This review appends an audit, occurrence and finding event only;
there is no migration, source mutation, correction event or screening calculation.
Restore the proposal archive's checksum-pinned inputs and use the runtime versions
in `report.json`:

```sh
python scripts/review_moosehead_spencer.py
python -m unittest discover -s tests -p 'test_moosehead_spencer_review.py'
python scripts/prepare_moosehead_spencer_review.py \
  --output .local/moosehead-spencer-review-load
```

Upload and independently download/hash-verify the prepared archive before applying
its metadata transaction with `apply_prepared_load.py`. Check the expected finding
event first. Read-only deployment verification is in
`scripts/check_moosehead_spencer_review.sql`; checkpoint and live readback record
the completed deployment.

## Deployment checkpoint

All **34 archive objects** passed independent download/checksum verification. The
review audit and TL-F-0029 occurrence/event are loaded in Supabase. Readback confirms
unchanged fingerprints across all **120,449 original county rows**, both proposals
still held, **159 effective zoning / 180 total holds**, and unchanged existing
acceptances and dependency snapshot. Other finding events are unchanged.

The first broad readback timed out. The completed check counts effective holds
within the 183 originally held rows, since this layer can only remove those holds;
original fingerprints still cover the entire cohort. No data mutation was used
to address the timeout. `checkpoint.json` and `live-verification.json` record the
verified result.
