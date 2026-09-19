# Architecture

TerraLucid is a data-first geospatial acquisition engine. The canonical entity is a **parcel**, which may exist without a listing. Listings, assessment records, deeds, geometries, environmental layers, findings, and transaction records attach to the parcel.

## Processing flow

1. **Discovery:** ingest candidate parcels and listings; apply deterministic filters and user-defined scores to geospatial and other structured data.
2. **Adjudication:** assemble a sourced parcel packet, compare conflicting evidence, calculate spatial facts, and use AI to explain risks and prioritize unresolved questions.
3. **Transaction:** produce a due-diligence package, resolve critical unknowns, and only then assess offer readiness.

PostgreSQL with PostGIS is the intended geospatial foundation; Supabase is the likely canonical store, pending the data-availability proof of concept and implementation choices. Keep raw source records and retrieval dates so calculations can be reproduced. AI is an analyst over the evidence, not the system of record.

Remoteness and access quality are separate dimensions. Jurisdiction type (organized town, plantation, unorganized territory) is an attribute. Regulatory consequences belong in separate sourced findings; the jurisdiction label itself is not the search objective.
