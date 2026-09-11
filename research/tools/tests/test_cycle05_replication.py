"""Regression tests for the separate telemetry-parser replication; no providers."""

from contextlib import ExitStack, redirect_stdout
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


legacy = load('cycle05_replication_legacy_under_test', TOOLS / 'run_cycle05_coordinator.py')
with mock.patch.dict(sys.modules, {'run_cycle05_coordinator': legacy}):
    replica = load('cycle05_replication_under_test', TOOLS / 'run_cycle05_replication.py')
SESSION = 'isolated-replication-test-session'

# This table is copied from the first observation's terminal metadata, read
# independently of the adapter. It contains no model answer or thought text.
OBSERVED_ZERO = {
    'spawned': 0, 'requested': {'background': 0, 'foreground': 0, 'unset': 0},
    'started_in_background': 0, 'max_depth': 0, 'spawned_by_subagents': 0,
    'completed': 0, 'failed': 0, 'killed': {'parent': 0, 'user': 0, 'system': 0},
    'refused': {'depth_limit': 0, 'concurrency_limit': 0, 'budget': 0}, 'by_type': {},
}


def events(session=SESSION):
    return [
        {'type': 'system', 'subtype': 'init', 'session_id': session,
         'model': legacy.MODEL, 'tools': [], 'mcp_servers': [], 'plugins': [], 'skills': []},
        {'type': 'assistant', 'message': {'id': 'test-message', 'model': legacy.MODEL,
         'usage': {'input_tokens': 10, 'output_tokens': 20}, 'stop_reason': 'end_turn',
         'content': [{'type': 'thinking', 'thinking': 'PRIVATE_THOUGHT_SENTINEL'}]}},
        {'type': 'result', 'subtype': 'success', 'is_error': False,
         'session_id': session, 'stop_reason': 'end_turn', 'result': '{"p_positive":0.625}',
         'total_cost_usd': 0.01, 'num_turns': 1,
         'usage': {'input_tokens': 10, 'output_tokens': 20},
         'modelUsage': {legacy.MODEL: {'canonicalModel': legacy.MODEL, 'provider': 'firstParty',
                                     'inputTokens': 10, 'outputTokens': 20, 'costUSD': 0.01}},
         'subagent_stats': deepcopy(OBSERVED_ZERO)}]


def raw(values):
    return ('\n'.join(json.dumps(value) for value in values) + '\n').encode('utf-8')


def leaf_paths(shape, prefix=()):
    for key, value in shape.items():
        if isinstance(value, dict):
            yield from leaf_paths(value, prefix + (key,))
        else:
            yield prefix + (key,)


