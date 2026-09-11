"""Cycle11 synthetic-parent checks. Never prepare from the actual parent seal."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle10_certificates as previous
from evaluation import cycle11_certificates as m


def synthetic_parent():
    return previous.construct_fixture(-3, 4)


class ConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = synthetic_parent()
        cls.fixture = m.construct_fixture(cls.parent)

    def test_parent_records_and_program_conditioned_identical_certificates_preserved(self):
        parent_before = m.canonical_json(self.parent)
        with patch.object(previous, 'build_fixture', side_effect=AssertionError('parent rebuild forbidden')):
            fixture = m.construct_fixture(self.parent)
        self.assertEqual(m.canonical_json(self.parent), parent_before)
        self.assertEqual(fixture['programs'], self.parent['programs'])
        self.assertEqual(fixture['parent_custody']['fixture_sha256'],
                         hashlib.sha256(parent_before.encode()).hexdigest())
        first, second = fixture['programs']
        for a, b in (('V', 'F'), ('F', 'V')):
            self.assertEqual(first['certificates'][a], second['certificates'][b])
            self.assertNotEqual(first['report_ids'][a], second['report_ids'][b])
        allowed = {p['report_ids'][label] for p in fixture['programs'] for label in ('V', 'F')}
        excluded = {p['report_ids']['I'] for p in fixture['programs']}
        submitted = {r['root_id'] for p in fixture['packets']
                     for r in m.parse_json(p['payload'])['reports'][:4]}
        self.assertEqual(submitted, allowed)
        self.assertTrue(submitted.isdisjoint(excluded))

    def test_instance_domain_ordinals_and_reuse_are_exact(self):
        identities = {}
        for packet in self.fixture['packets']:
            payload = m.parse_json(packet['payload'])
            counts = Counter()
            for report in payload['reports'][:4]:
                root = report['root_id']
                counts[root] += 1
                content = {'program': payload['program'], 'root_id': root,
                           'instance_ordinal': counts[root]}
                text = (json.dumps(content, sort_keys=True, separators=(',', ':'),
                                   ensure_ascii=True, allow_nan=False) + '\n').encode()
                expected = 's_' + hashlib.sha256(b'cycle11-submission\n' + text).hexdigest()[:16]
                escaped = 's_' + hashlib.sha256(b'cycle11-submission\\n' + text).hexdigest()[:16]
                self.assertEqual(report['report_id'], expected)
                self.assertNotEqual(expected, escaped)
                key = payload['program'], root, counts[root]
                self.assertEqual(identities.setdefault(key, expected), expected)
        self.assertEqual(len(identities), 12)
        self.assertEqual(len(set(identities.values())), 12)

    def test_fixed_crossing_balances_slots_truths_and_regimes(self):
        self.assertEqual([p['packet_id'] for p in self.fixture['packets']], list(m.REQUEST_ORDER))
        self.assertEqual(self.fixture['request_order'], ['R0-A', 'R1-B', 'R0-B', 'R1-A'])
        programs = {p['program_id']: p for p in self.fixture['programs']}
        balance = Counter()
        for packet in self.fixture['packets']:
            payload = m.parse_json(packet['payload'])
            self.assertEqual(payload['reports'][-1], None)
            self.assertEqual(len(payload['submission_ids']), 4)
            self.assertEqual(payload['submission_ids'], [r['report_id'] for r in payload['reports'][:4]])
            self.assertEqual(sorted(Counter(r['root_id'] for r in payload['reports'][:4]).values()), [1, 3])
            self.assertEqual(packet['private_order'], list(m.PLACEMENTS[packet['packet_id']]))
            self.assertEqual(packet['private_order'].count('V'), 1 if packet['private_regime'] == 'A' else 3)
            truth = programs[packet['program_id']]['python_truth']['answer']
            for position, label in enumerate(packet['private_order']):
                balance[position, truth, label] += 1
            self.assertEqual(packet['payload'], m.canonical_json(payload))
            self.assertEqual(packet['payload_bytes'], len(packet['payload'].encode()))
            self.assertEqual(packet['payload_sha256'], m.sha256_bytes(packet['payload'].encode()))
        self.assertEqual(len(balance), 16)
        self.assertEqual(set(balance.values()), {1})

    def test_reference_vectors_and_deduplication_abstention_denominators(self):
        answers = self.fixture['policy_totals']['answer']
        validities = self.fixture['policy_totals']['validity']
        self.assertEqual(answers['exact_replay']['vector'], [True, False, True, False])
        self.assertEqual(answers['majority']['vector'], [False, False, True, True])
        self.assertEqual(answers['minority']['vector'], [True, True, False, False])
        for name in m.ANSWER_POLICIES[:-1]:
            self.assertEqual(answers[name]['correct'], 4 if name == 'exact_replay' else 2)
            self.assertEqual((answers[name]['answered'], answers[name]['planned'], answers[name]['abstained']),
                             (4, 4, 0))
        self.assertEqual(answers['deduplicated_root_vote'],
                         {'correct': 0, 'answered': 0, 'planned': 4, 'abstained': 4, 'vector': [None] * 4})
        self.assertEqual(validities['exact_checker']['vector'], validities['endpoint_matches_truth']['vector'])
        for name in m.VALIDITY_POLICIES:
            self.assertEqual(validities[name]['correct'], 16 if name in ('exact_checker', 'endpoint_matches_truth') else 8)
            self.assertEqual((validities[name]['valid'], validities[name]['planned']), (16, 16))

    def test_collisions_and_wrong_parent_mapping_stop(self):
        with patch.object(m, 'submission_id', return_value='s_' + '0' * 16):
            with self.assertRaisesRegex(ValueError, 'collide'):
                m.construct_fixture(self.parent)
        parent = copy.deepcopy(self.parent)
        parent['programs'][0]['report_ids']['V'] = parent['programs'][0]['report_ids']['F']
        with self.assertRaises(ValueError):
            m.construct_fixture(parent)

    def test_packet_schema_exact_types_metadata_and_copy_bytes(self):
        payload = m.parse_json(self.fixture['packets'][0]['payload'])
        changed = copy.deepcopy(payload)
        changed['reports'][0]['certificate']['rows'][0]['state']['a'] = True
        with self.assertRaises(ValueError):
            m.validate_payload(changed)
        changed = copy.deepcopy(payload)
        changed['reports'][0]['certificate']['rows'][2]['state']['b'] += 1
        with self.assertRaisesRegex(ValueError, 'different certificate bytes'):
            m.validate_payload(changed)
        for update in ({'private_regime': 'A'}, {'original_ids': payload['submission_ids']}):
            with self.assertRaises(ValueError):
                m.validate_payload({**payload, **update})
        changed = copy.deepcopy(payload)
        changed['submission_ids'][0] = {}
        with self.assertRaises(ValueError):
            m.validate_payload(changed)
        with self.assertRaises(ValueError):
            m.submission_id(payload['program'], payload['reports'][0]['root_id'], True)

    def test_independent_reconstruction_and_readable_roundtrip(self):
        result = m._load_checker().verify_fixture(self.fixture, self.parent)
        self.assertTrue(result['all_parent_states_roots_instances_and_reference_vectors_match'])
        roundtrip = m.parse_json(m.canonical_json(self.fixture))
        self.assertEqual(m.readable_cases(roundtrip), m.readable_cases(self.fixture))
        wrong = copy.deepcopy(self.fixture)
        wrong['policy_totals']['answer']['deduplicated_root_vote']['answered'] = 4
        with self.assertRaises(ValueError):
            m._load_checker().verify_fixture(wrong, self.parent)


class CustodyTests(unittest.TestCase):
    def test_missing_source_blocks_parent_access(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m, '_source_hashes', side_effect=FileNotFoundError('missing checker')), \
                patch.object(m, '_load_parent') as load_parent:
            with self.assertRaises(FileNotFoundError):
                m.prepare_fixture(Path(directory) / 'prepared')
            load_parent.assert_not_called()

    def test_synthetic_parent_roundtrip_and_parent_packet_tamper(self):
        parent = synthetic_parent()
        with tempfile.TemporaryDirectory() as directory:
            parent_dir, output = Path(directory) / 'parent', Path(directory) / 'prepared'
            with patch.object(previous, 'build_fixture', return_value=parent):
                previous.prepare_fixture(parent_dir, ['synthetic-parent-test'])
            anchor = m.sha256_bytes((parent_dir / 'manifest.json').read_bytes())
            checker = m._load_checker()
            original_parent_bytes = (parent_dir / 'fixture.json').read_bytes()
            with patch.object(m, 'PARENT_DIRECTORY', parent_dir), \
                    patch.object(m, 'PARENT_MANIFEST_SHA', anchor), \
                    patch.object(checker, 'PARENT_SHA', anchor), \
                    patch.object(m, '_load_checker', return_value=checker), \
                    patch.object(previous, 'build_fixture', side_effect=AssertionError('no parent rebuild')):
                fixture, manifest = m.prepare_fixture(output, ['synthetic-cycle11-test'])
                self.assertEqual((parent_dir / 'fixture.json').read_bytes(), original_parent_bytes)
                self.assertEqual((output / 'parent-fixture.json').read_bytes(), original_parent_bytes)
                self.assertEqual(fixture['parent_custody']['manifest_sha256'], anchor)
                self.assertEqual(len(manifest['artifact_sha256']), 9)
                digest = m.sha256_bytes((output / 'manifest.json').read_bytes())
                recovered, recovered_manifest = m.validate_fixture_custody(output, digest)
                self.assertEqual(recovered, fixture)
                self.assertEqual(recovered_manifest, manifest)
                with self.assertRaises(FileExistsError):
                    m.prepare_fixture(output)
                with self.assertRaisesRegex(ValueError, 'manifest hash'):
                    m.validate_fixture_custody(output, '0' * 64)
                packet = output / 'packets' / 'R0-A.json'
                original = packet.read_bytes()
                packet.write_bytes(original + b'\n')
                with self.assertRaisesRegex(ValueError, 'artifact hash/byte'):
                    m.validate_fixture_custody(output, digest)
                packet.write_bytes(original)
                (output / 'parent-fixture.json').write_bytes(original_parent_bytes + b'\n')
                with self.assertRaisesRegex(ValueError, 'parent copy'):
                    m.validate_fixture_custody(output, digest)


if __name__ == '__main__':
    unittest.main()
