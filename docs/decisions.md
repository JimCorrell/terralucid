# Decision log

These are established design principles, not implementation commitments.

| Decision | Rationale or limit |
| --- | --- |
| Use a data-first geospatial acquisition engine. | Compute parcel facts from sourced records and GIS before AI analysis. |
| Make parcel the canonical entity. | Listings are transient and may not exist for off-market land. |
| Favor PostgreSQL/PostGIS; Supabase is the likely canonical store. | The spatial model needs reproducible queries; final deployment remains open. |
| Optimize for remote, rural, private characteristics. | Organized town, plantation, and unorganized territory are jurisdiction attributes, not a ranking goal by themselves. |
| Keep remoteness distinct from access quality. | Isolation is desirable; uncertain legal or practical access is a separate risk. |
| Use deterministic GIS and user-defined scoring before AI adjudication. | AI interprets a sourced packet; it does not create the underlying facts. |
| Use VERIFIED, DERIVED, INFERRED, UNKNOWN with provenance. | Prevent plausible inference from becoming asserted fact. |
| Preserve multiple parcel geometries and boundary evidence. | Assessment GIS is not a legal survey; confidence and boundary dependency affect conclusions. |
| Treat legal access/title and septic/buildability as first-class due diligence. | Maps and soil layers alone cannot establish rights or site approval. |
| Separate discovery, adjudication, and transaction. | A due-diligence package and resolution of critical unknowns precede offer readiness. |

Sequencing clarification (2026-09-19): begin with dataset discovery and validation, producing a source registry and ingestion plan. Use representative parcels later to test integration once coverage, identifiers and ingestion are understood. See the [source audit](../research/maine-sources/README.md).

## Open questions

- Actual coverage, freshness, rights, and integration methods for each data source.
- Parcel identity matching across state, municipal, registry, and listing records.
- Schema details, scoring weights, thresholds, user interface, and automation choices.
- Which critical unknowns are mandatory for a particular intended use and offer.
