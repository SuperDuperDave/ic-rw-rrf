"""Synthetic cycle09 native/scoring checks; no research RNG draws or providers."""

from contextlib import ExitStack, contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
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


shared = load('cycle09_shared_under_test', TOOLS / 'run_cycle05_coordinator.py')
with mock.patch.dict(sys.modules, {'run_cycle05_coordinator': shared}):
    telemetry = load('cycle09_telemetry_under_test', TOOLS / 'run_cycle05_replication.py')
    with mock.patch.dict(sys.modules, {'run_cycle05_replication': telemetry}):
        native = load('cycle09_native_under_test', TOOLS / 'native_stream_observer.py')
        with mock.patch.dict(sys.modules, {'native_stream_observer': native}):
            runner = load('cycle09_runner_under_test', TOOLS / 'run_cycle09_verifier.py')
scorer = load('cycle09_scorer_under_test', TOOLS / 'score_cycle09_verifier.py')
SESSION = 'synthetic-cycle09-session'
IDS = ['r_' + format(index, '016x') for index in range(1, 6)]
FALSE_MAP = {rid: False for rid in IDS[:3]}


def events(terminal=None, session=SESSION, cost=.01):
    return [
        {'type': 'system', 'subtype': 'init', 'session_id': session,
         'model': shared.MODEL, 'tools': [], 'mcp_servers': [], 'plugins': [], 'skills': []},
        {'type': 'assistant', 'message': {'id': 'synthetic-message', 'model': shared.MODEL,
         'usage': {'input_tokens': 10, 'output_tokens': 20}, 'stop_reason': 'end_turn',
         'content': [{'type': 'text', 'text': json.dumps(FALSE_MAP)},
                     {'type': 'thinking', 'thinking': 'SYNTHETIC_PRIVATE_SENTINEL'}]}},
        {'type': 'result', 'subtype': 'success', 'is_error': False,
         'session_id': session, 'stop_reason': 'end_turn',
         'result': json.dumps(FALSE_MAP) if terminal is None else terminal,
         'total_cost_usd': cost, 'num_turns': 1,
         'usage': {'input_tokens': 10, 'output_tokens': 20},
         'modelUsage': {shared.MODEL: {'canonicalModel': shared.MODEL,
                                     'provider': 'firstParty', 'outputTokens': 20}}}]


def encode(values):
    return ('\n'.join(json.dumps(value) for value in values) + '\n').encode()


