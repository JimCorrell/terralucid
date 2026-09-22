import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import box,MultiPolygon,shape,mapping
from shapely.ops import unary_union
from investigate_ten_case_zoning import compare_source,scenario_area,BASE,ROOT,IDS
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
    def test_exact_eleven_fixed_candidates(self):
        r=json.loads((BASE/'report.json').read_text());self.assertEqual([c['object_id'] for c in r['cases']],IDS)
        for c in r['cases']:
            raw=(ROOT/c['candidate_path']).read_bytes();self.assertEqual(digest(raw),c['candidate_sha256'])
            candidate=shape(json.loads(raw)['geometry']);e=r['evidence'][c['native_evidence']]
            native=json.loads((ROOT/e['response_path']).read_text());rings=native['features'][0]['geometry']['rings']
            from investigate_katahdin_contacts import review_katahdin_cycles
            fn=review_katahdin_cycles if c['object_id']==27358396 else review_cycles
            self.assertEqual(fn(rings,candidate),c['cycle_review'])
            self.assertEqual(review_geometry(rings,candidate),c['independent_fill_check'])
            self.assertLess(abs(c['area_difference_from_publisher_m2']),0.00001)
            self.assertEqual(c['status'],'proposed_not_accepted')


class NestedOwnership(unittest.TestCase):
    def rings(self):
        from shapely.geometry.polygon import orient
        return [list(orient(box(*bounds),sign=sign).exterior.coords) for bounds,sign in [((0,0,10,10),-1),((1,1,9,9),1),((2,2,8,8),-1),((3,3,4,4),1),((5,5,6,6),1)]]
    def test_multiple_holes_choose_innermost_shell(self):
        from investigate_moosehead_spencer import propose
        rings=self.rings();g,d=propose(rings)
        self.assertTrue(g.is_valid);self.assertAlmostEqual(g.area,70)
        self.assertEqual(sorted(len(p.interiors) for p in g.geoms),[1,2])
        self.assertTrue(review_geometry(rings,g)['equals_independent_even_odd_fill'])
        review_cycles(rings,g)
    def test_same_segments_wrong_parent_rejected(self):
        from shapely.geometry import Polygon
        r=self.rings();bad=MultiPolygon([Polygon(r[0],[r[1],r[3],r[4]]),Polygon(r[2])])
        with self.assertRaises(ValueError):review_geometry(r,bad)
    def test_missing_enclosing_hole_rejected(self):
        from investigate_moosehead_spencer import propose
        r=self.rings()
        with self.assertRaises(ValueError):propose([r[0],*r[2:]])

class KatahdinContacts(unittest.TestCase):
    def ring(self):
        return [[0,0],[2,1],[1,2],[0,0],[0,10],[10,10],[8,9],[9,8],[10,10],[10,0],[0,0]]
    def test_two_contact_shell_and_holes(self):
        from investigate_katahdin_contacts import propose_katahdin,review_katahdin_cycles
        r=[self.ring()];g,d=propose_katahdin(r)
        self.assertAlmostEqual(g.area,97);self.assertEqual(len(g.geoms[0].interiors),2)
        self.assertTrue(review_katahdin_cycles(r,g)['source_cycle_roles_preserved'])
        self.assertTrue(review_geometry(r,g)['equals_independent_even_odd_fill'])
    def test_rotated_traversal(self):
        from investigate_katahdin_contacts import propose_katahdin,review_katahdin_cycles
        r=self.ring()[:-1];r=r[4:]+r[:4];r.append(r[0]);g,d=propose_katahdin([r])
        self.assertAlmostEqual(g.area,97);review_katahdin_cycles([r],g)
    def test_reject_reversed_roles(self):
        from investigate_katahdin_contacts import split_two_contacts
        with self.assertRaises(ValueError):split_two_contacts(list(reversed(self.ring())))
    def test_reject_crossing_without_repeated_vertices(self):
        from investigate_katahdin_contacts import split_two_contacts
        with self.assertRaises(ValueError):split_two_contacts([[0,0],[2,2],[0,2],[2,0],[0,0]])
    def test_reject_duplicate_and_nonfinite(self):
        from investigate_katahdin_contacts import split_two_contacts
        r=self.ring();r.insert(1,r[0])
        with self.assertRaises(ValueError):split_two_contacts(r)
        r=self.ring();r[1]=[float('nan'),1]
        with self.assertRaises(ValueError):split_two_contacts(r)
    def test_reject_hole_removed(self):
        from investigate_katahdin_contacts import propose_katahdin,review_katahdin_cycles
        from shapely.geometry import Polygon
        r=[self.ring()];g,_=propose_katahdin(r);p=g.geoms[0];bad=MultiPolygon([Polygon(p.exterior,[p.interiors[0]])])
        with self.assertRaises(ValueError):review_katahdin_cycles(r,bad)
        with self.assertRaises(ValueError):review_geometry(r,bad)
    def test_reject_single_contact(self):
        from investigate_katahdin_contacts import split_two_contacts
        with self.assertRaises(ValueError):split_two_contacts([[0,0],[2,1],[1,2],[0,0],[0,10],[10,10],[10,0],[0,0]])
    def test_map_discrepancies_remain_open(self):
        maps=json.loads((BASE/'map-review.json').read_text())
        self.assertEqual(len(maps['new_date_discrepancies']),5)
        self.assertEqual(len(maps['retained_prior_followups']),2)
        self.assertNotEqual(maps['maps']['shawtown-twp']['effective'],maps['maps']['shawtown-twp']['latest_listed_amendment'])

if __name__=='__main__':unittest.main()
