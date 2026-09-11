"""Native workflow acceptance and process boundaries; never call a provider."""

from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from decimal import Decimal
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / 'run_cycle05_coordinator.py'
SPEC = importlib.util.spec_from_file_location('cycle05_runner_under_test', SOURCE)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
SESSION = 'test-session-0001'


def events(session=SESSION, terminal='{"p_positive":0.625}', cost=0.01):
    return [
        {'type': 'system', 'subtype': 'init', 'session_id': session,
         'model': runner.MODEL, 'tools': [], 'mcp_servers': [], 'plugins': [], 'skills': [],
         'agents': ['general-purpose', 'Explore']},
        {'type': 'assistant', 'message': {
            'id': 'msg1', 'model': runner.MODEL, 'stop_reason': 'end_turn',
            'usage': {'input_tokens': 10, 'output_tokens': 20},
            'content': [{'type': 'thinking', 'thinking': 'PRIVATE_REASONING_SENTINEL'},
                        {'type': 'text', 'text': terminal}]}},
        {'type': 'result', 'subtype': 'success', 'is_error': False,
         'session_id': session, 'stop_reason': 'end_turn', 'result': terminal,
         'total_cost_usd': cost, 'num_turns': 1,
         'usage': {'input_tokens': 10, 'output_tokens': 20},
         'modelUsage': {runner.MODEL: {'canonicalModel': runner.MODEL,
                                      'provider': 'firstParty', 'inputTokens': 10,
                                      'outputTokens': 20, 'costUSD': cost}}}]


def raw_stream(values):
    return ('\n'.join(json.dumps(value) for value in values) + '\n').encode('utf-8')


