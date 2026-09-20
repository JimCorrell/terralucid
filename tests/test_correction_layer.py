import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_correction_layer import validate_proposal
from prepare_source_staging import canonical,digest

class CorrectionGuards(unittest.TestCase):
    def setUp(self):
        self.feature={'properties':{'GEOCODE':'31030','STATE_ID':'31030_4-2'}}
        self.target={'attributes':{'STATE_ID':'31020_4-2'}}
        self.p={'source_snapshot_sha256':'snapshot','source_feature_sha256':digest(canonical(self.feature).encode()),
          'changes':{'GEOCODE':{'from':'31030','to':'31020'}},
          'assessment_candidate':{'object_id':1,'relationship_status':'candidate_only','source_snapshot_sha256':'assessment',
          'source_feature_sha256':digest(canonical(self.target).encode())}}
        self.p['proposal_id']=digest(canonical(self.p).encode())
    def check(self,p=None,feature=None,snapshot='snapshot',target=None):
        validate_proposal(p or self.p,feature or self.feature,snapshot,{1:target or self.target},'assessment')
    def test_source_and_snapshot_changes_rejected(self):
        self.check()
        with self.assertRaisesRegex(ValueError,'Stale source'):self.check(snapshot='new')
        feature=copy.deepcopy(self.feature);feature['properties']['new_field']='changed'
        with self.assertRaisesRegex(ValueError,'Stale source'):self.check(feature=feature)
    def test_candidate_change_rejected(self):
        with self.assertRaisesRegex(ValueError,'Stale assessment'):self.check(target={'attributes':{'STATE_ID':'other'}})
    def test_proposal_change_rejected(self):
        p=copy.deepcopy(self.p);p['changes']['GEOCODE']['to']='other'
        with self.assertRaisesRegex(ValueError,'Proposal identity'):self.check(p=p)
