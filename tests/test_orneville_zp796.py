import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_orneville_zp796 import BASE,validate_review,compare_note
T='The Federal Emergency Management Agency has identified special flood hazard areas. The FIRM [full title of the FIRM] dated [date of FIRM] is hereby adopted by reference. A copy of the FIRM may be obtained from Commission staff.'
class ReviewTests(unittest.TestCase):
 def setUp(self):self.r=json.loads((BASE/'review.json').read_text())
 def test_review(self):validate_review(self.r)
 def test_wrong_date(self):
  self.r['cases'][0]['decision_stated_effective_date']='1987-04-17'
  with self.assertRaises(ValueError):validate_review(self.r)
 def test_geometry_promotion(self):
  self.r['cases'][0]['geometry_change_authorized']=True
  with self.assertRaises(ValueError):validate_review(self.r)
 def test_legal_promotion(self):
  self.r['cases'][0]['legal_currency']='VERIFIED'
  with self.assertRaises(ValueError):validate_review(self.r)
 def test_whitespace(self):self.assertTrue(compare_note(T,T.replace('[full title of the FIRM]','Orneville').replace('[date of FIRM]','4/17/1987').replace(' ','\n'),'Orneville','4/17/1987'))
 def test_wrong_firm_date(self):self.assertFalse(compare_note(T,T.replace('[full title of the FIRM]','Orneville').replace('[date of FIRM]','8/1/2024'),'Orneville','4/17/1987'))
if __name__=='__main__':unittest.main()
