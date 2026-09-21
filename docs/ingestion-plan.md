# Source-first ingestion plan

The immediate milestone is a verified source registry and an ingestion plan. The [initial audit](../research/maine-sources/README.md) provides 34 recorded access/profile checks and an explicit gap list. Supabase is now selected, and the [first staging load](supabase-staging.md) preserves that audit. The broader coverage, identity and bulk-ingestion work below remains open.

## 1. Complete the coverage and identity audit

The [coverage and identifier audit](../research/maine-coverage/README.md) now establishes
917 status-coded reference entries, reported source presence and candidate-key
quality. The bounded assessment join disproves a universal one-to-one assumption.
Full match coverage, current legal-effective dates and UT valuation linkage remain
open; these findings support source staging with explicit unresolved records.

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

The [bounded ingestion step](../research/maine-ingestion/README.md) now preserves
2,058 source records and candidate assessment links. The [findings register](findings-register.md)
tracks audit deficiencies and record-level occurrences with stable IDs, next actions
and review history. This validates the bounded workflow; statewide coverage and
canonical identity remain separate gates.

Use PostgreSQL/PostGIS on the user-selected Supabase project. The first staging model preserves the existing research audit, exact responses and three geometry samples. It validates storage and traceability while the coverage and identity audit remains open; it does not imply readiness for bulk parcel ingestion.

For each source delivery retain the publisher, source ID, exact URL/query, retrieval time, publisher version/date, response or file checksum, coordinate reference system, terms/caveats and ingestion outcome. Raw snapshots should remain reproducible. Exact research artifacts use a private Supabase Storage bucket. Bulk retention and refresh cadence remain open decisions.

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

## First zoning pilot

The [bounded zoning ingestion](../research/zoning-ingestion/README.md) qualifies
Osborn LUPC GIS for provisional geometric screening and inventories municipal
publication routes for Kingsbury, Sweden and Alfred. It records source gaps,
invalid geometry, unknown legal currency and downstream correction dependencies.
Municipal polygon qualification and authoritative date/rule reconciliation remain
next ingestion gates; this pilot does not satisfy all of step 3.

The [Osborn geometry investigation](../research/osborn-zoning-investigation/README.md)
supports an exact-version shell/hole decoding for TL-F-0025, with unchanged source
segments. The [geometry correction layer](zoning-geometry-corrections.md) now accepts
that interpretation and provides versioned Osborn screening revisions. Historical
exclusions remain preserved; the projection and legal-currency caveats remain open.

## First wetlands qualification

The [Osborn NWI service pilot](../research/osborn-wetlands/README.md) preserves a
bounded inventory with imagery-source and availability evidence. It profiles native
geometry and identifiers and records two new deficiencies. The Maine package has
not yet been loaded; reconcile it with the service and resolve the lookup/availability
holds before wider ingestion. May 1983 imagery remains a qualification on downstream
use even if the package release is recent.

The [classification follow-up](../research/wetlands-classification/README.md)
archives the Maine GeoPackage and resolves the eight lookup interpretations.
Package/service identifiers and projected boundaries differ; candidate comparisons
do not establish a general crosswalk. Availability geometry (TL-F-0028), wider
package qualification and a queryable wetlands load remain future work.

The [availability follow-up](../research/wetlands-availability/README.md) diagnoses
TL-F-0028 and archives an unaccepted exact-segment decode. Review acceptance and
version dependencies before enabling that coverage overlay. Source-image age,
package/service reconciliation and field/regulatory limits remain separate gates.

The [availability acceptance](../research/availability-acceptance/README.md) now
activates that exact interpretation and records one versioned Osborn coverage
result. TL-F-0028's representation hold is resolved. Next qualify a bounded
queryable wetlands feature load, retaining package/service identity, projection,
imagery age and field/legal limits under TL-F-0117. Wider ingestion remains gated.
