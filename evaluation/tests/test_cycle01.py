import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'evaluation'))
from cycle01_rank_geometry import cv_predictions, paired_summary, identifiability_fixture, full_coverage_counterexample


class Cycle01ProtocolTests(unittest.TestCase):
    def test_held_out_labels_cannot_select_their_own_parameter(self):
        scores = {'q{:02d}'.format(i): {1:.4, 60:.5} for i in range(15)}
        baseline, folds = cv_predictions(scores, seed=42, grid=[1,60])
        held_out = folds[0]['test_qids']
        # Change every score in one test fold enough to dominate a leaky selector.
        changed = {q:dict(values) for q,values in scores.items()}
        for q in held_out:changed[q][1] = 100.0
        predictions, new_folds = cv_predictions(changed,seed=42,grid=[1,60])
        self.assertEqual(folds[0]['selected_k'],new_folds[0]['selected_k'])
        self.assertEqual(set(held_out) & set(folds[0]['train_qids']),set())
        self.assertEqual(sorted(baseline),sorted(scores))
        for q in held_out:self.assertEqual(predictions[q]['k'],60)

    def test_query_bootstrap_preserves_constant_effect(self):
        result=paired_summary([.1]*7,n_boot=100,seed=2)
        self.assertEqual(result['n_queries'],7)
        self.assertAlmostEqual(result['mean_delta'],.1)
        for bound in result['conditional_query_bootstrap_95']:
            self.assertAlmostEqual(bound,.1)

    def test_truth_swap_changes_scores_without_changing_observations(self):
        fixture=identifiability_fixture()
        self.assertEqual(fixture['observations']['confidences'],[.5,.5,.5])
        outcomes=fixture['ndcg10']
        self.assertGreater(outcomes['majority_correct']['rrf60'],outcomes['specialist_correct']['rrf60'])
        self.assertEqual(set(outcomes['majority_correct']),set(fixture['rankings_top10']))

    def test_duplicate_counterexample_does_not_need_missing_candidates(self):
        fixture=full_coverage_counterexample()
        self.assertTrue(all(set(source)==set(fixture['base'][0]) for source in fixture['copied']))
        for outcome in fixture['grid_results'].values():
            self.assertTrue(outcome['base_y_above_x'])
            self.assertTrue(outcome['copied_x_above_y'])

if __name__=='__main__':unittest.main()