class StreamTests(unittest.TestCase):
    def inspect(self, values=None, **kwargs):
        return runner.inspect_stream(raw_stream(events() if values is None else values), 0, SESSION, **kwargs)

    def test_valid_terminal_probability_and_private_text_boundary(self):
        record = self.inspect()
        self.assertTrue(record['native_acceptable'])
        self.assertEqual(record['p_positive'], '5/8')
        self.assertEqual(record['native_cost_usd'], '0.01')
        self.assertEqual(record['distinct_observed_message_count'], 1)
        self.assertEqual(record['messages']['msg1']['usage']['output_tokens'], 20)
        self.assertNotIn('PRIVATE_REASONING_SENTINEL', json.dumps(record))
        self.assertNotIn('{"p_positive":0.625}', json.dumps(record))
        self.assertNotIn('thinking_tokens', record['usage'])
        self.assertIsNone(record['parse_failure'])

    def test_continuations_merge_cumulative_usage_by_message_id(self):
        values = events()
        first = deepcopy(values[1])
        first['message']['stop_reason'] = 'max_tokens'
        first['message']['usage']['output_tokens'] = 500
        second = deepcopy(values[1])
        second['message']['id'] = 'msg2'
        second['message']['usage']['output_tokens'] = 40
        values = [values[0],
                  {'type': 'system', 'subtype': 'status', 'status': 'requesting'},
                  {'type': 'stream_event', 'event': {'type': 'message_start', 'message': {
                      'id': 'msg1', 'model': runner.MODEL, 'usage': {'output_tokens': 0}}}},
                  {'type': 'stream_event', 'event': {'type': 'message_delta', 'usage': {'output_tokens': 500},
                                                   'delta': {'stop_reason': 'max_tokens'}}},
                  first, {'type': 'system', 'subtype': 'api_retry'},
                  {'type': 'system', 'subtype': 'status', 'status': 'requesting'},
                  {'type': 'stream_event', 'event': {'type': 'message_start', 'message': {
                      'id': 'msg2', 'model': runner.MODEL, 'usage': {'output_tokens': 1}}}},
                  {'type': 'stream_event', 'event': {'type': 'message_delta', 'usage': {'output_tokens': 40},
                                                   'delta': {'stop_reason': 'end_turn'}}},
                  second, values[-1]]
        values[-1]['usage']['output_tokens'] = 540
        values[-1]['modelUsage'][runner.MODEL]['outputTokens'] = 540
        record = self.inspect(values)
        self.assertTrue(record['native_acceptable'], record['issues'])
        self.assertEqual(record['distinct_observed_message_count'], 2)
        self.assertEqual(record['messages']['msg1']['usage']['output_tokens'], 500)
        self.assertEqual(record['messages']['msg2']['usage']['output_tokens'], 40)
        self.assertEqual(record['usage']['output_tokens'], 540)
        self.assertEqual(record['requesting_status_count'], 2)
        self.assertEqual(record['recovery_markers'], ['api_retry'])

    def test_terminal_only_json_no_salvage_of_earlier_valid_answer(self):
        for terminal in ('625}', 'Here is the answer: {"p_positive":0.625}', '{"p_positive":"0.625"}',
                         '{"p_positive":0.1,"p_positive":0.625}'):
            values = events()
            values[-1]['result'] = terminal
            record = self.inspect(values)
            self.assertTrue(record['native_acceptable'])
            self.assertIsNone(record['p_positive'])
            self.assertIsNotNone(record['parse_failure'])

    def test_rejects_runtime_activity_and_model_changes(self):
        cases = [
            ('hook_activity', lambda v: v.insert(1, {'type': 'system', 'subtype': 'hook_started'})),
            ('tool_activity', lambda v: v[1]['message']['content'].append({'type': 'tool_use', 'name': 'Read'})),
            ('tool_activity', lambda v: v.insert(1, {'type': 'stream_event', 'event': {
                'type': 'content_block_start', 'content_block': {'type': 'tool_use'}}})),
            ('enabled_tools_or_mcp', lambda v: v[0].update(tools=['Read'])),
            ('enabled_tools_or_mcp', lambda v: v[0].update(mcp_servers=[{'name': 'x'}])),
            ('subagent_activity', lambda v: v[1].update(parent_tool_use_id='parent-tool')),
            ('subagent_activity', lambda v: v[-1].update(subagentStats={'count': 1})),
            ('init_model', lambda v: v[0].update(model='claude-fable-5-1')),
            ('observed_model', lambda v: v[1]['message'].update(model='claude-fable-5-1')),
            ('observed_model', lambda v: v[-1]['modelUsage'].update({'claude-fable-5-1': {}})),
            ('model_fallback', lambda v: v.insert(1, {'type': 'system', 'subtype': 'model_fallback'})),
        ]
        for code, mutate in cases:
            values = events()
            mutate(values)
            with self.subTest(code=code):
                record = self.inspect(values)
                self.assertFalse(record['native_acceptable'])
                self.assertIn(code, record['issues'])
                self.assertIsNone(record['p_positive'])

    def test_rejects_missing_cost_multiple_results_and_bad_terminal_status(self):
        cases = [('unknown_cost', lambda v: v[-1].pop('total_cost_usd')),
                 ('unknown_cost', lambda v: v[-1].update(total_cost_usd=True)),
                 ('unknown_cost', lambda v: v[-1].update(total_cost_usd='NaN')),
                 ('unknown_cost', lambda v: v[-1].update(total_cost_usd=-1)),
                 ('terminal_result_count', lambda v: v.append(deepcopy(v[-1]))),
                 ('terminal_stop', lambda v: v[-1].update(stop_reason='max_tokens')),
                 ('native_result_error', lambda v: v[-1].update(is_error=True)),
                 ('result_session', lambda v: v[-1].update(session_id='wrong')),
                 ('init_session', lambda v: v[0].update(session_id='wrong')),
                 ('init_count', lambda v: v.pop(0)),
                 ('message_output_ceiling', lambda v: v[1]['message']['usage'].update(output_tokens=501))]
        for code, mutate in cases:
            values = events()
            mutate(values)
            with self.subTest(code=code):
                record = self.inspect(values)
                self.assertIn(code, record['issues'])
                self.assertFalse(record['native_acceptable'])
                self.assertIsNone(record['p_positive'])
        self.assertIn('native_exit', runner.inspect_stream(raw_stream(events()), 1, SESSION)['issues'])
        self.assertIn('timeout', self.inspect(timed_out=True)['issues'])
        self.assertIn('malformed_native_stream', runner.inspect_stream(b'not json\n', 0, SESSION)['issues'])

    def test_context_suffix_is_allowed_but_model_aliases_are_not(self):
        values = events()
        values[1]['message']['model'] += '[1m]'
        values[-1]['modelUsage'][runner.MODEL + '[1m]'] = values[-1]['modelUsage'].pop(runner.MODEL)
        self.assertTrue(self.inspect(values)['native_acceptable'])
        for alias in ('opus', 'opus[1m]', 'claude-opus-5-1', 'claude-opus-5[2m]'):
            self.assertFalse(runner.canonical_model(alias))

    def test_model_usage_canonical_and_provider_metadata_fail_closed(self):
        for field, value in (('canonicalModel', 'claude-fable-5-1'), ('provider', 'bedrock')):
            values = events()
            values[-1]['modelUsage'][runner.MODEL][field] = value
            record = self.inspect(values)
            self.assertFalse(record['native_acceptable'], field)
            self.assertIsNone(record['p_positive'])


