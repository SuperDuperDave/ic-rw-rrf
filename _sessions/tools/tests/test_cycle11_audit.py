"""Synthetic cycle11 audit regressions; no actual parent preparation or calls."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load('cycle11_audit_test', TOOLS / 'check_cycle11_evidence.py')
parent_test = load('cycle11_synthetic_parent', TOOLS / 'tests/test_cycle10_audit.py')


def synthetic_fixture():
    parent = parent_test.synthetic_fixture()  # Hand-derived A=-2,B=5; no actual cycle11 panel.
    fixture = {'schema_version': 1, 'programs': deepcopy(parent['programs']),
        'parent_custody': {'fixture_sha256': audit.sha(audit.canonical(parent).encode()),
                           'manifest_sha256': None, 'artifact_sha256': {}},
        'generation': {'program_count': 2, 'root_certificate_count': 4, 'packet_count': 4,
            'distinct_submission_id_count': 12, 'submitted_instances': 16, 'rng_used': False,
            'construction_attempts': 1, 'exclusions': []},
        'request_order': ['R0-A', 'R1-B', 'R0-B', 'R1-A'], 'packets': [], 'reference_policies': {}}
    orders = [('R0-A', ['F', 'V', 'F', 'F']), ('R1-B', ['V', 'V', 'V', 'F']),
              ('R0-B', ['V', 'F', 'V', 'V']), ('R1-A', ['F', 'F', 'F', 'V'])]
    for pid, order in orders:
        program = parent['programs'][int(pid[1])]
        reports, occurrences = [], {}
        for label in order:
            root = program['report_ids'][label]
            occurrences[root] = occurrences.get(root, 0) + 1
            hashed = b'cycle11-submission\n' + audit.canonical({'program': program['program'],
                'root_id': root, 'instance_ordinal': occurrences[root]}).encode()
            sid = 's_' + hashlib.sha256(hashed).hexdigest()[:16]
            reports.append({'report_id': sid, 'root_id': root, 'certificate': deepcopy(program['certificates'][label])})
        ids = [report['report_id'] for report in reports]
        text = audit.canonical({'program': program['program'], 'submission_ids': ids, 'reports': reports + [None]})
        fixture['packets'].append({'packet_id': pid, 'program_id': pid[:2], 'private_regime': pid[-1],
            'private_order': order, 'payload': text, 'payload_sha256': audit.sha(text.encode()), 'payload_bytes': len(text.encode())})
        answer = pid.startswith('R1')
        endpoints = [answer if label == 'V' else not answer for label in order]
        choices = {'exact_replay': answer, 'majority': answer if pid[-1] == 'B' else not answer,
                   'minority': answer if pid[-1] == 'A' else not answer,
                   **{'position_' + str(i): endpoint for i, endpoint in enumerate(endpoints, 1)},
                   'always_true': True, 'always_false': False, 'deduplicated_root_vote': None}
        validities = {name: {sid: label == 'V' if name in ('exact_checker', 'endpoint_matches_truth')
                            else name == 'always_valid' for sid, label in zip(ids, order)}
                      for name in ('exact_checker', 'endpoint_matches_truth', 'always_valid', 'always_invalid')}
        fixture['reference_policies'][pid] = {
            'answer': {name: {'answer': value, 'correct': int(value is answer), 'answered': int(value is not None),
                             'planned': 1, 'abstained': int(value is None)} for name, value in choices.items()},
            'validity': {name: {'decisions': vector, 'correct': sum(vector[sid] == (label == 'V')
                         for sid, label in zip(ids, order)), 'valid': 4, 'planned': 4} for name, vector in validities.items()}}
    refs, order = fixture['reference_policies'], fixture['request_order']
    fixture['policy_totals'] = {
        'answer': {name: {**{field: sum(refs[pid]['answer'][name][field] for pid in order)
            for field in ('correct', 'answered', 'planned', 'abstained')},
            'vector': [refs[pid]['answer'][name]['answer'] for pid in order]} for name in choices},
        'validity': {name: {'correct': sum(refs[pid]['validity'][name]['correct'] for pid in order),
            'valid': 16, 'planned': 16, 'vector': [refs[p['packet_id']]['validity'][name]['decisions'][sid]
                for p in fixture['packets'] for sid in audit.parse_json(p['payload'])['submission_ids']]}
            for name in validities}}
    fixture['audit'] = {'source_and_certificate_bytes_preserved': True, 'program_conditioned_roots_preserved': True,
        'instance_identity_verified': True, 'regime_position_truth_balance_verified': True,
        'reference_vectors_verified': True,
        'payload_byte_lengths': {p['packet_id']: p['payload_bytes'] for p in fixture['packets']}}
    return fixture, parent


class Cycle11AuditTests(unittest.TestCase):
    def test_full_synthetic_crossing_and_abstention_denominators(self):
        fixture, parent = synthetic_fixture()
        result = audit.verify_fixture(fixture, parent)
        self.assertEqual(result['answer_policy_correct'], {'exact_replay': 4, 'majority': 2, 'minority': 2,
            'position_1': 2, 'position_2': 2, 'position_3': 2, 'position_4': 2,
            'always_true': 2, 'always_false': 2, 'deduplicated_root_vote': 0})
        self.assertEqual(result['validity_policy_correct'], {'exact_checker': 16, 'endpoint_matches_truth': 16,
                                                               'always_valid': 8, 'always_invalid': 8})
        self.assertEqual(result['deduplicated_root_vote'], {'answered': 0, 'abstained': 4, 'planned': 4})
        self.assertFalse(result['empirical_launch_authorized'])

    def test_program_conditioned_roots_and_reused_instance_ordinals(self):
        fixture, parent = synthetic_fixture()
        a, b = parent['programs']
        self.assertEqual(a['certificates']['V'], b['certificates']['F'])
        self.assertNotEqual(a['report_ids']['V'], b['report_ids']['F'])
        packets = [audit.parse_json(p['payload']) for p in fixture['packets']]
        self.assertEqual(packets[0]['reports'][1]['report_id'], packets[2]['reports'][0]['report_id'])
        self.assertEqual(packets[0]['reports'][0]['report_id'], packets[2]['reports'][1]['report_id'])
        self.assertEqual(len({sid for p in packets for sid in p['submission_ids']}), 12)

    def test_hash_uses_literal_lf_and_canonical_ordinal_tuple(self):
        fixture, parent = synthetic_fixture()
        source, root = parent['programs'][0]['program'], parent['programs'][0]['report_ids']['F']
        actual = audit.submission_id(source, root, 1)
        self.assertEqual(actual, audit.parse_json(fixture['packets'][0]['payload'])['submission_ids'][0])
        data = audit.canonical({'program': source, 'root_id': root, 'instance_ordinal': 1}).encode()
        for wrong in (b'cycle11-submission\\n' + data, b'cycle11-submission\n' + data[:-1]):
            self.assertNotEqual(actual, 's_' + hashlib.sha256(wrong).hexdigest()[:16])
        with mock.patch.object(audit, 'submission_id', return_value='s_' + '0' * 16):
            with self.assertRaisesRegex(ValueError, 'collide'):
                audit.verify_fixture(fixture, parent)

    def test_rehashed_packet_mutations_do_not_escape_content_checks(self):
        for mutation in ('wrong_root', 'extra_metadata', 'corrupt_unchanged_state', 'numeric_boolean', 'extra_copy'):
            with self.subTest(mutation=mutation):
                fixture, parent = synthetic_fixture()
                packet = fixture['packets'][0]
                payload = audit.parse_json(packet['payload'])
                if mutation == 'wrong_root':
                    payload['reports'][0]['root_id'] = parent['programs'][1]['report_ids']['F']
                elif mutation == 'extra_metadata':
                    payload['reports'][0]['valid'] = False
                elif mutation == 'corrupt_unchanged_state':
                    payload['reports'][0]['certificate']['rows'][2]['state']['b'] += 1
                elif mutation == 'numeric_boolean':
                    payload['reports'][0]['certificate']['rows'][-1]['state']['result'] = 1
                else:
                    payload['reports'][-1] = deepcopy(payload['reports'][0])
                packet['payload'] = audit.canonical(payload)
                packet['payload_sha256'] = audit.sha(packet['payload'].encode())
                packet['payload_bytes'] = len(packet['payload'].encode())
                with self.assertRaises(ValueError):
                    audit.verify_fixture(fixture, parent)

    def test_counterfeit_parent_and_forged_reference_count_stop(self):
        for mutation in ('parent_digest', 'parent_program', 'abstention', 'vector'):
            with self.subTest(mutation=mutation):
                fixture, parent = synthetic_fixture()
                if mutation == 'parent_digest':
                    fixture['parent_custody']['fixture_sha256'] = '0' * 64
                elif mutation == 'parent_program':
                    fixture['programs'][1]['program'] = fixture['programs'][0]['program']
                elif mutation == 'abstention':
                    fixture['policy_totals']['answer']['deduplicated_root_vote']['answered'] = 4
                else:
                    fixture['policy_totals']['answer']['majority']['vector'].reverse()
                with self.assertRaises(ValueError):
                    audit.verify_fixture(fixture, parent)


if __name__ == '__main__':
    unittest.main()
