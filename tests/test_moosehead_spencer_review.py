import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import Polygon,MultiPolygon
from review_moosehead_spencer import walk_cycles,review_cycles
from review_county_zoning_proposals import review_geometry
class CycleReview(unittest.TestCase):
    shell=[[-3,-3],[-3,3],[3,3],[3,-3],[-3,-3]]
    ring=[[0,0],[-2,0],[-2,-2],[0,-2],[0,0],[2,0],[2,2],[0,2],[0,0]]
    holes=[[[0,0],[-2,0],[-2,-2],[0,-2],[0,0]],[[0,0],[2,0],[2,2],[0,2],[0,0]]]
    def candidate(self):return MultiPolygon([Polygon(self.shell,self.holes)])
    def test_cycles_and_common_owner(self):
        r=review_cycles([self.shell,self.ring],self.candidate());self.assertEqual(r['exact_hole_cycles'],2);self.assertEqual(r['split_rings'][0]['candidate_shell_index'],0)
        self.assertEqual(review_geometry([self.shell,self.ring],self.candidate())['symmetric_difference_m2'],0)
    def test_rotated_ring_start(self):
        r=self.ring[2:-1]+self.ring[:3];self.assertEqual(len(walk_cycles(r)),2)
        self.assertTrue(review_cycles([self.shell,r],self.candidate())['source_cycle_roles_preserved'])
    def test_wrong_source_role(self):
        with self.assertRaises(ValueError):review_cycles([self.shell,self.ring[::-1]],self.candidate())
    def test_missing_hole(self):
        with self.assertRaises(ValueError):review_cycles([self.shell,self.ring],MultiPolygon([Polygon(self.shell,self.holes[:1])]))
    def test_coordinate_change(self):
        altered=[p[:] for p in self.ring];altered[1][0]-=.1
        with self.assertRaises(ValueError):review_cycles([self.shell,altered],self.candidate())
    def test_unsupported_walks(self):
        for r in [self.ring[:-1],[self.ring[0]]+self.ring,[[0,0],[2,2],[0,2],[2,0],[0,0]]]:
            with self.assertRaises(ValueError):walk_cycles(r)
if __name__=='__main__':unittest.main()
