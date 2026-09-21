import csv,io,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_source_staging import literal
from repack_county_transfer import values

class TransferChecks(unittest.TestCase):
    def test_sql_literal_and_csv_preserve_private_input_bytes(self):
        raw='{"name":"O\'Brien ),( \\\\ \\n \\\"quoted\\\"", "number": 1.25}'
        original=('a'*64,'source',123,raw)
        sql='('+','.join([literal(original[0]),literal(original[1]),'123',literal(raw)])+')'
        self.assertEqual(list(values(sql)),[original])
        stream=io.StringIO();csv.writer(stream,lineterminator='\n').writerow(original)
        self.assertEqual(next(csv.reader(io.StringIO(stream.getvalue()))),[original[0],original[1],'123',raw])
    def test_multiple_rows_keep_identity(self):
        self.assertEqual(list(values("('a','x',1,'one'),('a','y',2,'two')")),[('a','x',1,'one'),('a','y',2,'two')])
    def test_other_sql_is_rejected(self):
        with self.assertRaises((ValueError,IndexError)):list(values("('a','x',1,'one'); delete"))

if __name__=='__main__':unittest.main()
