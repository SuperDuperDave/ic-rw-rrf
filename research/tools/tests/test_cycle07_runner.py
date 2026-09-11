"""Offline Boolean-answer collection and scoring boundaries; no provider calls."""

from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared = load('cycle07_shared_under_test', TOOLS / 'run_cycle05_coordinator.py')
with mock.patch.dict(sys.modules, {'run_cycle05_coordinator': shared}):
    telemetry = load('cycle07_telemetry_under_test', TOOLS / 'run_cycle05_replication.py')
    with mock.patch.dict(sys.modules, {'run_cycle05_replication': telemetry}):
        native = load('cycle07_native_under_test', TOOLS / 'native_stream_observer.py')
        with mock.patch.dict(sys.modules, {'native_stream_observer': native}):
            runner = load('cycle07_runner_under_test', TOOLS / 'run_cycle07_programs.py')
scorer = load('cycle07_scorer_under_test', TOOLS / 'score_cycle07_programs.py')
SESSION = 'synthetic-cycle07-session'


def events(terminal='{"answer":false}', session=SESSION, cost=.01):
    return [
        {'type': 'system', 'subtype': 'init', 'session_id': session,
         'model': shared.MODEL, 'tools': [], 'mcp_servers': [], 'plugins': [], 'skills': []},
        {'type': 'assistant', 'message': {'id': 'synthetic-message', 'model': shared.MODEL,
         'usage': {'input_tokens': 10, 'output_tokens': 20}, 'stop_reason': 'end_turn',
         'content': [{'type': 'text', 'text': '{"answer":true}'},
                     {'type': 'thinking', 'thinking': 'SYNTHETIC_PRIVATE_SENTINEL'}]}},
        {'type': 'result', 'subtype': 'success', 'is_error': False,
         'session_id': session, 'stop_reason': 'end_turn', 'result': terminal,
         'total_cost_usd': cost, 'num_turns': 1,
         'usage': {'input_tokens': 10, 'output_tokens': 20},
         'modelUsage': {shared.MODEL: {'canonicalModel': shared.MODEL,
                                     'provider': 'firstParty', 'outputTokens': 20}}}]


def encode(values):
    return ('\n'.join(json.dumps(value) for value in values) + '\n').encode()


