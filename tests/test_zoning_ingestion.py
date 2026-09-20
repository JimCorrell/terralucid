import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import box,mapping
from prepare_zoning_ingestion import effective_input,overlap_result,geometry_state
from prepare_source_staging import canonical,digest

def feature(g):return {'type':'Feature','geometry':mapping(g),'properties':{'GEOCODE':'17290'}}
def zone(oid,g):return ({'object_id':oid,'properties':{'ZONE':'test'}},g,'valid')

class ZoningTests(unittest.TestCase):
    def setUp(self):self.g=box(-68.3,44.7,-68.29,44.71);self.f=feature(self.g)
    def test_overlap_union_does_not_double_count(self):
        r=overlap_result(self.f,[zone(1,self.g),zone(2,self.g)],True)
        self.assertEqual(len(r['intersections']),2);self.assertAlmostEqual(r['covered_fraction'],1)
        self.assertAlmostEqual(r['intersection_area_sum_m2'],r['source_area_m2']*2)
        self.assertEqual(r['legal_zoning_state'],'UNKNOWN')
    def test_no_coverage_is_unknown_not_zero(self):
        r=overlap_result(self.f,[],False)
        self.assertIsNone(r['covered_fraction']);self.assertEqual(r['evidence_state'],'UNKNOWN')
    def test_invalid_zone_preserved_but_not_used(self):
        r=overlap_result(self.f,[(zone(1,self.g)[0],self.g,'invalid')],True)
        self.assertEqual(r['intersections'],[]);self.assertEqual(r['invalid_zone_envelope_candidates'],[1])
    def test_invalid_parcel_never_repaired(self):
        f={'geometry':{'type':'Polygon','coordinates':[[[-68.3,44.7],[-68.29,44.71],[-68.29,44.7],[-68.3,44.71],[-68.3,44.7]]]}}
        self.assertEqual(geometry_state(f)[1],'invalid');self.assertEqual(overlap_result(f,[zone(1,self.g)],True)['status'],'source_geometry_unusable')
    def test_boundary_touch_not_area_assignment(self):
        r=overlap_result(self.f,[zone(1,box(-68.29,44.7,-68.28,44.71))],True)
        self.assertEqual(r['intersections'],[]);self.assertEqual(r['boundary_touches'],[1])
    def test_effective_values_and_version_guards(self):
        r={'source_feature_sha256':digest(canonical(self.f).encode()),'correction_status':'accepted','event_id':'review','effective_properties':{'GEOCODE':'17310'}}
        result=effective_input(r,self.f);self.assertEqual(result['effective_properties']['GEOCODE'],'17310')
        f=copy.deepcopy(self.f);f['properties']['GEOCODE']='other'
        with self.assertRaisesRegex(ValueError,'Changed correction'):effective_input(r,f)
        r['event_id']=None
        with self.assertRaisesRegex(ValueError,'review event'):effective_input(r,self.f)
        r['correction_status']='revoked'
        with self.assertRaisesRegex(ValueError,'Unaccepted correction'):effective_input(r,self.f)
