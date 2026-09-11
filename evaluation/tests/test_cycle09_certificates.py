"""Synthetic certificate regressions; actual frozen seeds are never drawn here."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

from evaluation import cycle09_certificates as m


PARAMETERS = {'A': -3, 'B': 4, 'R': 1}
ORDER = ['F', 'V', 'I']
IDS = ['r_' + f'{i:016x}' for i in range(5)]


def synthetic_fixture():
    return m.construct_fixture(PARAMETERS, ORDER, IDS)


class TruthTests(unittest.TestCase):
    def test_signed_initial_execution_is_hand_checked(self):
        truth = m.python_truth(m.render_program(PARAMETERS))
        states = [{'a': -3}, {'a': -3, 'b': 4}, {'a': 1, 'b': 4},
                  {'a': 1, 'b': -3}, {'a': -2, 'b': -3},
                  {'a': -2, 'b': -3, 'result': False}]
        self.assertEqual(truth['rows'], [{'step': n, 'state': state} for n, state in enumerate(states, 1)])
        self.assertEqual(truth['final_state'], states[-1])
        self.assertIs(truth['answer'], False)
        self.assertEqual(truth['executed_statements'], 6)
        self.assertEqual(truth['max_abs_intermediate'], 4)

    def test_full_ast_rejected_before_exec(self):
        source = m.render_program(PARAMETERS)
        variants = (source.replace('a = -3', 'a = -b'),
                    source.replace('a = -3', 'a = -(1 + 2)'),
                    source.replace('a = -3', 'a = True'),
                    source.replace('a = -3', 'a = 10'),
                    source.replace('a = -3', 'a = abs(-3)'),
                    source.replace('b = 4', 'import os'),
                    source.replace('a = a + b', 'a = a * b', 1),
                    source.replace('% 2', '% 0'),
                    source.replace('== 1', '== True'),
                    source.replace('== 1', '== 2'),
                    source + 'a = 1\n')
        for variant in variants:
            with self.subTest(source=variant), patch('builtins.exec') as execute:
                with self.assertRaises(ValueError):
                    m.python_truth(variant)
                execute.assert_not_called()

    def test_integer_bound_in_instrumented_execution(self):
        with patch.object(m, 'MAX_MAGNITUDE', 3), self.assertRaisesRegex(ValueError, 'bound'):
            m.python_truth(m.render_program(PARAMETERS))


class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = synthetic_fixture()

    def test_propagated_I_has_only_one_local_error_and_preserves_answer(self):
        fixture = self.fixture
        checks = fixture['certificate_checks']
        self.assertEqual([checks[k]['valid'] for k in m.LABELS], [True, False, False])
        self.assertEqual([checks[k]['first_invalid_step'] for k in m.LABELS], [None, 3, 6])
        self.assertEqual([row['valid'] for row in checks['I']['transitions']],
                         [True, True, False, True, True, True])
        expected = [{'a': -3}, {'a': -3, 'b': 4}, {'a': 2, 'b': 4},
                    {'a': 2, 'b': -2}, {'a': 0, 'b': -2},
                    {'a': 0, 'b': -2, 'result': False}]
        self.assertEqual([row['state'] for row in fixture['certificates']['I']['rows']], expected)
        self.assertEqual(fixture['negative_control']['I_final_a_delta'], 2)
        self.assertTrue(fixture['negative_control']['I_parity_preserved'])
        self.assertTrue(fixture['negative_control']['F_answer_flipped'])

    def test_unchanged_variable_corruption_is_detected(self):
        cert = copy.deepcopy(self.fixture['certificates']['V'])
        cert['rows'][2]['state']['b'] = 5
        check = m.check_certificate(self.fixture['program'], cert)
        self.assertFalse(check['valid'])
        self.assertEqual(check['first_invalid_step'], 3)
        self.assertEqual(check['transitions'][2]['expected_state'], {'a': 1, 'b': 4})
        # Row4 is evaluated from the submitted b=5, rather than the reference b=4.
        self.assertEqual(check['transitions'][3]['expected_state'], {'a': 1, 'b': -4})
        self.assertEqual([row['valid'] for row in check['transitions']],
                         [True, True, False, False, True, True])

    def test_full_state_including_unchanged_final_variables_is_checked(self):
        cert = copy.deepcopy(self.fixture['certificates']['V'])
        cert['rows'][5]['state']['b'] += 1
        check = m.check_certificate(self.fixture['program'], cert)
        self.assertFalse(check['valid'])
        self.assertEqual(check['first_invalid_step'], 6)
        self.assertEqual(cert['rows'][5]['state']['result'], self.fixture['python_truth']['answer'])

    def test_boolean_integer_and_complete_state_schema_boundaries(self):
        base = self.fixture['certificates']['V']
        variants = []
        for row, key, value in ((0, 'a', True), (1, 'b', False), (5, 'result', 0), (0, 'a', 101)):
            cert = copy.deepcopy(base)
            cert['rows'][row]['state'][key] = value
            variants.append(cert)
        cert = copy.deepcopy(base)
        cert['rows'][0]['step'] = True
        variants.append(cert)
        cert = copy.deepcopy(base)
        del cert['rows'][2]['state']['b']
        variants.append(cert)
        cert = copy.deepcopy(base)
        cert['rows'][0]['state']['b'] = 4
        variants.append(cert)
        variants.extend([{'rows': base['rows'][:-1]}, {'rows': base['rows'] + [base['rows'][-1]]}])
        for cert in variants:
            with self.subTest(cert=cert), self.assertRaises(ValueError):
                m.check_certificate(self.fixture['program'], cert)

    def test_strict_json_rejects_duplicate_keys_nonfinite_and_extra_text(self):
        source = m.canonical_json(self.fixture['certificates']['V'])
        variants = (source.replace('"a":-3', '"a":-3,"a":-3', 1),
                    source.replace('"a":-3', '"a":NaN', 1), source + '{}',
                    '{"rows":[],"rows":[]}', '\x60\x60\x60json\n' + source + '\x60\x60\x60')
        for text in variants:
            with self.subTest(text=text), self.assertRaises(ValueError):
                m.parse_certificate(text)
        self.assertEqual(m.parse_certificate(source), self.fixture['certificates']['V'])


class PacketAndOrderTests(unittest.TestCase):
    def test_originals_and_whole_certificate_copies_are_identical(self):
        fixture = synthetic_fixture()
        base, repeat = [m.parse_json(p['payload']) for p in fixture['packets']]
        self.assertEqual(base['original_ids'], IDS[:3])
        self.assertEqual(base['reports'][:3], repeat['reports'][:3])
        self.assertEqual(base['reports'][3:], [None, None])
        root = IDS[ORDER.index('F')]
        canonical_false = m.canonical_json(fixture['certificates']['F'])
        for index, copy_report in enumerate(repeat['reports'][3:], 3):
            self.assertEqual(copy_report['root_id'], root)
            self.assertEqual(copy_report['report_id'], IDS[index])
            self.assertEqual(m.canonical_json(copy_report['certificate']), canonical_false)
        for packet in fixture['packets']:
            self.assertTrue(packet['payload'].endswith('\n'))
            self.assertFalse(packet['payload'].endswith('\n\n'))
            self.assertEqual(packet['payload'], m.canonical_json(m.parse_json(packet['payload'])))
            self.assertEqual(packet['payload_sha256'], m.sha256_bytes(packet['payload'].encode()))
            self.assertNotIn('"V"', packet['payload'])
            self.assertNotIn('"I"', packet['payload'])
            self.assertNotIn('"F"', packet['payload'])

    def test_no_incidental_metadata_and_no_false_copy_claim(self):
        repeat = m.parse_json(synthetic_fixture()['packets'][1]['payload'])
        for key in ('validity', 'corruption_location', 'source_path', 'labels'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate_payload({**repeat, key: True})
        changed = copy.deepcopy(repeat)
        changed['reports'][3]['certificate']['rows'][2]['state']['a'] += 1
        with self.assertRaisesRegex(ValueError, 'copied certificate'):
            m.validate_payload(changed)
        changed = copy.deepcopy(repeat)
        changed['reports'][3]['report_id'] = changed['reports'][0]['report_id']
        with self.assertRaisesRegex(ValueError, 'colliding'):
            m.validate_payload(changed)

    def test_reference_policy_denominators(self):
        fixture = synthetic_fixture()
        for packet in ('base', 'repeat'):
            for policy, expected in (('always_valid', 1), ('always_invalid', 2), ('exact_checker', 3)):
                result = fixture['reference_policies'][packet][policy]
                self.assertEqual((result['correct'], result['valid'], result['planned']), (expected, 3, 3))
            self.assertEqual(fixture['reference_policies'][packet]['exact_checker']['decisions'],
                             {IDS[0]: False, IDS[1]: True, IDS[2]: False})

    def test_rng_order_and_format_with_mocks_no_actual_seed_draws(self):
        params = Mock()
        params.randint.side_effect = [-3, 4]
        params.randrange.return_value = 1
        identity = Mock()
        def shuffle(labels):
            self.assertEqual(labels, ['V', 'I', 'F'])
            labels[:] = ORDER
        identity.shuffle.side_effect = shuffle
        identity.getrandbits.side_effect = range(5)
        with patch.object(m.random, 'Random', side_effect=[params, identity]) as random_class:
            fixture = m.build_fixture()
        self.assertEqual(random_class.call_args_list, [call(420009), call(420010)])
        self.assertEqual(params.method_calls, [call.randint(-9, 9), call.randint(-9, 9), call.randrange(2)])
        self.assertEqual(identity.getrandbits.call_args_list, [call(64)] * 5)
        self.assertEqual(fixture['generation']['parameters'], PARAMETERS)
        self.assertEqual(fixture['generation']['report_ids'], IDS)
        self.assertEqual(fixture['generation']['candidate_attempts'], 1)
        self.assertEqual(fixture['generation']['exclusions'], [])

    def test_collision_has_no_replacement_draw(self):
        params = Mock()
        params.randint.side_effect = [-3, 4]
        params.randrange.return_value = 1
        identity = Mock()
        identity.getrandbits.side_effect = [0, 1, 2, 3, 3]
        with patch.object(m.random, 'Random', side_effect=[params, identity]), \
                self.assertRaisesRegex(ValueError, 'collision'):
            m.build_fixture()
        self.assertEqual(identity.getrandbits.call_count, 5)
        self.assertEqual(params.randint.call_count, 2)


class CustodyTests(unittest.TestCase):
    def test_missing_checker_blocks_before_seed_draw(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m, '_source_hashes', return_value={}), \
                patch.object(m, '_load_checker', return_value=SimpleNamespace()), \
                patch.object(m, 'build_fixture') as build:
            with self.assertRaisesRegex(ValueError, 'checker unavailable'):
                m.prepare_fixture(Path(directory) / 'prepared')
            build.assert_not_called()

    def test_roundtrip_and_tamper_with_synthetic_fixture_only(self):
        fixture = synthetic_fixture()
        checker = SimpleNamespace(verify_fixture=lambda value: {'verified': value == fixture})
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m, '_load_checker', return_value=checker), \
                patch.object(m, '_source_hashes', return_value={'synthetic': 'a' * 64}), \
                patch.object(m, 'build_fixture', return_value=fixture) as build, \
                patch.object(m.random, 'Random', side_effect=AssertionError('actual RNG forbidden')):
            prepared = Path(directory) / 'prepared'
            returned, manifest = m.prepare_fixture(prepared, ['synthetic-test'])
            self.assertEqual(returned, fixture)
            digest = m.sha256_bytes((prepared / 'manifest.json').read_bytes())
            recovered, recovered_manifest = m.validate_fixture_custody(prepared, digest)
            self.assertEqual(recovered, fixture)
            self.assertEqual(recovered_manifest, manifest)
            self.assertEqual(build.call_count, 1)
            with self.assertRaises(FileExistsError):
                m.prepare_fixture(prepared)
            with self.assertRaisesRegex(ValueError, 'manifest hash'):
                m.validate_fixture_custody(prepared, '0' * 64)
            payload_file = prepared / 'packets' / 'repeat.json'
            payload_file.write_text(payload_file.read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'artifact hash'):
                m.validate_fixture_custody(prepared, digest)


if __name__ == '__main__':
    unittest.main()
