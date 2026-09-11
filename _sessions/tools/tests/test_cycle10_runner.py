"""Cycle10 native adaptation checks using an explicit synthetic panel only."""

from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parents[1]

# The frozen predecessor supplies only fake native streams and temporary-file
# harnesses. Its setUpClass/build_fixture methods are never called here.
import importlib.util
spec = importlib.util.spec_from_file_location('cycle10_test_helpers', TOOLS / 'tests/test_cycle09_runner.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
with mock.patch.dict(sys.modules, {'run_cycle05_coordinator': prior.shared, 'native_stream_observer': prior.native}):
    runner = prior.load('cycle10_runner_under_test', TOOLS / 'run_cycle10_verifier.py')
scorer = prior.load('cycle10_scorer_under_test', TOOLS / 'score_cycle10_verifier.py')
from evaluation import cycle09_verifier as frozen_measure


class Cycle10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(runner.packets, 'build_fixture', side_effect=AssertionError('actual panel forbidden')) as actual, \
                mock.patch.object(runner.packets.previous.random, 'Random', side_effect=AssertionError('RNG forbidden')) as draw:
            cls.local_fixture = runner.packets.construct_fixture(-3, 4)
            actual.assert_not_called()
            draw.assert_not_called()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'synthetic-source.txt'
        self.source.write_text('immutable synthetic source')
        self.fixture = deepcopy(self.local_fixture)
        self.fixture.update(system_prompt=runner.measure.SYSTEM_PROMPT,
            system_prompt_sha256=hashlib.sha256(runner.measure.SYSTEM_PROMPT.encode()).hexdigest(),
            prepared_manifest_sha256='synthetic-prepared')
        self.packets = {packet['packet_id']: packet for packet in self.fixture['packets']}
        self.ids = {pid: json.loads(self.packets[pid]['payload'])['original_ids'] for pid in runner.measure.ORDER}
        self.false_maps = {pid: {rid: False for rid in ids} for pid, ids in self.ids.items()}

    def collect(self, **options):
        options.setdefault('terminals', [json.dumps(self.false_maps[pid]) for pid in runner.measure.ORDER])
        options.setdefault('costs', [.01] * 6)
        with mock.patch.object(prior, 'runner', runner):
            return prior.CollectionTests.collect(self, **options)

    def score(self, output):
        with mock.patch.object(prior, 'scorer', scorer):
            return prior.CollectionTests.score(self, output)

    @contextmanager
    def execution_context(self):
        with mock.patch.object(prior, 'runner', runner):
            with prior.CollectionTests.execution_context(self) as execution:
                yield execution

    def test_frozen_strict_parser_is_reused_including_giant_number_failure(self):
        self.assertIs(runner.measure.parse_validity, frozen_measure.parse_validity)
        self.assertIs(runner.measure.MapParseError, frozen_measure.MapParseError)
        self.assertEqual(runner.measure.SYSTEM_PROMPT, frozen_measure.SYSTEM_PROMPT)
        ids = self.ids[runner.measure.ORDER[0]]
        valid = json.dumps(self.false_maps[runner.measure.ORDER[0]])
        invalid = [valid[:-1] + ',' + json.dumps(ids[0]) + ':true}',
                   json.dumps({ids[0]: False, ids[1]: False}),
                   json.dumps({ids[0]: 0, ids[1]: False, ids[2]: False}),
                   '{' + json.dumps(ids[0]) + ':' + '1' * 5000 + ','
                   + json.dumps(ids[1]) + ':false,' + json.dumps(ids[2]) + ':false}']
        for terminal in [valid] + invalid:
            values = prior.events(terminal)
            values[1]['message']['content'][0]['text'] = valid
            record = runner.inspect_stream(prior.encode(values), 0, prior.SESSION, ids)
            self.assertTrue(record['native_acceptable'])
            if terminal == valid:
                self.assertEqual(record['validity'], self.false_maps[runner.measure.ORDER[0]])
                self.assertIsNone(record['parse_failure'])
            else:
                self.assertIsNone(record['validity'])
                self.assertIsNotNone(record['parse_failure'])
            self.assertNotIn('p_positive', record)
            self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL', json.dumps(record))

    def test_six_calls_in_exact_order_accept_all_false_with_twelve_correct(self):
        self.assertEqual(list(runner.measure.ORDER), ['R0-P1', 'R1-P2', 'R0-P3', 'R1-P1', 'R0-P2', 'R1-P3'])
        manifest, calls, records, output = self.collect()
        self.assertEqual((len(calls), manifest['valid_predictions']), (6, 6))
        self.assertEqual([row['packet_id'] for row in records], list(runner.measure.ORDER))
        self.assertEqual([call['payload'] for call in calls],
                         [self.packets[pid]['payload'].encode() for pid in runner.measure.ORDER])
        self.assertTrue(all(all(value is False for value in row['validity'].values()) for row in records))
        self.assertEqual(len({call['session'] for call in calls}), 6)
        self.assertEqual([call['argv'][call['argv'].index('--max-budget-usd') + 1] for call in calls],
                         ['1', '0.99', '0.98', '0.97', '0.96', '0.95'])
        self.assertEqual((manifest['native_budget_usd'], manifest['call_wall_seconds'], manifest['batch_wall_seconds']),
                         ('1', 120, 300))
        self.assertTrue(all(call['timeout'] == 120 and call['environment']['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] == '500'
                            for call in calls))
        result = self.score(output)
        self.assertEqual(result['observed_counts'], {'correct': 12, 'accepted': 18, 'planned': 18})
        self.assertEqual(result['invocations'], {'accepted': 6, 'invalid': 0, 'unsent': 0, 'planned': 6})
        self.assertEqual(result['full_primary']['counts'], result['observed_counts'])
        mismatches = {'exact_checker': 6, 'always_valid': 18, 'always_invalid': 0,
                      'position_1': 6, 'position_2': 6, 'position_3': 6,
                      'endpoint_matches_truth': 12, 'endpoint_boolean': 9}
        self.assertEqual({name: row['mismatches'] for name, row in result['policy_comparisons'].items()}, mismatches)
        for name, row in result['policy_comparisons'].items():
            self.assertEqual(row['compared'], 18)
            self.assertEqual(row['matches_full_vector'], name == 'always_invalid')

    def test_exact_vector_comparisons_and_root_type_position_groups(self):
        predictions = {pid: self.fixture['reference_policies'][pid]['exact_checker']['decisions']
                       for pid in runner.measure.ORDER}
        result = runner.measure.score_decisions(self.fixture, predictions, {})
        correct = {'exact_checker': 18, 'always_valid': 6, 'always_invalid': 12,
                   'position_1': 10, 'position_2': 10, 'position_3': 10,
                   'endpoint_matches_truth': 12, 'endpoint_boolean': 9}
        self.assertEqual(result['observed_counts']['correct'], 18)
        for name, row in result['policy_comparisons'].items():
            self.assertEqual(row['mismatches'], 18 - correct[name])
            self.assertEqual(row['matches_full_vector'], name == 'exact_checker')
        self.assertEqual(len(result['by_root_position']), 6)
        for rows in result['by_root_position'].values():
            self.assertEqual(len(rows), 3)
            self.assertEqual({row['position'] for row in rows}, {1, 2, 3})
            self.assertEqual(len({row['program_id'] for row in rows}), 1)
            self.assertEqual(len({row['private_type'] for row in rows}), 1)
        for rows in result['by_type_endpoint'].values():
            self.assertEqual(len(rows), 6)
            self.assertEqual(Counter(row['position'] for row in rows), {1: 2, 2: 2, 3: 2})
            self.assertEqual(Counter(row['program_id'] for row in rows), {'R0': 3, 'R1': 3})

    def test_partial_prefix_keeps_eighteen_rows_and_full_vector_claims_null(self):
        terminals = [json.dumps(self.false_maps[pid]) for pid in runner.measure.ORDER[:2]] + ['bad JSON']
        manifest, calls, records, output = self.collect(terminals=terminals)
        self.assertEqual((len(calls), manifest['valid_predictions']), (3, 2))
        self.assertEqual(manifest['stop_reason'], 'invalid_answer')
        self.assertEqual([row['packet_id'] for row in records], list(runner.measure.ORDER[:3]))
        result = self.score(output)
        self.assertIsNone(result['full_primary'])
        self.assertEqual(result['observed_counts'], {'correct': 4, 'accepted': 6, 'planned': 18})
        self.assertEqual([row['status'] for row in result['decisions']], ['accepted'] * 6 + ['invalid'] * 3 + ['unsent'] * 9)
        self.assertTrue(all(row['correct'] is None for row in result['decisions'][6:]))
        self.assertTrue(all(row['matches_full_vector'] is None and row['compared'] == 6
                            for row in result['policy_comparisons'].values()))
        self.assertEqual(result['policy_comparisons']['always_invalid']['mismatches'], 0)

    def test_first_native_format_or_resource_failure_stops_without_replacement(self):
        for name in ('native', 'timeout', 'unknown-cost', 'format', 'budget', 'wall'):
            options = {'name': name}
            if name in ('native', 'timeout', 'unknown-cost'):
                options['failure'] = name
            elif name == 'format':
                options['terminals'] = ['bad JSON']
            elif name == 'budget':
                options['costs'] = [1.1]
            else:
                options['times'] = [0, 0, 300, 300]
            with self.subTest(name=name):
                manifest, calls, _, output = self.collect(**options)
                self.assertEqual(len(calls), 1)
                accepted = 1 if name in ('budget', 'wall') else 0
                self.assertEqual(manifest['valid_predictions'], accepted)
                self.assertEqual(manifest['all_observed_costs_known'], name != 'unknown-cost')
                result = self.score(output)
                self.assertIsNone(result['full_primary'])
                self.assertEqual(len(result['decisions']), 18)
                self.assertEqual(result['invocations']['unsent'], 5)
        manifest, calls, _, _ = self.collect(name='remaining', times=[0, 0, 220, 300, 300])
        self.assertEqual([call['timeout'] for call in calls], [120, 80])
        self.assertEqual(manifest['stop_reason'], 'batch_wall_exhausted')

    def test_changed_collection_sources_are_invalid_and_seals_reject_extra_requests(self):
        manifest, _, _, output = self.collect(changed_sources=True)
        self.assertEqual(manifest['status'], 'invalid')
        self.assertFalse(manifest['sources_unchanged'])
        self.assertTrue((output / 'manifest-invalid.json').exists())
        self.assertFalse((output / 'manifest.json').exists())
        with self.execution_context() as execution:
            identity = runner.prepare_execution('synthetic-prepared')
            fixture, _ = runner.sources(identity)
            self.assertEqual(fixture['request_order'], list(runner.measure.ORDER))
            self.assertEqual({path.name for path in execution.iterdir()},
                             {'system-prompt.txt', 'manifest.json'} | {pid + '.json' for pid in runner.measure.ORDER})
            seal = json.loads((execution / 'manifest.json').read_text())
            seal['request_order'].append('seventh-request')
            (execution / 'manifest.json').write_text(json.dumps(seal))
            identity = prior.shared.digest(execution / 'manifest.json')
            with mock.patch.object(runner, 'invoke') as invoke, self.assertRaises(ValueError):
                runner.collect(identity)
            invoke.assert_not_called()

    def test_reused_strict_parser_source_is_pinned(self):
        self.assertIn('evaluation/cycle09_verifier.py', runner.PINNED)
        for relative, expected in runner.PINNED.items():
            self.assertEqual(prior.shared.digest(runner.ROOT / relative), expected)
        with mock.patch.object(runner, 'digest', return_value='changed-source'):
            with self.assertRaisesRegex(ValueError, 'preserved native implementation changed'):
                runner.current_sources({'source_sha256_start': {}})

    def test_grouping_rejects_malformed_types_and_conflicting_root_labels(self):
        for name in ('duplicate-type', 'conflicting-root', 'wrong-program'):
            fixture = deepcopy(self.fixture)
            order = fixture['packets'][0]['private_order']
            if name == 'duplicate-type':
                order[1] = order[0]
            elif name == 'conflicting-root':
                order[1], order[2] = order[2], order[1]
            else:
                fixture['packets'][0]['program_id'] = 'R1'
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner.measure.score_decisions(fixture, {}, {})

    def test_scorer_rejects_illegal_continuation_and_nonprefix_records(self):
        for name in ('continued-after-invalid', 'prefix'):
            manifest, _, records, output = self.collect(name=name)
            if name == 'continued-after-invalid':
                records[0].update(validity=None, parse_failure='invalid_json')
                individual = output / ('01-' + records[0]['packet_id'] + '.json')
                individual.write_text(json.dumps(records[0]))
                manifest['output_sha256'][individual.name] = prior.shared.digest(individual)
            else:
                records[0], records[1] = records[1], records[0]
            (output / 'responses.json').write_text(json.dumps(records))
            manifest['output_sha256']['responses.json'] = prior.shared.digest(output / 'responses.json')
            (output / 'manifest.json').write_text(json.dumps(manifest))
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.score(output)
            self.assertFalse((output.parent / 'scored').exists())


if __name__ == '__main__':
    unittest.main()
