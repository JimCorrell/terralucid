import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_soil_metadata import ranges,profile
class SoilMetadataTests(unittest.TestCase):
 def test_missing_range_is_not_zero_or_inversion(self):
  r=ranges([{'cokey':'1','slope_l':None,'slope_r':'0','slope_h':'1'}],'slope')
  self.assertEqual(r,{'incomplete_count':1,'inverted_keys':[]})
 def test_inversion_retains_source_key(self):
  self.assertEqual(ranges([{'cokey':'1','slope_l':'3','slope_r':'2','slope_h':'4'}],'slope')['inverted_keys'],['1'])
 def test_mixture_ties_missing_horizons_and_percent_exception(self):
  cs=[{'mukey':'m','cokey':str(i),'comppct_r':'40','drainagecl':v} for i,v in enumerate(['Well drained','Poorly drained'])]
  r=profile([{'mukey':'m'}],cs,[])
  self.assertEqual(r['mapunits_with_tied_largest_component'],1)
  self.assertEqual(r['mapunits_with_differing_drainage_classes'],1)
  self.assertEqual(r['component_percent_sum_exceptions'][0]['sum'],'80')
  self.assertEqual(len(r['components_without_horizons']),2)
 def test_horizon_overlap_and_gap_are_explicit(self):
  hs=[{'cokey':'c','chkey':str(i),'hzdept_r':str(t),'hzdepb_r':str(b)} for i,(t,b) in enumerate([(0,10),(9,20),(25,30)])]
  r=profile([],[],hs)
  self.assertEqual([x['problem'] for x in r['horizon_depth_observations']],['overlap','gap'])
if __name__=='__main__':unittest.main()
