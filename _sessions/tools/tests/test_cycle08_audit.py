"""Synthetic-only independent cycle08 regressions; never enumerate the task seed."""
import importlib.util
from copy import deepcopy
from pathlib import Path
import unittest
from unittest import mock


PATH = Path(__file__).resolve().parents[1] / 'check_cycle08_evidence.py'
SPEC = importlib.util.spec_from_file_location('cycle08_independent_under_test', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

PLUS = '''a = 1
b = 1
c = 1
for i in range(4):
    a = (a * b + c) % 997
    b = (b * c + a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 0)
'''
MINUS = PLUS.replace('b = 1', 'b = 2').replace('c = 1', 'c = 3')
MINUS = MINUS.replace('a * b + c', 'a * b - c').replace('b * c + a', 'b * c - a')
MINUS = MINUS.replace('a % 3 == 0', 'a % 3 == 1')


class TruthTests(unittest.TestCase):
    def test_hand_computed_plus_states_and_counts(self):
        row = audit.evaluate_program(PLUS)
        self.assertEqual(row['loop_states'], [
            {'a': 1, 'b': 1, 'c': 1}, {'a': 2, 'b': 3, 'c': 5},
            {'a': 11, 'b': 26, 'c': 81}, {'a': 367, 'b': 479, 'c': 296},
            {'a': 617, 'b': 827, 'c': 11}])
        self.assertEqual(row['final_state'], {'a': 447, 'b': 838, 'c': 11, 'i': 3})
        self.assertIs(row['answer'], True)
        self.assertEqual(row['executed_statements'], 27)
        self.assertEqual(row['worst_case_executed_statements'], 31)
        self.assertEqual(row['branch_counts'], {'true': 0, 'false': 4})
        self.assertEqual(row['max_abs_intermediate'], 183459)

    def test_hand_computed_minus_modulo_and_taken_branch(self):
        row = audit.evaluate_program(MINUS)
        self.assertEqual(row['loop_states'], [
            {'a': 1, 'b': 2, 'c': 3}, {'a': 996, 'b': 7, 'c': 4},
            {'a': 986, 'b': 39, 'c': 992}, {'a': 573, 'b': 229, 'c': 965},
            {'a': 642, 'b': 6, 'c': 263}])
        self.assertEqual(row['final_state'], {'a': 648, 'b': 269, 'c': 263, 'i': 3})
        self.assertIs(row['answer'], False)
        self.assertEqual(row['branch_counts'], {'true': 2, 'false': 2})
        self.assertEqual(row['executed_statements'], 29)
        self.assertEqual(row['max_abs_intermediate'], 623388)

    def test_entire_exact_ast_is_checked(self):
        mutations = [('a * b + c', 'a * b + i'), ('c = (c + b) % 997', 'c = abs(b)'),
            ('c = (c + b) % 997', 'import os'), ('b < c', 'b <= c'),
            ('a * b + c', 'a ** b + c'), ('% 997', '% 991'), ('range(4)', 'range(5)'),
            ('range(4)', 'range(a)'), ('a = 1', 'a = True'), ('a = 1', 'a = 997'),
            ('a = 1', 'a = 0'), ('a % 3 == 0', 'a % 3 != 0'),
            ('a = (a + b) % 997', 'a = 0'), ('a = 1\nb = 1', 'a = 1; b = 1')]
        for before, after in mutations:
            with self.subTest(mutation=after), self.assertRaises(ValueError):
                audit.evaluate_program(PLUS.replace(before, after))

    def test_static_and_actual_bounds_are_distinct(self):
        with mock.patch.object(audit, 'MAX_STEPS', 30), self.assertRaises(ValueError):
            audit.evaluate_program(PLUS)
        with mock.patch.object(audit, 'MAX_MAGNITUDE', 1000), self.assertRaises(ValueError):
            audit.evaluate_program(PLUS)
        row = audit.evaluate_program(PLUS.replace('range(4)', 'range(64)'))
        self.assertEqual(row['worst_case_executed_statements'], 391)
        self.assertLessEqual(row['executed_statements'], 391)
        self.assertLessEqual(row['max_abs_intermediate'], 993012)


class MatchingTests(unittest.TestCase):
    def test_matching_prefix_tail_and_actual_source_only_n(self):
        row = audit.matched_audit(PLUS, PLUS.replace('range(4)', 'range(64)'))
        self.assertEqual(len(row['prefix_results']), 65)
        self.assertEqual(row['prefix_results'][0],
                         {'iterations': 0, 'final_state': {'a': 2, 'b': 2, 'c': 1}, 'answer': False})
        self.assertEqual(row['prefix_results'][4],
                         {'iterations': 4, 'final_state': {'a': 447, 'b': 838, 'c': 11}, 'answer': True})
        self.assertTrue(row['only_n_changes'])
        with self.assertRaises(ValueError):
            audit.matched_audit(PLUS, PLUS.replace('range(4)', 'range(64)').replace('c = 1', 'c = 2'))

    def test_first_repeated_full_state_ignores_iteration_index(self):
        states = [{'a': 1, 'b': 2, 'c': 3}, {'a': 4, 'b': 5, 'c': 6},
                  {'a': 7, 'b': 8, 'c': 9}, {'a': 4, 'b': 5, 'c': 6},
                  {'a': 7, 'b': 8, 'c': 9}]
        self.assertEqual(audit.first_cycle(states), {'entry': 1, 'period': 2, 'repeat_at': 3})
        self.assertIsNone(audit.first_cycle(states[:3]))
        self.assertEqual(audit.first_cycle(states[:1] * 2), {'entry': 0, 'period': 1, 'repeat_at': 1})

    def test_structural_normalization_removes_bound_constants_names_predicate(self):
        variant = PLUS.replace('range(4)', 'range(64)').replace('a = 1', 'a = 37')
        variant = variant.replace('a % 3 == 0', 'a % 3 != 2')
        variant = variant.replace('a', 'x').replace('b', 'y').replace('c', 'z')
        # A lexical rename above also changes range; keep that builtin fixed.
        variant = variant.replace('rxnge', 'range')
        self.assertEqual(audit.normalized_template(PLUS), audit.normalized_template(variant))
        self.assertNotEqual(audit.normalized_template(PLUS), audit.normalized_template(MINUS))

    def test_minus_tail_identity_is_only_a_last_step_reduction(self):
        row = audit.evaluate_program(MINUS)
        previous = row['loop_states'][-2]
        self.assertEqual(row['final_state']['a'], previous['b'] * previous['c'] % 997)
        self.assertNotEqual(previous, row['loop_states'][0])


def synthetic_review():
    return {'schema_version': 1, 'reviewer': 'synthetic reviewer',
        'source_sha256': {key: '0' * 64 for key in (audit.CODE, audit.CHECKER, audit.DESIGN, audit.PROTOCOL)},
        'reviews': [{'operators': list(operators), 'demonstrated_bound_irrelevance': False,
                     'proof': '', 'reduction_finding': 'Synthetic source finding; no claimed shortcut.'}
                    for operators in audit.OPERATOR_PAIRS]}


class GateTests(unittest.TestCase):
    def setUp(self):
        self.templates = [{'template_id': str(i), 'operators': list(operators),
            'audit': {'same_final_state': False, 'first_cycle': None,
                      'constant_prefix_answer': True, 'endpoint_answers_equal': True}}
            for i, operators in enumerate(audit.OPERATOR_PAIRS)]
        self.items = [{'python_truth': {'answer': bool(i % 2)}} for i in range(8)]

    def test_only_explicit_gate_conditions_apply(self):
        result = audit.independent_decision(self.templates, self.items, synthetic_review())
        self.assertEqual(result, {'status': 'consider_execution_freeze', 'park_reasons': [],
                                  'empirical_launch_authorized': False})
        self.assertEqual(audit.independent_decision(self.templates, self.items, None)['status'],
                         'pending_source_review')
        equal = [{'python_truth': {'answer': True}} for _ in range(8)]
        self.assertEqual(audit.independent_decision(self.templates, equal, synthetic_review())['park_reasons'],
                         [{'code': 'all_eight_answers_equal'}])
        self.assertEqual(audit.independent_decision(self.templates[:3], self.items[:6], None)['park_reasons'],
                         [{'code': 'insufficient_distinct_templates'}])

    def test_state_and_proved_shortcut_failures_accumulate(self):
        self.templates[1]['audit'].update(same_final_state=True,
            first_cycle={'entry': 0, 'period': 1, 'repeat_at': 1})
        review = synthetic_review()
        review['reviews'][3].update(demonstrated_bound_irrelevance=True, proof='Synthetic explicit proof.')
        result = audit.independent_decision(self.templates, self.items, review)
        self.assertEqual(result['status'], 'parked')
        self.assertEqual(result['park_reasons'], [
            {'code': 'identical_final_triples', 'template_id': '1'},
            {'code': 'repeated_transition_state', 'template_id': '1'},
            {'code': 'demonstrated_bound_irrelevance', 'template_id': '3'}])
        review['reviews'][3]['proof'] = ''
        with self.assertRaises(ValueError):
            audit.independent_decision(self.templates, self.items, review)


class PanelTests(unittest.TestCase):
    def synthetic_panel(self):
        # Every literal is manually fixed, never drawn from the actual seed.
        candidates, templates, items = [], [], []
        parameters = {'A': 1, 'B': 1, 'C': 1, 'R': 0}
        for attempt, operators in enumerate(audit.OPERATOR_PAIRS):
            base = PLUS.replace('a * b + c', 'a * b ' + operators[0] + ' c')
            base = base.replace('b * c + a', 'b * c ' + operators[1] + ' a')
            sources = {'4': base, '64': base.replace('range(4)', 'range(64)')}
            hashes = {n: audit.sha(source.encode()) for n, source in sources.items()}
            truth = {n: audit.evaluate_program(source) for n, source in sources.items()}
            digest = audit.sha(audit.normalized_template(base).encode())
            tid = 't_' + digest[:20]
            candidate = {'attempt': attempt, 'parameters': dict(parameters), 'operators': list(operators),
                'programs': sources, 'program_sha256': hashes, 'template_hash': digest,
                'status': 'accepted', 'reason': None, 'checks': {n: {key: value[key] for key in
                    ('answer', 'executed_statements', 'max_abs_intermediate')} for n, value in truth.items()}}
            candidates.append(candidate)
            new_items = [{'item_id': 'i_' + hashes[str(n)][:20], 'template_id': tid, 'n': n,
                'program': sources[str(n)], 'program_sha256': hashes[str(n)], 'python_truth': truth[str(n)]}
                for n in (4, 64)]
            templates.append({'template_id': tid, 'template_hash': digest, 'parameters': dict(parameters),
                'operators': list(operators), 'item_ids': [item['item_id'] for item in new_items],
                'audit': audit.matched_audit(sources['4'], sources['64'])})
            items.extend(new_items)
        return {'schema_version': 1, 'old_template_hashes': [f'{i:064x}' for i in range(24)],
            'generation': {'seed': 420008, 'max_attempts': 32, 'attempt_count': 4, 'candidates': candidates},
            'bounds': {'loop_bounds': [4, 64], 'max_abs_integer': 1000000,
                       'max_executed_statements': 512, 'source_lines': 12},
            'items': items, 'templates': templates, 'source_review': None,
            'decision': audit.independent_decision(templates, items, None)}

    def check_synthetic(self, panel):
        fake_rng = mock.Mock()
        fake_rng.randint.side_effect = [1, 1, 1, 0] * 4
        with mock.patch.object(audit.random, 'Random', return_value=fake_rng):
            return audit.verify_panel(panel)

    def test_full_synthetic_reconstruction_rejects_trace_and_gate_corruption(self):
        panel = self.synthetic_panel()
        self.assertEqual(self.check_synthetic(panel)['program_count'], 8)
        corrupt = deepcopy(panel)
        corrupt['items'][1]['python_truth']['loop_states'][63]['a'] += 1
        with self.assertRaises(ValueError):
            self.check_synthetic(corrupt)
        corrupt = deepcopy(panel)
        corrupt['decision']['empirical_launch_authorized'] = True
        with self.assertRaises(ValueError):
            self.check_synthetic(corrupt)


if __name__ == '__main__':
    unittest.main()
