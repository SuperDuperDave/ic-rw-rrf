"""Independent analytic probabilities, channel boundaries, scoring, and custody."""

from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest
from unittest import mock

from evaluation import cycle06_noisy_lineage as c


class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = c.build_fixture()

    def test_unique_observations_and_canonical_bytes(self):
        fixture = self.fixture
        self.assertEqual(len(fixture['packets']), 8)
        self.assertEqual(len({p['payload'] for p in fixture['packets']}), 8)
        self.assertEqual(fixture['diagnostic_world_arm_rows'], 40)
        expected_order = sorted(p['packet_id'] for p in fixture['packets'])
        random.Random(42).shuffle(expected_order)
        self.assertEqual(fixture['request_order'], expected_order)
        self.assertEqual(fixture, c.build_fixture())
        self.assertEqual(fixture['system_prompt_sha256'], hashlib.sha256(fixture['system_prompt'].encode()).hexdigest())
        for packet in fixture['packets']:
            payload = json.loads(packet['payload'])
            self.assertEqual(set(payload), {'model_parameters', 'reports', 'noisy_lineage_hint'})
            self.assertEqual(payload['noisy_lineage_hint'], packet['noisy_lineage_hint'])
            self.assertEqual(payload['model_parameters']['hint_flip_probability'], '1/4')
            self.assertEqual(tuple(r['report_id'] for r in payload['reports']), c.REPORT_IDS)
            self.assertTrue(all(r['value'] is not None for r in payload['reports']))
            self.assertEqual(packet['payload_sha256'], hashlib.sha256(packet['payload'].encode()).hexdigest())
            self.assertEqual(packet['packet_id'], 'p_' + packet['payload_sha256'][:20])
            self.assertNotIn(packet['packet_id'], packet['payload'])
            self.assertEqual(c.canonical_json(payload), packet['payload'])
            self.assertEqual(c.validate_payload(payload), payload)

    def test_analytic_table_and_augmented_generator_weights(self):
        # Integrate irrelevant primitive readings analytically; do not import
        # the row-conditioning implementation or derive expectations from it.
        table = {
            ('11/20', 'copied'): (F(2443, 3576), F(1341, 4328)),
            ('11/20', 'independent'): (F(5187, 6584), F(823, 4328)),
            ('17/20', 'copied'): (F(2443, 7696), F(481, 1448)),
            ('17/20', 'independent'): (F(1729, 3888), F(243, 1448))}
        self.assertEqual(self.fixture['diagnostic_mass_by_p_specialist'], {
            '11/20': '541/2500', '17/20': '181/1250'})
        for packet in self.fixture['packets']:
            s, sign, hint = F(packet['p_specialist']), packet['generalist_sign'], packet['noisy_lineage_hint']
            a = {'copied': F(7, 10) * (1-s), 'independent': F(7, 10)**3 * (1-s)}
            b = {'copied': F(3, 10) * s, 'independent': F(3, 10)**3 * s}
            positive = sum((a[arm] * (F(3, 4) if arm == hint else F(1, 4)) / 6
                            for arm in ('copied', 'independent')), F(0))
            negative = sum((b[arm] * (F(3, 4) if arm == hint else F(1, 4)) / 6
                            for arm in ('copied', 'independent')), F(0))
            mass = positive + negative
            noisy, weight = table[packet['p_specialist'], hint]
            blind = sum(a.values()) / (sum(a.values()) + sum(b.values()))
            naive = a[hint] / (a[hint] + b[hint])
            if sign == -1:
                positive, noisy, blind, naive = negative, 1-noisy, 1-blind, 1-naive
            self.assertEqual(F(packet['diagnostic_mass']), mass)
            self.assertEqual(F(packet['truth_positive_mass']), positive)
            self.assertEqual(positive / mass, noisy)
            self.assertEqual(F(packet['diagnostic_weight']), weight)
            self.assertEqual(F(packet['reference_p_positive']), noisy)
            self.assertEqual({key: F(value) for key, value in packet['references'].items()}, {
                'noisy_bayes': noisy, 'blind': blind, 'naive_hint_trust': naive})
            self.assertEqual(sum(F(row['augmented_mass']) for row in packet['source_row_weights']), mass)
        for specialist in c.SPECIALIST_VALUES:
            cells = [p for p in self.fixture['packets'] if p['p_specialist'] == specialist]
            self.assertEqual(sum(F(p['diagnostic_weight']) for p in cells), 1)
            self.assertEqual(sum(F(p['truth_positive_mass']) for p in cells),
                             F(self.fixture['diagnostic_mass_by_p_specialist'][specialist]) / 2)
        strong_hint_i = next(p for p in self.fixture['packets'] if p['p_specialist'] == '17/20'
                             and p['generalist_sign'] == 1 and p['noisy_lineage_hint'] == 'independent')
        self.assertLess(F(strong_hint_i['reference_p_positive']), F(1, 2))
        self.assertLess(F(strong_hint_i['references']['blind']), F(1, 2))
        self.assertGreater(F(strong_hint_i['references']['naive_hint_trust']), F(1, 2))

    def test_channel_boundaries_recover_lineage_and_blind(self):
        _, rows, _ = c.frozen.load_baseline()
        for error, comparator in ((F(0), 'naive_hint_trust'), (F(1, 2), 'blind')):
            cells, count = c.reference_cells(rows, error)
            self.assertEqual(count, 40)
            self.assertEqual(len(cells), 8)
            for cell in cells.values():
                self.assertEqual(cell['noisy_bayes'], F(cell[comparator]))
        for error in (0.25, F(-1), F(3, 4)):
            with self.assertRaises(ValueError):
                c.reference_cells(rows, error)

    def test_payload_rejects_leaks_and_wrong_channel(self):
        base = json.loads(self.fixture['packets'][0]['payload'])
        for extra in ('packet_id', 'truth', 'arm', 'actual_construction', 'parent_partition',
                      'true_partition', 'reference_p_positive', 'answers', 'evaluation_id'):
            bad = deepcopy(base)
            bad[extra] = 'leaked'
            with self.assertRaises(ValueError):
                c.validate_payload(bad)
        mutations = [lambda p: p.update(noisy_lineage_hint='padded'),
                     lambda p: p.update(noisy_lineage_hint=True),
                     lambda p: p['reports'].pop(),
                     lambda p: p['reports'][0].update(value=True),
                     lambda p: p['reports'][0].update(value='1'),
                     lambda p: p['reports'][0].update(truth=1),
                     lambda p: p['reports'][0].update(report_id='other'),
                     lambda p: p['reports'][1].update(value=None),
                     lambda p: p['model_parameters'].update(hint_flip_probability='1/2'),
                     lambda p: p['model_parameters'].update(extra='leak')]
        for mutate in mutations:
            bad = deepcopy(base)
            mutate(bad)
            with self.assertRaises(ValueError):
                c.validate_payload(bad)

    def test_anchored_source_and_reference_changes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            for name in ('manifest.json', 'summary.json', 'per_world.json'):
                shutil.copyfile(c.BASELINE_DIRECTORY / name, source / name)
            self.assertEqual(c.build_fixture(source), self.fixture)
            (source / 'per_world.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'output hash mismatch'):
                c.build_fixture(source)
        for field in ('reference_p_positive', 'diagnostic_mass', 'payload'):
            bad = deepcopy(self.fixture)
            bad['packets'][0][field] += 'changed'
            with self.assertRaises(ValueError):
                c.validate_fixture(bad)


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = c.build_fixture()
        cls.oracle = {p['packet_id']: F(p['reference_p_positive']) for p in cls.fixture['packets']}

    def test_oracle_brier_and_comparator_distances(self):
        result = c.score_predictions(self.fixture, self.oracle)
        self.assertEqual(result['status'], 'complete')
        self.assertIsNone(result['valid_subset_diagnostic'])
        for summary in result['primary'].values():
            self.assertEqual(summary['conditional_excess_brier'], '0')
            self.assertEqual(summary['expected_brier'], summary['ideal_expected_brier'])
            for comparator in summary['comparators'].values():
                self.assertEqual(comparator['conditional_excess_brier'], comparator['model_squared_distance'])
                self.assertEqual(F(comparator['model_minus_expected_brier']), -F(comparator['conditional_excess_brier']))
        self.assertTrue(all(p['sign_matches_reference'] for p in result['packets']))
        for pair in result['contrasts']['sign_symmetry']:
            self.assertEqual(pair['probability_sum_minus_one'], '0')
        for pair in result['contrasts']['hint_contrast']:
            self.assertEqual(pair['hint_independent_minus_copied'],
                             pair['reference_hint_independent_minus_copied']['noisy_bayes'])
            self.assertEqual(pair['reference_hint_independent_minus_copied']['blind'], '0')

    def test_nonoracle_direct_expected_brier_and_hint_signs(self):
        predictions = {p['packet_id']: F(index, 8) for index, p in enumerate(self.fixture['packets'])}
        result = c.score_predictions(self.fixture, predictions)
        _, rows, _ = c.frozen.load_baseline()
        for specialist in c.SPECIALIST_VALUES:
            # Sum squared losses against actual binary truths in the raw worlds.
            losses = {name: F(0) for name in ('model',) + c.REFERENCES}
            total = F(0)
            for packet in self.fixture['packets']:
                if packet['p_specialist'] != specialist:
                    continue
                for source in packet['source_row_weights']:
                    truth = int(rows[source['source_row_id']]['world']['y'] == 1)
                    mass = F(source['augmented_mass'])
                    total += mass
                    values = dict(packet['references'], model=predictions[packet['packet_id']])
                    for name, prediction in values.items():
                        losses[name] += mass * (F(prediction) - truth)**2
            summary = result['primary'][specialist]
            self.assertEqual(F(summary['expected_brier']), losses['model'] / total)
            self.assertEqual(F(summary['conditional_excess_brier']),
                             (losses['model'] - losses['noisy_bayes']) / total)
            for name in c.REFERENCES:
                self.assertEqual(F(summary['comparators'][name]['expected_brier']), losses[name] / total)
                self.assertEqual(F(summary['comparators'][name]['model_minus_expected_brier']),
                                 (losses['model'] - losses[name]) / total)

    def test_partial_missingness_and_changed_mass(self):
        packet = self.fixture['packets'][0]
        probability = F(1, 2)
        result = c.score_predictions(self.fixture, {packet['packet_id']: probability})
        self.assertEqual(result['status'], 'incomplete')
        self.assertIsNone(result['primary'])
        self.assertEqual(result['coverage']['missing'], 7)
        summaries = result['valid_subset_diagnostic']['by_p_specialist']
        summary = summaries[packet['p_specialist']]
        self.assertEqual(summary['valid_diagnostic_mass'], packet['diagnostic_mass'])
        self.assertEqual(summary['diagnostic_mass_coverage'], packet['diagnostic_weight'])
        self.assertEqual(F(summary['conditional_excess_brier']), (probability-F(packet['reference_p_positive']))**2)
        other = next(value for key, value in summaries.items() if key != packet['p_specialist'])
        self.assertEqual(other['valid_diagnostic_mass'], '0')
        self.assertIsNone(other['expected_brier'])
        self.assertTrue(all(pair['probability_sum_minus_one'] is None for pair in result['contrasts']['sign_symmetry']))
        predictions = dict(self.oracle)
        del predictions[packet['packet_id']]
        partial = c.score_predictions(self.fixture, predictions, {packet['packet_id']: 'native_error'})
        self.assertIsNone(partial['primary'])
        self.assertEqual(partial['coverage']['failure_types'], {'native_error': 1})

    def test_frozen_parser_and_failures_are_not_repaired(self):
        self.assertIs(c.parse_probability, c.frozen.parse_probability)
        ids = self.fixture['request_order']
        result = c.score_responses(self.fixture, {ids[0]: '{"p_positive":"0.5"}',
                                                 ids[1]: '{"p_positive":0.125}'}, {ids[2]: 'timeout'})
        self.assertEqual(result['coverage'], {'planned': 8, 'valid': 1, 'invalid': 2, 'missing': 5,
                                              'failure_types': {'not_number': 1, 'timeout': 1}})
        for predictions in ({'unknown': F(1, 2)}, {ids[0]: 0.5}, {ids[0]: True}, {ids[0]: F(2)}):
            with self.assertRaises(ValueError):
                c.score_predictions(self.fixture, predictions)
        with self.assertRaises(ValueError):
            c.score_predictions(self.fixture, {ids[0]: F(1, 2)}, {ids[0]: 'error'})
        self.assertIsNone(c.score_predictions(self.fixture, {})['primary'])


class PreparationTests(unittest.TestCase):
    def test_exclusive_outputs_and_source_custody(self):
        with tempfile.TemporaryDirectory(dir=c.ROOT / 'results') as directory:
            root = Path(directory)
            protocol = root / 'test-protocol.md'
            protocol.write_text('Test-only protocol.\n')
            digest = hashlib.sha256(protocol.read_bytes()).hexdigest()
            output = root / 'prepared'
            fixture, manifest = c.prepare_fixture(output, protocol, digest)
            manifest_digest = hashlib.sha256((output / 'manifest.json').read_bytes()).hexdigest()
            self.assertEqual(c.validate_fixture_custody(output, manifest_digest), (fixture, manifest))
            for source in (c.CODE, c.TESTS, c.DESIGN, c.frozen.CODE, c.frozen.TESTS):
                self.assertIn(source, manifest['source_sha256_start'])
            self.assertEqual(set(path.name for path in output.iterdir()),
                             {'fixture.json', 'manifest-start.json', 'manifest.json'})
            with self.assertRaises(FileExistsError):
                c.prepare_fixture(output, protocol, digest)
            with self.assertRaisesRegex(ValueError, 'manifest hash mismatch'):
                c.validate_fixture_custody(output, '0'*64)
            changed = json.loads((output / 'fixture.json').read_text())
            changed['request_order'].reverse()
            (output / 'fixture.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'output hash mismatch'):
                c.validate_fixture_custody(output)
            (output / 'fixture.json').write_text(json.dumps(fixture))
            protocol.write_text('Changed test protocol.\n')
            with self.assertRaisesRegex(ValueError, 'source custody mismatch'):
                c.validate_fixture_custody(output)

    def test_protocol_hash_and_midprepare_change_guards(self):
        with tempfile.TemporaryDirectory(dir=c.ROOT / 'results') as directory:
            root = Path(directory)
            protocol = root / 'test-protocol.md'
            protocol.write_text('Test-only protocol.\n')
            digest = hashlib.sha256(protocol.read_bytes()).hexdigest()
            output = root / 'prepared'
            with self.assertRaisesRegex(ValueError, 'protocol hash mismatch'):
                c.prepare_fixture(output, protocol, '0'*64)
            self.assertFalse(output.exists())
            original = c._source_hashes(protocol)
            changed = dict(original, **{c.CODE: '0'*64})
            with mock.patch.object(c, '_source_hashes', side_effect=[original, changed]):
                with self.assertRaisesRegex(ValueError, 'source changed'):
                    c.prepare_fixture(output, protocol, digest)
            self.assertTrue((output / 'manifest-invalid.json').exists())
            self.assertFalse((output / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
