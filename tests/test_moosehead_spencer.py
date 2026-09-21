import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import Polygon
from investigate_moosehead_spencer import split_touching_holes,propose
from investigate_osborn_zoning import edges
from review_county_zoning_proposals import review_geometry

class TouchingHoles(unittest.TestCase):
    ring=[[0,0],[-2,0],[-2,-2],[0,-2],[0,0],[2,0],[2,2],[0,2],[0,0]]
    shell=[[-3,-3],[-3,3],[3,3],[3,-3],[-3,-3]]
    def test_exact_two_holes(self):
        loops,d=split_touching_holes(self.ring)
        self.assertEqual(edges([self.ring]),edges(loops));self.assertEqual(d['loop_area_m2'],[4,4])
    def test_whole_feature_and_independent_fill(self):
        g,d=propose([self.shell,self.ring]);self.assertTrue(g.is_valid);self.assertEqual(g.area,28)
        self.assertEqual(len(g.geoms[0].interiors),2);self.assertTrue(review_geometry([self.shell,self.ring],g)['equals_independent_even_odd_fill'])
    def test_clockwise_exteriors_rejected(self):
        with self.assertRaises(ValueError):split_touching_holes(self.ring[::-1])
    def test_shared_edge_rejected(self):
        ring=[[0,0],[2,0],[2,2],[0,2],[0,0],[2,0],[1,-1],[0,0]]
        with self.assertRaises(ValueError):split_touching_holes(ring)
    def test_crossing_loops_rejected(self):
        ring=[[0,0],[4,0],[4,4],[0,4],[0,0],[3,1],[1,3],[0,0]]
        with self.assertRaises(ValueError):split_touching_holes(ring)
    def test_uncontained_holes_rejected(self):
        with self.assertRaises(ValueError):propose([self.ring])
    def test_coordinate_change_rejected_by_review(self):
        g,_=propose([self.shell,self.ring]);altered=[p[:] for p in self.ring];altered[1][0]-=.1
        with self.assertRaises(ValueError):review_geometry([self.shell,altered],g)
    def test_bad_dimensions_and_duplicates_rejected(self):
        for r in [self.ring[:-1],[[x,y,0] for x,y in self.ring],[self.ring[0]]+self.ring,[[float('nan'),0]]+self.ring[1:]]:
            with self.assertRaises(ValueError):split_touching_holes(r)
if __name__=='__main__':unittest.main()
