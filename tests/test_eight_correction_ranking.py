import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import test_county_ranking_refresh as prior
from refresh_eight_correction_ranking import BASE,ROOT,ACTIVATIONS,validate_dependencies

class EightRankingTests(prior.RankingTests):
    def test_live_cohort_dependencies(self):
        d=json.loads((BASE/'dependencies.json').read_text())
        cs=[c for p in ACTIVATIONS for c in json.loads((ROOT/p).read_text())['corrections']]
        ids=[r['object_id'] for r in json.loads((ROOT/'research/piscataquis-zoning-holds/ranking.json').read_text())['ranking']]
        self.assertEqual(len(cs),8);self.assertEqual(len(d['held_object_ids']),154)
        validate_dependencies(d,cs,ids)
        for mutate in [lambda x:x['snapshot'].update(needs_revisit=True),lambda x:x['held_object_ids'].append(cs[-1]['object_id']),lambda x:x['snapshot']['dependencies'][cs[-1]['correction_id']].update(event_id='changed'),lambda x:x['accepted'][0].update(candidate_sha256='changed')]:
            bad=copy.deepcopy(d);mutate(bad)
            with self.assertRaises(ValueError):validate_dependencies(bad,cs,ids)
