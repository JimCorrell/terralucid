import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_county_zoning_cases import interpret
from investigate_osborn_zoning import edges

def square(a,b,cw=True):
    r=[[a,a],[a,b],[b,b],[b,a],[a,a]]
    return r if cw else r[::-1]

class CountyCases(unittest.TestCase):
    def test_nested_island_hole_attaches_to_innermost_shell(self):
        rings=[square(0,10),square(1,9,False),square(2,8),square(3,7,False)]
        g,d=interpret(rings)
        self.assertAlmostEqual(g.area,56)
        self.assertTrue(g.is_valid)
        self.assertEqual(len(d['nested_hole_assignments']),1)
        output=[list(p.exterior.coords) for p in g.geoms]+[list(h.coords) for p in g.geoms for h in p.interiors]
        self.assertEqual(edges(rings),edges(output))
    def test_nested_shell_without_separating_hole_is_rejected(self):
        with self.assertRaises(ValueError):interpret([square(0,10),square(2,8),square(3,7,False)])
    def test_duplicate_shell_is_rejected(self):
        with self.assertRaises(ValueError):interpret([square(0,10),square(0,10),square(2,8,False)])
    def test_crossing_and_disjoint_touch_remain_held(self):
        for ring in [[[0,0],[2,2],[0,2],[2,0],[0,0]],[[0,0],[-2,0],[-2,2],[0,0],[2,0],[2,-2],[0,0]]]:
            with self.assertRaises(ValueError):interpret([ring])
    def test_supported_single_touch_keeps_area(self):
        ring=[[0,5],[2,4],[2,6],[0,5],[0,10],[10,10],[10,0],[0,0],[0,5]]
        g,d=interpret([ring]);self.assertAlmostEqual(g.area,98);self.assertEqual(len(d['splits']),1)

if __name__=='__main__':unittest.main()
