"""Reject service error bodies and incomplete/ambiguous source membership."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_lupc_currency import complete_features, index, reconcile


class CurrencyEvidenceTests(unittest.TestCase):
    def test_http_success_error_body_is_not_empty_coverage(self):
        with self.assertRaises(ValueError):
            complete_features({'error':{'code':499,'message':'Token Required'}})

    def test_truncated_attribute_response_is_rejected(self):
        with self.assertRaises(ValueError):
            complete_features({'features':[{'attributes':{'OBJECTID':1}}], 'exceededTransferLimit':True})

    def test_unique_identity_required_for_cross_service_matching(self):
        with self.assertRaises(ValueError):
            index([{'GlobalID':'same'},{'GlobalID':'same'}],'GlobalID')

    def test_membership_mismatch_duplicate_and_wrong_map_rejected(self):
        rows=[{'OBJECTID':1,'MAP':'osborn'}]
        for ids,rr in [([1,2],rows),([1,1],rows),([1],[{'OBJECTID':1,'MAP':'other'}])]:
            with self.subTest(ids=ids,rows=rr),self.assertRaises(ValueError):
                reconcile({'objectIds':ids},rr)
        reconcile({'objectIds':[1]},rows)


if __name__=='__main__':unittest.main()
