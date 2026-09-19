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
