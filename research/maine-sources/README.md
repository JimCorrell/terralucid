# Maine source research — 2026-09-19

This pass inventories datasets and tests access, metadata, aggregate coverage and a few export formats. It does not assess or rank properties. Start with the [source registry](registry.json) and [ingestion plan](../../docs/ingestion-plan.md).

## What the checks establish

34 requests are recorded in the three run folders. 33 returned JSON without an API error; the LUPC-linked hosted download returned `499 Token Required` inside its JSON body. HTTP success alone is not an access-success test.

| Source | Direct observation | Limit of the result |
| --- | --- | --- |
| MRS UT parcels | 36,688 features; 467 GEOCODE/TOWNNAME groups; one polygon exported as GeoJSON | Four records have a blank GEOCODE and null town name. Groups include some towns/plantations and are not a count of unique legal jurisdictions. |
| Organized-town parcels | 708,382 features; 327 GEOCODE/TOWN/COUNTY groups; one polygon exported | Fourteen records form a blank jurisdiction group. Municipality completeness has not been established. |
| Organized-town dates | 68 distinct raw FMUPDAT values; 26,663 null and 79,322 empty values | Date strings include years, YYYYMMDD, M/D/YYYY, `0`, and `20`. A uniform date cast would destroy information or fail. |
| Organized-town assessment | Table 9 declares a one-to-one STATE_ID relationship to parcel layer 10 | Actual key uniqueness, match rate and cardinality remain untested. |
| LUPC zones | 168,336 features; one polygon exported; all grouped flags are PUBLISH=Yes and DRAW=Yes | Flags do not independently establish legal currency. State-hosted service works; a different link on the official page requires a token. |
| Civil boundaries | Dissolved source has 924 features; undissolved source exposes GEOCODE and a related GEOCODES table | Dissolved source lacks GEOCODE despite its description. Neither feature count is an established municipality denominator. |
| MaineDOT roads | 100,799 line features; code fields and traffic/surface fields exist | Coverage of private roads, update age and code definitions remain open. |
| Conservation | 12,851 features; identifiers and access fields exist | Inventory geometry and an access field cannot establish permission. |
| SSURGO | 20 Maine-prefixed survey catalog rows; all saverest dates are 2025-08-29 | Catalog presence and restoration timestamps do not establish full spatial coverage or field-observation dates. |
| USGS elevation | Maine-containing bounding-box query returned 1,860 product matches; inspected one GeoTIFF catalog record | First result is a neighboring NH project. This count is not a count of Maine tiles or a coverage measure. |
| USGS hydrography | Four matching 3DHP catalog products; inspected one CONUS FileGDB record | No archive or local features examined. |
| NWI, FEMA, structures | Layer metadata accessible | No full geometry download or Maine coverage check. FEMA probe was its availability index, not hazard polygons. |

The town-group totals reconcile with each parcel service's feature count. This checks completeness of these aggregate responses, not the underlying source. The grouped responses do not report transfer-limit truncation. The single-feature UT and zoning export responses do report truncation, as expected for a deliberately limited request.

The organized-town grouping also exposes code/name conflicts: GEOCODE 17290 appears with both Stow and Sweden, and 31030 with both Alfred and Arundel. These are observed source inconsistencies, not corrected jurisdiction assignments. Reconcile them against the civil reference before using GEOCODE as a trusted join key.

The three exported geometries are format probes only. They carry selected source identifiers, not parcel suitability conclusions.

## Publisher caveats and routes

- [GeoLibrary](https://www.maine.gov/geolib/) warns viewer data can exceed ten years in age. The organized-town catalog explains that FMUPDAT is record currency, while the layer timestamp is publication currency.
- [MRS valuation books](https://www1.maine.gov/revenue/taxes/property-tax/unorganized-territory/valuation-books) list 2026 county books and note ongoing map/lot index updates. PDF extraction remains untested.
- [LUPC](https://www.maine.gov/dacf/lupc/plans_maps_data/digital_maps_data.html) distinguishes assessment maps from surveys and warns digital zoning can lag official maps.
- [USGS](https://www.usgs.gov/national-hydrography) identifies NHD as retired and unmaintained since October 1, 2023. Assess 3DHP coverage before choosing a hydrography input.
- [NWI downloads](https://www.fws.gov/program/national-wetlands-inventory/download-state-wetlands-data) provide state packages with project metadata; map-image dates must accompany polygons.
- [Conserved Lands](https://www.maine.gov/dacf/mnap/assistance/conslands.htm) is an inventory. Its public catalog item explicitly warns that access is not implied. A browser fetch of the linked Hub page failed; the item API and direct feature service succeeded.
- [County registry directory](https://www.maine.gov/revenue/taxes/property-tax/transfer-tax/county-registries-of-deeds), [trail information](https://www.maine.gov/dacf/parks/trail_activities/atv/atv-trails.shtml), and [wastewater permitting](https://www1.maine.gov/dhhs/mecdc/services/business-services/hydrology-and-wastewater/subsurface-wastewater-system-permitting) identify document/manual research routes. API access and reuse rights are still unresolved.
- Utility serviceability, current-use tax records, listing access, land cover/imagery, and municipal zoning remain explicit research gaps.

## Evidence and reproduction

[registry.json](registry.json) records publishers, exact URLs, tested access, coverage limits, identifier candidates, freshness, rights questions, and the next verification for 22 source entries. Its access statuses are operational research labels; they do not replace the parcel evidence taxonomy.

Each `runs/*/results.json` records the exact request, UTC retrieval time, HTTP status, response path, SHA-256 hash and result status. `.response` files preserve response bytes. The records describe an observation at that time; changing services may produce different counts later.

Git treats raw response snapshots as binary to preserve original line endings and keep generated payloads out of textual diffs. They remain readable JSON on disk; use the registry and this report for review, and the response files to inspect underlying evidence.

The manifests contain metadata, aggregate queries and three one-feature exports. The USDA POST is a SELECT against the survey catalog. No credentials or bulk property-owner extracts are needed.

From the repository root, with Python 3 and network access:

```sh
python3 scripts/probe_sources.py research/maine-sources/probes.json /tmp/terralucid-source-check
python3 scripts/probe_sources.py research/maine-sources/profile-probes.json /tmp/terralucid-profile-check
python3 scripts/probe_sources.py research/maine-sources/joins-probes.json /tmp/terralucid-join-check
```

Use new output directories: the script refuses to overwrite a prior run. It reads at most 2 MB per response, uses a 25-second request timeout and makes one attempt per request. A completed run can contain errors; inspect the result log. It is a research probe, not a production ingestion system. Website caveats above were reviewed separately; full HTML pages are not included in the snapshots.
