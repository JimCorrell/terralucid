# Bounded wetlands feature ingestion

The first queryable wetlands load uses the already reviewed NWI service snapshot
around Osborn. It retains **669 distinct inventory features**, **677 distinct
joined lookup variants** and **679 page occurrences**. Neighboring envelope records
are included; this is not statewide ingestion or a legal wetland delineation.

## Storage and identity

`ingest.wetlands_batch` identifies the load audit, original source audit,
classification review and accepted availability coverage result.
`ingest.wetlands_feature` retains immutable native core attributes/rings, all joined
lookup variants, page observation/payload checksums and row ordinals, the exact
load input and its checksum, plus a queryable PostGIS MultiPolygon in EPSG:3857.
A GiST index supports spatial queries. Geometry decoding retains source coordinates
without repair. Unsupported or changed inputs stop this bounded load for review.

The feature key is `(audit_sha256, object_id)`. OBJECTID and GlobalID are source
identifiers, not canonical parcel or cross-release identities. No join to the Maine
GeoPackage is asserted. The prior eight package comparisons remain INFERRED.

The load audit pins every feature input checksum and source page, the method,
migration, decoder, classification audit, availability audit and imagery lineage.
An atomic load and deferred database completeness check prevent partial batches
from committing. Replays are no-ops; changed content under an existing identity
is rejected. Original responses and historical audits remain unchanged.

## Downstream query contract

Use `ingest.wetlands_feature_current`, **filtered to the intended load audit**.
“Current” refers to review-dependency status, not the newest upstream release or
current field conditions. There is no automatic refresh or cross-batch latest view.

- `code` and `wetland_type` retain source attributes.
- `lookup_variants` and `native_core` preserve original evidence.
- `effective_lookup` defaults to the reviewed reference-matched definition for the
  eight TL-F-0027 records, after native-core, lookup and reference hash checks.
  Other features retain their sole service lookup, without claiming independent
  reference verification for those definitions.
- A later TL-F-0027 review event, reopening or new occurrence flags those eight
  records with `classification_needs_revisit` and returns NULL effective lookup.
  `reviewed_lookup` retains the historical interpretation for audit.
- `availability_needs_revisit` reflects the exact accepted coverage result's
  dependency status. Withdrawal or reacceptance flags all 669 records. Raw feature
  geometry remains available; the availability qualification must be reviewed.
- Check `needs_revisit` before dependent analysis. Pin the load audit,
  classification event and availability result in downstream results. New source
  versions require new qualification; bypassing accepted interpretations requires
  a documented evidentiary reason. A stale batch is not silently refreshed.

The view exposes `prior_qualification_profile` from the original audit, including
study-boundary intersection area. These are historical DERIVED EPSG:26919 results
with the original audit's runtime/transformation and FEMA boundary dependencies;
they are not newly computed parcel screenings. 499 features had positive-area
intersections. Do not sum overlapping feature areas as unique wetland acreage, or
calculate physical acreage directly from Web Mercator geometry.

## Qualifications and access

Every row carries DERIVED evidence and explicit UNKNOWN completeness, present-day
conditions and legal applicability. Imagery lineage is May 1983 with later NHD
supplementation whose acquisition date is unestablished. Release and retrieval
dates are separate. Digital availability does not establish absence of wetlands.
Inventory classes do not establish LUPC P-WL, regulatory jurisdiction, septic
suitability or buildability.

TL-F-0117 continues to track package/service identity and projection, broader
qualification, refresh and ground/legal limitations. The load adds a review and
occurrence without resolving those deficiencies or changing TL-F-0027/0028.

Tables and view are private administrative ingestion resources, with RLS and
client privileges revoked. Normal paths enforce history, provenance and version
checks; administrators can bypass database controls. The query layer does not
prevent a downstream consumer from ignoring its status flags.

See the [load checkpoint](../research/wetlands-load/README.md).

## Separate bounded package records

The [package load](../research/wetlands-package-load/README.md) retains 669 reviewed
Maine package features alongside the service inventory, preserving native geometry
bytes and attributes. The package uses equivalent CRS identifier EPSG:5070 without
coordinate transformation. Candidate links remain INFERRED, and existing service
defaults remain unchanged. `ingest.wetlands_package_current` exposes comparison and
service review dependencies; source selection and boundary differences remain explicit.

The later [projection/lineage audit](../research/wetlands-projection-lineage/README.md)
numerically explains the bounded displacement using explicit ESRI:108190 and
qualifies native package project coverage. Consult it alongside historical comparison
metrics; source geometries, inferred identities and default views remain unchanged.
May 1983 imagery and undated supplementation remain explicit qualifications.
