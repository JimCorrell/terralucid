# Soil availability checks and component-gap investigation

## Inventory adapter

The area qualification packet now supports an **explicit, version-bound soil
inventory request**. It is a read-only adapter over the accepted soil geometry and
original tabular records. It installs no migration, changes no qualification flag,
and makes no septic/buildability determination.

Add `soils` to an otherwise valid area/source-parcel request:

```json
{
  "soils": {
    "batch": "b31e3034caee9f70361bb9c769b936b8709fcab38706f89cdee22c9265aad512",
    "snapshot": "ba5c5310cf4a81242b257a461a576d04d367cef4cafeaec1413a7a6b83e65b7c"
  }
}
```

These are reviewed historical versions, not a promise that the snapshot will stay
current. The adapter validates the supported batch and requires an existing soil
snapshot; it never creates acceptance/snapshot events or silently selects newer
sources. Without `soils`, the topic stays `missing` and no soil SQL is queried.
Unsupported batches fail validation until their metadata is reviewed.

Usable inventory intersections require all of:

- Current requested county and soil geometry snapshots, and an existing soil batch.
- AOI completely within both county and pinned soil study boundaries.
- No effective soil holds in the requested batch. This first implementation is
  conservative: even a distant withdrawn polygon blocks soil usability pending
  review rather than inferring the extent of invalid original soil WKT.
- Positive-area effective soil intersections and zero calculated AOI coverage gap,
  using the existing covering-input/union rule without an area tolerance.
- Map-unit, legend and component links for every positively intersecting map unit.

A missing horizon is reported explicitly and does not masquerade as a missing
map-unit link. Miscellaneous-area absence is distinguished from other absent
profiles. Boundary touches are retained but do not supply positive-area coverage.

The topic stays `review_required`, with `inventory_intersections_usable=true`
only when those checks pass. This boolean permits bounded inventory use, not
suitability screening. Stale soil snapshots produce `stale`; absent intersecting
evidence produces `missing`. No new status enum is introduced.

Packets include polygon/correction/event/source hashes, map-unit/component/horizon
rows and provenance, project scale, dated survey metadata, the bounded unit
dictionary, raw low/representative/high values and per-field missingness. Component
percent totals and unlisted remainders are preserved without normalization or
invented component footprints. Vermont-specific `vtsepticsyscl` remains visible as
excluded source interpretation, never a Maine septic approval.

The reviewed metadata report is verified by its exact hash before use. Geometry
review dependencies and the requested soil snapshot join the existing context
comparison; acceptance, withdrawal, reacceptance or a changed finding invalidate
older packets. Extraction stays one REPEATABLE READ READ ONLY transaction, using
existing snapshots only. Consumers must refresh/check before reuse. Soil
suitability stays UNKNOWN and the overall packet remains unqualified for parcel
screening. Septic/buildability checks remain purchase-triggered.

## Component gaps: evidence and conclusion

USDA's [Fundamental Query](https://sdmdataaccess.sc.egov.usda.gov/documents/FundamentalQuery.pdf),
version 1.1, printed page 5, explicitly permits component totals below 100% where
some minor components are not individually recorded. It also describes a possible
reason for totals above 100%; no such over-total occurred in the pinned county
subset. This general explanation does not identify omitted components at a site.

A fresh direct query of **all 262 county-linked map units with percentage deficits**
returned **716 component records**. Keys, names, kinds, major flags and all three
percentage fields exactly matched the original capture. There were no new or
missing keys. The original complete-table capture also reconciled source counts.

**DERIVED conclusion:** this bounded comparison finds no retrieval omission in
those components. The deficits are present in USDA's source representation and
consistent with the documented treatment of minor components. Their identities,
properties and locations remain UNKNOWN. Preserve 75–99% totals and the 1–25%
unlisted proportion. Do not normalize them to 100%, fabricate missing rows, or
resolve the broader soil qualification finding merely because this cause is
corroborated. The comparison does not certify every other attribute unchanged.

Evidence:

- [Component comparison](component-gaps.json), including exact compared fields.
- [Official source queries and hashes](gap-sources.json).
- [Private archive readback](gap-archive-verification.json): four objects verified.
- [Validation summary](validation.json) and [live diagnostic checks](live-tests.json).

TL-F-0113 receives an append-only investigation update and remains in progress.
No corrections, source attributes or parcel qualification states are modified.

## Reproduction

```sh
python scripts/investigate_soil_components.py \
  --bundle .local/county-soils-prepared-final --output .local/new-component-check
python -m unittest discover -s tests -p test_area_qualification.py
python -m unittest discover -s tests -p test_soil_availability.py
python tests/check_area_qualification_sql.py
python scripts/qualify_area.py capture \
  --request .local/request-with-soils.json --output .local/new-soil-packet
python scripts/qualify_area.py check --packet .local/new-soil-packet/packet.json
```

Raw packets and requests remain private. Use the existing SQL-editor export path
when appropriate; exports must match the complete request and represent a fresh
context. The live diagnostic harness uses one credential acquisition/session,
appends only the gap-finding event before captures, and checks fresh dependencies
for both resulting packets. It does not select land for purchase.
