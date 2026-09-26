#!/usr/bin/env python3
"""Verify six frozen Cycle18 heads with pinned NIST P@10; no data acquisition."""
import argparse
import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "_sessions/tools/check_cycle17_official_metric.py"
CHECKER_SHA256 = "e405e782b257ceb9ae0cde2e7d08b774a9d71839a94685d28cdbed0ff710496a"
QRELS = ROOT / "_sessions/local/cycle17/inputs/late.qrels"
QRELS_SHA256 = "84f608d302d07df206243b051e52ea0592a09ef0413cf56a12b77c9a30d022f5"
POLICIES = ("A", "D", "T", "S", "H", "F")
QIDS = tuple(str(i) for i in range(1, 31))
PROTOCOL = ROOT / "_sessions/cycles/2026-09-25-cycle18-protocol.md"
PLAN = ROOT / "_sessions/cycles/2026-09-25-cycle18-input-plan.json"


def load_checker():
    if hashlib.sha256(CHECKER.read_bytes()).hexdigest() != CHECKER_SHA256:
        raise ValueError("frozen official checker source changed")
    spec = importlib.util.spec_from_file_location("cycle17_frozen_official", CHECKER)
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    check.check_evaluator()
    return check


def validate_schema(check, saved, analysis):
    check.require(saved["query_ids"] == list(QIDS), "policy query vector mismatch")
    check.require(set(saved["queries"]) == set(QIDS), "policy query records mismatch")
    check.require(set(analysis["per_query"]) == set(QIDS), "analysis query records mismatch")
    means = analysis["benchmark"]["policies"]
    check.require(set(means) == set(POLICIES), "mean policies mismatch")
    check.require(all(isinstance(value, str) for value in means.values()), "means must be exact strings")
    for qid in QIDS:
        heads = saved["queries"][qid]["policies"]
        benchmarks = analysis["per_query"][qid]["benchmark"]
        check.require(set(heads) == set(POLICIES), "head policies mismatch")
        check.require(set(benchmarks) == set(POLICIES), "query benchmark policies mismatch")
        check.require(all(isinstance(value, str) for value in benchmarks.values()),
                      "query benchmarks must be exact strings")
        for head in heads.values():
            check.require(isinstance(head, list) and len(head) == 10 and all(check.token(doc) for doc in head)
                          and len(set(head)) == 10, "head must contain ten distinct document tokens")


def comparisons(check, saved, analysis, qrels, work, results):
    validate_schema(check, saved, analysis)
    started = time.monotonic()
    for policy in POLICIES:
        check.require(time.monotonic() - started < 270, "official checks exceeded wall bound")
        heads = {qid: saved["queries"][qid]["policies"][policy] for qid in QIDS}
        run = work / f"{policy}.run"
        check.export_heads(run, QIDS, heads, f"cycle18_{policy}")
        expected = {qid: check.Fraction(analysis["per_query"][qid]["benchmark"][policy]) for qid in QIDS}
        mean = check.Fraction(analysis["benchmark"]["policies"][policy])
        official, artifacts = check.invoke(qrels, run, work / policy, QIDS)
        results[policy] = {"artifacts": artifacts, **check.compare(official, expected, mean)}
    check.require(time.monotonic() - started < 300, "official checks exceeded wall bound")


