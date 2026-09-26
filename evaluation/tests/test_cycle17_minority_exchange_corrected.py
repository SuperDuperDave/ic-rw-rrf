"""Synthetic verification of the sole post-failure document-ID correction."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle17_minority_exchange as original
from evaluation import cycle17_minority_exchange_corrected as corrected


class CorrectedDocumentUniverseTests(unittest.TestCase):
    def test_duplicate_lines_collapse_without_changing_exact_keys(self):
        self.assertEqual(corrected.parse_docids("a\na\nb\na\n"), {"a", "b"})
        self.assertEqual(corrected.parse_docids("a\nb"), {"a", "b"})

    def test_spaced_entries_are_opaque_and_are_not_stripped_or_tokenized(self):
        result = corrected.parse_docids("A.; Bennett\nA.; Bennett\n leading\ntrailing \nx\n")
        self.assertEqual(result, {"A.; Bennett", " leading", "trailing ", "x"})
        self.assertTrue({"A.;", "Bennett", "leading", "trailing"}.isdisjoint(result))

    def test_opaque_spaced_key_cannot_authorize_individual_run_or_qrel_tokens(self):
        docids = corrected.parse_docids("A.; Bennett\n" + "\n".join(f"d{i}" for i in range(10)))
        run = "".join(f"1 Q0 d{i} {i + 1} {10 - i} fixture\n" for i in range(10))
        original.parse_run(run, docids, ("1",))
        with self.assertRaisesRegex(original.ContractError, "outside Round1"):
            original.parse_run(run.replace("d0", "Bennett", 1), docids, ("1",))
        with self.assertRaisesRegex(original.ContractError, "six fields"):
            original.parse_run(run.replace("d0", "A.; Bennett", 1), docids, ("1",))
        with self.assertRaisesRegex(original.ContractError, "outside Round1"):
            original.parse_qrels("1 0.5 Bennett 1\n", docids, ("1",))
        with self.assertRaisesRegex(original.ContractError, "four fields"):
            original.parse_qrels("1 0.5 A.; Bennett 1\n", docids, ("1",))

    def test_empty_blank_control_and_nonascii_entries_are_rejected(self):
        examples = ("", "\n", "a\n\n", "   ", "a\n  \n", "a\tb", "a\rb", "a\r\n",
                    "a\vb", "a\fb", "a\x00b", "a\x1fb", "a\x7fb", "é", "a\u2028b")
        for text in examples:
            with self.subTest(text=repr(text)), self.assertRaises(original.ContractError):
                corrected.parse_docids(text)

    def test_runtime_restores_original_and_does_not_change_other_functions(self):
        parser, custody = original.parse_docids, original.check_frozen
        unchanged = {name: getattr(original, name) for name in
                     ("parse_run", "parse_qrels", "build_query", "analyze", "compare_phases", "run_late")}
        with self.assertRaisesRegex(original.ContractError, "duplicate"):
            original.parse_docids("a\na\n")
        with corrected.corrected_runtime():
            self.assertIs(original.parse_docids, corrected.parse_docids)
            self.assertEqual(original.parse_docids("a\na\n"), {"a"})
            for name, function in unchanged.items():
                self.assertIs(getattr(original, name), function)
        self.assertIs(original.parse_docids, parser)
        self.assertIs(original.check_frozen, custody)
        with self.assertRaisesRegex(original.ContractError, "duplicate"):
            original.parse_docids("a\na\n")

    def test_runtime_restores_overrides_even_when_cli_raises(self):
        parser, custody = original.parse_docids, original.check_frozen
        with patch.object(original, "main", side_effect=RuntimeError("fixture failure")):
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                corrected.main([])
        self.assertIs(original.parse_docids, parser)
        self.assertIs(original.check_frozen, custody)

    def test_every_correction_identity_is_required_and_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keys = corrected.REQUIRED_FROZEN | {original.PROTOCOL, original.PLAN, original.SOURCE, original.TESTS}
            frozen = {}
            for name in keys:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic frozen evidence\n")
                frozen[name] = original.identity(path)["sha256"]
            with patch.object(original, "ROOT", root), corrected.corrected_runtime():
                self.assertEqual(len(original.check_frozen(frozen)), len(keys))
                for name in corrected.REQUIRED_FROZEN:
                    incomplete = {key: value for key, value in frozen.items() if key != name}
                    with self.subTest(omitted=name), self.assertRaisesRegex(original.ContractError, "correction omitted"):
                        original.check_frozen(incomplete)
                (root / corrected.FAILURE).write_text("changed failure evidence\n")
                with self.assertRaisesRegex(original.ContractError, "frozen identity changed"):
                    original.check_frozen(frozen)


if __name__ == "__main__":
    unittest.main()
