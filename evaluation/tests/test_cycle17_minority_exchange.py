"""Bounded synthetic tests; no selected benchmark inputs are opened."""

from contextlib import redirect_stderr, redirect_stdout
from fractions import Fraction
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle17_minority_exchange as exchange


def run_text(order, qids=("1",)):
    return "".join(f"{qid} Q0 {doc} {rank} {10000 - rank} fixture\n"
                   for qid in qids for rank, doc in enumerate(order, 1))


def source(order):
    return exchange.parse_run(run_text(order), set(order), ("1",))["1"]


def query_fixture(different=False, truncated=False):
    common = [f"d{i:03d}" for i in range(10)]
    a_order = common.copy()
    if different:
        a_order += [f"tail{i:03d}" for i in range(89)] + ["generic"]
        s_order = ["generic", "minority"] + common
    else:
        s_order = ["minority"] + common
    if truncated:
        a_order += [f"tail{i:03d}" for i in range(100 - len(a_order))] + ["minority"]
    return exchange.build_query(source(a_order), source(s_order))


class ParsingTests(unittest.TestCase):
    def setUp(self):
        self.docs = [f"d{i}" for i in range(10)]
        self.text = run_text(self.docs)

    def test_numeric_score_controls_order_and_ties_use_string_ids(self):
        text = self.text.replace("d0 1 9999", "d0 1 1").replace("d1 2 9998", "d1 2 1.00")
        result = exchange.parse_run(text, set(self.docs), ("1",))["1"]
        self.assertEqual(result["full_order"][-2:], ["d0", "d1"])
        self.assertEqual(result["tie_groups"], 1)
        self.assertEqual(result["tie_excess"], 1)
        self.assertEqual(result["tied_documents"], 2)
        self.assertEqual(result["supplied_rank_disagreements"], 10)
        self.assertEqual(result["details"]["d1"]["score"], "1.00")

    def test_decimal_comparison_preserves_more_than_28_digits(self):
        low = "1.0000000000000000000000000000000000000001"
        high = "1.0000000000000000000000000000000000000002"
        text = self.text.replace("d0 1 9999", "d0 1 " + low).replace("d1 2 9998", "d1 2 " + high)
        result = exchange.parse_run(text, set(self.docs), ("1",))["1"]
        self.assertEqual(result["full_order"][-2:], ["d1", "d0"])
        self.assertEqual(result["tie_groups"], 0)

    def test_run_rejects_bad_rows_duplicates_ids_depth_and_cohort(self):
        bad = ["", self.text + self.text.splitlines()[0] + "\n",
               self.text.replace("Q0 d0 1", "Q0 other 1"), self.text.replace("d0 1 9999", "d0 0 9999"),
               self.text.replace("d0 1 9999", "d0 1 NaN"), self.text.replace("d0 1 9999", "d0 1 Infinity"),
               self.text.replace("1 Q0", "01 Q0", 1), "\n".join(self.text.splitlines()[:9]),
               self.text.replace(" fixture", "", 1)]
        for text in bad:
            with self.subTest(text=text[:50]), self.assertRaises(exchange.ContractError):
                exchange.parse_run(text, set(self.docs), ("1",))
        with self.assertRaisesRegex(exchange.ContractError, "cohort"):
            exchange.parse_run(self.text, set(self.docs), ("1", "2"))
        too_many = [str(i) for i in range(1001)]
        with self.assertRaisesRegex(exchange.ContractError, "depth"):
            exchange.parse_run(run_text(too_many), set(too_many), ("1",))

    def test_docids_are_unique_ascii_tokens(self):
        self.assertEqual(exchange.parse_docids("01\n1\n"), {"01", "1"})
        for text in ("", "a\na\n", "a b\n", "a\n\n", "é\n"):
            with self.subTest(text=text), self.assertRaises(exchange.ContractError):
                exchange.parse_docids(text)

    def test_qrels_half_rounds_zero_negative_and_unknown_remain_distinct(self):
        result = exchange.parse_qrels("1 0.5 d0 0\n1 1 d1 2\n", set(self.docs), ("1",))
        self.assertEqual(result, {"1": {"d0": 0, "d1": 2}})
        self.assertNotIn("d2", result["1"])
        for text in ("", "1 0 d0 0\n", "1 -0.5 d0 0\n", "1 NaN d0 0\n", "1 Infinity d0 0\n",
                     "1 0.5 d0 3\n", "1 0.5 d0 -1\n", "1 0.5 d0 1.0\n", "1 0.5 no 0\n",
                     "1 0.5 d0 0\n1 1 d0 0\n", "2 0.5 d0 0\n", "1 0.5 d0\n"):
            with self.subTest(text=text), self.assertRaises(exchange.ContractError):
                exchange.parse_qrels(text, set(self.docs), ("1",))
        with self.assertRaisesRegex(exchange.ContractError, "cohort"):
            exchange.parse_qrels("1 0.5 d0 0\n", set(self.docs), ("1", "2"))


