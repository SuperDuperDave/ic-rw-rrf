"""Cycle07 safety, finite-panel semantics and prepared-custody regressions."""
import ast
from collections import Counter
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle07_program_errors as programs


SEQUENTIAL = """a = -8
b = 2
c = 3
a = a - b
b = (a + c) % 5
c = c + b
a = a + c
result = (a % 3 == 2)
"""
LOOP = """a = -8
b = 2
c = 3
for i in range(3):
    a = a + b
    if a < 0:
        b = b + 1
    c = (c + a) % 7
a = (a + b) + c
result = (a % 3 == 0)
"""


class BooleanParserTests(unittest.TestCase):
    def test_real_booleans_and_json_whitespace(self):
        self.assertIs(programs.parse_answer('  {"answer":false}\n'), False)
        self.assertIs(programs.parse_answer('{"answer": true}'), True)

    def test_reject_nonboolean_values(self):
        for value in ('0', '1', '"true"', 'null', '[]', '{}', '0.0'):
            with self.subTest(value=value), self.assertRaises(programs.AnswerParseError) as error:
                programs.parse_answer('{"answer":' + value + '}')
            self.assertEqual(error.exception.code, 'not_boolean')

    def test_duplicate_extra_missing_keys(self):
        for text, code in (
            ('{"answer":true,"answer":false}', 'duplicate_key'),
            ('{"answer":true,"reason":"x"}', 'keys'), ('{}', 'keys'),
            ('[]', 'not_object'), ('null', 'not_object'),
            ('{"answer":NaN}', 'nonfinite'), ('{"answer":Infinity}', 'nonfinite')):
            with self.subTest(text=text), self.assertRaises(programs.AnswerParseError) as error:
                programs.parse_answer(text)
            self.assertEqual(error.exception.code, code)

    def test_prose_fences_multiple_objects_and_nontext(self):
        for text in ('\x60\x60\x60json\n{"answer":true}\n\x60\x60\x60',
                     'Answer: {"answer":true}', '{"answer":true}{"answer":false}',
                     '{"answer":True}', ''):
            with self.subTest(text=text), self.assertRaises(programs.AnswerParseError):
                programs.parse_answer(text)
        with self.assertRaises(programs.AnswerParseError) as error:
            programs.parse_answer({'answer': True})
        self.assertEqual(error.exception.code, 'not_text')