class TelemetryTests(unittest.TestCase):
    def inspect(self, values):
        return replica.inspect_stream(raw(values), 0, SESSION)

    def test_exact_observed_zero_counts_correct_historical_false_positive(self):
        values = events()
        original = replica._inspect(raw(values), 0, SESSION)
        corrected = self.inspect(values)
        self.assertFalse(original['native_acceptable'])
        self.assertEqual(original['issues'], ['subagent_activity'])
        self.assertTrue(corrected['native_acceptable'], corrected['issues'])
        self.assertEqual(corrected['p_positive'], '5/8')
        self.assertEqual(corrected['subagent_statistics'], [{'field': 'subagent_stats', 'counts': OBSERVED_ZERO}])
        self.assertTrue(replica.exact_zero_stats(OBSERVED_ZERO))
        self.assertNotIn('PRIVATE_THOUGHT_SENTINEL', json.dumps(corrected))

    def test_every_count_leaf_rejects_nonzero_or_noninteger_values(self):
        for path in leaf_paths(OBSERVED_ZERO):
            for invalid in (1, -1, True, False, '0', 'PRIVATE_UNKNOWN_SENTINEL', None, 0.0, [], {}):
                values = events()
                parent = values[-1]['subagent_stats']
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = invalid
                with self.subTest(path=path, invalid=invalid):
                    record = self.inspect(values)
                    self.assertFalse(record['native_acceptable'])
                    self.assertIsNone(record['p_positive'])
                    self.assertIn('subagent_statistics_nonzero_or_unknown', record['issues'])
                    self.assertEqual(record['subagent_statistics'], [])
                    self.assertNotIn('PRIVATE_UNKNOWN_SENTINEL', json.dumps(record))

    def test_missing_extra_and_unknown_schema_fail_closed(self):
        variants = [None, {}, [], 'PRIVATE_UNKNOWN_SCHEMA', 0, False]
        for path in leaf_paths(OBSERVED_ZERO):
            changed = deepcopy(OBSERVED_ZERO)
            parent = changed
            for key in path[:-1]:
                parent = parent[key]
            del parent[path[-1]]
            variants.append(changed)
        for section in (None, 'requested', 'killed', 'refused', 'by_type'):
            changed = deepcopy(OBSERVED_ZERO)
            parent = changed if section is None else changed[section]
            parent['unknown'] = 0
            variants.append(changed)
        for stats in variants:
            values = events()
            values[-1]['subagent_stats'] = stats
            with self.subTest(stats=stats):
                record = self.inspect(values)
                self.assertFalse(record['native_acceptable'])
                self.assertIn('subagent_statistics_nonzero_or_unknown', record['issues'])
                self.assertIsNone(record['p_positive'])
                self.assertEqual(record['subagent_statistics'], [])
                self.assertNotIn('PRIVATE_UNKNOWN_SCHEMA', json.dumps(record))

    def test_camel_case_field_and_mixed_valid_invalid_statistics(self):
        values = events()
        values[-1]['subagentStats'] = values[-1].pop('subagent_stats')
        record = self.inspect(values)
        self.assertTrue(record['native_acceptable'])
        self.assertEqual(record['subagent_statistics'][0]['field'], 'subagentStats')
        values[-1]['subagent_stats'] = deepcopy(OBSERVED_ZERO)
        values[-1]['subagent_stats']['spawned'] = 1
        record = self.inspect(values)
        self.assertFalse(record['native_acceptable'])
        self.assertEqual(record['subagent_statistics'], [{'field': 'subagentStats', 'counts': OBSERVED_ZERO}])

    def test_absent_statistics_preserves_legacy_acceptance(self):
        values = events()
        del values[-1]['subagent_stats']
        original = replica._inspect(raw(values), 0, SESSION)
        corrected = self.inspect(values)
        statistics = corrected.pop('subagent_statistics')
        self.assertEqual(statistics, [])
        self.assertEqual(corrected, original)

    def test_zero_stats_never_override_real_runtime_activity_or_failures(self):
        mutations = [
            ('tool_activity', lambda values: values[1]['message']['content'].append({'type': 'tool_use', 'name': 'Agent'})),
            ('subagent_activity', lambda values: values[1].update(parent_tool_use_id='parent-tool')),
            ('hook_activity', lambda values: values.insert(1, {'type': 'system', 'subtype': 'hook_started'})),
            ('observed_model', lambda values: values[1]['message'].update(model='claude-fable-5-1')),
            ('unknown_cost', lambda values: values[-1].pop('total_cost_usd')),
            ('terminal_result_count', lambda values: values.append(deepcopy(values[-1]))),
        ]
        for code, mutate in mutations:
            values = events()
            mutate(values)
            with self.subTest(code=code):
                record = self.inspect(values)
                self.assertFalse(record['native_acceptable'])
                self.assertIn(code, record['issues'])
                self.assertIsNone(record['p_positive'])

    def test_terminal_parser_stays_strict_after_metadata_correction(self):
        values = events()
        values[1]['message']['content'].append({'type': 'text', 'text': '{"p_positive":0.625}'})
        values[-1]['result'] = '625}'
        record = self.inspect(values)
        self.assertTrue(record['native_acceptable'])
        self.assertIsNone(record['p_positive'])
        self.assertEqual(record['parse_failure'], 'malformed_json')

    def test_original_raw_bytes_and_terminal_hash_are_preserved(self):
        values = events()
        native_bytes = raw(values)
        before = hashlib.sha256(native_bytes).hexdigest()
        with mock.patch.object(replica, '_inspect', wraps=replica._inspect) as inspect:
            record = replica.inspect_stream(native_bytes, 0, SESSION)
        self.assertEqual(hashlib.sha256(native_bytes).hexdigest(), before)
        self.assertIn(b'subagent_stats', native_bytes)
        transformed = inspect.call_args.args[0]
        transformed_result = json.loads(transformed.splitlines()[-1])
        expected = deepcopy(values[-1])
        del expected['subagent_stats']
        self.assertEqual(transformed_result, expected)
        self.assertEqual(record['terminal_text_sha256'], hashlib.sha256(values[-1]['result'].encode()).hexdigest())


