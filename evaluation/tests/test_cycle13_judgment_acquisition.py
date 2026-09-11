"""Exhaustive small-instance proofs and synthetic-only cycle13 I/O checks."""
from fractions import Fraction
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle13_judgment_acquisition as m


def metric(ranking, grades):
    return sum((Fraction(1, 5) * Fraction(4, 5) ** index * Fraction(grades[doc], 3)
                for index, doc in enumerate(ranking[:10])), Fraction())


def synthetic_runs():
    lexical = ['d' + str(index) for index in range(30)]
    source = ['d' + str(index) for index in range(29, -1, -1)]
    source.extend('s' + str(index) for index in range(970))
    return {**{name: {'q': list(lexical)} for name in m.LEXICAL}, m.SOURCE_ID: {'q': source}}


class ExactBoundsTests(unittest.TestCase):
    def test_exhaustive_permutations_grade_completions_and_budget_subsets(self):
        docs = ('a', 'b', 'c')
        configurations = 0
        for a in itertools.permutations(docs):
            for b in itertools.permutations(docs):
                completions = []
                for grades in itertools.product(range(4), repeat=3):
                    labels = dict(zip(docs, grades))
                    completions.append((grades, metric(b, labels) - metric(a, labels)))
                # Independent metric perturbations recover each shared-identity coefficient.
                coefficients = {}
                for doc in docs:
                    one = {d: 3 if d == doc else 0 for d in docs}
                    coefficients[doc] = metric(b, one) - metric(a, one)
                for known_values in itertools.product((-1, 0, 1, 2, 3), repeat=3):
                    known = {doc: value for doc, value in zip(docs, known_values) if value >= 0}
                    remaining = [doc for doc in docs if doc not in known]
                    scores = [score for grades, score in completions
                              if all(value < 0 or grades[index] == value
                                     for index, value in enumerate(known_values))]
                    record = m.analyze_query(a, b, known)
                    self.assertEqual((record['lower'], record['upper']), (min(scores), max(scores)))
                    self.assertEqual({d['docid']: d['coefficient'] for d in record['documents']}, coefficients)
                    for budget in m.BUDGETS:
                        plan = record['acquisition'][str(budget)]
                        realized = min(budget, len(remaining))
                        subsets = list(itertools.combinations(remaining, realized))
                        widths = [sum((abs(coefficients[doc]) for doc in remaining if doc not in selected),
                                      Fraction()) for selected in subsets]
                        self.assertEqual(plan['absolute_influence']['projected_width'], min(widths))
                        self.assertEqual(plan['uniform']['expected_projected_width'],
                                         sum(widths, Fraction()) / len(widths))
                        for policy in ('absolute_influence', 'pooled_head'):
                            selected = plan[policy]['selected_docids']
                            # All grade outcomes of these labels remove the same width.
                            for added in itertools.product(range(4), repeat=len(selected)):
                                constrained = {**known, **dict(zip(selected, added))}
                                future_scores = [score for grades, score in completions
                                                 if all(grades[docs.index(doc)] == grade
                                                        for doc, grade in constrained.items())]
                                self.assertEqual(max(future_scores) - min(future_scores),
                                                 plan[policy]['projected_width'])
                    configurations += 1
        self.assertEqual(configurations, 4500)

    def test_support_changes_known_zero_and_unknown_zero_coefficient(self):
        record = m.analyze_query(['a', 'b'], ['a', 'c'], {})
        self.assertEqual(record['counts']['unknown'], 3)
        self.assertEqual(record['counts']['unknown_zero_coefficient'], 1)
        self.assertEqual(record['width'], Fraction(8, 25))
        plan = record['acquisition']['1']
        self.assertEqual(plan['absolute_influence']['selected_docids'], ['b'])
        self.assertEqual(plan['pooled_head']['selected_docids'], ['a'])
        self.assertEqual(plan['absolute_influence']['projected_width'], Fraction(4, 25))
        self.assertEqual(plan['pooled_head']['projected_width'], Fraction(8, 25))
        self.assertEqual(plan['uniform']['expected_projected_width'], Fraction(16, 75))
        self.assertEqual(plan['overlap'], {'equal_selected_sets': False, 'intersection_size': 0})
        known_zero = m.analyze_query(['a'], ['b'], {'a': 0})
        unknown = m.analyze_query(['a'], ['b'], {})
        self.assertEqual(known_zero['counts']['known'], 1)
        self.assertEqual((known_zero['lower'], known_zero['upper']), (0, Fraction(1, 5)))
        self.assertEqual(known_zero['status'], 'unresolved')
        self.assertEqual(unknown['width'] - known_zero['width'], Fraction(1, 5))

    def test_swap_signs_and_strict_zero_boundary(self):
        a, b, grades = ['a', 'b', 'c'], ['c', 'd', 'a'], {'a': 0, 'b': 3, 'd': 2}
        one, reverse = m.analyze_query(a, b, grades), m.analyze_query(b, a, grades)
        self.assertEqual((reverse['lower'], reverse['upper']), (-one['upper'], -one['lower']))
        self.assertEqual(reverse['width'], one['width'])
        for lower, upper, expected in ((1, 2, 'b_better'), (-2, -1, 'a_better'),
                                       (0, 0, 'tie'), (0, 1, 'unresolved'),
                                       (-1, 0, 'unresolved'), (-1, 1, 'unresolved')):
            self.assertEqual(m.classify_interval(Fraction(lower), Fraction(upper)), expected)

    def test_cutoff_without_tail_or_renormalization_and_string_ties(self):
        ranking = [str(i) for i in range(12)]
        weights = m.rank_weights(ranking)
        self.assertEqual(len(weights), 10)
        self.assertEqual(sum(weights.values()), 1 - Fraction(4, 5) ** 10)
        self.assertEqual(m.analyze_query(ranking, ranking, {})['counts']['union'], 10)
        tied = m.analyze_query(['2'], ['10'], {})
        self.assertEqual(tied['acquisition']['1']['absolute_influence']['selected_docids'], ['10'])
        self.assertEqual(tied['acquisition']['1']['pooled_head']['selected_docids'], ['10'])

    def test_zero_width_empty_pools_and_forced_budget_caps(self):
        empty = m.analyze_query([], [], {})
        cancelled = m.analyze_query(['x'], ['x'], {})
        known = m.analyze_query(['a'], ['b'], {'a': 3, 'b': 3})
        for record in (empty, cancelled, known):
            self.assertEqual(record['width'], 0)
            for plan in record['acquisition'].values():
                self.assertEqual(plan['absolute_influence']['projected_width'], 0)
                self.assertEqual(plan['uniform']['expected_projected_width'], 0)
        self.assertEqual(empty['acquisition']['3']['realized_budget'], 0)
        self.assertEqual(cancelled['acquisition']['3']['realized_budget'], 1)
        self.assertEqual(cancelled['acquisition']['3']['absolute_influence']['selected_docids'], ['x'])
        annual = m.summarize_queries({'a': empty, 'b': cancelled, 'c': known}, 2019)
        overlap = annual['acquisition']['3']['selected_set_overlap']
        self.assertEqual(overlap['identical_set_query_count'], 3)
        self.assertEqual(overlap['nonempty_pool_query_count'], 1)
        self.assertEqual(overlap['both_selections_empty_query_count'], 2)

    def test_ranking_and_grade_rejection(self):
        for ranking in (['a', 'a'], ['a', 2], 'abc', {'a', 'b'}, ['']):
            with self.subTest(ranking=ranking), self.assertRaises(ValueError):
                m.analyze_query(ranking, ['b'], {})
        for grades in ({'a': True}, {'a': 4}, {'a': -1}, {'a': 1.5}, {'a': '0'}):
            with self.subTest(grades=grades), self.assertRaises(ValueError):
                m.analyze_query(['a'], ['b'], grades)


