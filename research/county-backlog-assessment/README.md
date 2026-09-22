# Piscataquis backlog assessment after PR #44

## Recommendation

Move from three-at-a-time county cleanup to **grouped evidence review followed by parcel-triggered exceptions**. The computational checks are repeatable for most remaining features; source/map corroboration and exact-version acceptance are still required. This document proposes a workflow, not a new acceptance policy.

## What the assessment found

| Measure | Result |
| --- | ---: |
| Remaining zoning / parcel holds | 145 / 21 |
| Zoning cases passing existing geometry, cycle and fill checks | 140 |
| Zoning exceptions requiring another method or more source evidence | 5 |
| Distinct source map labels / labels among passing cases | 92 / 89 |
| Parcel cases passing the same computational checks / exceptions | 18 / 3 |
| Conditional combined gain from all passing zoning cases | 128.743 km² |
| Combined upper bound from every held zoning envelope | 534.666 km² |
| Current inventory gap outside all held zoning envelopes | 5,995.506 km² |

Passing means **archived-source computational feasibility**, not a reviewed correction. This assessment reuses the original archived capture; it makes no fresh-source or legal-currency claim. No candidate geometry artifacts were saved, no proposals activated, and no live findings or ranking changed.

The remaining holds comprise 131 ring self-intersections and 14 ambiguous/uncontained-hole decoder results. Detailed split types, ownership checks, source fingerprints and unsupported reasons are retained in [the report](report.json). Shared errors alone do not establish shared fixes.

## Coverage returns

The existing ranking uses bounding-box overlap. It is a conservative investigation bound, not expected recovered area. This assessment constructs temporary interpretations for the passing cases and measures their contribution inside the remaining inventory gap. Accepted geometry is excluded and overlapping contributions counted once.

| First cases by individual conditional gain | Combined conditional gain | Share of all passing-case scenario |
| ---: | ---: | ---: |
| 3 | 46.258 km² | 35.9% |
| 5 | 57.280 km² | 44.5% |
| 10 | 80.948 km² | 62.9% |
| 20 | 117.521 km² | 91.3% |
| 40 | 127.565 km² | 99.1% |
| 140 | 128.743 km² | 100.0% |

This ordering is reproducible, not an optimization of marginal gain. These are conditional results for passing cases only; the five exceptions have unknown gains. The 100 cases after the first 40 add only 1.178 km² in this scenario. A small coverage gain may still matter greatly to an individual property.

### Proposed first evidence-review batch

Review the ten largest conditional contributors together, sharing map/source retrieval where applicable while preserving per-feature evidence. Ten is a proposed manageable batch size, not a finding about reviewer capacity.

| OBJECTID | Source map | Zone | Conditional individual gain | Previous envelope rank |
| --- | --- | --- | ---: | ---: |
| 27342226 | beaver-cove | M-GN: General | 32.4023 km² | 4 |
| 27365331 | t7-r10-wels | P-SL2: Shoreland - 75' | 7.1264 km² | 14 |
| 27364426 | orneville-twp | P-SL2: Shoreland - 75' | 6.7297 km² | 9 |
| 27339379 | bowdoin-college-grant-west-twp | P-SL2: Shoreland - 75' | 5.7875 km² | 6 |
| 27364538 | t5-r14-wels | P-SL2: Shoreland - 75' | 5.2336 km² | 23 |
| 27324664 | t1-r13-wels | P-SL2: Shoreland - 75' | 4.9661 km² | 21 |
| 27321394 | t4-r9-nwp | P-SL2: Shoreland - 75' | 4.9646 km² | 5 |
| 27366878 | shawtown-twp | P-SL2: Shoreland - 75' | 4.6951 km² | 11 |
| 27261431 | t3-r13-wels | P-SL2: Shoreland - 75' | 4.5692 km² | 13 |
| 27304932 | t4-r12-wels | P-SL2: Shoreland - 75' | 4.4738 km² | 10 |

Individual gains overlap and must not be summed. This proposed order supplements the published ranking; it does not replace that live result.

## Exceptions remain visible

