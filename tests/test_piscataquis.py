import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import box,Polygon,Point
from prepare_piscataquis import package_geometry,relation,membership,manifest

class CountyChecks(unittest.TestCase):
    def blob(self,g,srid=300001):return b'GP\x00\x01'+struct.pack('<i',srid)+g.wkb
    def test_original_valid_wkb_unchanged(self):
        original=box(0,0,1,1);decoded,hold=package_geometry(self.blob(original))
        self.assertIsNone(hold);self.assertEqual(decoded.wkb,original.wkb)
    def test_invalid_polygon_is_held_without_repair(self):
        g,hold=package_geometry(self.blob(Polygon([(0,0),(1,1),(0,1),(1,0),(0,0)])))
        self.assertIsNone(g);self.assertIn('Self-intersection',hold)
    def test_unknown_srs_and_nonpolygon_held(self):
        for blob in [self.blob(box(0,0,1,1),4326),self.blob(Point(0,0)),b'bad']:
            g,hold=package_geometry(blob);self.assertIsNone(g);self.assertTrue(hold)
    def test_touch_outside_and_unknown_are_distinct(self):
        county=box(0,0,10,10)
        self.assertEqual(relation(box(9,9,11,11),county),'interior')
        self.assertEqual(relation(box(10,0,11,1),county),'touch')
        self.assertEqual(relation(box(11,0,12,1),county),'outside')
        self.assertEqual(relation(None,county),'held')
    def test_membership_does_not_accept_duplicates_or_missing_rows(self):
        for ids,count in [([1,1],2),([1],2),(['1'],1)]:
            with self.assertRaises(ValueError):membership(ids,count)
    def test_manifest_detects_changed_evidence_but_not_iteration_order(self):
        rows=[{'source_id':'a','object_id':1,'raw':1},{'source_id':'a','object_id':2,'raw':2}]
        expected=manifest(rows);self.assertEqual(expected,manifest(rows[::-1]))
        rows[0]['raw']=3;self.assertNotEqual(expected,manifest(rows))

if __name__=='__main__':unittest.main()
