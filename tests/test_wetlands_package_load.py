import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_wetlands_package_load import candidates

class PackageCandidates(unittest.TestCase):
    def fixture(self):
        return {'records':[{'candidates':[dict(package_objectid=1,hausdorff_distance_m=1.025,code_agrees=True,type_agrees=True)]}],'reverse_scope_records':[{'object_id':1}]}
    def test_retains_exact_candidate(self):self.assertEqual(candidates(self.fixture())[0][1]['package_objectid'],1)
    def test_rejects_classification_conflict(self):
        d=self.fixture();d['records'][0]['candidates'][0]['code_agrees']=False
        with self.assertRaises(ValueError):candidates(d)
    def test_rejects_multiple_and_shared_candidates(self):
        d=self.fixture();d['records'][0]['candidates']*=2
        with self.assertRaises(ValueError):candidates(d)
        d=self.fixture();d['records']*=2
        with self.assertRaisesRegex(ValueError,'Shared'):candidates(d)
    def test_rejects_scope_change(self):
        d=self.fixture();d['reverse_scope_records']=[]
        with self.assertRaisesRegex(ValueError,'scope'):candidates(d)