def self_test(check):
    inherited = check.self_test()
    saved = {"query_ids": list(QIDS), "queries": {}}
    analysis = {"benchmark": {"policies": {"A": "0", "D": "1/10", "T": "1/5",
                                           "S": "3/10", "H": "7/10", "F": "299/300"}},
                "per_query": {}}
    # Independent hand counts: 0,1,2,3,7,10 positives; query1 F has only9.
    # Alternating grades1/2 each count once; explicit zero and unknown count zero.
    for qid in QIDS:
        heads, benchmarks = {}, {}
        for policy, count, expected in zip(POLICIES, (0, 1, 2, 3, 7, 10),
                                            ("0", "1/10", "1/5", "3/10", "7/10", "1")):
            if qid == "1" and policy == "F":
                count, expected = 9, "9/10"
            heads[policy] = ([f"p{i}" for i in range(count)] + ["zero"]
                             + [f"u{i}" for i in range(10)])[:10]
            benchmarks[policy] = expected
        saved["queries"][qid] = {"policies": heads}
        analysis["per_query"][qid] = {"benchmark": benchmarks}
    rejected = 0
    malformed = []
    missing_query = copy.deepcopy(saved)
    del missing_query["queries"]["30"]
    malformed.append((missing_query, analysis))
    missing_policy = copy.deepcopy(saved)
    del missing_policy["queries"]["1"]["policies"]["F"]
    malformed.append((missing_policy, analysis))
    duplicate_doc = copy.deepcopy(saved)
    duplicate_doc["queries"]["1"]["policies"]["A"][1] = "zero"
    malformed.append((duplicate_doc, analysis))
    bad_number = copy.deepcopy(analysis)
    bad_number["per_query"]["1"]["benchmark"]["F"] = 0.9
    malformed.append((saved, bad_number))
    for bad_saved, bad_analysis in malformed:
        try:
            validate_schema(check, bad_saved, bad_analysis)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("invalid producer schema accepted")
    with tempfile.TemporaryDirectory(prefix="cycle18-official-synthetic-") as temp:
        work = Path(temp)
        qrels = work / "synthetic.qrels"
        qrels.write_text("".join(f"{qid} 0.5 p{i} {1 + i % 2}\n" for qid in QIDS for i in range(10))
                         + "".join(f"{qid} 0.5 zero 0\n" for qid in QIDS), encoding="utf-8")
        results = {}
        comparisons(check, saved, analysis, qrels, work, results)
        return {"status": "passed", "mode": "synthetic_only", "source": check.identity(__file__),
                "helper": check.identity(CHECKER), "evaluator": check.check_evaluator(),
                "actual_cycle18_inputs_read": False, "schema_rejection_cases": rejected,
                "comparisons": {"per_query": 180, "means": 6},
                "synthetic_qrels": check.identity(qrels),
                "synthetic_means": {name: value["mean"] for name, value in results.items()},
                "inherited_fixture_checks": inherited["checks"],
                "inherited_parser_rejections": inherited["negative_parser_cases"],
                "inherited_comparison_rejections": inherited["negative_comparison_cases"]}


def execute(check, args):
    check.require(check.sha256(__file__) == args.expected_source_sha256, "Cycle18 checker source changed after freeze")
    check.require(not args.output.exists(), "official metric result already exists")
    args.work_dir.mkdir(parents=True, exist_ok=False)
    paths = [Path(__file__), CHECKER, PROTOCOL, PLAN, args.policies, args.analysis, QRELS]

    def receipt():
        return {"files": {check.identity(path)["path"]: check.identity(path) for path in paths},
                "evaluator": check.check_evaluator()}

    result = {"schema": "cycle18-official-metric-check-v1", "status": "failed",
              "scope": "Six frozen policies; official binary P@10 on full raw late qrels, missing-zero convention.",
              "raw_qrels_unfiltered": True, "policies": {}, "query_count": 30,
              "per_query_tolerance": "0", "mean_rounding_tolerance_exact": str(check.MEAN_TOLERANCE),
              "rank_export": "Frozen supplied head order; one-based rank; score=-rank, without ties."}
    try:
        check.require(check.sha256(QRELS) == QRELS_SHA256, "pinned full late qrels mismatch")
        result["before"] = receipt()
        check.write_json(args.work_dir / "before.json", result["before"])
        comparisons(check, check.read_json(args.policies), check.read_json(args.analysis),
                    QRELS, args.work_dir, result["policies"])
        result["after"] = receipt()
        check.write_json(args.work_dir / "after.json", result["after"])
        check.require(result["before"] == result["after"], "inputs, code or evaluator changed during check")
        result.update(status="passed", comparisons={"per_query": 180, "means": 6})
    except Exception as exc:
        result["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        result["output_artifacts"] = {check.identity(path)["path"]: check.identity(path)
                                      for path in sorted(args.work_dir.iterdir()) if path.is_file()}
        check.write_json(args.output, result)
    return {"status": "passed", "result": check.identity(args.output), "comparisons": result["comparisons"],
            "means": {name: value["mean"] for name, value in result["policies"].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--expected-source-sha256")
    parser.add_argument("--policies", type=Path)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "results/cycle18-2026-09-25/official-metric-check.json")
    parser.add_argument("--work-dir", type=Path, default=ROOT / "_sessions/local/cycle18/official-metric")
    args = parser.parse_args()
    if args.execute and not all((args.expected_source_sha256, args.policies, args.analysis)):
        parser.error("--execute requires --expected-source-sha256, --policies and --analysis")
    for name in ("policies", "analysis", "output", "work_dir"):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    check = load_checker()
    result = self_test(check) if args.self_test else execute(check, args)
    print(check.json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
