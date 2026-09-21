import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import Polygon,MultiPolygon
from review_county_zoning_proposals import odd_inside,review_geometry

class ReviewTests(unittest.TestCase):
    def test_ray_crossings_ignore_winding_and_handle_vertex_height(self):
        ring=[[0,0],[0,10],[10,10],[10,0],[0,0]]
        for r in [ring,ring[::-1]]:
            self.assertTrue(odd_inside(r,5,5));self.assertFalse(odd_inside(r,11,5))
            self.assertFalse(odd_inside(r,-1,0));self.assertTrue(odd_inside(r,5,0))
    def test_touching_hole_matches_source_fill(self):
        source=[[0,5],[2,4],[2,6],[0,5],[0,10],[10,10],[10,0],[0,0],[0,5]]
        candidate=Polygon([[0,5],[0,10],[10,10],[10,0],[0,0],[0,5]],[[[0,5],[2,4],[2,6],[0,5]]])
        r=review_geometry([source],candidate);self.assertEqual(r['symmetric_difference_m2'],0);self.assertEqual(r['filled_faces'],1)
    def test_nested_island_with_hole_matches_fill(self):
        def square(a,b):return [[a,a],[a,b],[b,b],[b,a],[a,a]]
        rings=[square(0,10),square(1,9)[::-1],square(2,8),square(3,7)[::-1]]
        c=MultiPolygon([Polygon(rings[0],[rings[1]]),Polygon(rings[2],[rings[3]])])
        self.assertEqual(review_geometry(rings,c)['filled_faces'],2)
    def test_deleted_hole_or_moved_vertex_rejected(self):
        rings=[[[0,0],[0,10],[10,10],[10,0],[0,0]],[[2,2],[8,2],[8,8],[2,8],[2,2]]]
        for c in [Polygon(rings[0]),Polygon([[0,0],[0,11],[10,10],[10,0],[0,0]],[rings[1]])]:
            with self.assertRaises(ValueError):review_geometry(rings,c)

if __name__=='__main__':unittest.main()
