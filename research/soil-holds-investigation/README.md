# Held soil polygons and county coverage gap

## Result

**DERIVED — seven supported proposals, none activated.** Three held polygons
account for the 41.125706 km² gap in the pinned Piscataquis soil inventory.
The other four held polygons are outside this county boundary. This is evidence
of a geometry interpretation problem in the captured inventory, not evidence
that USDA has no soil mapping for the gap.

| USDA polygon key | Candidate county/gap area (km²) | Proposed interpretation |
| --- | ---: | --- |
| 363859326 | 0 | Split one exact ring touch; retain one hole |
| 363864542 | 0 | Split one exact ring touch; retain one hole |
| 364049010 | 0 | Split one exact ring touch; retain one hole |
| 364075555 | 1.552544 | Split one exact ring touch; retain one hole |
| 364075709 | 32.203145 | Split one touching hole ring; retain ten holes |
| 364075751 | 7.370017 | Split one exact ring touch; retain five holes |
| 364095557 | 0 | Split one exact ring touch; retain two holes |

The original union gap is reproduced exactly: **41,125,705.83461925 m²**.
Subtracting the seven proposed geometries leaves two numerical slivers totaling
**3.2899763023218256e-9 m²**. Floating overlay arithmetic also reports an
intersection total about 0.0000006 m² larger than the original gap. Raw results
are retained: no tolerance, rounding, snapping or silent promotion to full
coverage. The result remains `partial_geometric` under the existing strict rule.
This minute remainder is consistent with floating overlay precision, not a
material unmapped area; that explanation is an inference, not a completeness
certification. Operational coverage is unchanged until proposals are accepted.

## Evidence and method

- The complete prepared bundle passes archive/record verification. Analysis pins
  the bundle, original response rows, WKT hashes and county boundary version.
- A new official SDA query returns WKT and map-unit keys exactly matching all
  seven archived records. USDA SQL reports every native geometry valid, while
  GEOS rejects each exported WKT for a ring self-intersection.
- Each WKT has one twice-visited vertex. The proposal splits only at that exact
  vertex, reassembles oriented shell/hole loops, and verifies that every directed
  source edge and its multiplicity survive. It introduces no vertices or shifted
  segments. The existing wetlands exact-loop decoder is reused; its hash is pinned.
- `make_valid` is an independent equality diagnostic only. It does not construct
  the proposed correction. Tests reject a true crossing and a triple visit.
- Native WKB is separately retained. Six polygons differ from WKT by at most
  1.4210854715202004e-14 degrees per coordinate; one matches exactly. WKB is not
  substituted for the original WKT. Native SQL areas and candidate coordinate
  areas differ by at most 9.674e-12 square degrees; neither is a ground-area metric.
- The alternate stored Web Mercator representation has the same ring-touch
  pattern and decomposes to the same hole counts. It is corroboration only:
  [USDA documents projection-specific caveats](https://sdmdataaccess.sc.egov.usda.gov/documents/AdvancedQueries.html).
- Native SQL containment agrees with **all 28 controls**: seven candidate interior
  points and 21 hole points. These sampled controls support the interpretation;
  they do not establish exhaustive geometric equivalence. Sequential requests
  are not a transactionally consistent source snapshot.
- Metric areas use EPSG:26919 and the pinned county boundary. Originals, proposed
  WKB, raw native responses, controls and diagnostic gaps are separately preserved
  in the private source archive. [Archive verification](archive-verification.json)
  records 15 objects, each downloaded and SHA-256 verified.

[Machine-readable report](report.json) includes exact requests, retrieval dates,
source/candidate hashes, runtime, per-polygon results and raw coverage arithmetic.
TL-F-0113 was previously in progress. The attempted append-only investigation
update returned a database-process error; its outcome is **unverified**, and no
automatic retry was made. See [pending update](finding-update.json) and the
[exact attempted transaction](pending-finding-update.sql). Before replay, read
finding history for that event ID and diagnose connectivity with retained errors.
The last successful source/hold readback remains PR #58. No original records, holds, qualification adapters,
accepted corrections or parcel suitability states are changed by this investigation.

## Recommended next step

Review these exact-version proposals, then implement an append-only soil correction
and acceptance layer before any activation. It must preserve original WKT, bind
acceptance to source/candidate hashes, retain finding dependencies, and recompute
county coverage from accepted geometry. Preserve `partial_geometric` unless the
strict coverage test actually returns zero. Do not silently broaden an existing
zoning or wetlands adapter to cover soil records.

Units, scale, survey/source dates, null attributes and component variability still
need qualification before soil availability is enabled. Site-specific septic and
buildability checks remain limited to parcels selected for purchase investigation.

## Reproduce

Use the project's Shapely/PyProj environment and verified private bundle. Retrieve
private evidence by the content-addressed paths in the archive verification file;
restore the two response/request pairs into an evidence directory. Restoring the
pinned response bytes reproduces this investigation; fresh queries test currency
and will have new retrieval evidence.

```sh
python scripts/collect_soil_hold_evidence.py \
  --representation-request research/soil-holds-investigation/live-representations-request.json \
  --output .local/new-soil-evidence
# Restore archived containment-controls.json, then collect fresh native controls:
python scripts/collect_soil_hold_evidence.py \
  --controls .local/restored-controls.json --output .local/new-soil-evidence
python scripts/investigate_soil_holds.py \
  --bundle .local/county-soils-prepared-final \
  --county-report research/piscataquis-ingestion/report.json \
  --evidence .local/new-soil-evidence --output .local/new-soil-analysis
python -m unittest discover -s tests -p 'test_soil_holds.py'
```

All output directories/files must be new. Changed WKT, membership, source hashes,
control queries or containment results stop the analysis. Source responses and
geometry remain private; public reports contain hashes and summaries.
