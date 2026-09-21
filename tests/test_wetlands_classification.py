"""Keep reference selection conservative and multipart evidence verifiable."""
import copy
import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_wetlands_classification import choose_lookup, gpkg_geometry, literal_dictionaries, verify_package
from prepare_source_staging import digest
from shapely.geometry import Polygon

class ClassificationChecks(unittest.TestCase):
    def setUp(self):
        self.ref = {'ATTRIBUTE':'PUBFh','WATER_REGIME':'F','MODIFIER1':'h','SUBSYSTEM':''}
        self.good = {'NWI_Wetland_Codes.'+k:(v or None) for k,v in self.ref.items()}
        self.good['NWI_Wetland_Codes.OBJECTID'] = 5448
        self.incomplete = dict(self.good,**{'NWI_Wetland_Codes.OBJECTID':6186,'NWI_Wetland_Codes.WATER_REGIME':None,'NWI_Wetland_Codes.MODIFIER1':None})

    def test_complete_reference_match_wins_and_missing_fields_retained(self):
        selected,others = choose_lookup([self.incomplete,self.good],self.ref)
        self.assertEqual(selected,self.good)
        self.assertEqual(set(others[0]['differences']),{'WATER_REGIME','MODIFIER1'})
        self.assertIsNone(self.incomplete['NWI_Wetland_Codes.WATER_REGIME'])

    def test_incomplete_or_ambiguous_reference_match_is_not_resolved(self):
        for rows in [[self.incomplete],[self.good,dict(self.good)]]:
            with self.assertRaises(ValueError):choose_lookup(rows,self.ref)

    def test_nonempty_difference_not_normalized_away(self):
        changed = dict(self.good,**{'NWI_Wetland_Codes.MODIFIER1':'h '})
        with self.assertRaises(ValueError):choose_lookup([changed],self.ref)

    def test_decoder_is_read_as_data_without_executing_other_code(self):
        data = b"raise RuntimeError('not executed')\nParsedCodeDict={'P':'Palustrine'}\nParsedCodeDict2={'F':'Flooded'}"
        self.assertEqual(literal_dictionaries(data)['ParsedCodeDict']['P'],'Palustrine')
        with self.assertRaises(ValueError):literal_dictionaries(b"ParsedCodeDict=dict(P='Palustrine')\nParsedCodeDict2={}")

    def test_gpkg_srs_and_header_validated(self):
        polygon = Polygon([(0,0),(1,0),(1,1),(0,0)])
        blob = b'GP'+bytes([0,1])+struct.pack('<i',300001)+polygon.wkb
        self.assertTrue(gpkg_geometry(blob).equals(polygon))
        for changed in [b'XX'+blob[2:],blob[:4]+struct.pack('<i',4326)+blob[8:],blob[:3]+bytes([17])+blob[4:]]:
            with self.assertRaises(ValueError):gpkg_geometry(changed)

    def test_package_parts_require_full_original_hash_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);parts = []
            for i,data in enumerate([b'ab',b'cd']):
                (root/str(i)).write_bytes(data);parts.append({'offset':i*2,'bytes':2,'sha256':digest(data),'storage_object':str(i)})
            report = {'package':{'parts':parts,'bytes':4,'sha256':digest(b'abcd')}}
            self.assertEqual(verify_package(report,root)['original_package_bytes_verified'],4)
            bad = copy.deepcopy(report);bad['package']['parts'].reverse()
            with self.assertRaises(ValueError):verify_package(bad,root)
            (root/'1').write_bytes(b'ce')
            with self.assertRaises(ValueError):verify_package(report,root)

if __name__ == '__main__':unittest.main()
