"""Offline integrity checks; run with python3 -m unittest discover -s tests."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('staging', Path(__file__).parents[1] / 'scripts/prepare_source_staging.py')
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)


class SourceStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audit = self.root / 'audit'
        shutil.copytree(staging.AUDIT, self.audit)
        self.output = self.root / 'prepared'

    def test_archive_roundtrip_and_error_preservation(self):
        result = staging.prepare(self.audit, self.output)
        self.assertEqual((result['sources'], result['observations'], result['geometry_samples']), (22, 34, 3))
        self.assertEqual(result['outcomes'], {'JSON_RECEIVED': 33, 'API_ERROR': 1})
        self.assertEqual(staging.verify(self.output, self.output / 'objects')['verified_objects'], 38)
        # Simulate corrupt downloaded bytes; verification must fail.
        next((self.output / 'objects/sha256').glob('*')).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            staging.verify(self.output, self.output / 'objects')

    def test_altered_source_stops_before_output(self):
        next((self.audit / 'runs').glob('*/*.response')).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            staging.prepare(self.audit, self.output)
        self.assertFalse(self.output.exists())

    def test_unexpected_crs_is_rejected_even_with_valid_checksum(self):
        log = self.audit / 'runs/2026-09-19-profile/results.json'
        records = json.loads(log.read_text())
        record = next(r for r in records if r['id'] == 'organized-parcels-geometry')
        response = log.parent / record['response_file']
        payload = json.loads(response.read_text())
        payload['crs']['properties']['name'] = 'EPSG:3857'
        data = json.dumps(payload).encode()
        response.write_bytes(data)
        record.update(sha256=staging.digest(data), bytes=len(data))
        log.write_text(json.dumps(records))
        with self.assertRaises(ValueError):
            staging.prepare(self.audit, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
