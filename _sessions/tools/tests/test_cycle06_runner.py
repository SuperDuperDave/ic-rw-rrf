"""Cycle06 adapter boundaries using synthetic native streams; no provider calls."""

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


# Isolate the shared mutable driver from the historical test modules and CLI.
driver = load('cycle06_driver_under_test', TOOLS / 'run_cycle05_coordinator.py')
with mock.patch.dict(sys.modules, {'run_cycle05_coordinator': driver}):
    telemetry = load('cycle06_telemetry_under_test', TOOLS / 'run_cycle05_replication.py')
    with mock.patch.dict(sys.modules, {'run_cycle05_replication': telemetry}):
        runner = load('cycle06_runner_under_test', TOOLS / 'run_cycle06_coordinator.py')

CONFIGURED = ('OUTPUT', 'PREPARED', 'PREPARED_SHA', 'CAP', 'CALL_SECONDS',
              'BATCH_SECONDS', 'sources', 'inspect_stream', 'packets')
# Independently copied native schema; the historical parser tests exercise its
# malformed/nonzero variants. Here it distinguishes the selected adapter parser.
ZERO_STATS = {
    'spawned': 0, 'requested': {'background': 0, 'foreground': 0, 'unset': 0},
    'started_in_background': 0, 'max_depth': 0, 'spawned_by_subagents': 0,
    'completed': 0, 'failed': 0, 'killed': {'parent': 0, 'user': 0, 'system': 0},
    'refused': {'depth_limit': 0, 'concurrency_limit': 0, 'budget': 0}, 'by_type': {},
}


