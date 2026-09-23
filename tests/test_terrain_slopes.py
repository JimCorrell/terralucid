import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from compare_terrain_slopes import slope,boundary_hold

class Slopes(unittest.TestCase):
    def test_plane_and_constant_offset(self):
        r,c=np.indices((7,8));z=2*c+3*r
        a=slope(z,np.ones(z.shape,bool))
        np.testing.assert_allclose(a[1:-1,1:-1],np.degrees(np.arctan(np.sqrt(13))))
        np.testing.assert_allclose(a,slope(z+100,np.ones(z.shape,bool)))
        self.assertTrue(np.isnan(a[0]).all())

    def test_missing_support(self):
        z=np.zeros((7,7));v=np.ones(z.shape,bool);v[3,3]=False
        a=slope(z,v)
        self.assertEqual(np.isfinite(a).sum(),16)
        z[3,3]=np.inf
        np.testing.assert_array_equal(np.isfinite(a),np.isfinite(slope(z,np.ones(z.shape,bool))))

    def test_seam_width_and_diagonal(self):
        labels=np.zeros((7,7),bool);labels[:,3:]=True
        h=boundary_hold(labels)
        self.assertEqual(int(h.sum()),10)
        self.assertTrue(h[1:6,2:4].all())
        labels[:]=False;labels[3,3]=True
        self.assertEqual(int(boundary_hold(labels).sum()),9)

    def test_step_artifact_is_held(self):
        labels=np.zeros((7,7),bool);labels[:,3:]=True
        z=labels.astype(float)*.11
        a=slope(z,np.ones(z.shape,bool));h=boundary_hold(labels)
        self.assertTrue((a[h]>0).all())
        self.assertTrue((a[np.isfinite(a)&~h]==0).all())

if __name__=='__main__':unittest.main()
