#!/usr/bin/env python3
"""Check candidate-scoped late P@10 against official evaluation of raw qrels."""
import hashlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "_sessions/tools/check_cycle17_official_metric.py"
CHECKER_SHA256 = "e405e782b257ceb9ae0cde2e7d08b774a9d71839a94685d28cdbed0ff710496a"


def main():
    if hashlib.sha256(CHECKER.read_bytes()).hexdigest() != CHECKER_SHA256:
        raise ValueError("frozen official checker source changed")
    spec = importlib.util.spec_from_file_location("cycle17_frozen_official", CHECKER)
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    base = ROOT / "results/cycle17-2026-09-25"
    output = base / "candidate-official-metric-check.json"
    check.require(not output.exists(), "candidate official result already exists")
    work = ROOT / "_sessions/local/cycle17/candidate-official-metric"
    work.mkdir(parents=True, exist_ok=False)
    policy_path = base / "final/prepared/policies.json"
    analysis_path = base / "candidate-revelation/late.json"
    qrels_path = ROOT / "_sessions/local/cycle17/inputs/late.qrels"
    paths = [Path(__file__), CHECKER, policy_path, analysis_path, qrels_path]

    def receipt():
        return {"files": {str(path.relative_to(ROOT)): check.identity(path) for path in paths},
                "evaluator": check.check_evaluator()}

    result = {"schema": "cycle17-candidate-official-metric-check-v1", "status": "failed",
              "scope": "Candidate-scoped late benchmark checked against official P@10 on full raw late qrels.",
              "raw_qrels_unfiltered": True, "policies": {}, "query_count": 30,
              "per_query_tolerance": "0", "mean_rounding_tolerance_exact": str(check.MEAN_TOLERANCE),
              "rank_export": "Frozen supplied head order; one-based rank; score=-rank, without ties."}
    try:
        result["before"] = receipt()
        check.write_json(work / "before.json", result["before"])
        saved, analysis = check.read_json(policy_path), check.read_json(analysis_path)
        check.require(saved["query_ids"] == list(check.QIDS), "policy query vector mismatch")
        check.require(set(saved["queries"]) == set(check.QIDS), "policy query records mismatch")
        check.require(set(analysis["per_query"]) == set(check.QIDS), "analysis query cohort mismatch")
        check.require(set(analysis["benchmark"]["policies"]) == set(check.POLICIES), "mean policies mismatch")
        for policy in check.POLICIES:
            heads = {qid: saved["queries"][qid]["policies"][policy] for qid in check.QIDS}
            check.require(all(isinstance(head, list) and len(head) == 10 for head in heads.values()),
                          "actual policy head does not contain ten documents")
            run = work / f"{policy}.run"
            check.export_heads(run, check.QIDS, heads, f"cycle17_candidate_{policy}")
            expected = {qid: check.Fraction(analysis["per_query"][qid]["benchmark"][policy])
                        for qid in check.QIDS}
            mean = check.Fraction(analysis["benchmark"]["policies"][policy])
            official, artifacts = check.invoke(qrels_path, run, work / f"late-{policy}", check.QIDS)
            result["policies"][policy] = {"artifacts": artifacts, **check.compare(official, expected, mean)}
        result["after"] = receipt()
        check.write_json(work / "after.json", result["after"])
        check.require(result["before"] == result["after"], "inputs, code or evaluator changed during check")
        result.update(status="passed", comparisons={"per_query": 150, "means": 5})
    except Exception as exc:
        result["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        result["output_artifacts"] = {str(path.relative_to(ROOT)): check.identity(path)
                                      for path in sorted(work.iterdir()) if path.is_file()}
        check.write_json(output, result)
    print(check.json.dumps({"status": result["status"], "result": check.identity(output),
                            "comparisons": result["comparisons"],
                            "means": {key: value["mean"] for key, value in result["policies"].items()}},
                           indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