def stream(session, terminal, cost):
    values = [
        {'type': 'system', 'subtype': 'init', 'session_id': session,
         'model': driver.MODEL, 'tools': [], 'mcp_servers': [], 'plugins': [], 'skills': []},
        {'type': 'assistant', 'message': {'id': 'synthetic-message', 'model': driver.MODEL,
         'usage': {'input_tokens': 10, 'output_tokens': 20}, 'stop_reason': 'end_turn',
         'content': [{'type': 'thinking', 'thinking': 'PRIVATE_SENTINEL'}]}},
        {'type': 'result', 'subtype': 'success', 'is_error': False,
         'session_id': session, 'stop_reason': 'end_turn', 'result': terminal,
         'total_cost_usd': cost, 'num_turns': 1,
         'usage': {'input_tokens': 10, 'output_tokens': 20},
         'modelUsage': {driver.MODEL: {'canonicalModel': driver.MODEL,
                                     'provider': 'firstParty', 'outputTokens': 20}},
         'subagent_stats': deepcopy(ZERO_STATS)}]
    if cost is None:
        del values[-1]['total_cost_usd']
    return values


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = runner.experiment.build_fixture()

    def fake_collection(self, *, name='cycle06', terminals=None, costs=None,
                        native_error_at=None, exception_at=None, times=None):
        calls = []
        output = self.root / 'results' / name / 'observations'
        terminals = ['{"p_positive":0.625}'] * 8 if terminals is None else terminals
        costs = [.01] * 8 if costs is None else costs
        original_digest = driver.digest
        before = {key: getattr(driver, key) for key in CONFIGURED}

        def invoke(argv, payload, environment, timeout, stdout, stderr):
            index = len(calls)
            session = argv[argv.index('--session-id') + 1]
            calls.append({'argv': argv, 'payload': payload, 'environment': environment,
                          'timeout': timeout, 'session': session})
            if index == exception_at:
                raise RuntimeError('synthetic invocation failure')
            values = stream(session, terminals[index], costs[index])
            if index == native_error_at:
                values[-1]['is_error'] = True
            stdout.write_bytes(('\n'.join(json.dumps(v) for v in values) + '\n').encode())
            stderr.write_bytes(b'')
            return {'exit_code': 0, 'timed_out': False, 'interrupted': False, 'wall_seconds': .01}

        def digest(path):
            return driver.BINARY_SHA if Path(path) == driver.BINARY else original_digest(path)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(driver, 'ROOT', self.root))
            stack.enter_context(mock.patch.object(runner, 'BASE', output.parent))
            stack.enter_context(mock.patch.object(runner, 'PREPARED', output.parent / 'prepared'))
            stack.enter_context(mock.patch.object(runner, 'PREPARED_SHA', 'fresh-prepared-identity'))
            stack.enter_context(mock.patch.object(runner, 'sources', return_value=(self.fixture, {'frozen': 'identity'})))
            validator = stack.enter_context(mock.patch.object(runner.experiment, 'validate_payload',
                                                              wraps=runner.experiment.validate_payload))
            stack.enter_context(mock.patch.object(driver, 'digest', side_effect=digest))
            stack.enter_context(mock.patch.object(driver, 'process_environment', return_value=
                driver.process_environment({'HOME': str(self.root), 'PATH': '/usr/bin'})))
            stack.enter_context(mock.patch.object(driver, 'invoke', side_effect=invoke))
            stack.enter_context(mock.patch.object(driver.subprocess, 'check_output', return_value='test-head\n'))
            stack.enter_context(mock.patch.object(driver.time, 'monotonic',
                **({'return_value': 0} if times is None else {'side_effect': times})))
            stack.enter_context(redirect_stdout(io.StringIO()))
            if exception_at is None:
                manifest = runner.collect()
            else:
                with self.assertRaisesRegex(RuntimeError, 'synthetic invocation failure'):
                    runner.collect()
                manifest = json.loads((output / 'manifest-invalid.json').read_text())
        self.assertEqual({key: getattr(driver, key) for key in CONFIGURED}, before)
        return manifest, calls, json.loads((output / 'responses.json').read_text()), validator

    def test_eight_fresh_payloads_use_new_validator_and_frozen_native_controls(self):
        manifest, calls, records, validator = self.fake_collection()
        self.assertEqual(len(calls), 8)
        self.assertEqual(manifest['status'], 'complete')
        self.assertEqual(manifest['valid_predictions'], 8)
        self.assertEqual(manifest['prepared_manifest_sha256'], 'fresh-prepared-identity')
        self.assertEqual((manifest['native_budget_usd'], manifest['batch_wall_seconds'],
                          manifest['call_wall_seconds']), ('1', 300, 120))
        by_id = {p['packet_id']: p for p in self.fixture['packets']}
        expected = [by_id[key]['payload'].encode() for key in self.fixture['request_order']]
        self.assertEqual([row['packet_id'] for row in records], self.fixture['request_order'])
        self.assertEqual([call['payload'] for call in calls], expected)
        self.assertEqual([call.args[0] for call in validator.call_args_list], [json.loads(p) for p in expected])
        self.assertEqual(len({call['session'] for call in calls}), 8)
        self.assertEqual([call['argv'][call['argv'].index('--max-budget-usd') + 1] for call in calls],
                         ['1', '0.99', '0.98', '0.97', '0.96', '0.95', '0.94', '0.93'])
        for call, record in zip(calls, records):
            argv = call['argv']
            for key, value in (('--model', 'claude-opus-5'), ('--effort', 'high'),
                               ('--tools', ''), ('--setting-sources', ''),
                               ('--system-prompt', self.fixture['system_prompt'])):
                self.assertEqual(argv[argv.index(key) + 1], value)
            self.assertEqual(json.loads(argv[argv.index('--mcp-config') + 1]), {'mcpServers': {}})
            self.assertIn('--safe-mode', argv)
            self.assertIn('--no-session-persistence', argv)
            self.assertNotIn('--resume', argv)
            self.assertEqual(call['environment']['CLAUDE_CODE_MAX_OUTPUT_TOKENS'], '500')
            self.assertEqual(call['timeout'], 120)
            self.assertTrue(record['native_acceptable'])
            self.assertEqual(record['subagent_statistics'], [{'field': 'subagent_stats', 'counts': ZERO_STATS}])
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(records))

    def test_invalid_terminal_continues_but_native_error_stops_without_retry(self):
        manifest, calls, records, _ = self.fake_collection(
            terminals=['bad JSON'] + ['{"p_positive":0.625}'] * 7, native_error_at=2)
        self.assertEqual(len(calls), 3)
        self.assertEqual([row['packet_id'] for row in records], self.fixture['request_order'][:3])
        self.assertTrue(records[0]['native_acceptable'])
        self.assertIsNotNone(records[0]['parse_failure'])
        self.assertIsNone(records[0]['p_positive'])
        self.assertEqual(records[1]['p_positive'], '5/8')
        self.assertFalse(records[2]['native_acceptable'])
        self.assertEqual(manifest['valid_predictions'], 1)
        self.assertEqual(manifest['stop_reason'], 'native_or_configuration_failure')

    def test_unknown_cost_and_budget_exhaustion_preserve_only_scheduled_prefix(self):
        for name, costs, reason, spent, known in (
                ('unknown', [.01, None], 'native_or_configuration_failure', '0.01', False),
                ('budget', [.9, .2], 'native_budget_exhausted', '1.1', True)):
            with self.subTest(name=name):
                manifest, calls, records, _ = self.fake_collection(name=name, costs=costs)
                self.assertEqual(len(calls), 2)
                self.assertEqual([row['packet_id'] for row in records], self.fixture['request_order'][:2])
                self.assertEqual(manifest['invocations_scheduled'], 2)
                self.assertEqual(manifest['stop_reason'], reason)
                self.assertEqual(manifest['known_native_cost_usd'], spent)
                self.assertEqual(manifest['all_observed_costs_known'], known)

    def test_batch_deadline_caps_remaining_call_and_stops_scheduling(self):
        manifest, calls, records, _ = self.fake_collection(times=[0, 0, 220, 300, 300])
        self.assertEqual([call['timeout'] for call in calls], [120, 80])
        self.assertEqual(len(records), 2)
        self.assertEqual(manifest['stop_reason'], 'batch_wall_exhausted')

    def test_configuration_restores_after_exception_and_nested_repeated_use(self):
        original = {key: getattr(driver, key) for key in CONFIGURED}
        with self.assertRaisesRegex(RuntimeError, 'synthetic scope failure'):
            with runner.configured_driver():
                outer = {key: getattr(driver, key) for key in CONFIGURED}
                with runner.configured_driver():
                    self.assertIs(driver.packets.validate_payload, runner.experiment.validate_payload)
                    self.assertIs(driver.packets.parse_probability, runner.strict.parse_probability)
                    self.assertIs(driver.inspect_stream, telemetry.inspect_stream)
                self.assertEqual({key: getattr(driver, key) for key in CONFIGURED}, outer)
                raise RuntimeError('synthetic scope failure')
        self.assertEqual({key: getattr(driver, key) for key in CONFIGURED}, original)
        failed, calls, records, _ = self.fake_collection(name='failed', exception_at=1)
        self.assertEqual((len(calls), len(records)), (2, 1))
        self.assertEqual(failed['status'], 'invalid')
        self.assertEqual(failed['stop_reason'], 'collection_exception')
        self.assertFalse(failed['all_observed_costs_known'])
        complete, fresh, _, _ = self.fake_collection(name='after-failure')
        self.assertEqual(complete['valid_predictions'], 8)
        self.assertTrue({call['session'] for call in calls}.isdisjoint(call['session'] for call in fresh))

    def test_repeated_batches_never_read_or_carry_forward_old_responses(self):
        old_files = []
        for name in ('cycle05-2026-09-10', 'cycle05-replication-2026-09-10'):
            path = self.root / 'results' / name / 'observations/responses.json'
            path.parent.mkdir(parents=True)
            path.write_text('OLD_RESPONSE_SENTINEL')
            old_files.append(path)
        original_open = Path.open

        def guarded_open(path, *args, **kwargs):
            if path in old_files:
                self.fail('cycle06 accessed historical responses')
            return original_open(path, *args, **kwargs)

        with mock.patch.object(Path, 'open', guarded_open):
            first, calls1, _, _ = self.fake_collection(name='first')
            second, calls2, records, _ = self.fake_collection(name='second')
        self.assertEqual((len(calls1), len(calls2)), (8, 8))
        self.assertNotEqual(first['batch_id'], second['batch_id'])
        self.assertTrue({call['session'] for call in calls1}.isdisjoint(call['session'] for call in calls2))
        self.assertTrue(all(row['p_positive'] == '5/8' for row in records))
        self.assertEqual([path.read_text() for path in old_files], ['OLD_RESPONSE_SENTINEL'] * 2)
        with mock.patch.object(runner, 'BASE', self.root / 'results/second'), \
                mock.patch.object(runner, 'sources', return_value=(self.fixture, {})), \
                mock.patch.object(driver, 'process_environment', return_value={}), \
                mock.patch.object(driver, 'digest', return_value=driver.BINARY_SHA), \
                mock.patch.object(driver, 'invoke') as invoke:
            with self.assertRaises(FileExistsError):
                runner.collect()
            invoke.assert_not_called()


