# TL-F-0026: two invalid FEMA polygons

## Conclusion

Both defects are **representation compatibility problems with a supported,
boundary-preserving alternate decoding**. They do not demonstrate incorrect
FEMA boundary coordinates. Two exact-version proposals are archived as DERIVED;
neither is accepted or used by an active screening.

The original records, newly queried GeoJSON, native Esri rings and source
attributes match. Each native ring visits one vertex twice, forming an exterior
loop and an oppositely wound interior loop. The [Esri polygon convention](https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects/#polygon)
permits a vertex touch and specifies ring orientation and even-odd display filling.
The unsplit exported ring fails the GEOS validation used by TerraLucid.
Separating those existing loops into an exterior and a hole produces a valid
polygon with **every original boundary segment and its multiplicity preserved**.

No vertex moved, segment disappeared, hole was filled, or tolerance-based repair
was applied. The method reuses the narrow decoder already tested in the Osborn
zoning investigation; it is not a general ingestion fallback.

## Evidence by polygon

| FEMA OBJECTID | Existing loop structure | Proposed polygon area | Hole area | Map context |
| --- | --- | ---: | ---: | --- |
| 27129510 | 280 input coordinates; 271 exterior / 10 hole coordinates after splitting | 656.75 m² | 8.53 m² | Approximate location is blank in reviewed 0443D revision enclosure; discrepancy remains |
| 27129583 | 605 input coordinates; 267 exterior / 339 hole coordinates after splitting | 1,831.07 m² | 5,020.87 m² | Across 0437D/0439D near Joe Moore Brook, shaded fringe surrounds Zone A |

Counts include each ring's closure coordinate; separate rings repeat the shared
vertex as their closures without adding an edge. Both records are **Zone X,
0.2% annual chance flood hazard**, sourced to `23009C_LOMC5`. Both proposed shapes
are covered by the captured FEMA Osborn jurisdiction and the 22-01-0871P footprint.
Neither footprint coverage nor source citation alone establishes legal applicability.

All coordinates remain in native **NAD83 EPSG:4269**. Areas use **EPSG:26919**,
NAD83 / UTM zone 19N. Locally projected proposals and service-projected native-ring
interpretations differ by less than 0.000001 m in the boundary comparison. This is
numerical consistency between these representations, not ground accuracy.

### Why preserving the holes matters

The earlier captured NFHL neighbors account for both interior areas:

- 27129510's small hole is covered by minimal-hazard Zone X feature **27128999**.
- 27129583's large hole is covered mostly by Zone A feature **27181082**, plus
  about 4.77 m² of another shaded Zone X feature, **27129549**.

Filling the holes would override these source distinctions. A hole in one hazard
polygon does **not** imply absence of flood risk. Neighbor corroboration uses the
same NFHL snapshot and is not independent legal evidence.

### Map evidence and its limits

The original [22-01-0871P Osborn determination and enclosures](https://msc.fema.gov/portal/downloadProduct?productTypeID=LOMC&productSubTypeID=LOMR&productID=22-01-0871P-230595)
were preserved and visually inspected at PDF pages 6–8 (panels 0437D, 0439D and
0443D), including enlarged crops and legends. The [review record](map-review.json)
pins the PDF hash, pages, crop rectangles and locator method.

The larger polygon's regional shape/category context agrees with the map depiction
across the 0437D/0439D seam. Labels, strokes and scale prevent independent
certification of the exact vertex touch. The smaller polygon's approximate
location falls in a blank part of the 0443D enclosure, while current FEMA service
rendering depicts hazards there. **The reason is UNKNOWN.** This is recorded under
TL-F-0105 for map/service reconciliation; blank depiction must not clear the hazard
or justify removing it.

Embedded PDF control coordinates were used only to locate visual crops. The map
identifies NAD83(2011), while the service labels its native data NAD83; their
realization equivalence is not established. No map coordinates were digitized or
substituted into a proposal. Service-generated PNGs provide additional fill
context, not an independent survey or legal map determination.

## Diagnostic impact, not adopted results

A counterfactual calculation adds only the two proposed decodings to the previously
valid flood-zone polygons within the same FEMA jurisdiction. They contribute
**2,487.82 m²**, overlap the valid baseline by **0 m²**, and leave **0 m² geometric
gap** in this calculation. This explains the earlier exclusion gap. It is not a
claim of regulatory completeness, parcel suitability, current LUPC adoption or
absence of risk. The earlier report and all screening results remain unchanged.

## Proposal and finding state

The DERIVED [report](report.json) records each exact original feature hash, source
response, ring diagnostics, candidate hash and private storage key. Proposed
GeoJSON files include explicit EPSG:4269 and `proposed_not_accepted` metadata.
They stay private alongside the source evidence.

- **TL-F-0026:** in progress/high; structural diagnosis and two proposals recorded.
  Original invalid records stay excluded until an explicit acceptance step.
- **TL-F-0105:** in progress/medium; adds the 0443D map/service discrepancy to
  existing source qualification work.
- LUPC adoption and neighboring revision applicability remain unresolved. This
  investigation does not change TL-F-0109's review or any legal-zoning state.

A future acceptance implementation must preserve originals, exact feature/candidate
versions, review history, withdrawal and downstream dependencies. The existing
zoning-only correction table cannot be reused as a FEMA acceptance store. Any
accepted geometry must become the default only for its reviewed source version,
with the map-evidence and legal-adoption qualifications carried into its uses.
New captures must be reviewed again. No publisher inquiry has been sent.

## Reproduction and private loading

Restore raw responses to the paths in their retrieval logs and restore dependencies
listed in the report's `inputs` from private content-addressed storage. The earlier
FEMA report supplies the large PDF's original retrieval metadata and three exact
byte-part references; it remains a multipart archived document, with no ordinary
whole-file source-response row. Restore its bytes to
`research/osborn-fema/large-documents/osborn-lomr-document.response` using the
existing `restore` helper, which validates the parts and original full-file hash.

Using Shapely 2.0.7 and pyproj 3.6.1:

```sh
python3 scripts/investigate_fema_geometry.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/investigate_fema_geometry.py \
  --prepare .local/fema-geometry-load --current .local/fema-geometry-current.json
```

The current file must contain fresh `finding_id`/`event_id` rows for TL-F-0026 and
TL-F-0105. Review the prepared transaction, upload objects to the existing private
bucket, download the manifest objects, and verify before applying `load.sql`:

```sh
python3 scripts/investigate_fema_geometry.py \
  --verify-download .local/fema-geometry-download --prepared .local/fema-geometry-load
```

The verification includes both candidate files and reconstruction of the original
revision PDF. Preparation archives the narrow decoder and other method/input
versions, adds one audit and source-response observations, and appends two
finding occurrences/reviews with optimistic review tokens. Exact SQL replay is
idempotent. No geometry acceptance, screening mutation or schema migration occurs.

## Applied checkpoint

Audit `97dcabac9db9de0f153760755f8fe6e2088d9588c73e98bd58b7505fb7cbd5f3`
is recorded in private Supabase staging with seven new source observations.
All **45 archive objects** passed download/checksum verification, including both
proposals and reconstruction of the original 53,028,043-byte revision PDF.

Readback confirms TL-F-0026 **in_progress/high** with two evidence occurrences,
and TL-F-0105 **in_progress/medium** with three. Both have `needs_revisit=false`
after this review; that is review currency, not issue resolution. Neither proposal
has been accepted. The earlier excluded-source record and screening state remain.

The complete zoning correction/event and screening-history fingerprints match
before and after this load. There remain 2,648 default zoning screenings, 119
holds, 153 revisions and zero stale defaults. The private bucket and checked
client-access denials remain intact. The report reproduces byte-for-byte and all
53 Python tests pass.

## Subsequent map-display investigation

The [0443D follow-up](../fema-map-discrepancy/README.md) explains the default-view
blankness using an opaque PDF MASK layer. Existing hazard graphics are visible
underneath in a controlled diagnostic view. The earlier report is retained;
mask purpose and regulatory interpretation remain unresolved, and neither
geometry proposal is activated by this additional evidence.
