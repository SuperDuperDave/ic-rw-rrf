"""Hand-calculated synthetic audit checks; no collection files or production imports."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("cycle15_results_audit_test", Path(__file__).resolve().parents[1] / "audit_cycle15_results.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class IndependentFormulaTests(unittest.TestCase):
    def test_unicode_token_boundaries_stopwords_and_short_terms(self):
        self.assertEqual(audit.tokenize("THE Gene_βeta café² p53 A naïve 123 ⅣⅥ 中文 ább"),
                         ["gene", "βeta", "café²", "p53", "naïve", "123", "ⅳⅵ", "中文", "bb"])

    def test_union_statistics_count_each_document_once(self):
        corpus = {"d1": ("Gene gene", "cell"), "d2": ("Cell", "cells"), "outside": ("Other", "other")}
        terms, lengths, stats = audit.prepare_terms(corpus, {"d1", "d2"})
        self.assertEqual(lengths, {"d1": 3, "d2": 2})
        self.assertEqual(stats, {"N": 2, "avg_dl": 2.5, "total_terms": 5,
                                 "df": Counter({"gene": 1, "cell": 2, "cells": 1}),
                                 "cf": Counter({"gene": 2, "cell": 2, "cells": 1})})

    def test_four_scores_from_hand_arithmetic_and_query_occurrence_weight(self):
        stats = {"N": 4, "avg_dl": 5, "total_terms": 20,
                 "df": Counter({"gene": 2}), "cf": Counter({"gene": 6})}
        scores = audit.document_scores(["gene", "absent"], Counter({"gene": 2, "cell": 2}), 4, stats)
        bm25 = math.log(2) * (2 * 2.2) / (2 + 1.2 * (.25 + .75 * 4 / 5))
        tuned = math.log(2) * (2 * 1.9) / (2 + .9 * (.6 + .4 * 4 / 5))
        tfidf = (1 + math.log(2)) * math.log(4 / 3) / 2
        ql = math.log((2 + 2000 * .3) / 2004)
        for actual, expected in zip(scores, (bm25, tuned, tfidf, ql)):
            self.assertAlmostEqual(actual, expected, places=14)
        repeated = audit.document_scores(["gene", "gene"], Counter({"gene": 2, "cell": 2}), 4, stats)
        for actual, once in zip(repeated, scores):
            self.assertAlmostEqual(actual, 2 * once, places=14)
        self.assertEqual(audit.document_scores(["gene"], Counter(), 0, stats), (0.0, 0.0, 0.0, -1e10))

    def test_rrf_rank_origin_missing_contributions_and_document_ties(self):
        ranking = audit.fuse([[('z', 100), ('a', 1)], [('a', 999), ('z', 9)]])
        self.assertEqual([doc for doc, _ in ranking], ['a', 'z'])
        self.assertEqual(ranking[0][1], 1 / 61 + 1 / 62)
        self.assertEqual(audit.fuse([[], [('only', 3)]]), [('only', 1 / 61)])

    def test_binary_metric_retains_unjudged_positions_and_unretrieved_idcg(self):
        ranking = [('unjudged', 4), ('yes', 3)]
        grades = {'yes': 1, 'unretrieved': 1}
        expected = (1 / math.log2(3)) / (1 + 1 / math.log2(3))
        self.assertEqual(audit.binary_ndcg(ranking, grades), expected)
        self.assertEqual(audit.binary_ndcg([], grades), 0)
        self.assertEqual(audit.binary_ndcg([('00101', 9)], {'00101': 1}), 1)
        self.assertAlmostEqual(audit.rbp(ranking, grades), .16)
        self.assertEqual(audit.binary_ndcg([(str(i), 0) for i in range(11)], {'10': 1}), 0)

    def test_reconstruct_keeps_source_ties_and_lexical_stability(self):
        corpus = {'z': ('Gene', 'cell'), 'a': ('Gene', 'cell')}
        sources = {'P': {'q': [('z', 1), ('a', 1)]}, 'S': {'q': [('a', 2)]}}
        runs, stats, union = audit.reconstruct(['q'], corpus, {'q': 'gene'}, sources)
        for name in audit.NAMES:
            self.assertEqual([doc for doc, _ in runs[name]['q']], ['z', 'a'])
        self.assertEqual([doc for doc, _ in runs['A']['q']], ['z', 'a'])
        self.assertEqual([doc for doc, _ in runs['B']['q']], ['a', 'z'])
        self.assertEqual(union, {'z', 'a'})

    def test_complete_query_metrics_diagnostics_and_sign_counts(self):
        qids = ['empty', 'q']
        runs = {arm: {'empty': [], 'q': [('zero', 2), ('yes', 1)]} for arm in audit.ARMS}
        runs['B']['q'] = [('outside', 2), ('yes', 1)]
        grades = {'empty': {'missing': 1}, 'q': {'yes': 1, 'zero': 0}}
        rows, summary = audit.numeric_results(qids, grades, runs, .25)
        self.assertEqual(summary['n_queries'], 2)
        self.assertAlmostEqual(summary['means_ndcg10']['A'], 1 / math.log2(3) / 2)
        self.assertEqual(summary['contrasts_ndcg10']['B-A']['zero'], 2)
        self.assertEqual(summary['B_top10_outside_P_totals'], {'count': 1, 'returned_top10': 2})
        self.assertEqual(summary['judgedness_totals']['B'], {'count': 1, 'returned_top10': 2})
        self.assertEqual(rows['empty']['arm_depths']['B'], 0)


class IndependentFormatTests(unittest.TestCase):
    def test_saved_trec_full_scores_order_and_rank_errors_are_rejected(self):
        expected = {'q': [('z', 1.123456789123), ('a', 1.0)]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bm25.trec'
            path.write_text('q Q0 z 1 1.123456789123 bm25\nq Q0 a 2 1.0 bm25\n')
            actual = audit.read_trec(path, 'bm25', ['q'])
            self.assertEqual(audit.compare_rankings(expected, actual, 'bm25')['rows'], 2)
            for changed in ({'q': [('a', 1.123456789123), ('z', 1.0)]},
                            {'q': [('z', 1.123457), ('a', 1.0)]}, {'q': [('z', 1.123456789123)]}):
                with self.assertRaises(ValueError):
                    audit.compare_rankings(expected, changed, 'bm25')
            for invalid in ('q Q0 z 0 1.123456789123 bm25\n', 'q Q0 z 1 nan bm25\n',
                            'q Q0 z 1 2.0 bm25\nq Q0 z 2 1.0 bm25\n'):
                path.write_text(invalid)
                with self.assertRaises(ValueError):
                    audit.read_trec(path, 'bm25', ['q'])

    def test_recursive_comparison_requires_keys_exact_counts_and_numeric_match(self):
        expected = {'q': {'count': 2, 'metric': .5, 'ranking': ['a', 'z']}}
        self.assertEqual(audit.compare_tree(expected, deepcopy(expected)), 0)
        for changed in ({'q': {'count': 2.0, 'metric': .5, 'ranking': ['a', 'z']}},
                        {'q': {'count': 2, 'metric': .51, 'ranking': ['a', 'z']}},
                        {'q': {'count': 2, 'metric': .5, 'ranking': ['a', 'z'], 'extra': 1}}):
            with self.assertRaises(ValueError):
                audit.compare_tree(expected, changed)

    def test_official_output_requires_complete_denominator_and_finite_values(self):
        valid = 'ndcg_cut_10 empty 0.0000\nndcg_cut_10 q 1.0000\nndcg_cut_10 all 0.5000\n'
        self.assertEqual(audit.parse_official(valid, ['empty', 'q'])['all'], .5)
        for invalid in (valid.replace('ndcg_cut_10 empty 0.0000\n', ''), valid.replace('1.0000', 'nan'),
                        valid + 'ndcg_cut_10 all 0.5000\n', valid.replace('ndcg_cut_10', 'ndcg_cut_20')):
            with self.assertRaises(ValueError):
                audit.parse_official(invalid, ['empty', 'q'])

    def test_cache_checks_full_canonical_text_source_order_and_string_ids(self):
        corpus = {'001': ('Gene', 'cell')}
        row = {'query': {'qid': '001', 'text': 'Gene'},
               'candidates': [{'docid': '001', 'score': 2.0, 'doc': {'_id': '001', 'title': 'Gene', 'text': 'cell'}}]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'cache.jsonl'
            path.write_text(json.dumps(row) + '\n')
            self.assertEqual(audit.read_cache(path, corpus, {'001': 'Gene'}, ['001']), {'001': [('001', 2.0)]})
            for mutation in ('text', 'duplicate', 'qid', 'score'):
                changed = deepcopy(row)
                if mutation == 'text':
                    changed['candidates'][0]['doc']['text'] = 'changed'
                elif mutation == 'duplicate':
                    changed['candidates'].append(deepcopy(changed['candidates'][0]))
                elif mutation == 'qid':
                    changed['query']['qid'] = 1
                else:
                    changed['candidates'][0]['score'] = '2.0'
                path.write_text(json.dumps(changed) + '\n')
                with self.assertRaises(ValueError):
                    audit.read_cache(path, corpus, {'001': 'Gene'}, ['001'])


if __name__ == '__main__':
    unittest.main()
