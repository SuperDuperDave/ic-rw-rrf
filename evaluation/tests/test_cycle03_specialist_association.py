"""Synthetic cycle03 tests only. Never open actual research qrels.

Run: python3 -B -m unittest discover -s evaluation/tests -p test_cycle03_specialist_association.py -v
"""

import contextlib
from fractions import Fraction
import hashlib
import io
import itertools
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

from evaluation import cycle03_specialist_association as association


def candidates(supported, isolated, grades):
    return [{'docid': doc, 'group': group, 'judged': doc in grades}
            for group, docs in zip(association.GROUPS, (supported, isolated)) for doc in docs]


class ArithmeticTests(unittest.TestCase):
    def test_entirely_missing_and_fully_observed(self):
        for grades, expected in (({}, (-1, 1)), ({'s': 3, 'i': 0}, (1, 1)),
                                 ({'s': 0, 'i': 2}, (-1, -1)), ({'s': 2, 'i': 3}, (0, 0))):
            result = association.query_outcome(candidates(['s'], ['i'], grades), grades, 2)
            self.assertEqual((result['contrast']['lower'], result['contrast']['upper']), expected)
            self.assertEqual(result['contrast']['width'], result['contrast']['missing_fraction_sum'])

    def test_exhaustive_missing_label_completions_attain_both_sharp_extrema(self):
        # Independent enumeration has no endpoint formula and uses exact fractions.
        checked = 0
        for ns, ni in itertools.product(range(1, 4), repeat=2):
            supported = ['s' + str(i) for i in range(ns)]
            isolated = ['i' + str(i) for i in range(ni)]
            docs = supported + isolated
            for states in itertools.product((None, 0, 2), repeat=len(docs)):
                grades = {doc: grade for doc, grade in zip(docs, states) if grade is not None}
                unknown = [doc for doc in docs if doc not in grades]
                possible = []
                for labels in itertools.product((0, 1), repeat=len(unknown)):
                    known = {doc: int(grade >= 2) for doc, grade in grades.items()}
                    known.update(zip(unknown, labels))
                    possible.append(Fraction(sum(known[doc] for doc in supported), ns) -
                                    Fraction(sum(known[doc] for doc in isolated), ni))
                actual = association.query_outcome(candidates(supported, isolated, grades), grades, 2)['contrast']
                self.assertAlmostEqual(actual['lower'], float(min(possible)))
                self.assertAlmostEqual(actual['upper'], float(max(possible)))
                checked += 1
        self.assertEqual(checked, 1521)

    def test_equal_query_mean_differs_from_pooled_documents(self):
        qrels = {'a': {'as': 3, 'ai': 0},
                 'b': dict([('bs' + str(i), 0) for i in range(9)] + [('bi', 3)])}
        cohorts = {'a': candidates(['as'], ['ai'], qrels['a']),
                   'b': candidates(['bs' + str(i) for i in range(9)], ['bi'], qrels['b'])}
        summary, _ = association.analyze_year(cohorts, qrels, replicates=5)
        interval = summary['outcomes'][association.PRIMARY]['empirical_sharp_interval']
        self.assertEqual(interval['lower'], 0)
        self.assertEqual(interval['upper'], 0)
        pooled_contrast = Fraction(1, 10) - Fraction(1, 2)
        self.assertNotEqual(interval['lower'], pooled_contrast)

    def test_candidate_eligibility_preserves_fully_unjudged_group_and_excluded_rows(self):
        qrels = {'paired': {'s': 2}, 'only_s': {'s': 2}, 'empty': {'other': 0}}
        cohorts = {'paired': candidates(['s'], ['i'], qrels['paired']),
                   'only_s': candidates(['s'], [], qrels['only_s']), 'empty': []}
        summary, rows = association.analyze_year(cohorts, qrels, replicates=4)
        self.assertEqual(summary['eligible_qids'], ['paired'])
        self.assertEqual(summary['excluded_qids'], ['empty', 'only_s'])
        self.assertEqual(summary['all_qids'], ['empty', 'only_s', 'paired'])
        self.assertEqual(rows['paired']['outcomes'][association.PRIMARY]['groups']['isolated']['u'], 1)
        self.assertIsNone(rows['only_s']['outcomes'][association.PRIMARY]['contrast'])
        self.assertEqual(rows['empty']['missing_candidate_groups'], list(association.GROUPS))

    def test_primary_secondary_thresholds_and_width_membership(self):
        grades = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'i': 0}
        cohort = candidates(['zero', 'one', 'two', 'three', 'missing'], ['i'], grades)
        summary, rows = association.analyze_year({'q': cohort}, {'q': grades}, replicates=3)
        primary, secondary = (rows['q']['outcomes'][name] for name in association.OUTCOMES)
        self.assertEqual(primary['groups']['tail_supported']['r'], 2)
        self.assertEqual(secondary['groups']['tail_supported']['r'], 3)
        self.assertEqual(primary['groups']['tail_supported']['u'], 1)
        self.assertAlmostEqual(primary['contrast']['width'], secondary['contrast']['width'])
        self.assertIn('interpretation', summary['outcomes']['grade_ge_2'])
        self.assertNotIn('interpretation', summary['outcomes']['grade_gt_0'])

    def test_invalid_threshold_grades_duplicate_candidates_and_membership(self):
        for threshold in (0, 3, 1.5, True, '2'):
            with self.assertRaises(ValueError):
                association.group_bounds(['d'], {'d': 1}, threshold)
        for grade in (-1, 4, 2.0, True, '2'):
            with self.assertRaises(ValueError):
                association.group_bounds(['d'], {'d': grade}, 2)
        with self.assertRaises(ValueError):
            association.group_bounds(['d', 'd'], {'d': 1}, 2)
        with self.assertRaises(ValueError):
            association.query_outcome(candidates(['d'], ['d'], {}), {}, 2)
        for mutation in ({'judged': 1}, {'judged': True}, {'group': 'selected'}):
            cohort = candidates(['s'], ['i'], {})
            cohort[0].update(mutation)
            with self.assertRaises(ValueError):
                association.query_outcome(cohort, {}, 2)


