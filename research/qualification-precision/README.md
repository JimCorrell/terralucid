# Qualification coverage precision — 2026-09-23

Local follow-up `qualification-numerical-precision` from PR #54 is resolved for
the observed cases. This is an offline replay of four immutable private captures,
not a fresh Supabase extraction or a statement of present source currency. No
source geometry, correction, finding event or database record was changed.

## Evidence and change

The overlapping-source AOI has an input geometry equal to the AOI. That input
covers it, yet union followed by intersection and difference reported a
5.426966254162835e-08 m² gap. Even removing the intermediate intersection left a
7.169929235018805e-10 m² gap. The input containment proves that these derived
slivers cannot represent missing coverage in this set of stored geometries.
It does not prove the assessment boundary is legally correct.

The accepted-area example's old fractions were 1.0000000000000002, despite zero
uncovered area. Independent covered-area division introduced the discrepancy.

Coverage now checks whether any effective input covers the AOI before overlay.
If so, it reports fraction 1 and gap 0. Otherwise it measures AOI minus the union
and derives the fraction from the uncovered-area complement, bounded to [0, 1].
The output records the calculation basis. There is no tolerance, snapping or
geometry repair. Any positive gap remains partial, even when its percentage
rounds to 100%. Collective overlays still have floating-point limits; this fix
is not a universal proof that all tiny gaps are artifacts.

## Replay results

- Overlapping-source identity coverage is full; all three identity overlap
  candidates remain. Zoning remains partial at approximately 1.07% coverage.
- The parcel near the held zoning feature retains its hold and blocked zoning
  intersections. Its approximately 5.776 m² gap remains partial.
- Accepted-area fractions are exactly 1. Orneville retains full coverage and its
  archived FEMA evidence with applicability unknown.
- All noncoverage evidence, holds, permissions, source references, purchase
  requirements and screening/offer limits match the previous packets exactly.
- Previous packets require revisit because the method hash changed. Regeneration
  from a saved capture does not refresh the capture's source dependencies.

[Aggregate replay report](report.json) pins capture file hashes and method/runtime,
with before/after coverage measurements. Original PR #54 measurements remain in
[the historical report](../county-qualification-tests/report.json).

## Reproduce

```sh
python3 -m unittest discover -s tests -p test_area_qualification.py
python3 tests/replay_qualification_precision.py /path/to/private/PR54-capture-directory
```

25 unit tests pass, including a synthetic projected-coordinate union-sliver
reproducer, collective full coverage, genuine small gaps (down to 1e-18 m²),
missing/disjoint/touching coverage and the existing hold/dependency tests. The
four-capture replay asserts unchanged noncoverage results and method invalidation.
Source SQL and database behavior are unchanged; no new live authentication was
needed. Raw assessment geometries and private packet evidence remain uncommitted.
