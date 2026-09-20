"""Narrow topology guards: a valid result alone never authorizes a repair."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from investigate_osborn_zoning import edges, split_single_touch
from shapely.geometry import Polygon


class SingleTouchTests(unittest.TestCase):
    # A clockwise square contains a CCW triangular hole touching at (0, 5).
    ring = [[0, 5], [2, 4], [2, 6], [0, 5],
            [0, 10], [10, 10], [10, 0], [0, 0], [0, 5]]

    def test_existing_hole_and_all_segments_are_preserved(self):
        candidate, details = split_single_touch(self.ring)
        self.assertFalse(Polygon(self.ring).is_valid)
        self.assertTrue(candidate.is_valid)
        self.assertEqual(candidate.area, 98)
        self.assertEqual(len(candidate.interiors), 1)
        self.assertEqual(edges([self.ring]), edges([list(candidate.exterior.coords),
                                                   list(candidate.interiors[0].coords)]))
        self.assertEqual(details['zero_based_indices'], [0, 3])

    def test_reversed_export_and_rotated_start_preserve_result(self):
        expected, _ = split_single_touch(self.ring)
        for k in range(len(self.ring) - 1):
            rotated = self.ring[k:-1] + self.ring[:k] + [self.ring[k]]
            for ring in (rotated, list(reversed(rotated))):
                candidate, _ = split_single_touch(ring)
                self.assertTrue(candidate.equals(expected))

    def test_disjoint_lobes_are_not_guessed_as_hole(self):
        ring = [[0, 0], [-2, 0], [-2, 2], [0, 0], [2, 0], [2, -2], [0, 0]]
        with self.assertRaises(ValueError):
            split_single_touch(ring)

    def test_same_winding_is_rejected(self):
        ring = [self.ring[0], self.ring[2], self.ring[1]] + self.ring[3:]
        with self.assertRaises(ValueError):
            split_single_touch(ring)

    def test_crossing_is_not_repaired(self):
        with self.assertRaises(ValueError):
            split_single_touch([[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]])

    def test_nonfinite_extra_dimension_open_and_duplicate_rejected(self):
        cases = [self.ring[:-1], [p + [0] for p in self.ring],
                 self.ring[:2] + [self.ring[1]] + self.ring[2:],
                 [self.ring[0], [float('nan'), 4]] + self.ring[2:],
                 self.ring[:3] + self.ring[1:3] + self.ring[3:]]
        for ring in cases:
            with self.subTest(ring=ring), self.assertRaises(ValueError):
                split_single_touch(ring)


if __name__ == '__main__':
    unittest.main()
