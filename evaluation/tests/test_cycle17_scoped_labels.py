"""Synthetic-only tests for retaining inert qrels outside the run inventory."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle17_minority_exchange as original
from evaluation import cycle17_minority_exchange_corrected as corrected
from evaluation import cycle17_minority_exchange_compatible as compatible
from evaluation import cycle17_scoped_labels as scoped


def run(order):
    return "".join(f"1 Q0 {doc} {rank} {100 - rank} fixture\n" for rank, doc in enumerate(order, 1))


class ScopedJudgmentTests(unittest.TestCase):
    def test_outside_labels_retained_without_mutating_document_universe(self):
        docids = {"inside"}
        labels = scoped.parse_qrels("1 0.5 inside 0\n1 1 outside 2\n", docids, ("1",))
        self.assertEqual(labels, {"1": {"inside": 0, "outside": 2}})
        self.assertEqual(docids, {"inside"})
        with self.assertRaisesRegex(original.ContractError, "outside Round1"):
            original.parse_qrels("1 1 outside 2\n", docids, ("1",))

    def test_added_outside_labels_leave_every_fixed_policy_and_contrast_unchanged(self):
        common = [f"d{i}" for i in range(10)]
        docids = set(common) | {"minority"}
        a = compatible.parse_run(run(common), docids, ("1",))
        s = compatible.parse_run(run(["minority"] + common), docids, ("1",))
        policies = original.prepare_policies(a, s, ("1",))
        policies_before = copy.deepcopy(policies)
        early_text = "1 0.5 d0 2\n1 0.5 d9 0\n"
        base = scoped.parse_qrels(early_text, docids, ("1",))
        extra = scoped.parse_qrels(early_text + "1 1 outside-positive 2\n1 1 outside-negative 0\n", docids, ("1",))
        before, after = original.analyze(policies, base), original.analyze(policies, extra)
        self.assertEqual(before.pop("qrels_pair_count"), 2)
        self.assertEqual(after.pop("qrels_pair_count"), 4)
        self.assertEqual(before, after)
        self.assertEqual(policies, policies_before)
        self.assertEqual(before["contrasts"]["M-H"]["width"], "1/10")

    def test_malformed_ids_and_existing_qrel_gates_still_reject(self):
        examples = ("", "1 0.5 outside 0\n1 1 outside 0\n", "1 0.5 outside 3\n",
                    "1 0.5 outside -1\n", "1 0 outside 1\n", "1 NaN outside 1\n",
                    "1 0.5 bad\x00id 1\n", "1 0.5 bad\x7fid 1\n", "1 0.5 dé 1\n",
                    "1 0.5 spaced id 1\n", "2 0.5 outside 1\n", "1 0.5 outside\n")
        for text in examples:
            with self.subTest(text=repr(text)), self.assertRaises(original.ContractError):
                scoped.parse_qrels(text, {"inside"}, ("1",))
        with self.assertRaisesRegex(original.ContractError, "cohort"):
            scoped.parse_qrels("1 0.5 outside 1\n", {"inside"}, ("1", "2"))

    def test_scoped_runtime_keeps_run_membership_and_policy_code_unchanged(self):
        docs = [f"d{i}" for i in range(10)]
        text = run(docs).replace("d0", "outside", 1)
        functions = {name: getattr(original, name) for name in ("build_query", "analyze", "compare_phases", "run_late")}
        with scoped.scoped_runtime():
            self.assertIs(original.parse_run, compatible.parse_run)
            with self.assertRaisesRegex(original.ContractError, "outside Round1"):
                original.parse_run(text, set(docs), ("1",))
            self.assertEqual(original.parse_qrels("1 1 outside 2\n", set(docs), ("1",)),
                             {"1": {"outside": 2}})
            for name, function in functions.items():
                self.assertIs(getattr(original, name), function)

    def test_all_overrides_restore_even_on_exception(self):
        names = ("parse_qrels", "parse_run", "parse_docids", "check_frozen")
        before = {name: getattr(original, name) for name in names}
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            with scoped.scoped_runtime():
                raise RuntimeError("fixture failure")
        for name, function in before.items():
            self.assertIs(getattr(original, name), function)

    def test_prior_policy_failure_and_all_corrections_are_required_and_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keys = (scoped.REQUIRED_FROZEN | compatible.REQUIRED_FROZEN | corrected.REQUIRED_FROZEN |
                    {original.PROTOCOL, original.PLAN, original.SOURCE, original.TESTS})
            frozen = {}
            for name in keys:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic frozen evidence\n")
                frozen[name] = original.identity(path)["sha256"]
            with patch.object(original, "ROOT", root), scoped.scoped_runtime():
                self.assertEqual(len(original.check_frozen(frozen)), len(keys))
                for name in scoped.REQUIRED_FROZEN:
                    incomplete = {key: value for key, value in frozen.items() if key != name}
                    with self.subTest(omitted=name), self.assertRaisesRegex(original.ContractError, "qrel correction omitted"):
                        original.check_frozen(incomplete)
                (root / scoped.PRIOR_PREPARED / "policies.json").write_text("changed frozen policy\n")
                with self.assertRaisesRegex(original.ContractError, "frozen identity changed"):
                    original.check_frozen(frozen)


if __name__ == "__main__":
    unittest.main()
