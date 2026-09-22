# Architecture

TerraLucid is a data-first geospatial acquisition engine. The canonical entity is a **parcel**, which may exist without a listing. Listings, assessment records, deeds, geometries, environmental layers, findings, and transaction records attach to the parcel.

## Processing flow

1. **Discovery:** ingest candidate parcels and listings; apply deterministic filters and user-defined scores to geospatial and other structured data.
2. **Adjudication:** assemble a sourced parcel packet, compare conflicting evidence, calculate spatial facts, and use AI to explain risks and prioritize unresolved questions.
3. **Transaction:** produce a due-diligence package, resolve critical unknowns, and only then assess offer readiness.

PostgreSQL with PostGIS on Supabase is the selected geospatial foundation. The initial implementation is [private source staging](supabase-staging.md); canonical parcel integration follows source validation. Keep raw source records and retrieval dates so calculations can be reproduced. AI is an analyst over the evidence, not the system of record.

Remoteness and access quality are separate dimensions. Jurisdiction type (organized town, plantation, unorganized territory) is an attribute. Regulatory consequences belong in separate sourced findings; the jurisdiction label itself is not the search objective.

## Analytical source interpretation

Downstream analysis uses accepted corrections as its default interpretation for
the exact reviewed source version. Read effective properties with their correction
history, provenance, evidence classification and unresolved findings. Preserve raw
sources for audit and evidence-based reconsideration. An analytical override to
raw values needs a recorded evidentiary reason; new deliveries require validation.
See [the correction-layer policy](correction-layer.md) for consumer requirements
and the distinction between documented policy and implemented controls.

Reviewed zoning geometry follows the same exact-version policy through
`ingest.corrected_zoning_feature`. Consumers use `ingest.zoning_screening_latest`
and inspect `needs_revisit`; geometry review changes preserve prior results and
flag dependent calculations. See [geometry history](zoning-geometry-corrections.md).

The initial [area qualification consumer](area-qualification.md) builds a private,
read-only evidence packet for an AOI or assessment source record. It checks
coverage, holds, source conflicts and dependencies separately by topic. It does
not change the county inventory's qualification flags or establish canonical
parcel identity, legal applicability or offer readiness.
