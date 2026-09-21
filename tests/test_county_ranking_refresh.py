import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import box, MultiPolygon
from shapely.ops import unary_union
from refresh_county_ranking import newly_covered, refreshed_area, validate_dependencies, BASE, ROOT, ACTIVATIONS, jurisdiction_reductions

class RankingTests(unittest.TestCase):
    def test_overlap_holes_touch_and_disjoint(self):
        gap=MultiPolygon([box(0,0,10,10).difference(box(3,3,7,7)),box(20,0,25,5)])
        candidates=[box(-1,-1,5,6),box(2,2,9,9),box(10,0,12,2),box(21,1,30,4)]
        actual=newly_covered(gap,candidates)
        expected=gap.intersection(unary_union(candidates))
        self.assertLess(unary_union(actual).symmetric_difference(expected).area,1e-9)
        self.assertAlmostEqual(sum(p.area for p in actual),expected.area)
        env=box(2,1,23,8)
        self.assertAlmostEqual(refreshed_area(gap.intersection(env).area,sum(p.intersection(env).area for p in actual)),gap.difference(unary_union(candidates)).intersection(env).area)
    def test_multiple_records_per_jurisdiction(self):
        r=jurisdiction_reductions([box(0,0,10,10)],[('islands',box(0,0,1,1)),('islands',box(2,2,4,4)),('other',box(20,20,21,21))])
        self.assertEqual(r['islands'],5)
        self.assertEqual(r['other'],0)
    def test_no_intersection(self):
        self.assertEqual(newly_covered(box(0,0,1,1),[box(2,2,3,3)]),[])
    def test_bad_subtraction(self):
        with self.assertRaises(ValueError):refreshed_area(1,2)
    def test_live_cohort_dependencies(self):
        d=json.loads((BASE/'dependencies.json').read_text())
        cs=[c for p in ACTIVATIONS for c in json.loads((ROOT/p).read_text())['corrections']]
        ids=[r['object_id'] for r in json.loads((ROOT/'research/piscataquis-zoning-holds/ranking.json').read_text())['ranking']]
        validate_dependencies(d,cs,ids)
        for mutate in [lambda x:x['snapshot'].update(needs_revisit=True),lambda x:x['held_object_ids'].append(cs[0]['object_id']),lambda x:x['snapshot']['dependencies'][cs[0]['correction_id']].update(event_id='changed'),lambda x:x['accepted'][0].update(candidate_sha256='changed')]:
            bad=copy.deepcopy(d);mutate(bad)
            with self.assertRaises(ValueError):validate_dependencies(bad,cs,ids)

if __name__=='__main__':unittest.main()
