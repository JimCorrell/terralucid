import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from affine import Affine
from compare_terrain_heights import sample,seam,stats

class Heights(unittest.TestCase):
    def test_shifted_plane(self):
        source=Affine(1,0,-1.0003,0,-1,5.0004)
        target=Affine(1,0,0,0,-1,4)
        r,c=np.indices((7,7));x,y=source*(c+.5,r+.5)
        data=2*x+3*y+10
        sampled=sample(data,np.ones(data.shape,bool),source,target,(3,3))
        r,c=np.indices((3,3));x,y=target*(c+.5,r+.5)
        np.testing.assert_allclose(sampled,2*x+3*y+10,atol=1e-12)

    def test_invalid_stencil_and_outside(self):
        a=np.ones((4,4));v=np.ones((4,4),bool);v[1,1]=False
        t=Affine(1,0,0,0,-1,4)
        out=sample(a,v,t,t,(4,4))
        self.assertTrue(np.isnan(out[0,0]))
        self.assertTrue(np.isnan(out[-1,-1]))
        self.assertEqual(out[2,2],1)

    def test_seam_separates_terrain_from_offset(self):
        base=np.array([[0.,2.,np.nan],[0.,2.,np.nan]])
        alt=np.array([[.1,2.1,4.1],[.1,2.1,4.1]])
        result=seam(base,alt)
        self.assertEqual(result['candidate_edges'],2)
        self.assertAlmostEqual(result['cross_source_step']['mean_m'],2.1)
        self.assertAlmostEqual(result['within_alternative_step']['mean_m'],2)
        self.assertAlmostEqual(result['source_switch_contribution']['mean_m'],.1)
        alt[0,2]=np.nan
        self.assertEqual(seam(base,alt)['unsupported_edges'],1)

    def test_reverse_and_vertical_edges(self):
        b=np.array([[np.nan,2],[2,2.]])
        a=np.ones((2,2))*1.5
        result=seam(b,a)
        self.assertEqual(result['supported_edges'],2)
        self.assertEqual(result['source_switch_contribution']['mean_m'],-.5)
        self.assertEqual(stats([]),{'count':0})

if __name__=='__main__':unittest.main()
