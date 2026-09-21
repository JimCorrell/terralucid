# Piscataquis held zoning investigation

Following merged PR #28, rank all **162 held zoning features** and investigate a
bounded first group. Original county audit:
`fad71a48eab71fce398a8e51bd3fb4e9b7169e1d0e0f2a6ed91b1a18a5fad259`.

## Findings

Fresh native EPSG:26919 responses retain the original coordinates and selected
attributes for all five investigated features. Service GeoJSON exports use the
same native coordinate system and retain the same boundary-segment multisets.
No projection, snapping, clipping, simplification or automatic repair is used.

| Feature | Source map / zone | Result | Proposed additional usable county area |
| --- | --- | --- | ---: |
| 27334504 | Blanchard / P-SL2 | One self-touching ring can be expressed as its existing shell and touching hole | 8.5693 km² |
| 27208875 | Moosehead Junction / P-SL2 | Three nonsimple rings; one fails the supported nested-touch interpretation | No proposal |
| 27336229 | Spencer Bay / P-SL2 | Two nonsimple rings; one fails the supported nested-touch interpretation | No proposal |
| 27249007 | Atkinson / M-GN | One self-touching ring can be expressed as its existing shell and touching hole | 62.4672 km² |
| 27291625 | Atkinson / P-SL2 | Ten holes need the innermost containing shell; candidate equals the valid service GeoJSON | 8.1962 km² |

The three **DERIVED proposals are not accepted**. Each has valid final topology,
preserves every original segment with multiplicity and matches the publisher's
recorded area to within 0.000003 m². The area comparison is a numerical check,
not survey precision or legal authority. The proposed combined contribution is
**79.2327 km²**, calculated as the candidate union intersected with the county
area outside the original valid zoning union. These are scenario measurements;
the county inventory's effective coverage and all holds remain unchanged.

The Atkinson shoreland hold reflects a limitation of the conservative ingestion
decoder: a hole nested inside an island also lies inside the larger exterior shell.
The reviewed candidate attaches it to the innermost shell, with strict nesting and
final validity checks. This is independently corroborated by the service's valid
GeoJSON. The other four service GeoJSON geometries remain invalid under GEOS.
A format conversion alone does not remove their holds.

Moosehead Junction and Spencer Bay require separate interpretation of the remaining
non-nested touch patterns. Failure of the bounded method is not proof of an
erroneous source boundary. No partial-feature candidate is proposed for them.
The remaining **157 held features were ranked but not individually adjudicated**.

## Prioritization

`ranking.json` ranks the intersection of each held feature's **bounding box** with
the county area not covered by valid captured LUPC polygons. It is a conservative
potential-area measure, not the area of an invalid polygon. Overlapping envelopes
are not additive and can greatly overstate a feature's contribution. The valid
union includes all retained source versions/flags, as in the original inventory;
it is not a current legal zoning mask.

The first three envelope-ranked cases are Blanchard, Moosehead Junction and Spencer
Bay. Atkinson's M-GN feature (rank 7) was added because its publisher-reported area
is large and the county inventory flagged Atkinson's usable coverage gap. Its
P-SL2 feature (rank 8) provides a related nested-hole comparison. This is a bounded
first investigation, not a claim that these are the five largest true gaps.

## Official map evidence and limits

Four full-size PDFs were obtained through the [LUPC map index](https://www.maine.gov/dacf/lupc/plans_maps_data/digital_maps_data.html),
archived and visually reviewed. `map-review.json` pins their checksums, recorded
adoption/amendment dates and observations. They corroborate the general districts
and their setting; no PDF boundary was traced and no exact vertex relationship is
certified from page pixels. Their notes retain rule-dependent and map-omitted
protections and dependencies on water locations on the ground. Legal currency,
site applicability and buildability remain UNKNOWN.

The publisher page currently carries a viewer-maintenance notice and warns of
possible lag between digital data and official maps. A successful retrieval is
not proof of authoritative currency. The [Esri polygon specification](https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects/#polygon)
supports interpreting winding and vertex touches; unsupported topology still
fails closed. These methods are investigation tools, not ingestion fallbacks.

## Evidence, tracking and deployment

`report.json` pins original feature checksums, fresh responses, method dependencies,
candidate checksums and comparison results. Native responses, official PDFs and
candidate geometries stay in the private checksum archive. `archive-manifest.json`
identifies the archived bytes. Existing county evidence remains under its original
audit; no source records are overwritten.

TL-F-0029 receives an append-only review and occurrence for this investigation;
TL-F-0022 receives supporting evidence without replacing its existing review.
Deployment is complete: **37 archive objects** were independently downloaded and
hash-verified; **18 observations**, the audit, two finding occurrences and the
TL-F-0029 review are stored in Supabase. Readback confirms all **120,449 county
rows**, **183 total geometry holds** and **162 zoning holds** are unchanged, with
source fingerprints matching the original audit. Prior TL-F-0022 and TL-F-0109
review events remain unchanged. See `checkpoint.json`, `live-verification.json`
and `scripts/check_county_zoning_review.sql`. There is no schema migration,
county geometry update, correction acceptance or screening recomputation here.
A future activation needs a county-specific versioned correction mechanism; the
existing Osborn mechanism must not be reused implicitly.

## Reproduction and validation

Restore the original county capture/report using its archived checkpoint and the
new responses from this investigation's retrieval logs. Candidate files can be
restored by checksum or regenerated. Use the original Shapely 2.0.7 / GEOS 3.11.4
runtime. The ranking step recreates a private local gap cache and pins its checksum.

```sh
python scripts/investigate_county_zoning.py
python scripts/investigate_county_zoning_cases.py
python scripts/prepare_county_zoning_review.py --output .local/county-holds-load
python scripts/prepare_source_staging.py verify \
  --output .local/county-holds-load --download .local/county-holds-download
python scripts/apply_prepared_load.py --prepared .local/county-holds-load \
  --download .local/county-holds-download --project-ref yytsjlmbyqhcqfalbjca
```

Archive and independently download/hash-verify all prepared objects before applying
the metadata/finding load. Review the expected finding event before first apply;
concurrent reviews must not be overwritten. Exact replay of the same event is safe.

Eleven targeted tests pass: supported touching shell/hole representations, unchanged
segments, nested island/hole ownership, and rejection of crossing, duplicate,
overlapping or unsupported alternatives. The five authentic feature comparisons
also verify unchanged native coordinates, service segment agreement and final
candidate validity. Full county ranking is anchored to the original audit's page
checksums. Public reports omit full source geometry and PDF contents.

## Next work

Review the three proposals and implement exact-version county correction history
before any activation. Separately investigate the remaining Moosehead Junction and
Spencer Bay touch patterns, then continue down the ranked holds. Parcel identity,
municipal zoning applicability and wetland imagery qualifications remain separate
open work under the county finding.
