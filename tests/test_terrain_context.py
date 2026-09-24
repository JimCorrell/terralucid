import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import box
from terrain_context import catalog_context,ROOT,CATALOG,SELECTION,FILES
from qualify_area import qualify,currency
from test_area_qualification import capture

class TerrainContext(unittest.TestCase):
    def test_pilot_candidates_no_suitability(self):
        t=catalog_context(box(475114,5024374,475626,5024886))
        ids={x['sourceId'] for x in t['catalog_candidates']}
        self.assertTrue({'5eacf6f382cefae35a24ebc7','6635c4e3d34edc29f40a1058','6a753eb51ba49b79d0c34402'}<=ids)
        self.assertEqual(t['status'],'review_required')
        self.assertIsNone(t['slope_result']);self.assertIsNone(t['preferred_source'])
        self.assertFalse(t['blocks_general_discovery'])
        self.assertEqual(set(t['source_versions']),set(FILES))

    def test_outside_is_not_clearance(self):
        t=catalog_context(box(0,0,10,10))
        self.assertEqual(t['status'],'missing');self.assertEqual(t['catalog_candidates'],[])
        self.assertIn('UNKNOWN',t['elevation_availability'])

    def test_bad_catalog_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in [CATALOG,SELECTION]:
                (root/name).parent.mkdir(parents=True,exist_ok=True)
                (root/name).write_bytes((ROOT/name).read_bytes())
            with (root/CATALOG).open('a') as f:f.write(' ')
            with self.assertRaisesRegex(ValueError,'does not match'):catalog_context(box(0,0,1,1),root)

    def test_purchase_flag_and_currency(self):
        c=capture();p=qualify(c)
        self.assertEqual(p['topics']['buildability']['status'],'not_requested')
        self.assertEqual(p['discovery_summary']['topic_statuses']['wetlands'],p['topics']['wetlands']['status'])
        c['request']['purchase_candidate']=True
        p=qualify(c)
        self.assertEqual(p['topics']['buildability']['status'],'review_required')
        self.assertFalse(p['qualified_for_parcel_screening'])
        with patch('qualify_area.method_hash',return_value='changed_catalog'):
            self.assertTrue(currency(p,p['context'])['needs_revisit'])

if __name__=='__main__':unittest.main()
