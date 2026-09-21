# Three Piscataquis zoning priorities

Investigate the first three cases from merged PR #35 together. **All three have supported, source-preserving proposals.** They are not activated; the effective inventory remains at **157 zoning / 178 total holds**, with five accepted corrections and no qualified parcel screenings.

## Results

| Priority / source OBJECTID | Interpretation | Source rings → candidate shells / holes | Potential added geometry |
| --- | --- | --- | ---: |
| East Middlesex Canal Grant / 27304757 | Ring 35 splits into two holes touching at one existing vertex; one nested hole elsewhere retains its innermost shell. | 155 → 89 / 67 | 3.0459 km² |
| T7 R11 WELS / 27270812 | Ring 11 separates a shell and its hole at one existing vertex. | 262 → 131 / 132 | 4.8141 km² |
| T4 R11 WELS / 27207268 | Rings 25 and 28 each split into two holes touching at one existing vertex. | 78 → 29 / 51 | 3.3685 km² |

Ring indices are zero based. The combined additional-geometry scenario is **11.2285 km²**, calculated against the original valid-zoning coverage plus all five accepted corrections. The method unions proposal contributions and subtracts the accepted baseline without double counting. This is potential usable inventory geometry, not legal coverage, available building area or a parcel score. The much larger ranking estimates were bounding-box upper bounds.

## Source comparison and proposal checks

Fresh native EPSG:26919 service records match the archived county features exactly, including attributes and coordinates. The service GeoJSON variants preserve the same attributes and segment multiplicities but are invalid for all three features. A format conversion alone does not resolve these holds.

The proposals reuse the already reviewed nested-shell/hole and touching-hole methods. Only repeated existing vertices are split; coordinates are not moved, snapped, simplified or repaired with a general validity operation. Every original segment, including multiplicity, is retained. Each complete candidate is valid and agrees with the publisher’s numeric area field within 0.000002 m²; that agreement is a numerical cross-check, not survey precision.

After writing each candidate, separate review routines read the fixed bytes and walk the original rings to check exact shell/hole cycles and common ownership of touching holes. A separate ray-crossing algorithm classifies **499 original linework faces** across the three cases; all classifications and the resulting fill agree, with zero symmetric-difference area. These are independent interpretation algorithms using the same GEOS engine, not independent publisher or survey evidence.

[Report](report.json) records complete source comparisons, contact coordinates, cycle roles, hashes, area calculations and map evidence. [Tests](test-results.json) record 20 passing checks, including altered source/coordinates, missing holes, wrong CRS, incomplete responses, unsupported contacts and overlapping coverage calculations.

## Official map evidence

The three full-page official maps and enlarged notes were visually reviewed. URLs were obtained from the publisher’s map index, not inferred from names.

| Map | Stated adoption / effectiveness | Amendment evidence |
| --- | --- | --- |
| [East Middlesex Canal Grant](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/east-middlesex-canal-grant-twp.pdf) | September 16 / October 1, 1999 | May 31, 2001 and June 27, 2002 time extensions; December 26, 2002 P-RP expiration. |
| [T7 R11 WELS](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/t7-r11-wels.pdf) | August 3 / August 18, 2005 | August 18, 2005 adoption of digital NWI wetlands. |
| [T4 R11 WELS](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/t4-r11-wels.pdf) | August 3 / August 18, 2005 | August 18, 2005 adoption of digital NWI wetlands. |

All show P-SL2 shoreland corridors and wetland context. Their notes defer to Chapter 10 for conflicting descriptions, retain protections omitted from the drawing, and describe water-dependent boundaries in relation to water locations on the ground. The PDFs corroborate context and limitations; they are not traced and cannot certify exact contact vertices. Recorded document dates do not establish current legal applicability, title/access, septic suitability or buildability. See the versioned [map review](map-review.json).

## Capture and audit history

The first service pass encountered two read timeouts and one response exceeding its 2 MB cap. The bounded 25 MB document collector then captured all three retry responses. Its generic `NON_JSON_RESPONSE` label is preserved; the investigation separately parses and validates the JSON, feature count, identity, CRS and complete geometry. All successful responses and the original failed-attempt logs are retained. Twelve successful new observations are archived; no missing response body is invented for the failed attempts.

- Investigation audit: `a4b734b5498166be9a802b3cdc4dd08c24567ac10bb9f6764962f187e346d797`.
- Ranking audit: `07efac22afa8829de039ada598fa06533f378c33edc720f40a255b67c75d0136`.
- Effective baseline snapshot: `6953a46ca94beb0c5fa74bac958926d015afb78c65ccfe28c35b08fc10f9d048`.
- [Dependency capture](dependencies.json) binds the scenario to the five accepted correction/event versions. The load locks the county batch and rejects stale dependencies before recording the audit and finding event. Recheck snapshot currency before using the scenario.
- [Archive manifest](archive-manifest.json) identifies private source responses, official PDFs, candidate geometries, original gap cache, methods and tests. Geometry/PDF bytes are excluded from Git.
- [Finding review](finding-review.json) keeps TL-F-0029 in progress and records all three cases together. The 21 parcel holds, municipal applicability, wetland imagery and other due-diligence follow-ups remain open.

## Next step

Extend and test the bounded county acceptance validator for these exact source and candidate hashes, retaining the recorded cycle roles and fill evidence. Then activate supported versions with immutable expected-event history, capture a new dependency snapshot and refresh the remaining ranking. This investigation does not broaden the live validator or accept geometry.

## Reproduce

Restore the manifest objects to their paths in `report.inputs`, including the private source pages, accepted candidates and original gap cache. Use the runtime versions in the report.

```sh
python scripts/investigate_three_zoning_priorities.py
python -m unittest discover -s tests -p 'test_three_zoning_priorities.py' -v
python -m unittest discover -s tests -p 'test_moosehead_spencer*.py' -v
python scripts/prepare_three_zoning_priorities.py --output .local/new-three-priority-load
```

A new retrieval or changed dependency set requires a new audit; replaying the archived evidence is not a freshness claim. Upload prepared objects, independently download/hash-verify them, then apply the guarded metadata load. No migration or source-feature write is included.

## Recorded state

All **58 private archive objects** passed independent download/checksum verification.
The audit, twelve new source observations and ninth TL-F-0029 occurrence/review
are recorded in Supabase. [Live verification](live-verification.json) confirms
all 120,449 original row fingerprints, five accepted correction versions and
other finding events are unchanged. All three investigated features remain held;
the baseline snapshot remains current. See the [checkpoint](checkpoint.json).
