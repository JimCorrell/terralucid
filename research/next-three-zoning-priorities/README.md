# Next three Piscataquis zoning priorities

Investigate the first three cases from merged PR #38. **All three support exact-source proposals.** Acceptance remains a separate step; the eight existing corrections and **154 zoning / 175 total effective holds** are unchanged.

## Results

| Source OBJECTID / map | Interpretation | Source rings → candidate shells / holes | Potential added geometry |
| --- | --- | --- | ---: |
| 27224591 / T4 R13 WELS | Assign one nested hole to its innermost shell; no ring splitting. | 253 → 155 / 98 | 4.3274 km² |
| 27320676 / T7 R9 WELS | Split ring 105 into two holes at their existing shared vertex; assign a separate nested hole to its innermost shell. | 521 → 264 / 258 | 5.4564 km² |
| 27243652 / T6 R15 WELS | Assign two nested holes to their innermost shell; no ring splitting. | 258 → 132 / 126 | 4.1530 km² |

All three are P-SL2 records. Indices are zero based. The combined scenario is **13.9368 km²** beyond original valid zoning and all eight accepted corrections, with overlapping contributions counted once. It measures potential usable inventory geometry, not legal coverage, building area or parcel quality. Ranking estimates were much larger bounding-box upper bounds.

## Evidence and checks

Fresh native EPSG:26919 records exactly match the preserved county features, including attributes and coordinates. Both valid service GeoJSON representations—T4 R13 and T6 R15—equal the proposals. Those two holds came from conservative hole ownership decoding, not invalid individual rings. T7 R9 service GeoJSON remains invalid at the shared hole vertex; its proposal preserves the source's complete boundary segments and multiplicities.

The existing interpretation methods move no coordinates and use no snapping or general geometry repair. Each complete candidate is valid; publisher area agreement is within 0.000002 m², a numerical cross-check rather than survey precision. Separate routines check fixed serialized candidates against source cycle roles and touching-hole ownership. Ray-crossing classification agrees on all **1,033 source faces**, with zero fill difference. These distinct algorithms share GEOS; they are not independent publisher approval.

The [report](report.json) records source versions, contact coordinates, ownership, complete checks and scenario calculations. The [23 passing tests](test-results.json) cover authentic candidates, nested ownership, wrong parents, missing enclosing holes, unsupported contacts, altered sources/segments, incomplete responses, wrong CRS and overlapping scenario contributions.

## Official map evidence

Publisher map-index URLs led to the official [T4 R13](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/t4-r13-wels.pdf), [T7 R9](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/t7-r9-wels.pdf) and [T6 R15](https://www.maine.gov/dacf/lupc/plans_maps_data/maps/t6-r15-wels.pdf) PDFs. Full pages and enlarged notes were visually reviewed. All state adoption August 3, 2005, effectiveness August 18, 2005, and adoption of digital NWI wetlands on August 18, 2005.

They show P-SL2 corridors among lakes and wetlands, but do not establish exact contact topology. Notes defer to Chapter 10 for conflicting descriptions, retain protections omitted from the drawing and describe water-dependent boundaries following water locations on the ground. These are recorded document statements, not a current legal determination. No map tracing was used. See [map review](map-review.json). Title/access, legal boundaries, septic suitability and buildability remain unknown.

## Audit and next step

- Audit: `a45d02d957bc6a5db61a53e8bf42be4000e582e08a07ea520f6e22254947b3be`.
- Ranking: `6b8896283cc6637d5d2dc77c51fe1fe28f2600f64c76ef25649f05893ad418eb`.
- Baseline snapshot: `7a862e0e28a8d54afd6c5a58c0964a5482393836fc2af767cad80b42e26a20f8`.
- [Dependencies](dependencies.json) pin eight accepted versions. The load locks the county batch and rejects stale dependencies before appending the audit and finding event.
- [Archive manifest](archive-manifest.json) identifies originals, fresh responses, maps, proposals, methods and tests in private Supabase storage. Source and geometry bytes are excluded from Git.
- Twelve requests succeeded. The document collector's generic `NON_JSON_RESPONSE` label is retained; the investigation separately parses and validates all service JSON. No failed retrievals occurred.
- [Finding review](finding-review.json) keeps TL-F-0029 in progress. Next: review exact proposal hashes, extend/test the bounded acceptance layer as needed, activate supported versions, then refresh ranking. The 21 parcel holds and other county qualification issues remain open.

## Reproduce

Restore private manifest bytes to `report.inputs` paths and use the recorded runtime versions.

```sh
python scripts/investigate_next_three_zoning_priorities.py
python -m unittest discover -s tests -p 'test_next_three_zoning_priorities.py' -v
python -m unittest discover -s tests -p 'test_moosehead_spencer*.py' -v
python scripts/prepare_next_three_zoning_priorities.py --output .local/new-next-three-load
```

Upload prepared objects, independently download/hash-verify them, then apply the guarded metadata load. No migration or source-feature write is included. Replaying archived observations does not establish freshness; changed sources/dependencies require a new audit.

## Recorded state

All **61 private archive objects** passed checksum verification: 26 newly downloaded
objects and 35 reverified copies from earlier independent archive downloads.
Supabase contains the audit, twelve new observations and twelfth TL-F-0029
occurrence/review. [Live verification](live-verification.json) confirms all
120,449 original row fingerprints, eight accepted correction versions and unrelated
finding events are unchanged. All three proposals remain held; the baseline
snapshot is current and qualified parcel screenings remain zero. See the
[checkpoint](checkpoint.json).
