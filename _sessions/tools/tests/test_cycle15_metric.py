"""Synthetic fault injection only: no official evaluator invocation or real data."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cycle15_metric_test", TOOLS / "check_cycle15_metric.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def simulated_official(fixtures):
    """Model the official four-decimal text boundary, not its metric algorithm."""
    rows = [f"ndcg_cut_10\t{f['qid']}\t{f['expected']:.4f}" for f in fixtures]
    rows.append(f"ndcg_cut_10\tall\t{math.fsum(f['expected'] for f in fixtures) / len(fixtures):.4f}")
    return "\n".join(rows) + "\n"


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = gate.fixed_fixtures()
        self.by_id = {f["qid"]: f for f in self.fixtures}
        self.qids = sorted(self.by_id)

    def test_local_subject_matches_hand_positions_including_unretrieved_positives(self):
        actual = gate.compare_scores(self.fixtures, gate.parse_official(simulated_official(self.fixtures), self.qids))
        self.assertEqual(actual["query_count"], 11)
        self.assertEqual(actual["aggregate_denominator"], 11)
        self.assertEqual(actual["empty_query_ids"], ["empty"])
        self.assertEqual(actual["per_fixture"]["rank1"]["local"], 1.0)
        self.assertAlmostEqual(actual["per_fixture"]["rank2"]["local"], 1 / math.log2(3))
        self.assertAlmostEqual(actual["per_fixture"]["rank10"]["local"], 1 / math.log2(11))
        self.assertEqual(actual["per_fixture"]["rank11"]["local"], 0.0)
        self.assertLess(actual["per_fixture"]["multiple"]["local"],
                        (1 / math.log2(3) + 1 / math.log2(5)) / (1 + 1 / math.log2(3)))
        self.assertEqual(actual["per_fixture"]["unjudged"]["local"], 0.5)

    def test_export_preserves_tied_original_order_and_query_doc_namespace(self):
        with tempfile.TemporaryDirectory() as temp:
            qrels, run = Path(temp) / "qrels", Path(temp) / "run"
            gate.export_fixtures(self.fixtures, qrels, run)
            rows = [row.split() for row in run.read_text().splitlines()]
            tied = [row for row in rows if row[0] == "tied_original"]
            self.assertEqual(self.by_id["tied_original"]["original_scores"], [7.0, 7.0])
            self.assertEqual([row[2] for row in tied], ["a_positive", "z_zero"])
            self.assertEqual([row[4] for row in tied], ["-1", "-2"])
            self.assertIn(["00101", "Q0", "00101", "1", "-1", "cycle15_fixture"], rows)
            self.assertFalse(any(row[0] == "empty" for row in rows))
            self.assertIn("empty 0 unretrieved 1\n", qrels.read_text())
            for qid in self.qids:
                group = [row for row in rows if row[0] == qid]
                self.assertEqual([int(row[3]) for row in group], list(range(1, len(group) + 1)))
                self.assertEqual([int(row[4]) for row in group], list(range(-1, -len(group) - 1, -1)))

    def test_nonbinary_and_coerced_grades_fail(self):
        for grade in (-1, 2, True, 1.0, "1"):
            with self.subTest(grade=grade):
                fixtures = deepcopy(self.fixtures)
                fixtures[0]["qrels"]["00101"] = grade
                with self.assertRaisesRegex(gate.MetricGateError, "binary integers"):
                    gate.validate_fixtures(fixtures)

    def test_duplicate_docs_and_queries_fail(self):
        fixtures = deepcopy(self.fixtures)
        fixtures[0]["ranking"] = ["00101", "00101"]
        with self.assertRaisesRegex(gate.MetricGateError, "duplicate fixture document"):
            gate.validate_fixtures(fixtures)
        with self.assertRaisesRegex(gate.MetricGateError, "sorted and unique"):
            gate.validate_fixtures(self.fixtures + [self.fixtures[-1]])

    def test_wrong_local_algorithm_or_official_value_fails(self):
        official = gate.parse_official(simulated_official(self.fixtures), self.qids)
        with self.assertRaisesRegex(gate.MetricGateError, "local metric mismatch"):
            gate.compare_scores(self.fixtures, official, local_metric=lambda ranking, qrels, k: 0.0)
        official["rank2"] += 0.001
        with self.assertRaisesRegex(gate.MetricGateError, "official metric mismatch for rank2"):
            gate.compare_scores(self.fixtures, official)

    def test_common_metric_semantic_errors_are_distinguished(self):
        official = gate.parse_official(simulated_official(self.fixtures), self.qids)
        incorrect_metrics = {
            "compress unjudged": lambda ranking, qrels, k: gate.ndcg_at_k(
                [doc for doc in ranking if doc in qrels], qrels, k),
            "IDCG uses retrieved positives only": lambda ranking, qrels, k: gate.ndcg_at_k(
                ranking, {doc: grade for doc, grade in qrels.items() if doc in ranking}, k),
            "remove identical query/document ID": lambda ranking, qrels, k: gate.ndcg_at_k(
                [doc for doc in ranking if doc != "00101"], qrels, k),
            "off by one cutoff": lambda ranking, qrels, k: gate.ndcg_at_k(ranking, qrels, k + 1),
        }
        for description, metric in incorrect_metrics.items():
            with self.subTest(description=description):
                with self.assertRaisesRegex(gate.MetricGateError, "local metric mismatch"):
                    gate.compare_scores(self.fixtures, official, local_metric=metric)

    def test_dropping_empty_query_from_denominator_fails(self):
        official = gate.parse_official(simulated_official(self.fixtures), self.qids)
        official["all"] = math.fsum(f["expected"] for f in self.fixtures) / (len(self.fixtures) - 1)
        with self.assertRaisesRegex(gate.MetricGateError, "complete qrel query denominator"):
            gate.compare_scores(self.fixtures, official)

    def test_parser_rejects_missing_extra_duplicate_and_malformed_values(self):
        output = simulated_official(self.fixtures)
        empty_row = "ndcg_cut_10\tempty\t0.0000\n"
        mutations = {
            "empty omitted": output.replace(empty_row, ""),
            "aggregate omitted": "\n".join(output.splitlines()[:-1]),
            "unexpected query": output + "ndcg_cut_10 unknown 0.0\n",
            "duplicate query": output + empty_row,
            "duplicate aggregate": output + output.splitlines()[-1] + "\n",
            "wrong metric": output.replace("ndcg_cut_10", "ndcg_cut_20", 1),
            "extra column": output.replace(empty_row, "ndcg_cut_10 empty 0.0 extra\n"),
        }
        for token in ("nan", "inf", "-inf", "-0.1", "1.1", "not-a-number"):
            mutations[token] = output.replace(empty_row, "ndcg_cut_10 empty " + token + "\n")
        for description, bad_output in mutations.items():
            with self.subTest(description=description):
                with self.assertRaises(gate.MetricGateError):
                    gate.parse_official(bad_output, self.qids)


class BuildAndRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        (self.source / "m_ndcg_cut.c").write_text("synthetic source; never compiled or executed\n")
        self.source_hash = hashlib.sha256((self.source / "m_ndcg_cut.c").read_bytes()).hexdigest()
        # This executable is only an identity fixture. All subprocess calls are mocked.
        self.binary = self.source / "trec_eval"
        self.binary.write_text("synthetic executable; never executed\n")
        self.binary.chmod(0o700)
        self.receipt_path = self.base / "build.json"
        self.receipt = {"status": "passed", "evaluator_revision": gate.REVISION,
                        "source_archive_sha256": "a" * 64, "source_directory": str(self.source),
                        "binary_path": str(self.binary), "binary_sha256": gate.sha256(self.binary),
                        "metric_source_sha256": self.source_hash,
                        "local_metric_sha256": gate.LOCAL_METRIC_SHA256,
                        "build_command": ["make", "-C", str(self.source)], "build_exit_code": 0}
        self.save_receipt()
        patcher = mock.patch.object(gate, "METRIC_SOURCE_SHA256", self.source_hash)
        patcher.start()
        self.addCleanup(patcher.stop)

    def save_receipt(self):
        gate.write_json(self.receipt_path, self.receipt)

    def test_build_identity_accepts_recorded_source_and_binary(self):
        result = gate.validate_build_receipt(self.receipt_path, self.binary)
        self.assertEqual(result["binary_sha256"], gate.sha256(self.binary))

    def test_build_identity_rejects_wrong_revision_digest_status_and_command(self):
        mutations = {"evaluator_revision": "0" * 40, "binary_sha256": "0" * 64,
                     "metric_source_sha256": "0" * 64, "local_metric_sha256": "0" * 64,
                     "build_exit_code": True, "status": "failed", "source_archive_sha256": "not-a-hash",
                     "build_command": ["make", "-C", str(self.base)]}
        original = deepcopy(self.receipt)
        for field, value in mutations.items():
            with self.subTest(field=field):
                self.receipt = {**original, field: value}
                self.save_receipt()
                with self.assertRaises(gate.MetricGateError):
                    gate.validate_build_receipt(self.receipt_path, self.binary)
        self.receipt = original
        del self.receipt["binary_sha256"]
        self.save_receipt()
        with self.assertRaisesRegex(gate.MetricGateError, "missing required keys"):
            gate.validate_build_receipt(self.receipt_path, self.binary)

    def test_build_identity_rejects_changed_source_bytes(self):
        (self.source / "m_ndcg_cut.c").write_text("changed after build\n")
        with self.assertRaisesRegex(gate.MetricGateError, "metric source hash mismatch"):
            gate.validate_build_receipt(self.receipt_path, self.binary)

    def test_freezes_protocol_before_one_invocation_and_records_complete_results(self):
        output = self.base / "gate"

        def fake_run(command, **kwargs):
            protocol = json.loads((output / "metric-protocol.json").read_text())
            self.assertEqual(protocol["status"], "frozen_before_evaluator_invocation")
            self.assertEqual(protocol["command"], command)
            self.assertEqual(command[1:5], ["-q", "-c", "-m", "ndcg_cut.10"])
            self.assertEqual(protocol["tolerance"], gate.TOLERANCE)
            self.assertEqual(protocol["query_denominator"], 11)
            self.assertEqual(kwargs["env"]["LC_ALL"], "C")
            self.assertEqual(kwargs["timeout"], 30)
            return subprocess.CompletedProcess(command, 0, simulated_official(gate.fixed_fixtures()), "")

        with mock.patch.object(gate.subprocess, "run", side_effect=fake_run) as invocation:
            result = gate.run_gate(self.binary, self.receipt_path, output)
        invocation.assert_called_once()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["aggregate_denominator"], 11)
        self.assertEqual(result, json.loads((output / "metric-gate.json").read_text()))
        self.assertFalse(result["real_collection_effectiveness"])
        with self.assertRaises(FileExistsError):
            gate.run_gate(self.binary, self.receipt_path, output)

    def test_failed_invocation_and_bad_output_preserve_failure_evidence(self):
        valid = simulated_official(gate.fixed_fixtures())
        failures = [(2, "", "bad command"), (0, valid, "unexpected warning"), (0, "", ""),
                    (0, valid.replace("ndcg_cut_10\trank1\t1.0000", "ndcg_cut_10\trank1\t0.0000"), "")]
        for index, (code, stdout, stderr) in enumerate(failures):
            with self.subTest(index=index):
                output = self.base / ("failure" + str(index))
                with mock.patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess([], code, stdout, stderr)):
                    with self.assertRaises(gate.MetricGateError):
                        gate.run_gate(self.binary, self.receipt_path, output)
                receipt = json.loads((output / "metric-gate.json").read_text())
                self.assertEqual(receipt["status"], "failed")
                self.assertIn("error", receipt)
                self.assertEqual((output / "trec_eval.stdout.txt").read_text(), stdout)
                self.assertEqual((output / "trec_eval.stderr.txt").read_text(), stderr)

    def test_bad_build_never_invokes_evaluator(self):
        self.receipt["evaluator_revision"] = "wrong"
        self.save_receipt()
        with mock.patch.object(gate.subprocess, "run") as invocation:
            with self.assertRaisesRegex(gate.MetricGateError, "wrong evaluator revision"):
                gate.run_gate(self.binary, self.receipt_path, self.base / "bad-build")
        invocation.assert_not_called()

    def test_timeout_retains_partial_output_without_retry(self):
        output = self.base / "timeout"
        timeout = subprocess.TimeoutExpired([str(self.binary)], 30, output=b"partial stdout\n", stderr=b"partial stderr\n")
        with mock.patch.object(gate.subprocess, "run", side_effect=timeout) as invocation:
            with self.assertRaises(gate.MetricGateError):
                gate.run_gate(self.binary, self.receipt_path, output)
        invocation.assert_called_once()
        receipt = json.loads((output / "metric-gate.json").read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertTrue(receipt["timed_out"])
        self.assertEqual((output / "trec_eval.stdout.txt").read_bytes(), b"partial stdout\n")
        self.assertEqual((output / "trec_eval.stderr.txt").read_bytes(), b"partial stderr\n")


if __name__ == "__main__":
    unittest.main()
