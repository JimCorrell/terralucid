import copy,json,sys,tempfile,unittest
from unittest.mock import patch
import contextlib,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import box
from qualify_area import qualify,currency,validate_request,private_write,query_sql,read_export,main

def feature(source,oid,g=None,hold=None,rings=None,code=None):
    return {'source_id':source,'object_id':oid,'input_sha256':str(oid),'geometry_wkb':g.wkb_hex if g is not None else None,
        'hold':hold,'raw_held_geometry':{'rings':rings} if rings is not None else None,'native_srid':26919,
        'attributes':{'GEOCODE':code},'flags':[],'provenance':{'fixture':True},'correction_status':'original'}
def capture():
    a=box(0,0,10,10)
    return {'request':{'audit':'a'*64,'snapshot':'b'*64,'geometry':box(-69,45,-68.99,45.01).__geo_interface__,'purchase_candidate':False},
      'context':{'source_audit':'a'*64,'geometry_snapshot':'b'*64,'source_exists':True,'snapshot_current':True,'geometry_dependencies':{},'finding_dependencies':{}},
      'aoi_wkb':a.wkb_hex,'aoi_within_county':True,'findings':[],
      'features':[feature('ut-parcels',1,a),feature('lupc-zoning',2,a),feature('nwi-project',3,a),feature('nwi-package',4,box(0,0,2,2))]}
