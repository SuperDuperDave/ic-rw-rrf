"""Synthetic-only checks for the separate Arrow string-width correction.

Optional real Parquet fixtures use the already acquired isolated decoder when
CYCLE15_TEST_DECODER_PATH and CYCLE15_TEST_DECODER_WHEEL are explicitly set.
They never read collection inputs or install a package.
"""

import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evaluation import cycle15_large_string_adapter as adapter

original = adapter.original


class Schema(list):
    @property
    def names(self):
        return [field.name for field in self]


class Reader:
    def __init__(self, fields, rows):
        self.schema_arrow = Schema(SimpleNamespace(name=name, type=kind) for name, kind in fields)
        self.rows = rows
        self.batches_requested = False

    def iter_batches(self, batch_size):
        self.batches_requested = True
        yield SimpleNamespace(to_pylist=lambda: self.rows)


class WidthAdapterTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"_id": "文献-é", "title": "Café\nβ", "text": "  e\u0301 / 東京 😀\r\n"}]
        self.arrow = SimpleNamespace(string=lambda: "string", large_string=lambda: "large_string")

    def read(self, widths, rows=None, names=("_id", "title", "text")):
        reader = Reader(list(zip(names, widths)), self.rows if rows is None else rows)
        parquet = SimpleNamespace(ParquetFile=lambda path: reader)
        schemas = {}
        value = adapter.parquet_texts("synthetic", self.arrow, parquet, "corpus", schemas)
        return value, schemas, reader

    def test_both_widths_and_mixed_widths_preserve_unicode_exactly(self):
        for widths in (("string",) * 3, ("large_string",) * 3, ("string", "large_string", "string")):
            with self.subTest(widths=widths):
                value, schemas, _ = self.read(widths)
                self.assertEqual(value, {"文献-é": ("Café\nβ", "  e\u0301 / 東京 😀\r\n")})
                self.assertEqual(schemas["corpus"], dict(zip(("_id", "title", "text"), widths)))
                self.assertIs(value["文献-é"][1], self.rows[0]["text"])

    def test_original_string_reader_and_correction_agree_on_existing_supported_type(self):
        reader = Reader([(name, "string") for name in ("_id", "title", "text")], self.rows)
        parquet = SimpleNamespace(ParquetFile=lambda path: reader)
        self.assertEqual(adapter.parquet_texts("synthetic", self.arrow, parquet, "queries"),
                         original.parquet_texts("synthetic", self.arrow, parquet, "queries"))

    def test_other_physical_types_fail_before_row_decoding(self):
        for bad_type in ("binary", "large_binary", "string_view", "int64", "dictionary<string>"):
            for index in range(3):
                with self.subTest(type=bad_type, column=index):
                    types = ["large_string"] * 3
                    types[index] = bad_type
                    reader = Reader(list(zip(("_id", "title", "text"), types)), self.rows)
                    parquet = SimpleNamespace(ParquetFile=lambda path: reader)
                    with self.assertRaisesRegex(original.ContractError, "unsupported Parquet schema"):
                        adapter.parquet_texts("synthetic", self.arrow, parquet, "corpus")
                    self.assertFalse(reader.batches_requested)

    def test_missing_extra_and_duplicate_fields_fail_before_rows(self):
        for names in (("_id", "text"), ("_id", "title", "text", "metadata"), ("_id", "title", "text", "text"), ("_id", "text", "text")):
            with self.subTest(names=names):
                reader = Reader([(name, "large_string") for name in names], self.rows)
                parquet = SimpleNamespace(ParquetFile=lambda path: reader)
                with self.assertRaises(original.ContractError):
                    adapter.parquet_texts("synthetic", self.arrow, parquet, "corpus")
                self.assertFalse(reader.batches_requested)

    def test_null_nonstring_duplicate_invalid_ID_and_empty_rows_fail(self):
        invalid_rows = [[], self.rows * 2]
        for field in ("_id", "title", "text"):
            invalid_rows.append([{**self.rows[0], field: None}])
            invalid_rows.append([{**self.rows[0], field: 17}])
        invalid_rows.extend([{**self.rows[0], "_id": bad}] for bad in ("", "two words", "line\nbreak"))
        for rows in invalid_rows:
            with self.subTest(rows=rows):
                with self.assertRaises(original.ContractError):
                    self.read(("large_string",) * 3, rows)

    def test_input_identity_failure_precedes_decoder_or_qrel_reads(self):
        gate = {"source_sha256": dict.fromkeys(adapter.CORRECTION_SOURCES, "fixture")}
        with patch.object(adapter, "require_corrected_preflight", return_value=gate), \
                patch.object(original, "verify_frozen_code", return_value={}), \
                patch.object(original, "read_json", return_value={}), \
                patch.object(original, "verify_inputs", side_effect=original.ContractError("identity mismatch")), \
                patch.object(original, "pinned_decoder") as decoder, \
                patch.object(original, "read_binary_qrels") as qrels, \
                patch.object(original, "validate_components") as components:
            with self.assertRaisesRegex(original.ContractError, "identity mismatch"):
                adapter.load_validate({}, preflight="synthetic")
            decoder.assert_not_called()
            qrels.assert_not_called()
            components.assert_not_called()


class PreflightAncestryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root_patch = patch.object(original, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        original_paths = set(original.FROZEN_SHA256) | {
            "evaluation/cycle15_scifact_transfer.py", "evaluation/tests/test_cycle15_scifact_transfer.py", "original-extra.py"}
        hashes = {}
        for relative in original_paths | set(adapter.CORRECTION_SOURCES + adapter.CUSTODY_SOURCES):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic source: " + relative)
            hashes[relative] = original.file_identity(path)["sha256"]
        self.ancestor = self.root / "ancestor.json"
        self.ancestor.write_text(json.dumps({"status": "passed", "source_sha256": {name: hashes[name] for name in original_paths}}))
        self.corrected = self.root / "corrected.json"
        self.receipt = {"status": "passed", "source_sha256": hashes,
                        "original_preflight": {"path": "ancestor.json", "sha256": original.file_identity(self.ancestor)["sha256"]}}
        self.save()

    def save(self):
        self.corrected.write_text(json.dumps(self.receipt))

    def test_corrected_preflight_keeps_every_original_and_added_source_identity(self):
        checked = adapter.require_corrected_preflight(self.corrected)
        self.assertEqual(checked["source_sha256"], self.receipt["source_sha256"])
        self.assertEqual(checked["original_preflight"], self.receipt["original_preflight"])

    def test_missing_extra_original_or_correction_source_is_rejected(self):
        for relative in ("original-extra.py", *adapter.CORRECTION_SOURCES, *adapter.CUSTODY_SOURCES):
            with self.subTest(relative=relative):
                value = self.receipt["source_sha256"].pop(relative)
                self.save()
                with self.assertRaises(original.ContractError):
                    adapter.require_corrected_preflight(self.corrected)
                self.receipt["source_sha256"][relative] = value

    def test_modified_ancestor_receipt_is_rejected(self):
        self.ancestor.write_text(self.ancestor.read_text() + "\n")
        with self.assertRaisesRegex(original.ContractError, "original preflight identity mismatch"):
            adapter.require_corrected_preflight(self.corrected)


class RealParquetWidthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = os.environ.get("CYCLE15_TEST_DECODER_PATH")
        wheel = os.environ.get("CYCLE15_TEST_DECODER_WHEEL")
        if not directory or not wheel:
            raise unittest.SkipTest("set isolated decoder fixture paths to enable real Parquet checks")
        plan = original.read_json(original.ROOT / original.PLAN)
        context = original.pinned_decoder(directory, plan, wheel)
        cls.arrow, cls.parquet, cls.decoder_receipt = context.__enter__()
        cls.addClassCleanup(context.__exit__, None, None, None)

    def test_real_unicode_fixtures_both_widths_and_invalid_schemas_or_rows(self):
        arrow, parquet = self.arrow, self.parquet
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.parquet"
            source = {"_id": ["文献-é"], "title": ["Café\nβ"], "text": ["  e\u0301 / 東京 😀\r\n"]}
            expected = {"文献-é": ("Café\nβ", "  e\u0301 / 東京 😀\r\n")}
            for width in (arrow.string(), arrow.large_string()):
                table = arrow.table({name: arrow.array(values, type=width) for name, values in source.items()})
                parquet.write_table(table, path)
                self.assertEqual(adapter.parquet_texts(path, arrow, parquet, "corpus"), expected)
            bad_tables = [
                arrow.table({"_id": ["d"], "title": ["title"], "text": arrow.array([b"bytes"], type=arrow.binary())}),
                arrow.table({"_id": ["d"], "title": ["title"]}),
                arrow.table([arrow.array(["d"])] * 4, names=["_id", "title", "text", "text"]),
                arrow.table({"_id": ["d"], "title": ["title"], "text": arrow.array([None], type=arrow.large_string())}),
                arrow.table({"_id": ["d", "d"], "title": ["a", "b"], "text": ["c", "d"]}),
            ]
            for number, table in enumerate(bad_tables):
                with self.subTest(invalid=number):
                    parquet.write_table(table, path)
                    with self.assertRaises(original.ContractError):
                        adapter.parquet_texts(path, arrow, parquet, "corpus")


if __name__ == "__main__":
    unittest.main()