class BootstrapTests(unittest.TestCase):
    def test_exact_prescribed_draws_lexicographic_order_hash_and_per_year_reset(self):
        draws, receipt = association.bootstrap_indices(['2', '1', '10'], replicates=10000)
        rng = random.Random(42)
        reference = [[rng.randrange(3) for _ in range(3)] for _ in range(10000)]
        self.assertEqual(draws, reference)
        self.assertEqual(draws[:2], [[2, 0, 0], [2, 1, 0]])
        self.assertEqual(receipt['sorted_qids'], ['1', '10', '2'])
        expected_hash = hashlib.sha256(json.dumps(reference, separators=(',', ':')).encode('utf-8')).hexdigest()
        self.assertEqual(receipt['indices_sha256'], expected_hash)
        self.assertEqual(draws, association.bootstrap_indices(['10', '2', '1'])[0])

    def test_same_draws_couple_endpoints_groups_and_both_thresholds(self):
        grades = {'a': {'s': 1, 'i': 0}, 'b': {'s': 2, 'i': 1}, 'c': {'i': 2}}
        cohorts = {qid: candidates(['s'], ['i'], values) for qid, values in grades.items()}
        prescribed = [[0, 0, 0], [2, 2, 2], [1, 0, 2], [2, 1, 2]]
        with mock.patch.object(association, 'bootstrap_indices', return_value=(prescribed, {'fixture': True})) as make_draws:
            summary, rows = association.analyze_year(cohorts, grades, replicates=4)
        make_draws.assert_called_once()
        for name in association.OUTCOMES:
            bounds = [rows[qid]['outcomes'][name]['contrast'] for qid in sorted(rows)]
            for endpoint in ('lower', 'upper'):
                expected = [sum(bounds[index][endpoint] for index in draw) / 3 for draw in prescribed]
                actual = summary['outcomes'][name]['bootstrap'][endpoint + '_endpoint_quantiles']
                for p in (0.025, 0.975):
                    self.assertAlmostEqual(actual[str(p)], association.quantile(expected, p))
            envelope = summary['outcomes'][name]['bootstrap']['exploratory_uncertainty_envelope']
            self.assertLessEqual(envelope['lower'], envelope['upper'])

    def test_linear_quantile_and_null_collapse(self):
        self.assertEqual(association.quantile([10, 0], .025), .25)
        self.assertEqual(association.quantile([10, 0], .975), 9.75)
        self.assertEqual(association.quantile([3], .4), 3)
        grades = {'s': 3, 'i': 3}
        summary, _ = association.analyze_year({'q': candidates(['s'], ['i'], grades)}, {'q': grades}, replicates=8)
        primary = summary['outcomes'][association.PRIMARY]
        self.assertEqual(primary['interpretation'], 'small_under_chosen_bound')
        self.assertEqual(primary['bootstrap']['exploratory_uncertainty_envelope'], {'lower': 0, 'upper': 0, 'width': 0})

    def test_decision_boundaries_and_secondary_cannot_advance_gate(self):
        cases = [(0.100001, .2, 'material_positive'), (-.2, -.100001, 'material_negative'),
                 (.1, .2, 'inconclusive'), (-.2, -.1, 'inconclusive'),
                 (-.05, .05, 'small_under_chosen_bound'), (-.1, 0, 'small_under_chosen_bound'),
                 (0, .1, 'small_under_chosen_bound'), (-.1, .1, 'inconclusive'),
                 (-.05, .050001, 'inconclusive')]
        for lower, upper, expected in cases:
            self.assertEqual(association.interpret_envelope(lower, upper), expected)
        for first, second in itertools.product(('material_positive', 'material_negative',
                                                'inconclusive', 'small_under_chosen_bound'), repeat=2):
            result = association.branch_decision([first, second])
            self.assertEqual(result.startswith('advance'), first == second and first.startswith('material_'))
        for lower, upper in ((1, 0), (float('nan'), 0), (0, float('inf'))):
            with self.assertRaises(ValueError):
                association.interpret_envelope(lower, upper)