class PolicyTests(unittest.TestCase):
    def test_same_candidate_and_absent_shared_only_control(self):
        query = query_fixture()
        self.assertTrue(query["eligible"])
        self.assertEqual(query["m"], "minority")
        self.assertEqual(query["j"], "minority")
        self.assertTrue(query["m_equals_j"])
        self.assertEqual(query["policies"]["M"][:9], query["policies"]["H"][:9])
        # J is feasible even when S has no A-supported result outside H's head.
        outside = set(query["policies"]["S"]) - set(query["policies"]["H"])
        self.assertEqual(outside, {"minority"})

    def test_minority_and_generic_priority_differ_with_same_trigger(self):
        query = query_fixture(different=True)
        self.assertTrue(query["eligible"])
        self.assertEqual((query["m"], query["j"]), ("minority", "generic"))
        self.assertFalse(query["m_equals_j"])
        self.assertEqual(query["policies"]["M"][:9], query["policies"]["J"][:9])
        self.assertEqual(query["sources"]["A"]["details"]["generic"]["canonical_rank"], 100)

    def test_no_eligibility_for_identical_or_disjoint_heads(self):
        docs = [f"d{i}" for i in range(10)]
        for s in (docs, [f"s{i}" for i in range(10)]):
            query = exchange.build_query(source(docs), source(s))
            self.assertFalse(query["eligible"])
            self.assertEqual(query["policies"]["M"], query["policies"]["H"])
            self.assertEqual(query["policies"]["J"], query["policies"]["H"])
            self.assertIsNone(query["m"])
            self.assertIsNone(query["j"])

    def test_truncated_membership_is_distinct_from_full_submission_absence(self):
        query = query_fixture(truncated=True)
        self.assertTrue(query["eligible"])
        observed = exchange.document_observation("minority", query, {})
        self.assertEqual(observed["A_full_rank"], 101)
        self.assertTrue(observed["A_full_member"])
        self.assertFalse(observed["A_retained_member"])
        self.assertIsNone(observed["A_retained_rank"])
        self.assertEqual(query["sources"]["A"]["retained_depth"], 100)

    def test_no_opportunity_and_identical_policy_point_zero(self):
        docs = [f"d{i}" for i in range(10)]
        prepared = exchange.prepare_policies({"1": source(docs)}, {"1": source(docs)}, ("1",))
        result = exchange.analyze(prepared, {"1": {}})
        self.assertEqual(result["primary_decision"], "no_opportunity")
        self.assertIsNone(result["triggered_only_contrasts"])
        for contrast in result["contrasts"].values():
            self.assertEqual(contrast["lower"], "0/1")
            self.assertEqual(contrast["upper"], "0/1")
            self.assertEqual(contrast["sign"], "point_zero")


