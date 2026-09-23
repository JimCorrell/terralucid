import sys,unittest,json,hashlib,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely import wkt
from investigate_soil_holds import candidate_from_source,vertex_difference,verify_controls
from collect_soil_hold_evidence import containment_query

class SoilHoldTests(unittest.TestCase):
    def test_touching_hole_preserves_source_edges_and_original(self):
        source=wkt.loads('POLYGON ((0 0,0 4,4 4,4 0,2 0,3 1,2 2,1 1,2 0,0 0))')
        original=source.wkb
        candidate,detail=candidate_from_source(source)
        self.assertFalse(source.is_valid);self.assertTrue(candidate.is_valid)
        self.assertEqual(source.wkb,original)
        self.assertEqual(detail['twice_visited_vertices'],1)
        self.assertEqual(detail['directed_edges_preserved'],9)
        self.assertEqual(len(candidate.geoms[0].interiors),1)
        self.assertEqual(candidate.area,14)
    def test_true_crossing_has_no_supported_split(self):
        with self.assertRaises(ValueError):candidate_from_source(wkt.loads('POLYGON ((0 0,2 2,0 2,2 0,0 0))'))
    def test_triple_visit_rejected(self):
        with self.assertRaises(ValueError):candidate_from_source(wkt.loads('POLYGON ((0 0,0 3,3 3,3 0,1 0,2 1,1 0,2 2,1 0,0 0))'))
    def test_precision_difference_not_hidden(self):
        a=wkt.loads('POLYGON ((0 0,0 1,1 1,1 0,0 0))')
        b=wkt.loads('POLYGON ((0 0,0 1,1.00000001 1,1 0,0 0))')
        self.assertGreater(vertex_difference(a,b),0)
    def test_native_control_mismatch_and_tampering_fail_closed(self):
        controls=[{'mupolygonkey':'123','x':1,'y':2,'expected':1}]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def write(value):
                raw=json.dumps({'Table':[['control_id','mupolygonkey','contains_point'],['0','123',str(value)]]}).encode()
                (root/'native-containment.response').write_bytes(raw)
                (root/'native-containment-request.json').write_text(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'payload':{'query':containment_query(controls),'format':'JSON+COLUMNNAME'}}))
            write(1);self.assertTrue(verify_controls(controls,root)['all_match'])
            write(0)
            with self.assertRaisesRegex(ValueError,'containment differs'):verify_controls(controls,root)
            write(1);(root/'native-containment.response').write_text('{}')
            with self.assertRaisesRegex(ValueError,'response changed'):verify_controls(controls,root)
    def test_control_query_rejects_nonfinite_and_untrusted_key(self):
        for c in [{'mupolygonkey':'1;drop','x':1,'y':2},{'mupolygonkey':'1','x':float('nan'),'y':2}]:
            with self.assertRaises(ValueError):containment_query([c])
if __name__=='__main__':unittest.main()
