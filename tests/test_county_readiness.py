import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from assess_county_readiness import ids,summarize_catalog
class ReadinessTests(unittest.TestCase):
    def test_empty_ids_are_observation(self):
        self.assertEqual(ids({'objectIds':None}),[])
    def test_error_or_truncation_is_not_absence(self):
        for value in [{'error':{'code':500}},{'objectIds':[],'exceededTransferLimit':True},{}]:
            with self.assertRaises(ValueError):ids(value)
    def test_invalid_catalog_rejected(self):
        with self.assertRaises(ValueError):summarize_catalog({'error':'failed'})
if __name__=='__main__':unittest.main()
