# TL-F-0028: national wetlands availability geometry

## Conclusion

A supported **DERIVED representation proposal** preserves every source boundary
segment while making the national Digital availability polygon valid for GEOS.
The original Esri response is unchanged from the previous audit. Its GeoJSON
export has the same boundary segments and attributes, but still fails validation.
This does not establish that the publisher mapped the boundary incorrectly.

The proposal is archived privately and **not accepted or activated**. TL-F-0028
moves from open to in progress; the original overlay hold remains until acceptance
and dependency handling are implemented.

## What caused the failure

The source has 156 rings and 372,409 coordinates including closure points. Five
rings revisit eleven vertices. The [Esri polygon format](https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects/#polygon)
permits vertex touches and describes clockwise exterior rings, counterclockwise
holes and even-odd display filling. The unsplit cycles are incompatible with the
strict ring validity used in the earlier audit.

| Original ring index (zero-based) | Repeated vertices | Resulting simple cycles | Roles |
|---|---:|---:|---|
| 40 | 4 | 5 | One exterior, four holes |
| 66 | 1 | 2 | Two holes |
| 123 | 4 | 5 | One exterior, four holes |
| 134 | 1 | 2 | Two holes |
| 144 | 1 | 2 | Two holes |

The [method](../../scripts/investigate_wetlands_availability.py) separates cycles
only at **exact, twice-visited source vertices**, checks each cycle's validity and
winding, and assigns each hole to its unique containing exterior. It rejects
crossings without repeated vertices, triple visits, degenerate cycles, zero-length
edges, ambiguous holes and invalid assembled topology. It is a bounded proposal
method, not a general ingestion fallback.

## Proposed representation

- **93 polygon exteriors and 74 holes** form a valid MultiPolygon in native EPSG:3857.
- All **372,253 directed segments**, including their multiplicities, are preserved.
- No coordinate moves, snapping, buffering, `make_valid`, segment removal or hole
  filling occurs. Splitting adds eleven closure-coordinate occurrences, not edges.
- Native and exported undirected segment multisets agree. Attributes also agree.
- The candidate's coordinate-space area differs from the publisher's Shape_Area
  by about 0.086 in squared Web Mercator units, at a total near 2.17 × 10¹³. This
  is a numerical consistency check, **not physical acreage** or an accuracy claim.

The candidate is `candidates/status-3.geojson`, hash
`173e3680d2a5474ec7ffbbe460206ddc90374fe21e37c4be3f46e915c0a6e836`.
It retains an explicit EPSG:3857 CRS, like the inspected service export; it must not
be treated as longitude/latitude web GeoJSON. Exact candidate bytes are private.

## Osborn coverage corroboration

All eleven contact vertices are outside the exact prior FEMA Osborn study boundary.
The proposed national polygon covers that study boundary with no uncovered area.
Four valid NWI imagery-source footprints independently provide complete footprint
coverage of the same scope, as recorded in the prior audit. These sources share
publisher lineage; they are not independent field observations.

The original 800×800 image exported by the official availability service for the
requested Osborn extent was visually inspected. It is solid Digital green. Every
pixel also matches the captured renderer's Digital RGBA value `[152,179,64,255]`.
Aspect-ratio adjustment may expand the requested map extent. This is regional
cartographic corroboration, not verification of distant touch vertices or national
boundary accuracy.

The study-boundary transformation from NAD83 to Web Mercator reports 4-metre
accuracy; the exact selected operation is recorded. The FEMA study boundary is
not a legal/surveyed parcel boundary. Coverage calculations depend on its pinned
version. No parcel screening or national physical-area metric is introduced.

**Digital availability is not exhaustive wetland detection.** May 1983 imagery,
source omissions, present-day conditions, legal delineation and applicability
remain qualified. A valid availability geometry does not resolve those issues.

## Findings and downstream handling

- **TL-F-0028 — in progress:** diagnosis and exact-segment candidate preserved;
  acceptance and downstream dependency handling remain pending.
- **TL-F-0117 — in progress:** package/service identity and projection, refresh,
  wider qualification and ground/legal limits remain open.
- **TL-F-0027 — unchanged/resolved** for its eight-record code interpretation.

Continue using existing accepted corrections for their intended sources. This
proposal changes no accepted geometry, correction view or screening. Before using
it as effective coverage geometry, record acceptance tied to the source audit and
candidate checksum, with an append-only review event and dependency checks. A new
source version never inherits this proposal automatically. Do not silently bypass
the original validity hold.

## Reproduction and staging

`probes.json` records requests for native/exported geometry, metadata, format
conventions and the original map image. `report.json` pins response hashes, prior
inputs, transformation, runtime, per-ring decomposition and the candidate checksum.
`review.json` records the visual review and limits. Source responses and candidate
geometry remain outside Git in the private `terralucid-source-snapshots` archive.

Restore every `evidence` response and `inputs` file using its SHA-256 storage key
and recorded path. Then run:

```sh
.local/conflict-venv/bin/python scripts/investigate_wetlands_availability.py
.local/conflict-venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.local/conflict-venv/bin/python scripts/investigate_wetlands_availability.py \
  --prepare .local/availability-load --current .local/availability-current.json
.local/conflict-venv/bin/python scripts/investigate_wetlands_availability.py \
  --verify-download .local/availability-download --prepared .local/availability-load
```

Preparation requires fresh event tokens for TL-F-0028 and TL-F-0117. Independently
download and hash-verify every archive object before applying atomic `load.sql`.
Exact SQL replays preserve later review history. Reproduce from captured evidence;
a fresh live capture is a new version requiring review.

## Applied checkpoint

Audit `73a3f6899afdc374c273a2a69f4ef445926b02b4af6b73351cedfd12a5de7d66`
and registry `5b0871d12a4b81f55107894242cdfed44532b5cbecca88f7f6d8f4df9ca6573f`
are loaded after **19 archive objects** passed independent download/hash verification.
The transaction recorded six source observations, one audit and two append-only
finding reviews/occurrences. The candidate remains **proposed only**.

Readback confirms TL-F-0028 **in_progress/medium**, two occurrences, and TL-F-0117
**in_progress/medium**, four occurrences. TL-F-0027's resolved status and resolution
event are unchanged. All have `needs_revisit=false` after review; this does not
remove remaining holds or qualifications.

The bucket remains private. Complete before/after fingerprints of accepted
geometry, geometry events, zoning screenings and screening revisions match. The
report reproduces byte-for-byte and all **74 tests** pass. No schema change,
geometry acceptance or screening recomputation was performed.