class BoundAndRevelationTests(unittest.TestCase):
    def test_all_partial_assignments_match_exhaustive_sharp_completions(self):
        shared = [f"shared{i}" for i in range(8)]
        left, right = shared + ["p1", "p2"], shared + ["n1", "n2"]
        support = ["p1", "p2", "n1", "n2"]
        checked_completions = 0
        for assignment in itertools.product((None, 0, 1), repeat=4):
            labels = {doc: grade for doc, grade in zip(support, assignment) if grade is not None}
            result = exchange.contrast_bounds(left, right, labels)
            self.assertEqual(len(result["support"]), 4)
            self.assertFalse(set(shared) & {row["docid"] for row in result["support"]})
            unknown = [doc for doc in support if doc not in labels]
            realized = []
            for completion in itertools.product((0, 1), repeat=len(unknown)):
                full = {**labels, **dict(zip(unknown, completion))}
                value = Fraction(sum(full.get(doc, 0) for doc in left) -
                                 sum(full.get(doc, 0) for doc in right), 10)
                realized.append(value)
                checked_completions += 1
            self.assertEqual(Fraction(result["lower"]), min(realized))
            self.assertEqual(Fraction(result["upper"]), max(realized))
            self.assertLessEqual(min(realized), Fraction(result["benchmark_zero"]))
            self.assertLessEqual(Fraction(result["benchmark_zero"]), max(realized))
        self.assertEqual(checked_completions, 256)

    def test_uniform_unknown_completion_is_not_contrast_bounds(self):
        common = [f"s{i}" for i in range(9)]
        result = exchange.contrast_bounds(common + ["positive_coefficient"], common + ["negative_coefficient"], {})
        self.assertEqual((result["lower"], result["upper"], result["benchmark_zero"]), ("-1/10", "1/10", "0/1"))

    def test_ledger_binary_categories_preserve_exact_grades(self):
        query = query_fixture()
        old = query["displaced"]
        for admitted, displaced, category in ((2, 0, "rescue"), (0, 1, "harm"), (1, 2, "neutral"),
                                                (0, 0, "neutral"), (None, 0, "unresolved"), (2, None, "unresolved")):
            labels = {doc: grade for doc, grade in (("minority", admitted), (old, displaced)) if grade is not None}
            row = exchange.exchange_row("1", "M", query, labels)
            self.assertEqual(row["category"], category)
            self.assertEqual(row["admitted"]["grade"], admitted)
            self.assertEqual(row["displaced"]["grade"], displaced)

    def test_all_queries_in_primary_denominator_and_additions_nest(self):
        query = query_fixture(different=True)
        unchanged = exchange.build_query(source([f"u{i}" for i in range(10)]), source([f"u{i}" for i in range(10)]))
        policies = {"query_ids": ["1", "2"], "queries": {"1": query, "2": unchanged}}
        before_labels = {"1": {query["displaced"]: 0}, "2": {}}
        after_labels = {"1": {query["displaced"]: 0, "minority": 2, "generic": 0}, "2": {"u0": 1}}
        before, after = exchange.analyze(policies, before_labels), exchange.analyze(policies, after_labels)
        self.assertEqual(before["contrasts"]["M-H"]["upper"], "1/20")
        self.assertEqual(before["triggered_only_contrasts"]["M-H"]["upper"], "1/10")
        self.assertEqual(after["contrasts"]["M-H"]["lower"], "1/20")
        revelation = exchange.compare_phases(before, after, before_labels, after_labels)
        self.assertTrue(revelation["primary_width_reduced"])
        self.assertEqual(revelation["contrasts"]["M-H"]["width_reduction"], "1/20")
        self.assertEqual(revelation["contrasts"]["M-H"]["added_labels_on_support"], 1)
        self.assertEqual(revelation["added_qrels_pairs"], 3)
        self.assertEqual(revelation["exchange_category_transitions"][0]["late_category"], "rescue")
        for contrast in after["contrasts"]:
            left, right = contrast.split("-")
            benchmark = after["benchmark"]["policies"]
            self.assertEqual(Fraction(after["contrasts"][contrast]["benchmark_zero"]),
                             Fraction(benchmark[left]) - Fraction(benchmark[right]))

    def test_exact_grade_preservation_rejects_even_binary_equivalent_revisions(self):
        early = {"1": {"a": 1, "b": 0, "c": 2}}
        late = {"1": {"a": 2, "c": 2, "new": 1}}
        mismatches = exchange.label_mismatches(early, late)
        self.assertEqual([row["kind"] for row in mismatches], ["revised", "removed"])
        with self.assertRaisesRegex(exchange.ContractError, "removed or revised"):
            exchange.compare_phases({}, {}, early, late)

    def test_sign_statuses_distinguish_zero_boundary(self):
        cases = [(-1, -1, "strict_negative", "positive_excluded"),
                 (0, 0, "point_zero", "positive_excluded"),
                 (1, 2, "strict_positive", "all_completions_positive"),
                 (-1, 0, "nonpositive_with_zero", "positive_excluded"),
                 (0, 1, "nonnegative_with_zero", "sign_unresolved"),
                 (-1, 1, "crosses_zero", "sign_unresolved")]
        for lower, upper, sign, decision in cases:
            result = exchange.interval_fields(Fraction(lower), Fraction(lower), Fraction(upper))
            self.assertEqual((result["sign"], result["decision"]), (sign, decision))


