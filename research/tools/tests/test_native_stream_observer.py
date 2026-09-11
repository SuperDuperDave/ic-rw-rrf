"""Offline refusal-event attribution checks; never invoke a provider."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = load('native_observer_driver_under_test', TOOLS / 'run_cycle05_coordinator.py')
with mock.patch.dict(sys.modules, {'run_cycle05_coordinator': driver}):
    verified = load('native_observer_telemetry_under_test', TOOLS / 'run_cycle05_replication.py')
    with mock.patch.dict(sys.modules, {'run_cycle05_replication': verified}):
        observer = load('native_observer_under_test', TOOLS / 'native_stream_observer.py')

SESSION = 'synthetic-session'
REQUEST = 'synthetic-request'
PROVIDER_MESSAGE = 'provider-message'
LOCAL_MESSAGE = 'local-message'


def encode(events):
    return ('\n'.join(json.dumps(event) for event in events) + '\n').encode()


def refusal_stream():
    return [
        {'type': 'system', 'subtype': 'init', 'session_id': SESSION,
         'model': driver.MODEL, 'tools': [], 'mcp_servers': [], 'plugins': [], 'skills': []},
        {'type': 'stream_event', 'event': {'type': 'message_start', 'message': {
            'id': PROVIDER_MESSAGE, 'model': driver.MODEL,
            'usage': {'input_tokens': 10, 'output_tokens': 0}}}},
        {'type': 'system', 'subtype': 'model_refusal_no_fallback',
         'session_id': SESSION, 'request_id': REQUEST, 'original_model': driver.MODEL,
         'api_refusal_category': 'reasoning_extraction'},
        {'type': 'assistant', 'session_id': SESSION, 'request_id': REQUEST,
         'parent_tool_use_id': None, 'is_api_error_message': True, 'error': 'invalid_request',
         'message': {'id': LOCAL_MESSAGE, 'model': '<synthetic>', 'role': 'assistant',
                     'type': 'message', 'stop_reason': 'refusal',
                     'usage': {'input_tokens': 0, 'output_tokens': 0,
                               'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0,
                               'output_tokens_details': None,
                               'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0},
                               'service_tier': None,
                               'cache_creation': {'ephemeral_1h_input_tokens': 0, 'ephemeral_5m_input_tokens': 0},
                               'inference_geo': None, 'iterations': None, 'speed': None},
                     'content': [{'type': 'text', 'text': 'SYNTHETIC_LOCAL_ERROR_SENTINEL'}]}},
        {'type': 'stream_event', 'event': {'type': 'message_delta',
            'usage': {'output_tokens': 87}, 'delta': {'stop_reason': 'refusal'}}},
        {'type': 'result', 'subtype': 'error_during_execution', 'is_error': True,
         'session_id': SESSION, 'stop_reason': 'refusal', 'num_turns': 1,
         'result': 'SYNTHETIC_TERMINAL_ERROR_SENTINEL', 'total_cost_usd': .01,
         'usage': {'input_tokens': 10, 'output_tokens': 87},
         'modelUsage': {driver.MODEL: {'canonicalModel': driver.MODEL,
                                     'provider': 'firstParty', 'outputTokens': 87}}}]


class RefusalObserverTests(unittest.TestCase):
    def inspect(self, events=None, exit_code=1):
        return observer.inspect_stream(encode(refusal_stream() if events is None else events),
                                       exit_code, SESSION)

    def test_known_no_fallback_refusal_is_distinguished_but_remains_rejected(self):
        record = self.inspect()
        self.assertFalse(record['native_acceptable'])
        self.assertIsNone(record['p_positive'])
        self.assertIsNone(record['parse_failure'])
        self.assertTrue({'provider_refusal', 'native_exit', 'native_result_error', 'terminal_stop'}
                        .issubset(record['issues']))
        self.assertNotIn('model_fallback', record['issues'])
        self.assertNotIn('observed_model', record['issues'])
        self.assertEqual(record['provider_refusals'], [{
            'request_id': REQUEST, 'original_model': driver.MODEL,
            'category': 'reasoning_extraction', 'fallback_observed': False}])
        self.assertEqual(record['local_error_records'], [{
            'message_id': LOCAL_MESSAGE, 'request_id': REQUEST,
            'kind': 'native_local_api_error', 'stop_reason': 'refusal'}])
        self.assertEqual(record['observed_models'], [driver.MODEL])
        self.assertNotIn('SYNTHETIC_LOCAL_ERROR_SENTINEL', json.dumps(record))
        self.assertNotIn('SYNTHETIC_TERMINAL_ERROR_SENTINEL', json.dumps(record))

    def test_post_error_delta_belongs_to_provider_message_and_raw_bytes_are_unchanged(self):
        raw = encode(refusal_stream())
        before = hashlib.sha256(raw).hexdigest()
        original = verified.inspect_stream(raw, 1, SESSION)
        observed = observer.inspect_stream(raw, 1, SESSION)
        self.assertEqual(original['messages'][PROVIDER_MESSAGE]['usage']['output_tokens'], 0)
        self.assertEqual(original['messages'][LOCAL_MESSAGE]['usage']['output_tokens'], 87)
        self.assertEqual(set(observed['messages']), {PROVIDER_MESSAGE})
        self.assertEqual(observed['distinct_observed_message_count'], 1)
        self.assertEqual(observed['messages'][PROVIDER_MESSAGE]['usage']['output_tokens'], 87)
        self.assertEqual(observed['messages'][PROVIDER_MESSAGE]['stop_reason'], 'refusal')
        self.assertEqual(observed['usage']['output_tokens'], 87)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), before)
        self.assertEqual(observed['terminal_text_sha256'], original['terminal_text_sha256'])

    def test_incomplete_or_unmatched_local_error_signature_is_never_removed(self):
        changes = [
            ('missing_error_flag', lambda e: e[3].pop('is_api_error_message')),
            ('false_error_flag', lambda e: e[3].update(is_api_error_message=False)),
            ('wrong_error', lambda e: e[3].update(error='unknown_error')),
            ('wrong_session', lambda e: e[3].update(session_id='other-session')),
            ('missing_session', lambda e: e[3].pop('session_id')),
            ('wrong_request', lambda e: e[3].update(request_id='other-request')),
            ('missing_request', lambda e: e[3].pop('request_id')),
            ('list_request', lambda e: e[3].update(request_id=[])),
            ('dict_request', lambda e: e[3].update(request_id={})),
            ('subagent_parent', lambda e: e[3].update(parent_tool_use_id='parent-tool')),
            ('wrong_role', lambda e: e[3]['message'].update(role='user')),
            ('wrong_message_type', lambda e: e[3]['message'].update(type='unknown')),
            ('wrong_message_stop', lambda e: e[3]['message'].update(stop_reason='end_turn')),
            ('missing_refusal', lambda e: e.pop(2)),
            ('refusal_after_error', lambda e: e.insert(3, e.pop(2))),
        ]
        for name, mutate in changes:
            values = refusal_stream()
            mutate(values)
            with self.subTest(name=name):
                record = self.inspect(values)
                self.assertFalse(record['native_acceptable'])
                self.assertEqual(record['local_error_records'], [])
                self.assertIn(LOCAL_MESSAGE, record['messages'])
                self.assertIn('observed_model', record['issues'])

    def test_refusal_normalization_requires_matching_terminal_and_system_identity(self):
        changes = [
            ('terminal_success', lambda e: e[-1].update(is_error=False)),
            ('terminal_stop', lambda e: e[-1].update(stop_reason='end_turn')),
            ('terminal_session', lambda e: e[-1].update(session_id='other-session')),
            ('duplicate_terminal', lambda e: e.append(deepcopy(e[-1]))),
            ('system_session', lambda e: e[2].update(session_id='other-session')),
            ('system_model', lambda e: e[2].update(original_model='claude-fable-5-1')),
            ('system_request', lambda e: e[2].update(request_id='')),
        ]
        for name, mutate in changes:
            values = refusal_stream()
            mutate(values)
            with self.subTest(name=name):
                record = self.inspect(values)
                self.assertFalse(record['native_acceptable'])
                self.assertEqual(record['provider_refusals'], [])
                self.assertEqual(record['local_error_records'], [])
                self.assertIn('model_fallback', record['issues'])
                self.assertIn('observed_model', record['issues'])

    def test_real_fallback_is_not_suppressed_by_a_known_refusal(self):
        values = refusal_stream()
        values.insert(3, {'type': 'system', 'subtype': 'model_fallback',
                          'session_id': SESSION, 'request_id': REQUEST})
        record = self.inspect(values)
        self.assertFalse(record['native_acceptable'])
        self.assertIn('model_fallback', record['issues'])
        self.assertIn('model_fallback', record['recovery_markers'])
        self.assertIn('provider_refusal', record['issues'])
        changed_model = refusal_stream()
        changed_model[1]['event']['message']['model'] = 'claude-fable-5-1'
        record = self.inspect(changed_model)
        self.assertFalse(record['native_acceptable'])
        self.assertIn('observed_model', record['issues'])

    def test_local_looking_tool_and_excess_usage_records_retain_legacy_gates(self):
        for name in ('tool', 'usage'):
            values = refusal_stream()
            if name == 'tool':
                values[3]['message']['content'].append({'type': 'tool_use', 'name': 'Agent'})
                issue = 'tool_activity'
            else:
                values[3]['message']['usage']['output_tokens'] = 501
                del values[4]  # Keep this value from being overwritten by a later delta.
                issue = 'message_output_ceiling'
            with self.subTest(name=name):
                record = self.inspect(values)
                self.assertFalse(record['native_acceptable'])
                self.assertEqual(record['local_error_records'], [])
                self.assertIn(LOCAL_MESSAGE, record['messages'])
                self.assertIn(issue, record['issues'])
                self.assertIn('observed_model', record['issues'])

    def test_only_verified_zero_usage_shape_can_be_removed(self):
        variants = []
        known = refusal_stream()[3]['message']['usage']
        for key in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'):
            for invalid in (1, None, {}, False, 0.0, '0'):
                variants.append((key + ':' + repr(invalid), dict(known, **{key: invalid})))
        variants.append(('unknown-counter', dict(known, unknown_counter=0)))
        variants.append(('unknown-detail', dict(known, output_tokens_details={'unknown': 0})))
        for key in known:
            changed = deepcopy(known)
            del changed[key]
            variants.append(('missing:' + key, changed))
        for section in ('server_tool_use', 'cache_creation'):
            for key in known[section]:
                for invalid in (1, None, {}, False, 0.0, '0'):
                    changed = deepcopy(known)
                    changed[section][key] = invalid
                    variants.append((section + ':' + key + ':' + repr(invalid), changed))
            changed = deepcopy(known)
            changed[section]['unknown'] = 0
            variants.append(('unknown:' + section, changed))
        for key in ('output_tokens_details', 'service_tier', 'inference_geo', 'iterations', 'speed'):
            for invalid in (0, False, {}):
                variants.append((key + ':' + repr(invalid), dict(known, **{key: invalid})))
        for name, usage in variants:
            values = refusal_stream()
            values[3]['message']['usage'] = usage
            with self.subTest(name=name):
                record = self.inspect(values)
                self.assertFalse(record['native_acceptable'])
                self.assertEqual(record['local_error_records'], [])
                self.assertIn(LOCAL_MESSAGE, record['messages'])
                self.assertIn('observed_model', record['issues'])

    def test_unknown_refusal_category_is_sanitized_and_cannot_justify_local_removal(self):
        for category in ({'text': 'UNKNOWN_CATEGORY_SENTINEL'}, ['UNKNOWN_CATEGORY_SENTINEL'],
                         'UNKNOWN_CATEGORY_SENTINEL', None, True):
            values = refusal_stream()
            values[2]['api_refusal_category'] = category
            with self.subTest(category=category):
                record = self.inspect(values)
                self.assertFalse(record['native_acceptable'])
                self.assertEqual(record['provider_refusals'][0]['category'], 'unrecognized')
                self.assertEqual(record['local_error_records'], [])
                self.assertIn('observed_model', record['issues'])
                self.assertNotIn('UNKNOWN_CATEGORY_SENTINEL', json.dumps(record))

    def test_successful_stream_is_unchanged_except_empty_observer_metadata(self):
        values = refusal_stream()
        del values[2:4]
        values[2]['event']['delta']['stop_reason'] = 'end_turn'
        values[-1].update(subtype='success', is_error=False, stop_reason='end_turn',
                          result='{"p_positive":0.625}')
        raw = encode(values)
        expected = verified.inspect_stream(raw, 0, SESSION)
        observed = observer.inspect_stream(raw, 0, SESSION)
        self.assertTrue(observed['native_acceptable'])
        self.assertEqual(observed.pop('provider_refusals'), [])
        self.assertEqual(observed.pop('local_error_records'), [])
        self.assertEqual(observed, expected)


if __name__ == '__main__':
    unittest.main()
