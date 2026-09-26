"""Synthetic-only coverage; these tests never open historical benchmark rows."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle16_support_census as census


def ranks(docs):
    return {doc: rank for rank, doc in enumerate(docs, 1)}


def support_fixture():
    lexical = ranks(["u%d" % i for i in range(1, 12)])
    runs = {name: dict(lexical) for name in census.LEXICAL}
    runs["S"] = ranks(["u%d" % i for i in range(1, 11)] + ["inside", "outside"])
    runs["P"] = ranks(list(lexical) + ["inside"])
    runs["B"] = ranks(list(lexical) + ["inside", "outside"])
    return runs, {"u1", "u11", "inside", "outside", "neither"}


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def parse(self, text, qrels=False):
        path = self.root / "fixture"
        path.write_text(text, encoding="utf-8")
        return census.read_rows(path, qrels=qrels)

    def test_deeper_only_positives_and_all_partitions(self):
        runs, positives = support_fixture()
        query, rows = census.analyze_query("001", runs, positives)
        self.assertEqual(query["positive_partition"], {"U-and-S": 1, "U-only": 1, "S-only": 2, "neither": 1})
        self.assertEqual(query["S_only_positive_head"], 0)
        self.assertEqual(query["S_only_positive_deep"], 2)
        self.assertEqual(query["S_only_positive_inside_P"], 1)
        self.assertEqual(query["S_only_positive_outside_P"], 1)
        self.assertTrue(query["exclusion_certificate"]["certified"])
        self.assertEqual([row["docid"] for row in rows], sorted(positives))
        absent = next(row for row in rows if row["docid"] == "neither")
        self.assertIsNone(absent["S_rank"])
        self.assertFalse(absent["in_P"])
        summary = census.summarize([query])
        self.assertEqual(summary["positive_partition_query_counts"]["S-only"], 1)
        self.assertEqual(summary["S_only_positive_deep"], {"pairs": 2, "queries": 1})
        self.assertIn("preserve", summary["decision"])

    def test_certificates_strict_equality_lower_and_small_union(self):
        lexical = ranks(["u%d" % i for i in range(1, 11)])
        for s_rank, expected, t, v in [(11, True, "1/70", "1/71"),
                                       (10, False, "1/70", "1/70"),
                                       (1, False, "1/70", "1/61")]:
            with self.subTest(s_rank=s_rank):
                result = census.certificate([lexical, {}, {}, {}], {"solo": s_rank})
                self.assertEqual((result["certified"], result["T"], result["V"]), (expected, t, v))
        small = census.certificate([ranks(list(lexical)[:9]), {}, {}, {}], {"solo": 1})
        self.assertFalse(small["certified"])
        self.assertIsNone(small["T"])
        no_only = census.certificate([lexical] * 4, lexical)
        self.assertIsNone(no_only["V"])
        self.assertFalse(no_only["certified"])
        self.assertEqual(no_only["T"], "2/35")

    def test_top10_entries_keep_positive_and_unjudged_distinct(self):
        runs = {name: {"u": 1} for name in census.LEXICAL}
        runs.update(S=ranks(["solo", "unjudged", "u"] + ["f%d" % i for i in range(8)]),
                    P={"u": 1}, B=ranks(["u", "solo", "unjudged"] + ["f%d" % i for i in range(8)]))
        query, _ = census.analyze_query("q", runs, {"solo"})
        summary = census.summarize([query])
        self.assertEqual(summary["B_top10"], {"denominator": 10, "S_only_entries": 9,
                                             "queries_with_S_only": 1, "explicit_qrel_positive_entries": 1,
                                             "unjudged_entries": 8})
        self.assertEqual(query["S_only_positive_head"], 1)
        self.assertEqual(query["B_top10_S_only_entries"][0]["docid"], "solo")

    def test_certificate_contradiction_stops(self):
        runs, positives = support_fixture()
        runs["B"] = ranks(["inside"] + list(runs["B"])[:10])
        with self.assertRaisesRegex(census.ContractError, "contradicts"):
            census.analyze_query("q", runs, positives)

    def test_zero_observed_examples_decision(self):
        runs, _ = support_fixture()
        query, _ = census.analyze_query("q", runs, {"u1"})
        self.assertIn("park", census.summarize([query])["decision"])

    def test_rank_column_and_string_ids_are_authoritative(self):
        result = self.parse("001 Q0 01 1 0 fixture\n001 Q0 1 2 100 fixture\n")
        self.assertEqual(result, {"001": {"01": 1, "1": 2}})
        self.assertEqual(self.parse("001 0 01 1\n", True), {"001": {"01": 1}})

    def test_malformed_runs(self):
        cases = ["", "\n", "q Q0 d 1 0\n", "q Q0 d 0 0 tag\n", "q Q0 d 2 0 tag\n",
                 "q Q0 d 01 0 tag\n", "q Q0 d 1 nan tag\n", "q Q0 d 1 inf tag\n",
                 "q Q0 d 1 1e999 tag\n", "q Q0 d 1 nope tag\n", "q Q1 d 1 0 tag\n",
                 "q Q0 d\x00 1 0 tag\n", "q Q0 dé 1 0 tag\n", "q Q0 d 1 0 t\x00\n",
                 "q Q0 d 1 0 tag\nq Q0 d 2 0 tag\n",
                 "q Q0 d 1 0 tag\nq Q0 e 3 0 tag\n",
                 "q Q0 d 1 0 tag\nq Q0 e 1 0 tag\n"]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(census.ContractError):
                self.parse(text)

    def test_malformed_positive_only_qrels(self):
        for text in ["", "q 0 d 0\n", "q 0 d 2\n", "q 0 d -1\n", "q 0 d 1.0\n",
                     "q 1 d 1\n", "q 0 d 1 extra\n", "q 0 d 1\nq 0 d 1\n"]:
            with self.subTest(text=text), self.assertRaises(census.ContractError):
                self.parse(text, True)

    def valid_panel(self):
        runs = {name: {"q": ranks(["u"])} for name in census.LEXICAL}
        runs.update(S={"q": ranks(["s%d" % i for i in range(1000)])},
                    P={"q": ranks(["u"])}, B={"q": ranks(["u"] + ["s%d" % i for i in range(9)])})
        manifest = {"n_queries": 1, "qids": ["q"],
                    "lexical_depths": {name: {"q": 1} for name in census.LEXICAL},
                    "arm_depths": {name: {"q": len(runs[name]["q"])} for name in ("S", "P", "B")}}
        return runs, {"q": {"u": 1}}, manifest

    def test_cohort_depth_and_pool_contracts(self):
        runs, qrels, manifest = self.valid_panel()
        census.validate_panel(runs, qrels, manifest, expected_queries=1)
        with self.assertRaisesRegex(census.ContractError, "cohort"):
            census.validate_panel(runs, qrels, manifest)
        for name, bad_docs in [("bm25", ranks([str(i) for i in range(201)])),
                               ("S", ranks(["s"])), ("P", ranks([str(i) for i in range(1001)])),
                               ("B", ranks(["u"])), ("P", ranks(["missing"]))]:
            broken = copy.deepcopy(runs)
            broken[name]["q"] = bad_docs
            with self.subTest(name=name, depth=len(bad_docs)), self.assertRaises(census.ContractError):
                census.validate_panel(broken, qrels, manifest, 1)
        broken = copy.deepcopy(runs)
        broken["B"]["extra"] = broken["B"]["q"]
        with self.assertRaisesRegex(census.ContractError, "cohort"):
            census.validate_panel(broken, qrels, manifest, 1)

    def custody_fixture(self):
        for name, relative in census.INPUTS.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic bytes " + name)
        manifest = {"outputs": {name + ".trec": census.identity(self.root / census.INPUTS[name]) for name in census.RUNS}}
        for relative, content in [(census.MANIFEST, json.dumps(manifest)),
                                  (census.OFFICIAL, json.dumps({"qrels_sha256": census.identity(self.root / census.INPUTS["qrels"])["sha256"]})),
                                  (census.SOURCE, "synthetic source"), (census.PROTOCOL, "synthetic protocol")]:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        pinned = [census.MANIFEST, census.OFFICIAL] + list(census.INPUTS.values())
        blobs = "\n".join(census.identity(self.root / relative)["git-blob-sha1"] for relative in pinned)
        protocol_hash = census.identity(self.root / census.PROTOCOL)["sha256"]
        return blobs, protocol_hash

    def test_custody_rejects_changes_before_row_parser(self):
        blobs, protocol_hash = self.custody_fixture()
        with patch.object(census.subprocess, "run") as git, patch.object(census, "PROTOCOL_SHA256", protocol_hash):
            git.return_value.stdout = blobs
            identities, _ = census.verify_custody(self.root)
            self.assertEqual(len(identities), 12)
            path = self.root / census.INPUTS["S"]
            path.write_text("changed")
            with patch.object(census, "read_rows") as reader:
                with self.assertRaisesRegex(census.ContractError, "checkpoint identity"):
                    census.run_census(self.root / "out", self.root)
                reader.assert_not_called()
            self.assertFalse((self.root / "out/execution-start.json").exists())

    def test_receipt_precedes_any_rows_and_exclusive_output(self):
        blobs, protocol_hash = self.custody_fixture()
        output = self.root / "out"
        def stop_at_rows(*args, **kwargs):
            receipt = json.loads((output / "execution-start.json").read_text())
            self.assertEqual(set(receipt["inputs"]), set(census.INPUTS))
            self.assertEqual(receipt["phase"], "before_input_row_parsing")
            self.assertEqual(receipt["identities"][census.PROTOCOL]["sha256"], protocol_hash)
            raise census.ContractError("fixture stop before rows")
        with patch.object(census.subprocess, "run") as git, patch.object(census, "PROTOCOL_SHA256", protocol_hash), \
                patch.object(census, "read_rows", side_effect=stop_at_rows) as reader:
            git.return_value.stdout = blobs
            with self.assertRaisesRegex(census.ContractError, "fixture stop"):
                census.run_census(output, self.root)
            self.assertEqual(reader.call_count, 1)
            self.assertTrue((output / "failure.json").exists())
            with self.assertRaises(FileExistsError):
                census.run_census(output, self.root)
            self.assertEqual(reader.call_count, 1)

    def test_full_fixture_outputs_deterministic_and_hashed(self):
        runs, qrels, manifest = self.valid_panel()
        self.custody_fixture()
        for name in census.RUNS:
            (self.root / census.INPUTS[name]).write_text("".join(
                "%s Q0 %s %d 0 fixture\n" % (qid, docid, rank)
                for qid, docs in runs[name].items() for docid, rank in docs.items()))
        (self.root / census.INPUTS["qrels"]).write_text("q 0 u 1\n")
        identities = {path: census.identity(self.root / path)
                      for path in list(census.INPUTS.values()) + [census.PROTOCOL, census.SOURCE]}
        validator = census.validate_panel
        with patch.object(census, "verify_custody", return_value=(identities, manifest)), \
                patch.object(census, "validate_panel", side_effect=lambda r, q, m: validator(r, q, m, 1)):
            first = self.root / "first"
            second = self.root / "second"
            census.run_census(first, self.root)
            census.run_census(second, self.root)
        for name in ("perquery.json", "positive-support.json", "summary.json"):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
        completed = json.loads((first / "manifest.json").read_text())
        for name, expected in completed["outputs"].items():
            self.assertEqual(census.identity(first / name), expected)
        self.assertEqual(completed["status"], "completed")
        summary = json.loads((first / "summary.json").read_text())
        self.assertEqual(summary["positive_partition"]["U-only"], 1)
        self.assertEqual(summary["B_top10"]["S_only_entries"], 9)


if __name__ == "__main__":
    unittest.main()
