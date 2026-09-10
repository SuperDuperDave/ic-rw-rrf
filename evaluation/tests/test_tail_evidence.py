"""Handcrafted tail-support/depth checks; no dataset evaluation.

Run: python3 -B -m unittest discover -s evaluation/tests -p test_tail_evidence.py -v
"""

from pathlib import Path
import tempfile
import unittest

from evaluation.cycle01_tail_evidence import (
    aggregate_ensembles,
    depth_variants,
    evaluate_query,
    group_statistics,
    new_output_directory,
    ranking_transition,
    specialist_candidates,
    summarize_groups,
    write_json,
)


def fixture_candidates():
    # Other-source rank30 fails eligibility; rank31 provides tail support.
    owner = ['tail', 'isolated', 'at30', 'shared', 'late_isolated']
    other = ['shared'] + ['other-{}'.format(i) for i in range(2, 30)] + ['at30', 'tail']
    qrel = {'tail': 3, 'isolated': 0, 'late_isolated': 2}
    return specialist_candidates(['owner', 'other'], [owner, other], qrel)


class TailEvidenceTests(unittest.TestCase):
    def test_specialist_eligibility_requires_absence_from_all_other_top30(self):
        candidates = fixture_candidates()
        docs = {row['docid']: row for row in candidates}
        self.assertNotIn('at30', docs)
        self.assertNotIn('shared', docs)
        self.assertEqual(docs['tail']['group'], 'tail_supported')
        self.assertEqual(docs['tail']['owner_source'], 'owner')
        self.assertEqual(docs['tail']['full_source_evidence']['source_ranks'], {'owner': 1, 'other': 31})
        self.assertEqual(docs['tail']['full_source_evidence']['top30_coverage_count'], 1)
        self.assertEqual(docs['isolated']['group'], 'isolated')
        self.assertEqual(docs['late_isolated']['stratum'], 'rank4_10')
        self.assertEqual(len(docs), len(candidates))
        # A third source top30 vetoes eligibility even when another source has tail support.
        third = specialist_candidates(['a', 'b', 'c'],
                                      [['tail'], ['b{}'.format(i) for i in range(30)] + ['tail'], ['tail']], {})
        self.assertNotIn('tail', [row['docid'] for row in third])

    def test_unjudged_and_explicit_zero_have_different_judged_denominators(self):
        candidates = specialist_candidates(['a', 'b'], [['yes', 'zero', 'missing'], []], {'yes': 3, 'zero': 0})
        stats = group_statistics(candidates)
        self.assertEqual(stats['n_candidates'], 3)
        self.assertEqual(stats['n_judged'], 2)
        self.assertEqual(stats['n_unjudged'], 1)
        self.assertAlmostEqual(stats['judged_fraction'], 2 / 3)
        self.assertEqual(stats['relevance_ge2_among_judged'], .5)
        self.assertAlmostEqual(stats['all_candidate_relevance_ge2'], 1 / 3)
        self.assertAlmostEqual(stats['all_candidate_mean_graded_gain'], 7 / 3)
        unknown = group_statistics([row for row in candidates if row['docid'] == 'missing'])
        self.assertIsNone(unknown['relevance_ge2_among_judged'])
        self.assertEqual(unknown['all_candidate_relevance_ge2'], 0)
        self.assertIsNone(group_statistics([])['all_candidate_relevance_ge2'])

    def test_group_contrasts_use_only_queries_with_both_groups(self):
        both = fixture_candidates()
        isolated_only = [row for row in both if row['group'] == 'isolated']
        no_judged_isolated = [dict(row, judged=False, grade_unjudged_zero=0,
                                   relevant_ge2_unjudged_zero=0, gain_unjudged_zero=0)
                               if row['group'] == 'isolated' else dict(row) for row in both]
        result = summarize_groups({'both': both, 'single': isolated_only, 'partial': no_judged_isolated}, n_boot=20)
        self.assertEqual(result['n_queries_with_both_groups'], 2)
        contrasts = result['paired_tail_supported_minus_isolated']
        self.assertEqual(contrasts['all_candidate_relevance_ge2']['summary']['n_queries'], 2)
        self.assertEqual(contrasts['relevance_ge2_among_judged']['eligible_qids'], ['both'])
        self.assertEqual(contrasts['relevance_ge2_among_judged']['summary']['n_queries'], 1)
        no_pairs = summarize_groups({'single': isolated_only}, n_boot=20)
        self.assertIsNone(no_pairs['paired_tail_supported_minus_isolated']['judged_fraction']['summary']['mean_delta'])

    def test_depth_arms_equalize_per_query_without_padding_or_mutating(self):
        lists = [[str(i) for i in range(40)], ['short', 'two']]
        variants = depth_variants(lists)
        self.assertEqual(list(map(len, variants['full'])), [40, 2])
        self.assertEqual(list(map(len, variants['equalized'])), [2, 2])
        self.assertEqual(list(map(len, variants['top30_cap'])), [30, 2])
        variants['equalized'][0].append('changed')
        self.assertEqual(len(lists[0]), 40)

    def test_pure_reordering_changes_ndcg_without_entrants_or_exits(self):
        # z has ranks (1,100); a has (40,40). k60 favors z, k200 favors a.
        sources = [['f{}-{}'.format(index, rank) for rank in range(1, 101)] for index in range(2)]
        sources[0][0], sources[1][99] = 'z', 'z'
        sources[0][39], sources[1][39] = 'a', 'a'
        result = evaluate_query(['first', 'second'], sources, {'z': 3, 'a': 0})
        full = result['arms']['full']
        self.assertLess(full['ndcg10_delta_k200_minus_k60'], 0)
        transition = full['transition']
        self.assertEqual(transition['entrants'], [])
        self.assertEqual(transition['exits'], [])
        self.assertFalse(transition['membership_changed'])
        self.assertTrue(transition['ordered_top10_changed'])
        changed = {row['docid']: row for row in transition['position_changes']}
        self.assertEqual(set(changed), {'a', 'z'})
        self.assertEqual(changed['z']['k60_fused_rank'], 1)
        self.assertEqual(changed['z']['k200_fused_rank'], 2)
        self.assertEqual(changed['z']['active_source_evidence']['source_ranks'], {'first': 1, 'second': 100})
        candidates = {row['docid']: row for row in result['specialist_candidates']}
        self.assertEqual(candidates['z']['group'], 'tail_supported')
        self.assertEqual(candidates['z']['full_source_evidence']['source_ranks']['second'], 100)

    def test_entrants_and_exits_keep_positions_outside_top10(self):
        old = ['d{}'.format(index) for index in range(11)]
        new = [old[10]] + old[1:10] + [old[0]]
        result = ranking_transition(old, new, ['source'], [old], [old], {'d0': 3, 'd10': 2})
        self.assertEqual(result['entrants'], ['d10'])
        self.assertEqual(result['exits'], ['d0'])
        changes = {row['docid']: row for row in result['position_changes']}
        self.assertEqual(set(changes), {'d0', 'd10'})
        self.assertEqual(changes['d0']['k60_fused_rank'], 1)
        self.assertEqual(changes['d0']['k200_fused_rank'], 11)
        self.assertEqual(changes['d10']['k60_fused_rank'], 11)
        self.assertEqual(changes['d10']['k200_fused_rank'], 1)

    def test_repeated_ensemble_effects_are_averaged_within_query(self):
        def row(value):
            return {'arms': {arm: {'ndcg10_delta_k200_minus_k60': value,
                                   'k_effect_delta_minus_full': 0,
                                   'ndcg10_k60_minus_full': 0,
                                   'ndcg10_k200_minus_full': 0}
                             for arm in ('full', 'equalized', 'top30_cap')}}
        result = aggregate_ensembles({'n4': {'q1': row(1), 'q2': row(0)},
                                      'n5': {'q1': row(0), 'q2': row(0)}}, n_boot=20)
        metric = result['depth_arms']['full']['ndcg10_delta_k200_minus_k60']
        self.assertEqual(metric['summary']['n_queries'], 2)
        self.assertEqual(metric['per_query_deltas'], {'q1': .5, 'q2': 0})
        self.assertEqual(metric['summary']['mean_delta'], .25)
        with self.assertRaises(ValueError):
            aggregate_ensembles({'n4': {'q1': row(0)}, 'n5': {'q2': row(0)}}, n_boot=20)

    def test_evidence_directory_and_json_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'new-run'
            output = new_output_directory(path)
            with self.assertRaises(FileExistsError):
                new_output_directory(path)  # Even an existing empty directory is rejected.
            artifact = output / 'test.json'
            write_json(artifact, {'original': True})
            original = artifact.read_text()
            with self.assertRaises(FileExistsError):
                write_json(artifact, {'original': False})
            self.assertEqual(artifact.read_text(), original)


if __name__ == '__main__':
    unittest.main()
