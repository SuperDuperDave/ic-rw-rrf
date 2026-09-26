"""Independent expected-value synthetic tests; selected run bodies stay unopened."""

from contextlib import redirect_stderr, redirect_stdout
import copy
from fractions import Fraction
import io
import itertools
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle18_family_outputs as family


def run_text(order, qids=("1",)):
    return "".join(f"{qid} Q0 {doc} {rank - 1} {10000 - rank} fixture\n"
                   for qid in qids for rank, doc in enumerate(order, 1))


def source(order, qids=("1",)):
    return family.run_parser.parse_run(run_text(order, qids), set(order), qids)


def pareto_fixture(qids=("1",)):
    base = ["y"] + [f"x{i:02d}" for i in range(1, 100)]
    variants = base[1:] + ["y"]
    runs = {name: source(base if name in ("A", "S") else variants, qids) for name in family.SOURCES}
    historical = {"queries": {qid: {"policies": {name: base[:10] for name in ("A", "S", "H")}} for qid in qids}}
    return runs, historical


class ExactFamilyTests(unittest.TestCase):
    def test_identical_variants_reproduce_h_and_zero_primary(self):
        order = [f"d{i:03d}" for i in range(100)]
        runs = {name: source(order) for name in family.SOURCES}
        old = {"queries": {"1": {"policies": {name: order[:10] for name in ("A", "S", "H")}}}}
        policies = family.build_policies(runs, old, ("1",))
        self.assertEqual(policies["queries"]["1"]["policies"]["F"], order[:10])
        self.assertEqual(policies["structural"]["absolute_effect_bound"], "0/1")
        self.assertEqual(policies["structural"]["changed_slots_total"], 0)
        self.assertTrue(policies["structural"]["scalar"]["common"]["feasible"])
        self.assertTrue(all(row["delta"] == "0/1" for row in policies["queries"]["1"]["candidates"]))
        result = family.analyze(policies, {"1": {}})
        self.assertEqual(result["contrasts"]["F-H"]["lower"], "0/1")
        self.assertEqual(result["contrasts"]["F-H"]["upper"], "0/1")
        self.assertEqual(result["exchange_ledger"], [])

    def test_changed_scores_need_not_change_heads(self):
        order = [f"d{i:03d}" for i in range(100)]
        variant = order[:-2] + list(reversed(order[-2:]))
        sources = {name: source(variant if name == "D" else order)["1"] for name in family.SOURCES}
        query = family.build_query(sources)
        self.assertEqual(query["policies"]["F"], query["policies"]["H"])
        changed = [row["docid"] for row in query["candidates"] if row["delta"] != "0/1"]
        self.assertEqual(changed, ["d098", "d099"])

    def test_family_mean_is_not_three_to_one_and_can_escape_without_new_access(self):
        runs, old = pareto_fixture()
        policies = family.build_policies(runs, old, ("1",))
        query = policies["queries"]["1"]
        self.assertEqual(query["policies"]["H"], ["y"] + [f"x{i:02d}" for i in range(1, 10)])
        self.assertEqual(query["policies"]["F"], [f"x{i:02d}" for i in range(1, 11)])
        self.assertEqual(query["entrants"], ["x10"])
        self.assertEqual(query["exits"], ["y"])
        self.assertEqual(query["scalar"]["coverage_outside"], [])
        self.assertFalse(query["scalar"]["feasible"])
        self.assertEqual(query["scalar"]["pareto_witness"], {"head": "x01", "excluded": "y"})
        by_doc = {row["docid"]: row for row in query["candidates"]}
        self.assertEqual(by_doc["y"]["F"], "127/4880")
        self.assertEqual(by_doc["x10"]["F"], "211/7455")
        self.assertEqual(by_doc["x10"]["delta"], "1/7455")
        self.assertEqual(by_doc["y"]["delta"], "-33/4880")
        self.assertEqual(policies["structural"]["absolute_effect_bound"], "1/10")

    def test_same_structural_escape_can_help_harm_or_remain_unknown(self):
        runs, old = pareto_fixture()
        policies = family.build_policies(runs, old, ("1",))
        for labels, lower, upper in (({"x10": 2, "y": 0}, "1/10", "1/10"),
                                      ({"x10": 0, "y": 1}, "-1/10", "-1/10"), ({}, "-1/10", "1/10")):
            with self.subTest(labels=labels):
                result = family.analyze(policies, {"1": labels})
                self.assertEqual((result["contrasts"]["F-H"]["lower"], result["contrasts"]["F-H"]["upper"]), (lower, upper))
                self.assertEqual(result["exchange_counts"]["entrant_outside_original_pool"], 0)
                self.assertEqual([row["role"] for row in result["exchange_ledger"]], ["entrant", "exit"])
                self.assertEqual(result["exchange_ledger"][0]["ranks"], {"A": 11, "D": 10, "T": 10, "S": 11})

    def test_decomposition_categories_and_exact_values(self):
        self.assertEqual(family.component(1, 2), {"category": "shared", "value": "-1/11346"})
        self.assertEqual(family.component(None, 1), {"category": "arrival", "value": "1/183"})
        self.assertEqual(family.component(1, None), {"category": "departure", "value": "-1/183"})
        self.assertEqual(family.component(None, None), {"category": "absent", "value": "0/1"})
        order = [f"d{i:03d}" for i in range(100)]
        d = ["new"] + order[:99]
        query = family.build_query({name: source(d if name == "D" else order)["1"] for name in family.SOURCES})
        rows = {row["docid"]: row for row in query["candidates"]}
        self.assertFalse(rows["new"]["in_original_pool"])
        self.assertEqual(rows["new"]["decomposition"]["D"]["category"], "arrival")
        self.assertEqual(rows["d099"]["decomposition"]["D"]["category"], "departure")
        for row in rows.values():
            self.assertEqual(Fraction(row["F"]) - Fraction(row["H"]),
                             Fraction(row["decomposition"]["D"]["value"]) + Fraction(row["decomposition"]["T"]["value"]))

    def test_all_thirty_queries_share_fixed_denominator_and_slot_bound(self):
        qids = tuple(str(i) for i in range(1, 31))
        runs, old = pareto_fixture(qids)
        policies = family.build_policies(runs, old, qids)
        labels = {qid: {"x10": 0, "y": 0} for qid in qids}
        labels["1"]["x10"] = 2
        result = family.analyze(policies, labels)
        self.assertEqual(result["contrasts"]["F-H"]["lower"], "1/300")
        self.assertEqual(policies["structural"]["changed_slots_total"], 30)
        self.assertEqual(policies["structural"]["changed_query_count"], 30)
        self.assertEqual(policies["structural"]["absolute_effect_bound"], "1/10")

    def test_historical_orders_and_source_depth_are_gates(self):
        runs, old = pareto_fixture()
        for name in ("A", "S", "H"):
            changed = copy.deepcopy(old)
            changed["queries"]["1"]["policies"][name].reverse()
            with self.subTest(name=name), self.assertRaisesRegex(family.core.ContractError, "historical"):
                family.build_policies(runs, changed, ("1",))
        runs["A"]["1"]["full_depth"] = 99
        with self.assertRaisesRegex(family.core.ContractError, "depth"):
            family.build_policies(runs, old, ("1",))

    def test_signed_unknown_bounds_are_sharp_under_every_completion(self):
        left = [f"common{i}" for i in range(8)] + ["p1", "p2"]
        right = left[:8] + ["n1", "n2"]
        support = ["p1", "p2", "n1", "n2"]
        for assignment in itertools.product((None, 0, 1), repeat=4):
            labels = {doc: value for doc, value in zip(support, assignment) if value is not None}
            bounds = family.core.contrast_bounds(left, right, labels)
            unknown = [doc for doc in support if doc not in labels]
            values = []
            for completion in itertools.product((0, 1), repeat=len(unknown)):
                full = {**labels, **dict(zip(unknown, completion))}
                values.append(Fraction(full["p1"] + full["p2"] - full["n1"] - full["n2"], 10))
            self.assertEqual(Fraction(bounds["lower"]), min(values))
            self.assertEqual(Fraction(bounds["upper"]), max(values))
            self.assertEqual(len(bounds["support"]), 4)


