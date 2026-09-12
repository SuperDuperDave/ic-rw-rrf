#!/usr/bin/env python3
"""Cross-check fixed binary fixtures against a separately built pinned trec_eval.

No downloads, evaluator builds, real collection data, or general harness driver.
The output directory must be fresh; failed gates retain their available evidence.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluation"))
from trec_eval_harness import ndcg_at_k  # noqa: E402

REVISION = "ba38899cbd4de0fb699b47f39b64ef1c107e4a5c"
METRIC_SOURCE_SHA256 = "d5a369ec235a35726b4980b10ad161a1174dfe64aaf5159b1234e99fbdb92ed9"
LOCAL_METRIC_SHA256 = "0b437034007e0e6ccfd8979c3eee6603374afb2234b895bccc47546347c9b85b"
LOCAL_METRIC = ROOT / "evaluation/trec_eval_harness.py"
TOLERANCE = {"official_absolute": 0.0000500001, "local_absolute": 1e-12, "relative": 0.0}
TIMEOUT_SECONDS = 30
MEASURE = "ndcg_cut_10"


class MetricGateError(ValueError):
    """A failed identity, fixture, evaluator, or numerical gate."""


def require(condition, message):
    if not condition:
        raise MetricGateError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def root_path(value):
    path = Path(value)
    return (ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def fixed_fixtures():
    """Hand-selected relevant positions; expectations do not read the rankings.

    d(r)=1/log2(r+1). All qrel queries have at least one positive, matching
    the prospective retained cohort. Original scores are retained as evidence
    but never used to reconstruct or export the already chosen ranking.
    """
    d = lambda rank: 1.0 / math.log2(rank + 1)
    fixtures = []

    def add(qid, ranking, qrels, expected, formula, original_scores=None):
        fixtures.append({"qid": qid, "ranking": ranking, "qrels": qrels,
                         "expected": expected, "expected_formula": formula,
                         "original_scores": original_scores if original_scores is not None
                         else [float(100 - rank) for rank in range(len(ranking))]})

    for rank in (1, 2, 10, 11):
        add("rank" + str(rank), ["u" + str(i) for i in range(1, rank)] + ["positive"],
            {"positive": 1}, d(rank) if rank <= 10 else 0.0,
            "d(" + str(rank) + ")" if rank <= 10 else "0 (positive below cutoff)")
    add("multiple", ["unjudged", "p1", "zero", "p2"],
        {"p1": 1, "p2": 1, "unretrieved": 1, "zero": 0},
        (d(2) + d(4)) / (d(1) + d(2) + d(3)),
        "(d(2)+d(4))/(d(1)+d(2)+d(3)); third positive unretrieved")
    add("ideal_cutoff", ["p1"] + ["u" + str(i) for i in range(2, 10)] + ["p2"],
        {"p" + str(i): 1 for i in range(1, 13)},
        (d(1) + d(10)) / math.fsum(d(i) for i in range(1, 11)),
        "(d(1)+d(10))/sum(d(r),r=1..10); twelve qrel positives")
    add("unjudged", ["unjudged", "zero", "positive"], {"zero": 0, "positive": 1},
        d(3), "d(3); unjudged and explicit zero both retain rank positions")
    add("short_miss", ["unjudged", "zero"], {"zero": 0, "unretrieved": 1},
        0.0, "0 (short ranking without a positive)")
    add("empty", [], {"unretrieved": 1}, 0.0, "0 (empty ranking; included in denominator)")
    add("tied_original", ["a_positive", "z_zero"], {"a_positive": 1, "z_zero": 0},
        1.0, "d(1); preserve chosen a-before-z order despite tied original scores", [7.0, 7.0])
    add("00101", ["00101", "other"], {"00101": 1},
        1.0, "d(1); identical query/document strings are separate namespaces")
    return sorted(fixtures, key=lambda fixture: fixture["qid"])


def validate_fixtures(fixtures):
    qids = [fixture["qid"] for fixture in fixtures]
    require(bool(qids) and qids == sorted(set(qids)), "fixture query vector must be sorted and unique")
    for fixture in fixtures:
        qid, ranking, qrels = fixture["qid"], fixture["ranking"], fixture["qrels"]
        for value in [qid] + list(ranking) + list(qrels):
            require(isinstance(value, str) and value and not any(c.isspace() for c in value),
                    "fixture IDs must be nonempty string tokens")
        require(qid != "all", "fixture query ID 'all' is reserved by evaluator output")
        require(len(ranking) == len(set(ranking)), "duplicate fixture document ID")
        require(all(type(grade) is int and grade in (0, 1) for grade in qrels.values()),
                "fixture grades must be binary integers")
        require(any(grade == 1 for grade in qrels.values()), "fixture query has zero IDCG")
        scores = fixture["original_scores"]
        require(len(scores) == len(ranking) and all(math.isfinite(score) for score in scores),
                "invalid fixture original scores")
        require(math.isfinite(fixture["expected"]) and 0 <= fixture["expected"] <= 1,
                "invalid hand expectation")


def export_fixtures(fixtures, qrels_path, run_path):
    validate_fixtures(fixtures)
    qrel_rows, run_rows = [], []
    for fixture in fixtures:
        qid = fixture["qid"]
        qrel_rows.extend(f"{qid} 0 {docid} {grade}\n" for docid, grade in sorted(fixture["qrels"].items()))
        run_rows.extend(f"{qid} Q0 {docid} {rank} {-rank} cycle15_fixture\n"
                        for rank, docid in enumerate(fixture["ranking"], 1))
    Path(qrels_path).write_text("".join(qrel_rows))
    Path(run_path).write_text("".join(run_rows))


def validate_build_receipt(receipt_path, executable):
    receipt = json.loads(Path(receipt_path).read_text())
    require(isinstance(receipt, dict), "build receipt must be an object")
    required = {"status", "evaluator_revision", "source_archive_sha256", "source_directory",
                "binary_path", "binary_sha256", "metric_source_sha256", "local_metric_sha256",
                "build_command", "build_exit_code"}
    require(required <= receipt.keys(), "build receipt missing required keys: " + str(sorted(required - receipt.keys())))
    require(receipt["status"] == "passed" and type(receipt["build_exit_code"]) is int
            and receipt["build_exit_code"] == 0, "build receipt does not record a successful build")
    require(receipt["evaluator_revision"] == REVISION, "wrong evaluator revision")
    require(isinstance(receipt["source_archive_sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", receipt["source_archive_sha256"]), "invalid archive digest")
    executable = Path(executable).resolve()
    source = root_path(receipt["source_directory"])
    require(root_path(receipt["binary_path"]) == executable, "build receipt binary path mismatch")
    require(executable.is_file() and os.access(executable, os.X_OK), "evaluator is not an executable file")
    require(receipt["binary_sha256"] == sha256(executable), "evaluator binary hash mismatch")
    require(receipt["metric_source_sha256"] == METRIC_SOURCE_SHA256
            and sha256(source / "m_ndcg_cut.c") == METRIC_SOURCE_SHA256, "pinned evaluator metric source hash mismatch")
    require(receipt["local_metric_sha256"] == LOCAL_METRIC_SHA256
            and sha256(LOCAL_METRIC) == LOCAL_METRIC_SHA256, "pinned local metric hash mismatch")
    command = receipt["build_command"]
    require(isinstance(command, list) and len(command) == 3 and command[:2] == ["make", "-C"]
            and root_path(command[2]) == source, "unexpected evaluator build command")
    return receipt


def parse_official(text, expected_qids):
    """Require precisely one finite nDCG value per frozen qid and one aggregate."""
    parsed = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        require(len(fields) == 3 and fields[0] == MEASURE,
                f"unexpected evaluator output at line {line_number}")
        _, qid, raw_value = fields
        require(qid not in parsed, "duplicate evaluator query key: " + qid)
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise MetricGateError("invalid evaluator numeric value: " + raw_value) from exc
        require(math.isfinite(value) and 0 <= value <= 1, "invalid evaluator nDCG value: " + raw_value)
        parsed[qid] = value
    expected_keys = set(expected_qids) | {"all"}
    require(set(parsed) == expected_keys,
            f"evaluator query keys mismatch: missing={sorted(expected_keys - parsed.keys())}; "
            f"extra={sorted(parsed.keys() - expected_keys)}")
    return parsed


def compare_scores(fixtures, official, local_metric=ndcg_at_k):
    validate_fixtures(fixtures)
    qids = [fixture["qid"] for fixture in fixtures]
    require(set(official) == set(qids) | {"all"}, "comparison query keys mismatch")
    per_fixture = {}
    for fixture in fixtures:
        qid, expected = fixture["qid"], fixture["expected"]
        local = local_metric(fixture["ranking"], fixture["qrels"], 10)
        require(math.isfinite(local) and abs(local - expected) <= TOLERANCE["local_absolute"],
                f"local metric mismatch for {qid}: {local} versus hand expectation {expected}")
        require(math.isfinite(official[qid]) and abs(official[qid] - expected) <= TOLERANCE["official_absolute"],
                f"official metric mismatch for {qid}: {official[qid]} versus hand expectation {expected}")
        per_fixture[qid] = {"independent_formula": expected, "local": local, "official": official[qid],
                            "expected_formula": fixture["expected_formula"],
                            "official_absolute_error": abs(official[qid] - expected),
                            "local_absolute_error": abs(local - expected)}
    expected_mean = math.fsum(fixture["expected"] for fixture in fixtures) / len(qids)
    local_mean = math.fsum(value["local"] for value in per_fixture.values()) / len(qids)
    require(math.isfinite(official["all"])
            and abs(official["all"] - expected_mean) <= TOLERANCE["official_absolute"],
            "official aggregate mismatch against complete qrel query denominator")
    return {"query_vector": qids, "query_count": len(qids), "aggregate_denominator": len(qids),
            "empty_query_ids": [fixture["qid"] for fixture in fixtures if not fixture["ranking"]],
            "per_fixture": per_fixture,
            "aggregate": {"independent_formula": expected_mean, "local": local_mean, "official": official["all"],
                          "official_absolute_error": abs(official["all"] - expected_mean)},
            "max_official_absolute_error": max(value["official_absolute_error"] for value in per_fixture.values()),
            "max_local_absolute_error": max(value["local_absolute_error"] for value in per_fixture.values())}


def run_gate(executable, build_receipt_path, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    evidence = {"status": "failed", "evaluator_revision": REVISION,
                "local_metric_sha256": LOCAL_METRIC_SHA256, "tolerance": TOLERANCE,
                "metric": "binary nDCG@10", "real_collection_effectiveness": False}
    try:
        executable, build_receipt_path = Path(executable).resolve(), Path(build_receipt_path).resolve()
        build = validate_build_receipt(build_receipt_path, executable)
        evidence.update({"binary_sha256": sha256(executable), "build_receipt_sha256": sha256(build_receipt_path),
                         "source_archive_sha256": build["source_archive_sha256"], "build_command": build["build_command"],
                         "gate_code_sha256": sha256(__file__)})
        fixtures = fixed_fixtures()
        qrels_path, run_path = output / "fixtures.qrels", output / "fixtures.run"
        export_fixtures(fixtures, qrels_path, run_path)
        command = [str(executable), "-q", "-c", "-m", "ndcg_cut.10", str(qrels_path), str(run_path)]
        protocol = {**evidence, "status": "frozen_before_evaluator_invocation", "command": command,
                    "hypothesis": "The pinned local metric agrees with hand binary expectations and official trec_eval.",
                    "distinguishing_prediction": "Every per-query value and full-cohort mean meets the frozen tolerances.",
                    "baseline": "Hand expectations at fixed relevant ranks using d(r)=1/log2(r+1).",
                    "primary_metric": "binary nDCG@10 on eleven synthetic qrel queries, including one empty ranking",
                    "stopping_rule": "One official invocation; any identity, key, exit, or numeric mismatch fails the gate.",
                    "rng_used": False, "query_vector": [fixture["qid"] for fixture in fixtures],
                    "query_denominator": len(fixtures), "fixtures": fixtures,
                    "rank_export": "Supplied ranking order with one-based rank and strictly decreasing score=-rank.",
                    "empty_ranking_policy": "No exported run rows; require official -c per-query zero and inclusion in mean.",
                    "official_tolerance_basis": "Half of the default four-decimal output unit plus 1e-10 for representation.",
                    "timeout_seconds": TIMEOUT_SECONDS, "environment_overrides": {"LC_ALL": "C"},
                    "fixture_sha256": {"qrels": sha256(qrels_path), "run": sha256(run_path)}}
        write_json(output / "metric-protocol.json", protocol)
        evidence.update({"protocol_sha256": sha256(output / "metric-protocol.json"), "command": command})
        started = time.monotonic()
        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=False,
                                       timeout=TIMEOUT_SECONDS, env={**os.environ, "LC_ALL": "C"})
        except subprocess.TimeoutExpired as exc:
            evidence.update({"elapsed_seconds": time.monotonic() - started, "timed_out": True})
            for channel in ("stdout", "stderr"):
                partial = getattr(exc, channel) or b""
                path = output / ("trec_eval." + channel + ".txt")
                path.write_bytes(partial if isinstance(partial, bytes) else partial.encode())
                evidence[channel + "_sha256"] = sha256(path)
            raise
        evidence["elapsed_seconds"] = time.monotonic() - started
        (output / "trec_eval.stdout.txt").write_text(completed.stdout)
        (output / "trec_eval.stderr.txt").write_text(completed.stderr)
        evidence.update({"evaluator_exit_code": completed.returncode,
                         "stdout_sha256": sha256(output / "trec_eval.stdout.txt"),
                         "stderr_sha256": sha256(output / "trec_eval.stderr.txt")})
        require(completed.returncode == 0, "official evaluator failed with exit " + str(completed.returncode))
        require(not completed.stderr.strip(), "official evaluator wrote unexpected stderr")
        official = parse_official(completed.stdout, protocol["query_vector"])
        evidence.update(compare_scores(fixtures, official))
        evidence["status"] = "passed"
    except (MetricGateError, OSError, TypeError, KeyError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        evidence["error"] = str(exc)
        write_json(output / "metric-gate.json", evidence)
        raise MetricGateError(str(exc)) from exc
    write_json(output / "metric-gate.json", evidence)
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trec-eval", required=True, type=Path)
    parser.add_argument("--build-receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_gate(args.trec_eval, args.build_receipt, args.output)
    except (MetricGateError, OSError) as exc:
        print("metric gate failed: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"], "query_count": result["query_count"],
                      "receipt": str(args.output / "metric-gate.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
