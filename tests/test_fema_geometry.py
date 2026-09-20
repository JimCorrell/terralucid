"""Exact-source guards for the two FEMA interpretation proposals."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_fema_geometry import OIDS, selected, compare_source
from investigate_osborn_fema import CRS


class FemaGeometryTests(unittest.TestCase):
    def payload(self,native=False):
        fs=[]
        for oid in sorted(OIDS):
            ring=[[0,0],[0,1],[1,0],[0,0]]
            fs.append({'attributes' if native else 'properties':{'OBJECTID':oid},
                       'geometry':{'rings':[ring]} if native else {'type':'Polygon','coordinates':[ring]}})
        return {'spatialReference':{'wkid':4269},'features':fs} if native else {'type':'FeatureCollection','crs':CRS,'features':fs}

    def test_incomplete_or_duplicate_pair_rejected(self):
        for change in ['missing','duplicate','truncated','error']:
            p=self.payload()
            if change=='missing':p['features'].pop()
            if change=='duplicate':p['features'][1]=copy.deepcopy(p['features'][0])
            if change=='truncated':p['exceededTransferLimit']=True
            if change=='error':p['error']={'code':500}
            with self.subTest(change=change),self.assertRaises(ValueError):selected(p)

    def test_curves_and_extra_rings_require_new_review(self):
        for change in ['curve','extra']:
            p=self.payload(True);g=p['features'][0]['geometry']
            if change=='curve':g['curveRings']=g.pop('rings')
            else:g['rings'].append(g['rings'][0])
            with self.subTest(change=change),self.assertRaises(ValueError):selected(p,True)

    def test_crs_change_is_not_silently_transformed(self):
        p=self.payload(True);p['spatialReference']['wkid']=4326
        with self.assertRaises(ValueError):selected(p,True)
        p=self.payload();p.pop('crs')
        with self.assertRaises(ValueError):selected(p)

    def test_source_attribute_and_segment_drift_rejected(self):
        old=self.payload()['features'][0];nf=self.payload(True)['features'][0]
        compare_source(old,nf,copy.deepcopy(old),copy.deepcopy(nf))
        for change in ['old','attribute','coordinate']:
            native=copy.deepcopy(nf);export=copy.deepcopy(old);projected=copy.deepcopy(nf)
            if change=='old':export['properties']['new']='changed'
            if change=='attribute':projected['attributes']['new']='changed'
            if change=='coordinate':native['geometry']['rings'][0][1]=[0,2]
            with self.subTest(change=change),self.assertRaises(ValueError):compare_source(old,native,export,projected)


if __name__=='__main__':unittest.main()
