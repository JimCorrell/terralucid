# Why the 0443D revision map looked blank

## Finding

The blank region is caused by an **opaque white PDF layer named MASK**. The
original 2024 FEMA revision document already contains hazard graphics beneath it.
Hiding that specific layer in a temporary diagnostic view reveals flood graphics
at the same location as the previously captured service rendering.

This explains the **display discrepancy** recorded in the prior investigation.
It does not establish why FEMA applied the mask, whether its covered graphics
are operative regulatory content, or whether LUPC adopted the revision.
Those questions remain UNKNOWN. The published display and exact original PDF
are preserved; the diagnostic view does not replace either.

## Evidence and controlled comparison

Source: [FEMA case 22-01-0871P, Osborn determination](https://msc.fema.gov/portal/downloadProduct?productTypeID=LOMC&productSubTypeID=LOMR&productID=22-01-0871P-230595),
effective May 31, 2024; PDF page 8, panel **23009C0443D**. This investigation
reuses the archived bytes and NFHL rendering from earlier audits. No new FEMA
source snapshot was fetched.

| Check | Result |
| --- | --- |
| Original PDF SHA-256 | `fcef7a0a0838e02a45ded5ab071078e5f4938ae02c2849b4bd1639bfb333320b` |
| Page resource | `OC6` references optional-content group **103**, named `MASK` |
| Paint | One opaque white four-segment path covers the whole diagnostic crop |
| Diagnostic crop | PDF points `[560, 240, 740, 390]`, containing the prior approximate locator for OBJECTID 27129510 |
| Display change | Exclude group 103 only, by object reference |
| Map content | All page drawing-instruction streams unchanged |
| Control pages | Pages 7 and 9 render identically before/after |
| Reversibility | Restoring the mask reproduces the original crop pixel-for-pixel |
| Original file | Bytes unchanged; no modified PDF saved or published |

The recorded group metadata identifies an Esri ArcMap layer, but a technical
layer name and creator do not explain its regulatory purpose. Another page has
another group named MASK: selection by name alone could affect both. The method
therefore targets the exact object reference in the checksum-pinned PDF.

The temporary rendering configuration is reopened **in memory** so the renderer
uses the new state. Serialization can re-encode PDF dictionaries; the method
checks the catalog-only change before serialization and unchanged page content
streams afterward. It does not rewrite the source file, draw new features or
change any GIS geometry. See the archived [PyMuPDF layer reference](https://pymupdf.readthedocs.io/en/latest/document.html#Document.set_layer).

The DERIVED [report](report.json) records the mask path, state checks, hashes and
private diagnostic image paths. [review.json](review.json) separates observed
content, diagnostic interpretation and regulatory unknowns.

## What this changes

The earlier statement that the default map view is blank remains correct.
Additional layer inspection now explains that blankness; it is not evidence that
the PDF lacks hazard graphics. The newly exposed pattern provides visual context
for the smaller polygon. It does not certify the exact vertex-touch topology,
survey accuracy or equivalence of all map/service geometry.

The original approximate locator is reused without changing its coordinates.
The earlier NAD83/NAD83(2011) realization qualification remains. The correspondence
is visual corroboration only, with no map tracing or inferred legal boundary.

- **TL-F-0105 remains in progress:** the display cause is explained; mask purpose,
  status of the covered content, revision coverage and legal adoption remain open.
- **TL-F-0026 remains in progress/high:** the two exact-version decoding proposals
  gain additional map context but remain unaccepted. Candidate files and hashes,
  original exclusions and all existing screenings are unchanged.

A future consumer must retain the published map, identify any diagnostic layer
state explicitly, and carry the regulatory qualifications forward. Do not use a
mask-hidden rendering as an authoritative replacement map or as flood clearance.
No publisher inquiry has been sent.

## Reproduction and archive

Restore dependencies listed in `report.inputs` from private content-addressed
storage. Reconstruct the original PDF from the existing three byte-part objects
using the earlier FEMA `restore` helper, verifying its full hash, and place it at
`research/osborn-fema/large-documents/osborn-lomr-document.response`.

With PyMuPDF 1.24.14 and the existing Shapely/pyproj investigation environment:

```sh
python3 scripts/investigate_fema_map_mask.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/investigate_fema_map_mask.py \
  --prepare .local/fema-mask-load --current .local/fema-mask-current.json
```

The current input contains fresh administrative `finding_id`/`event_id` rows for
TL-F-0105 and TL-F-0026. Upload prepared objects to the existing private bucket,
download the manifest objects, and verify before applying `load.sql`:

```sh
python3 scripts/investigate_fema_map_mask.py \
  --verify-download .local/fema-mask-download --prepared .local/fema-mask-load
```

Verification includes both labeled diagnostic PNGs and reconstruction of the
original PDF. Only the library-reference page is a new retrieval observation;
FEMA evidence is reused through pinned prior-audit references. The atomic load
adds one audit and two finding occurrences/reviews. It does not introduce a
schema migration, geometry acceptance or screening mutation. Exact SQL replay is
idempotent. Raw PDF, service rendering and derived crops remain private.

## Applied checkpoint

Audit `b06c8d155bc23b05a3bc0f7d221a7ff53bc2924021d379762ea7731515a00e35`
is recorded in Supabase with one new technical-reference observation and two
finding occurrence/review appends. All **18 manifest objects** were downloaded
and verified, including reconstructed original PDF bytes and both diagnostic PNGs.

TL-F-0105 remains **in_progress/medium** with four occurrences; TL-F-0026 remains
**in_progress/high** with three. Their `needs_revisit=false` flags indicate review
currency, not resolution of remaining unknowns. There are still 43 findings,
with 68 historical review events.

Both proposed geometry files retain their original hashes. Complete geometry
correction/event and screening-history fingerprints match before/after. The
2,648 default screenings, 119 holds, 153 revisions and zero stale defaults remain.
The bucket is private and checked client access remains denied. All 54 Python
tests pass, including the same-name mask isolation test; the report reproduces
byte-for-byte.
