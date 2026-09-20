"""Coverage claims must reject incomplete evidence and preserve uncertainty."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).parents[1] / 'scripts/audit_maine_coverage.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class CoverageAuditTests(unittest.TestCase):
    def test_date_precision_and_invalid_values(self):
        self.assertEqual(audit.parse_date('2011')['precision'], 'year')
        self.assertEqual(audit.parse_date('4/1/2011')['value'], '2011-04-01')
        self.assertEqual(audit.parse_date('20240229')['value'], '2024-02-29')
        for raw in [None, '', ' ', '0', '20', '20230229', '13/1/2020']:
            self.assertEqual(audit.parse_date(raw)['state'], 'UNKNOWN')
            self.assertIsNone(audit.parse_date(raw)['value'])

    def test_reject_truncated_aggregate(self):
        with self.assertRaises(ValueError):
            audit.attributes({'features': [], 'exceededTransferLimit': True})

    def test_recorded_audit_invariants(self):
        report = audit.derive(audit.AUDIT)
        self.assertEqual(report['summary']['status_coded_reference_codes'], 917)
        self.assertEqual(report['summary']['parcel_source_union_codes'] + report['summary']['neither_parcel_source_codes'], 917)
        self.assertEqual(sum(report['join_sample']['cardinalities'].values()), 321)
        self.assertTrue(any(not r['geocodes_agree'] and r['assessment_rows'] for r in report['join_sample']['results']))
        # Raw conflict codes and unmatched source codes must survive; no automatic reassignment.
        self.assertTrue(any(x['source_group'].get('TOWN') == 'Sweden' and x['source_group']['GEOCODE'] == '17290' for x in report['code_name_conflicts']))
        self.assertTrue(any(x['source_group']['GEOCODE'] == '65185' for x in report['unrecognized_source_groups']))
        for row in report['jurisdictions']:
            self.assertTrue(all(x['completeness'] == 'UNKNOWN' for x in row['sources'].values()))

    def test_reject_altered_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'audit'
            shutil.copytree(audit.AUDIT, target)
            response = next((target / 'runs').glob('*/*.response'))
            response.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                audit.derive(target)


if __name__ == '__main__':
    unittest.main()