class PhaseCustodyTests(unittest.TestCase):
    """Use a tiny synthetic repository to exercise full CLI custody gates."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.prepared, self.early, self.late = (self.root / name for name in ("prepared", "early", "late"))
        common = [f"d{i:03d}" for i in range(10)]
        files = {"A.run": run_text(common, exchange.QUERY_IDS),
                 "S.run": run_text(["minority"] + common, exchange.QUERY_IDS),
                 "docids.txt": "\n".join(common + ["minority"]) + "\n",
                 "early.qrels": "".join(f"{qid} 0.5 {common[-1]} 0\n" for qid in exchange.QUERY_IDS),
                 "late.qrels": "".join(f"{qid} 0.5 {common[-1]} 0\n{qid} 2 minority 2\n" for qid in exchange.QUERY_IDS)}
        for name, text in files.items():
            (self.inputs / name).write_text(text, encoding="utf-8")
        for name in (exchange.PROTOCOL, exchange.SOURCE, exchange.TESTS):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("frozen synthetic source\n", encoding="utf-8")
        plan = {"items": {name: {"filename": name, "max_bytes": 100000,
                                 "expected_bytes": (self.inputs / name).stat().st_size} for name in files}}
        exchange.write_json(self.root / exchange.PLAN, plan)
        self.frozen = {name: exchange.identity(self.root / name)["sha256"]
                       for name in (exchange.PROTOCOL, exchange.PLAN, exchange.SOURCE, exchange.TESTS)}
        self.receipt = self.root / "acquisition.json"
        exchange.write_json(self.receipt, {"status": "passed", "frozen": self.frozen,
                             "inputs": {name: exchange.identity(self.inputs / name)
                                        for name in files if name != "late.qrels"}})
        self.root_patch = patch.object(exchange, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def invoke(self, args):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return exchange.main(args)

    def prepare(self):
        return self.invoke(["prepare", "--inputs", str(self.inputs), "--acquisition", str(self.receipt),
                            "--output", str(self.prepared)])

    def analyze_early(self):
        return self.invoke(["early", "--prepared", str(self.prepared), "--output", str(self.early)])

    def analyze_late(self):
        receipt = self.root / "late-acquisition.json"
        exchange.write_json(receipt, {"status": "passed", "frozen": self.frozen,
                             "inputs": {"late.qrels": exchange.identity(self.inputs / "late.qrels")},
                             "early_manifest_sha256": exchange.identity(self.early / "manifest.json")["sha256"]})
        return self.invoke(["late", "--prepared", str(self.prepared), "--early", str(self.early),
                            "--late-input", str(self.inputs / "late.qrels"), "--late-acquisition", str(receipt),
                            "--output", str(self.late)])

    def test_full_phases_freeze_before_labels_and_never_rebuild_late(self):
        with patch.object(exchange, "parse_qrels", side_effect=AssertionError("label parse during prepare")):
            self.assertEqual(self.prepare(), 0)
        policy_identity = exchange.identity(self.prepared / "policies.json")
        self.assertEqual(self.analyze_early(), 0)
        with patch.object(exchange, "build_query", side_effect=AssertionError("late policy rebuilt")), \
                patch.object(exchange, "parse_run", side_effect=AssertionError("late run reparsed")):
            self.assertEqual(self.analyze_late(), 0)
        self.assertEqual(policy_identity, exchange.identity(self.prepared / "policies.json"))
        after = exchange.read_json(self.late / "analysis.json")
        self.assertEqual(after["query_count"], 30)
        self.assertEqual(after["contrasts"]["M-H"]["lower"], "1/10")
        self.assertTrue(exchange.read_json(self.late / "revelation.json")["primary_width_reduced"])

    def test_mutated_policy_input_source_receipt_each_stop_before_label_parse(self):
        self.assertEqual(self.prepare(), 0)
        targets = [self.prepared / "policies.json", self.inputs / "A.run",
                   self.root / exchange.SOURCE, self.receipt]
        for index, target in enumerate(targets):
            original = target.read_bytes()
            target.write_bytes(original + b" ")
            out = self.root / f"mutation-{index}"
            with patch.object(exchange, "parse_qrels", side_effect=AssertionError("unexpected label parse")):
                status = self.invoke(["early", "--prepared", str(self.prepared), "--output", str(out)])
            self.assertEqual(status, 1)
            failure = exchange.read_json(out / "failure.json")
            self.assertEqual(failure["error_type"], "ContractError")
            self.assertFalse((out / "analysis.json").exists())
            target.write_bytes(original)

    def test_late_revision_emits_mismatch_and_failure_without_analysis(self):
        self.assertEqual(self.prepare(), 0)
        self.assertEqual(self.analyze_early(), 0)
        late = self.inputs / "late.qrels"
        late.write_text(late.read_text().replace("1 0.5 d009 0", "1 0.5 d009 1", 1))
        self.assertEqual(self.analyze_late(), 1)
        self.assertFalse((self.late / "analysis.json").exists())
        self.assertTrue((self.late / "failure.json").exists())
        preserved = exchange.read_json(self.late / "label-preservation.json")
        self.assertFalse(preserved["passed"])
        self.assertEqual(len(preserved["mismatches"]), 1)

    def test_exclusive_output_never_overwrites_success(self):
        self.assertEqual(self.prepare(), 0)
        before = exchange.identity(self.prepared / "success.json")
        self.assertEqual(self.prepare(), 1)
        self.assertEqual(before, exchange.identity(self.prepared / "success.json"))
        self.assertEqual(len(list(self.root.glob("prepared.failure-*.json"))), 1)

    def test_after_phase_mutation_is_detected(self):
        original = exchange.parse_run
        calls = 0
        def mutate_after_second_parse(*args, **kwargs):
            nonlocal calls
            result = original(*args, **kwargs)
            calls += 1
            if calls == 2:
                with (self.inputs / "A.run").open("a") as handle:
                    handle.write(" ")
            return result
        with patch.object(exchange, "parse_run", side_effect=mutate_after_second_parse):
            self.assertEqual(self.prepare(), 1)
        self.assertTrue((self.prepared / "failure.json").exists())
        self.assertFalse((self.prepared / "success.json").exists())


if __name__ == "__main__":
    unittest.main()
