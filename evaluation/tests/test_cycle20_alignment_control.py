"""Synthetic-only preservation, exact aggregation and custody tests for Cycle20."""

from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
import copy
from fractions import Fraction
import io
import itertools
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle18_family_outputs as prior
from evaluation import cycle20_alignment_control as alignment


def synthetic_panel(qids=("1",), mixed_masks=False):
    order = [f"d{i:03d}" for i in range(100)]
    orders = {name: list(order) for name in prior.SOURCES}
    if mixed_masks:
        orders["D"] = order[:80] + [f"d-only-{i:03d}" for i in range(20)]
        orders["T"] = order[:60] + [f"t-only-{i:03d}" for i in range(40)]
    runs = {}
    for name, documents in orders.items():
        text = "".join(f"{qid} Q0 {doc} {rank} {1000 - rank} fixture\n"
                       for qid in qids for rank, doc in enumerate(documents, 1))
        runs[name] = prior.run_parser.parse_run(text, set(documents), qids)
    old = {"queries": {qid: {"policies": {name: order[:10] for name in ("A", "S", "H")}} for qid in qids}}
    policies = prior.build_policies(runs, old, qids)
    all_documents = order + sorted(set().union(*map(set, orders.values())) - set(order))
    labels = {qid: {doc: 0 if index in (0, 99) else 2 if index % 3 == 0 else 1
                    for index, doc in enumerate(all_documents) if index != 50} for qid in qids}
    return policies, labels


def control_fixture(natural, controls):
    return {"query_ids": ["1"], "control_count": len(controls), "natural_heads": {"1": natural},
            "controls": [{"replicate": index, "heads": {"1": head}} for index, head in enumerate(controls)],
            "head_counts": {"1": dict(Counter(doc for head in controls for doc in head))}}


