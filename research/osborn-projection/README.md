# TL-F-0025: Osborn projection discrepancy

## Finding

**DERIVED; resolved for the reviewed source version.** The approximately 1.022 m
native/export discrepancy is explained by different NAD83/WGS84 datum operations.
The accepted ring interpretation from PR #12 and its coordinates remain unchanged.

All 345 coordinate occurrences in LUPC OBJECTID **27232839** were compared:

| Comparison | Maximum separation |
| --- | ---: |
| Default service WGS84 vs explicit service transformation 108190 | Exactly equal coordinates |
| Service WGS84 projected locally with the automatic operation vs native | 1.022404 m |
| Service WGS84 returned to native with explicit ESRI:108190 | 0.000000346 m |
| Native transformed using inverse ESRI:108190 vs service WGS84 | 0.000000020 m |
| Explicit service 1188 vs default service WGS84 | 1.022509 m |
| Explicit service 1515 vs default service WGS84 | 0.013526 m |

The observed service default is numerically equivalent to inverse
**ESRI:108190, WGS_1984_(ITRF00)_To_NAD_1983**. The automatic local operation uses
**EPSG:1188, NAD83 to WGS 84 (1)** in the opposite direction when returning to
UTM 19N. Explicit 1188 and 1515 service requests distinguish these alternatives.
The NAD83 geographic control also agrees with the native inverse projection.
Distances between geographic outputs are compared in the same local projected
frame. Exact pipelines and authority definitions are in [operations.json](operations.json).

Submicrometre numerical closure is **not real-world positional accuracy**.
Metadata exposes transformation support but does not identify the server's
selected default operation. This conclusion describes observed output, not
verified hidden server configuration. No global transformation policy is adopted.

## Scope and preserved evidence

This is one unchanged Osborn polygon, not a statewide comparison. Native and
geographic features, including attributes and coordinate order, match the PR #11
captures. Layer metadata matches at the beginning and end of this capture.

The original invalid GeoJSON, native representation, official-map review,
accepted interpretation, acceptance event and all screening results are preserved.
PR #11's map evidence remains relevant: it supports regional context but cannot
independently establish the exact boundary or point-touch topology. No new map
interpretation or coordinate correction is proposed here.

TL-F-0025's original representation defect was addressed in PR #12; this review
explains its remaining projection discrepancy. Historical reports and immutable
correction limits retain the caveats known when written. Consult this later
finding review for the projection issue's disposition. TL-F-0109 continues to
track legal currency and map-omitted protections. Legal zoning and buildability
remain UNKNOWN. Future source versions and precision-sensitive/native-coordinate
analyses need their own explicitly qualified transformations.

## Reproduction and private archive

[report.json](report.json) records retrieval provenance, source checksums,
operation comparisons, runtime/database identity, limits and proposed review.
Public files contain aggregate diagnostics and CRS parameters; raw responses
remain ignored locally and archived in the existing private Supabase bucket.
The collector's generic `NON_JSON_RESPONSE` label describes document capture;
the investigation separately parses and validates each geometry response.

With the exact archived responses restored to their logged paths, use pyproj
3.6.1 / PROJ 9.3.0 (the original investigation environment):

```sh
python scripts/investigate_osborn_projection.py
```

The method rejects changed source versions, incomplete queries, wrong CRS,
attribute drift, unexpected ring structure, changed metadata, failed explicit
108190 agreement and failed numerical control comparisons. Authority operations
use latitude/longitude axes; the UTM CRS transformers explicitly use x/y axes.

To prepare the append-only review, first retrieve the current TL-F-0025 event ID
through the authorized administrative connection, then:

```sh
python scripts/investigate_osborn_projection.py \
  --prepare .local/projection-load \
  --current .local/projection-current-finding.json
```

Upload the prepared objects to the private bucket, download and checksum-verify
all manifest objects before applying `load.sql`. The transaction adds an audit,
one occurrence and one optimistic-lock finding event. It has no geometry or
screening writes. Exact replay is idempotent. No schema migration is needed.

## Applied checkpoint

Audit `fa5ba2a0745ce3ba5ba1ba8e8f789e1e3a5eb2051900ec44ab2d4a163ed6f5d7`
is archived and recorded in Supabase. All 19 archive objects were downloaded and
checksum-verified before loading. TL-F-0025 is **resolved**, with four evidence
occurrences and `needs_revisit=false`; earlier reviews remain available.

Before/after fingerprints of the complete geometry correction/event tables and
both screening-history tables are identical. The live checkpoint retains one
accepted interpretation, 2,648 original screenings and 153 revisions, with 2,648
current default screenings, 652 intersections, 119 holds and no stale defaults.
All 2,648 legal-zoning states remain UNKNOWN. The bucket remains private, RLS is
enabled and client access remains denied. The report reproduces byte-for-byte;
all 41 existing Python tests pass.