class ScalarRepresentationTests(unittest.TestCase):
    def test_nonnegative_unbounded_interval_and_id_tie_open_endpoint(self):
        closed = family.scalar_interval(["a"], {"a": 1, "z": 0}, {"a": 0, "z": 0}, {"a", "z"})
        self.assertEqual(closed["interval"], {"lower": "0/1", "lower_closed": True, "upper": None, "upper_closed": None})
        opened = family.scalar_interval(["z"], {"z": 1, "a": 0}, {"z": 0, "a": 0}, {"a", "z"})
        self.assertTrue(opened["feasible"])
        self.assertFalse(opened["interval"]["lower_closed"])
        self.assertTrue(opened["lower_witness"]["strict"])

    def test_closed_singleton_and_open_contradiction(self):
        closed = family.scalar_interval(["a"], {"a": 1, "b": 0, "c": 2}, {"a": 1, "b": 2, "c": 0}, {"a", "b", "c"})
        self.assertTrue(closed["feasible"])
        self.assertEqual(closed["interval"], {"lower": "1/1", "lower_closed": True, "upper": "1/1", "upper_closed": True})
        opened = family.scalar_interval(["b"], {"b": 1, "a": 0, "c": 2}, {"b": 1, "a": 2, "c": 0}, {"a", "b", "c"})
        self.assertFalse(opened["feasible"])
        self.assertEqual(opened["reason"], "empty_interval")
        self.assertFalse(opened["interval"]["lower_closed"])

    def test_zero_slope_tie_and_strict_pareto_witnesses(self):
        tie = family.scalar_interval(["z"], {"z": 1, "a": 1}, {"z": 1, "a": 1}, {"a", "z"})
        self.assertEqual(tie["reason"], "zero_slope")
        self.assertIsNone(tie["zero_slope_witness"]["threshold"])
        self.assertTrue(tie["zero_slope_witness"]["strict"])
        dominated = family.scalar_interval(["a"], {"a": 1, "z": 2}, {"a": 1, "z": 2}, {"a", "z"})
        self.assertEqual(dominated["reason"], "empty_interval")
        self.assertEqual(dominated["pareto_witness"], {"head": "a", "excluded": "z"})

    def test_coverage_failure_precedes_other_impossibilities(self):
        result = family.scalar_interval(["outside"], {"inside": 1}, {"inside": 1}, {"inside"})
        self.assertFalse(result["feasible"])
        self.assertEqual(result["reason"], "coverage")
        self.assertEqual(result["coverage_outside"], ["outside"])
        self.assertIsNone(result["pareto_witness"])
        self.assertIsNone(result["interval"])
        self.assertEqual(result["constraint_count"], 0)

    def test_individually_feasible_queries_can_have_empty_common_interval(self):
        first = family.scalar_interval(["a"], {"a": 0, "z": 1}, {"a": 1, "z": 0}, {"a", "z"})
        second = family.scalar_interval(["a"], {"a": 1, "z": 0}, {"a": 0, "z": 2}, {"a", "z"})
        self.assertTrue(first["feasible"] and second["feasible"])
        result = family.common_scalar_interval({"1": first, "2": second})
        self.assertFalse(result["feasible"])
        self.assertEqual(result["reason"], "empty_common")
        self.assertEqual(result["interval"]["lower"], "2/1")
        self.assertEqual(result["interval"]["upper"], "1/1")
        self.assertEqual(result["lower_witness"]["qid"], "2")
        self.assertEqual(result["upper_witness"]["qid"], "1")

    def test_open_upper_and_only_infinite_limit_do_not_admit_finite_weight(self):
        opened = family.scalar_interval(["z"], {"z": 0, "a": 1}, {"z": 1, "a": 0}, {"a", "z"})
        self.assertEqual(opened["interval"]["upper"], "1/1")
        self.assertFalse(opened["interval"]["upper_closed"])
        impossible = family.scalar_interval(["z"], {"z": 1, "a": 1}, {"z": 0, "a": 1}, {"a", "z"})
        self.assertFalse(impossible["feasible"])
        self.assertEqual(impossible["reason"], "zero_slope")


class CustodyAndPhaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.output = self.root / "output"
        qids = family.core.QUERY_IDS
        runs, old = pareto_fixture(qids)
        for name in family.SOURCES:
            (self.inputs / (name + ".run")).write_text(run_text(runs[name]["1"]["full_order"], qids))
        (self.inputs / "docids.txt").write_text("\n".join(runs["A"]["1"]["full_order"]) + "\n")
        (self.inputs / "late.qrels").write_text("".join(f"{qid} 0.5 y 0\n{qid} 1 x10 2\n" for qid in qids))
        for name in family.REQUIRED_FROZEN:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name not in (family.PLAN, family.HISTORICAL):
                path.write_text("frozen synthetic source\n")
        family.write_json(self.root / family.HISTORICAL, old)
        cached = {name: {"path": str((self.inputs / name).relative_to(self.root)), **family.core.identity(self.inputs / name)}
                  for name in ("A.run", "S.run", "docids.txt", "late.qrels")}
        items = {key: {"filename": key + ".run", "expected_bytes": (self.inputs / (key + ".run")).stat().st_size,
                       "max_bytes": 1000000} for key in ("D", "T")}
        family.write_json(self.root / family.PLAN, {"cached": cached, "items": items, "max_total_bytes": 2000000})
        frozen = {name: family.core.identity(self.root / name)["sha256"] for name in family.REQUIRED_FROZEN}
        self.preflight, self.acquisition = self.root / "preflight.json", self.root / "acquisition.json"
        family.write_json(self.preflight, {"status": "passed", "frozen": frozen})
        family.write_json(self.acquisition, {"status": "passed", "frozen": frozen,
                                            "inputs": {key + ".run": family.core.identity(self.inputs / (key + ".run")) for key in ("D", "T")}})
        self.root_patch = patch.object(family, "ROOT", self.root)
        self.hash_patch = patch.object(family, "HISTORICAL_SHA256", frozen[family.HISTORICAL])
        self.root_patch.start()
        self.hash_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.hash_patch.stop)

    def invoke(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return family.main(["--preflight", str(self.preflight), "--acquisition", str(self.acquisition),
                                "--inputs", str(self.inputs), "--output", str(self.output)])

    def test_complete_phase_saves_label_free_artifacts_before_qrels(self):
        original_parser = family.label_parser.parse_qrels
        seen = []
        def assert_saved(*args, **kwargs):
            self.assertTrue((self.output / "policies.json").is_file())
            self.assertFalse((self.output / "analysis.json").exists())
            seen.append(family.core.identity(self.output / "policies.json")["sha256"])
            return original_parser(*args, **kwargs)
        with patch.object(family.label_parser, "parse_qrels", side_effect=assert_saved):
            self.assertEqual(self.invoke(), 0)
        manifest = family.core.read_json(self.output / "manifest.json")
        self.assertEqual(seen, [manifest["labels_joined_after_policies_sha256"]])
        self.assertEqual(manifest["preflight"], "preflight.json")
        self.assertEqual(manifest["acquisition"], "acquisition.json")
        self.assertEqual(manifest["inputs"]["A.run"]["path"], "inputs/A.run")
        self.assertIn("output/policies.json", manifest["tracked_before"])
        self.assertTrue(all(not Path(path).is_absolute() for path in manifest["tracked_after"]))
        self.assertEqual(family.artifact_path(self.root.parent / "outside-synthetic-root"),
                         str(self.root.parent / "outside-synthetic-root"))
        result = family.core.read_json(self.output / "analysis.json")
        self.assertEqual(result["contrasts"]["F-H"]["lower"], "1/10")

    def test_changed_cached_or_new_inputs_stop_before_parsing(self):
        for filename in ("A.run", "D.run", "late.qrels"):
            path = self.inputs / filename
            old = path.read_bytes()
            path.write_bytes(old + b" ")
            self.output = self.root / ("failed-" + filename)
            with patch.object(family.doc_parser, "parse_docids", side_effect=AssertionError("parsed changed inputs")):
                self.assertEqual(self.invoke(), 1)
            failure = family.core.read_json(self.output / "failure.json")
            self.assertEqual(failure["error_type"], "ContractError")
            path.write_bytes(old)

    def test_mutation_after_labels_and_exclusive_output_are_failures(self):
        original_parser = family.label_parser.parse_qrels
        def mutate(*args, **kwargs):
            result = original_parser(*args, **kwargs)
            with (self.inputs / "D.run").open("a") as stream:
                stream.write(" ")
            return result
        with patch.object(family.label_parser, "parse_qrels", side_effect=mutate):
            self.assertEqual(self.invoke(), 1)
        self.assertFalse((self.output / "success.json").exists())
        saved = family.core.identity(self.output / "failure.json")
        self.assertEqual(self.invoke(), 1)
        self.assertEqual(saved, family.core.identity(self.output / "failure.json"))
        self.assertEqual(len(list(self.root.glob("output.failure-*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