| OBJECTID | Source map | Envelope upper bound | Reason existing methods rejected it |
| --- | --- | ---: | --- |
| 27358396 | katahdin-iron-works-twp | 26.8643 km² | Expected one twice-visited vertex |
| 27367116 | t7-r10-wels | 1.8592 km² | Expected one twice-visited vertex |
| 27326991 | t3-r8-wels | 0.3017 km² | Expected one twice-visited vertex |
| 27312797 | sapling-twp | 0.0049 km² | Expected one twice-visited vertex |
| 27237435 | sapling-twp | 0.0000 km² | Expected one twice-visited vertex |

**Katahdin Iron Works OBJECTID 27358396 deserves a parallel exception investigation**: its 26.86 km² envelope upper bound is material, even though the actual recoverable area is unknown. The five bounds overlap and are not additive; the percentages above do not cover these exceptions.

The [parcel assessment](parcel-holds.json) accounts for all 18 UT and three organized-source holds. Existing methods fail on UT OBJECTIDs 90153 and 109315 and organized-source OBJECTID 407265. The other 18 passing checks do not establish surveyed boundaries or authorize reuse of the zoning acceptance validator. These are broader-capture features; county-interior relevance remains to be checked.

## Proposed stopping and restart rules

1. **Next batch:** compare the ten cases above against native service/GeoJSON representations and official maps. Separate changed sources, contradictions and unsupported interpretations. Only then propose exact-version corrections with the existing acceptance tests.
2. **Checkpoint after that batch:** refresh actual accepted gains and the conditional curve. Also investigate the high-bound Katahdin Iron Works exception before concluding that the remaining work has low coverage value. Continue broad cleanup only if remaining cases contribute materially to the search area or unblock selected parcels. Use the curve to discuss that tradeoff, rather than adopt an unagreed area or percentage threshold.
3. **Parcel trigger:** reopen a deferred case whenever its conservative envelope intersects a candidate parcel or its area of interest, its source version changes, or new authoritative evidence contradicts the retained interpretation. Until resolved, the affected zoning/boundary result remains UNKNOWN or held; absence of valid overlay is never clearance.
4. **Five zoning exceptions and three parcel exceptions:** keep a separate investigation queue. Prioritize when they affect a candidate area or potentially material coverage; do not force them through the repeatable method.
5. **County completion is not a prerequisite for bounded evaluation:** first implement a parcel/area qualification check that captures current correction dependencies, source identities, applicable zoning evidence, held-envelope intersections and unresolved findings. It must withhold conclusions affected by holds. The existing inventory remains unqualified for parcel screening until that work is implemented and reviewed.

## Work geometry cleanup cannot finish

The envelope-union result shows how much of the current inventory gap cannot be reached by any interpretation bounded by the held source envelopes. That does **not** establish absent legal zoning. Coverage scope, municipal applicability and source limitations need separate investigation.

The [county inventory](../piscataquis-ingestion/README.md) already records 24 jurisdictions with both parcel sources, uncertain source dates and wetland imagery from 1984–1986. These need identity, currency and use-specific qualification. Big Moose and T1 R11 amendment-date discrepancies remain open. Access/title, boundary authority and septic/buildability still require parcel-level evidence. Small-area deferral does not remove any of these requirements.

## Evidence and verification

- [Report](report.json): all 145 zoning cases, pinned source and method hashes, conditional scenarios and exception reasons.
- [Parcel holds](parcel-holds.json): full scan of 8,391 UT and 10,080 organized capture records, 21 held cases, computational feasibility only.
- [Live baseline](live-baseline.json): read-only confirmation that the PR #44 snapshot is current at its recorded verification time, 17 acceptances and unchanged originals. Recheck before future use.
- [Tests](test-results.json): input hashes, complete unique cohorts, current baseline, union bounds and sequential direct-overlay checks of the top three conditional contributors. The independent calculation still uses GEOS; it is not independent publisher evidence.

Reproduce with archived private inputs restored at report paths and the recorded Shapely/GEOS runtime:

```sh
python scripts/assess_county_backlog.py
python scripts/assess_county_parcel_holds.py
python tests/check_county_backlog_assessment.py
```

For a fresh baseline, run `scripts/check_seventeen_correction_ranking.sql` read-only and retain its result, or capture a new dependency set if corrections have changed. Inputs from the original county archive and PR #44 remain in private storage; this assessment adds metadata only.
