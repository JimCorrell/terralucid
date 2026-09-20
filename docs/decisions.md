# Decision log

These are established design principles and the explicitly selected implementation choices.

| Decision | Rationale or limit |
| --- | --- |
| Use a data-first geospatial acquisition engine. | Compute parcel facts from sourced records and GIS before AI analysis. |
| Make parcel the canonical entity. | Listings are transient and may not exist for off-market land. |
| Use PostgreSQL/PostGIS on Supabase. | Supabase selected by the user after the initial source audit; canonical parcel integration remains later work. |
| Optimize for remote, rural, private characteristics. | Organized town, plantation, and unorganized territory are jurisdiction attributes, not a ranking goal by themselves. |
| Keep remoteness distinct from access quality. | Isolation is desirable; uncertain legal or practical access is a separate risk. |
| Use deterministic GIS and user-defined scoring before AI adjudication. | AI interprets a sourced packet; it does not create the underlying facts. |
| Use VERIFIED, DERIVED, INFERRED, UNKNOWN with provenance. | Prevent plausible inference from becoming asserted fact. |
| Preserve multiple parcel geometries and boundary evidence. | Assessment GIS is not a legal survey; confidence and boundary dependency affect conclusions. |
| Treat legal access/title and septic/buildability as first-class due diligence. | Maps and soil layers alone cannot establish rights or site approval. |
| Separate discovery, adjudication, and transaction. | A due-diligence package and resolution of critical unknowns precede offer readiness. |

Sequencing clarification (2026-09-19): begin with dataset discovery and validation, producing a source registry and ingestion plan. Use representative parcels later to test integration once coverage, identifiers and ingestion are understood. See the [source audit](../research/maine-sources/README.md).

## Initial storage implementation

Use private Supabase Storage for exact research snapshots and a private `ingest`
schema for registry versions, retrieval provenance and three existing geometry
samples. SHA-256 object names and deterministic observation identities support
reproducible loads. This is an implementation choice for the bounded audit load,
not a bulk retention or refresh policy. See [setup and checks](supabase-staging.md).

## Audit-driven staging constraints

The [coverage audit](../research/maine-coverage/README.md) found missing/repeated
parcel identifiers and assessment matches with multiple rows. Preserve source
records separately; do not enforce STATE_ID/TPL/GPL as canonical unique parcel keys.
Use GEOCODES.STATUS for the dated reference classification; civil polygon TYPE is
not jurisdiction organization. Raw code/name conflicts remain unresolved until
reviewed. Source presence is not evidence of complete jurisdiction coverage.

## Findings follow-up and bounded ingestion

The user approved adding the findings register with the next ingestion step.
Implement stable issue IDs, append-only status/priority/next-action events and
versioned evidence occurrences in private Supabase staging. Repeated loads must
preserve reviews; later evidence after resolution is flagged for another review.
Initial priority is operational review triage, not a parcel ranking weight.

Use source/version/OBJECTID row identity with retained GlobalID and raw business
identifiers in the first bounded load. Preserve zero/one/multiple assessment
candidates, invalid geometries and unknowns. No candidate is a canonical parcel
match; no geometry is silently repaired. See [the load report](../research/maine-ingestion/README.md).

## Open questions

- Actual coverage, freshness, rights, and integration methods for each data source.
- Parcel identity matching across state, municipal, registry, and listing records.
- Schema details, scoring weights, thresholds, user interface, and automation choices.
- Which critical unknowns are mandatory for a particular intended use and offer.

## Reviewed correction layer

After PR #7, the user approved a separate correction layer. Accept its reviewed
GEOCODE and STATE_ID proposals only for their exact historical source snapshots.
Preserve raw features, assessment candidates, original geometries, exception holds
and findings. Acceptance does not change INFERRED evidence into VERIFIED evidence.
Use immutable source interpretations and append-only acceptance/withdrawal events;
new source deliveries require new review. See [correction layer](correction-layer.md).


## Default interpretation for downstream analysis

The user confirmed that accepted corrections are the default for downstream
analysis. Use the effective values for their exact reviewed source versions,
carrying evidence classification, provenance and unresolved holds forward. Retain
raw values for audit; overriding an accepted value in analysis requires a recorded
evidentiary reason. Preserve the acceptance event used by each result so later
review can identify affected analyses. This policy does not transfer corrections
to new snapshots or certify uncorrected values. Consumer enforcement and analytical
result tracking remain downstream implementation work.
