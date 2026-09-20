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