class BoundaryTests(unittest.TestCase):
    def test_environment_preserves_home_and_rejects_inherited_behavior(self):
        inherited = {'HOME': '/home/example', 'PATH': '/usr/bin', 'LANG': 'C.UTF-8'}
        result = runner.process_environment(inherited)
        self.assertEqual(result['HOME'], inherited['HOME'])
        self.assertEqual(inherited, {'HOME': '/home/example', 'PATH': '/usr/bin', 'LANG': 'C.UTF-8'})
        self.assertEqual({key: result[key] for key in runner.OVERRIDES}, runner.OVERRIDES)
        for key in ('ANTHROPIC_BASE_URL', 'CLAUDE_CODE_MAX_OUTPUT_TOKENS', 'AWS_PROFILE',
                    'GOOGLE_APPLICATION_CREDENTIALS', 'MAX_THINKING_TOKENS', 'DISABLE_AUTO_COMPACT'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                runner.process_environment(dict(inherited, **{key: 'unsafe-test-override'}))

    def test_command_contains_exact_prompt_and_isolated_controls(self):
        prompt = 'literal system prompt\nwith $(not-a-shell) and `no execution`'
        argv = runner.command(prompt, SESSION, Decimal('3.75'))
        self.assertEqual(argv[argv.index('--system-prompt') + 1], prompt)
        self.assertEqual(argv[argv.index('--model') + 1], runner.MODEL)
        self.assertEqual(argv[argv.index('--effort') + 1], 'high')
        self.assertEqual(argv[argv.index('--max-budget-usd') + 1], '3.75')
        self.assertEqual(argv[argv.index('--session-id') + 1], SESSION)
        for option in ('--setting-sources', '--tools'):
            self.assertEqual(argv[argv.index(option) + 1], '')
        self.assertEqual(json.loads(argv[argv.index('--mcp-config') + 1]), {'mcpServers': {}})
        self.assertTrue(json.loads(argv[argv.index('--settings') + 1])['disableAllHooks'])
        for option in ('--safe-mode', '--no-session-persistence', '--disable-slash-commands', '--no-chrome'):
            self.assertIn(option, argv)
        self.assertNotIn('--resume', argv)

    def test_invoke_uses_fresh_empty_cwd_and_exact_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'fake process.py'
            executable.write_text('import json, os, sys\nprint(json.dumps({"cwd":os.getcwd(),"files":os.listdir(),"stdin":sys.stdin.buffer.read().hex(),"argv":sys.argv[1:],"home":os.environ["HOME"]}))\n')
            payload = b'{"literal":"$()","utf8":"\xc3\xa9"}'
            stdout, stderr = root / 'stdout', root / 'stderr'
            result = runner.invoke([sys.executable, str(executable), 'a literal argument'], payload,
                                   {'HOME': directory, 'PATH': '/usr/bin'}, 5, stdout, stderr)
            record = json.loads(stdout.read_text())
            self.assertEqual(result['exit_code'], 0)
            self.assertFalse(result['timed_out'])
            self.assertEqual(record['files'], [])
            self.assertEqual(bytes.fromhex(record['stdin']), payload)
            self.assertEqual(record['argv'], ['a literal argument'])
            self.assertEqual(record['home'], directory)
            self.assertFalse(Path(record['cwd']).exists())
            self.assertEqual(stderr.read_bytes(), b'')
            with self.assertRaises(FileExistsError):
                runner.invoke([sys.executable, str(executable)], payload, {'HOME': directory}, 5, stdout, stderr)

    def test_timeout_terminates_and_reaps_owned_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'waiting process.py'
            executable.write_text('import json, os, sys, time\nprint(json.dumps({"pid":os.getpid(),"cwd":os.getcwd()}),flush=True)\ntime.sleep(30)\n')
            stdout, stderr = root / 'stdout', root / 'stderr'
            result = runner.invoke([sys.executable, str(executable)], b'', {'PATH': '/usr/bin'}, 0.3, stdout, stderr)
            record = json.loads(stdout.read_text())
            self.assertTrue(result['timed_out'])
            self.assertEqual(result['exit_code'], -signal.SIGTERM)
            self.assertLess(result['wall_seconds'], 5)
            with self.assertRaises(ProcessLookupError):
                os.kill(record['pid'], 0)
            self.assertFalse(Path(record['cwd']).exists())


class CollectionTests(unittest.TestCase):
    def run_fake_collection(self, terminals, costs, failure_at=None, changed_sources=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        fixture = runner.packets.build_fixture()
        fixture['request_order'] = fixture['request_order'][:len(terminals)]
        invocations = []

        def invoke(argv, payload, environment, timeout, stdout, stderr):
            index = len(invocations)
            session = argv[argv.index('--session-id') + 1]
            invocations.append({'argv': argv, 'payload': payload, 'timeout': timeout})
            data = events(session, terminals[index], costs[index])
            if index == failure_at:
                data[-1]['is_error'] = True
            stdout.write_bytes(raw_stream(data))
            stderr.write_bytes(b'')
            return {'exit_code': 0, 'timed_out': False, 'interrupted': False, 'wall_seconds': .01}

        original_digest = runner.digest

        def digest(path):
            return runner.BINARY_SHA if Path(path) == runner.BINARY else original_digest(path)

        output = root / 'results/observations'
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(runner, 'ROOT', root))
            stack.enter_context(mock.patch.object(runner, 'OUTPUT', output))
            hashes = [ {'test-source': 'before'}, {'test-source': 'after' if changed_sources else 'before'} ]
            stack.enter_context(mock.patch.object(runner, 'sources', side_effect=[(fixture, hashes[0]), (fixture, hashes[1])]))
            stack.enter_context(mock.patch.object(runner, 'digest', side_effect=digest))
            stack.enter_context(mock.patch.object(runner, 'process_environment', return_value={'HOME': str(root)}))
            stack.enter_context(mock.patch.object(runner, 'invoke', side_effect=invoke))
            stack.enter_context(mock.patch.object(runner.subprocess, 'check_output', return_value='test-head\n'))
            stack.enter_context(redirect_stdout(io.StringIO()))
            manifest = runner.collect()
        return manifest, invocations, output, fixture

    def test_json_failure_continues_frozen_order_without_retry(self):
        manifest, calls, output, fixture = self.run_fake_collection(['bad JSON', '{"p_positive":0.625}'], [.01, .02])
        self.assertEqual(manifest['invocations_observed'], 2)
        self.assertEqual(manifest['valid_predictions'], 1)
        self.assertEqual(manifest['known_native_cost_usd'], '0.03')
        records = json.loads((output / 'responses.json').read_text())
        self.assertEqual([row['packet_id'] for row in records], fixture['request_order'])
        by_id = {packet['packet_id']: packet for packet in fixture['packets']}
        self.assertEqual([call['payload'] for call in calls], [by_id[packet_id]['payload'].encode() for packet_id in fixture['request_order']])
        self.assertEqual([call['argv'][call['argv'].index('--max-budget-usd') + 1] for call in calls], ['4', '3.99'])
        self.assertNotEqual(records[0]['session_id'], records[1]['session_id'])
        self.assertNotIn('PRIVATE_REASONING_SENTINEL', (output / 'responses.json').read_text())

    def test_native_failure_stops_and_preserves_prefix(self):
        manifest, calls, output, _ = self.run_fake_collection(['{"p_positive":0.625}'] * 3, [.01] * 3, failure_at=1)
        self.assertEqual(len(calls), 2)
        self.assertEqual(manifest['stop_reason'], 'native_or_configuration_failure')
        self.assertEqual(manifest['invocations_observed'], 2)
        self.assertEqual(manifest['valid_predictions'], 1)
        self.assertTrue((output / 'manifest.json').exists())

    def test_budget_overshoot_stops_scheduling_and_is_accounted(self):
        manifest, calls, _, _ = self.run_fake_collection(['{"p_positive":0.625}'] * 3, [3.9, .2, .1])
        self.assertEqual(len(calls), 2)
        self.assertEqual(manifest['stop_reason'], 'native_budget_exhausted')
        self.assertEqual(manifest['known_native_cost_usd'], '4.1')

    def test_source_custody_change_invalidates_collection(self):
        manifest, _, output, _ = self.run_fake_collection(['{"p_positive":0.625}'], [.01], changed_sources=True)
        self.assertEqual(manifest['status'], 'invalid')
        self.assertFalse(manifest['sources_unchanged'])
        self.assertTrue((output / 'manifest-invalid.json').exists())
        self.assertFalse((output / 'manifest.json').exists())

    def test_existing_output_refuses_before_native_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = runner.packets.build_fixture()
            with mock.patch.object(runner, 'sources', return_value=(fixture, {})), \
                    mock.patch.object(runner, 'process_environment', return_value={}), \
                    mock.patch.object(runner, 'digest', return_value=runner.BINARY_SHA), \
                    mock.patch.object(runner, 'OUTPUT', Path(directory)), \
                    mock.patch.object(runner, 'invoke') as invoke:
                with self.assertRaises(FileExistsError):
                    runner.collect()
                invoke.assert_not_called()


if __name__ == '__main__':
    unittest.main()
