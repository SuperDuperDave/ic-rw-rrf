"""Acquisition contract tests using handcrafted data and mocked HTTP, never network."""

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "acquire_cycle02_source.py"
SPEC = importlib.util.spec_from_file_location("acquire_cycle02_source", SCRIPT)
acquisition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquisition)


class Response(io.BytesIO):
    status = 200

    def __init__(self, body, header=True):
        super().__init__(body)
        self.headers = {"Content-Length": str(len(body))} if header else {}


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.cache = self.root / "cache"
        self.output = self.root / "data/acquired"
        self.record = {"query": {"qid": "101", "text": "PRIVATE_QUERY_TEXT"},
                       "candidates": [
                           {"docid": "20", "score": 3.0, "doc": {"contents": "PRIVATE_PASSAGE_TEXT"}},
                           {"docid": "10", "score": 3.0, "doc": {"contents": "PRIVATE_PASSAGE_TEXT"}},
                           {"docid": "30", "score": 1, "doc": "PRIVATE_PASSAGE_TEXT"}]}
        self.body = self.encode([self.record])
        self.item = self.file_item(self.body)
        self.selection = self.root / "selection.json"
        self.write_selection([self.item])

    def encode(self, records):
        return b"".join((json.dumps(record) + "\n").encode() for record in records)

    def file_item(self, body, year=2019):
        return {"year": year, "filename": f"dl{year}_top1000.jsonl",
                "url": f"https://example.org/pinned-revision/dl{year}.jsonl",
                "expected_bytes": len(body), "expected_sha256": hashlib.sha256(body).hexdigest()}

    def write_selection(self, items):
        self.selection.write_text(json.dumps({"source_id": "fixture_source",
                                             "dataset_id": "owner/dataset",
                                             "dataset_revision": "pinned-revision",
                                             "files": items}))

    def run_acquisition(self, opener=None):
        return acquisition.acquire(self.selection, self.cache, self.output, root=self.root,
                                   opener=opener or (lambda *a, **k: Response(self.body)))

    def convert(self, records):
        raw = self.root / "raw.jsonl"
        raw.write_bytes(self.encode(records))
        return acquisition.convert_jsonl(raw, self.root / "converted.trec", "fixture_source")

    def test_conversion_preserves_order_ties_and_scores_without_text(self):
        stats = self.convert([self.record])
        self.assertEqual((self.root / "converted.trec").read_text(),
                         "101 Q0 20 1 3.0 fixture_source\n"
                         "101 Q0 10 2 3.0 fixture_source\n"
                         "101 Q0 30 3 1 fixture_source\n")
        self.assertEqual(stats["query_count"], 1)
        self.assertEqual(stats["row_count"], 3)
        self.assertEqual((stats["depth_min"], stats["depth_max"]), (3, 3))
        self.assertEqual(stats["adjacent_score_ties"], 1)
        self.assertEqual(stats["queries_with_score_ties"], 1)

    def test_integer_ids_are_normalized_and_duplicate_queries_rejected(self):
        other = copy.deepcopy(self.record)
        other["query"]["qid"] = 101
        with self.assertRaisesRegex(acquisition.AcquisitionError, "Duplicate query"):
            self.convert([self.record, other])
        self.assertFalse((self.root / "converted.trec").exists())

    def test_invalid_records_reject_without_partial_output_or_text_in_errors(self):
        variants = []
        duplicate = copy.deepcopy(self.record)
        duplicate["candidates"][1]["docid"] = "20"
        variants.append(duplicate)
        ascending = copy.deepcopy(self.record)
        ascending["candidates"][1]["score"] = 4
        variants.append(ascending)
        for value in (float("nan"), float("inf"), -float("inf"), True, "3.0", None):
            bad = copy.deepcopy(self.record)
            bad["candidates"][0]["score"] = value
            variants.append(bad)
        for field in ("qid", "docid"):
            for value in ("", "private id", "PRIVATE_QUERY_TEXT\n", "id\x00", True, None, []):
                bad = copy.deepcopy(self.record)
                target = bad["query"] if field == "qid" else bad["candidates"][0]
                target[field] = value
                variants.append(bad)
        for key in ("query", "candidates"):
            bad = copy.deepcopy(self.record)
            bad.pop(key)
            variants.append(bad)
        for candidates in ([], {}, None):
            bad = copy.deepcopy(self.record)
            bad["candidates"] = candidates
            variants.append(bad)
        variants.extend([None, [], {"query": {"qid": "1"}, "candidates": []}])
        for index, record in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaises(acquisition.AcquisitionError) as raised:
                    self.convert([record])
                self.assertNotIn("PRIVATE_", str(raised.exception))
                self.assertFalse((self.root / "converted.trec").exists())

    def test_invalid_json_and_duplicate_keys_never_echo_source(self):
        for body in (b"PRIVATE_QUERY_TEXT\n", b'{"query": {}, "query": "PRIVATE_QUERY_TEXT"}\n', b"\xff\n", b""):
            (self.root / "raw.jsonl").write_bytes(body)
            with self.assertRaises(acquisition.AcquisitionError) as raised:
                acquisition.convert_jsonl(self.root / "raw.jsonl", self.root / "converted.trec", "fixture")
            self.assertNotIn("PRIVATE_", str(raised.exception))
            self.assertFalse((self.root / "converted.trec").exists())

    def test_download_manifest_integrity_and_immutable_outputs(self):
        calls = []

        def opener(request, timeout):
            calls.append((request.full_url, timeout))
            return Response(self.body)

        manifest = self.run_acquisition(opener)
        self.assertEqual(calls, [(self.item["url"], 60)])
        run = manifest["derived_runs"][0]
        self.assertEqual(run["path"], "data/acquired/dl2019.trec")
        self.assertEqual(run["sha256"], acquisition.sha256_file(self.root / run["path"]))
        self.assertEqual(manifest["selection_sha256"], acquisition.sha256_file(self.selection))
        self.assertEqual(manifest["script_sha256"], acquisition.sha256_file(SCRIPT))
        self.assertEqual(manifest["original_inputs"][0]["bytes"], len(self.body))
        self.assertFalse(manifest["original_inputs"][0]["cache_reused"])
        for path in self.output.iterdir():
            self.assertNotIn("PRIVATE_", path.read_text())
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        with self.assertRaisesRegex(acquisition.AcquisitionError, "already exists"):
            self.run_acquisition(lambda *a, **k: self.fail("No fetch for existing output"))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})

    def test_empty_existing_output_also_rejected(self):
        self.output.mkdir(parents=True)
        with self.assertRaisesRegex(acquisition.AcquisitionError, "already exists"):
            self.run_acquisition(lambda *a, **k: self.fail("No fetch for existing output"))
        self.assertTrue(self.output.is_dir())

    def test_verified_cache_reuse_and_corrupt_cache_refetch(self):
        raw, reused = acquisition.acquire_raw(self.item, self.cache,
                                             opener=lambda *a, **k: Response(self.body))
        self.assertFalse(reused)
        same, reused = acquisition.acquire_raw(self.item, self.cache,
                                               opener=lambda *a, **k: self.fail("Cache should prevent fetch"))
        self.assertEqual(raw, same)
        self.assertTrue(reused)
        raw.write_bytes(b"x" * len(self.body))
        _, reused = acquisition.acquire_raw(self.item, self.cache,
                                           opener=lambda *a, **k: Response(self.body))
        self.assertFalse(reused)
        self.assertEqual(raw.read_bytes(), self.body)

    def test_download_hash_size_header_and_stream_bound_fail_cleanly(self):
        cases = [(b"x" * len(self.body), True, "SHA256"),
                 (self.body + b"x", True, "Content-Length"),
                 (self.body + b"x", False, "exceeds"),
                 (self.body[:-1], False, "byte count")]
        for body, header, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(acquisition.AcquisitionError, message):
                    self.run_acquisition(lambda *a, **k: Response(body, header=header))
                self.assertFalse(self.output.exists())
                self.assertEqual(list(self.cache.iterdir()), [])

    def test_second_file_failure_removes_first_run_but_keeps_verified_cache(self):
        invalid_body = b"PRIVATE_QUERY_TEXT\n"
        second = self.file_item(invalid_body, year=2020)
        self.write_selection([self.item, second])
        responses = iter([self.body, invalid_body])
        with self.assertRaises(acquisition.AcquisitionError):
            self.run_acquisition(lambda *a, **k: Response(next(responses)))
        self.assertFalse(self.output.exists())
        self.assertEqual(len(list(self.cache.iterdir())), 2)

    def test_failure_preserves_concurrent_unowned_file(self):
        def opener(*args, **kwargs):
            (self.output / "someone-elses.txt").write_text("keep")
            return Response(b"x" * len(self.body))

        with self.assertRaises(acquisition.AcquisitionError):
            self.run_acquisition(opener)
        self.assertEqual((self.output / "someone-elses.txt").read_text(), "keep")
        self.assertFalse((self.output / "source-manifest.json").exists())

    def test_manifest_failure_leaves_no_success_manifest(self):
        with patch.object(acquisition.os, "link", side_effect=OSError("fixture error")):
            with self.assertRaises(OSError):
                self.run_acquisition()
        self.assertFalse(self.output.exists())

    def test_relative_paths_resolve_against_root_from_arbitrary_cwd(self):
        original = Path.cwd()
        try:
            os.chdir(self.root.parent)
            manifest = acquisition.acquire("selection.json", "cache", "data/acquired",
                                           root=self.root, opener=lambda *a, **k: Response(self.body))
        finally:
            os.chdir(original)
        self.assertEqual(manifest["derived_runs"][0]["path"], "data/acquired/dl2019.trec")

    def test_raw_cache_cannot_live_inside_outputs(self):
        with self.assertRaisesRegex(acquisition.AcquisitionError, "Raw cache"):
            acquisition.acquire(self.selection, self.output / "cache", self.output, root=self.root)
        self.assertFalse(self.output.exists())

    def test_conversion_never_overwrites_existing_file(self):
        (self.root / "converted.trec").write_text("keep")
        with self.assertRaises(FileExistsError):
            self.convert([self.record])
        self.assertEqual((self.root / "converted.trec").read_text(), "keep")

    def test_cli_sanitizes_transport_errors_and_prints_no_source_text(self):
        stderr, stdout = io.StringIO(), io.StringIO()
        with patch.object(acquisition, "ROOT", self.root), \
                patch.object(acquisition, "acquire", side_effect=OSError("PRIVATE_PASSAGE_TEXT")), \
                contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            status = acquisition.main(["--selection", str(self.selection), "--cache-dir", str(self.cache),
                                       "--output", str(self.output)])
        self.assertEqual(status, 1)
        self.assertNotIn("PRIVATE_", stderr.getvalue() + stdout.getvalue())

    def test_help_available_from_arbitrary_cwd(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=self.root,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Selection schema", result.stdout)


if __name__ == "__main__":
    unittest.main()
