"""Independent synthetic cycle10 regressions; never construct the actual A2/B3 panel."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    'cycle10_audit_test', Path(__file__).resolve().parents[1] / 'check_cycle10_evidence.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def synthetic_fixture():
    """Hand-derived A=-2,B=5 states, cyclic orders and reference decisions."""
    fixture = {'schema_version': 1,
        'generation': {'parameters': {'A': -2, 'B': 5}, 'program_count': 2,
            'root_certificate_count': 6, 'packet_count': 6, 'rng_used': False,
            'candidate_attempts': 1, 'exclusions': []},
        'programs': [], 'packets': [], 'reference_policies': {},
        'request_order': ['R0-P1', 'R1-P2', 'R0-P3', 'R1-P1', 'R0-P2', 'R1-P3']}
    for residue in (0, 1):
        pid = f'R{residue}'
        source = ('a = -2\nb = 5\na = a + b\nb = a - b\na = a + b\n'
                  f'result = (a % 2 == {residue})\n')
        states = [{'a': -2}, {'a': -2, 'b': 5}, {'a': 3, 'b': 5}, {'a': 3, 'b': -2},
                  {'a': 1, 'b': -2}, {'a': 1, 'b': -2, 'result': residue == 1}]
        certs = {'V': {'rows': [{'step': i, 'state': state} for i, state in enumerate(states, 1)]}}
        certs['I'] = deepcopy(certs['V'])
        for i, state in enumerate([{'a': 4, 'b': 5}, {'a': 4, 'b': -1}, {'a': 3, 'b': -1},
                                   {'a': 3, 'b': -1, 'result': residue == 1}], 2):
            certs['I']['rows'][i]['state'] = state
        certs['F'] = deepcopy(certs['V'])
        certs['F']['rows'][-1]['state']['result'] = residue == 0
        ids = {label: 'r_' + hashlib.sha256(b'cycle10-certificate\n' + audit.canonical(
            {'program': source, 'certificate': cert}).encode()).hexdigest()[:16] for label, cert in certs.items()}
        reports = {label: {'report_id': ids[label], 'root_id': ids[label], 'certificate': cert}
                   for label, cert in certs.items()}
        fixture['programs'].append({'program_id': pid, 'parameters': {'A': -2, 'B': 5, 'R': residue},
            'program': source, 'program_sha256': audit.sha(source.encode()),
            'python_truth': audit.truth.evaluate_program(source), 'certificates': certs,
            'certificate_checks': {label: audit.truth.check_certificate(source, cert) for label, cert in certs.items()},
            'certificate_sha256': {label: audit.sha(audit.canonical(cert).encode()) for label, cert in certs.items()},
            'report_ids': ids, 'report_sha256': {label: audit.sha(audit.canonical(report).encode())
                                               for label, report in reports.items()}})
        for order_name, order in [('P1', ['V', 'I', 'F']), ('P2', ['F', 'V', 'I']), ('P3', ['I', 'F', 'V'])]:
            packet_id = pid + '-' + order_name
            text = audit.canonical({'program': source, 'original_ids': [ids[label] for label in order],
                                    'reports': [reports[label] for label in order] + [None, None]})
            fixture['packets'].append({'packet_id': packet_id, 'program_id': pid, 'private_order': order,
                'payload': text, 'payload_sha256': audit.sha(text.encode()), 'payload_bytes': len(text.encode())})
            policies = {}
            for name in ('exact_checker', 'always_valid', 'always_invalid', 'position_1', 'position_2',
                         'position_3', 'endpoint_matches_truth', 'endpoint_boolean'):
                if name == 'exact_checker':
                    chosen = {'V'}
                elif name == 'always_valid':
                    chosen = {'V', 'I', 'F'}
                elif name == 'always_invalid':
                    chosen = set()
                elif name.startswith('position_'):
                    chosen = {order[int(name[-1]) - 1]}
                elif name == 'endpoint_matches_truth':
                    chosen = {'V', 'I'}
                else:
                    chosen = {'V', 'I'} if residue == 1 else {'F'}
                policies[name] = {'decisions': {ids[label]: label in chosen for label in order},
                    'correct': sum((label in chosen) == (label == 'V') for label in order), 'valid': 3, 'planned': 3}
            fixture['reference_policies'][packet_id] = policies
    counts = {'exact_checker': 18, 'always_valid': 6, 'always_invalid': 12, 'position_1': 10,
              'position_2': 10, 'position_3': 10, 'endpoint_matches_truth': 12, 'endpoint_boolean': 9}
    fixture['policy_totals'] = {name: {'correct': n, 'valid': 18, 'planned': 18,
        'vector_differs_from_exact': name != 'exact_checker'} for name, n in counts.items()}
    fixture['audit'] = {'r_complement_verified': True, 'position_endpoint_balance': True,
        'root_and_report_identity_verified': True, 'heuristic_vectors_distinct_from_exact': True,
        'payload_byte_lengths': {p['packet_id']: p['payload_bytes'] for p in fixture['packets']}}
    return fixture


class Cycle10AuditTests(unittest.TestCase):
    def test_hand_derived_synthetic_panel_and_reference_scores(self):
        result = audit.verify_fixture(synthetic_fixture())
        self.assertEqual(result['reference_policy_correct'], {'exact_checker': 18, 'always_valid': 6,
            'always_invalid': 12, 'position_1': 10, 'position_2': 10, 'position_3': 10,
            'endpoint_matches_truth': 12, 'endpoint_boolean': 9})
        self.assertEqual(result['first_invalid_step'], {'V': None, 'I': 3, 'F': 6})
        self.assertEqual(result['distinct_programs'], 2)
        self.assertFalse(result['empirical_launch_authorized'])

    def test_hash_requires_real_prefix_newline_and_canonical_terminal_newline(self):
        program = synthetic_fixture()['programs'][0]
        cert = program['certificates']['I']
        message = audit.canonical({'program': program['program'], 'certificate': cert}).encode()
        actual = audit.certificate_id(program['program'], cert)
        self.assertEqual(actual, program['report_ids']['I'])
        for wrong in (b'cycle10-certificate\\n' + message, b'cycle10-certificate\n' + message[:-1]):
            self.assertNotEqual(actual, 'r_' + hashlib.sha256(wrong).hexdigest()[:16])

    def test_rehashed_packet_corruptions_do_not_escape_content_checks(self):
        def metadata(payload):
            payload['reports'][0]['expected_valid'] = True
        def copy(payload):
            payload['reports'][4] = deepcopy(payload['reports'][2])
        def order(payload):
            payload['original_ids'].reverse()
        def root(payload):
            payload['reports'][0]['root_id'] = payload['reports'][1]['root_id']
        def unchanged(payload):
            payload['reports'][0]['certificate']['rows'][2]['state']['b'] += 1
        for mutation in (metadata, copy, order, root, unchanged):
            with self.subTest(mutation=mutation.__name__):
                fixture = synthetic_fixture()
                packet = fixture['packets'][0]
                payload = audit.parse_json(packet['payload'])
                mutation(payload)
                packet['payload'] = audit.canonical(payload)
                packet['payload_sha256'] = audit.sha(packet['payload'].encode())
                packet['payload_bytes'] = len(packet['payload'].encode())
                with self.assertRaises(ValueError):
                    audit.verify_fixture(fixture)

    def test_full_rows_exact_types_and_invalid_propagation_are_checked(self):
        for label, row, key, value in [('I', 3, 'b', -2), ('V', 2, 'a', True),
                                        ('V', 5, 'result', 0), ('V', 2, 'b', 4)]:
            with self.subTest(label=label, row=row, key=key):
                fixture = synthetic_fixture()
                fixture['programs'][0]['certificates'][label]['rows'][row]['state'][key] = value
                with self.assertRaises(ValueError):
                    audit.verify_fixture(fixture)

    def test_tampered_reference_vector_cannot_hide_behind_correct_total(self):
        fixture = synthetic_fixture()
        packet = fixture['reference_policies']['R0-P1']
        decisions = packet['endpoint_matches_truth']['decisions']
        ids = fixture['programs'][0]['report_ids']
        decisions[ids['I']], decisions[ids['F']] = False, True
        with self.assertRaisesRegex(ValueError, 'reference vectors'):
            audit.verify_fixture(fixture)

    def test_complement_generation_order_and_collision_fail_closed(self):
        fixture = synthetic_fixture()
        with mock.patch.object(audit, 'certificate_id', return_value='r_' + '0' * 16):
            with self.assertRaises(ValueError):
                audit.verify_fixture(fixture)
        variants = []
        copy = deepcopy(fixture); copy['programs'][1]['parameters']['R'] = 0; variants.append(copy)
        copy = deepcopy(fixture); copy['generation']['rng_used'] = True; variants.append(copy)
        copy = deepcopy(fixture); copy['request_order'].reverse(); variants.append(copy)
        copy = deepcopy(fixture); copy['schema_version'] = True; variants.append(copy)
        for corrupted in variants:
            with self.assertRaises(ValueError):
                audit.verify_fixture(corrupted)

    def test_run_checks_artifact_bytes_and_rejects_synthetic_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = root / 'prepared'
            prepared.mkdir()
            sources = {}
            for name in audit.SOURCE_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'synthetic source\n')
                sources[name] = audit.file_sha(path)
            names = {'fixture.json', 'independent-check.json', 'cases.md'}
            names.update(f'programs/R{r}.py' for r in (0, 1))
            names.update(f'certificates/R{r}-{label}.json' for r in (0, 1) for label in ('V', 'I', 'F'))
            names.update('packets/' + pid + '.json' for pid in audit.REQUEST_ORDER)
            for name in names:
                path = prepared / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(audit.canonical(synthetic_fixture()).encode() if name == 'fixture.json'
                                 else b'synthetic artifact\n')
            manifest = {'source_sha256_start': sources, 'source_sha256_end': sources,
                        'empirical_launch_authorized': False,
                        'artifact_sha256': {name: audit.file_sha(prepared / name) for name in names}}
            (prepared / 'manifest.json').write_text(audit.canonical(manifest))
            with mock.patch.object(audit, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'actual fixed constants'):
                    audit.run(prepared)
                (prepared / 'packets/R0-P1.json').write_bytes(b'counterfeit\n')
                with self.assertRaisesRegex(ValueError, 'sealed artifact packets/R0-P1.json'):
                    audit.run(prepared)


if __name__ == '__main__':
    unittest.main()
