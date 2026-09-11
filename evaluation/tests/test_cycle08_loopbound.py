"""Synthetic-only cycle08 regressions. Never enumerate the actual seed/panel."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evaluation import cycle08_loopbound as m


PARAMETERS = {'A': 1, 'B': 2, 'C': 3, 'R': 1}
OLD_HASHES = [f'{i:064x}' for i in range(24)]


def synthetic_candidates(operators=m.OPERATOR_PAIRS):
    for attempt, pair in enumerate(operators):
        yield {'attempt': attempt, 'parameters': dict(PARAMETERS), 'operators': list(pair)}


def source_review(irrelevant=False):
    return {'schema_version': 1, 'reviewer': 'synthetic unit-test reviewer',
            'source_sha256': {name: 'a' * 64 for name in m.REVIEW_SOURCES},
            'reviews': [{'operators': list(ops), 'demonstrated_bound_irrelevance': irrelevant,
                         'proof': 'synthetic proof fixture' if irrelevant else '',
                         'reduction_finding': 'synthetic review fixture'}
                        for ops in m.OPERATOR_PAIRS]}


def synthetic_panel():
    return m._assemble_panel(synthetic_candidates(), OLD_HASHES, source_review())


class SemanticsTests(unittest.TestCase):
    def test_hand_checked_sequential_updates_trace_tail_and_counts(self):
        truth = m.python_truth(m.render_program(PARAMETERS, ('+', '+'), 4))
        self.assertEqual(truth['loop_states'], [
            {'a': 1, 'b': 2, 'c': 3}, {'a': 5, 'b': 11, 'c': 26},
            {'a': 81, 'b': 367, 'c': 479}, {'a': 296, 'b': 617, 'c': 827},
            {'a': 11, 'b': 803, 'c': 787}])
        self.assertEqual(truth['final_state'], {'a': 814, 'b': 593, 'c': 787, 'i': 3})
        self.assertIs(truth['answer'], True)
        self.assertEqual(truth['executed_statements'], 28)
        self.assertEqual(truth['worst_case_executed_statements'], 31)
        self.assertEqual(truth['max_abs_intermediate'], 510270)
        self.assertEqual(truth['branch_counts'], {'true': 1, 'false': 3})

    def test_negative_modulo(self):
        truth = m.python_truth(m.render_program({'A': 1, 'B': 1, 'C': 2, 'R': 0}, ('-', '-'), 4))
        self.assertEqual(truth['loop_states'][1], {'a': 996, 'b': 3, 'c': 1})

    def test_full_ast_rejection_precedes_exec_even_in_unreached_branch(self):
        source = m.render_program(PARAMETERS, ('+', '+'), 4)
        variants = (
            source.replace('a = 1', 'a = True', 1),
            source.replace('a = 1', 'a = 997', 1),
            source.replace('a = 1', 'a = abs(1)', 1),
            source.replace('b = 2', 'import os', 1),
            source.replace('range(4)', 'range(1000000)'),
            source.replace('range(4)', 'range(3)'),
            source.replace('c = (c + b) % 997', 'c = open("x")'),
            source.replace('a * b + c', 'a ** b + c'),
            source.replace('a * b + c', 'a * b + i'),
            source.replace('a % 3 == 1', 'a % 4 == 1'),
            source.replace('a % 3 == 1', 'a % 3 == 3'),
            source.replace('% 997', '% 0', 1),
        )
        for variant in variants:
            with self.subTest(source=variant), patch('builtins.exec') as execute:
                with self.assertRaises(ValueError):
                    m.python_truth(variant)
                execute.assert_not_called()

    def test_bounds_apply_to_intermediates_before_modulo(self):
        with patch.object(m, 'MAX_MAGNITUDE', 2000), self.assertRaisesRegex(ValueError, 'magnitude'):
            m.python_truth(m.render_program(PARAMETERS, ('+', '+'), 4))

    def test_matched_prefix_and_loop_bound_static_proof(self):
        panel = synthetic_panel()
        self.assertEqual(len(panel['items']), 8)
        for template in panel['templates']:
            items = [item for item in panel['items'] if item['template_id'] == template['template_id']]
            low, high = [item['python_truth'] for item in items]
            self.assertEqual(len(high['loop_states']), 65)
            self.assertEqual(low['loop_states'], high['loop_states'][:5])
            self.assertEqual(high['worst_case_executed_statements'], 391)
            self.assertLessEqual(high['executed_statements'], 391)
            self.assertLessEqual(high['max_abs_intermediate'], 1_000_000)
            self.assertEqual(len(template['audit']['prefix_results']), 65)
            self.assertTrue(template['audit']['only_n_changes'])

    def test_cycle_reports_first_repeat_with_correct_entry_and_period(self):
        a, b, c = ({'a': n, 'b': 1, 'c': 2} for n in (1, 2, 3))
        self.assertIsNone(m.first_cycle([a, b, c]))
        self.assertEqual(m.first_cycle([a, b, c, b]), {'entry': 1, 'period': 2, 'repeat_at': 3})
        self.assertEqual(m.first_cycle([a, a]), {'entry': 0, 'period': 1, 'repeat_at': 1})


class SelectionAndDecisionTests(unittest.TestCase):
    def test_four_acceptances_stop_without_a_fifth_draw_or_audit_replacement(self):
        consumed = []
        def candidates():
            for candidate in synthetic_candidates():
                consumed.append(candidate['attempt'])
                yield candidate
            self.fail('attempted a fifth candidate after four accepted templates')
        # Audit failure is deliberately attached to every accepted template.
        with patch.object(m, 'audit_template', return_value={
                'same_final_state': True, 'first_cycle': None,
                'constant_prefix_answer': True, 'endpoint_answers_equal': True}):
            panel = m._assemble_panel(candidates(), OLD_HASHES, source_review())
        self.assertEqual(consumed, [0, 1, 2, 3])
        self.assertEqual(panel['generation']['attempt_count'], 4)
        self.assertEqual(panel['decision']['status'], 'parked')
        self.assertEqual(len(panel['templates']), 4)

    def test_repeated_structure_stops_at_32_without_consuming_33(self):
        consumed = []
        def candidates():
            for index in range(100):
                consumed.append(index)
                yield {'attempt': index, 'parameters': dict(PARAMETERS), 'operators': ['+', '+']}
        panel = m._assemble_panel(candidates(), OLD_HASHES)
        self.assertEqual(consumed, list(range(32)))
        self.assertEqual(len(panel['templates']), 1)
        self.assertEqual(panel['generation']['attempt_count'], 32)
        self.assertTrue(all(c['reason'] == 'duplicate_accepted_template'
                            for c in panel['generation']['candidates'][1:]))
        self.assertIn({'code': 'insufficient_distinct_templates'}, panel['decision']['park_reasons'])

    def test_old_template_identity_rejected_from_hash_only(self):
        source = m.render_program(PARAMETERS, ('+', '+'), 4)
        digest = m.sha256_bytes(m.normalized_template(source).encode())
        hashes = sorted(OLD_HASHES[:-1] + [digest])
        panel = m._assemble_panel(synthetic_candidates((('+', '+'),)), hashes)
        self.assertEqual(panel['generation']['candidates'][0]['reason'], 'previous_cycle_template')
        self.assertEqual(panel['items'], [])

    def decision_inputs(self):
        templates = [{'template_id': str(index), 'operators': list(ops),
                      'audit': {'same_final_state': False, 'first_cycle': None,
                                'constant_prefix_answer': True, 'endpoint_answers_equal': True}}
                     for index, ops in enumerate(m.OPERATOR_PAIRS)]
        items = [{'python_truth': {'answer': bool(i % 2)}} for i in range(8)]
        return templates, items

    def test_constant_prefix_and_equal_endpoint_answers_are_descriptive(self):
        templates, items = self.decision_inputs()
        result = m.panel_decision(templates, items, source_review())
        self.assertEqual(result['status'], 'consider_execution_freeze')
        self.assertEqual(result['park_reasons'], [])
        self.assertIs(result['empirical_launch_authorized'], False)
        self.assertEqual(m.panel_decision(templates, items)['status'], 'pending_source_review')

    def test_exact_explicit_parking_criteria(self):
        templates, items = self.decision_inputs()
        for item in items:
            item['python_truth']['answer'] = False
        templates[0]['audit']['same_final_state'] = True
        templates[1]['audit']['first_cycle'] = {'entry': 0, 'period': 1, 'repeat_at': 1}
        result = m.panel_decision(templates, items, source_review(irrelevant=True))
        codes = [reason['code'] for reason in result['park_reasons']]
        self.assertEqual(codes, ['all_eight_answers_equal', 'identical_final_triples',
                                'repeated_transition_state'] + ['demonstrated_bound_irrelevance'] * 4)
        self.assertEqual(result['status'], 'parked')

    def test_source_proof_and_previous_hash_boundary(self):
        review = source_review(irrelevant=True)
        review['reviews'][0]['proof'] = ''
        with self.assertRaisesRegex(ValueError, 'proof'):
            m.validate_source_review(review)
        export = {'schema_version': 1, 'source_fixture_sha256': 'f' * 64,
                  'template_hashes': OLD_HASHES}
        self.assertEqual(m.validate_old_hash_export(export), export)
        with self.assertRaises(ValueError):
            m.validate_old_hash_export({**export, 'reserved_sources': []})


class CustodyTests(unittest.TestCase):
    def test_missing_source_blocks_before_seed_enumeration(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m, '_source_hashes', side_effect=FileNotFoundError('checker')), \
                patch.object(m, 'build_panel') as build:
            with self.assertRaises(FileNotFoundError):
                m.prepare_fixture(Path(directory) / 'prepared', 'unused', 'unused')
            build.assert_not_called()

    def test_roundtrip_tamper_and_existing_directory_use_synthetic_panel_only(self):
        panel = synthetic_panel()
        source_hashes = {name: 'a' * 64 for name in m.SOURCE_FILES}
        checker = SimpleNamespace(verify_panel=lambda value: {'verified': value == panel})
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m, '_source_hashes', return_value=source_hashes), \
                patch.object(m, '_load_checker', return_value=checker), \
                patch.object(m, '_candidate_stream', side_effect=AssertionError('actual seed forbidden')), \
                patch.object(m, 'build_panel', return_value=panel) as build:
            base = Path(directory)
            old_path, review_path = base / 'old.json', base / 'review.json'
            old_path.write_text(json.dumps({'schema_version': 1, 'source_fixture_sha256': 'f' * 64,
                                           'template_hashes': OLD_HASHES}))
            review_path.write_text(json.dumps(source_review()))
            prepared = base / 'prepared'
            returned, manifest = m.prepare_fixture(prepared, old_path, review_path, ['synthetic-test'])
            self.assertEqual(returned, panel)
            digest = m.sha256_bytes((prepared / 'manifest.json').read_bytes())
            recovered, recovered_manifest = m.validate_fixture_custody(prepared, digest)
            self.assertEqual(recovered, panel)
            self.assertEqual(recovered_manifest, manifest)
            self.assertEqual(build.call_count, 1)
            with self.assertRaises(FileExistsError):
                m.prepare_fixture(prepared, old_path, review_path)
            self.assertEqual(build.call_count, 1)
            (prepared / 'cases.md').write_text('tampered\n')
            with self.assertRaisesRegex(ValueError, 'artifact hash'):
                m.validate_fixture_custody(prepared, digest)


if __name__ == '__main__':
    unittest.main()

