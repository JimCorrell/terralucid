"""Conservative exact-segment decomposition for the availability proposal."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_wetlands_availability import split_touches, assemble, directed_edges

SHELL = [[0,0],[0,10],[10,10],[10,0],[0,0]]

class AvailabilityChecks(unittest.TestCase):
    def test_two_touching_holes_in_one_shell_ring(self):
        r = [[0,0],[2,1],[1,2],[0,0],[0,10],[10,10],[8,9],[9,8],[10,10],[10,0],[0,0]]
        loops = split_touches(r);g = assemble(loops)
        self.assertEqual(len(loops),3);self.assertEqual(len(g.geoms[0].interiors),2)
        self.assertEqual(g.area,97);self.assertEqual(directed_edges([r]),directed_edges(loops))

    def test_two_same_winding_holes_touching_at_one_vertex(self):
        r = [[5,5],[3,5],[3,3],[5,3],[5,5],[7,5],[7,7],[5,7],[5,5]]
        g = assemble([SHELL]+split_touches(r))
        self.assertTrue(g.is_valid);self.assertEqual(len(g.geoms[0].interiors),2);self.assertEqual(g.area,92)

    def test_crossing_without_source_vertex_is_rejected(self):
        with self.assertRaises(ValueError):split_touches([[0,0],[10,10],[0,10],[10,0],[0,0]])

    def test_triple_visit_or_zero_edge_or_nonfinite_is_rejected(self):
        examples = [SHELL[:2]+[SHELL[1]]+SHELL[2:],[[0,0],[1,0],[0,1],[0,0],[2,0],[0,2],[0,0],[3,0],[0,3],[0,0]],[[0,0],[0,float('nan')],[1,1],[0,0]]]
        for r in examples:
            with self.assertRaises(ValueError):split_touches(r)

    def test_uncontained_hole_or_overlapping_shells_is_rejected(self):
        for loops in [[list(reversed(SHELL))],[SHELL,[[x+5,y] for x,y in SHELL]]]:
            with self.assertRaises(ValueError):assemble(loops)

    def test_disjoint_shells_preserve_coordinates_and_edges(self):
        loops = [SHELL,[[x+20,y] for x,y in SHELL]];g = assemble(loops)
        self.assertEqual(len(g.geoms),2);self.assertEqual(g.area,200)
        self.assertEqual(directed_edges(loops),directed_edges([list(p.exterior.coords) for p in g.geoms]))

if __name__ == '__main__':unittest.main()
