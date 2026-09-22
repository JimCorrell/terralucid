# Piscataquis readiness after PR #49

## Assessment

**Ready for bounded evidence research; not yet qualified for automated parcel
screening or offer readiness.** Finish the consumer's parcel/AOI qualification
checks before spending more cycles on county-wide geometry repair. This is a
recommendation, not a new acceptance policy or a change to qualification flags.

The fresh read-only [baseline](baseline.json) confirms 120,449 inventory rows,
28 accepted exact-version corrections, 134 zoning and 21 parcel geometry holds,
unchanged original fingerprints and zero qualified rows. The 28-correction ranking
snapshot remains current. Rows include source variants and metadata; this is not
120,449 unique parcels. Historical backlog curves are not recalculated here and
must not be presented as the current remaining repair benefit.

| Topic | Evidence available | What must still happen |
| --- | --- | --- |
| Parcel inventory | County capture includes both assessment sources; each of 113 civil codes has some valid parcel intersection | Resolve identity/source overlap for the selected property, confirm freshness and retain boundary uncertainty; 24 jurisdictions intersect both sources |
| Zoning | LUPC inventory, 28 accepted interpretations and map-date research | Route to the actual authority; municipal zoning has not been loaded. Check held envelopes, coverage gaps, amendments and current applicability for the selected area |
| Wetlands | County package has 58,584 positive-area feature intersections and 107 project footprints with no computed county footprint gap | Retain 1984–1986 imagery age and completeness uncertainty; mapped absence is not a site determination |
| FEMA | Prior detailed work concerns Osborn in Hancock County; new Orneville evidence below | A qualified Piscataquis flood overlay has not been established. Route each area to digital or scanned products and applicable letters |
| Access, title, septic/buildability | First-class requirements, not established by the inventory | Property-specific records, rights, constraints and professional/site evidence before affected conclusions or offer readiness |

Counts and date limitations come from the [original county evaluation](../piscataquis-ingestion/README.md),
with geometry status updated from the current baseline. Its original per-town
zoning fractions are historical and are not current corrected coverage measures.
Assessment geometry, civil limits and overlap candidates remain distinct from
legal boundaries and canonical parcel identity.

## Orneville: mapped flood evidence exists

The official [MSC catalog](https://msc.fema.gov/portal/advanceSearch) community
query for **230465** identifies **ORNEVILLE, TOWNSHIP OF**, with effective-category
product **230465A**, dated **April 17, 1987**. The downloaded
[official FIRM](https://msc.fema.gov/portal/downloadProduct?productTypeID=FINAL_PRODUCT&productSubTypeID=FIRM_PANEL&productID=230465A)
is a ZIP containing an unchanged four-page TIFF and FEMA's README PDF.
All four TIFF pages were visually inspected:

- Page 1 is the index for panels 01–04; panel 03 is marked not printed, area in Zone C.
- Page 2 is panel 01 and shows Zone A along Alder Stream.
- Page 3 is panel 02 and shows Zone A around Freese Bog, Boyd Lake and Dead Stream.
- Page 4 is panel 04 and shows Zone A around Boyd Lake and Dead Stream.
- The printed panels state April 17, 1987. Zone A's legend says base flood
  elevations are not determined. These observations establish map contents;
  they do not locate an assessment parcel within a zone.

The same catalog returns **27 effective-category LOMAs**, all associated with
230465A. Their displayed dates range from November 15, 2007 through September 16,
2026. No effective-category LOMR or revalidation relation was returned. The
letter documents were not reviewed: catalog dates, status and associations are
not determinations of parcel applicability or a guarantee of complete revision
history. A state NFHL download appearing in the catalog does not establish local
digital flood-zone coverage.

NFHL queries returned no jurisdiction feature for CID 230465, no availability
polygon IDs and no hazard polygon IDs for the archived Orneville civil-boundary
envelope (EPSG:26919). The panel layer returned two envelope candidates,
OBJECTIDs 546495 and 546496; both follow-up detail requests failed, so their
identity and actual Orneville intersection remain unverified. An envelope match
is not coverage. The successful empty hazard/availability responses describe
these queries only; they do not contradict the scanned map's Zone A areas.
Initial request failures and retries are retained separately from successful
empty results.

The [ZP796 investigation](../orneville-zp796/README.md) established the separate
August 1, 2024 text-correction effective date and the FIRM-only reference. Neither
that correction nor absent P-FP display supersedes this flood evidence. Panel 03's
historical publication note is not present-day flood clearance.

The [Maine mapping guidance](https://www.maine.gov/moca/programs/floodplain-management-program/mapping-resources)
distinguishes current digital NFHL from approximate Q3 mapping and requires Q3
confirmation against official printed FIRMs. Q3 has not been qualified or loaded
in this review. No raster tracing, georeferencing or replacement flood geometry
is proposed.

## Next bounded work (recommended order)

1. **Implement and test a parcel/AOI evidence packet.** Pin source versions and
   current correction dependencies; keep competing assessment identities;
   intersect applicable held envelopes and surface missing coverage. Report
   readiness separately for zoning, wetlands and flood evidence, with reasons.
   Unknown or stale dependencies must withhold the affected conclusion. Test
   held-envelope intersections, source overlaps, missing municipal zoning,
   raster-only flood evidence and dependency changes before ranking parcels.
2. **Build a county FEMA product/coverage inventory.** Start with Orneville as a
   regression example: scanned map availability is different from digital
   polygon availability. Reconcile county/community catalogs and spatial
   availability; retain panels, dates and letters. The county catalog captured
   here is discovery evidence, not a completed community-by-community audit.
3. **Exercise the packet on selected land or a bounded search area.** Review
   applicable letters, current zoning and identity conflicts there. Reopen
   deferred geometry cases when their conservative envelope intersects that
   area, a source changes, or authoritative evidence contradicts an interpretation.

There is no defensible county completion percentage: record validity, geographic
coverage, currentness and transaction due diligence measure different things.
The remaining geometry backlog alone should not determine when research begins.
Keep critical access/title, boundary and septic/buildability unknowns visible
until resolved before offer readiness.

## Evidence and scope

Request manifests, response hashes, retrieval failures and the deterministic
[report](report.json) accompany this review. Raw source responses and diagnostic
images are private archive objects, not Git files. Catalog counts are observed
responses, not regulatory absence claims. This assessment appends TL-F-0029;
Osborn-specific findings remain separate. Original source values, all correction
versions, the ranking and qualification flags are unchanged.
