"""Synthetic-only input, ordering, denominator and five-arm transfer checks."""

import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle15_scifact_transfer as transfer


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.corpus = {
            "q1": ("signal", "first abstract"), "z": ("signal", "second abstract"),
            "a": ("signal", "third abstract"), "unretrieved": ("missing", "positive abstract"),
            "excluded_only": ("excluded", "should not enter statistics"),
        }
        self.queries = {"q1": ("", "signal"), "q2": ("", "signal"), "q0": ("", "signal"), "non_test": ("", "unused query")}
        self.qrels = {"q1": {"q1": 1, "unretrieved": 1, "z": 0}, "q2": {"a": 1}, "q0": {"excluded_only": 0}}
        self.paths = {"P": self.root / "P.jsonl", "S": self.root / "S.jsonl"}
        self.records = {
            "P": [self.record("q2", []), self.record("q1", ["z", "q1"]), self.record("q0", ["excluded_only"])],
            "S": [self.record("q0", []), self.record("q1", ["a", "q1"]), self.record("q2", [])],
        }
        self.save()

    def record(self, qid, docs):
        return {"query": {"qid": qid, "text": self.queries[qid][1]},
                "candidates": [{"docid": docid, "score": 100 - rank,
                                "doc": {"_id": docid, "title": self.corpus[docid][0], "text": self.corpus[docid][1], "metadata": {}}}
                               for rank, docid in enumerate(docs)]}

    def save(self):
        for arm in ("P", "S"):
            self.paths[arm].write_text("".join(json.dumps(row) + "\n" for row in self.records[arm]), encoding="utf-8")

    def validated(self):
        return transfer.validate_components(self.corpus, self.queries, self.qrels, self.paths["P"], self.paths["S"])

    def receipt(self, **changes):
        receipt = {"status": "passed", "evaluator_revision": transfer.EVALUATOR_REVISION,
                   "local_metric_sha256": transfer.FROZEN_SHA256["evaluation/trec_eval_harness.py"],
                   "tolerance": {"official_absolute": 0.0000500001, "local_absolute": 1e-12, "relative": 0.0}}
        receipt.update(changes)
        path = self.root / "gate.json"
        path.write_text(json.dumps(receipt))
        return path

    def preflight(self):
        hashes = dict(transfer.FROZEN_SHA256)
        for relative in ("evaluation/cycle15_scifact_transfer.py", "evaluation/tests/test_cycle15_scifact_transfer.py"):
            hashes[relative] = transfer.file_identity(transfer.ROOT / relative)["sha256"]
        path = self.root / "preflight.json"
        path.write_text(json.dumps({"status": "passed", "source_sha256": hashes}))
        return path

    def test_official_vector_preserves_empty_sources_and_all_qrels(self):
        validated = self.validated()
        self.assertEqual(validated.qids, ("q1", "q2"))
        self.assertEqual(validated.manifest["official_test_qids"], ["q0", "q1", "q2"])
        self.assertEqual(validated.manifest["excluded_zero_idcg_qids"], ["q0"])
        self.assertEqual(validated.sources["P"]["q2"], ())
        self.assertEqual([doc for doc, _ in validated.sources["P"]["q1"]], ["z", "q1"])
        self.assertIn("unretrieved", validated.qrels["q1"])
        self.assertEqual(validated.stats["N"], 2)
        self.assertNotIn("excluded", validated.stats["df"])
        self.assertNotIn("third", validated.stats["df"])
        self.assertEqual(validated.manifest["P_candidate_union_over_corpus"], 2 / 5)

    def test_shared_doc_text_is_one_canonical_joined_object(self):
        self.records["P"][0] = self.record("q2", ["q1"])
        self.save()
        validated = self.validated()
        first = dict(validated.data["q1"])["q1"]
        second = dict(validated.data["q2"])["q1"]
        self.assertEqual(first, "signal\nfirst abstract")
        self.assertIs(first, second)
        self.assertEqual(validated.stats["N"], 2)

    def test_missing_positive_or_excluded_query_never_intersects(self):
        original = copy.deepcopy(self.records)
        for qid in ("q0", "q1", "q2"):
            with self.subTest(qid=qid):
                self.records = copy.deepcopy(original)
                self.records["S"] = [row for row in self.records["S"] if row["query"]["qid"] != qid]
                self.save()
                with patch.object(transfer.lexical, "build_collection_stats") as stats:
                    with self.assertRaisesRegex(transfer.ContractError, "coverage mismatch"):
                        self.validated()
                    stats.assert_not_called()

    def test_complete_binary_domain_checked_before_exclusion(self):
        for bad in (2, -1, 0.0, True):
            with self.subTest(grade=bad):
                self.qrels["q0"]["excluded_only"] = bad
                with patch.object(transfer, "read_cache") as reader:
                    with self.assertRaisesRegex(transfer.ContractError, "integer binary"):
                        self.validated()
                    reader.assert_not_called()

    def test_qrels_tsv_rejects_duplicates_noninteger_and_wrong_header(self):
        path = self.root / "qrels.tsv"
        for text in ("query-id\tcorpus-id\tscore\nq1\ta\t1\nq1\ta\t0\n",
                     "query-id\tcorpus-id\tscore\nq1\ta\t1.0\n",
                     "query-id\tcorpus-id\tscore\nq1\ta\t2\n",
                     "query_id\tcorpus_id\tscore\nq1\ta\t1\n"):
            with self.subTest(text=text):
                path.write_text(text)
                with self.assertRaises(transfer.ContractError):
                    transfer.read_binary_qrels(path)
        path.write_text("query-id\tcorpus-id\tscore\nq1\tq1\t1\nq1\ta\t0\n")
        self.assertEqual(transfer.read_binary_qrels(path), {"q1": {"q1": 1, "a": 0}})

    def test_unsupported_schema_text_identity_and_scores_fail_before_stats(self):
        original = copy.deepcopy(self.records)
        mutations = {
            "duplicate_query": lambda row: self.records["S"].append(copy.deepcopy(row)),
            "duplicate_document": lambda row: row["candidates"].append(copy.deepcopy(row["candidates"][0])),
            "query_text": lambda row: row["query"].update(text="normalized changed text"),
            "title": lambda row: row["candidates"][0]["doc"].update(title="changed"),
            "body": lambda row: row["candidates"][0]["doc"].update(text="changed"),
            "missing_title": lambda row: row["candidates"][0]["doc"].pop("title"),
            "wrong_doc_id": lambda row: row["candidates"][0]["doc"].update(_id="z"),
            "unknown_doc": lambda row: row["candidates"][0].update(docid="not-in-corpus"),
            "numeric_id": lambda row: row["candidates"][0].update(docid=12),
            "increasing_score": lambda row: row["candidates"][1].update(score=101),
            "nonfinite": lambda row: row["candidates"][0].update(score=float("nan")),
            "boolean_score": lambda row: row["candidates"][0].update(score=True),
            "string_score": lambda row: row["candidates"][0].update(score="100"),
            "unknown_schema": lambda row: row["candidates"][0].update(rank=1),
            "too_deep": lambda row: row.update(candidates=row["candidates"] * 501),
        }
        for name, mutate in mutations.items():
            with self.subTest(failure=name):
                self.records = copy.deepcopy(original)
                mutate(self.records["S"][1])
                self.save()
                with patch.object(transfer.lexical, "build_collection_stats") as stats, patch.object(transfer.lexical, "generate_lexical_run") as score:
                    with self.assertRaises(transfer.ContractError):
                        self.validated()
                    stats.assert_not_called()
                    score.assert_not_called()

    def test_duplicate_json_fields_and_blank_rows_are_rejected(self):
        original = self.paths["S"].read_text()
        for broken in (original + "\n", original.replace('"qid": "q1"', '"qid": "q1", "qid": "q1"')):
            with self.subTest(broken=broken[:20]):
                self.paths["S"].write_text(broken)
                with self.assertRaises(transfer.ContractError):
                    self.validated()

    def test_zero_token_query_stops_before_scoring(self):
        self.queries["q2"] = ("", "the a !")
        with patch.object(transfer.lexical, "generate_lexical_run") as score:
            with self.assertRaisesRegex(transfer.ContractError, "tokenized-empty"):
                self.validated()
            score.assert_not_called()

    def test_all_input_identities_precede_parquet_qrels_or_cache_parse(self):
        # A tiny plan fixture exercises all five roles without any real inputs.
        paths, plan = {}, {"inputs": [], "raw_input_byte_cap": 1000}
        for role in transfer.ROLES:
            path = self.root / role
            path.write_text(role)
            paths[role] = path
            identity = transfer.file_identity(path)
            plan["inputs"].append({"role": role, "expected_bytes": identity["bytes"],
                                   "expected_digest": identity["sha256"], "identity_algorithm": "sha256",
                                   "revision": "synthetic", "path": role})
        for role in transfer.ROLES:
            with self.subTest(role=role):
                original = paths[role].read_bytes()
                paths[role].write_bytes(original + b"x")
                try:
                    with patch.object(transfer, "verify_frozen_code", return_value={}), \
                            patch.object(transfer, "read_json", return_value=plan), \
                            patch.object(transfer, "pinned_decoder") as decoder, \
                            patch.object(transfer, "read_binary_qrels") as qrels, \
                            patch.object(transfer, "read_cache") as cache:
                        with self.assertRaisesRegex(transfer.ContractError, "identity mismatch"):
                            transfer.load_validate(paths)
                        decoder.assert_not_called()
                        qrels.assert_not_called()
                        cache.assert_not_called()
                finally:
                    paths[role].write_bytes(original)

    def test_raw_lexical_scores_preserve_near_ties_and_exact_tie_source_order(self):
        self.records["P"][1] = self.record("q1", ["z", "a", "q1"])
        self.save()
        validated = self.validated()

        def scorer(query, tokens, stats):
            return 0.1234564002 if "third" in tokens else 0.1234564001

        with patch.dict(transfer.lexical.LEXICAL_RANKERS, {name: scorer for name in transfer.LEXICAL_NAMES}):
            runs = transfer.lexical_rankings(validated)
        for name in transfer.LEXICAL_NAMES:
            self.assertEqual(runs[name]["q1"], [("a", 0.1234564002), ("z", 0.1234564001), ("q1", 0.1234564001)])
            self.assertEqual(runs[name]["q2"], [])

    def test_lexical_cap_applied_after_scoring_all_P_candidates(self):
        for number in range(205):
            self.corpus["doc%d" % number] = ("same", "text")
        docs = ["doc%d" % number for number in range(205)]
        self.records["P"][1] = self.record("q1", docs)
        self.save()
        validated = self.validated()
        calls = []

        def scorer(*args):
            calls.append(1)
            return 1.0

        with patch.dict(transfer.lexical.LEXICAL_RANKERS, {name: scorer for name in transfer.LEXICAL_NAMES}):
            runs = transfer.lexical_rankings(validated)
        self.assertEqual(len(calls), 4 * 205)
        self.assertEqual([doc for doc, _ in runs["bm25"]["q1"]], docs[:200])

    def test_metric_denominators_keep_unknown_ranks_unretrieved_positives_and_empty_queries(self):
        validated = self.validated()
        arms = {name: {"q1": [("a", 1.0), ("q1", 0.5)], "q2": []} for name in transfer.ARMS}
        arms["B"]["q1"] = [("q1", 1.0), ("z", 0.5)]
        rows, summary = transfer.analyze(validated, arms)
        ideal = 1 + 1 / math.log2(3)
        self.assertAlmostEqual(rows["q1"]["ndcg10"]["A"], (1 / math.log2(3)) / ideal)
        self.assertAlmostEqual(rows["q1"]["ndcg10"]["B"], 1 / ideal)
        self.assertAlmostEqual(summary["means_ndcg10"]["B"], 1 / ideal / 2)
        self.assertEqual(rows["q2"]["top10_without_explicit_qrel"]["B"], {"count": 0, "returned_top10": 0})
        self.assertEqual(rows["q1"]["top10_without_explicit_qrel"]["A"], {"count": 1, "returned_top10": 2})
        self.assertEqual(summary["contrasts_ndcg10"]["B-A"]["positive"], 1)
        self.assertEqual(summary["contrasts_ndcg10"]["B-A"]["zero"], 1)
        self.assertEqual(set(summary["contrasts_ndcg10"]), set(transfer.CONTRASTS))

    def test_rbp_truncation_uses_one_minus_p_without_mass_normalization(self):
        docs = ["d%d" % rank for rank in range(1, 12)]
        p = 4 / 5
        for rank in (1, 2, 10, 11):
            with self.subTest(rank=rank):
                expected = (1 - p) * p ** (rank - 1) if rank <= 10 else 0
                self.assertEqual(transfer.rbp10(docs, {docs[rank - 1]: 1}), expected)
        self.assertEqual(transfer.rbp10([], {"positive": 1}), 0)
        self.assertAlmostEqual(transfer.rbp10(docs, dict.fromkeys(docs, 1)), 1 - p ** 10)

    def test_fusion_ties_use_string_ids_but_source_ties_preserve_order(self):
        self.records["P"][1]["candidates"][1]["score"] = 100
        self.save()
        validated = self.validated()
        self.assertEqual([doc for doc, _ in validated.sources["P"]["q1"]], ["z", "q1"])
        self.assertEqual([doc for doc, _ in transfer.fused_scores([["z"], ["a"]])], ["a", "z"])

    def test_metric_gate_failure_prevents_any_lexical_scoring_or_output(self):
        validated = self.validated()
        output = self.root / "run"
        for changes in ({"status": "failed"}, {"evaluator_revision": "different"}, {"local_metric_sha256": "different"}, {"tolerance": {}}):
            with self.subTest(changes=changes), patch.object(transfer, "lexical_rankings") as scoring:
                with self.assertRaises(transfer.ContractError):
                    transfer.execute(validated, output, self.receipt(**changes))
                scoring.assert_not_called()
                self.assertFalse(output.exists())

    def test_five_arm_execution_outputs_numeric_only_fresh_immutable_artifacts(self):
        validated = self.validated()
        output = self.root / "run"
        summary = transfer.execute(validated, output, self.receipt(), self.preflight())
        self.assertEqual(set(summary["means_ndcg10"]), set(transfer.ARMS))
        for name in (*transfer.ARMS, *transfer.LEXICAL_NAMES):
            self.assertTrue((output / (name + ".trec")).exists())
        self.assertEqual((output / "P.trec").read_text(), "q1 Q0 z 1 100.0 P\nq1 Q0 q1 2 99.0 P\n")
        manifest = transfer.read_json(output / "manifest.json")
        self.assertEqual(manifest["status"], "completed")
        self.assertTrue(manifest["effectiveness_completed"])
        self.assertEqual(manifest["arm_depths"]["P"]["q2"], 0)
        for path in output.iterdir():
            self.assertNotIn("first abstract", path.read_text())
        with patch.object(transfer, "lexical_rankings") as scoring:
            with self.assertRaises(FileExistsError):
                transfer.execute(validated, output, self.receipt(), self.preflight())
            scoring.assert_not_called()

    def test_preflight_source_change_prevents_any_scoring(self):
        validated = self.validated()
        preflight = self.preflight()
        receipt = transfer.read_json(preflight)
        receipt["source_sha256"]["evaluation/cycle15_scifact_transfer.py"] = "wrong"
        preflight.write_text(json.dumps(receipt))
        with patch.object(transfer, "lexical_rankings") as scoring:
            with self.assertRaisesRegex(transfer.ContractError, "preflight identity mismatch"):
                transfer.execute(validated, self.root / "run", self.receipt(), preflight)
            scoring.assert_not_called()
        self.assertFalse((self.root / "run").exists())

    def test_failure_after_metric_start_preserves_numeric_rankings_and_partial_outcomes(self):
        validated = self.validated()
        output = self.root / "failed-run"
        original = transfer.ndcg_at_k
        calls = []

        def fails_second_query(*args):
            calls.append(1)
            if len(calls) == 6:
                raise transfer.ContractError("synthetic failure after first query")
            return original(*args)

        with patch.object(transfer, "ndcg_at_k", side_effect=fails_second_query):
            with self.assertRaisesRegex(transfer.ContractError, "after first query"):
                transfer.execute(validated, output, self.receipt(), self.preflight())
        failure = transfer.read_json(output / "failure.json")
        self.assertEqual(failure["phase"], "effectiveness")
        self.assertTrue(failure["effectiveness_started"])
        self.assertFalse(failure["effectiveness_completed"])
        for arm in transfer.ARMS:
            self.assertTrue((output / (arm + ".trec")).exists())
        partial = [json.loads(line) for line in (output / "per-query.jsonl").read_text().splitlines()]
        self.assertEqual([row["qid"] for row in partial], ["q1"])
        self.assertFalse((output / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
