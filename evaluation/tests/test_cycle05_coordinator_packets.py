"""Independent probability tables, custody, boundaries, and missingness checks."""

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest
from unittest import mock

from evaluation import cycle05_coordinator_packets as c


class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = c.build_fixture()

    def test_counts_order_bytes_and_provider_boundary(self):
        f = self.fixture
        self.assertEqual(len(f['packets']), 20)
        self.assertEqual(sum(p['view'] == 'blind' for p in f['packets']), 8)
        self.assertEqual(sum(p['view'] == 'aware' for p in f['packets']), 12)
        self.assertEqual(len(f['pairs']), 12)
        self.assertEqual(f['diagnostic_world_arm_rows'], 72)
        expected_order = sorted(p['packet_id'] for p in f['packets'])
        random.Random(42).shuffle(expected_order)
        self.assertEqual(f['request_order'], expected_order)
        self.assertEqual(f, c.build_fixture())
        self.assertEqual(f['system_prompt_sha256'], hashlib.sha256(f['system_prompt'].encode()).hexdigest())
        self.assertEqual(len(set(p['payload'] for p in f['packets'])), 20)
        for packet in f['packets']:
            payload = json.loads(packet['payload'])
            self.assertEqual(set(payload), {'model_parameters', 'reports'} | ({'parent_partition'} if packet['view'] == 'aware' else set()))
            self.assertEqual(packet['payload_sha256'], hashlib.sha256(packet['payload'].encode()).hexdigest())
            self.assertFalse(packet['payload'].endswith('\n'))
            self.assertNotIn(packet['packet_id'], packet['payload'])
            self.assertEqual(tuple(p['report_id'] for p in payload['reports']), c.REPORT_IDS)
            c.validate_payload(payload)
        self.assertEqual(c.validate_fixture(f), f)

    def test_independent_probability_table(self):
        # Integrate the unused roots analytically rather than importing the
        # cycle04 generator or conditioning implementation.
        for specialist in c.SPECIALIST_VALUES:
            s, g = Fraction(specialist), Fraction(7, 10)
            masses = {}
            for sign in (-1, 1):
                gp, sp = (g, 1 - s) if sign == 1 else (1 - g, s)
                for arm, roots in (('padded', 1), ('copied', 1), ('independent', 3)):
                    positive = gp ** roots * sp / 6
                    negative = (1 - gp) ** roots * (1 - sp) / 6
                    masses[arm, sign] = (positive + negative, positive)
            total = sum((mass for mass, _ in masses.values()), Fraction(0))
            self.assertEqual(total, Fraction(self.fixture['diagnostic_mass_by_p_specialist'][specialist]))
            for packet in self.fixture['packets']:
                if packet['p_specialist'] != specialist:
                    continue
                payload = json.loads(packet['payload'])
                sign = packet['generalist_sign']
                if packet['view'] == 'aware':
                    arm = c.ARMS[c.PARTITIONS.index(tuple(payload['parent_partition']))]
                    expected = [masses[arm, sign]]
                elif payload['reports'][1]['value'] is None:
                    expected = [masses['padded', sign]]
                else:
                    expected = [masses[arm, sign] for arm in ('copied', 'independent')]
                mass = sum((m for m, _ in expected), Fraction(0))
                positive = sum((p for _, p in expected), Fraction(0))
                self.assertEqual(Fraction(packet['diagnostic_mass']), mass)
                self.assertEqual(Fraction(packet['truth_positive_mass']), positive)
                self.assertEqual(Fraction(packet['reference_p_positive']), positive / mass)
                self.assertEqual(Fraction(packet['diagnostic_weight']), mass / total)
            for view in c.VIEWS:
                packets = [p for p in self.fixture['packets'] if p['view'] == view and p['p_specialist'] == specialist]
                self.assertEqual(sum(Fraction(p['diagnostic_weight']) for p in packets), 1)
                self.assertEqual(sum(Fraction(p['truth_positive_mass']) for p in packets), total / 2)
        self.assertEqual(self.fixture['diagnostic_mass_by_p_specialist'], {'11/20': '941/2500', '17/20': '331/1250'})

    def test_lineage_blind_response_reuse(self):
        for specialist in c.SPECIALIST_VALUES:
            for sign in (-1, 1):
                pairs = {pair['arm']: pair for pair in self.fixture['pairs'] if pair['p_specialist'] == specialist and pair['generalist_sign'] == sign}
                self.assertEqual(pairs['copied']['blind_packet_id'], pairs['independent']['blind_packet_id'])
                self.assertNotEqual(pairs['copied']['aware_packet_id'], pairs['independent']['aware_packet_id'])
                self.assertEqual(pairs['padded']['aware_q'], pairs['copied']['aware_q'])
                self.assertNotEqual(pairs['copied']['aware_q'], pairs['independent']['aware_q'])

    def test_payload_rejects_leaks_and_invalid_observations(self):
        base = json.loads(self.fixture['packets'][0]['payload'])
        for extra in ('packet_id', 'truth', 'arm', 'reference_p_positive', 'cost', 'view'):
            bad = deepcopy(base)
            bad[extra] = 'leaked'
            with self.assertRaises(ValueError):
                c.validate_payload(bad)
        mutations = [lambda p: p['reports'].pop(),
                     lambda p: p['reports'][0].update(value=True),
                     lambda p: p['reports'][0].update(value='1'),
                     lambda p: p['reports'][0].update(value=None),
                     lambda p: p['reports'][0].update(value=p['reports'][3]['value']),
                     lambda p: p['reports'][0].update(report_id='other'),
                     lambda p: p['reports'][0].update(truth=1),
                     lambda p: p['model_parameters'].update(p_specialist='0.55'),
                     lambda p: p['model_parameters'].update(extra='leak'),
                     lambda p: p.update(parent_partition=[False, None, None, 1]),
                     lambda p: p.update(parent_partition=[0, 0, 0, 0])]
        for mutate in mutations:
            bad = deepcopy(base)
            mutate(bad)
            with self.assertRaises(ValueError):
                c.validate_payload(bad)

    def test_immutable_source_and_fixture_custody(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            for name in ('manifest.json', 'summary.json', 'per_world.json'):
                shutil.copyfile(c.BASELINE_DIRECTORY / name, source / name)
            self.assertEqual(c.build_fixture(source), self.fixture)
            (source / 'per_world.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'output hash mismatch'):
                c.build_fixture(source)
            (source / 'manifest.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'manifest hash mismatch'):
                c.build_fixture(source)
        for field in ('payload', 'reference_p_positive', 'diagnostic_mass'):
            bad = deepcopy(self.fixture)
            bad['packets'][0][field] += 'changed'
            with self.assertRaises(ValueError):
                c.validate_fixture(bad)


class ParserTests(unittest.TestCase):
    def test_json_numbers_preserve_exact_decimal(self):
        for raw, expected in [('0', Fraction(0)), ('1', Fraction(1)), ('0.125', Fraction(1, 8)),
                              ('1e-3', Fraction(1, 1000)), ('-0', Fraction(0)),
                              ('0.1234567890123456789', Fraction('0.1234567890123456789'))]:
            self.assertEqual(c.parse_probability(' {"p_positive":' + raw + '}\n'), expected)

    def test_rejects_non_json_probability_responses(self):
        cases = {
            'not_text': [None, b'{"p_positive":0.5}'],
            'duplicate_key': ['{"p_positive":0.4,"p_positive":0.6}'],
            'nonfinite': ['{"p_positive":NaN}', '{"p_positive":Infinity}', '{"p_positive":-Infinity}'],
            'not_object': ['[0.5]', '0.5', 'null'],
            'keys': ['{}', '{"other":0.5}', '{"p_positive":0.5,"explanation":"x"}'],
            'not_number': ['{"p_positive":true}', '{"p_positive":false}', '{"p_positive":"0.5"}',
                           '{"p_positive":null}', '{"p_positive":[0.5]}', '{"p_positive":{}}'],
            'out_of_range': ['{"p_positive":-0.01}', '{"p_positive":1.001}', '{"p_positive":1e309}'],
            'malformed_json': ['{"p_positive":1/2}', '{"p_positive":.5}', '```json\n{"p_positive":0.5}\n```',
                               '{"p_positive":0.5} because', '{"p_positive":0.5}{"p_positive":0.5}']}
        for code, raws in cases.items():
            for raw in raws:
                with self.subTest(raw=raw):
                    with self.assertRaises(c.ProbabilityParseError) as caught:
                        c.parse_probability(raw)
                    self.assertEqual(caught.exception.code, code)


class PreparationTests(unittest.TestCase):
    def test_preparation_custody_and_exclusive_outputs(self):
        with tempfile.TemporaryDirectory(dir=c.ROOT / 'results') as directory:
            root = Path(directory)
            protocol = root / 'test-protocol.md'
            protocol.write_text('A test-only execution contract.\n')
            digest = hashlib.sha256(protocol.read_bytes()).hexdigest()
            output = root / 'prepared'
            fixture, manifest = c.prepare_fixture(output, protocol, digest)
            self.assertEqual(manifest['status'], 'complete')
            self.assertEqual(set(path.name for path in output.iterdir()), {'fixture.json', 'manifest-start.json', 'manifest.json'})
            manifest_digest = hashlib.sha256((output / 'manifest.json').read_bytes()).hexdigest()
            self.assertEqual(c.validate_fixture_custody(output, manifest_digest), (fixture, manifest))
            with self.assertRaises(FileExistsError):
                c.prepare_fixture(output, protocol, digest)
            with self.assertRaisesRegex(ValueError, 'manifest hash mismatch'):
                c.validate_fixture_custody(output, '0' * 64)
            changed = json.loads((output / 'fixture.json').read_text())
            changed['request_order'].reverse()
            (output / 'fixture.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'output hash mismatch'):
                c.validate_fixture_custody(output)

    def test_contract_hash_and_source_change_guards(self):
        with tempfile.TemporaryDirectory(dir=c.ROOT / 'results') as directory:
            root = Path(directory)
            protocol = root / 'test-protocol.md'
            protocol.write_text('Test-only contract.\n')
            digest = hashlib.sha256(protocol.read_bytes()).hexdigest()
            output = root / 'prepared'
            with self.assertRaisesRegex(ValueError, 'protocol hash mismatch'):
                c.prepare_fixture(output, protocol, '0' * 64)
            self.assertFalse(output.exists())
            original = c._source_hashes(protocol)
            changed = dict(original, **{c.CODE: '0' * 64})
            with mock.patch.object(c, '_source_hashes', side_effect=[original, changed]):
                with self.assertRaisesRegex(ValueError, 'source changed'):
                    c.prepare_fixture(output, protocol, digest)
            self.assertTrue((output / 'manifest-invalid.json').exists())
            self.assertFalse((output / 'manifest.json').exists())
            second = root / 'second-prepared'
            c.prepare_fixture(second, protocol, digest)
            protocol.write_text('Changed test contract.\n')
            with self.assertRaisesRegex(ValueError, 'source custody mismatch'):
                c.validate_fixture_custody(second)

    def test_output_must_be_inside_results(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                c._fresh_results_directory(Path(directory) / 'not-repository-results')
        with self.assertRaises(ValueError):
            c._fresh_results_directory(c.ROOT / 'results')


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = c.build_fixture()
        cls.oracle = {p['packet_id']: Fraction(p['reference_p_positive']) for p in cls.fixture['packets']}

    def test_oracle_zero_regret_and_ideal_information_value(self):
        result = c.score_predictions(self.fixture, self.oracle)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['coverage'], {'planned': 20, 'valid': 20, 'invalid': 0, 'missing': 0, 'failure_types': {}})
        self.assertIsNone(result['valid_subset_diagnostic'])
        for specialist in c.SPECIALIST_VALUES:
            for view in c.VIEWS:
                summary = result['primary'][specialist][view]
                self.assertEqual(summary['conditional_excess_brier'], '0')
                self.assertEqual(summary['expected_brier'], summary['ideal_expected_brier'])
            pair = result['paired']['by_p_specialist'][specialist]
            self.assertEqual(pair['selection_cross_term'], '0')
            self.assertEqual(pair['original_posterior_regret_delta'], '0')
            self.assertEqual(Fraction(pair['aware_minus_blind_expected_brier']), -Fraction(pair['posterior_squared_gap']))
        self.assertTrue(all(row['probability_sum_minus_one'] == '0' for row in result['contrasts']['sign_symmetry']))
        self.assertTrue(all(row['copied_minus_padded'] == '0' for row in result['contrasts']['padded_to_copied'] if row['view'] == 'aware'))

    def test_nonoracle_full_decomposition_and_independent_brier(self):
        predictions = {packet['packet_id']: Fraction(index, 20) for index, packet in enumerate(self.fixture['packets'])}
        result = c.score_predictions(self.fixture, predictions)
        for specialist in c.SPECIALIST_VALUES:
            pair = result['paired']['by_p_specialist'][specialist]
            primary = result['primary'][specialist]
            self.assertEqual(pair['selection_cross_term'], '0')
            gap = Fraction(pair['aware_minus_blind_expected_brier'])
            self.assertEqual(gap, Fraction(pair['ideal_information_gap']) + Fraction(primary['aware']['conditional_excess_brier']) - Fraction(primary['blind']['conditional_excess_brier']))
            direct = Fraction(0)
            for case in self.fixture['pairs']:
                if case['p_specialist'] != specialist:
                    continue
                mass, pos = Fraction(case['diagnostic_mass']), Fraction(case['truth_positive_mass'])
                pa, pb = predictions[case['aware_packet_id']], predictions[case['blind_packet_id']]
                direct += pos * ((1 - pa) ** 2 - (1 - pb) ** 2) + (mass - pos) * (pa ** 2 - pb ** 2)
            self.assertEqual(gap, direct / Fraction(self.fixture['diagnostic_mass_by_p_specialist'][specialist]))

    def test_partial_requires_changed_denominators_and_cross_term(self):
        case = next(p for p in self.fixture['pairs'] if p['arm'] == 'independent' and p['p_specialist'] == '17/20' and p['generalist_sign'] == 1)
        predictions = {case['aware_packet_id']: Fraction(1, 4), case['blind_packet_id']: Fraction(3, 4)}
        result = c.score_predictions(self.fixture, predictions)
        self.assertEqual(result['status'], 'incomplete')
        self.assertIsNone(result['primary'])
        self.assertEqual(result['coverage']['missing'], 18)
        pair = result['paired']['by_p_specialist']['17/20']
        self.assertEqual(pair['valid_pair_count'], 1)
        self.assertEqual(pair['valid_diagnostic_mass'], case['diagnostic_mass'])
        self.assertNotEqual(pair['selection_cross_term'], '0')
        self.assertEqual(Fraction(pair['aware_minus_blind_expected_brier']), sum(Fraction(pair[key]) for key in ('ideal_information_gap', 'original_posterior_regret_delta', 'selection_cross_term')))
        subsets = result['valid_subset_diagnostic']['by_p_specialist']['17/20']
        self.assertGreater(Fraction(subsets['blind']['valid_diagnostic_mass']), Fraction(subsets['aware']['valid_diagnostic_mass']))
        for packet_id, probability in predictions.items():
            packet = next(p for p in self.fixture['packets'] if p['packet_id'] == packet_id)
            self.assertEqual(Fraction(subsets[packet['view']]['conditional_excess_brier']), (probability - Fraction(packet['reference_p_positive'])) ** 2)
        self.assertIsNone(result['paired']['by_p_specialist']['11/20']['aware_minus_blind_expected_brier'])

    def test_one_missing_makes_whole_primary_incomplete(self):
        predictions = dict(self.oracle)
        missing = next(p['packet_id'] for p in self.fixture['packets'] if p['p_specialist'] == '11/20')
        del predictions[missing]
        result = c.score_predictions(self.fixture, predictions, {missing: 'native_error'})
        self.assertIsNone(result['primary'])
        self.assertEqual(result['coverage']['failure_types'], {'native_error': 1})
        self.assertEqual(result['valid_subset_diagnostic']['by_p_specialist']['17/20']['aware']['diagnostic_mass_coverage'], '1')

    def test_failures_are_not_repaired_and_input_ids_are_strict(self):
        ids = self.fixture['request_order']
        result = c.score_responses(self.fixture, {ids[0]: '{"p_positive":"0.5"}', ids[1]: '{"p_positive":0.5}'}, {ids[2]: 'timeout'})
        self.assertEqual(result['coverage']['valid'], 1)
        self.assertEqual(result['coverage']['invalid'], 2)
        self.assertEqual(result['coverage']['failure_types'], {'not_number': 1, 'timeout': 1})
        for predictions in ({'unknown': Fraction(1, 2)}, {ids[0]: .5}, {ids[0]: True}, {ids[0]: Fraction(2)}):
            with self.assertRaises(ValueError):
                c.score_predictions(self.fixture, predictions)
        with self.assertRaises(ValueError):
            c.score_predictions(self.fixture, {ids[0]: Fraction(1, 2)}, {ids[0]: 'error'})
        empty = c.score_predictions(self.fixture, {})
        self.assertIsNone(empty['primary'])
        self.assertEqual(empty['coverage']['missing'], 20)


if __name__ == '__main__':
    unittest.main()