class PermutationTests(unittest.TestCase):
    def test_known_exact_grades_and_unknown_identity_rank_positions_are_preserved(self):
        order = ["a", "b", "c", "d", "e", "f", "unknown1", "unknown2"]
        labels = {"a": 0, "b": 0, "c": 1, "d": 1, "e": 2, "f": 2}
        masks = {doc: 15 for doc in order}
        for replicate in range(16):
            changed = alignment.permute_order(order, labels, masks, replicate, "1", "D")
            self.assertEqual(set(changed), set(order))
            self.assertEqual(changed[6:], ["unknown1", "unknown2"])
            self.assertEqual(alignment.grade_symbols(order, labels), alignment.grade_symbols(changed, labels))
            for first, second in itertools.product((0, 1), repeat=2):
                completed = {**labels, "unknown1": first, "unknown2": second}
                self.assertEqual([completed[doc] > 0 for doc in order], [completed[doc] > 0 for doc in changed])

    def test_seed_streams_reproduce_and_separate_source_query_grade_mask_and_replicate(self):
        base = alignment.stream_seed(0, "1", "D", 0, 15)
        self.assertEqual(base, alignment.stream_seed(0, "1", "D", 0, 15))
        self.assertEqual(len({base, alignment.stream_seed(1, "1", "D", 0, 15), alignment.stream_seed(0, "2", "D", 0, 15),
                              alignment.stream_seed(0, "1", "T", 0, 15), alignment.stream_seed(0, "1", "D", 1, 15),
                              alignment.stream_seed(0, "1", "D", 0, 3)}), 6)
        order = [str(i) for i in range(20)]
        labels = {doc: 0 for doc in order}
        masks = {doc: 15 for doc in order}
        self.assertEqual(alignment.permute_order(order, labels, masks, 2, "3", "D"),
                         alignment.permute_order(order, labels, masks, 2, "3", "D"))

    def test_unknown_only_or_singleton_strata_are_valid_no_ops(self):
        order = ["u", "a", "b", "c"]
        masks = {doc: 15 for doc in order}
        self.assertEqual(alignment.permute_order(order, {}, masks, 0, "1", "D"), order)
        self.assertEqual(alignment.permute_order(order, {"a": 0, "b": 1, "c": 2}, masks, 0, "1", "D"), order)

    def test_full_membership_mask_bits_are_fixed_by_all_four_sources(self):
        orders = {"A": ["all", "ad", "a"], "D": ["all", "ad", "dt"],
                  "T": ["all", "dt", "ts"], "S": ["all", "ts", "s"]}
        self.assertEqual(alignment.membership_masks(orders), {"all": 15, "ad": 3, "a": 1, "dt": 6, "ts": 12, "s": 8})

    def test_same_grade_different_mask_cannot_exchange_reciprocal_mass(self):
        order = ["a", "b", "c", "d", "e", "f", "g", "h", "unknown"]
        labels = {"a": 0, "b": 0, "c": 0, "d": 0, "e": 1, "f": 1, "g": 2, "h": 2}
        masks = {"a": 3, "b": 3, "c": 15, "d": 15, "e": 6, "f": 6, "g": 10, "h": 10, "unknown": 14}
        before = alignment.reciprocal_mass_by_class(order, labels, masks)
        summary = alignment.stratum_summary(order, labels, masks)
        self.assertEqual(summary["known"][:2], [{"grade": 0, "mask": 3, "size": 2, "reciprocal_mass": "123/3782"},
                                               {"grade": 0, "mask": 15, "size": 2, "reciprocal_mass": "127/4032"}])
        self.assertEqual(summary["unknown"], 1)
        for replicate in range(32):
            changed = alignment.permute_order(order, labels, masks, replicate, "1", "D")
            self.assertEqual([masks[doc] for doc in changed], [masks[doc] for doc in order])
            self.assertEqual(alignment.reciprocal_mass_by_class(changed, labels, masks), before)
            self.assertEqual(changed[-1], "unknown")
        broader = list(order)
        broader[1], broader[2] = broader[2], broader[1]
        self.assertEqual(alignment.grade_symbols(order, labels), alignment.grade_symbols(broader, labels))
        self.assertNotEqual(alignment.reciprocal_mass_by_class(broader, labels, masks), before)

    def test_rank_alignment_can_change_head_and_precision_with_identical_marginals(self):
        order = [f"d{i:03d}" for i in range(100)]
        orders = {name: list(order) for name in alignment.SOURCES}
        natural = alignment.head(alignment.integer_scores(orders, {"A": 1, "D": 1, "T": 1, "S": 3}))
        changed = copy.deepcopy(orders)
        for source in ("D", "T"):
            changed[source][0], changed[source][99] = changed[source][99], changed[source][0]
        labels = {doc: int(index not in (0, 99)) for index, doc in enumerate(order)}
        masks = alignment.membership_masks(orders)
        for source in alignment.SOURCES:
            self.assertEqual(alignment.grade_symbols(orders[source], labels), alignment.grade_symbols(changed[source], labels))
            self.assertEqual(alignment.reciprocal_mass_by_class(orders[source], labels, masks),
                             alignment.reciprocal_mass_by_class(changed[source], labels, masks))
        intervened = alignment.head(alignment.integer_scores(changed, {"A": 1, "D": 1, "T": 1, "S": 3}))
        self.assertEqual(natural, order[:10])
        self.assertEqual(intervened, order[1:11])
        self.assertEqual(sum(labels[doc] for doc in natural), 9)
        self.assertEqual(sum(labels[doc] for doc in intervened), 10)

    def test_exact_integer_ranking_uses_string_ties(self):
        scores = {"z": 10, "a": 10, "m": 11}
        self.assertEqual(alignment.head(scores), ["m", "a", "z"])
        orders = {"A": ["z", "a"], "S": ["a", "z"]}
        scores = alignment.integer_scores(orders, {"A": 1, "S": 1})
        self.assertEqual(scores["a"], scores["z"])
        self.assertEqual(alignment.head(scores), ["a", "z"])

    def test_identity_replays_prior_fraction_scores_and_control_generation_is_deterministic(self):
        policies, labels = synthetic_panel()
        before = copy.deepcopy(policies)
        first = alignment.generate_controls(policies, labels, 8, ("1",))
        second = alignment.generate_controls(policies, labels, 8, ("1",))
        self.assertEqual(first, second)
        self.assertEqual(policies, before)
        self.assertTrue(any(row["changed_slots"]["1"] > 0 for row in first["controls"]))
        self.assertEqual(sum(first["head_counts"]["1"].values()), 80)
        self.assertEqual(first["invariants"]["new_only_head_admissions"], 0)
        result = alignment.analyze(first, labels)
        alignment.verify_saved_reference(result, prior.analyze(policies, labels))

    def test_saved_head_or_exact_score_mutation_stops_before_controls(self):
        policies, labels = synthetic_panel()
        changed = copy.deepcopy(policies)
        changed["queries"]["1"]["policies"]["F"].reverse()
        with self.assertRaisesRegex(alignment.core.ContractError, "identity control"):
            alignment.generate_controls(changed, labels, 1, ("1",))
        changed = copy.deepcopy(policies)
        changed["queries"]["1"]["candidates"][0]["F"] = "0/1"
        with self.assertRaisesRegex(alignment.core.ContractError, "score differs"):
            alignment.generate_controls(changed, labels, 1, ("1",))

    def test_saved_metric_mismatch_is_rejected_by_precontrol_identity_replay(self):
        policies, labels = synthetic_panel()
        reference = prior.analyze(policies, labels)
        alignment.replay_saved_reference(policies, labels, reference)
        reference["contrasts"]["F-H"]["lower"] = "-1/10"
        with self.assertRaisesRegex(alignment.core.ContractError, "saved natural aggregate"):
            alignment.replay_saved_reference(policies, labels, reference)


