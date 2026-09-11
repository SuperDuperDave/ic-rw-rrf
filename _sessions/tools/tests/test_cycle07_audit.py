"""Independent audit regressions with hand-derived states and native examples."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


PATH = Path(__file__).resolve().parents[1] / 'check_cycle07_evidence.py'
SPEC = importlib.util.spec_from_file_location('cycle07_audit_under_test', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

SEQUENTIAL = '''a = 3
b = 4
c = 1
a = a + b
b = a - b
c = c * a
if a > b:
    a = a + c
result = (a % 3 == 2)
'''
LOOP = '''a = 2
b = 3
c = 1
for i in range(4):
    a = a + b
    b = b + i
    if a % 2 == 0:
        c = c + a
    b = b - c
result = (a % 3 == 1)
'''


class InterpreterTests(unittest.TestCase):
    def test_hand_derived_sequential_state(self):
        row = audit.evaluate_program(SEQUENTIAL)
        self.assertIs(row['answer'], True)
        self.assertEqual(row['final_state'], {'a': 14, 'b': 3, 'c': 7})
        self.assertEqual(row['executed_statements'], 9)
        self.assertEqual(row['worst_case_executed_statements'], 9)
        self.assertEqual(row['max_abs_intermediate'], 14)

    def test_hand_derived_loop_state_and_header_visits(self):
        row = audit.evaluate_program(LOOP)
        self.assertIs(row['answer'], False)
        self.assertEqual(row['final_state'], {'a': 12, 'b': -7, 'c': 13, 'i': 3})
        self.assertEqual(row['executed_statements'], 26)
        self.assertEqual(row['worst_case_executed_statements'], 29)
        self.assertEqual(row['max_abs_intermediate'], 13)

    def test_signed_integer_modulus_and_uninitialized_read(self):
        row = audit.evaluate_program(SEQUENTIAL.replace('a = 3', 'a = -3'))
        self.assertEqual(row['final_state']['a'], 2)
        self.assertIs(row['answer'], True)
        with self.assertRaises(ValueError):
            audit.evaluate_program(SEQUENTIAL.replace('a = 3', 'a = i'))

    def test_unexecuted_branch_is_still_allowlisted(self):
        for replacement in ('    import os', '    a = abs(c)', '    a = c ** 2',
                            '    a = c % 0', '    a = c / 2', '    a += c',
                            '    a = True', '    a = [1]', '    a = c.real'):
            source = SEQUENTIAL.replace('if a > b:', 'if a < b:').replace('    a = a + c', replacement)
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                audit.evaluate_program(source)

    def test_exact_grammar_and_bounds(self):
        cases = [SEQUENTIAL.replace('a = 3', 'a = 1000001'),
            SEQUENTIAL.replace('a = a + b', 'a = 999999 * b'),
            SEQUENTIAL.replace('    a = a + c', '    a = a + c\nelse:\n    a = a - c'),
            SEQUENTIAL.replace('    a = a + c', '    if b > 0:\n        a = a + c'),
            SEQUENTIAL.replace('c = 1', 'x = 1'),
            SEQUENTIAL.replace('result = (a % 3 == 2)', 'result = (a % 4 == 2)'),
            SEQUENTIAL.replace('a = 3\nb = 4', 'a = 3; b = 4'),
            LOOP.replace('range(4)', 'range(7)'), LOOP.replace('range(4)', 'range(a)'),
            LOOP.replace('range(4)', 'range(True)')]
        for source in cases:
            with self.subTest(source=source), self.assertRaises(ValueError):
                audit.evaluate_program(source)
        with mock.patch.object(audit, 'MAX_STEPS', 28), self.assertRaises(ValueError):
            audit.evaluate_program(LOOP)

    def test_normalizer_blocks_parameter_alpha_and_predicate_complement_leakage(self):
        variant = SEQUENTIAL.replace('a', 'x').replace('b', 'y').replace('c', 'z')
        variant = variant.replace('= 3', '= -37').replace('= 4', '= 9').replace('== 2', '!= 1')
        self.assertEqual(audit.normalized_template(SEQUENTIAL), audit.normalized_template(variant))
        self.assertNotEqual(audit.normalized_template(SEQUENTIAL),
                            audit.normalized_template(SEQUENTIAL.replace('a = a + b', 'a = a * b')))


class ScoringTests(unittest.TestCase):
    def test_boolean_parse_is_terminal_schema_strict(self):
        for text, answer in [(' {"answer": true} \n', True), ('{"answer":false}', False)]:
            self.assertEqual(audit.boolean_answer(text), (answer, None))
        for text in ('{"answer":0}', '{"answer":"true"}', '{"answer":true,"answer":false}',
                     '{"answer":false,"why":0}', '```json\n{"answer":true}\n```',
                     '{"answer":NaN}', '{"answer":true} trailing', None):
            with self.subTest(text=text):
                answer, failure = audit.boolean_answer(text)
                self.assertIsNone(answer)
                self.assertIsNotNone(failure)

    def test_exact_joint_events_and_zero_denominators(self):
        pairs = [{'truth': False, 'g_answer': False, 's_answer': False},
                 {'truth': False, 'g_answer': False, 's_answer': True},
                 {'truth': True, 'g_answer': False, 's_answer': True},
                 {'truth': True, 'g_answer': False, 's_answer': False}]
        table = audit.independent_table(pairs)
        self.assertEqual(table['cells'], {'00': 1, '01': 1, '10': 1, '11': 1})
        self.assertEqual(table['conditional_correction'], {'numerator': 1, 'denominator': 2, 'value': .5})
        self.assertEqual(table['conditional_harm'], {'numerator': 1, 'denominator': 2, 'value': .5})
        self.assertEqual(table['s_minus_g_error']['value'], 0)
        for truth in ('false', 'true'):
            self.assertEqual(table['by_truth'][truth]['joint_error_excess'],
                             {'numerator': 0, 'denominator': 4, 'value': 0.0})
        empty = audit.independent_table([])
        self.assertIsNone(empty['conditional_correction']['value'])
        self.assertEqual(empty['by_truth']['true']['joint_error_excess'],
                         {'numerator': 0, 'denominator': 0, 'value': None})

    def test_truth_conditioned_excess_is_not_pooled_product(self):
        pairs = [{'truth': False, 'g_answer': False, 's_answer': False},
                 {'truth': True, 'g_answer': False, 's_answer': False}]
        table = audit.independent_table(pairs)
        self.assertEqual(table['by_truth']['true']['joint_error_excess']['value'], 0)
        self.assertEqual(table['by_truth']['false']['joint_error_excess']['value'], 0)
        self.assertEqual(table['cells']['11'] / table['N'] - .5 * .5, .25)


class NativeTests(unittest.TestCase):
    def native_case(self, root, refused=False):
        session, mid, rid = 'synthetic-session', 'synthetic-provider-id', 'synthetic-request-id'
        init = {'type': 'system', 'subtype': 'init', 'session_id': session, 'model': audit.MODEL,
                'tools': [], 'mcp_servers': [], 'skills': [], 'plugins': []}
        events = [init, {'type': 'stream_event', 'event': {'type': 'message_start',
            'message': {'id': mid, 'model': audit.MODEL, 'usage': {'output_tokens': 0}, 'content': []}}}]
        stop, issues, locals_, refusals = 'end_turn', [], [], []
        if refused:
            stop, issues = 'refusal', ['native_result_error', 'provider_refusal', 'terminal_stop']
            events += [{'type': 'system', 'subtype': 'model_refusal_no_fallback',
                        'session_id': session, 'request_id': rid, 'original_model': audit.MODEL,
                        'api_refusal_category': 'reasoning_extraction'},
                       {'type': 'assistant', 'session_id': session, 'request_id': rid,
                        'is_api_error_message': True, 'error': 'invalid_request', 'parent_tool_use_id': None,
                        'message': {'id': 'synthetic-local-error', 'model': '<synthetic>', 'type': 'message',
                                    'role': 'assistant', 'stop_reason': 'refusal', 'usage': deepcopy(audit.LOCAL_USAGE),
                                    'content': [{'type': 'text', 'text': 'PRIVATE_LOCAL_SENTINEL'}]}}]
            locals_ = [{'message_id': 'synthetic-local-error', 'request_id': rid,
                        'kind': 'native_local_api_error', 'stop_reason': 'refusal'}]
            refusals = [{'request_id': rid, 'original_model': audit.MODEL,
                         'category': 'reasoning_extraction', 'fallback_observed': False}]
        events += [{'type': 'stream_event', 'event': {'type': 'message_delta',
                    'delta': {'stop_reason': stop}, 'usage': {'output_tokens': 20}}}]
        terminal_text = '{"answer":false}'
        terminal = {'type': 'result', 'subtype': 'error_during_execution' if refused else 'success',
                    'session_id': session, 'is_error': refused, 'stop_reason': stop, 'result': terminal_text,
                    'total_cost_usd': .01, 'num_turns': 1, 'usage': {'output_tokens': 20},
                    'modelUsage': {audit.MODEL: {'canonicalModel': audit.MODEL, 'provider': 'firstParty'}},
                    'subagent_stats': deepcopy(audit.ZERO_STATS)}
        events += [terminal]
        stdout, stderr = root / 'native.jsonl', root / 'native.stderr'
        stdout.write_text('\n'.join(json.dumps(e) for e in events) + '\n')
        stderr.write_text('PRIVATE_STDERR_SENTINEL')
        record = {'packet_id': 'synthetic-packet', 'session_id': session,
            'stdout_path': stdout.name, 'stderr_path': stderr.name,
            'stdout_sha256': audit.file_sha(stdout), 'stderr_sha256': audit.file_sha(stderr),
            'exit_code': 0, 'timed_out': False,
            'init': {key: init.get(key) for key in ('model', 'tools', 'mcp_servers', 'skills', 'plugins', 'permissionMode')},
            'messages': {mid: {'model': audit.MODEL, 'usage': {'output_tokens': 20}, 'stop_reason': stop}},
            'distinct_observed_message_count': 1, 'requesting_status_count': 0,
            'provider_refusals': refusals, 'local_error_records': locals_, 'recovery_markers': [],
            'observed_models': [audit.MODEL], 'model_usage': terminal['modelUsage'],
            'subagent_statistics': [{'field': 'subagent_stats', 'counts': deepcopy(audit.ZERO_STATS)}],
            'native_cost_usd': '0.01', 'usage': terminal['usage'],
            'native_subtype': terminal['subtype'], 'native_is_error': refused, 'native_stop_reason': stop,
            'terminal_session_id': session, 'num_turns': 1, 'terminal_text_sha256': audit.sha(terminal_text.encode()),
            'native_acceptable': not refused, 'issues': issues, 'answer': None if refused else False,
            'parse_failure': None}
        return record

    def test_native_success_and_local_refusal_preserve_custody_without_text(self):
        for refused in (False, True):
            with self.subTest(refused=refused), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                record = self.native_case(root, refused)
                with mock.patch.object(audit, 'ROOT', root):
                    checked = audit.check_raw(record)
                    self.assertEqual(checked['provider_message_count'], 1)
                    self.assertEqual(checked['native_acceptable'], not refused)
                    self.assertNotIn('PRIVATE_', json.dumps(checked))
                    self.assertEqual(audit.check_raw(record, public_only=True)['status'], 'unavailable')
                    record['messages']['synthetic-provider-id']['usage']['output_tokens'] = 0
                    with self.assertRaises(ValueError):
                        audit.check_raw(record)

    def test_typed_telemetry_rejects_bool_and_unknown_keys(self):
        invalid = deepcopy(audit.ZERO_STATS)
        invalid['spawned'] = False
        self.assertFalse(audit.typed_shape(invalid, audit.ZERO_STATS))
        invalid = dict(audit.ZERO_STATS, unknown=0)
        self.assertFalse(audit.typed_shape(invalid, audit.ZERO_STATS))


if __name__ == '__main__':
    unittest.main()
