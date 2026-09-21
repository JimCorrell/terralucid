"""Review inheritance must fail closed when native or classification bytes differ."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_wetlands_load import select_lookup
from prepare_source_staging import canonical,digest

class ClassificationInheritance(unittest.TestCase):
    def setUp(self):
        self.core={'attributes':{'Wetlands.ATTRIBUTE':'PUBFh'},'geometry':{'rings':[]}}
        self.lookup={'NWI_Wetland_Codes.OBJECTID':5448,'NWI_Wetland_Codes.CODE':'PUBFh','NWI_Wetland_Codes.EXTRA':None}
        self.refs={'PUBFh':{'CODE':'PUBFh','EXTRA':''}}
        self.sha=digest(canonical(self.lookup).encode())
        self.review={'native_core_sha256':digest(canonical(self.core).encode()),'prior_native_geometry_sha256':digest(canonical(self.core['geometry']).encode()),'reference_row_sha256':digest(canonical(self.refs['PUBFh']).encode()),'selected_lookup_sha256':self.sha,'selected_lookup_objectid':5448}
        self.variants={self.sha:self.lookup}
    def test_exact_review_with_csv_empty_normalization(self):
        self.assertEqual(select_lookup(self.core,self.variants,self.review,self.refs),(self.lookup,'reviewed_reference_match'))
    def test_changed_native_geometry_blocks_inheritance(self):
        c=copy.deepcopy(self.core);c['geometry']['rings']=[[[0,0]]]
        with self.assertRaisesRegex(ValueError,'core changed'):select_lookup(c,self.variants,self.review,self.refs)
    def test_missing_selected_variant_blocks_inheritance(self):
        with self.assertRaisesRegex(ValueError,'lookup missing'):select_lookup(self.core,{},self.review,self.refs)
    def test_changed_reference_blocks_inheritance(self):
        with self.assertRaisesRegex(ValueError,'Reference row'):select_lookup(self.core,self.variants,self.review,{'PUBFh':{'CODE':'OTHER'}})
    def test_unreviewed_conflict_not_arbitrarily_selected(self):
        with self.assertRaisesRegex(ValueError,'Unreviewed lookup conflict'):select_lookup(self.core,dict(self.variants,other={}),None,{})
    def test_single_source_variant_is_not_called_reference_verified(self):
        self.assertEqual(select_lookup(self.core,self.variants,None,{})[1],'source_single_variant')
