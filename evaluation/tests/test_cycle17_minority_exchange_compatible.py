"""Synthetic-only coverage of ignored zero-based supplied-rank compatibility."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle17_minority_exchange as original
from evaluation import cycle17_minority_exchange_corrected as corrected
from evaluation import cycle17_minority_exchange_compatible as compatible


def fixture(zero_based=False):
    docs = [f"d{i:02d}" for i in range(10)]
    text = "".join(f"1 Q0 {doc} {index if zero_based else index + 1} {index} fixture\n"
                   for index, doc in enumerate(docs))
    return docs, text


class SuppliedRankCompatibilityTests(unittest.TestCase):
    def test_zero_based_supplied_metadata_preserved_and_score_order_unchanged(self):
        docs, text = fixture(zero_based=True)
        query = compatible.parse_run(text, set(docs), ("1",))["1"]
        self.assertEqual(query["full_order"], list(reversed(docs)))
        self.assertEqual(query["details"]["d00"]["supplied_rank"], 0)
        self.assertEqual(query["details"]["d00"]["canonical_rank"], 10)
        for index, doc in enumerate(docs):
            self.assertEqual(query["details"][doc]["supplied_rank"], index)
            self.assertEqual(query["details"][doc]["score"], str(index))
        self.assertEqual(query["supplied_rank_disagreements"], 9)

    def test_positive_rank_inputs_are_identical_to_frozen_original_outputs(self):
        docs, text = fixture()
        self.assertEqual(compatible.parse_run(text, set(docs), ("1",)),
                         original.parse_run(text, set(docs), ("1",)))
        tied = text.replace("d00 1 0", "d00 1 8.00")
        self.assertEqual(compatible.parse_run(tied, set(docs), ("1",)),
                         original.parse_run(tied, set(docs), ("1",)))

    def test_negative_noncanonical_and_other_invalid_rows_still_rejected(self):
        docs, text = fixture()
        for rank in ("-1", "-0", "+0", "+1", "00", "01", "1.0", "NaN"):
            with self.subTest(rank=rank), self.assertRaisesRegex(original.ContractError, "canonical nonnegative"):
                compatible.parse_run(text.replace("d00 1 0", f"d00 {rank} 0"), set(docs), ("1",))
        for invalid in (text + text.splitlines()[0], text.replace("d00", "missing", 1),
                        text.replace("d00 1 0", "d00 1 NaN"), text.replace(" fixture", "", 1)):
            with self.subTest(text=invalid[:40]), self.assertRaises(original.ContractError):
                compatible.parse_run(invalid, set(docs), ("1",))

    def test_runtime_only_changes_parsers_and_custody_and_restores_on_exception(self):
        run_parser, doc_parser, custody = original.parse_run, original.parse_docids, original.check_frozen
        unchanged = {name: getattr(original, name) for name in
                     ("parse_qrels", "build_query", "analyze", "compare_phases", "run_late")}
        docs, text = fixture(zero_based=True)
        with self.assertRaisesRegex(original.ContractError, "positive integer"):
            original.parse_run(text, set(docs), ("1",))
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            with compatible.compatible_runtime():
                self.assertIs(original.parse_run, compatible.parse_run)
                self.assertIs(original.parse_docids, corrected.parse_docids)
                original.parse_run(text, set(docs), ("1",))
                for name, function in unchanged.items():
                    self.assertIs(getattr(original, name), function)
                raise RuntimeError("fixture failure")
        self.assertIs(original.parse_run, run_parser)
        self.assertIs(original.parse_docids, doc_parser)
        self.assertIs(original.check_frozen, custody)

    def test_new_and_prior_correction_evidence_are_required_and_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keys = (compatible.REQUIRED_FROZEN | corrected.REQUIRED_FROZEN |
                    {original.PROTOCOL, original.PLAN, original.SOURCE, original.TESTS})
            frozen = {}
            for name in keys:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic frozen evidence\n")
                frozen[name] = original.identity(path)["sha256"]
            with patch.object(original, "ROOT", root), compatible.compatible_runtime():
                self.assertEqual(len(original.check_frozen(frozen)), len(keys))
                for name in compatible.REQUIRED_FROZEN | corrected.REQUIRED_FROZEN:
                    incomplete = {key: value for key, value in frozen.items() if key != name}
                    with self.subTest(omitted=name), self.assertRaisesRegex(original.ContractError, "omitted"):
                        original.check_frozen(incomplete)
                (root / compatible.AUDIT).write_text("changed audit\n")
                with self.assertRaisesRegex(original.ContractError, "frozen identity changed"):
                    original.check_frozen(frozen)


if __name__ == "__main__":
    unittest.main()