class StreamTests(unittest.TestCase):
    def test_oversized_integer_remains_a_format_failure(self):
        limit = sys.get_int_max_str_digits()
        if not limit:
            self.skipTest('Python integer decoder limit is disabled')
        terminal = json.dumps(FALSE_MAP).replace('false', '9' * (limit + 1), 1)
        record = runner.inspect_stream(encode(events(terminal)), 0, SESSION, IDS[:3])
        self.assertTrue(record['native_acceptable'])
        self.assertIsNone(record['validity'])
        self.assertEqual(record['parse_failure'], 'invalid_json')

    def test_exact_id_maps_accept_false_and_key_order_without_exposing_thoughts(self):
        for values in (FALSE_MAP, {rid: index == 1 for index, rid in enumerate(reversed(IDS[:3]))}):
            text = ' \n' + json.dumps(values) + '\t '
            record = runner.inspect_stream(encode(events(text)), 0, SESSION, IDS[:3])
            self.assertTrue(record['native_acceptable'])
            self.assertEqual(record['validity'], values)
            self.assertTrue(all(type(value) is bool for value in record['validity'].values()))
            self.assertIsNone(record['parse_failure'])
            for excluded in ('answer', 'p_positive'):
                self.assertNotIn(excluded, record)
            self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL', json.dumps(record))

    def test_terminal_only_strict_map_discards_every_entry_on_one_format_error(self):
        invalid = [
            json.dumps({rid: False for rid in IDS[:2]}),
            json.dumps(dict(FALSE_MAP, **{IDS[3]: False})),
            json.dumps({IDS[0].upper(): False, IDS[1]: False, IDS[2]: False}),
            json.dumps(FALSE_MAP)[:-1] + ',' + json.dumps(IDS[0]) + ':true}',
            '{}', '[]', 'false', 'null',
            '```json\n' + json.dumps(FALSE_MAP) + '\n```',
            'Answer: ' + json.dumps(FALSE_MAP),
            json.dumps(FALSE_MAP) + json.dumps(FALSE_MAP),
        ]
        invalid.extend(json.dumps(dict(FALSE_MAP, **{IDS[0]: value}))
                       for value in (None, 0, 1, 'false', [], {}))
        invalid.append(json.dumps(FALSE_MAP).replace('false', 'NaN', 1))
        for terminal in invalid:
            with self.subTest(terminal=terminal):
                record = runner.inspect_stream(encode(events(terminal)), 0, SESSION, IDS[:3])
                self.assertTrue(record['native_acceptable'])
                self.assertIsNone(record['validity'])
                self.assertIsNotNone(record['parse_failure'])

    def test_native_refusal_activity_and_timeout_gate_all_map_parsing(self):
        for name in ('refusal', 'tool', 'timeout'):
            values = events()
            if name == 'refusal':
                values[-1].update(is_error=True, subtype='error_during_execution', stop_reason='refusal')
                values.insert(1, {'type': 'system', 'subtype': 'model_refusal_no_fallback',
                    'session_id': SESSION, 'request_id': 'synthetic-request',
                    'original_model': shared.MODEL, 'api_refusal_category': 'reasoning_extraction'})
            elif name == 'tool':
                values[1]['message']['content'].append({'type': 'tool_use', 'name': 'Read'})
            with self.subTest(name=name), mock.patch.object(runner.measure, 'parse_validity') as parse:
                record = runner.inspect_stream(encode(values), 0, SESSION, IDS[:3], name == 'timeout')
                parse.assert_not_called()
                self.assertFalse(record['native_acceptable'])
                self.assertIsNone(record['validity'])
                self.assertIsNone(record['parse_failure'])
                self.assertIn({'refusal': 'provider_refusal', 'tool': 'tool_activity', 'timeout': 'timeout'}[name],
                              record['issues'])


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Explicit test values only: neither prescribed research RNG is run.
        with mock.patch.object(runner.packets.random, 'Random', side_effect=AssertionError('unexpected RNG draw')) as draw:
            cls.local_fixture = runner.packets.construct_fixture(
                {'A': 2, 'B': -3, 'R': 1}, ['I', 'V', 'F'], list(IDS))
            draw.assert_not_called()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = deepcopy(self.local_fixture)
        self.fixture.update(system_prompt=runner.measure.SYSTEM_PROMPT,
            system_prompt_sha256=hashlib.sha256(runner.measure.SYSTEM_PROMPT.encode()).hexdigest(),
            request_order=['base', 'repeat'], prepared_manifest_sha256='synthetic-prepared')
        self.source = self.root / 'synthetic-source.txt'
        self.source.write_text('immutable synthetic source')

    def collect(self, *, name='batch', terminals=None, costs=None, failure=None,
                changed_sources=False, times=None, expected_error=None):
        calls = []
        output = self.root / 'results' / name / 'observations'
        terminals = [json.dumps(FALSE_MAP)] * 2 if terminals is None else terminals
        costs = [.01, .02] if costs is None else costs
        identities = {self.source.name: shared.digest(self.source)}
        original_digest = runner.digest

        def invoke(argv, payload, environment, timeout, stdout, stderr):
            index = len(calls)
            session = argv[argv.index('--session-id') + 1]
            calls.append({'argv': argv, 'payload': payload, 'environment': environment,
                          'timeout': timeout, 'session': session})
            values = events(terminals[index], session, costs[index])
            if failure == 'native':
                values[-1]['is_error'] = True
            elif failure == 'unknown-cost':
                values[-1].pop('total_cost_usd')
            stdout.write_bytes(encode(values))
            stderr.write_bytes(b'')
            return {'exit_code': 0, 'timed_out': failure == 'timeout',
                    'interrupted': False, 'wall_seconds': .01}

        def digest(path):
            return runner.BINARY_SHA if Path(path) == runner.BINARY else original_digest(path)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(runner, 'ROOT', self.root))
            stack.enter_context(mock.patch.object(runner, 'OUTPUT', output))
            stack.enter_context(mock.patch.object(runner, 'sources', side_effect=[
                (self.fixture, identities), (self.fixture, {} if changed_sources else identities)]))
            stack.enter_context(mock.patch.object(runner, 'digest', side_effect=digest))
            stack.enter_context(mock.patch.object(runner, 'invoke', side_effect=invoke))
            stack.enter_context(mock.patch.object(runner, 'process_environment', return_value=
                runner.process_environment({'HOME': str(self.root), 'PATH': '/usr/bin'})))
            stack.enter_context(mock.patch.object(runner.subprocess, 'check_output', return_value='synthetic-head\n'))
            stack.enter_context(mock.patch.object(runner.time, 'monotonic',
                **({'return_value': 0} if times is None else {'side_effect': times})))
            stack.enter_context(redirect_stdout(io.StringIO()))
            if expected_error is None:
                manifest = runner.collect('synthetic-execution')
            else:
                with self.assertRaises(expected_error):
                    runner.collect('synthetic-execution')
                manifest = json.loads((output / 'manifest-invalid.json').read_text())
        return manifest, calls, json.loads((output / 'responses.json').read_text()), output

    def score(self, output):
        with mock.patch.object(scorer, 'ROOT', self.root), \
                mock.patch.object(scorer, 'BASE', output.parent), \
                mock.patch.object(scorer, '__file__', str(self.source)), \
                mock.patch.object(scorer.packets, 'validate_fixture_custody', return_value=(self.fixture, {})), \
                redirect_stdout(io.StringIO()):
            return scorer.score()

    def test_two_calls_preserve_false_maps_exact_payloads_and_native_controls(self):
        for name in ('command', 'process_environment', 'invoke', 'native_cost'):
            self.assertIs(getattr(runner, name), getattr(shared, name))
        for relative, expected in runner.PINNED.items():
            self.assertEqual(shared.digest(runner.ROOT / relative), expected)
        manifest, calls, records, output = self.collect()
        self.assertEqual((len(calls), manifest['valid_predictions']), (2, 2))
        self.assertEqual([r['packet_id'] for r in records], ['base', 'repeat'])
        self.assertEqual([r['validity'] for r in records], [FALSE_MAP, FALSE_MAP])
        self.assertEqual([c['payload'] for c in calls], [p['payload'].encode() for p in self.fixture['packets']])
        self.assertEqual(len({c['session'] for c in calls}), 2)
        self.assertEqual((manifest['native_budget_usd'], manifest['call_wall_seconds'],
                          manifest['batch_wall_seconds']), ('1', 120, 300))
        self.assertEqual([c['argv'][c['argv'].index('--max-budget-usd') + 1] for c in calls], ['1', '0.99'])
        for call in calls:
            argv = call['argv']
            for key, value in (('--model', 'claude-opus-5'), ('--effort', 'high'), ('--tools', ''),
                               ('--system-prompt', runner.measure.SYSTEM_PROMPT)):
                self.assertEqual(argv[argv.index(key) + 1], value)
            self.assertEqual(call['environment']['CLAUDE_CODE_MAX_OUTPUT_TOKENS'], '500')
            self.assertEqual(call['timeout'], 120)
            self.assertNotIn('--resume', argv)
        result = self.score(output)
        self.assertEqual(result['observed_counts'], {'correct': 4, 'accepted': 6, 'planned': 6})
        self.assertEqual(result['full_primary']['counts'], result['observed_counts'])
        self.assertEqual(len(result['full_primary']['transitions']), 3)
        self.assertTrue(all(row['base_validity'] is False and row['repeat_validity'] is False
                            for row in result['full_primary']['transitions']))
        self.assertEqual(result['invocations'], {'accepted': 2, 'invalid': 0, 'unsent': 0, 'planned': 2})

    def test_first_failure_stops_without_retry_and_keeps_invalid_and_unsent_rows(self):
        for name in ('format', 'native', 'unknown-cost', 'timeout'):
            with self.subTest(name=name):
                manifest, calls, records, output = self.collect(name=name,
                    terminals=['bad JSON'] if name == 'format' else None,
                    failure=None if name == 'format' else name)
                self.assertEqual((len(calls), manifest['valid_predictions']), (1, 0))
                self.assertIsNone(records[0]['validity'])
                self.assertEqual(manifest['stop_reason'], 'invalid_answer' if name == 'format'
                                 else 'native_or_configuration_failure')
                self.assertEqual(manifest['all_observed_costs_known'], name != 'unknown-cost')
                result = self.score(output)
                self.assertIsNone(result['full_primary'])
                self.assertEqual(result['observed_counts'], {'correct': 0, 'accepted': 0, 'planned': 6})
                self.assertEqual([r['status'] for r in result['decisions']], ['invalid'] * 3 + ['unsent'] * 3)
                self.assertTrue(all(r['correct'] is None and r['returned_validity'] is None for r in result['decisions']))

    def test_partial_map_failure_discards_all_repeat_bits_but_preserves_base_counts(self):
        malformed = json.dumps(dict(FALSE_MAP, **{IDS[1]: 0}))
        manifest, calls, _, output = self.collect(terminals=[json.dumps(FALSE_MAP), malformed])
        self.assertEqual((len(calls), manifest['valid_predictions']), (2, 1))
        result = self.score(output)
        self.assertIsNone(result['full_primary'])
        self.assertEqual(result['observed_counts'], {'correct': 2, 'accepted': 3, 'planned': 6})
        self.assertEqual(result['per_packet']['base'], {'correct': 2, 'accepted': 3, 'planned': 3, 'status': 'accepted'})
        self.assertEqual(result['per_packet']['repeat'], {'correct': 0, 'accepted': 0, 'planned': 3, 'status': 'invalid'})
        self.assertEqual([r['status'] for r in result['decisions']], ['accepted'] * 3 + ['invalid'] * 3)
        self.assertTrue(all(r['correct'] is None for r in result['decisions'][3:]))

    def test_budget_and_remaining_deadline_stop_or_bound_second_call(self):
        for name, costs, times, count, reason in (
                ('budget', [1.1], None, 1, 'native_budget_exhausted'),
                ('wall', [.01], [0, 0, 300, 300], 1, 'batch_wall_exhausted'),
                ('remaining-time', [.01, .02], [0, 0, 220, 230], 2, 'all_invocations_finished')):
            with self.subTest(name=name):
                manifest, calls, _, output = self.collect(name=name, costs=costs, times=times)
                self.assertEqual(len(calls), count)
                self.assertEqual(manifest['stop_reason'], reason)
                if name == 'remaining-time':
                    self.assertEqual([c['timeout'] for c in calls], [120, 80])
                else:
                    result = self.score(output)
                    self.assertIsNone(result['full_primary'])
                    self.assertEqual(result['observed_counts'], {'correct': 2, 'accepted': 3, 'planned': 6})
                    self.assertEqual(result['invocations']['unsent'], 1)
                if name == 'budget':
                    self.assertEqual(manifest['known_native_cost_usd'], '1.1')

    def test_changed_source_or_payload_preserves_invalid_collection_receipts(self):
        manifest, _, _, output = self.collect(changed_sources=True)
        self.assertEqual(manifest['status'], 'invalid')
        self.assertFalse(manifest['sources_unchanged'])
        self.assertTrue((output / 'manifest-invalid.json').exists())
        self.assertFalse((output / 'manifest.json').exists())
        self.fixture['packets'][0]['payload_sha256'] = '0' * 64
        manifest, calls, records, _ = self.collect(name='changed-payload', expected_error=ValueError)
        self.assertEqual((calls, records), ([], []))
        self.assertEqual(manifest['stop_reason'], 'collection_exception')
        self.assertEqual(manifest['invocations_scheduled'], 0)

    @contextmanager
    def execution_context(self):
        execution = self.root / 'results/sealed/execution'
        decision = self.root / runner.DECISION
        decision.parent.mkdir(parents=True, exist_ok=True)
        decision.write_text(json.dumps({'proceed': True, 'prepared_manifest_sha256': 'synthetic-prepared'}))
        original_digest = runner.digest
        with ExitStack() as stack:
            for name, value in (('ROOT', self.root), ('EXECUTION', execution),
                                ('PREPARED', execution.parent / 'prepared'), ('OUTPUT', execution.parent / 'observations')):
                stack.enter_context(mock.patch.object(runner, name, value))
            stack.enter_context(mock.patch.object(runner.packets, 'validate_fixture_custody',
                side_effect=lambda *_args: (deepcopy(self.local_fixture), {'source_sha256_start': {}})))
            stack.enter_context(mock.patch.object(runner, 'current_sources',
                return_value={self.source.name: shared.digest(self.source)}))
            stack.enter_context(mock.patch.object(runner, 'process_environment', return_value={}))
            stack.enter_context(mock.patch.object(runner, 'digest', side_effect=lambda path:
                runner.BINARY_SHA if Path(path) == runner.BINARY else original_digest(path)))
            yield execution

    def test_real_execution_seal_checks_bytes_order_controls_and_exclusive_output(self):
        with self.execution_context() as execution:
            identity = runner.prepare_execution('synthetic-prepared')
            fixture, _ = runner.sources(identity)
            self.assertEqual(fixture['request_order'], ['base', 'repeat'])
            for packet in self.local_fixture['packets']:
                self.assertEqual((execution / (packet['packet_id'] + '.json')).read_bytes(), packet['payload'].encode())
            with self.assertRaises(FileExistsError):
                runner.prepare_execution('synthetic-prepared')
            seal_bytes = (execution / 'manifest.json').read_bytes()
            base_bytes = (execution / 'base.json').read_bytes()
            for name in ('manifest', 'payload', 'order', 'control'):
                expected = identity
                if name == 'manifest':
                    expected = '0' * 64
                elif name == 'payload':
                    (execution / 'base.json').write_bytes(base_bytes + b' ')
                else:
                    seal = json.loads(seal_bytes)
                    seal['request_order' if name == 'order' else 'native_budget_usd'] = (
                        ['base', 'repeat', 'third'] if name == 'order' else '2')
                    (execution / 'manifest.json').write_text(json.dumps(seal))
                    expected = shared.digest(execution / 'manifest.json')
                with self.subTest(name=name), mock.patch.object(runner, 'invoke') as invoke:
                    with self.assertRaises(ValueError):
                        runner.collect(expected)
                    invoke.assert_not_called()
                (execution / 'manifest.json').write_bytes(seal_bytes)
                (execution / 'base.json').write_bytes(base_bytes)
            runner.OUTPUT.mkdir()
            with mock.patch.object(runner, 'invoke') as invoke, self.assertRaises(FileExistsError):
                runner.collect(identity)
            invoke.assert_not_called()

    def test_scorer_rejects_output_tampering_nonprefix_and_continuation_after_failure(self):
        for name in ('output', 'prefix', 'continued-after-invalid'):
            manifest, _, records, output = self.collect(name=name)
            if name == 'output':
                (output / 'responses.json').write_text('[]')
            else:
                if name == 'prefix':
                    records.reverse()
                else:
                    records[0].update(validity=None, parse_failure='invalid_json')
                    (output / '01-base.json').write_text(json.dumps(records[0]))
                    manifest['output_sha256']['01-base.json'] = shared.digest(output / '01-base.json')
                (output / 'responses.json').write_text(json.dumps(records))
                manifest['output_sha256']['responses.json'] = shared.digest(output / 'responses.json')
            (output / 'manifest.json').write_text(json.dumps(manifest))
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.score(output)
            self.assertFalse((output.parent / 'scored').exists())


if __name__ == '__main__':
    unittest.main()
