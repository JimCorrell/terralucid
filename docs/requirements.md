# Initial requirements

## Search objective

Find remote, rural, private Maine property suitable for the user's intended basecamp, homestead, and recreation uses. Evaluate parcel characteristics across jurisdiction types. User-defined filters and weights should govern ranking; none are fixed here.

## Evidence and analysis

- Keep parcels independent of listings and preserve all material source records.
- Compute reproducible GIS intersections and metrics before AI review.
- Label each finding VERIFIED, DERIVED, INFERRED, or UNKNOWN, with provenance, retrieval date, and relevant caveats.
- Preserve conflicting geometries and report boundary confidence and boundary dependency: how strongly an intended use depends on the precise boundary.
- Score remoteness separately from physical and legal access quality.
- Treat mapped soils, wetlands, zoning, roads, trails, and parcel lines as screening evidence with source-specific limits.

## Due diligence and readiness

Keep qualified soils and terrain data readily available across the study area
for retrieval and later analysis. Trigger parcel-specific septic suitability and
buildability investigations only when the user selects a parcel for purchase
investigation. Unassessed suitability does not block general discovery or data
availability and must not be presented as either suitable or unsuitable. For a
purchase candidate, resolve material suitability unknowns before offer readiness.

- Investigate legal access, deed and title, easements, recorded plans, road status, zoning, septic suitability, and practical buildability.
- Investigate soil map-unit boundaries and attributes for septic screening, retaining mapping scale, boundary uncertainty, source dates and within-unit variability; require site-specific evaluation for suitability.
- Investigate topography/elevation for slope-related buildability, retaining elevation resolution, accuracy, datum, acquisition date and slope calculation method. Evaluate usable areas within a parcel rather than relying only on parcel-average slope; no suitability threshold is established yet.
- Generate a parcel due-diligence package with evidence, critical unknowns, and requests for documents or field/professional checks.
- Do not mark a parcel offer-ready while critical unknowns for its intended use remain unresolved.

Begin with source-level discovery, access tests, coverage, freshness, identifiers and join feasibility across unorganized and organized jurisdictions. Produce a source registry and ingestion plan before fixing schemas or automation. Representative parcels are later integration checks after the data foundation is established.
