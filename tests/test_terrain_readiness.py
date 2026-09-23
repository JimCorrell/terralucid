"""Transfer bounds protect against accidentally downloading complete DEMs."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from investigate_terrain_readiness import Capture, RangeFile

class Response(io.BytesIO):
    def __init__(self, body, status, headers):
        super().__init__(body); self.status=status; self.headers=headers; self.read_called=False
    def read(self,n=-1):
        self.read_called=True
        return super().read(n)

class BoundsTests(unittest.TestCase):
    def capture(self, response, expected=(0,4), limit=4):
        with tempfile.TemporaryDirectory() as tmp, patch('urllib.request.urlopen',return_value=response):
            return Capture(Path(tmp)/'capture').get('https://example.test','sample.bin',limit=limit,expected_range=expected)
    def test_full_response_refused_before_body(self):
        r=Response(b'x'*100,200,{})
        with self.assertRaises(ValueError):self.capture(r)
        self.assertFalse(r.read_called)
    def test_wrong_range_refused_before_body(self):
        r=Response(b'abcd',206,{'Content-Range':'bytes 1-4/100'})
        with self.assertRaises(ValueError):self.capture(r)
        self.assertFalse(r.read_called)
    def test_short_or_excess_body_refused(self):
        for body in (b'ab',b'abcde'):
            with self.assertRaises(ValueError):self.capture(Response(body,206,{'Content-Range':'bytes 0-3/100'}))
    def test_exact_response_retained(self):
        data,record=self.capture(Response(b'abcd',206,{'Content-Range':'bytes 0-3/100'}))
        self.assertEqual(data,b'abcd');self.assertEqual(record['bytes'],4)
    def test_budget_and_unbounded_read_refused(self):
        f=RangeFile.__new__(RangeFile);f.pos=0;f.size=100;f.parts=[];f.used=8*1024*1024
        with self.assertRaises(ValueError):f.read()
        with self.assertRaises(ValueError):f.read(1)
    def test_etag_change_refused(self):
        f=RangeFile.__new__(RangeFile);f.pos=0;f.size=100;f.parts=[];f.used=0;f.etag='old';f.url='test';f.index=0
        class MockCapture:
            def get(self,*args,**kwargs):return b'a',{'etag':'new'}
        f.cap=MockCapture()
        with self.assertRaises(ValueError):f.read(1)

if __name__=='__main__':unittest.main()
