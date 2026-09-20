# Osborn FEMA source qualification

This bounded step captures official FEMA evidence for **Osborn, Maine (CID 230595)**.
It loads source evidence and an audit into the existing private Supabase archive.
It does not yet create parcel flood screenings or a statewide flood-zone table.

## What changed since the 2016 study

The [Osborn determination for case 22-01-0871P](https://msc.fema.gov/portal/downloadProduct?productTypeID=LOMC&productSubTypeID=LOMR&productID=22-01-0871P-230595)
revises five panels, adding Zone A and shaded Zone X areas. Its annotated map
pages are part of the evidence. FEMA did **not** revise the study report or
republish the base FIRM as part of this letter. Consequently, the 2016 study's
Osborn “no Special Flood Hazard Areas identified” note is historical context,
not current flood clearance.

| Evidence | Date | Interpretation |
| --- | --- | --- |
| FIS and base FIRM panels | July 20, 2016 | Base publication, still named in the letter |
| Revision letter issued | January 8, 2024 | MSC labels this value `product_EFFECTIVE_DATE_STRING` for this product |
| Revision effective | **May 31, 2024** | Explicit in the letter; agrees with NFHL `EFF_DATE` |
| County NFHL `DBREV_DT` | July 8, 2024 | Database revision metadata, not the letter's effective date |
| County download filename | `23009C_20260717.zip` | Catalog observation; ZIP not downloaded or equated with a legal effective date |

The catalog discrepancy is preserved and explained for this product. No global
rewrite of MSC dates is proposed. The [document review](review.json) records exact
checksums, inspected pages, observations and limitations. LUPC incorporation of
the 2024 FEMA revision remains **UNKNOWN** under TL-F-0109; the 2016 adoption note
alone does not settle it.

## Scope and results

The [effective NFHL service](https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer)
is captured in its native **NAD83 EPSG:4269** coordinates. The FEMA jurisdiction
polygon defines the query envelope and subsequent scope. It is not a parcel
survey. ID-only queries reconcile every feature page, and separately captured
hazard attributes match the geometry responses exactly.

| Layer | Envelope candidates | Within/intersecting Osborn scope |
| --- | ---: | --- |
| Availability | 1 | Hancock coverage polygon covers the jurisdiction |
| FIRM panels | 14 | 13 positive-area intersections: 5 printed, 8 not printed |
| LOMR footprints | 3 | 2 intersections, with applicability caveat below |
| LOMA points | 1 | 0; the candidate is associated with Mariaville |
| Flood-zone polygons | 1,503 | 1,124 valid positive-area intersections; 2 invalid candidates excluded |

The 13 intersecting panel IDs match the 2016 FIS Table 1. The five printed panels
also match MSC's Osborn catalog and the Osborn revision letter: **0437D, 0439D,
0443D, 0606D and 0630D**, each prefixed `23009C`. “Not printed” is a publication
status, not an independent assessment of today's flood risk.

Valid intersecting polygons include 13 Zone A features, with a derived union of
about **5.98 km²** in this jurisdiction scope. Zone X retains three separate
subtypes: 0.2% annual chance, 1% drainage area less than one square mile, and
minimal flood hazard. `SFHA_TF=F` does not mean no flood risk.

Areas use NAD83 / UTM zone 19N (EPSG:26919), with no datum conversion or geometry
repair. Valid polygons cover about 99.997% of the FEMA jurisdiction geometrically;
this excludes invalid features and is **not** regulatory completeness or a
clearance result. Exact counts, unions, membership, diagnostics, runtime versions
and methods are in the DERIVED [report](report.json).

### Defects and unresolved applicability

- **TL-F-0026:** flood-zone OBJECTIDs **27129510** and **27129583** fail ring
  validity. Both are shaded Zone X (0.2% annual chance), reference
  `23009C_LOMC5`, and have bounding boxes intersecting the jurisdiction. Preserve
  them unchanged and compare native Esri representation with official map
  evidence before considering a correction. No area/intersection calculation
  uses these invalid polygons.
- **22-01-0873P:** roughly 481 m² of its footprint intersects the FEMA jurisdiction
  at the boundary. The catalog associates it with neighboring Mariaville. Its
  determination has not been reviewed; this small, boundary-dependent intersection
  does not establish that it legally applies in Osborn.
- **22-01-1010P:** an envelope candidate with no actual Osborn intersection.
- The separate Osborn CID LOMA query returns zero features. FEMA warns that LOMA
  point locations are less accurate; neighboring catalog panel associations are
  not proof of parcel applicability. Do not conclude that no applicable letters
  exist from these queries alone.
- Partial case-ID catalog searches returned empty; community/county searches
  found the products. Empty discovery probes are not absence evidence. Two
  publication/status pages returned HTTP 403 and remain recorded as failures.
- Current county/state ZIPs, a complete revision/preliminary history, statewide
  coverage, site boundaries and LUPC legal reconciliation remain unqualified.

TL-F-0105 and TL-F-0109 receive evidence-linked **in_progress** reviews. The new
geometry finding remains **open/high**. Existing zoning corrections, screening
history and legal-unknown holds remain in place.

## Storage and reproduction

Raw responses stay out of Git. Normal captures have `ingest.source_response`
observations; `ingest.audit_result` contains the report and evidence references.
The native FEMA coordinates are retained in archived response bodies, not inserted
into the older EPSG:4326 geometry-sample table. No database migration is needed.

The original 53,028,043-byte LOMR PDF exceeds the private bucket's 50 MiB per-object
limit. It is archived as three **unchanged byte ranges** (20 MiB, 20 MiB, remainder).
`report.large_document_evidence` holds the original retrieval record, full-file
SHA-256, and ordered offsets, lengths and hashes of all parts. This one PDF has no
ordinary whole-payload `source_response` row; follow the audit's part references.
The original five-product capture log is retained alongside its explicit partition
into normal captures and the large document. No PDF rewriting or lossy compression.

Restore ordinary response files from their content-addressed objects to the paths
in the logs. Restore report `inputs` the same way. Reassemble the large PDF using
`restore(report['large_document_evidence'], downloaded_object_directory)` in
`scripts/investigate_osborn_fema.py`; it validates every part and the full original.
Write those returned bytes to `large-documents/osborn-lomr-document.response`.
Then, with Shapely 2.0.7 and pyproj 3.6.1:

```sh
python3 scripts/investigate_osborn_fema.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/investigate_osborn_fema.py \
  --prepare .local/fema-load --current .local/fema-current-findings.json
```

The current finding input must be a fresh administrative query of TL-F-0105,
TL-F-0109 and proposed TL-F-0026, including `finding_id` and `event_id`; a new
finding must not already exist. Inspect the prepared atomic load, upload its
objects to the private bucket, download the manifest objects, then verify:

```sh
python3 scripts/investigate_osborn_fema.py \
  --verify-download .local/fema-download --prepared .local/fema-load
```

Verification checks every archived object **and reconstructs the original PDF**.
Only then apply the prepared `load.sql`. Replaying that same SQL is idempotent;
new investigations must reread finding tokens and use fresh preparation directories.
Collectors and query manifests preserve exact request details, including the
read-only MSC POST search form. Collector `NON_JSON_RESPONSE` labels are generic;
the investigation explicitly parses and validates the JSON it uses.

## Next bounded step

Investigate TL-F-0026 using native service geometry and the annotated revision
maps, preserving originals. Resolve or explicitly bound the neighboring revision
and legal-adoption dependencies before proposing a parcel screening overlay.
No publisher inquiry has been sent.

## Applied checkpoint

Audit `2f106e1b19fa2b13415741a109d34f1f9dbc4fdb04cf67e77fe882325aebe5ff`
was loaded into Supabase after all **90 archive objects** passed download/hash
verification and the 53,028,043-byte PDF reconstructed to its original hash.
The atomic load records 59 ordinary response observations, one audit, the new
finding, and three evidence occurrences/reviews. The multipart document is an
additional audit-linked capture, as described above.

Readback confirms TL-F-0026 **open/high** (one occurrence), TL-F-0105 **in_progress**
(two), and TL-F-0109 **in_progress** (four), all with `needs_revisit=false` after
this review. This flag describes review currency, not resolution. TL-F-0025
remains resolved. There are 43 findings and 64 historical finding events.

Before/after fingerprints of the complete geometry correction/event tables and
both zoning-screening history tables match. The 2,648 default screenings retain
119 holds, 153 revisions, zero stale defaults and UNKNOWN legal zoning for every
result. The archive remains private and the checked client access remains denied.
The report reproduces byte-for-byte and all 49 Python tests pass. No schema or
accepted geometry change was made.

## Subsequent geometry investigation

The [TL-F-0026 follow-up](../fema-geometry-investigation/README.md) identifies the
two ring-structure problems and archives exact-version alternate decodings without
accepting them. It also records a map/service depiction discrepancy at the smaller
feature. This original qualification report and its exclusion counts are unchanged.
