# Maine data-source inventory

The table below preserves the category inventory from the design discussion. The [source registry and access audit](../research/maine-sources/README.md) now records tested endpoints, observed gaps, and untested sources as of September 19, 2026. The [ingestion plan](ingestion-plan.md) identifies the checks needed before loading and joining data. Confirm licenses, coverage, dates, identifiers, and update cadence for each source before production ingestion.

| Category | Candidate sources discussed | Caution |
| --- | --- | --- |
| Unorganized Territory parcel maps and assessment | Maine Revenue Services (MRS) parcel GIS, valuation books, map/lot indexes | Assessment polygons are not legal surveys. GIS ownership may be stale; check current MRS records and title. |
| Organized towns and plantations | Municipal assessors, tax maps, local GIS and zoning records | Coverage, formats, freshness, and availability vary by municipality. |
| LUPC zoning | LUPC GIS and official Land Use Guidance Maps | Digital zoning may lag the official map; verify current rules and map for a serious candidate. |
| Terrain and water | USGS/Maine elevation or LiDAR, hydrography, Maine GIS | Slope and aspect are derived; mapped features and resolution have limits. |
| Soils, wetlands, flood | USDA SSURGO, National Wetlands Inventory/Maine DEP, FEMA | Screening layers do not establish a buildable site or septic approval. |
| Roads, trails, conservation | MaineDOT/state GIS, OpenStreetMap, clubs/state trail information, public/conservation land layers | A mapped road or trail does not establish legal access or permission; routes can change. |
| Ownership, access, restrictions | Registry deeds and recorded plans; assessor and tax records | Legal rights, easements, boundary descriptions, and current vesting require document review. |
| Utilities and listings | Provider information and listing sources | Coverage and claims may be incomplete or stale; corroborate material claims. |

Actual septic suitability requires site-specific evaluation. Recorded deed descriptions or survey plans may support boundary analysis, but any reconstructed geometry remains distinct from a licensed survey.

## LUPC qualification follow-up

The [TL-F-0109 investigation](../research/lupc-currency/README.md) distinguishes
Osborn's map amendments, service update label and current published rule edition.
Matching digital attributes do not establish legal currency. Keep flood, wetland,
shoreland and physical-boundary dependencies explicit; complete polygon coverage
does not establish complete regulatory coverage. TL-F-0109 remains in progress.
The FEMA follow-up below addresses part of this dependency; additional screening
and legal zoning conclusions still require the recorded qualifications.

## FEMA qualification follow-up

The [Osborn FEMA investigation](../research/osborn-fema/README.md) captures effective
NFHL hazard features, panels, availability, revision footprints and official
study/revision documents. A May 31, 2024 revision adds mapped hazards while the
base FIRM/FIS retains its 2016 date. Keep these dates separate and do not treat the
2016 no-SFHA note as current clearance. Two invalid FEMA polygons are preserved
under TL-F-0026; parcel screening and LUPC adoption remain pending qualification.
This is bounded Osborn source evidence, not statewide FEMA ingestion.

[TL-F-0026 follow-up](../research/fema-geometry-investigation/README.md) identifies
vertex-touching native rings and proposes boundary-preserving shell/hole decodings.
The proposals are not accepted. The reviewed 0443D map enclosure is blank at one
feature's approximate location despite current service depiction; carry this
map-evidence discrepancy under TL-F-0105 rather than clearing or deleting hazards.

The [0443D display investigation](../research/fema-map-discrepancy/README.md)
explains that blank region: an opaque PDF MASK layer covers existing hazard
graphics. Preserve the published display and label any layer-hidden diagnostic
view. Mask purpose and regulatory status remain unknown; inspecting hidden
content does not establish adoption or authorize a replacement map.
