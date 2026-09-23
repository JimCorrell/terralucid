import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import rasterio
from rasterio.transform import from_origin
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from retrieve_terrain_area import retrieve,checked_window

class MemoryCapture:
    def __init__(self,raw):self.raw=raw;self.calls=[]
    def get(self,url,name,headers=None,limit=None,expected_range=None):
        start,n=expected_range;self.calls.append((start,n))
        if headers.get('If-Match') not in (None,'pinned'):raise ValueError('Changed ETag')
        return self.raw[start:start+n],{'etag':'pinned','content_range':f'bytes {start}-{start+n-1}/{len(self.raw)}'}

class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.a=np.random.default_rng(42).random((1024,1024),dtype=np.float32)*100
        self.a[250:260,250:260]=-999999;self.a[270,270]=np.nan
        path=self.root/'source.tif'
        with rasterio.open(path,'w',driver='GTiff',width=1024,height=1024,count=1,dtype='float32',crs='EPSG:26919',transform=from_origin(400000,5100000,1,1),nodata=-999999,tiled=True,blockxsize=256,blockysize=256,compress='deflate') as ds:ds.write(self.a,1)
        self.raw=path.read_bytes()
        with rasterio.open(path) as ds:
            self.expected={'url':'https://example.test/source.tif','etag':'pinned','current_file_bytes':len(self.raw),'source_id':'fixture','width':ds.width,'height':ds.height,'bounds':list(ds.bounds),'resolution':list(ds.res),'crs_wkt':ds.crs.to_wkt(),'nodata':ds.nodata,'dtype':ds.dtypes[0]}
    def tearDown(self):self.tmp.cleanup()
    def test_multiblock_subset_matches_original_and_preserves_gaps(self):
        cap=MemoryCapture(self.raw);out=self.root/'subset.tif';r=retrieve(cap,self.expected,[240,240,80,80],0,out)
        with rasterio.open(out) as ds:np.testing.assert_array_equal(ds.read(1),self.a[240:320,240:320])
        self.assertEqual(r['nodata_pixels'],100);self.assertEqual(r['nonfinite_unmasked_pixels'],1)
        self.assertEqual(r['valid_pixels'],6299);self.assertEqual(r['coverage'],'partial_native_pixel_coverage');self.assertFalse(r['analysis_qualified'])
        self.assertEqual(len(r['captured_blocks']),4);self.assertLess(r['raster_transfer_bytes'],len(self.raw))
    def test_changed_etag_rejected(self):
        with self.assertRaisesRegex(ValueError,'version changed'):retrieve(MemoryCapture(self.raw),dict(self.expected,etag='old'),[0,0,10,10],0,self.root/'no.tif')
    def test_header_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'header mismatch'):retrieve(MemoryCapture(self.raw),dict(self.expected,resolution=[2,2]),[0,0,10,10],0,self.root/'no.tif')
    def test_window_limits(self):
        for values in ([0,0,2048,2048],[-1,0,1,1],[1000,0,25,1],[0,0,0,1],[0,0,1.5,2]):
            with self.subTest(values=values),self.assertRaises(ValueError):checked_window(values,1024,1024)
    def test_full_valid_window(self):
        r=retrieve(MemoryCapture(self.raw),self.expected,[0,0,10,10],0,self.root/'valid.tif')
        self.assertEqual(r['coverage'],'full_native_pixel_coverage');self.assertEqual(r['valid_area_m2'],100)
        self.assertFalse(r['analysis_qualified'])

if __name__=='__main__':unittest.main()
