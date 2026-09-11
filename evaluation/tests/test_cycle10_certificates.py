"""Cycle10 synthetic regressions; never render the actual A=2,B=3 panel."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle10_certificates as m


def synthetic_fixture():
    return m.construct_fixture(-3, 4)


class ConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = synthetic_fixture()

    def test_two_programs_six_roots_and_complemented_certificates(self):
        first, second = self.fixture['programs']
        self.assertEqual([p['parameters']['R'] for p in self.fixture['programs']], [0, 1])
        self.assertEqual(first['program'].replace('== 0)', '== 1)'), second['program'])
        roots = [rid for p in self.fixture['programs'] for rid in p['report_ids'].values()]
        self.assertEqual(len(set(roots)), 6)
        for label in m.LABELS:
            one = copy.deepcopy(first['certificates'][label])
            one['rows'][-1]['state']['result'] = not one['rows'][-1]['state']['result']
            self.assertEqual(one, second['certificates'][label])
            self.assertEqual(first['certificate_checks'][label]['first_invalid_step'],
                             {'V': None, 'I': 3, 'F': 6}[label])
        self.assertEqual(self.fixture['generation'], {
            'parameters': {'A': -3, 'B': 4}, 'program_count': 2, 'root_certificate_count': 6,
            'packet_count': 6, 'rng_used': False, 'candidate_attempts': 1, 'exclusions': []})

    def test_id_domain_has_real_newline_and_no_construction_label(self):
        for program in self.fixture['programs']:
            for label, certificate in program['certificates'].items():
                payload = (json.dumps({'program': program['program'], 'certificate': certificate},
                    sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode()
                expected = 'r_' + hashlib.sha256(b'cycle10-certificate\n' + payload).hexdigest()[:16]
                wrong_escape = 'r_' + hashlib.sha256(b'cycle10-certificate\\n' + payload).hexdigest()[:16]
                self.assertEqual(program['report_ids'][label], expected)
                self.assertNotEqual(expected, wrong_escape)
                self.assertEqual(m.certificate_id(program['program'], certificate), expected)

    def test_permutations_preserve_full_report_bytes_and_balance_position_endpoints(self):
        programs = {p['program_id']: p for p in self.fixture['programs']}
        balance, appearances = Counter(), Counter()
        for packet in self.fixture['packets']:
            payload = m.parse_json(packet['payload'])
            program = programs[packet['program_id']]
            self.assertEqual(payload['reports'][3:], [None, None])
            self.assertEqual(payload['original_ids'], [r['report_id'] for r in payload['reports'][:3]])
            for position, (label, report) in enumerate(zip(packet['private_order'], payload['reports'])):
                self.assertEqual(report['report_id'], report['root_id'])
                self.assertEqual(report['root_id'], program['report_ids'][label])
                self.assertEqual(m.sha256_bytes(m.canonical_json(report).encode()), program['report_sha256'][label])
                balance[label, position, report['certificate']['rows'][-1]['state']['result']] += 1
                appearances[report['report_id']] += 1
            self.assertEqual(packet['payload_bytes'], len(packet['payload'].encode()))
            self.assertEqual(packet['payload_sha256'], m.sha256_bytes(packet['payload'].encode()))
            self.assertEqual(packet['payload'], m.canonical_json(payload))
        self.assertEqual(len(balance), 18)
        self.assertEqual(set(balance.values()), {1})
        self.assertEqual(set(appearances.values()), {3})
        self.assertEqual(self.fixture['request_order'],
                         ['R0-P1', 'R1-P2', 'R0-P3', 'R1-P1', 'R0-P2', 'R1-P3'])

    def test_reference_scores_preserve_distinct_vectors_and_denominators(self):
        expected = {'exact_checker': 18, 'always_valid': 6, 'always_invalid': 12,
                    'position_1': 10, 'position_2': 10, 'position_3': 10,
                    'endpoint_matches_truth': 12, 'endpoint_boolean': 9}
        for name, correct in expected.items():
            total = self.fixture['policy_totals'][name]
            self.assertEqual((total['correct'], total['valid'], total['planned']), (correct, 18, 18))
            self.assertEqual(total['vector_differs_from_exact'], name != 'exact_checker')
        for packet in self.fixture['packets']:
            references = self.fixture['reference_policies'][packet['packet_id']]
            self.assertEqual(set(references), set(expected))
            for policy in references.values():
                self.assertEqual((len(policy['decisions']), policy['valid'], policy['planned']), (3, 3, 3))
                self.assertTrue(all(type(value) is bool for value in policy['decisions'].values()))

    def test_collision_across_programs_stops_without_replacement(self):
        first_ids = list(self.fixture['programs'][0]['report_ids'].values())
        with patch.object(m, 'certificate_id', side_effect=first_ids + first_ids) as identify:
            with self.assertRaisesRegex(ValueError, 'collision'):
                synthetic_fixture()
        self.assertEqual(identify.call_count, 6)

    def test_reused_strict_types_and_corrupted_construction_block(self):
        for A, B in ((True, 4), (-3, False), (-10, 4)):
            with self.subTest(A=A, B=B), self.assertRaises(ValueError):
                m.construct_fixture(A, B)
        original = m.previous._certificate_variants
        def corrupt(source, truth):
            certificates = original(source, truth)
            certificates['I']['rows'][2]['state']['a'] = True
            return certificates
        with patch.object(m.previous, '_certificate_variants', side_effect=corrupt), self.assertRaises(ValueError):
            synthetic_fixture()

    def test_input_metadata_is_rejected_and_readable_cases_survive_json_roundtrip(self):
        payload = m.parse_json(self.fixture['packets'][0]['payload'])
        with self.assertRaises(ValueError):
            m.validate_payload({**payload, 'private_order': ['V', 'I', 'F']})
        decoded = m.parse_json(m.canonical_json(self.fixture))
        self.assertEqual(m.readable_cases(decoded), m.readable_cases(self.fixture))
        self.assertIn('Difference from R0-P1', m.readable_cases(decoded))

    def test_actual_builder_fixed_arguments_without_rendering_them(self):
        sentinel = object()
        with patch.object(m, 'construct_fixture', return_value=sentinel) as construct:
            self.assertIs(m.build_fixture(), sentinel)
            construct.assert_called_once_with(2, 3)


class IndependentAndCustodyTests(unittest.TestCase):
    def test_independent_synthetic_fixture_and_corruption(self):
        checker = m._load_checker()
        fixture = synthetic_fixture()
        result = checker.verify_fixture(fixture)
        self.assertTrue(result['all_states_transitions_ids_packets_and_policies_match'])
        changed = copy.deepcopy(fixture)
        policy = changed['reference_policies']['R0-P1']['position_1']
        first_id = next(iter(policy['decisions']))
        policy['decisions'][first_id] = not policy['decisions'][first_id]
        with self.assertRaises(ValueError):
            checker.verify_fixture(changed)

    def test_cli_style_import_loads_independent_checker(self):
        code = ('import cycle10_certificates as m; '
                'r=m._load_checker().verify_fixture(m.construct_fixture(-3,4)); '
                'assert r["all_states_transitions_ids_packets_and_policies_match"]')
        result = subprocess.run([sys.executable, '-c', code], cwd=m.ROOT / 'evaluation',
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_sources_block_before_actual_builder(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m, '_source_hashes', side_effect=FileNotFoundError('missing checker')), \
                patch.object(m, 'build_fixture') as build:
            with self.assertRaises(FileNotFoundError):
                m.prepare_fixture(Path(directory) / 'prepared')
            build.assert_not_called()

    def test_real_independent_custody_with_synthetic_builder_and_tamper(self):
        fixture = synthetic_fixture()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m, 'build_fixture', return_value=fixture) as build:
            prepared = Path(directory) / 'prepared'
            returned, manifest = m.prepare_fixture(prepared, ['synthetic-unit-test'])
            self.assertEqual(returned, fixture)
            digest = m.sha256_bytes((prepared / 'manifest.json').read_bytes())
            reconstructed, recovered = m.validate_fixture_custody(prepared, digest)
            self.assertEqual(reconstructed, fixture)
            self.assertEqual(recovered, manifest)
            self.assertEqual(len(manifest['artifact_sha256']), 17)
            self.assertEqual(build.call_count, 1)
            with self.assertRaises(FileExistsError):
                m.prepare_fixture(prepared)
            self.assertEqual(build.call_count, 1)
            with self.assertRaisesRegex(ValueError, 'manifest hash'):
                m.validate_fixture_custody(prepared, '0' * 64)
            packet = prepared / 'packets' / 'R0-P2.json'
            packet.write_bytes(packet.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'artifact hash/byte'):
                m.validate_fixture_custody(prepared, digest)


if __name__ == '__main__':
    unittest.main()
