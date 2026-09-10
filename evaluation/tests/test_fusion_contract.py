"""Focused semantic checks; no datasets or third-party dependencies.

Run: python3 -B -m unittest discover -s evaluation/tests -v
"""

from fractions import Fraction
from itertools import permutations
import unittest

from evaluation.fusion_contract import (
    asymptotic_rrf,
    canonical_rrf,
    coverage_limit,
    duplicate_quotient,
)


def rankings_with_positions(positions):
    """Place named documents at given source positions; fill with unique docs."""
    sources = []
    for source_index in range(len(next(iter(positions.values())))):
        last = max(ranks[source_index] for ranks in positions.values())
        source = ["filler-{}-{}".format(source_index, rank)
                  for rank in range(1, last + 1)]
        for doc, ranks in positions.items():
            source[ranks[source_index] - 1] = doc
        sources.append(source)
    return sources


class FusionContractTests(unittest.TestCase):
    def test_reciprocal_kernel_is_not_average_rank(self):
        # a: 1 + 1/4 = 5/4; b: 1/2 + 1/2 = 1; w: 1.
        # Mean rank favors b (2) over a (2.5), opposite to RRF at k=0.
        sources = [["a", "b", "u", "v"], ["w", "b", "x", "a"]]
        self.assertGreater(Fraction(1) + Fraction(1, 4), 2 * Fraction(1, 2))
        self.assertGreater(Fraction(1 + 4, 2), Fraction(2 + 2, 2))
        self.assertEqual(canonical_rrf(sources, k=0), ["a", "b", "w", "u", "x", "v"])

    def test_one_based_k_equals_zero_based_k_plus_one(self):
        sources = [["d", "b", "a"], ["a", "c"], ["c", "d", "b"]]
        for k in (0, 1, 60, 100):
            with self.subTest(k=k):
                old_scores = {}
                for source in sources:
                    for zero_rank, doc in enumerate(source):
                        old_scores[doc] = old_scores.get(doc, Fraction()) + Fraction(
                            1, (k + 1) + zero_rank)
                expected = sorted(old_scores, key=lambda doc: (-old_scores[doc], doc))
                self.assertEqual(canonical_rrf(sources, k=k), expected)

    def test_exact_ties_use_document_id_including_zero_weights(self):
        self.assertEqual(canonical_rrf([["z", "a"], ["a", "z"]]), ["a", "z"])
        self.assertEqual(canonical_rrf([["z"], ["a"]]), ["a", "z"])
        self.assertEqual(canonical_rrf([["z", "a"], ["b"]], weights=[0, 0]),
                         ["a", "b", "z"])

    def test_fsum_keeps_small_contributions_and_ranker_permutation_invariance(self):
        # Repeated float addition can drop each tiny contribution to z, creating
        # an artificial tie that document ID would award to a.
        pairs = [(["z"], 1.0), (["z"], 1e-16), (["z"], 1e-16), (["a"], 1.0)]
        for ordering in permutations(pairs):
            sources, weights = zip(*ordering)
            self.assertEqual(canonical_rrf(sources, k=0, weights=weights), ["z", "a"])
        sources = [["d", "a", "c"], ["c", "b", "a"], ["b", "d"]]
        for method in (canonical_rrf, coverage_limit, asymptotic_rrf):
            expected = method(sources)
            for ordering in permutations(sources):
                self.assertEqual(method(ordering), expected)

    def test_finite_weights_with_overflowing_totals_preserve_ranking(self):
        self.assertEqual(canonical_rrf([["z"], ["z"], ["a"]], k=0,
                                       weights=[1e308, 1e308, 1e308]), ["z", "a"])
        self.assertEqual(canonical_rrf([["z"], ["z"], ["a"], ["a"]], k=0,
                                       weights=[1e308] * 4), ["a", "z"])

    def test_unrelated_overflow_does_not_change_existing_finite_score_ties(self):
        sources = [["a"], ["z"], ["z"]]
        weights = [1.0, 1.0, 1e-16]
        original = canonical_rrf(sources, k=0, weights=weights)
        extended = canonical_rrf(sources + [["x"], ["x"]], k=0,
                                 weights=weights + [1e308, 1e308])
        self.assertEqual(original, ["a", "z"])
        self.assertEqual([doc for doc in extended if doc != "x"], original)

    def test_float_score_ties_are_distinct_from_mathematical_ties(self):
        sources = rankings_with_positions({"z": [2, 12], "a": [3, 4]})
        self.assertEqual(Fraction(1, 2) + Fraction(1, 12),
                         Fraction(1, 3) + Fraction(1, 4))
        ranking = canonical_rrf(sources, k=0)
        # fsum sums rounded float reciprocals; it does not recover exact kernels.
        self.assertLess(ranking.index("z"), ranking.index("a"))

    def test_exact_duplicate_quotient_removes_repeated_evidence(self):
        sources = [["a", "b"], ["b", "c"]]
        repeated = [sources[0], sources[0], sources[1], sources[0]]
        self.assertEqual(duplicate_quotient(repeated), sources)
        self.assertEqual(canonical_rrf(duplicate_quotient(repeated), k=0), ["b", "a", "c"])
        self.assertNotEqual(canonical_rrf(repeated, k=0), canonical_rrf(sources, k=0))
        self.assertEqual(duplicate_quotient([["a", "b"], ["b", "a"], ["a"], []]),
                         [["a", "b"], ["b", "a"], ["a"], []])
        output = duplicate_quotient(sources)
        output[0].append("new")
        self.assertEqual(sources, [["a", "b"], ["b", "c"]])

    def test_large_finite_k_agrees_with_simple_coverage_fixture(self):
        sources = [["s", "u", "c"], ["v", "w", "c"]]
        expected = ["c", "s", "v", "u", "w"]
        self.assertEqual(coverage_limit(sources), expected)
        self.assertEqual(asymptotic_rrf(sources), expected)
        self.assertEqual(canonical_rrf(sources, k=1_000_000), expected)
        self.assertNotEqual(canonical_rrf(sources, k=0), expected)

    def test_second_moment_can_break_coverage_and_rank_sum_tie(self):
        sources = rankings_with_positions({"z": [1, 4], "a": [2, 3]})
        self.assertEqual(coverage_limit(sources)[:2], ["a", "z"])
        self.assertEqual(asymptotic_rrf(sources)[:2], ["z", "a"])
        self.assertEqual(canonical_rrf(sources, k=1000)[:2], ["z", "a"])

    def test_third_moment_can_break_first_two_moment_ties(self):
        # Both rank multisets sum to 9 and have squared sum 33. Cubed sums
        # are 129 for z and 141 for a; the smaller third moment ranks first.
        sources = rankings_with_positions({"z": [1, 4, 4], "a": [2, 2, 5]})
        self.assertEqual(coverage_limit(sources)[:2], ["a", "z"])
        self.assertEqual(asymptotic_rrf(sources)[:2], ["z", "a"])
        self.assertEqual(canonical_rrf(sources, k=100)[:2], ["z", "a"])

    def test_empty_inputs_and_invalid_rankings(self):
        for method in (canonical_rrf, coverage_limit, asymptotic_rrf):
            self.assertEqual(method([]), [])
            self.assertEqual(method([[], []]), [])
        self.assertEqual(duplicate_quotient([]), [])
        self.assertEqual(duplicate_quotient([[], []]), [[]])
        invalid = ([["a", "a"]], [["a", 1]], ["abc"], "abc", None, [None],
                   [{"a", "b"}], [frozenset(("a", "b"))], {("a", "b")})
        for method in (canonical_rrf, coverage_limit, asymptotic_rrf, duplicate_quotient):
            for sources in invalid:
                with self.subTest(method=method.__name__, sources=sources):
                    with self.assertRaises(ValueError):
                        method(sources)

    def test_invalid_kernel_and_weights(self):
        for value in (-1, Fraction(-1, 10 ** 1000), float("nan"), float("inf"),
                      -float("inf"), "60", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonical_rrf([["a"]], k=value)
                with self.assertRaises(ValueError):
                    canonical_rrf([["a"]], weights=[value])
        for weights in ([], [1, 1], 1):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                canonical_rrf([["a"]], weights=weights)


if __name__ == "__main__":
    unittest.main()
