"""Evidence gates: do not treat failed captures, CRS ambiguity or damaged parts as data."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_osborn_fema import CRS, features, reconcile, parts, restore
from prepare_source_staging import digest


class FemaEvidenceTests(unittest.TestCase):
    def test_error_and_truncation_are_not_empty_coverage(self):
        for payload in [{'error':{'code':500},'features':[]},
                        {'features':[],'exceededTransferLimit':True}]:
            with self.subTest(payload=payload),self.assertRaises(ValueError):features(payload)

    def test_native_crs_must_be_explicit(self):
        for crs in [None, {'type':'name','properties':{'name':'EPSG:4326'}}]:
            with self.subTest(crs=crs),self.assertRaises(ValueError):
                features({'type':'FeatureCollection','crs':crs,'features':[]},True)
        self.assertEqual(features({'type':'FeatureCollection','crs':CRS,'features':[]},True),[])

    def test_id_membership_and_uniqueness(self):
        for ids,rows in [([1,2],[{'OBJECTID':1}]),([1,1],[{'OBJECTID':1}]),
                         ([1],[{'OBJECTID':1},{'OBJECTID':1}])]:
            with self.subTest(ids=ids),self.assertRaises(ValueError):reconcile({'objectIds':ids},rows)

    def test_multipart_original_verified_not_just_individual_parts(self):
        data=b'original PDF bytes'
        document={'retrieval':{'sha256':digest(data),'bytes':len(data)},'parts':parts(data)}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'sha256').mkdir()
            (root/document['parts'][0]['storage_object']).write_bytes(data)
            self.assertEqual(restore(document,root),data)
            wrong=copy.deepcopy(document);wrong['retrieval']['sha256']='0'*64
            with self.assertRaises(ValueError):restore(wrong,root)
            wrong=copy.deepcopy(document);wrong['parts'][0]['offset']=1
            with self.assertRaises(ValueError):restore(wrong,root)
            (root/document['parts'][0]['storage_object']).write_bytes(data[:-1])
            with self.assertRaises(ValueError):restore(document,root)


if __name__=='__main__':unittest.main()
