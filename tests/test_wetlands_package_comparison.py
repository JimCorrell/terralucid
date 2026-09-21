"""Candidate classification must retain ambiguity and not conceal disagreement."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_wetlands_package import classify, comparison
from shapely.geometry import box

class CandidateStates(unittest.TestCase):
    def candidate(self,distance=1.025,code=True,kind=True):
        return dict(hausdorff_distance_m=distance,code_agrees=code,type_agrees=kind)
    def test_empty_is_unmatched_not_absent_wetlands(self):
        self.assertEqual(classify([]),'no_candidate_within_gate')
    def test_tolerance_changes_candidate_membership(self):
        m=[self.candidate()]
        self.assertEqual(classify(m,1),'no_candidate_within_gate')
        self.assertEqual(classify(m,2),'single_agreeing_candidate')
    def test_classification_conflict_is_not_filtered_out(self):
        self.assertEqual(classify([self.candidate(code=False)]),'single_conflicting_candidate')
        self.assertEqual(classify([self.candidate(kind=False)]),'single_conflicting_candidate')
    def test_multiple_candidates_never_select_nearest(self):
        self.assertEqual(classify([self.candidate(0.1),self.candidate(1.9,code=False)]),'multiple_candidates_within_gate')
    def test_gate_is_inclusive(self):
        self.assertEqual(classify([self.candidate(2)]),'single_agreeing_candidate')
    def test_geometry_hold_is_not_zero_distance(self):
        self.assertEqual(classify([{'geometry_hold':'invalid'}]),'no_candidate_within_gate')

    def test_distant_bound_skips_distance_without_dropping_candidate(self):
        g=box(0,0,1,1);other=box(20,0,21,1)
        row=dict(OBJECTID=1,NWI_ID='candidate',ATTRIBUTE='P',WETLAND_TYPE='test',Shape=b'fixture')
        result=comparison(g,other,'P','test',row)
        self.assertEqual(result['hausdorff_lower_bound_m'],20)
        self.assertNotIn('hausdorff_distance_m',result)
        self.assertEqual(result['intersection_m2'],0)
        self.assertEqual(classify([result],10),'no_candidate_within_gate')
    def test_near_candidate_keeps_computed_distance(self):
        row=dict(OBJECTID=1,NWI_ID='candidate',ATTRIBUTE='P',WETLAND_TYPE='test',Shape=b'fixture')
        result=comparison(box(0,0,10,10),box(1,0,11,10),'P','test',row)
        self.assertEqual(result['hausdorff_distance_m'],1)
        self.assertEqual(result['intersection_m2'],90)
        self.assertEqual(classify([result]),'single_agreeing_candidate')
