"""Synthetic cycle09 audit regressions; actual candidate and ID RNGs stay mocked."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest import mock


PATH = Path(__file__).resolve().parents[1] / 'check_cycle09_evidence.py'
SPEC = importlib.util.spec_from_file_location('cycle09_audit_under_test', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
SOURCE = '''a = -2
b = 3
a = a + b
b = a - b
a = a + b
result = (a % 2 == 1)
'''


class CertificateTests(unittest.TestCase):
    def test_hand_derived_negative_initial_trace(self):
        actual = audit.evaluate_program(SOURCE)
        states = [{'a': -2}, {'a': -2, 'b': 3}, {'a': 1, 'b': 3}, {'a': 1, 'b': -2},
                  {'a': -1, 'b': -2}, {'a': -1, 'b': -2, 'result': True}]
        self.assertEqual(actual['rows'], [{'step': step, 'state': state} for step, state in enumerate(states, 1)])
        self.assertEqual(actual['max_abs_intermediate'], 3)
        self.assertEqual(actual['executed_statements'], 6)
        self.assertIs(actual['answer'], True)

    def test_corruptions_have_only_the_prescribed_local_invalid_row(self):
        certs = audit.reconstruct_certificates(SOURCE)
        checked = {label: audit.check_certificate(SOURCE, cert) for label, cert in certs.items()}
        self.assertEqual({label: row['first_invalid_step'] for label, row in checked.items()},
                         {'V': None, 'I': 3, 'F': 6})
        self.assertEqual([row['valid'] for row in checked['I']['transitions']], [True, True, False, True, True, True])
        self.assertEqual(certs['I']['rows'][4]['state'], {'a': 1, 'b': -1})
        self.assertIs(certs['I']['rows'][5]['state']['result'], True)
        self.assertIs(certs['F']['rows'][5]['state']['result'], False)
        maximum = audit.reconstruct_certificates(SOURCE.replace('a = -2', 'a = 9').replace('b = 3', 'b = 9'))
        self.assertEqual(maximum['I']['rows'][4]['state']['a'], 29)

    def test_unchanged_variable_corruption_is_detected_at_that_row(self):
        cert = audit.reconstruct_certificates(SOURCE)['V']
        cert['rows'][2]['state']['b'] = 4
        checked = audit.check_certificate(SOURCE, cert)
        self.assertEqual(checked['first_invalid_step'], 3)
        self.assertEqual(checked['transitions'][2]['expected_state'], {'a': 1, 'b': 3})
        self.assertFalse(checked['transitions'][2]['valid'])

    def test_malformed_schema_is_rejected_separately(self):
        valid = audit.reconstruct_certificates(SOURCE)['V']
        variants = []
        cert = deepcopy(valid); cert['rows'][2]['state']['a'] = True; variants.append(cert)
        cert = deepcopy(valid); cert['rows'][0]['step'] = True; variants.append(cert)
        cert = deepcopy(valid); cert['rows'][5]['state']['result'] = 1; variants.append(cert)
        cert = deepcopy(valid); del cert['rows'][3]['state']['b']; variants.append(cert)
        cert = deepcopy(valid); cert['rows'][0]['state']['b'] = 3; variants.append(cert)
        cert = deepcopy(valid); cert['rows'][0]['state']['a'] = 101; variants.append(cert)
        cert = deepcopy(valid); cert['rows'].append(cert['rows'][-1]); variants.append(cert)
        for cert in variants:
            with self.subTest(certificate=cert), self.assertRaises(ValueError):
                audit.check_certificate(SOURCE, cert)
        for text in ('{"rows":[],"rows":[]}', '{"value":NaN}', '{"value":Infinity}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                audit.parse_json(text)

    def test_exact_signed_literal_and_whole_program_allowlist(self):
        for before, after in [('a = -2', 'a = -(1 + 1)'), ('a = -2', 'a = --2'),
            ('a = -2', 'a = True'), ('a = -2', 'a = -10'), ('b = 3', 'b = abs(a)'),
            ('a = a + b', 'a = a * b'), ('b = a - b', 'import os'),
            ('a % 2 == 1', 'a % 2 != 1'), ('a % 2 == 1', 'a % 3 == 1'),
            ('a = -2\nb = 3', 'a = -2; b = 3')]:
            with self.subTest(replacement=after), self.assertRaises(ValueError):
                audit.evaluate_program(SOURCE.replace(before, after))


class FixtureTests(unittest.TestCase):
    def fixture(self):
        order, ids = ['I', 'F', 'V'], [f'r_{index:016x}' for index in range(1, 6)]
        certs = audit.reconstruct_certificates(SOURCE)
        checks = {label: audit.check_certificate(SOURCE, cert) for label, cert in certs.items()}
        originals = [{'report_id': rid, 'root_id': rid, 'certificate': certs[label]}
                     for rid, label in zip(ids[:3], order)]
        copies = [{'report_id': rid, 'root_id': ids[1], 'certificate': certs['F']} for rid in ids[3:]]
        packets = []
        for name, tail in (('base', [None, None]), ('repeat', copies)):
            text = audit.canonical({'program': SOURCE, 'original_ids': ids[:3], 'reports': originals + tail})
            packets.append({'packet_id': name, 'payload': text, 'payload_sha256': audit.sha(text.encode())})
        policies = audit.reference_policies(ids[:3], {r['report_id']: r['certificate'] for r in originals}, SOURCE)
        return {'schema_version': 1, 'program': SOURCE, 'program_sha256': audit.sha(SOURCE.encode()),
            'generation': {'parameter_seed': 420009, 'identity_seed': 420010,
                'parameters': {'A': -2, 'B': 3, 'R': 1}, 'private_order': order,
                'report_ids': ids, 'candidate_attempts': 1, 'exclusions': []},
            'python_truth': audit.evaluate_program(SOURCE), 'certificates': certs, 'certificate_checks': checks,
            'certificate_sha256': {label: audit.sha(audit.canonical(cert).encode()) for label, cert in certs.items()},
            'packets': packets, 'reference_policies': {'base': policies, 'repeat': policies},
            'negative_control': {'whole_certificate_validity': {'V': True, 'I': False, 'F': False},
                'first_invalid_step': {'V': None, 'I': 3, 'F': 6},
                'final_answers': {'V': True, 'I': True, 'F': False}, 'I_final_a_delta': 2,
                'I_parity_preserved': True, 'F_answer_flipped': True}}

    def verify(self, fixture, collision=False):
        parameters, identifiers = mock.Mock(), mock.Mock()
        parameters.randint.side_effect = [-2, 3]
        parameters.randrange.return_value = 1
        identifiers.shuffle.side_effect = lambda order: order.__setitem__(slice(None), ['I', 'F', 'V'])
        identifiers.getrandbits.side_effect = [1] * 5 if collision else [1, 2, 3, 4, 5]
        with mock.patch.object(audit.random, 'Random', side_effect=[parameters, identifiers]):
            return audit.verify_fixture(fixture)

    def test_mocked_complete_fixture_and_policy_denominators(self):
        checked = self.verify(self.fixture())
        self.assertEqual(checked['reference_policy_correct_per_packet'],
                         {'always_valid': 1, 'always_invalid': 2, 'exact_checker': 3})
        self.assertEqual(checked['reference_policy_correct_across_two_packets'],
                         {'always_valid': 2, 'always_invalid': 4, 'exact_checker': 6})
        self.assertEqual(checked['distinct_original_certificates'], 3)
        self.assertFalse(checked['empirical_launch_authorized'])

    def test_counterfeit_copy_is_rejected_even_with_a_fresh_hash(self):
        fixture = self.fixture()
        packet = fixture['packets'][1]
        payload = audit.parse_json(packet['payload'])
        payload['reports'][4]['certificate'] = deepcopy(fixture['certificates']['I'])
        packet['payload'] = audit.canonical(payload)
        packet['payload_sha256'] = audit.sha(packet['payload'].encode())
        with self.assertRaises(ValueError):
            self.verify(fixture)

    def test_id_collision_and_injected_metadata_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'collision'):
            self.verify({}, collision=True)
        fixture = self.fixture()
        packet = fixture['packets'][0]
        payload = audit.parse_json(packet['payload'])
        payload['reports'][0]['valid'] = False
        packet['payload'] = audit.canonical(payload)
        packet['payload_sha256'] = audit.sha(packet['payload'].encode())
        with self.assertRaises(ValueError):
            self.verify(fixture)


if __name__ == '__main__':
    unittest.main()
