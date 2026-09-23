import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_county_soils import rows,sha
from prepare_county_soils import verified_responses,validate_geometry
from pyproj import Transformer

class SoilEvidenceTests(unittest.TestCase):
    def test_column_contract_and_string_keys(self):
        self.assertEqual(rows({'Table':[['mukey','value'],['000123',None]]}),[{'mukey':'000123','value':None}])
        for bad in [{},{'Table':[['key','key'],['a','b']]},{'Table':[['key'],['a','b']]}]:
            with self.assertRaises(ValueError):rows(bad)
    def test_invalid_polygon_preserved_as_hold(self):
        source='POLYGON ((0 0, 1 1, 0 1, 1 0, 0 0))'
        g,p,hold=validate_geometry(source,lambda x,y:(x,y))
        self.assertIsNone(g);self.assertIsNone(p);self.assertIn('Self-intersection',hold)
    def test_valid_geometry_keeps_source_and_projects(self):
        source='POLYGON ((-69 45,-68.99 45,-68.99 45.01,-69 45.01,-69 45))'
        g,p,hold=validate_geometry(source,Transformer.from_crs(4326,26919,always_xy=True).transform)
        self.assertIsNone(hold);self.assertEqual(g.bounds,(-69,45,-68.99,45.01));self.assertTrue(p.is_valid);self.assertGreater(p.area,800000)
    def test_nonpolygon_rejected(self):
        for text in ['POINT (0 0)','POLYGON EMPTY','bad']:
            self.assertIsNotNone(validate_geometry(text,lambda x,y:(x,y))[2])
    def test_response_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);raw=b'{"Table":[["key"],["1"]]}'
            (root/'response.json').write_bytes(raw)
            logs=[{'id':'sample','response_file':'response.json','sha256':sha(raw),'bytes':len(raw)}]
            manifest=json.dumps(logs).encode();(root/'requests.json').write_bytes(manifest)
            (root/'capture.json').write_text(json.dumps({'requests_sha256':sha(manifest)}))
            self.assertEqual(verified_responses(root)[1]['sample'][0],[{'key':'1'}])
            (root/'response.json').write_bytes(raw.replace(b'"1"',b'"2"'))
            with self.assertRaisesRegex(ValueError,'Response checksum'):verified_responses(root)
    def test_manifest_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'capture.json').write_text(json.dumps({'requests_sha256':'0'*64}));(root/'requests.json').write_text('[]')
            with self.assertRaisesRegex(ValueError,'manifest checksum'):verified_responses(root)
if __name__=='__main__':unittest.main()
