"""Exact structural tests for cycle04; CLI artifacts live only in temporary roots.

Run: python3 -B -m unittest discover -s evaluation/tests -p test_cycle04_known_truth.py -v
"""

from collections import defaultdict
import contextlib
from fractions import Fraction
import io
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from evaluation import cycle04_known_truth as fixture


def reference_conditioning(specialist):
    """Direct world masses and observation keys, independent of fixture helpers."""
    blind, aware = defaultdict(lambda: [Fraction(0), Fraction(0)]), defaultdict(lambda: [Fraction(0), Fraction(0)])
    for y, a, b, c, s in product((-1, 1), repeat=5):
        weight = Fraction(1, 2)
        for value, accuracy in ((a, Fraction(7, 10)), (b, Fraction(7, 10)),
                                (c, Fraction(7, 10)), (s, specialist)):
            weight *= accuracy if value == y else 1 - accuracy
        observations = (((a, None, None, s), (0, None, None, 1)),
                        ((a, a, a, s), (0, 0, 0, 1)),
                        ((a, b, c, s), (0, 1, 2, 3)))
        for values, partition in observations:
            for table, key in ((blind, values), (aware, (values, partition))):
                table[key][0] += weight / 3
                table[key][1] += weight / 3 * (y == 1)
    return ({key: positive / mass for key, (mass, positive) in blind.items()},
            {key: positive / mass for key, (mass, positive) in aware.items()})