def write_file(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def write_json(root, name, value):
    return write_file(root, name, json.dumps(value, sort_keys=True) + '\n')


def fixture_repository(root):
    """A wholly synthetic two-year cycle02 custody chain with 3/2 query counts."""
    observation = association.observation
    for name in ('evaluation/cycle03_specialist_association.py',
                 'evaluation/tests/test_cycle03_specialist_association.py',
                 'evaluation/cycle02_observation_audit.py', association.PROTOCOL,
                 '_sessions/cycles/2026-09-10-cycle02-observation-protocol.md'):
        write_file(root, name, 'Synthetic fixture placeholder\n')
    selection = {'source_id': association.SOURCE_ID, 'dataset_id': 'synthetic', 'dataset_revision': 'fixture'}
    selection_path = write_json(root, association.SELECTION, selection)
    acquired = dict(selection, selection_sha256=observation.sha256(selection_path), derived_runs=[])
    all_rows, all_summaries = {}, {}
    for year in association.YEARS:
        qrels = {'10': {'s': 0, 'i': 1}, '2': {'s': 2}, '3': {'i': 0}}
        runs = {name: {} for name in (*observation.LEXICAL, association.SOURCE_ID)}
        for qid in qrels:
            for name in observation.LEXICAL:
                runs[name][qid] = [name + '-' + str(i) for i in range(32)]
            if qid != '3':
                runs['bm25'][qid][30] = 's'
                runs[association.SOURCE_ID][qid] = ['s', 'i']
            else:
                runs[association.SOURCE_ID][qid] = ['i']
        for name, queries in runs.items():
            origin = 1 if name == association.SOURCE_ID else 0
            relative = ('data/cycle02/acquired/dl{}.trec'.format(year) if origin else
                        'data/trec-dl-{}/runs/{}.txt'.format(year, name))
            text = ''.join('{} Q0 {} {} {} synthetic\n'.format(qid, doc, index + origin, len(docs) - index)
                           for qid, docs in queries.items() for index, doc in enumerate(docs))
            path = write_file(root, relative, text)
            if origin:
                acquired['derived_runs'].append({'year': year, 'path': relative, 'sha256': observation.sha256(path)})
        write_file(root, 'data/trec-dl-{0}/{0}qrels-pass.txt'.format(year),
                   ''.join('{} Q0 {} {}\n'.format(qid, doc, grade)
                           for qid, grades in qrels.items() for doc, grade in grades.items()))
        all_summaries[str(year)], all_rows[str(year)] = observation.summarize_year(
            year, association.SOURCE_ID, runs, {qid: set(grades) for qid, grades in qrels.items()})
    write_json(root, association.ACQUIRED, acquired)
    obs = association.OBSERVATIONS
    write_json(root, obs + '/summary.json', {'source_id': association.SOURCE_ID, 'years': all_summaries})
    write_json(root, obs + '/per_query.json', all_rows)
    write_json(root, obs + '/manifest-start.json', {'status': 'started'})
    old_sources = [root / name for name in (association.ACQUIRED, association.SELECTION,
                   'evaluation/cycle02_observation_audit.py',
                   '_sessions/cycles/2026-09-10-cycle02-observation-protocol.md')]
    # fixed_paths needs manifest.json to exist before enumerating the input files.
    write_json(root, obs + '/manifest.json', {})
    _, data, _ = association.fixed_paths(root, root / association.PROTOCOL)
    sources, inputs = observation.hash_paths(old_sources, root), observation.hash_paths(data, root)
    manifest = {'status': 'complete', 'sources_and_inputs_unchanged': True,
                'source_id': association.SOURCE_ID, 'source_sha256_start': sources, 'source_sha256_end': sources,
                'input_sha256_start': inputs, 'input_sha256_end': inputs,
                'output_sha256': {name: observation.sha256(root / obs / name)
                                  for name in ('summary.json', 'per_query.json', 'manifest-start.json')}}
    return observation.sha256(write_json(root, obs + '/manifest.json', manifest))


class InputAndCustodyTests(unittest.TestCase):
    def test_strict_qrel_reader_including_zero_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_file(root, 'qrels', 'q Q0 zero 0\nq Q0 one 1\nq Q0 two 2\nq Q0 three 3\n')
            self.assertEqual(association.read_qrels(path)['q'], {'zero': 0, 'one': 1, 'two': 2, 'three': 3})
            for raw in ('', 'q Q0 d -1\n', 'q Q0 d 4\n', 'q Q0 d 2.0\n', 'q Q0 d nan\n',
                        'q Q0 d 2 extra\n', 'q Q0 d 0\nq Q0 d 0\n', 'q Q0 d 0\nq Q0 d 2\n'):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    association.read_qrels(path)

    def test_duplicate_json_key_and_output_location_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                association.read_json(write_file(root, 'ambiguous.json', '{"a":1,"a":2}'))
            with self.assertRaises(ValueError):
                association.new_output_directory(root / 'outside', root)
            output = association.new_output_directory(root / 'results/new', root)
            with self.assertRaises(FileExistsError):
                association.new_output_directory(output, root)
            association.observation.write_json(output / 'record.json', {'fixed': 1})
            with self.assertRaises(FileExistsError):
                association.observation.write_json(output / 'record.json', {'fixed': 2})

    def run_fixture(self, root, pinned_hash, output='new'):
        argv = ['--output', str(root / 'results' / output)]
        with mock.patch.object(association, 'ROOT', root), \
                mock.patch.object(association, 'OBS_MANIFEST_SHA256', pinned_hash), \
                mock.patch.object(association, 'EXPECTED_COUNTS', {2019: (3, 2), 2020: (3, 2)}), \
                mock.patch.object(association, 'git_state', return_value={'head': 'synthetic', 'dirty_status': []}), \
                contextlib.redirect_stdout(io.StringIO()):
            association.main(argv)

    def test_synthetic_cli_complete_manifest_all_queries_and_immutable_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pin = fixture_repository(root)
            self.run_fixture(root, pin)
            output = root / 'results/new'
            manifest = association.read_json(output / 'manifest.json')
            summary = association.read_json(output / 'summary.json')
            rows = association.read_json(output / 'per_query.json')
            self.assertEqual(manifest['status'], 'complete')
            self.assertTrue(manifest['sources_and_inputs_unchanged'])
            self.assertEqual(manifest['input_sha256_start'], manifest['input_sha256_end'])
            self.assertEqual(manifest['argv'][1:], ['--output', str(output)])
            self.assertEqual(set(manifest['output_sha256']), {'manifest-start.json', 'summary.json', 'per_query.json'})
            for name, digest in manifest['output_sha256'].items():
                self.assertEqual(association.observation.sha256(output / name), digest)
            for year in ('2019', '2020'):
                self.assertEqual(list(rows[year]), ['10', '2', '3'])
                self.assertEqual(summary['years'][year]['eligible_qids'], ['10', '2'])
                self.assertEqual(summary['years'][year]['excluded_qids'], ['3'])
                self.assertEqual(summary['years'][year]['bootstrap_draws']['B'], 10000)
                self.assertIn('per_query_sha256', summary['years'][year]['frozen_observation_inventory'])
            original = association.observation.sha256(output / 'manifest.json')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.run_fixture(root, pin)
            self.assertEqual(association.observation.sha256(output / 'manifest.json'), original)

    def test_custody_rejects_modified_inputs_outputs_or_manifest_before_reading_grades(self):
        targets = ('data/trec-dl-2019/2019qrels-pass.txt', association.SELECTION, association.ACQUIRED,
                   association.OBSERVATIONS + '/per_query.json', association.OBSERVATIONS + '/manifest.json')
        for target in targets:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                pin = fixture_repository(root)
                path = root / target
                path.write_text(path.read_text() + '\n')
                with mock.patch.object(association, 'read_qrels') as read_grades, self.assertRaises(ValueError):
                    self.run_fixture(root, pin)
                read_grades.assert_not_called()
                receipt = association.read_json(root / 'results/new/manifest-invalid.json')
                self.assertEqual(receipt['status'], 'invalid')
                self.assertIn('input_sha256_end', receipt)
                self.assertIn('source_sha256_end', receipt)
                self.assertFalse((root / 'results/new/manifest.json').exists())

    def test_frozen_cohort_mutation_rejected_even_with_consistent_rehashed_manifest(self):
        for field, value in (('group', 'isolated'), ('judged', False), ('docid', 'changed')):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture_repository(root)
                obs = root / association.OBSERVATIONS
                frozen = association.read_json(obs / 'per_query.json')
                row = next(row for row in frozen['2019']['10']['arms']['full']['specialist_candidates']
                           if row['owner_source'] == association.SOURCE_ID and row['docid'] == 's')
                row[field] = value
                write_json(root, association.OBSERVATIONS + '/per_query.json', frozen)
                manifest = association.read_json(obs / 'manifest.json')
                manifest['output_sha256']['per_query.json'] = association.observation.sha256(obs / 'per_query.json')
                pin = association.observation.sha256(write_json(root, association.OBSERVATIONS + '/manifest.json', manifest))
                with self.assertRaisesRegex(ValueError, 'SPLADE specialist'):
                    self.run_fixture(root, pin)

    def test_midrun_input_change_produces_invalid_end_hash_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pin = fixture_repository(root)
            original = association.analyze_year
            def mutate_after_analysis(*args, **kwargs):
                result = original(*args, **kwargs)
                path = root / 'data/trec-dl-2019/2019qrels-pass.txt'
                path.write_text(path.read_text() + '\n')
                return result
            with mock.patch.object(association, 'analyze_year', side_effect=mutate_after_analysis), \
                    self.assertRaisesRegex(RuntimeError, 'changed during cycle03'):
                self.run_fixture(root, pin)
            receipt = association.read_json(root / 'results/new/manifest-invalid.json')
            self.assertFalse(receipt['sources_and_inputs_unchanged'])
            self.assertNotEqual(receipt['input_sha256_start'], receipt['input_sha256_end'])
            self.assertFalse((root / 'results/new/manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