class ProgramSafetyTests(unittest.TestCase):
    def test_python_signed_modulo_and_final_state(self):
        result = programs.python_truth(SEQUENTIAL)
        self.assertEqual(result['final_state'], {'a': -4, 'b': 3, 'c': 6})
        self.assertIs(result['answer'], True)
        self.assertEqual(result['executed_statements'], 8)
        self.assertEqual(result['max_abs_intermediate'], 10)
        self.assertEqual(result['ast_dump'], ast.dump(ast.parse(SEQUENTIAL), include_attributes=False))

    def test_loop_header_and_branch_visit_counts(self):
        result = programs.python_truth(LOOP)
        self.assertEqual(result['final_state'], {'a': 7, 'b': 4, 'c': 2, 'i': 2})
        self.assertIs(result['answer'], False)
        # 3 init + 4 header + (4+4+3) body + 2 final assignments.
        self.assertEqual(result['executed_statements'], 20)
        self.assertEqual(result['worst_case_executed_statements'], 21)

    def test_illegal_ast_is_rejected_before_any_exec(self):
        variants = (
            SEQUENTIAL.replace('b = 2', 'b = True'),
            SEQUENTIAL.replace('b = 2', 'b = abs(-2)'),
            SEQUENTIAL.replace('b = 2', 'import os'),
            SEQUENTIAL.replace('b = 2', 'b = a.real'),
            SEQUENTIAL.replace('a = a - b', 'a = a ** b'),
            SEQUENTIAL.replace('% 5', '% 0'),
            SEQUENTIAL.replace('% 5', '% b'),
            SEQUENTIAL.replace('b = 2', 'b = c + 2'),
            SEQUENTIAL.replace('b = 2', 'b = 1000001'),
            SEQUENTIAL.replace('b = 2', 'b = c = 2'),
            SEQUENTIAL.replace('b = 2', 'b += 2'),
            LOOP.replace('range(3)', 'range(1000000)'),
            LOOP.replace('range(3)', 'range(c)'),
            LOOP.replace('for i in range(3):', 'while a < 0:'),
            LOOP.replace('b = b + 1', 'b = __import__("os")'),
        )
        for source in variants:
            with self.subTest(source=source), patch('builtins.exec') as execute:
                with self.assertRaises(ValueError):
                    programs.python_truth(source)
                execute.assert_not_called()

    def test_final_predicate_is_fixed(self):
        for replacement in ('a % 4 == 2', 'a % 3 == 3', 'a % 3 != 2',
                            'b % 3 == 2', 'a % 3 == True'):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                programs.python_truth(SEQUENTIAL.replace('a % 3 == 2', replacement))

    def test_unreachable_bad_branch_still_rejected(self):
        source = LOOP.replace('if a < 0:', 'if a > 100:').replace('b = b + 1', 'b = open("x")')
        with patch('builtins.exec') as execute, self.assertRaises(ValueError):
            programs.python_truth(source)
        execute.assert_not_called()

    def test_intermediate_bound_even_when_later_modulo_is_small(self):
        source = SEQUENTIAL.replace('a = -8', 'a = 1000000').replace('a = a - b', 'a = (a * b) % 3')
        with self.assertRaisesRegex(ValueError, 'intermediate_magnitude_bound'):
            programs.python_truth(source)

    def test_nested_conditionals_else_and_excess_lines_rejected(self):
        variants = (LOOP.replace('    c = (c + a) % 7', '    else:\n        c = 2'),
                    LOOP.replace('        b = b + 1', '        if b > 0:\n            b = b + 1'),
                    SEQUENTIAL + 'a = 1\n',
                    SEQUENTIAL.replace('b = 2\n', 'b = 2; c = 1\n'))
        for source in variants:
            with self.subTest(source=source), self.assertRaises(ValueError):
                programs.python_truth(source)

    def test_normalization_blocks_parameters_renames_complements(self):
        reference = programs.normalized_template(SEQUENTIAL)
        renamed = SEQUENTIAL.replace('a', 'x').replace('b', 'y').replace('c', 'z')
        changed = SEQUENTIAL.replace('-8', '7').replace('% 5', '% 11')
        complemented = SEQUENTIAL.replace('a % 3 == 2', 'a % 3 != 2')
        for source in (renamed, changed, complemented):
            self.assertEqual(programs.normalized_template(source), reference)
        self.assertNotEqual(programs.normalized_template(
            SEQUENTIAL.replace('a = a - b', 'a = a + b')), reference)


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = programs.build_fixture()

    def test_deterministic_balanced_distinct_splits(self):
        self.assertEqual(self.fixture, programs.build_fixture())
        counts = Counter((item['stratum'], item['truth'], item['split'])
                         for item in self.fixture['items'])
        for stratum, truth in programs.CELLS:
            self.assertEqual(counts[stratum, truth, 'development'], 2)
            self.assertEqual(counts[stratum, truth, 'reserved'], 4)
        self.assertEqual(len({item['template_hash'] for item in self.fixture['items']}), 24)
        self.assertEqual(self.fixture['generation']['attempt_count'], 48)
        self.assertEqual(self.fixture['generation']['exclusion_counts'], {'cell_full': 24})

    def test_candidates_audited_and_first_accepted_policy(self):
        counts, accepted = Counter(), set()
        for candidate in self.fixture['generation']['candidates']:
            self.assertEqual(candidate['program_sha256'],
                             programs.sha256_bytes(candidate['program'].encode()))
            cell = candidate['stratum'], candidate['truth']
            if candidate['status'] == 'accepted':
                self.assertLess(counts[cell], 6)
                self.assertNotIn(candidate['template_hash'], accepted)
                counts[cell] += 1
                accepted.add(candidate['template_hash'])
            else:
                self.assertEqual(candidate['reason'], 'cell_full')
                self.assertEqual(counts[cell], 6)
        self.assertEqual(set(counts.values()), {6})

    def test_payload_exact_keys_and_truth_separation(self):
        by_item = {item['item_id']: item for item in self.fixture['items']}
        for packet in self.fixture['packets']:
            payload = json.loads(packet['payload'])
            self.assertEqual(set(payload), {'program', 'role_instruction'})
            self.assertEqual(programs.validate_payload(payload), payload)
            self.assertEqual(payload['program'], by_item[packet['item_id']]['program'])
            self.assertEqual(by_item[packet['item_id']]['split'], 'development')
            self.assertEqual(programs.sha256_bytes(packet['payload'].encode()), packet['payload_sha256'])
            for key in ('truth', 'item_id', 'split', 'other_answer'):
                with self.assertRaises(ValueError):
                    programs.validate_payload({**payload, key: True})

    def test_adjacent_roles_and_counterbalanced_first_role(self):
        packets = {p['packet_id']: p for p in self.fixture['packets']}
        items = {i['item_id']: i for i in self.fixture['items']}
        firsts = Counter()
        for index in range(0, 16, 2):
            first, second = [packets[pid] for pid in self.fixture['request_order'][index:index+2]]
            self.assertEqual(first['item_id'], second['item_id'])
            self.assertEqual({first['role'], second['role']}, {'G', 'S'})
            item = items[first['item_id']]
            firsts[item['stratum'], item['truth'], first['role']] += 1
        self.assertEqual(set(firsts.values()), {1})
        self.assertEqual(len(firsts), 8)

    def test_fixture_mutation_cannot_change_truth_or_split(self):
        for field, value in (('truth', None), ('split', 'reserved'), ('program', SEQUENTIAL)):
            fixture = copy.deepcopy(self.fixture)
            item = next(item for item in fixture['items'] if item['split'] == 'development')
            item[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                programs.validate_fixture(fixture)


class JointScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = programs.build_fixture()

    def answers_for_errors(self, errors):
        items = {item['item_id']: item for item in self.fixture['items']}
        return {p['packet_id']: items[p['item_id']]['truth'] ^ errors[p['item_id']][p['role'] == 'S']
                for p in self.fixture['packets']}

    def test_all_truth_error_cells_have_named_denominators(self):
        items = [item for item in self.fixture['items'] if item['split'] == 'development']
        errors = {}
        for truth in (False, True):
            selected = [item for item in items if item['truth'] is truth]
            for item, pattern in zip(selected,
                                     ((False, False), (False, True), (True, False), (True, True))):
                errors[item['item_id']] = pattern
        result = programs.score_answers(self.fixture, self.answers_for_errors(errors))
        table = result['primary']
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(table['N'], 8)
        self.assertEqual(table['cells'], {'00': 2, '01': 2, '10': 2, '11': 2})
        for truth in ('false', 'true'):
            self.assertEqual(table['by_truth'][truth]['N'], 4)
            self.assertEqual(table['by_truth'][truth]['cells'], {'00': 1, '01': 1, '10': 1, '11': 1})
            self.assertEqual(table['by_truth'][truth]['joint_error_excess'],
                             {'numerator': 0, 'denominator': 16, 'value': 0.0})
        for key in ('g_error', 's_error', 'disagreement', 'conditional_correction', 'conditional_harm'):
            self.assertEqual(table[key]['value'], .5)
        self.assertEqual(table['s_minus_g_error']['value'], 0)
        self.assertTrue(result['observability_gate']['passed'])

    def test_partial_false_unpaired_invalid_and_unsent_distinct(self):
        order = self.fixture['request_order']
        result = programs.score_answers(self.fixture, {pid: False for pid in order[:3]},
                                        {order[3]: 'not_boolean'})
        self.assertIsNone(result['primary'])
        self.assertEqual(result['partial_valid_pair_table']['N'], 1)
        self.assertEqual(result['coverage'], {'planned_items': 8, 'planned_invocations': 16,
            'valid_pairs': 1, 'valid_answers': 3, 'invalid_answers': 1, 'unsent': 12,
            'valid_unpaired_answers': 1})
        self.assertFalse(result['observability_gate']['passed'])

    def test_empty_panel_zeros_and_null_zero_denominators(self):
        result = programs.score_answers(self.fixture, {})
        table = result['partial_valid_pair_table']
        self.assertEqual(table['cells'], {'00': 0, '01': 0, '10': 0, '11': 0})
        self.assertEqual(table['g_error'], {'numerator': 0, 'denominator': 0, 'value': None})
        for truth in ('false', 'true'):
            self.assertEqual(table['by_truth'][truth]['joint_error_excess'],
                             {'numerator': 0, 'denominator': 0, 'value': None})

    def test_perfect_panel_is_valid_gate_failure(self):
        errors = {item_id: (False, False) for item_id in self.fixture['item_order']}
        result = programs.score_answers(self.fixture, self.answers_for_errors(errors))
        self.assertEqual(result['status'], 'complete')
        self.assertFalse(result['observability_gate']['passed'])
        self.assertEqual(result['primary']['conditional_correction']['denominator'], 0)
        self.assertIsNone(result['primary']['conditional_correction']['value'])

    def test_gate_does_not_require_correct_dissent(self):
        order = self.fixture['item_order']
        errors = {item_id: (False, False) for item_id in order}
        errors[order[0]], errors[order[1]] = (True, True), (False, True)
        result = programs.score_answers(self.fixture, self.answers_for_errors(errors))
        self.assertTrue(result['observability_gate']['passed'])
        self.assertEqual(result['observability_gate']['counts']['correct_dissent'], 0)
        self.assertEqual(result['primary']['s_minus_g_error'],
                         {'numerator': 1, 'denominator': 8, 'value': .125})

    def test_invalid_mapping_inputs_rejected(self):
        pid = self.fixture['request_order'][0]
        for answers, failures in (({pid: 0}, {}), ({'unknown': False}, {}),
                                  ({pid: False}, {pid: 'invalid'}), ({}, {pid: None})):
            with self.subTest(answers=answers, failures=failures), self.assertRaises(ValueError):
                programs.score_answers(self.fixture, answers, failures)


class CustodyTests(unittest.TestCase):
    def test_prepare_roundtrip_and_payload_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared = Path(directory) / 'prepared'
            manifest = programs.prepare_fixture(prepared, ['unit-test', 'prepare'])
            digest = programs.sha256_bytes((prepared / 'manifest.json').read_bytes())
            fixture, recovered = programs.validate_fixture_custody(prepared, digest)
            self.assertEqual(recovered, manifest)
            self.assertEqual(len(fixture['items']), 24)
            with self.assertRaises(FileExistsError):
                programs.prepare_fixture(prepared)
            packet = fixture['packets'][0]
            path = prepared / 'payloads' / (packet['packet_id'] + '.json')
            path.write_text(path.read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'artifact hash'):
                programs.validate_fixture_custody(prepared, digest)

    def test_prepared_manifest_identity_when_supplied(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared = Path(directory) / 'prepared'
            programs.prepare_fixture(prepared)
            with self.assertRaisesRegex(ValueError, 'manifest hash'):
                programs.validate_fixture_custody(prepared, '0' * 64)


if __name__ == '__main__':
    unittest.main()
