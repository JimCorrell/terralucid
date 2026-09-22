# Reproduction and applied evidence

Restore each `report.inputs` path from its private object
`sha256/<hash>.response`. Restore source responses to their `response_path`
from `report.evidence`, verifying recorded byte counts and hashes. Restore the
unchanged product ZIP; its TIFF and README member hashes are in the report.
Diagnostic PNGs are also pinned inputs. They are full-page visual-review
artifacts, not new authoritative maps.

With the established PyMuPDF 1.24.14 environment:

```sh
python3 scripts/assess_county_readiness.py
python3 -m unittest discover -s tests -p test_county_readiness.py
```

The generated report must match the archive manifest's audit hash. The spatial
probe envelope is the min/max of every source ring vertex of civil-boundary
OBJECTID521, GEOCODE21821, from archived county capture page1, EPSG:26919:
`499386.8127,4997082.9998,511275.0625,5008399.5`. This is a conservative
request rectangle, not a surveyed jurisdiction or parcel boundary. No area
or georeferenced raster intersection is calculated here.

`prepare_county_readiness.py --output <fresh-directory>` checks method, inputs,
response logs and source scope, stages content-addressed archive objects and
creates atomic append SQL. Its inherited snapshot guard serializes against
county correction writers, and the finding append expects the reviewed prior
event. For a new assessment, first refresh dependencies and finding tokens;
do not reuse this historical baseline as current. Download and verify all
manifest objects with the existing `apply_prepared_load.py` workflow before
applying. Never run synthetic mutation tests against the live project.

`check_county_readiness.sql` is read-only. The applied readback and
`checkpoint.json` record this review's live result separately from its original
baseline. It does not modify acceptance, qualification, or screening data.