class ExactModelTests(unittest.TestCase):
    def test_mass_marginals_and_both_bayes_policies_match_independent_conditioning(self):
        for specialist in fixture.SPECIALIST_ACCURACIES:
            parameters = fixture.Parameters(specialist)
            worlds = fixture.enumerate_worlds(parameters)
            self.assertEqual(len(worlds), 32)
            self.assertEqual(sum(weight for _, weight in worlds), 1)
            self.assertEqual(sum(weight for world, weight in worlds if world.y == 1), Fraction(1, 2))
            for position, expected in ((1, Fraction(7, 10)), (2, Fraction(7, 10)),
                                       (3, Fraction(7, 10)), (4, specialist)):
                self.assertEqual(sum(weight for world, weight in worlds if world[position] == world.y), expected)
            blind_reference, aware_reference = reference_conditioning(specialist)
            for world, _ in worlds:
                for arm in fixture.ARMS:
                    blind, aware = fixture.make_packets(world, arm)
                    values = tuple(report.value for report in blind.reports)
                    partition = fixture.canonical_partition(aware)
                    self.assertEqual(fixture.optimal_blind_bayes(blind, parameters), blind_reference[values])
                    self.assertEqual(fixture.optimal_aware_bayes(aware, parameters), aware_reference[(values, partition)])

    def test_information_boundaries_ids_and_unobserved_readings(self):
        self.assertEqual(fixture.BlindPacket._fields, ('reports',))
        self.assertEqual(fixture.AwarePacket._fields, ('reports', 'parent_partition'))
        self.assertEqual(fixture.Report._fields, ('report_id', 'role', 'value'))
        parameters = fixture.Parameters(Fraction(17, 20))
        packets = []
        for world, _ in fixture.enumerate_worlds(parameters):
            for arm in fixture.ARMS:
                blind, aware = fixture.make_packets(world, arm)
                self.assertFalse(hasattr(blind, '__dict__'))
                self.assertEqual(tuple(report.report_id for report in blind.reports), fixture.REPORT_IDS)
                for name, policy in fixture.POLICIES.items():
                    with self.assertRaises(ValueError):
                        policy(blind if name in fixture.AWARE_POLICIES else aware, parameters)
                packets.append(blind)
        # Same visible copied/independent unanimity must have the same blind input.
        world = fixture.World(1, 1, 1, 1, -1)
        copied, _ = fixture.make_packets(world, 'copied')
        independent, _ = fixture.make_packets(world, 'independent')
        self.assertEqual(copied, independent)
        first, _ = fixture.make_packets(fixture.World(-1, 1, -1, -1, -1), 'padded')
        second, _ = fixture.make_packets(fixture.World(1, 1, 1, 1, -1), 'padded')
        self.assertEqual(first, second)

    def test_renaming_sign_swap_and_aware_copy_invariance_exhaustively(self):
        for specialist in fixture.SPECIALIST_ACCURACIES:
            parameters = fixture.Parameters(specialist)
            for world, _ in fixture.enumerate_worlds(parameters):
                for arm in fixture.ARMS:
                    blind, aware = fixture.make_packets(world, arm)
                    renamed_reports = tuple(report._replace(report_id='renamed' + str(index))
                                            for index, report in enumerate(blind.reports))
                    renamed_roots = tuple(None if root is None else 'renamed-' + root for root in aware.parent_partition)
                    renamed_blind = fixture.BlindPacket(renamed_reports)
                    renamed_aware = fixture.AwarePacket(renamed_reports, renamed_roots)
                    inverse_blind, inverse_aware = fixture.make_packets(fixture.World(*(-value for value in world)), arm)
                    for name, policy in fixture.POLICIES.items():
                        original, renamed, inverse = ((aware, renamed_aware, inverse_aware) if name in fixture.AWARE_POLICIES
                                                       else (blind, renamed_blind, inverse_blind))
                        probability = policy(original, parameters)
                        self.assertEqual(policy(renamed, parameters), probability)
                        self.assertEqual(policy(inverse, parameters), 1 - probability)
                _, padded = fixture.make_packets(world, 'padded')
                _, copied = fixture.make_packets(world, 'copied')
                for name in fixture.AWARE_POLICIES:
                    self.assertEqual(fixture.POLICIES[name](padded, parameters), fixture.POLICIES[name](copied, parameters))

    def test_shared_tie_coin_preserves_correction_harm_and_identical_ties(self):
        for probability, baseline, truth in product((Fraction(0), Fraction(1, 2), Fraction(1)),
                                                    (Fraction(0), Fraction(1, 2), Fraction(1)), (-1, 1)):
            actual = fixture.paired_losses(probability, baseline, truth)
            baseline_loss = fixture.paired_losses(baseline, baseline, truth)
            self.assertEqual(actual['correction'] - actual['harm'],
                             baseline_loss['classification_error'] - actual['classification_error'])
            if probability == baseline:
                self.assertEqual((actual['correction'], actual['harm']), (0, 0))
        identical_ties = fixture.paired_losses(Fraction(1, 2), Fraction(1, 2), 1)
        self.assertEqual(identical_ties['classification_error'], Fraction(1, 2))
        tie_to_right = fixture.paired_losses(Fraction(1), Fraction(1, 2), 1)
        self.assertEqual((tie_to_right['correction'], tie_to_right['harm']), (Fraction(1, 2), 0))

    def test_calibration_targets_and_equal_information_coincidences(self):
        positive_generalists = fixture.World(1, 1, 1, 1, -1)
        for specialist in fixture.SPECIALIST_ACCURACIES:
            parameters = fixture.Parameters(specialist)
            for world, _ in fixture.enumerate_worlds(parameters):
                for arm in fixture.ARMS:
                    blind, aware = fixture.make_packets(world, arm)
                    generals = tuple(report.value for report in blind.reports[:3])
                    if arm == 'padded' or len(set(generals)) > 1:
                        self.assertEqual(fixture.optimal_blind_bayes(blind, parameters),
                                         fixture.optimal_aware_bayes(aware, parameters))
            blind, copied = fixture.make_packets(positive_generalists, 'copied')
            _, independent = fixture.make_packets(positive_generalists, 'independent')
            copied_p = fixture.optimal_aware_bayes(copied, parameters)
            independent_p = fixture.optimal_aware_bayes(independent, parameters)
            self.assertEqual(copied_p / (1 - copied_p), Fraction(7, 3) * (1 - specialist) / specialist)
            self.assertEqual(independent_p / (1 - independent_p), Fraction(7, 3) ** 3 * (1 - specialist) / specialist)
            blind_p = fixture.optimal_blind_bayes(blind, parameters)
            self.assertEqual(blind_p / (1 - blind_p), Fraction(1043, 327) * (1 - specialist) / specialist)
            self.assertEqual(fixture.protected_minority(blind, parameters), 1 - specialist)

    def test_reject_invalid_packets_partitions_and_unfrozen_parameters(self):
        parameters = fixture.Parameters(Fraction(11, 20))
        blind, aware = fixture.make_packets(fixture.World(1, 1, 1, 1, -1), 'copied')
        bad_reports = (blind.reports[0]._replace(value=True),) + blind.reports[1:]
        with self.assertRaises(ValueError):
            fixture.optimal_blind_bayes(fixture.BlindPacket(bad_reports), parameters)
        with self.assertRaises(ValueError):
            fixture.optimal_blind_bayes(blind, fixture.Parameters(Fraction(3, 4)))
        with self.assertRaises(ValueError):
            fixture.optimal_blind_bayes(blind, parameters._replace(truth_prior_positive=0.5))
        with self.assertRaises(ValueError):
            fixture.optimal_aware_bayes(aware._replace(parent_partition=('same',) * 4), parameters)
        with self.assertRaises(ValueError):
            fixture.optimal_aware_bayes(aware._replace(parent_partition=('a', 'a', 'b', 'c')), parameters)

    def test_all_rows_aggregates_and_conditional_expectation_brier_identity(self):
        summary, per_world = fixture.build_results()
        self.assertEqual(len(per_world['rows']), 192)
        expected_order = [(str(p), 'w{:02d}'.format(i), arm) for p in fixture.SPECIALIST_ACCURACIES
                          for i in range(32) for arm in fixture.ARMS]
        self.assertEqual([(row['p_specialist'], row['world_id'], row['arm']) for row in per_world['rows']], expected_order)
        for specialist in fixture.SPECIALIST_ACCURACIES:
            key = str(specialist)
            mixture = summary['mixtures'][key]
            self.assertEqual(Fraction(mixture['probability_mass']), 1)
            self.assertEqual(-Fraction(mixture['aware_minus_blind']['brier_loss']), Fraction(mixture['posterior_squared_gap']))
            for name in fixture.POLICIES:
                metrics = mixture['policies'][name]
                for metric in fixture.METRICS:
                    cell_mean = sum(Fraction(summary['cells'][key][arm]['policies'][name][metric]) for arm in fixture.ARMS) / 3
                    self.assertEqual(Fraction(metrics[metric]), cell_mean)
                    self.assertEqual(str(Fraction(metrics[metric])), metrics[metric])
                baseline_error = Fraction(mixture['policies'][fixture.BASELINE]['classification_error'])
                self.assertEqual(Fraction(metrics['correction']) - Fraction(metrics['harm']),
                                 baseline_error - Fraction(metrics['classification_error']))
            for name in fixture.AWARE_POLICIES:
                self.assertEqual(summary['copy_invariance'][key][name]['changed_count'], 0)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in (fixture.PROTOCOL, fixture.DESIGN, fixture.CODE, fixture.TESTS):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((fixture.ROOT / name).read_bytes())
        self.root_patch = mock.patch.object(fixture, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.git_patch = mock.patch.object(fixture, 'git_state', return_value={'head': 'synthetic-head', 'dirty_status': []})
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)

    def run_cli(self, output='results/fixture'):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            fixture.main(['--output', output])

    def read(self, name):
        return json.loads((self.root / 'results/fixture' / name).read_text(encoding='utf-8'))

    def test_complete_manifest_hashes_all_sources_and_outputs_and_refuses_overwrite(self):
        self.run_cli()
        start, final = self.read('manifest-start.json'), self.read('manifest.json')
        self.assertEqual(start['status'], 'started')
        self.assertEqual(final['status'], 'complete')
        self.assertTrue(final['sources_unchanged'])
        self.assertEqual(final['source_sha256_start'], final['source_sha256_end'])
        self.assertEqual(set(final['source_sha256_start']), {fixture.PROTOCOL, fixture.DESIGN, fixture.CODE, fixture.TESTS})
        self.assertEqual(set(final['output_sha256']), {'manifest-start.json', 'summary.json', 'per_world.json'})
        for name, digest in final['output_sha256'].items():
            self.assertEqual(fixture.sha256(self.root / 'results/fixture' / name), digest)
        final_hash = fixture.sha256(self.root / 'results/fixture/manifest.json')
        with self.assertRaises(SystemExit):
            self.run_cli()
        self.assertEqual(fixture.sha256(self.root / 'results/fixture/manifest.json'), final_hash)

    def test_changed_frozen_protocol_fails_before_enumeration_with_invalid_manifest(self):
        (self.root / fixture.PROTOCOL).write_text('tampered protocol\n', encoding='utf-8')
        with mock.patch.object(fixture, 'build_results') as build:
            with self.assertRaisesRegex(ValueError, 'frozen input hash mismatch'):
                self.run_cli()
            build.assert_not_called()
        self.assertEqual(self.read('manifest-invalid.json')['status'], 'invalid')
        self.assertFalse((self.root / 'results/fixture/summary.json').exists())
        self.assertFalse((self.root / 'results/fixture/manifest.json').exists())

    def test_mid_run_code_change_is_invalid_and_preserves_partial_outputs(self):
        original = fixture.build_results

        def change_source():
            result = original()
            (self.root / fixture.CODE).write_text('changed during execution\n', encoding='utf-8')
            return result

        with mock.patch.object(fixture, 'build_results', side_effect=change_source):
            with self.assertRaisesRegex(RuntimeError, 'changed during execution'):
                self.run_cli()
        final = self.read('manifest-invalid.json')
        self.assertEqual(final['status'], 'invalid')
        self.assertFalse(final['sources_unchanged'])
        self.assertNotEqual(final['source_sha256_start'][fixture.CODE], final['source_sha256_end'][fixture.CODE])
        self.assertTrue((self.root / 'results/fixture/per_world.json').exists())
        self.assertFalse((self.root / 'results/fixture/manifest.json').exists())

    def test_failed_enumeration_missing_source_and_escaping_output_fail_closed(self):
        with mock.patch.object(fixture, 'build_results', side_effect=RuntimeError('injected failure')):
            with self.assertRaisesRegex(RuntimeError, 'injected failure'):
                self.run_cli()
        self.assertEqual(self.read('manifest-invalid.json')['status'], 'invalid')
        with self.assertRaises(SystemExit):
            self.run_cli('outside-results')
        self.assertFalse((self.root / 'outside-results').exists())
        (self.root / fixture.TESTS).unlink()
        with self.assertRaises(SystemExit):
            self.run_cli('results/missing-source')
        self.assertFalse((self.root / 'results/missing-source').exists())

    def test_symlinked_results_cannot_escape_the_repository(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'results').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(SystemExit):
                self.run_cli()
            self.assertEqual(list(Path(outside).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
