import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from collect_bounded_sources import validate_ids,validate_page
from prepare_bounded_ingestion import classify,validate_capture
from prepare_finding_event import event_sql
from apply_prepared_load import connection_environment


class BoundedIngestionTests(unittest.TestCase):
    def test_direct_connection_rejects_wrong_project_and_incomplete_credentials(self):
        script = "\n".join(["export PGHOST=example.test", "export PGPORT=5432",
                            "export PGUSER=postgres.expectedproject", "export PGDATABASE=postgres",
                            "export PGPASSWORD='sample with spaces'"])
        self.assertEqual(connection_environment(script, 'expectedproject')['PGPASSWORD'], 'sample with spaces')
        with self.assertRaises(ValueError):connection_environment(script, 'differentproject')
        with self.assertRaises(ValueError):connection_environment('export PGHOST=expectedproject', 'expectedproject')

    def test_id_control_rejects_incomplete_duplicate_and_oversize(self):
        for payload,count,cap in [({'objectIds':[1]},2,10),({'objectIds':[1,1]},2,10),
                                  ({'objectIds':[1,2]},2,1),({'objectIds':[1],'exceededTransferLimit':True},1,10)]:
            with self.assertRaises(ValueError):validate_ids(payload,count,cap)

    def test_page_membership_and_crs(self):
        payload={'type':'FeatureCollection','features':[{'properties':{'OBJECTID':1},'geometry':None}]}
        with self.assertRaises(ValueError):validate_page(payload,[1,2],True)
        payload['crs']={'type':'name','properties':{'name':'EPSG:3857'}}
        with self.assertRaises(ValueError):validate_page(payload,[1],True)

    def test_multiple_candidates_preserved_and_blank_keys_not_joined(self):
        def record(source,oid,key,code):
            return dict(source_id=source,object_id=oid,global_id=str(oid),
                        record_kind='assessment' if source=='organized-assessment' else 'assessment_geometry',
                        properties={'STATE_ID':key,'GEOCODE':code,'TOWN':'Test','FMUPDAT':'2020'})
        records=[record('organized-parcels',1,'001_A','001'),record('organized-parcels',2,' ','001'),
                 record('organized-assessment',3,'001_A','001'),record('organized-assessment',4,'001_A','002'),
                 record('organized-assessment',5,' ','001')]
        audit={'jurisdictions':[{'reference':{'GEOCODE':'001','COMMONNAME':'Test'},
                'sources':{'ut':{'source_feature_count':0},'organized':{'source_feature_count':1}}}]}
        candidates=classify(records,audit)
        self.assertEqual(len(candidates),2)
        self.assertIn('assessment_multiple_candidates',records[0]['quality_flags'])
        self.assertIn('assessment_geocode_disagreement',records[0]['quality_flags'])
        self.assertEqual(records[1]['candidate_count'],0)

    def test_capture_reconciles(self):
        _,_,records=validate_capture(Path(__file__).parents[1]/'research/maine-ingestion/2026-09-20')
        self.assertEqual(len(records),2058)
        self.assertEqual(len({(r['source_id'],r['object_id']) for r in records}),2058)

    def test_resolution_requires_evidence_and_review_note(self):
        with self.assertRaises(ValueError):
            event_sql('TL-F-0002','a'*64,'resolved','high','Monitor','Reviewer','Reason',[])
        with self.assertRaises(ValueError):
            event_sql('TL-F-0002','a'*64,'resolved','high','Monitor','Reviewer',' ',['audit:proof'])
        sql=event_sql('TL-F-0002','a'*64,'resolved','high','Monitor','Reviewer',"Publisher's correction",['audit:proof'])
        self.assertIn("Publisher''s correction",sql)
        self.assertIn('ingest.record_finding_event',sql)


if __name__=='__main__':unittest.main()
