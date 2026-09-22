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

The [mask-purpose follow-up](../research/fema-mask-purpose/README.md) finds a similar
blank area on the 2016 base panel and independently corroborates the 2024 revision's
finalization. Carry-forward of an older mask is INFERRED; its intended purpose and
the status of specific covered graphics remain UNKNOWN. Publisher questions are
prepared but unsent. Do not treat blank display as absence of flood hazard.

The [LUPC flood-adoption review](../research/osborn-flood-adoption/README.md)
retrieves signed ZP 796: the August 2024 map change corrected text while retaining
existing zoning. Incorporation of FEMA case 22-01-0871P remains UNKNOWN; neither
adoption nor non-adoption follows from the available dates. Keep FEMA hazard class,
LUPC applicability and the mask question separate; do not equate all Zone X with P-FP.

### Bounded wetlands qualification

The [Osborn NWI audit](../research/osborn-wetlands/README.md) preserves 669 distinct
wetland/deepwater source features, with 499 intersecting the study boundary.
Imagery-source metadata dates to May 1983, despite the May 2026 release label.
Eight conflicting joined classification lookups (TL-F-0027) and an invalid national
availability ring (TL-F-0028) remain open. Valid imagery-source footprints cover the
study scope; this does not establish exhaustive or current wetland detection.
Maine package reconciliation, statewide ingestion and regulatory applicability
remain separate gates. Empty inventory space does not establish wetland absence.

The [classification follow-up](../research/wetlands-classification/README.md)
resolves TL-F-0027's eight-record interpretation using the official CSV and decoder.
The complete PUBFh/PUBFx definitions match; incomplete duplicate lookups remain in
the live service and in the archive. The Maine package is now archived with eight
spatial candidate comparisons, not loaded statewide. Identifier/projection differences,
May 1983 imagery and TL-F-0028 remain qualified. Use exact reviewed versions downstream.

The [TL-F-0028 investigation](../research/wetlands-availability/README.md) finds
five self-touching native availability rings. An exact-segment decomposition gives
a valid 93-exterior/74-hole proposal. Osborn availability agrees with the official
service rendering and imagery footprints, without establishing wetland completeness.
The proposal is unaccepted; the original geometry hold and source-age/legal limits remain.

The subsequent [availability acceptance](../research/availability-acceptance/README.md)
activates only that reviewed version. The national availability geometry is stored
and one Osborn coverage result is computed; this is not statewide wetlands feature
ingestion. TL-F-0028's representation hold is resolved, with original evidence and
all source-age/completeness/legal qualifications preserved.

The [bounded feature load](../research/wetlands-load/README.md) makes the historical
669-record Osborn service capture queryable in private PostGIS. It retains all
677 joined lookup variants and 679 page occurrences, with exact-version defaults
for the eight resolved classifications. This does not reconcile or ingest the
Maine package statewide; imagery-age, completeness and applicability limits persist.

The [service/package comparison](../research/wetlands-package-comparison/README.md)
extends comparison to the entire qualified Osborn service scope. Its spatial
candidates are INFERRED identities, with DERIVED distance/overlap metrics, preserved
identifiers and a reverse package-coverage check. No cross-release identity rule
or geometry replacement follows automatically from spatial/classification agreement.

The [bounded package ingestion](../research/wetlands-package-load/README.md) preserves
669 native package features in private PostGIS, with original blobs/attributes and
INFERRED service candidate links. This neither replaces the service nor establishes
new imagery dates, accepted identity links or statewide qualification.

The [projection and lineage follow-up](../research/wetlands-projection-lineage/README.md)
numerically reconciles all 669 pairs through explicit ESRI:108190, supported by four
unchanged live service controls. Four native package project footprints cover the
load and study boundary, retaining May 1983 imagery and undated NHD supplementation.
This neither corrects source geometry nor establishes current/complete/legal wetlands.

The [Piscataquis County inventory](../research/piscataquis-ingestion/README.md)
expands native parcel and LUPC capture and extracts county wetlands/project metadata
from the archived Maine package. It preserves source versions, held geometry,
outside capture candidates and per-jurisdiction coverage evidence. County project
imagery is dated 1984–1986; accepted Osborn corrections and qualifications do not
transfer automatically. Official municipal zoning and legal applicability remain
separate evidence requirements.

## Planned soils and terrain investigations

Requested after the county readiness review; both remain **pending investigation**.
These are planned work items, not observed dataset defects or completed loads.

Qualify and make soils and elevation/terrain data readily available across the
study area, independent of purchase interest in any individual parcel. Source
coverage, provenance and quality checks belong to this data preparation stage.
Parcel-specific septic suitability, usable building areas and siting analysis
are triggered only when a parcel is selected for purchase investigation.

- **Soil boundaries / septic screening:** qualify the candidate USDA SSURGO
  coverage for Piscataquis County, map-unit boundaries and component/limitation
  attributes. Check identifiers, dates, mapping scale, geometry quality and
  boundary uncertainty. Preserve variation within a map unit and identify the
  field evidence needed to assess a proposed septic location. Do not turn a
  soil polygon intersection into septic approval.
- **Topography / slope buildability:** qualify candidate USGS/Maine elevation
  or LiDAR coverage, acquisition dates, resolution, vertical accuracy, units,
  datum and missing-data areas. Define reproducible slope calculations for later
  purchase-candidate analysis of usable areas, access and septic siting. Keep slope evidence separate from legal buildability and
  site approval; no source product, cutoff or scoring weight is selected yet.

Here “topography” means terrain elevation and slope, as requested for buildability;
geometry topology remains a separate shape-validity concern. Keep data availability/quality status separate from parcel suitability status.
For parcels without purchase interest, suitability is not yet assessed and is
not a discovery gate. For purchase candidates, carry unresolved suitability
questions into due diligence. Record discovered source deficiencies in the
private findings register.
