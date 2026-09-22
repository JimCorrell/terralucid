import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reconcile_zoning_dates import BASE,validate_review
class ReviewTests(unittest.TestCase):
 def setUp(self):self.review=json.loads((BASE/'review.json').read_text())
 def test_review(self):validate_review(self.review)
 def test_changed_date(self):
  self.review['cases'][0]['decision_stated_effective_date']='2015-07-21'
  with self.assertRaises(ValueError):validate_review(self.review)
 def test_legal_promotion(self):
  self.review['cases'][0]['legal_currency']='VERIFIED'
  with self.assertRaises(ValueError):validate_review(self.review)
 def test_source_replacement(self):
  self.review['cases'][1]['source_value_replacement']='2018-04-26'
  with self.assertRaises(ValueError):validate_review(self.review)
 def test_closed_variance(self):
  self.review['cases'][0]['reconciliation_status']='resolved'
  with self.assertRaises(ValueError):validate_review(self.review)
 def test_scope(self):
  self.review['cases'].append(copy.deepcopy(self.review['cases'][0]))
  with self.assertRaises(ValueError):validate_review(self.review)
if __name__=='__main__':unittest.main()
