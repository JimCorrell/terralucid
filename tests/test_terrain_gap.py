import sys
from pathlib import Path
import unittest
from rasterio.transform import from_origin
from shapely.geometry import box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_terrain_gap import enclosing_window
from compare_terrain_gap import coverage

class GapTests(unittest.TestCase):
    def test_offset_grid_encloses_aoi_without_snapping(self):
        t=from_origin(0.0003,20.0004,1,1)
        self.assertEqual(enclosing_window([5,5,10,10],t,20,20),[4,10,6,6])
    def test_native_exact_grid_has_no_extra_border(self):
        self.assertEqual(enclosing_window([5,5,10,10],from_origin(0,20,1,1),20,20),[5,10,5,5])
    def test_outside_rejected(self):
        with self.assertRaises(ValueError):enclosing_window([-1,5,10,10],from_origin(0,20,1,1),20,20)
    def test_complementary_sources_cover_gap_not_entire_area(self):
        c=coverage(box(0,0,1,2),box(1,0,2,2),box(0,0,2,2))
        self.assertTrue(c['alternative_covers_original_gap']);self.assertFalse(c['alternative_covers_entire_aoi'])
        self.assertEqual(c['combined_coverage'],'full_geometric');self.assertEqual(c['original_gap_remaining_m2'],0)
    def test_subpixel_gap_is_not_rounded_away(self):
        c=coverage(box(0,0,1,2),box(1.000001,0,2,2),box(0,0,2,2))
        self.assertFalse(c['alternative_covers_original_gap']);self.assertEqual(c['combined_coverage'],'partial_geometric')
        self.assertGreater(c['original_gap_remaining_m2'],0)

if __name__=='__main__':unittest.main()
