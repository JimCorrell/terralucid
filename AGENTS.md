# TerraLucid contributor guidance

TerraLucid is a data-first geospatial acquisition engine for finding and assessing remote, rural, private Maine property.

Read the documents in `docs/` before changing the model or workflow. Preserve the distinction between a parcel, its listings, its assessment records, and its title evidence. A mapped assessment polygon is not a legal or surveyed boundary. Keep alternate geometries, source dates, provenance, confidence, and unresolved contradictions visible.

Classify findings as VERIFIED, DERIVED, INFERRED, or UNKNOWN. Record the supporting source and the exact calculation or reasoning. Do deterministic GIS analysis and user-defined scoring before asking AI to adjudicate a parcel packet. AI may explain and prioritize evidence; it must not silently promote an inference into a fact.

Treat legal access, title, boundary uncertainty, septic suitability, and buildability as due-diligence matters. Do not claim that a road, trail, soil map, or zoning overlay alone establishes a legal right or site-specific approval. Resolve critical unknowns before marking a parcel offer-ready.

Keep implementation minimal. Document new decisions in `docs/decisions.md`; label proposals and unresolved questions as such. Do not assume an endpoint, dataset coverage, schema, scoring weight, or regulatory conclusion without verification.

Track source and ingestion deficiencies in the private findings register described
in `docs/findings-register.md`. Preserve stable finding IDs and evidence links.
Append reviews through finding events; do not overwrite history or reset status
when reloading data. New evidence after resolution must remain visible for review.

For downstream analysis, default to accepted corrections through
`ingest.corrected_source.effective_properties` for the exact reviewed source
version. Preserve evidence classification, provenance, holds and findings in
results. Using an original value instead of an accepted correction requires a
recorded evidentiary reason and source/correction versions; raw inspection for
an audit is always available. New snapshots require new validation. Follow
[the correction-layer policy](docs/correction-layer.md).

For reviewed zoning geometry, use `ingest.corrected_zoning_feature` and
`ingest.zoning_screening_latest`, scoped to the intended original audit. Check
`needs_revisit` before using a screening; stale results require review or
recomputation. Preserve geometry acceptance-event dependencies and limits. See
[the geometry correction policy](docs/zoning-geometry-corrections.md).

For reviewed NWI availability, default to `ingest.effective_availability_geometry`
for the exact source version and require `geometry_hold=false`. Use
`ingest.availability_coverage_latest` for the intended study-boundary version and
check `needs_revisit` before use. Carry imagery-age, completeness and legal unknowns
forward. See [availability geometry policy](docs/availability-geometry-corrections.md).

For wetlands inventory, use `ingest.wetlands_feature_current` filtered to the intended
load audit. Check `needs_revisit`, retain source variants and use `effective_lookup`
for reviewed classifications. Carry imagery age and legal/completeness unknowns
forward. See [wetlands ingestion policy](docs/wetlands-ingestion.md).

Keep bounded package wetlands separate in `ingest.wetlands_package_current`, filtered
by audit. Candidate links remain INFERRED; check `needs_revisit` and do not replace
service defaults or merge identities. See [package load](research/wetlands-package-load/README.md).

For the Piscataquis source inventory, use `ingest.effective_county_inventory`
filtered to the intended audit. Default to accepted exact-version interpretations;
retain original evidence and require an evidentiary reason for analytical overrides.
Capture correction dependency snapshots with downstream results and verify them
against the intended audit before use. Follow the
[county correction policy](docs/county-geometry-corrections.md). Distinguish interior intersections, boundary touches, outside
capture candidates, and held geometry. This inventory is explicitly not qualified for parcel screening. Do not inherit Osborn corrections, service/package
identity links, availability results, or legal interpretations. See the
[county scope and evaluation](research/piscataquis-ingestion/README.md).

For reviewed soil geometry, use `ingest.effective_soil_geometry` filtered to the
intended source report hash. Capture `ingest.record_soil_geometry_snapshot` in the
same READ COMMITTED transaction as analytical reads and require
`ingest.soil_geometry_snapshot_is_current` before reusing results. Preserve original
holds, evidence and correction versions; acceptance changes only effective geometry.
Soil availability and purchase-triggered septic/buildability qualification remain
separate. See [soil acceptance policy](docs/soil-geometry-acceptance.md).
