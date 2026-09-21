"""Failure gates for native rings and the observed NWI joined-ID response."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_osborn_wetlands import decode, group_source_rows, reconcile

SHELL = [[0,0],[0,10],[10,10],[10,0],[0,0]]
HOLE = [[2,2],[8,2],[8,8],[2,8],[2,2]]

class WetlandsChecks(unittest.TestCase):
    def feature(self, lookup=1):
        return {'attributes':{'Wetlands.OBJECTID':1,'Wetlands.ATTRIBUTE':'PUBFh','NWI_Wetland_Codes.OBJECTID':lookup},'geometry':{'rings':[copy.deepcopy(SHELL)]}}

    def test_hole_is_subtracted_without_changing_vertices(self):
        g,hold = decode([HOLE,SHELL])
        self.assertIsNone(hold);self.assertEqual(g.area,64)
        self.assertEqual(list(g.exterior.coords),list(map(tuple,SHELL)))
        self.assertEqual(list(g.interiors[0].coords),list(map(tuple,HOLE)))

    def test_disjoint_shells_retained(self):
        g,hold = decode([SHELL,[[x+20,y] for x,y in SHELL]])
        self.assertIsNone(hold);self.assertEqual(g.area,200)

    def test_non_simple_ring_is_held(self):
        g,hold = decode([[[0,0],[10,10],[0,10],[10,0],[0,0]]])
        self.assertIsNone(g);self.assertTrue(hold)

    def test_uncontained_hole_and_overlapping_shells_held(self):
        for rings in [[HOLE],[SHELL,[[x+5,y] for x,y in SHELL]]]:
            g,hold = decode(rings);self.assertIsNone(g);self.assertTrue(hold)

    def test_lookup_variants_preserved_and_exact_native_grouped(self):
        a,b = self.feature(),self.feature(2)
        rows,conflicts = group_source_rows([a,b,a])
        self.assertEqual(len(rows),1);self.assertEqual(len(conflicts),1)
        self.assertEqual(conflicts[0]['differing_join_fields']['NWI_Wetland_Codes.OBJECTID'],[1,2])
        self.assertEqual(rows[0]['geometry'],a['geometry'])

    def test_conflicting_native_attributes_or_coordinates_stop_capture(self):
        for which in ['geometry','attributes']:
            a,b = self.feature(),self.feature(2)
            if which == 'geometry':b['geometry']['rings'][0][1][1] = 11
            else:b['attributes']['Wetlands.ATTRIBUTE'] = 'PUBH'
            with self.assertRaises(ValueError):group_source_rows([a,b])

    def test_truncation_missing_ids_wrong_crs_rejected(self):
        base = {'spatialReference':{'wkid':102100,'latestWkid':3857},'features':[self.feature()]}
        for change in [{'exceededTransferLimit':True},{'features':[]},{'spatialReference':{'wkid':4326}},{'error':{'code':500}}]:
            with self.assertRaises(ValueError):reconcile(dict(base,**change),[1],'Wetlands.OBJECTID')

    def test_duplicate_response_requires_explicit_join_handling(self):
        p = {'spatialReference':{'wkid':3857},'features':[self.feature(),self.feature(2)]}
        with self.assertRaises(ValueError):reconcile(p,[1],'Wetlands.OBJECTID')
        self.assertEqual(len(reconcile(p,[1],'Wetlands.OBJECTID',joined=True)),2)

if __name__ == '__main__':unittest.main()
