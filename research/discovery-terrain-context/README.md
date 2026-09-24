# Terrain context alongside parcel evidence

The area evidence packet now adds frozen terrain catalog candidates alongside
identity, zoning, wetlands, flood and optional soils. A discovery summary presents
all topic statuses together. This implements the user's decision to defer terrain
source adjudication until it could affect a purchase decision.

This release routes candidates and uncertainty; it does not supply parcel slopes,
claim elevation availability, select a preferred source or clear TL-F-0104. Raster
retrieval remains bounded/on demand. Existing topic holds and freshness checks
remain active; purchase-specific investigations remain opt-in through the existing
purchase-candidate request flag.

## Validation

[Offline replay results](report.json) cover five historical private captures:

| Saved case | Terrain catalog candidates | Soils included in capture |
| --- | ---: | --- |
| Orneville source parcel | 2 | Yes |
| Accepted zoning area | 3 | No |
| Orneville parcel | 2 | No |
| Overlapping sources | 4 | No |
| Parcel near hold | 1 | No |

The raw captures and regenerated packets stay private. These replays are **not
current database checks** and do not authorize reuse of saved packets without
fresh dependency validation. Source findings and geometry dependencies may have
changed since capture.

25 existing area-qualification tests and four new terrain-context tests pass.
New coverage checks real pilot catalog IDs without promoting availability,
no-candidate unknowns, catalog/selection mismatch, purchase-triggered suitability,
and method-change invalidation. Packet schema is version 3. Catalog/report hashes
and projection runtime join the method dependency hash.

Use the existing capture/check workflow in
[area qualification](../../docs/area-qualification.md). Include its optional soil
batch/snapshot to obtain all available topic evidence in one packet. The next
practical step is a fresh packet for a user-selected parcel or AOI, then bounded
source-specific elevation retrieval if relevant to the decision.