class PreflightTests(unittest.TestCase):
    def test_shared_native_hash_or_eight_input_contract_fails_before_provider(self):
        fixture = runner.experiment.build_fixture()
        for name, changed in [('shared-hash', None), ('seven-inputs', fixture['request_order'][:7]),
                              ('duplicate-input', fixture['request_order'][:7] + fixture['request_order'][:1])]:
            candidate = deepcopy(fixture)
            if changed is not None:
                candidate['request_order'] = changed
            with self.subTest(name=name), \
                    mock.patch.object(runner.experiment, 'validate_fixture_custody',
                                      return_value=(candidate, {'source_sha256_start': {}})), \
                    mock.patch.object(driver, 'digest', return_value='altered-identity'), \
                    mock.patch.object(driver, 'invoke') as invoke:
                with self.assertRaisesRegex(ValueError, 'implementation changed|eight unique inputs'):
                    runner.collect()
                invoke.assert_not_called()

    def test_real_prepared_manifest_output_and_source_custody_fail_before_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared = Path(directory) / 'prepared'
            protocol = runner.ROOT / '_sessions/cycles/2026-09-10-cycle06-execution-protocol.md'

            def fresh_output(path):
                path = Path(path)
                path.mkdir()
                return path

            # Only bypass the production results/ location restriction and Git
            # metadata lookup; preparation and custody validation remain real.
            with mock.patch.object(runner.experiment.frozen, '_fresh_results_directory', side_effect=fresh_output), \
                    mock.patch.object(runner.experiment.subprocess, 'check_output', return_value='test-head\n'):
                runner.experiment.prepare_fixture(prepared, protocol, driver.digest(protocol))
            identity = driver.digest(prepared / 'manifest.json')
            fixture_bytes = (prepared / 'fixture.json').read_bytes()
            runner.experiment.validate_fixture_custody(prepared, identity)
            original_sources = runner.experiment._source_hashes(protocol)
            for name in ('manifest', 'output', 'source'):
                with self.subTest(name=name), ExitStack() as stack:
                    stack.enter_context(mock.patch.object(runner, 'PREPARED', prepared))
                    stack.enter_context(mock.patch.object(runner, 'PREPARED_SHA',
                                                          '0' * 64 if name == 'manifest' else identity))
                    invoke = stack.enter_context(mock.patch.object(driver, 'invoke'))
                    if name == 'source':
                        stack.enter_context(mock.patch.object(runner.experiment, '_source_hashes',
                            return_value=dict(original_sources, **{'synthetic-source': 'changed'})))
                    if name == 'output':
                        (prepared / 'fixture.json').write_bytes(fixture_bytes + b' ')
                    try:
                        with self.assertRaisesRegex(ValueError, 'prepared (manifest hash|output hash|source custody) mismatch'):
                            runner.collect()
                        invoke.assert_not_called()
                    finally:
                        (prepared / 'fixture.json').write_bytes(fixture_bytes)


if __name__ == '__main__':
    unittest.main()