class CohortAndInputTests(unittest.TestCase):
    def test_full_source_lists_reach_canonical_floating_fusion(self):
        runs = synthetic_runs()
        actual = m.canonical_rrf
        observed_lengths = []
        def observed(lists, **kwargs):
            observed_lengths.append([len(source) for source in lists])
            return actual(lists, **kwargs)
        with patch.object(m, 'canonical_rrf', side_effect=observed):
            summary, records = m.analyze_year(runs, {}, 2019, expected_count=1)
        self.assertEqual(observed_lengths, [[30] * 4, [30] * 4 + [1000]])
        self.assertEqual(summary['query_count'], 1)
        self.assertEqual(summary['query_ids'], ['q'])
        self.assertEqual(summary['mean_lower'], records['q']['lower'])
        self.assertEqual(records['q']['counts']['known'], 0)
        # The imported float-score tie contract uses ascending string IDs.
        self.assertEqual(m.canonical_rrf([['2', '10'], ['10', '2']]), ['10', '2'])

    def test_cohort_depth_and_qrel_validation_do_not_drop_queries(self):
        runs = synthetic_runs()
        with self.assertRaisesRegex(ValueError, 'query count'):
            m.analyze_year(runs, {}, 2019)
        short = {name: {qid: list(docs) for qid, docs in queries.items()} for name, queries in runs.items()}
        short[m.LEXICAL[0]]['q'].pop()
        with self.assertRaisesRegex(ValueError, 'depth'):
            m.analyze_year(short, {}, 2019, expected_count=1)
        different = {name: dict(queries) for name, queries in runs.items()}
        different[m.SOURCE_ID] = {'other': runs[m.SOURCE_ID]['q']}
        with self.assertRaisesRegex(ValueError, 'query sets differ'):
            m.analyze_year(different, {}, 2019, expected_count=1)
        with self.assertRaisesRegex(ValueError, 'invalid document ID or grade'):
            m.analyze_year(runs, {'unmatched_qid': {'x': True}}, 2019, expected_count=1)

    def test_strict_reused_serialized_readers(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / 'run.txt'
            run.write_text('q Q0 a 0 2 tag\nq Q0 b 1 1 tag\n')
            self.assertEqual(m.read_ranked_run(run, 0), {'q': ['a', 'b']})
            with self.assertRaises(ValueError):
                m.read_ranked_run(run, 1)
            for text in ('q Q0 a 0 2 tag\nq Q0 a 1 1 tag\n',
                         'q Q0 a 0 2 tag\nq Q0 b 1 3 tag\n', 'q Q0 a 0 nan tag\n'):
                run.write_text(text)
                with self.assertRaises(ValueError):
                    m.read_ranked_run(run, 0)
            qrels = Path(directory) / 'qrels.txt'
            qrels.write_text('q 0 a 0\nq 0 b 3\n')
            self.assertEqual(m.read_qrels(qrels), {'q': {'a': 0, 'b': 3}})
            for text in ('q 0 a 0\nq 0 a 3\n', 'q 0 a -1\n', 'q 0 a 1.5\n'):
                qrels.write_text(text)
                with self.assertRaises(ValueError):
                    m.read_qrels(qrels)

    def test_annual_bounds_equal_query_weighting_and_exact_serialization(self):
        records = {'q1': m.analyze_query(['a'], ['b'], {'a': 0, 'b': 3}),
                   'q2': m.analyze_query(['a', 'b'], ['a', 'b'], {})}
        summary = m.summarize_queries(records, 2020)
        self.assertEqual((summary['mean_lower'], summary['mean_upper']), (Fraction(1, 10), Fraction(1, 10)))
        self.assertEqual(summary['annual_mean_status'], 'b_better')
        self.assertEqual(summary['query_status_counts'], {'b_better': 1, 'a_better': 0, 'tie': 1, 'unresolved': 0})
        serialized = json.loads(m.canonical_json(summary))
        self.assertEqual(serialized['mean_lower'], '1/10')
        self.assertEqual(serialized['mean_width'], '0')

    def test_cli_io_on_isolated_synthetic_files_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = synthetic_runs()
            for year in m.YEARS:
                base = root / 'data' / ('trec-dl-' + str(year))
                (base / 'runs').mkdir(parents=True)
                for name in m.SOURCES:
                    path = (base / 'runs' / (name + '.txt') if name in m.LEXICAL else
                            root / 'data/cycle02/acquired' / ('dl' + str(year) + '.trec'))
                    path.parent.mkdir(parents=True, exist_ok=True)
                    origin = 0 if name in m.LEXICAL else 1
                    text = ''.join(f'q Q0 {doc} {index + origin} {2000 - index} synthetic\n'
                                   for index, doc in enumerate(runs[name]['q']))
                    path.write_text(text)
                (base / (str(year) + 'qrels-pass.txt')).write_text('q 0 d0 0\nq 0 d1 3\n')
            output = root / 'output'
            with patch.object(m, 'EXPECTED_QUERY_COUNTS', {2019: 1, 2020: 1}):
                _, summary, manifest = m.run_audit(output, root=root, command_argv=['synthetic-test'])
            self.assertEqual(set(path.name for path in output.iterdir()), {'per_query.json', 'summary.json', 'manifest.json'})
            self.assertEqual(len(manifest['input_sha256_start']), 12)
            self.assertEqual(manifest['input_sha256_start'], manifest['input_sha256_end'])
            self.assertEqual(manifest['source_sha256_start'], manifest['source_sha256_end'])
            self.assertEqual(manifest['new_labels_acquired'], 0)
            self.assertEqual(summary['years']['2019']['query_count'], 1)
            for name, digest in manifest['artifact_sha256'].items():
                self.assertEqual(m.sha256(output / name), digest)
            with patch.object(m, 'fixed_inputs', side_effect=AssertionError('must not read inputs')):
                with self.assertRaises(FileExistsError):
                    m.run_audit(output, root=root)


if __name__ == '__main__':
    unittest.main()
