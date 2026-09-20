import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
try:
    from shapely.geometry import Polygon, box
    from investigate_source_conflicts import spatial_comparison, assess_candidates
    SPATIAL = True
except ModuleNotFoundError as error:
    if error.name not in ('shapely','pyproj'):raise
    SPATIAL = False


@unittest.skipUnless(SPATIAL, 'Install research/conflict-investigation/requirements.txt')
class ConflictInvestigationTests(unittest.TestCase):
    def test_point_inside_is_not_full_containment(self):
        r=spatial_comparison(box(0,0,10,10),{'A':box(1,1,9,9)})
        self.assertEqual(r['point_codes'],['A'])
        self.assertEqual(r['fully_covered_codes'],[])
        self.assertAlmostEqual(r['area_fraction_by_code']['A'],0.64)

    def test_invalid_geometry_is_not_repaired_or_assigned(self):
        r=spatial_comparison(Polygon([(0,0),(1,1),(1,0),(0,1),(0,0)]),{'A':box(-1,-1,2,2)})
        self.assertEqual(r['state'],'invalid')
        self.assertNotIn('point_codes',r)

    def test_prefix_trial_preserves_multiplicity_and_original_identifier(self):
        def record(oid,key,code,town='Alfred'):
            return {'object_id':oid,'properties':{'STATE_ID':key,'GEOCODE':code,'TOWN':town,'MAP_BK_LOT':'1-2'}}
        source=record(1,'31030_1-2','31030')
        summary,rows=assess_candidates([source], [record(2,'31020_1-2','31020'),record(3,'31020_1-2','31020')],[])
        self.assertEqual(summary['Alfred']['prefix_trial_multiple'],1)
        self.assertEqual(rows[0]['prefix_trial_assessment_object_ids'],[2,3])
        self.assertEqual(source['properties']['STATE_ID'],'31030_1-2')

    def test_match_scope_does_not_claim_unqueried_identifiers(self):
        with self.assertRaises(ValueError):
            assess_candidates([{'object_id':1,'properties':{'STATE_ID':'unexpected','TOWN':'Alfred'}}],[],[])


if __name__=='__main__':unittest.main()
