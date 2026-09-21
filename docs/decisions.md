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

## Bounded zoning evidence and downstream dependency tracking

The user approved the zoning ingestion pilot. Preserve all observed zoning
features and publication evidence, with unknown legal currency when a current-zone
selection rule has not been established. Use accepted correction values for their
exact versions and record the review event used. Retain immutable analytical
results and flag them for review after input/correction changes. Treat missing
municipal digital coverage and omitted rule-based protections as explicit unknowns;
no PDF-derived zoning boundaries or legal buildability conclusions are introduced.
See [the pilot report](../research/zoning-ingestion/README.md).

## Reviewed zoning geometry acceptance

After merged PR #11, the user authorized an append-only geometry correction layer,
acceptance of the exact reviewed Osborn shell/hole decoding, and versioned
recomputation. Default downstream zoning analysis to the accepted geometry view
and latest screening view with explicit staleness checks. Preserve original
features, historical results, DERIVED evidence, projection caveats and unknown
legal currency. See [geometry correction policy](zoning-geometry-corrections.md).

## Reviewed NWI availability acceptance

After merged PR #22, the user approved activation of the exact-segment Digital
availability interpretation, with original geometry preserved, append-only review
events and stale-result dependencies. The bounded Osborn coverage calculation is
DERIVED; completeness, current conditions and legal applicability remain UNKNOWN.
This resolves TL-F-0028's exact-version representation hold. See the
[availability geometry policy](availability-geometry-corrections.md).

## Bounded queryable wetlands inventory

After PR #23, the user approved the wetlands load. Load the already qualified
Osborn service snapshot into private versioned feature storage, retaining all
joined variants and page provenance. Default the eight reviewed classifications
to exact reference matches, track their review and availability dependencies, and
keep the Maine package separate pending reconciliation. No canonical parcel joins
or regulatory conclusions are introduced. See [wetlands ingestion](wetlands-ingestion.md).

## Independent bounded package storage

After PR #25, the user authorized the next bounded package load. Preserve the 669
reviewed package features independently, retain exact geometry bytes and source
attributes, and keep service links INFERRED with review dependencies. Mapping the
package-local CRS identifier to equivalent EPSG:5070 changes no coordinates; no
projection correction or source preference change is accepted.

## Piscataquis County evaluation scope

After PR #27, the user chose Piscataquis County as a middle ground between
statewide qualification and individual-parcel investigation, explicitly including
parcels, zoning, and wetlands together. Include organized and unorganized areas;
jurisdiction type remains an attribute. Preserve county-bounded sources first,
then evaluate coverage, geometry, identifiers, source age, and unresolved risks.
This authorizes a county source inventory, not new scoring weights, automatic
corrections, legal conclusions, or statewide qualification.

The study boundary is a DERIVED union of Maine civil features labeled Piscataquis,
including water parts. Capture surrounding-envelope candidates and retain full
source geometries. Store this new source scope separately from exact-version
Osborn acceptances. Native wetlands package geometry remains independent of
service identity and accepted service defaults. See the
[county ingestion](../research/piscataquis-ingestion/README.md).

## Reviewed county geometry acceptance

After PR #30 was merged, the user authorized implementing the county correction
layer. Activate the three independently supported exact-version interpretations
through immutable review history, preserving every original county record and
hold. Accepted interpretations become the downstream default for their reviewed
source version. Withdrawal restores the original hold; downstream dependency
snapshots detect changed reviews and source versions. This authorizes no automatic
repair of other features and does not qualify county parcel screening. See the
[county correction policy](county-geometry-corrections.md).

## Moosehead Junction / Spencer Bay acceptance

After merged PR #33, the user authorized the reviewed next step: extend the county
validator for the two pinned proposals, test preservation of the existing three
approvals, and activate the pair. Keep both source/report formats explicit;
validity alone does not authorize a new feature or audit. New corrections require
a new dependency snapshot and make the previous county snapshot stale. Original
evidence, remaining holds and parcel-screening limits remain unchanged.
