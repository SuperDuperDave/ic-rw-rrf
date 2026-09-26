"""Synthetic tests for a fixed candidate-scope observation, with no new policy."""

from contextlib import redirect_stderr, redirect_stdout
import copy
from fractions import Fraction
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle17_minority_exchange as original
from evaluation import cycle17_candidate_revelation as candidate


def fixture():
    common = [f"d{i}" for i in range(10)]
    def source(order):
        text = "".join(f"1 Q0 {doc} {rank} {100 - rank} fixture\n" for rank, doc in enumerate(order, 1))
        return original.parse_run(text, set(order), ("1",))
    policies = original.prepare_policies(source(common), source(["minority"] + common), ("1",))
    early = {"1": {"d0": 2, "d9": 0, "off-candidate-removed": 1, "off-candidate-revised": 0}}
    late = {"1": {"d0": 2, "d9": 0, "minority": 2, "off-candidate-revised": 2,
                   "off-candidate-added": 1}}
    return policies, early, late


class CandidateRevelationTests(unittest.TestCase):
    def test_removing_or_revising_off_candidate_labels_does_not_change_fixed_early_analysis(self):
        policies, early_labels, late_labels = fixture()
        reference = original.analyze(policies, early_labels)
        artifacts = candidate.analyze_candidates(policies, early_labels, late_labels, reference)
        early = artifacts["early.json"]
        self.assertEqual(early["qrels_pair_count"], 2)
        self.assertEqual(reference["qrels_pair_count"], 4)
        self.assertEqual({key: value for key, value in early.items() if key != "qrels_pair_count"},
                         {key: value for key, value in reference.items() if key != "qrels_pair_count"})
        scope = artifacts["scope.json"]
        self.assertTrue(scope["early_equivalence_passed"])
        self.assertTrue(scope["scoped_preservation_passed"])
        self.assertEqual(scope["counts"], {"early_global": 4, "late_global": 5, "early_scoped": 2,
                                           "late_scoped": 3, "early_excluded": 2, "late_excluded": 2,
                                           "scoped_added_pairs": 1})
        self.assertEqual(len(scope["removed_full_pairs"]), 1)
        self.assertEqual(len(scope["revised_full_pairs"]), 1)
        for row in scope["removed_full_pairs"] + scope["revised_full_pairs"]:
            self.assertFalse(row["in_candidate_scope"])
            self.assertFalse(row["in_A_retained"])
            self.assertFalse(row["in_S_retained"])

    def test_any_scoped_removal_or_exact_grade_revision_stops(self):
        policies, early, late = fixture()
        for grade in (None, 1, 0):
            labels = copy.deepcopy(late)
            if grade is None:
                del labels["1"]["d0"]
            else:
                labels["1"]["d0"] = grade
            with self.subTest(grade=grade), self.assertRaises(candidate.CandidateScopeError) as caught:
                candidate.analyze_candidates(policies, early, labels, original.analyze(policies, early))
            self.assertFalse(caught.exception.scope["scoped_preservation_passed"])
            self.assertEqual(caught.exception.scope["scoped_mismatches"][0]["docid"], "d0")

    def test_restriction_is_to_all_frozen_candidates_not_only_policy_heads(self):
        policies, early, late = fixture()
        # A candidate with no nonzero contrast coefficient is still inside the
        # fixed observation scope and cannot lose its early grade.
        early["1"]["d5"] = 1
        with self.assertRaises(candidate.CandidateScopeError):
            candidate.analyze_candidates(policies, early, late, original.analyze(policies, early))

    def test_added_labels_nest_and_h_s_is_declared_primary(self):
        policies, early, late = fixture()
        result = candidate.analyze_candidates(policies, early, late, original.analyze(policies, early))
        for name, before in result["early.json"]["contrasts"].items():
            after = result["late.json"]["contrasts"][name]
            self.assertLessEqual(Fraction(before["lower"]), Fraction(after["lower"]))
            self.assertLessEqual(Fraction(after["upper"]), Fraction(before["upper"]))
        revelation = result["revelation.json"]
        self.assertEqual(revelation["design_primary_contrast"], "H-S")
        self.assertTrue(revelation["design_primary_width_reduced"])
        self.assertEqual(revelation["contrasts"]["H-S"]["width_reduction"], "1/10")
        self.assertEqual(revelation["added_qrels_pairs"], 1)

    def test_policy_builder_and_run_parser_are_never_called(self):
        policies, early, late = fixture()
        saved = copy.deepcopy(policies)
        reference = original.analyze(policies, early)
        with patch.object(original, "build_query", side_effect=AssertionError("rebuilt policy")), \
                patch.object(original, "parse_run", side_effect=AssertionError("reparsed run")), \
                patch.object(original, "prepare_policies", side_effect=AssertionError("new policy")):
            result = candidate.analyze_candidates(policies, early, late, reference)
        self.assertEqual(saved, policies)
        self.assertTrue(result["scope.json"]["early_equivalence_passed"])

    def test_any_early_analysis_difference_beyond_count_stops(self):
        policies, early, late = fixture()
        reference = original.analyze(policies, early)
        reference["eligible_count"] += 1
        with self.assertRaisesRegex(candidate.CandidateScopeError, "differs beyond"):
            candidate.analyze_candidates(policies, early, late, reference)

    def test_no_narrowing_remains_negative_without_new_policy(self):
        policies, early, late = fixture()
        del late["1"]["minority"]
        result = candidate.analyze_candidates(policies, early, late, original.analyze(policies, early))
        self.assertFalse(result["revelation.json"]["design_primary_width_reduced"])
        self.assertEqual(result["revelation.json"]["contrasts"]["H-S"]["width_reduction"], "0/1")

    def test_scope_cannot_drop_or_add_a_candidate(self):
        policies, early, late = fixture()
        reference = original.analyze(policies, early)
        policies["queries"]["1"]["hybrid_order"].remove("minority")
        with self.assertRaisesRegex(original.ContractError, "differs from source union"):
            candidate.analyze_candidates(policies, early, late, reference)

    def test_failure_and_exclusive_output_preserve_scope_evidence(self):
        policies, early, late = fixture()
        del late["1"]["d0"]
        with self.assertRaises(candidate.CandidateScopeError) as caught:
            candidate.analyze_candidates(policies, early, late, original.analyze(policies, early))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result"
            argv = ["--preflight", "unused-synthetic", "--output", str(output)]
            with patch.object(candidate, "run_observation", side_effect=caught.exception), \
                    redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(candidate.main(argv), 1)
                failure_identity = original.identity(output / "failure.json")
                self.assertEqual(candidate.main(argv), 1)
            self.assertEqual(failure_identity, original.identity(output / "failure.json"))
            self.assertFalse(original.read_json(output / "scope-failure.json")["scoped_preservation_passed"])
            self.assertEqual(len(list(Path(tmp).glob("result.failure-*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