class StreamTests(unittest.TestCase):
    def test_true_and_false_are_valid_without_legacy_probability_fields(self):
        for answer in (True, False):
            with self.subTest(answer=answer):
                record = runner.inspect_stream(encode(events(json.dumps({'answer': answer}))), 0, SESSION)
                self.assertTrue(record['native_acceptable'])
                self.assertIs(record['answer'], answer)
                self.assertIsNone(record['parse_failure'])
                self.assertNotIn('p_positive', record)
                self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL', json.dumps(record))

    def test_terminal_only_parse_never_salvages_earlier_answer_or_probability(self):
        for terminal in ('false', '{}', '{"answer":null}', '{"answer":0}',
                         '{"answer":"false"}', '{"answer":true,"answer":false}',
                         'Answer: {"answer":false}', '{"p_positive":0.625}'):
            with self.subTest(terminal=terminal):
                record = runner.inspect_stream(encode(events(terminal)), 0, SESSION)
                self.assertTrue(record['native_acceptable'])
                self.assertIsNone(record['answer'])
                self.assertIsNotNone(record['parse_failure'])
                self.assertNotIn('p_positive', record)

    def test_refusal_and_tool_gates_prevent_answer_parsing(self):
        for kind in ('refusal', 'tool'):
            values = events()
            if kind == 'refusal':
                values[-1].update(is_error=True, subtype='error_during_execution', stop_reason='refusal')
                values.insert(1, {'type': 'system', 'subtype': 'model_refusal_no_fallback',
                    'session_id': SESSION, 'request_id': 'synthetic-request',
                    'original_model': shared.MODEL, 'api_refusal_category': 'reasoning_extraction'})
                issue = 'provider_refusal'
            else:
                values[1]['message']['content'].append({'type': 'tool_use', 'name': 'Read'})
                issue = 'tool_activity'
            with self.subTest(kind=kind), mock.patch.object(runner.packets, 'parse_answer') as parse:
                record = runner.inspect_stream(encode(values), 0, SESSION)
                parse.assert_not_called()
                self.assertFalse(record['native_acceptable'])
                self.assertIsNone(record['answer'])
                self.assertIsNone(record['parse_failure'])
                self.assertIn(issue, record['issues'])


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen_fixture = runner.packets.build_fixture()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = deepcopy(self.frozen_fixture)
        self.source = self.root / 'synthetic-source.txt'
        self.source.write_text('immutable synthetic source')

    def collect(self, *, name='batch', terminals=None, costs=None, mutate_stream=None,
                changed_sources=False, expected_error=None, times=None):
        calls = []
        output = self.root / 'results' / name / 'observations'
        terminals = ['{"answer":false}'] * 16 if terminals is None else terminals
        costs = [.01] * 16 if costs is None else costs
        source_hashes = {self.source.name: shared.digest(self.source)}
        original_digest = runner.digest

        def invoke(argv, payload, environment, timeout, stdout, stderr):
            ordinal = len(calls)
            session = argv[argv.index('--session-id') + 1]
            calls.append({'argv': argv, 'payload': payload, 'environment': environment,
                          'timeout': timeout, 'session': session})
            values = events(terminals[ordinal], session, costs[ordinal])
            if mutate_stream:
                mutate_stream(ordinal, values)
            stdout.write_bytes(encode(values))
            stderr.write_bytes(b'')
            return {'exit_code': 0, 'timed_out': False, 'interrupted': False, 'wall_seconds': .01}

        def digest(path):
            return runner.BINARY_SHA if Path(path) == runner.BINARY else original_digest(path)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(runner, 'ROOT', self.root))
            stack.enter_context(mock.patch.object(runner, 'OUTPUT', output))
            stack.enter_context(mock.patch.object(runner, 'PREPARED', output.parent / 'prepared'))
            stack.enter_context(mock.patch.object(runner, 'PREPARED_SHA', 'synthetic-prepared-identity'))
            stack.enter_context(mock.patch.object(runner, 'sources', side_effect=[
                (self.fixture, source_hashes),
                (self.fixture, {} if changed_sources else source_hashes)]))
            stack.enter_context(mock.patch.object(runner, 'digest', side_effect=digest))
            stack.enter_context(mock.patch.object(runner, 'invoke', side_effect=invoke))
            stack.enter_context(mock.patch.object(runner, 'process_environment', return_value=
                runner.process_environment({'HOME': str(self.root), 'PATH': '/usr/bin'})))
            stack.enter_context(mock.patch.object(runner.subprocess, 'check_output', return_value='synthetic-head\n'))
            stack.enter_context(mock.patch.object(runner.time, 'monotonic',
                **({'return_value': 0} if times is None else {'side_effect': times})))
            stack.enter_context(redirect_stdout(io.StringIO()))
            if expected_error is None:
                manifest = runner.collect()
            else:
                with self.assertRaises(expected_error):
                    runner.collect()
                manifest = json.loads((output / 'manifest-invalid.json').read_text())
        records = json.loads((output / 'responses.json').read_text())
        return manifest, calls, records, output

    def score(self, output):
        with mock.patch.object(scorer, 'ROOT', self.root), \
                mock.patch.object(scorer, 'BASE', output.parent), \
                mock.patch.object(scorer, '__file__', str(self.source)), \
                mock.patch.object(scorer.packets, 'validate_fixture_custody', return_value=(self.fixture, {})), \
                redirect_stdout(io.StringIO()):
            scorer.score()
        return json.loads((output.parent / 'scored/scores.json').read_text())

    def test_full_development_order_accepts_false_and_uses_unchanged_native_helpers(self):
        for name in ('digest', 'write_json', 'now', 'process_environment', 'command', 'native_cost', 'invoke'):
            self.assertIs(getattr(runner, name), getattr(shared, name))
        for relative, expected in runner.PINNED.items():
            self.assertEqual(shared.digest(runner.ROOT / relative), expected)
        manifest, calls, records, output = self.collect()
        self.assertEqual((manifest['invocations_observed'], manifest['valid_predictions']), (16, 16))
        self.assertEqual(manifest['stop_reason'], 'all_invocations_finished')
        self.assertTrue(all(record['answer'] is False for record in records))
        self.assertEqual([record['packet_id'] for record in records], self.fixture['request_order'])
        by_id = {packet['packet_id']: packet for packet in self.fixture['packets']}
        items = {item['item_id']: item for item in self.fixture['items']}
        self.assertEqual([call['payload'] for call in calls],
                         [by_id[pid]['payload'].encode() for pid in self.fixture['request_order']])
        self.assertTrue(all(items[by_id[pid]['item_id']]['split'] == 'development'
                            for pid in self.fixture['request_order']))
        self.assertEqual(len({call['session'] for call in calls}), 16)
        self.assertEqual((manifest['native_budget_usd'], manifest['batch_wall_seconds'],
                          manifest['call_wall_seconds']), ('1', 300, 120))
        self.assertEqual([calls[index]['argv'][calls[index]['argv'].index('--max-budget-usd') + 1]
                          for index in (0, 1, 15)], ['1', '0.99', '0.85'])
        for call in calls:
            argv = call['argv']
            for flag, value in (('--model', 'claude-opus-5'), ('--effort', 'high'), ('--tools', ''),
                                ('--system-prompt', self.fixture['system_prompt'])):
                self.assertEqual(argv[argv.index(flag) + 1], value)
            self.assertEqual(call['environment']['CLAUDE_CODE_MAX_OUTPUT_TOKENS'], '500')
            self.assertEqual(call['timeout'], 120)
            self.assertNotIn('--resume', argv)
        result = self.score(output)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['coverage']['valid_pairs'], 8)
        self.assertEqual(result['coverage']['valid_answers'], 16)
        self.assertEqual(result['primary']['N'], 8)
        self.assertIsNone(result['partial_valid_pair_table'])

    def test_invalid_answer_stops_at_first_failure_with_valid_prefix_preserved(self):
        manifest, calls, records, output = self.collect(
            terminals=['{"answer":false}'] * 3 + ['bad JSON'])
        self.assertEqual(len(calls), 4)
        self.assertEqual((manifest['invocations_observed'], manifest['valid_predictions']), (4, 3))
        self.assertEqual(manifest['stop_reason'], 'invalid_answer')
        self.assertEqual([record['packet_id'] for record in records], self.fixture['request_order'][:4])
        self.assertIs(records[2]['answer'], False)
        self.assertIsNone(records[3]['answer'])
        self.assertTrue(records[3]['native_acceptable'])
        self.assertIsNotNone(records[3]['parse_failure'])
        result = self.score(output)
        self.assertEqual(result['status'], 'incomplete')
        self.assertIsNone(result['primary'])
        self.assertEqual(result['partial_valid_pair_table']['N'], 1)
        self.assertEqual(result['coverage'], {
            'planned_items': 8, 'planned_invocations': 16, 'valid_pairs': 1,
            'valid_answers': 3, 'invalid_answers': 1, 'unsent': 12, 'valid_unpaired_answers': 1})

    def test_native_failure_unknown_cost_and_resource_limits_stop_without_replacement(self):
        for name in ('native', 'unknown-cost', 'budget', 'wall'):
            def mutate(index, values):
                if index == 1 and name == 'native':
                    values[-1]['is_error'] = True
                if index == 1 and name == 'unknown-cost':
                    values[-1].pop('total_cost_usd')

            with self.subTest(name=name):
                manifest, calls, records, _ = self.collect(
                    name=name, costs=[.9, .2] if name == 'budget' else [.01, .02], mutate_stream=mutate,
                    times=[0, 0, 220, 300, 300] if name == 'wall' else None)
                self.assertEqual(len(calls), 2)
                self.assertEqual(manifest['valid_predictions'], 2 if name in ('budget', 'wall') else 1)
                self.assertEqual([r['packet_id'] for r in records], self.fixture['request_order'][:2])
                self.assertEqual(manifest['stop_reason'], {
                    'budget': 'native_budget_exhausted', 'wall': 'batch_wall_exhausted'}
                    .get(name, 'native_or_configuration_failure'))
                self.assertEqual(manifest['all_observed_costs_known'], name != 'unknown-cost')
                if name == 'budget':
                    self.assertEqual(manifest['known_native_cost_usd'], '1.1')
                if name == 'wall':
                    self.assertEqual([call['timeout'] for call in calls], [120, 80])

    def test_payload_and_end_source_mutations_preserve_invalid_receipts(self):
        manifest, calls, records, output = self.collect(changed_sources=True)
        self.assertEqual(manifest['status'], 'invalid')
        self.assertFalse(manifest['sources_unchanged'])
        self.assertEqual(len(calls), 16)
        self.assertTrue((output / 'manifest-invalid.json').exists())
        self.assertFalse((output / 'manifest.json').exists())
        first = next(p for p in self.fixture['packets'] if p['packet_id'] == self.fixture['request_order'][0])
        first['payload_sha256'] = '0' * 64
        manifest, calls, records, _ = self.collect(name='payload-mutation', expected_error=ValueError)
        self.assertEqual(calls, [])
        self.assertEqual(records, [])
        self.assertEqual(manifest['stop_reason'], 'collection_exception')
        self.assertEqual(manifest['invocations_scheduled'], 0)

    def test_preflight_rejects_reserve_order_and_changed_shared_sources_before_invoke(self):
        for name in ('reserve', 'order-count', 'shared-source'):
            fixture = deepcopy(self.fixture)
            if name == 'reserve':
                first = fixture['packets'][0]
                next(item for item in fixture['items'] if item['item_id'] == first['item_id'])['split'] = 'reserved'
            elif name == 'order-count':
                fixture['request_order'].pop()
            with self.subTest(name=name), \
                    mock.patch.object(runner.packets, 'validate_fixture_custody',
                                      return_value=(fixture, {'source_sha256_start': {}})), \
                    mock.patch.object(runner, 'digest', return_value='changed-identity'), \
                    mock.patch.object(runner, 'invoke') as invoke:
                with self.assertRaisesRegex(ValueError, 'reserve item|sixteen unique|implementation changed'):
                    runner.collect()
                invoke.assert_not_called()

    def test_existing_output_refuses_before_invoke(self):
        output = self.root / 'already-exists'
        output.mkdir()
        with mock.patch.object(runner, 'OUTPUT', output), \
                mock.patch.object(runner, 'sources', return_value=(self.fixture, {})), \
                mock.patch.object(runner, 'process_environment', return_value={}), \
                mock.patch.object(runner, 'digest', return_value=runner.BINARY_SHA), \
                mock.patch.object(runner, 'invoke') as invoke:
            with self.assertRaises(FileExistsError):
                runner.collect()
            invoke.assert_not_called()

    def test_scorer_rejects_changed_sources_outputs_and_nonprefix_records(self):
        for name in ('source', 'output', 'prefix', 'continued-after-invalid'):
            manifest, _, records, output = self.collect(name=name, terminals=['bad JSON'])
            if name == 'source':
                manifest['source_sha256_end'] = {}
            elif name == 'output':
                (output / 'responses.json').write_text('[]')
            elif name == 'prefix':
                records[0]['packet_id'] = self.fixture['request_order'][1]
                (output / 'responses.json').write_text(json.dumps(records))
                manifest['output_sha256']['responses.json'] = shared.digest(output / 'responses.json')
            else:
                # A self-consistent second receipt cannot authorize continuing
                # after the first invalid terminal output.
                record = deepcopy(records[0])
                record['ordinal'] = 2
                record['packet_id'] = self.fixture['request_order'][1]
                packet = next(p for p in self.fixture['packets'] if p['packet_id'] == record['packet_id'])
                record.update(payload_sha256=packet['payload_sha256'], answer=False, parse_failure=None)
                records.append(record)
                individual = output / ('02-' + record['packet_id'] + '.json')
                individual.write_text(json.dumps(record))
                (output / 'responses.json').write_text(json.dumps(records))
                manifest.update(invocations_observed=2, invocations_scheduled=2)
                manifest['output_sha256'].update({p.name: shared.digest(p) for p in (individual, output / 'responses.json')})
            (output / 'manifest.json').write_text(json.dumps(manifest))
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.score(output)
            self.assertFalse((output.parent / 'scored').exists())


if __name__ == '__main__':
    unittest.main()
