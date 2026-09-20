import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
try:
    from shapely.geometry import box,shape
    from prepare_municipal_crosswalk import decode_native_rings,propose_record,source_matches,build
    SPATIAL=True
except ModuleNotFoundError as error:
    if error.name not in ('shapely','pyproj'):raise
    SPATIAL=False


@unittest.skipUnless(SPATIAL,'Install research/municipal-corroboration/requirements.txt')
class MunicipalCrosswalkTests(unittest.TestCase):
    def feature(self):
        return {'type':'Feature','properties':{'OBJECTID':1,'GlobalID':'test-id','TOWN':'Alfred','GEOCODE':'31030',
                'STATE_ID':'31030_1-2','MAP_BK_LOT':'1-2','FMUPDAT':'2013'},'geometry':None}

    def test_native_hole_is_not_a_filled_shell(self):
        shell=list(box(0,0,10,10).exterior.coords)[::-1]
        hole=list(box(1,1,3,3).exterior.coords)
        other=list(box(20,20,22,22).exterior.coords)[::-1]
        decoded=decode_native_rings([shell,hole,other])
        self.assertTrue(decoded.is_valid)
        self.assertEqual(decoded.area,100)
        self.assertEqual(decoded.intersection(box(1,1,3,3)).area,0)
        self.assertEqual(sum(len(p.interiors) for p in decoded.geoms),1)

    def test_orphan_hole_and_open_ring_are_rejected(self):
        with self.assertRaises(ValueError):decode_native_rings([list(box(0,0,2,2).exterior.coords)])
        with self.assertRaises(ValueError):decode_native_rings([[[0,0],[1,0],[1,1],[0,1]]])

    def test_unmatched_or_multiple_candidates_do_not_gain_identifier_correction(self):
        feature=self.feature();before=copy.deepcopy(feature)
        for ids in [[],[2,3]]:
            p,holds=propose_record(feature,{'state':'valid','point_codes':['31020']},
                                  {'prefix_trial_assessment_object_ids':ids},{},'s','a',[])
            self.assertEqual(p['changes'],{'GEOCODE':{'from':'31030','to':'31020'}})
            self.assertTrue(holds)
            self.assertEqual(p['status'],'proposed')
        self.assertEqual(feature,before)

    def test_invalid_original_geometry_is_held(self):
        proposal,holds=propose_record(self.feature(),{'state':'invalid'}, {},{},'s','a',[])
        self.assertIsNone(proposal)
        self.assertEqual(holds,['invalid_original_geometry'])

    def test_snapshot_or_feature_change_invalidates_proposal_guard(self):
        feature=self.feature()
        p,_=propose_record(feature,{'state':'valid','point_codes':['31020']},
                           {'prefix_trial_assessment_object_ids':[]},{},'snapshot','a',[])
        self.assertTrue(source_matches(p,feature,'snapshot'))
        self.assertFalse(source_matches(p,feature,'new-snapshot'))
        feature['properties']['GEOCODE']='31020'
        self.assertFalse(source_matches(p,feature,'snapshot'))

    @unittest.skipUnless((Path(__file__).parents[1]/"research/municipal-corroboration/runs/geometry/alfred-native-rings.response").exists(), "Restore private evidence for the captured fixture")
    def test_captured_scope_and_exception_gates(self):
        report=build();s=report['summary']
        self.assertEqual((s['jurisdiction_proposals'],s['identifier_proposals'],s['exception_records']),(2324,1595,119))
        self.assertEqual(s['hold_counts']['shared_assessment_candidate'],5)
        g=report['geometry_format_evidence']
        self.assertFalse(g['original_geojson_valid'])
        self.assertTrue(g['native_decode_valid'])
        self.assertEqual(g['native_decode_overlap_with_inset_m2'],0)
        for part in shape(g['decoded_geojson']).geoms:
            self.assertTrue(part.exterior.is_ccw)
            self.assertTrue(all(not ring.is_ccw for ring in part.interiors))
        self.assertTrue(all(p['status']=='proposed' for p in report['crosswalk']['proposals']))


if __name__=='__main__':unittest.main()