class SharedBoundsTests(unittest.TestCase):
    def setUp(self):
        self.common = [f"shared{i}" for i in range(9)]
        self.f, self.h = self.common + ["p"], self.common + ["n"]
        self.controls = control_fixture({"F": self.f, "H": self.h, "S": self.h}, [self.h, self.f])

    def test_frequency_coefficients_cancel_shared_unknowns_and_preserve_triangle(self):
        result = alignment.analyze(self.controls, {"1": {}})
        primary = result["per_query"]["1"]["contrasts"]["F-C"]
        self.assertEqual(primary["support"], [{"docid": "n", "coefficient": "-1/20", "grade": None},
                                             {"docid": "p", "coefficient": "1/20", "grade": None}])
        self.assertEqual((primary["lower"], primary["upper"]), ("-1/20", "1/20"))
        self.assertTrue(all(result["coefficient_checks"].values()))
        for positive, negative in itertools.product((0, 1), repeat=2):
            labels = {"1": {"p": positive, "n": negative}}
            contrasts = alignment.analyze(self.controls, labels)["contrasts"]
            self.assertEqual(Fraction(contrasts["F-H"]["known"]),
                             Fraction(contrasts["F-C"]["known"]) + Fraction(contrasts["C-H"]["known"]))
            self.assertEqual(Fraction(contrasts["F-C"]["known"]), Fraction(positive - negative, 20))

    def test_all_partial_assignments_have_sharp_bounds_and_endpoint_averaging_equivalence(self):
        for positive, negative in itertools.product((None, 0, 1), repeat=2):
            labels = {doc: value for doc, value in (("p", positive), ("n", negative)) if value is not None}
            result = alignment.analyze(self.controls, {"1": labels})["contrasts"]["F-C"]
            completions = []
            for yp in ((0, 1) if positive is None else (positive,)):
                for yn in ((0, 1) if negative is None else (negative,)):
                    completions.append(Fraction(yp - yn, 20))
            self.assertEqual(Fraction(result["lower"]), min(completions))
            self.assertEqual(Fraction(result["upper"]), max(completions))
            individual = [alignment.core.contrast_bounds(self.f, row["heads"]["1"], labels) for row in self.controls["controls"]]
            for endpoint in ("lower", "upper"):
                self.assertEqual(Fraction(result[endpoint]), sum((Fraction(row[endpoint]) for row in individual), Fraction()) / 2)

    def test_control_metric_is_mean_of_metrics_and_fixed_reference_directions(self):
        result = alignment.analyze(self.controls, {"1": {"p": 2, "n": 0}})
        self.assertEqual(result["benchmark"]["policies"], {"F": "1/10", "C": "1/20", "H": "0/1", "S": "0/1"})
        self.assertEqual(result["benchmark"]["control_draw_means"], [{"replicate": 0, "mean": "0/1"},
                                                                    {"replicate": 1, "mean": "1/10"}])
        self.assertEqual(result["contrasts"]["C-S"]["lower"], "1/20")

    def test_mean_scaled_route_uses_one_query_average_only(self):
        controls = copy.deepcopy(self.controls)
        controls["query_ids"] = ["1", "2"]
        controls["natural_heads"]["2"] = copy.deepcopy(controls["natural_heads"]["1"])
        controls["head_counts"]["2"] = copy.deepcopy(controls["head_counts"]["1"])
        for row in controls["controls"]:
            row["heads"]["2"] = list(row["heads"]["1"])
        labels = {"1": {"p": 1, "n": 0}, "2": {"p": 0, "n": 0}}
        result = alignment.analyze(controls, labels)
        self.assertEqual(result["contrasts"]["F-C"]["lower"], "1/40")
        self.assertEqual(alignment.mean_scaled_bounds(controls, labels)["F-C"]["lower"], "1/40")
        self.assertTrue(result["coefficient_checks"]["mean_scaled_sum_equals_query_average"])


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in alignment.REQUIRED_FROZEN:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name not in {alignment.PRIOR + "/" + file for file in ("policies.json", "analysis.json", "manifest.json", "success.json")}:
                path.write_text("synthetic frozen dependency\n")
        policies, labels = synthetic_panel(alignment.QUERY_IDS, mixed_masks=True)
        prior_dir = self.root / alignment.PRIOR
        alignment.write_json(prior_dir / "policies.json", policies)
        alignment.write_json(prior_dir / "analysis.json", prior.analyze(policies, labels))
        self.qrels = self.root / "late.qrels"
        self.qrels.write_text("".join(f"{qid} 0.5 {doc} {grade}\n" for qid in alignment.QUERY_IDS for doc, grade in labels[qid].items()))
        alignment.write_json(prior_dir / "manifest.json", {
            "inputs": {"late.qrels": {"path": "late.qrels", **alignment.core.identity(self.qrels)}},
            "outputs": {file: alignment.core.identity(prior_dir / file) for file in ("policies.json", "analysis.json")}})
        alignment.write_json(prior_dir / "success.json", {"status": "passed", "manifest": alignment.core.identity(prior_dir / "manifest.json")})
        frozen = {name: alignment.core.identity(self.root / name)["sha256"] for name in alignment.REQUIRED_FROZEN}
        self.preflight = self.root / "preflight.json"
        alignment.write_json(self.preflight, {"status": "passed", "frozen": frozen})
        self.output = self.root / "output"
        root_patch = patch.object(alignment, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def invoke(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return alignment.main(["--preflight", str(self.preflight), "--output", str(self.output)])

    def test_full_fixed_256_control_phase_has_portable_custody_and_explicit_label_use(self):
        self.assertEqual(self.invoke(), 0)
        controls = alignment.core.read_json(self.output / "controls.json")
        self.assertEqual(len(controls["controls"]), 256)
        self.assertEqual(controls["query_ids"], list(alignment.QUERY_IDS))
        self.assertTrue(controls["labels_used_to_construct_controls"])
        manifest = alignment.core.read_json(self.output / "manifest.json")
        self.assertEqual(manifest["inputs"]["late.qrels"]["path"], "late.qrels")
        self.assertEqual(manifest["preflight"], "preflight.json")
        self.assertTrue(all(not Path(path).is_absolute() for path in manifest["tracked_after"]))
        self.assertTrue(manifest["labels_used_to_construct_controls"])

    def test_changed_labels_fail_before_any_control_generation(self):
        with self.qrels.open("a") as stream:
            stream.write(" ")
        with patch.object(alignment, "generate_controls", side_effect=AssertionError("generated controls from changed input")):
            self.assertEqual(self.invoke(), 1)
        self.assertEqual(alignment.core.read_json(self.output / "failure.json")["error_type"], "ContractError")

    def test_changed_dependency_after_generation_and_existing_output_fail(self):
        original = alignment.generate_controls
        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            with (self.root / alignment.SOURCE).open("a") as stream:
                stream.write(" ")
            return result
        with patch.object(alignment, "generate_controls", side_effect=mutate):
            self.assertEqual(self.invoke(), 1)
        self.assertFalse((self.output / "success.json").exists())
        previous = alignment.core.identity(self.output / "failure.json")
        self.assertEqual(self.invoke(), 1)
        self.assertEqual(previous, alignment.core.identity(self.output / "failure.json"))
        self.assertEqual(len(list(self.root.glob("output.failure-*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