class QualificationTests(unittest.TestCase):
    def test_source_overlap_preserved_without_merge(self):
        c=capture();c['features'].append(feature('organized-parcels',8,box(1,1,5,5)))
        p=qualify(c);t=p['topics']['identity'];self.assertEqual(len(t['records']),2)
        self.assertEqual(t['cross_source_overlap_candidates'][0]['overlap_within_aoi_m2'],16)
        self.assertFalse(p['qualified_for_parcel_screening'])
    def test_touch_not_identity_overlap(self):
        c=capture();c['features'].append(feature('organized-parcels',8,box(10,0,11,10)))
        t=qualify(c)['topics']['identity'];self.assertEqual(t['cross_source_overlap_candidates'],[])
        self.assertEqual(next(f for f in t['records'] if f['source_id']=='organized-parcels')['aoi_relation'],'touch')
    def test_envelope_blocks_only_affected_topic(self):
        c=capture();c['features'].append(feature('lupc-zoning',5,hold='crossing',rings=[[[9,9],[12,9],[12,12],[9,9]]]))
        p=qualify(c);self.assertFalse(p['topics']['zoning']['inventory_intersections_usable'])
        self.assertTrue(p['topics']['wetlands']['inventory_intersections_usable'])
    def test_unlocatable_hold_not_dropped(self):
        c=capture();c['features'].append(feature('lupc-zoning',5,hold='missing'))
        self.assertEqual(qualify(c)['topics']['zoning']['held_evidence'][0]['reason'],'held_geometry_extent_unknown')
    def test_remote_hold_not_global_block(self):
        c=capture();c['features'].append(feature('lupc-zoning',5,hold='crossing',rings=[[[100,100],[101,101],[100,100]]]))
        self.assertTrue(qualify(c)['topics']['zoning']['inventory_intersections_usable'])
    def test_compact_held_bounds_preserve_topic_blocks(self):
        c=capture();f=feature('lupc-zoning',5,hold='crossing',rings=[[[9,9],[12,9],[12,12],[9,9]]]);c['features'].append(f)
        raw=qualify(c)['topics']['zoning']['held_evidence']
        f['held_bounds']=[9,9,12,12];f.pop('raw_held_geometry')
        self.assertEqual(qualify(c)['topics']['zoning']['held_evidence'],raw)
        for bounds in [None,[12,9,9,12],[False,9,12,12],[9,9,float('inf'),12]]:
            f['held_bounds']=bounds
            from qualify_area import held_envelope
            self.assertIsNone(held_envelope(f))
    def test_accepted_effective_geometry_used(self):
        c=capture();c['features'][1].update(correction_status='accepted',geometry_event_id='event',candidate_sha256='candidate')
        p=qualify(c);self.assertTrue(p['topics']['zoning']['inventory_intersections_usable'])
        self.assertEqual(p['topics']['zoning']['records'][0]['geometry_event_id'],'event')
    def test_missing_municipal_zoning(self):
        c=capture();c['features']=[f for f in c['features'] if f['source_id']!='lupc-zoning']
        t=qualify(c)['topics']['zoning'];self.assertEqual(t['status'],'missing');self.assertIn('municipal_zoning_not_loaded',t['reasons'])
    def test_wetland_project_coverage_is_not_clearance(self):
        t=qualify(capture())['topics']['wetlands'];self.assertEqual(t['coverage']['state'],'full_geometric')
        self.assertIn('inventory_absence_not_wetland_clearance',t['reasons'])
    def test_changed_dependencies_and_new_findings(self):
        c=capture();p=qualify(c);self.assertFalse(currency(p,c['context'])['needs_revisit'])
        for key in ['geometry_dependencies','finding_dependencies','source_observations_sha256','evidence_catalog_sha256']:
            changed=copy.deepcopy(c['context']);changed[key]={'new':'version'}
            self.assertTrue(currency(p,changed)['needs_revisit'])
    def test_stale_snapshot_withholds_intersections(self):
        c=capture();c['context']['snapshot_current']=False;p=qualify(c)
        self.assertTrue(currency(p,c['context'])['needs_revisit'])
        self.assertEqual(p['topics']['zoning']['status'],'stale');self.assertFalse(p['topics']['zoning']['inventory_intersections_usable'])
    def test_partial_aoi_and_coverage(self):
        c=capture();c['aoi_within_county']=False;c['features'][1]=feature('lupc-zoning',2,box(0,0,5,10))
        t=qualify(c)['topics']['zoning'];self.assertEqual(t['coverage']['fraction'],0.5);self.assertFalse(t['inventory_intersections_usable'])
    def test_purchase_switch_only_triggers_diligence(self):
        c=capture();p=qualify(c);c['request']['purchase_candidate']=True;q=qualify(c)
        for name in ['septic_suitability','buildability']:
            self.assertEqual(p['topics'][name]['status'],'not_requested');self.assertEqual(q['topics'][name]['status'],'review_required')
            self.assertFalse(q['topics'][name]['blocks_general_discovery'])
        self.assertEqual(p['topics']['soils'],q['topics']['soils']);self.assertEqual(p['offer_readiness'],'NOT_ASSESSED')
    def test_raster_fema_evidence_not_digital_clearance(self):
        c=capture();c['features'].append(feature('civil-boundaries',10,box(0,0,10,10),code='21821'))
        c['readiness_audits']=[{'sha256':'audit','document':{'orneville':{'community_id':'230465','base_product':{'product_NAME':'230465A'},'letters':[{'id':'letter'}],'letter_documents_reviewed':False,'nfhl_hazard_envelope_ids':[],'review':{'pages':4}}}}]
        t=qualify(c)['topics']['flood'];self.assertEqual(t['status'],'review_required');self.assertEqual(len(t['evidence']),1);self.assertFalse(t['inventory_intersections_usable'])
        c['features'][-1]['attributes']['GEOCODE']='other';self.assertEqual(qualify(c)['topics']['flood']['status'],'missing')
    def test_archived_orneville_evidence_regression(self):
        c=capture();c['features'].append(feature('civil-boundaries',10,box(0,0,10,10),code='21821'))
        report=Path(__file__).resolve().parents[1]/'research/county-readiness/report.json'
        import hashlib
        raw=report.read_bytes();c['readiness_audits']=[{'sha256':hashlib.sha256(raw).hexdigest(),'document':json.loads(raw)}]
        flood=qualify(c)['topics']['flood'];e=flood['evidence'][0]
        self.assertEqual(e['base_product']['product_NAME'],'230465A');self.assertEqual(len(e['letters']),27)
        self.assertEqual(e['parcel_applicability'],'UNKNOWN');self.assertFalse(flood['inventory_intersections_usable'])
    def test_unusable_requests_rejected(self):
        for change in [{'audit':'bad'},{'purchase_candidate':'false'},{'geometry':{'type':'Point','coordinates':[0,0]}},{'geometry':box(200,0,210,1).__geo_interface__}]:
            c=capture();c['request'].update(change)
            with self.assertRaises(ValueError):validate_request(c['request'])
        c=capture();c['aoi_wkb']=None
        with self.assertRaises(ValueError):qualify(c)
    def test_findings_preserved_not_auto_applied(self):
        c=capture();c['findings']=[{'id':'TL-F-0029','scope':{'county':'Piscataquis'},'status':'in_progress'}]
        p=qualify(c);self.assertEqual(p['potential_findings'][0]['id'],'TL-F-0029');self.assertIn('UNASSESSED',p['potential_findings'][0]['applicability'])
    def test_capture_from_other_audit_rejected(self):
        c=capture();c['context']['source_audit']='c'*64
        with self.assertRaises(ValueError):qualify(c)
    def test_private_output_does_not_replace_history(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'packet.json';private_write(p,{'a':1});self.assertEqual(p.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):private_write(p,{'a':2})
class ExportTests(unittest.TestCase):
    def test_export_workflow_never_connects(self):
        with tempfile.TemporaryDirectory() as d, patch('qualify_area.read_database',side_effect=AssertionError('Unexpected authentication')):
            root=Path(d);c=json.loads(json.dumps(capture()));r=root/'request.json';r.write_text(json.dumps(c['request']))
            source=root/'capture-export.json';source.write_text(json.dumps([{'jsonb_build_object':c}]))
            output=root/'packet'
            with contextlib.redirect_stdout(io.StringIO()),patch.object(sys,'argv',['qualify_area','capture','--request',str(r),'--output',str(output),'--from-export',str(source)]):
                self.assertEqual(main(),0)
            ctx=root/'context-export.json';ctx.write_text(json.dumps([{'document':c['context']}]))
            args=['qualify_area','check','--packet',str(output/'packet.json'),'--from-export',str(ctx)]
            with contextlib.redirect_stdout(io.StringIO()) as stdout,patch.object(sys,'argv',args):self.assertEqual(main(),0)
            self.assertIn('supplied_context_export',stdout.getvalue())
            c['context']['finding_dependencies']={'new':'evidence'};ctx.write_text(json.dumps([{'document':c['context']}]))
            with contextlib.redirect_stdout(io.StringIO()),patch.object(sys,'argv',args):self.assertEqual(main(),2)
            c['request']['purchase_candidate']=True;source.write_text(json.dumps([{'jsonb_build_object':c}]))
            with patch.object(sys,'argv',['qualify_area','capture','--request',str(r),'--output',str(root/'wrong'),'--from-export',str(source)]),self.assertRaises(ValueError):main()
            self.assertFalse((root/'wrong').exists())
    def test_invalid_exports_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'export.json'
            for value in [[],[{},{}],[{'document':None}],[{'unexpected':{}}],{'document':{}}]:
                p.write_text(json.dumps(value))
                with self.assertRaises(ValueError):read_export(p,'document')
    def test_generated_sql_preserves_readonly_and_quotes(self):
        r=capture()['request'];r['note']="a'b\\c"
        for context_only in (False,True):
            sql=query_sql(r,context_only)
            self.assertTrue(sql.startswith('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;'))
            self.assertTrue(sql.endswith('COMMIT;'))
            self.assertIn('standard_conforming_strings=on',sql)
            self.assertIn("a''b",sql)
            self.assertEqual('select document from context;' in sql,context_only)

if __name__=='__main__':unittest.main()
