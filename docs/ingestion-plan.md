# Source-first ingestion plan

The immediate milestone is a verified source registry and an ingestion plan. The [initial audit](../research/maine-sources/README.md) provides 34 recorded access/profile checks and an explicit gap list. The steps below are proposed implementation work, not a finalized schema or infrastructure selection.

## 1. Complete the coverage and identity audit

Start with the civil-boundary reference, MRS parcel geometry, organized-town parcel geometry, and the associated assessment sources.

- Validate the civil GEOCODES reference and jurisdiction TYPE meanings. Establish a dated jurisdiction denominator before reporting coverage percentages.
- Preserve source GEOCODE and raw map/lot identifiers, including leading zeroes. Names are display labels; codes require validation across publishers.
- Resolve observed code/name conflicts (including Stow/Sweden and Alfred/Arundel) against the civil reference. Do not silently correct or join ambiguous source assignments.
- Profile candidate keys for nulls, blanks, duplicates and multiple geometries. Verify the organized STATE_ID-to-assessment relationship empirically.
- Reconcile the two parcel products' overlapping jurisdictions. Keep distinct source records until matching evidence supports a crosswalk; do not collapse records solely by overlap or owner name.
- Parse FMUPDAT into a value plus precision (year or day), retaining its original string. Quarantine malformed values. Keep source date, service edit date and retrieval date separate.
- Inspect the UT valuation PDFs for reliable extraction and identity linkage.
- Create a coverage table by source and jurisdiction: presence, feature count, date distribution, identifier completeness and known omissions. A missing source record means unknown coverage, not an absence of property.

**Exit condition:** candidate keys, known coverage gaps, and date handling are documented well enough to design a small staging model. Unresolved joins remain explicit.

## 2. Design and implement a minimal source-preserving load

Use the audit to propose the first PostgreSQL/PostGIS staging model and confirm deployment choices. Supabase remains the likely host; this research has not provisioned it.

For each source delivery retain the publisher, source ID, exact URL/query, retrieval time, publisher version/date, response or file checksum, coordinate reference system, terms/caveats and ingestion outcome. Raw snapshots should remain reproducible. Bulk data storage location, retention and refresh cadence are open decisions.

For ArcGIS sources, read live layer metadata, use a stable pagination strategy, honor advertised page limits, detect transfer-limit flags, and reconcile loaded counts. A service count is a control total, not a guarantee of correct or complete legal property data. Service drift during a load requires reconciliation. Preserve source geometries and identifiers; log transformations and geometry repairs.

Assessment and listing data remain separate from legal title. Every canonical parcel match should retain its source crosswalk and the evidence for the match. Do not choose a universal parcel key merely because one publisher uses it.

**Exit condition:** a bounded dataset load can be repeated and audited, with unresolved records retained and existing source snapshots traceable.

## 3. Add spatial sources with explicit coverage

- **Zoning:** determine the current-zone rule and source-map dates; inventory municipal zoning routes alongside LUPC.
- **Soils:** validate map-unit/component/horizon identifiers, survey boundaries and incomplete mapping. Preserve units and interpretation versions.
- **Wetlands:** ingest the Maine package with project/image-date metadata and coverage.
- **Elevation:** build the actual Maine tile inventory, including acquisition dates, horizontal/vertical references, resolution, overlap and gaps. Derive slope/aspect only after these are known.
- **Hydrography:** inspect 3DHP distribution and Maine lineage; retain legacy NHD version only if needed and clearly labeled.
- **Flood:** identify and test the actual hazard layer plus availability/study coverage. An empty result in unmapped coverage remains unknown.
- **Roads/conservation:** resolve field definitions, dates and identifiers; keep spatial proximity distinct from rights and permission.
- **Privacy/remoteness inputs:** qualify building, imagery and land-cover coverage before calculating absence-of-development metrics. The inspected state-hosted building layer is sourced from OpenStreetMap.

For every spatial calculation, record input layer and geometry versions, method, units, coverage and boundary dependency. Derived values do not inherit legal authority from a map.

**Exit condition:** each enabled metric has validated input coverage and an explicit failure/unknown path.

## 4. Track document and field evidence paths

Inventory registry indexing and plan access, local zoning records, current-use tax documentation, road/easement instruments, trail permissions, utility serviceability, and septic/site records. Record access cost and reuse limits where found. No paid provider or scraping commitment has been made.

Site and professional checks remain explicit unresolved evidence requirements where public datasets cannot establish the intended fact.

## Later integration checks

After the source registry, coverage audit and first loads are usable, select representative parcels to test joins and derivations. User-defined scoring, AI adjudication, a user interface and transaction readiness follow the data foundation. A successful endpoint probe alone does not justify a suitability assessment.
