import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from affine import Affine
from inspect_terrain_extremes import patch,describe

class Extremes(unittest.TestCase):
    def test_native_location_and_mask(self):
        a=np.arange(225,dtype=float).reshape(15,15);v=np.ones(a.shape,bool);v[7,7]=False
        p,center=patch(a,v,Affine(1,0,.0003,0,-1,15.0004),7.5,7.5)
        np.testing.assert_allclose(center,[7.5003,7.5004])
        self.assertTrue(np.isnan(p[5,5]));self.assertEqual(p.shape,(11,11))
        d=describe(p);self.assertEqual(d['valid_cells'],120)
        self.assertIsNone(d['west_to_east_center_profile_m'][5])
        self.assertLess(d['plane_residual_rms_m'],1e-10)

    def test_plane_and_feature(self):
        r,c=np.indices((11,11));a=(2*r+3*c).astype(float)
        self.assertLess(describe(a)['plane_residual_rms_m'],1e-10)
        a[5,5]+=4
        self.assertGreater(describe(a)['plane_residual_rms_m'],.3)

    def test_outside_and_insufficient_support(self):
        with self.assertRaises(ValueError):patch(np.ones((11,11)),np.ones((11,11),bool),Affine.identity(),0,0)
        with self.assertRaises(ValueError):describe(np.full((11,11),np.nan))

if __name__=='__main__':unittest.main()
