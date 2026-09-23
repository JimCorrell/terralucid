import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from soil_availability import BATCH,METADATA
from qualify_area import qualify,currency,validate_request,query_sql
from test_area_qualification import capture
from shapely.geometry import box

def soil_capture():
 c=capture();c['request']['soils']={'batch':BATCH,'snapshot':'c'*64}
 c['context']['soils']={'batch':BATCH,'snapshot':'c'*64,'metadata_sha256':METADATA,'source_exists':True,'snapshot_current':True,'geometry_dependencies':{}}
 def row(kind,key,raw):return {'kind':kind,'source_key':key,'input_sha256':'hash','response_sha256':'response','raw':raw,'provenance':{}}
 c['soils']={'aoi_within_study':True,'held_keys':[],'polygons':[{'source_key':'p','mukey':'m','geometry_wkb':box(0,0,10,10).wkb_hex,'correction_status':'accepted','geometry_event_id':'e'}],
 'tables':[row('legend','l',{'areasymbol':'ME615','projectscale':'24000'}),row('mapunit','m',{'lkey':'l','vtsepticsyscl':'Ia'}),row('component','c',{'mukey':'m','comppct_r':'85','compkind':'Miscellaneous area','ksat_r':None})]}
 return c
class SoilAvailabilityTests(unittest.TestCase):
 def test_available_inventory_retains_unknown_remainder_and_site_limits(self):
  p=qualify(soil_capture());t=p['topics']['soils']
  self.assertTrue(t['inventory_intersections_usable']);self.assertEqual(t['status'],'review_required')
  self.assertEqual(t['component_mixtures'][0]['unlisted_percent'],'15');self.assertFalse(t['component_mixtures'][0]['normalized'])
  self.assertEqual(t['horizon_profiles'][0]['horizon_state'],'absent_miscellaneous_area')
  self.assertEqual(t['legal_or_site_suitability'],'UNKNOWN');self.assertFalse(p['qualified_for_parcel_screening'])
  self.assertEqual(p['topics']['septic_suitability']['status'],'not_requested')
  self.assertEqual(t['tables'][1]['excluded_interpretations'],['vtsepticsyscl'])
  self.assertEqual(t['survey_metadata'][0]['project_scale_denominator'],'24000')
 def test_stale_withdrawal_dependency_invalidates_packet(self):
  c=soil_capture();p=qualify(c);ctx=copy.deepcopy(c['context']);ctx['soils']['snapshot_current']=False
  self.assertTrue(currency(p,ctx)['needs_revisit']);c['context']=ctx
  self.assertFalse(qualify(c)['topics']['soils']['inventory_intersections_usable'])
 def test_missing_rows_hold_scope_and_tiny_gap_block_usability(self):
  for change in ['rows','hold','scope','gap','batch']:
   c=soil_capture()
   if change=='rows':c['soils']['tables']=[]
   if change=='hold':c['soils']['held_keys']=['outside-or-unknown']
   if change=='scope':c['soils']['aoi_within_study']=False
   if change=='gap':c['soils']['polygons'][0]['geometry_wkb']=box(0.000000001,0,10,10).wkb_hex
   if change=='batch':c['context']['soils']['source_exists']=False
   self.assertFalse(qualify(c)['topics']['soils']['inventory_intersections_usable'],change)
 def test_overfull_and_missing_percent_are_not_normalized(self):
  for value,state,remainder in [('110','over_100',None),(None,'unknown',None),('100','sums_to_100','0')]:
   c=soil_capture();c['soils']['tables'][2]['raw']['comppct_r']=value
   t=qualify(c)['topics']['soils']['component_mixtures'][0]
   self.assertEqual(t['percentage_state'],state);self.assertEqual(t['unlisted_percent'],remainder)
 def test_explicit_version_and_missing_capture_fail_closed(self):
  c=soil_capture();del c['soils']
  with self.assertRaises(ValueError):qualify(c)
  c=soil_capture();c['request']['soils']['batch']='d'*64
  with self.assertRaises(ValueError):validate_request(c['request'])
 def test_optional_query_does_not_require_soil_tables(self):
  self.assertNotIn('ingest.soil_',query_sql(capture()['request']))
  self.assertIn('ingest.effective_soil_geometry',query_sql(soil_capture()['request']))
  self.assertNotIn('__SOIL_',query_sql(soil_capture()['request']))
if __name__=='__main__':unittest.main()
