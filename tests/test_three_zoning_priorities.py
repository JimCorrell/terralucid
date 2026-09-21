import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import box,MultiPolygon,shape,mapping
from shapely.ops import unary_union
from investigate_three_zoning_priorities import compare_source,scenario_area,BASE,ROOT,IDS
from prepare_source_staging import digest
from review_moosehead_spencer import review_cycles
from review_county_zoning_proposals import review_geometry

class ThreePriorities(unittest.TestCase):
    def fixture(self):
        g=box(0,0,3,3);o={'attributes':{'OBJECTID':1,'ZONE':'P-SL2'},'geometry':{'rings':[list(g.exterior.coords)]}}
        n={'spatialReference':{'wkid':26919},'features':[copy.deepcopy(o)]}
        j={'crs':{'properties':{'name':'EPSG:26919'}},'features':[{'properties':copy.deepcopy(o['attributes']),'geometry':mapping(g)}]}
        return o,n,j
    def test_exact_variants(self):
        o,n,j=self.fixture();self.assertTrue(compare_source(o,n,j,1).is_valid)
    def test_source_version_change(self):
        o,n,j=self.fixture();n['features'][0]['attributes']['ZONE']='M-GN'
        with self.assertRaises(ValueError):compare_source(o,n,j,1)
    def test_incomplete_and_wrong_crs(self):
        for change in [lambda n:n.update(exceededTransferLimit=True),lambda n:n.update(features=[]),lambda n:n.update(spatialReference={'wkid':4326})]:
            o,n,j=self.fixture();change(n)
            with self.assertRaises(ValueError):compare_source(o,n,j,1)
    def test_geojson_segment_change(self):
        o,n,j=self.fixture();j['features'][0]['geometry']=mapping(box(0,0,4,3))
        with self.assertRaises(ValueError):compare_source(o,n,j,1)
    def test_overlapping_proposals_and_baseline(self):
        gap=MultiPolygon([box(0,0,10,10).difference(box(2,2,3,3)),box(20,0,30,10)])
        proposed=[box(-1,-1,6,6),box(4,4,25,8)];accepted=[box(1,1,5,5),box(3,3,7,7)]
        expected=gap.intersection(unary_union(proposed)).difference(unary_union(accepted)).area
        self.assertAlmostEqual(scenario_area(gap,proposed,accepted),expected)
    def test_exact_three_fixed_candidates(self):
        r=json.loads((BASE/'report.json').read_text());self.assertEqual([c['object_id'] for c in r['cases']],IDS)
        for c in r['cases']:
            raw=(ROOT/c['candidate_path']).read_bytes();self.assertEqual(digest(raw),c['candidate_sha256'])
            candidate=shape(json.loads(raw)['geometry']);e=r['evidence'][c['native_evidence']]
            native=json.loads((ROOT/e['response_path']).read_text());rings=native['features'][0]['geometry']['rings']
            self.assertEqual(review_cycles(rings,candidate),c['cycle_review'])
            self.assertEqual(review_geometry(rings,candidate),c['independent_fill_check'])
            self.assertLess(abs(c['area_difference_from_publisher_m2']),0.00001)
            self.assertEqual(c['status'],'proposed_not_accepted')

if __name__=='__main__':unittest.main()
