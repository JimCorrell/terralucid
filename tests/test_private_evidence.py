import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from restore_private_evidence import restore


class PrivateEvidenceTests(unittest.TestCase):
    def fixture(self,root):
        audit=root/'audit';run=audit/'runs'/'sample';run.mkdir(parents=True)
        download=root/'download';(download/'sha256').mkdir(parents=True)
        data=b'captured document';sha=hashlib.sha256(data).hexdigest()
        (run/'results.json').write_text(json.dumps([{'response_file':'doc.response','sha256':sha,'bytes':len(data)}]))
        archive=download/'sha256'/(sha+'.response');archive.write_bytes(data)
        return audit,download,run/'doc.response',archive

    def test_checksum_failure_does_not_restore(self):
        with tempfile.TemporaryDirectory() as d:
            audit,download,target,archive=self.fixture(Path(d));archive.write_bytes(b'changed')
            with self.assertRaises(ValueError):restore(audit,download)
            self.assertFalse(target.exists())

    def test_existing_evidence_is_preserved_and_replay_is_safe(self):
        with tempfile.TemporaryDirectory() as d:
            audit,download,target,_=self.fixture(Path(d))
            self.assertEqual(restore(audit,download),1)
            self.assertEqual(restore(audit,download),0)
            target.write_bytes(b'existing different evidence')
            with self.assertRaises(ValueError):restore(audit,download)
            self.assertEqual(target.read_bytes(),b'existing different evidence')


if __name__=='__main__':unittest.main()