class ReplicaCustodyTests(unittest.TestCase):
    def test_configure_changes_only_process_parser_and_output_custody(self):
        names = ('BINARY', 'BINARY_SHA', 'MODEL', 'CAP', 'CALL_SECONDS', 'BATCH_SECONDS',
                 'PREPARED', 'PREPARED_SHA', 'OVERRIDES')
        before = {name: deepcopy(getattr(legacy, name)) for name in names}
        with mock.patch.object(legacy, 'OUTPUT'), mock.patch.object(legacy, 'inspect_stream'), mock.patch.object(legacy, 'sources'):
            replica.configure()
            self.assertEqual(legacy.OUTPUT, legacy.ROOT / 'results/cycle05-replication-2026-09-10/observations')
            self.assertIs(legacy.inspect_stream, replica.inspect_stream)
            self.assertIs(legacy.sources, replica.sources)
            self.assertEqual({name: getattr(legacy, name) for name in names}, before)

    def test_original_sources_remain_identical_to_original_receipt(self):
        original_manifest = json.loads((legacy.ROOT / 'results/cycle05-2026-09-10/observations/manifest.json').read_text())
        for name in ('_sessions/tools/run_cycle05_coordinator.py', '_sessions/tools/tests/test_cycle05_runner.py',
                     'evaluation/cycle05_coordinator_packets.py', 'evaluation/tests/test_cycle05_coordinator_packets.py'):
            expected = original_manifest['source_sha256_start'][name]
            self.assertEqual(hashlib.sha256((legacy.ROOT / name).read_bytes()).hexdigest(), expected)

    def test_replica_collection_hashes_original_stream_and_preserves_private_stats(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            fixture = legacy.packets.build_fixture()
            fixture['request_order'] = fixture['request_order'][:1]
            captured = []
            original_digest = legacy.digest

            def invoke(argv, payload, environment, timeout, stdout, stderr):
                session = argv[argv.index('--session-id') + 1]
                native_bytes = raw(events(session))
                captured.append(native_bytes)
                stdout.write_bytes(native_bytes)
                stderr.write_bytes(b'')
                return {'exit_code': 0, 'timed_out': False, 'interrupted': False, 'wall_seconds': 0.01}

            def digest(path):
                return legacy.BINARY_SHA if Path(path) == legacy.BINARY else original_digest(path)

            stack.enter_context(mock.patch.object(legacy, 'ROOT', root))
            stack.enter_context(mock.patch.object(legacy, 'OUTPUT'))
            stack.enter_context(mock.patch.object(legacy, 'inspect_stream'))
            stack.enter_context(mock.patch.object(legacy, 'sources'))
            replica.configure()
            stack.enter_context(mock.patch.object(legacy, 'sources', return_value=(fixture, {'frozen': 'identity'})))
            stack.enter_context(mock.patch.object(legacy, 'process_environment', return_value={}))
            stack.enter_context(mock.patch.object(legacy, 'digest', side_effect=digest))
            stack.enter_context(mock.patch.object(legacy, 'invoke', side_effect=invoke))
            stack.enter_context(mock.patch.object(legacy.subprocess, 'check_output', return_value='test-head\n'))
            stack.enter_context(redirect_stdout(io.StringIO()))
            manifest = legacy.collect()
            records = json.loads((legacy.OUTPUT / 'responses.json').read_text())
            self.assertEqual(manifest['status'], 'complete')
            self.assertEqual(manifest['valid_predictions'], 1)
            record = records[0]
            self.assertTrue(record['native_acceptable'])
            self.assertEqual(record['stdout_sha256'], hashlib.sha256(captured[0]).hexdigest())
            self.assertEqual((root / record['stdout_path']).read_bytes(), captured[0])
            self.assertEqual(record['subagent_statistics'], [{'field': 'subagent_stats', 'counts': OBSERVED_ZERO}])
            self.assertNotIn('PRIVATE_THOUGHT_SENTINEL', json.dumps(record))
            self.assertFalse((root / 'results/cycle05-2026-09-10/observations').exists())


if __name__ == '__main__':
    unittest.main()
