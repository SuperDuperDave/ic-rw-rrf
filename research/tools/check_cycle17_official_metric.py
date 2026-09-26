#!/usr/bin/env python3
"""Check frozen Cycle17 P@10 against the existing pinned NIST trec_eval.

Standalone standard-library reader: never imports the primary implementation,
fetches data, installs/builds an evaluator, or changes policies. Run --self-test
before freezing this source; --execute requires its recorded source digest.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
REVISION = "ba38899cbd4de0fb699b47f39b64ef1c107e4a5c"
BINARY = ROOT / f"_sessions/local/cycle15/runtime/trec_eval-{REVISION}/trec_eval"
BINARY_SHA256 = "ceab60f88648fe691c65bd4fdda4d293e2627a8378a22a8795f2e4c3455d0a17"
BUILD_RECEIPT = ROOT / "_sessions/evidence/2026-09-12-cycle15-evaluator-build.json"
BUILD_RECEIPT_SHA256 = "257f96e8f823c68e2f6c032e44ffcc349f275425ed17de880e24ca8d7c6abb0c"
P_SOURCE_SHA256 = "46f2a5f6b7cfc1c05d0c9cd2f6f8c59bd1e15a61355be4bfbbb38cadf578c057"
RESULTS = ROOT / "results/cycle17-2026-09-25"
LOCAL = ROOT / "_sessions/local/cycle17"
POLICIES = ("A", "S", "H", "M", "J")
QIDS = tuple(str(i) for i in range(1, 31))
MEAN_TOLERANCE = Fraction(1, 20000)  # Half a four-decimal output unit.


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "sha256": sha256(path), "bytes": path.stat().st_size}


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_evaluator():
    require(sha256(BUILD_RECEIPT) == BUILD_RECEIPT_SHA256, "prior build receipt changed")
    receipt = read_json(BUILD_RECEIPT)
    require(receipt["status"] == "passed" and receipt["build_exit_code"] == 0,
            "prior evaluator build did not pass")
    require(receipt["evaluator_revision"] == REVISION, "evaluator revision mismatch")
    require((ROOT / receipt["binary_path"]).resolve() == BINARY.resolve(),
            "prior build binary path mismatch")
    require(receipt["binary_sha256"] == BINARY_SHA256 and sha256(BINARY) == BINARY_SHA256,
            "pinned evaluator binary mismatch")
    require(os.access(BINARY, os.X_OK), "pinned evaluator is not executable")
    p_source = BINARY.parent / "m_P.c"
    require(sha256(p_source) == P_SOURCE_SHA256, "pinned P metric source mismatch")
    return {"binary": identity(BINARY), "build_receipt": identity(BUILD_RECEIPT),
            "P_source": identity(p_source), "revision": REVISION,
            "source_archive_sha256": receipt["source_archive_sha256"]}


def token(value):
    return isinstance(value, str) and value and not any(c.isspace() for c in value)


def export_heads(path, qids, heads, tag):
    """Artificial scores preserve the supplied order, including across cutoff10."""
    require(len(qids) == len(set(qids)) and set(heads) == set(qids), "export query mismatch")
    lines = []
    for qid in qids:
        require(token(qid) and qid != "all", "invalid query ID")
        head = heads[qid]
        require(isinstance(head, list) and all(token(doc) for doc in head), "invalid head")
        require(len(head) == len(set(head)), "duplicate document in head")
        lines.extend(f"{qid} Q0 {doc} {rank} {-rank} {tag}\n"
                     for rank, doc in enumerate(head, 1))
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.writelines(lines)


def parse_official(output, qids):
    parsed = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        require(len(fields) == 3 and fields[0] == "P_10", "unexpected official output row")
        _, qid, value = fields
        require(qid not in parsed, "duplicate official query row")
        require(re.fullmatch(r"[01]\.\d{4}", value) is not None,
                "official output is not a four-decimal value")
        require(0 <= Fraction(value) <= 1, "official P@10 outside [0,1]")
        parsed[qid] = value
    require(set(parsed) == set(qids) | {"all"}, "official query cohort mismatch")
    return parsed


def invoke(qrels, run, prefix, qids):
    command = [str(BINARY), "-q", "-c", "-m", "P.10", str(qrels), str(run)]
    stdout_path, stderr_path = Path(str(prefix) + ".stdout"), Path(str(prefix) + ".stderr")
    with stdout_path.open("x", encoding="utf-8") as stdout, stderr_path.open("x", encoding="utf-8") as stderr:
        completed = subprocess.run(command, stdout=stdout, stderr=stderr, check=False,
                                   timeout=30, env={**os.environ, "LC_ALL": "C"})
    require(completed.returncode == 0, "official evaluator failed")
    require(not stderr_path.read_text().strip(), "official evaluator wrote stderr")
    values = parse_official(stdout_path.read_text(), qids)
    return values, {"command": command, "exit_code": completed.returncode,
                    "run": identity(run), "stdout": identity(stdout_path), "stderr": identity(stderr_path)}


def compare(official, expected, mean):
    require(set(official) == set(expected) | {"all"}, "comparison cohort mismatch")
    require(all(0 <= value <= 1 and (value * 10).denominator == 1
                for value in expected.values()), "expected query P@10 is not a count/10")
    require(mean == sum(expected.values(), Fraction()) / len(expected), "saved mean is not query mean")
    for qid, value in expected.items():
        require(Fraction(official[qid]) == value, f"official query mismatch for {qid}")
    error = abs(Fraction(official["all"]) - mean)
    require(error <= MEAN_TOLERANCE, "official mean mismatch beyond output rounding")
    return {"per_query": {qid: {"saved_exact": str(value), "official": official[qid], "matches": True}
                           for qid, value in expected.items()},
            "mean": {"saved_exact": str(mean), "official": official["all"],
                     "absolute_error_exact": str(error), "rounding_tolerance_exact": str(MEAN_TOLERANCE)},
            "query_count": len(expected), "passed": True}


def self_test():
    evaluator = check_evaluator()
    # Hand expectations: grade2 counts once; unknown and grade0 count zero.
    # A short run and an empty run still use denominator10 and -c query mean.
    heads = {"mixed": ["g2", "unknown", "zero", "g1"] + [f"u{i}" for i in range(6)],
             "short": ["g2"], "empty": [],
             "boundary": [f"u{i}" for i in range(9)] + ["z_zero", "a_positive"],
             "perfect": [f"p{i}" for i in range(10)], "negative": ["zero"]}
    grades = {"mixed": {"g2": 2, "zero": 0, "g1": 1}, "short": {"g2": 2},
              "empty": {"not_retrieved": 1},
              "boundary": {"z_zero": 0, "a_positive": 2},
              "perfect": {f"p{i}": 1 for i in range(10)}, "negative": {"zero": 0}}
    expected = dict(zip(heads, map(Fraction, ["1/5", "1/10", "0", "0", "1", "0"])))
    with tempfile.TemporaryDirectory(prefix="cycle17-official-synthetic-") as directory:
        directory = Path(directory)
        qrels, run = directory / "synthetic.qrels", directory / "synthetic.run"
        qrels.write_text("".join(f"{q} 0.5 {doc} {grade}\n" for q, docs in grades.items()
                                 for doc, grade in docs.items()))
        export_heads(run, list(heads), heads, "cycle17_synthetic")
        rows = [line.split() for line in run.read_text().splitlines()]
        for qid, head in heads.items():
            selected = [row for row in rows if row[0] == qid]
            require([row[2] for row in selected] == head, "export reordered supplied IDs")
            require([int(row[4]) for row in selected] == list(range(-1, -len(head) - 1, -1)),
                    "export scores do not strictly decrease")
        official, artifacts = invoke(qrels, run, directory / "synthetic", list(heads))
        checked = compare(official, expected, Fraction(13, 60))
        # Reject malformed, extra/missing, duplicate, nonfinite and wrong-measure output.
        bad_outputs = ["P_10 mixed nan\n", "P_10 mixed 0.2000\n", "P_10 all 1.1000\n",
                       "P_10 mixed 0.2000\nP_10 mixed 0.2000\n", "map all 0.2000\n",
                       "".join(f"P_10 {qid} {value}\n" for qid, value in official.items())
                       + "P_10 intruder 0.0000\n"]
        for output in bad_outputs:
            try:
                parse_official(output, list(heads))
            except ValueError:
                pass
            else:
                raise AssertionError("invalid official output accepted")
        try:
            compare({**official, "mixed": "0.3000"}, expected, Fraction(13, 60))
        except ValueError:
            pass
        else:
            raise AssertionError("incorrect official value accepted")
        return {"status": "passed", "mode": "synthetic_only", "source": identity(__file__),
                "evaluator": evaluator, "qrels": identity(qrels), "artifacts": artifacts,
                "checks": checked, "negative_parser_cases": len(bad_outputs),
                "negative_comparison_cases": 1, "actual_cycle17_labels_read": False}


def execute(expected_source, results_dir):
    require(sha256(__file__) == expected_source, "checker source changed after freeze")
    output = RESULTS / "official-metric-check.json"
    require(not output.exists(), "official metric result already exists")
    work = LOCAL / "official-metric"
    work.mkdir(parents=True, exist_ok=False)
    result = {"status": "failed", "source": identity(__file__), "metric": "binary P@10",
              "scope": "Fixed heads and supplied qrels; unjudged-zero benchmark convention only.",
              "queries": list(QIDS), "policies": list(POLICIES),
              "rank_export": "Supplied order, one-based rank, strictly descending score=-rank.",
              "per_query_tolerance": "0", "mean_rounding_tolerance_exact": str(MEAN_TOLERANCE),
              "analysis_directory": str(results_dir.relative_to(ROOT)), "phases": {}}
    try:
        result["evaluator"] = check_evaluator()
        policies_path = results_dir / "prepared/policies.json"
        input_paths = [policies_path]
        for phase in ("early", "late"):
            input_paths.extend([results_dir / phase / "analysis.json", LOCAL / "inputs" / f"{phase}.qrels"])
        result["inputs"] = {str(path.relative_to(ROOT)): identity(path) for path in input_paths}
        saved = read_json(policies_path)
        require(isinstance(saved["query_ids"], list) and len(saved["query_ids"]) == 30
                and set(saved["query_ids"]) == set(QIDS), "frozen policy query cohort mismatch")
        require(set(saved["queries"]) == set(QIDS), "frozen query records mismatch")
        exported = {}
        for policy in POLICIES:
            heads = {qid: saved["queries"][qid]["policies"][policy] for qid in QIDS}
            require(all(isinstance(head, list) and len(head) == 10 for head in heads.values()),
                    "actual policy head does not contain ten documents")
            exported[policy] = work / f"{policy}.run"
            export_heads(exported[policy], QIDS, heads, f"cycle17_{policy}")
        for phase in ("early", "late"):
            analysis = read_json(results_dir / phase / "analysis.json")
            require(set(analysis["per_query"]) == set(QIDS), "analysis query cohort mismatch")
            require(set(analysis["benchmark"]["policies"]) == set(POLICIES), "analysis policies mismatch")
            phase_result = result["phases"][phase] = {}
            for policy in POLICIES:
                expected = {qid: Fraction(analysis["per_query"][qid]["benchmark"][policy]) for qid in QIDS}
                mean = Fraction(analysis["benchmark"]["policies"][policy])
                official, artifacts = invoke(LOCAL / "inputs" / f"{phase}.qrels", exported[policy],
                                             work / f"{phase}-{policy}", QIDS)
                phase_result[policy] = {"artifacts": artifacts, **compare(official, expected, mean)}
        require(sha256(__file__) == expected_source, "checker source changed during evaluation")
        check_evaluator()
        for path in input_paths:
            require(identity(path) == result["inputs"][str(path.relative_to(ROOT))],
                    "input changed during official evaluation: " + str(path))
        result.update(status="passed", comparisons={"per_query": 300, "means": 10})
    except Exception as exc:
        result["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        result["output_artifacts"] = {str(path.relative_to(ROOT)): identity(path)
                                      for path in sorted(work.iterdir()) if path.is_file()}
        write_json(output, result)
    return {"status": "passed", "result": identity(output), "comparisons": result["comparisons"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true", help="synthetic labels only")
    mode.add_argument("--execute", action="store_true", help="read actual frozen artifacts and qrels")
    parser.add_argument("--expected-source-sha256", help="source digest frozen before actual acquisition")
    parser.add_argument("--results-dir", type=Path, default=RESULTS,
                        help="directory containing prepared, early and late; inside this repository")
    args = parser.parse_args()
    if args.execute and not args.expected_source_sha256:
        parser.error("--execute requires --expected-source-sha256")
    try:
        result = self_test() if args.self_test else execute(args.expected_source_sha256, args.results_dir.resolve())
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"official metric gate failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
