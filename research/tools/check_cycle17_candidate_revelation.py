#!/usr/bin/env python3
"""Independent audit of the separately frozen Cycle17 candidate observation.

No primary algorithm is imported. Original global late preservation failure
remains a checked prerequisite; this audit concerns only frozen candidate scope.
Run only after the coordinator authorizes the new later-label comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = ROOT / "_sessions/tools/check_cycle17_checkpoint.py"
CHECKPOINT_SHA256 = "5860567ee78957ee5c54e5fad01959862c49b7c51c5e708b11ef6701df28205c"
PREFLIGHT = ROOT / "_sessions/evidence/2026-09-25-cycle17-candidate-preflight.json"
OUTPUTS = ROOT / "results/cycle17-2026-09-25/candidate-revelation"
POLICY_SHA256 = "888b101919af30f36bc1d12d15c3c7c028bb42a017d71c417cf5bd02360a14cd"
REQUIRED = {
    "_sessions/cycles/2026-09-25-cycle17-candidate-revelation-protocol.md",
    "evaluation/cycle17_candidate_revelation.py",
    "evaluation/tests/test_cycle17_candidate_revelation.py",
    "_sessions/tools/check_cycle17_checkpoint.py",
    "_sessions/tools/check_cycle17_candidate_revelation.py",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def helpers():
    require(hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest() == CHECKPOINT_SHA256,
            "frozen independent checkpoint verifier changed")
    spec = importlib.util.spec_from_file_location("cycle17_independent_checkpoint", CHECKPOINT)
    checkpoint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checkpoint)
    module, scoped, compatible, corrected = checkpoint.load_helpers()
    return checkpoint, module, scoped, compatible, corrected


def scope_labels(module, queries, early, late):
    narrowed_early, narrowed_late, per_query = {}, {}, {}
    removed, revised, scoped_mismatches = [], [], []
    for q in module.QUERY_IDS:
        candidate = set(queries[q]["hybrid_order"])
        narrowed_early[q] = {d: g for d, g in early[q].items() if d in candidate}
        narrowed_late[q] = {d: g for d, g in late[q].items() if d in candidate}
        per_query[q] = {
            "candidate_ids": sorted(candidate), "early_global": len(early[q]),
            "late_global": len(late[q]), "early_scoped": len(narrowed_early[q]),
            "late_scoped": len(narrowed_late[q]),
        }
        for d, grade in early[q].items():
            if late[q].get(d) == grade:
                continue
            original = {"qid": q, "docid": d, "early_grade": grade,
                        "late_grade": late[q].get(d), "kind": "revised" if d in late[q] else "removed"}
            proof = original | {
                "in_candidate_scope": d in candidate,
                "in_A_retained": d in queries[q]["sources"]["A"]["retained_order"],
                "in_S_retained": d in queries[q]["sources"]["S"]["retained_order"],
            }
            (revised if d in late[q] else removed).append(proof)
            if d in candidate:
                scoped_mismatches.append(original)
    counts = {key: sum(row[key] for row in per_query.values())
              for key in ("early_global", "late_global", "early_scoped", "late_scoped")}
    counts.update(
        early_excluded=counts["early_global"] - counts["early_scoped"],
        late_excluded=counts["late_global"] - counts["late_scoped"],
        scoped_added_pairs=sum(len(narrowed_late[q].keys() - narrowed_early[q].keys())
                               for q in module.QUERY_IDS),
    )
    scope = {
        "schema": 1, "scope_definition": "per-query frozen A100 union S100 (hybrid_order)",
        "query_ids": module.QUERY_IDS, "per_query": per_query, "counts": counts,
        "removed_full_pairs": removed, "revised_full_pairs": revised,
        "scoped_mismatches": scoped_mismatches,
        "scoped_preservation_passed": not scoped_mismatches,
        "early_equivalence_passed": False,
    }
    return narrowed_early, narrowed_late, scope


def self_test(module):
    queries = {q: {"hybrid_order": ["a", "b"],
                   "sources": {"A": {"retained_order": ["a"]},
                               "S": {"retained_order": ["b"]}}}
               for q in module.QUERY_IDS}
    early = {q: {"a": 1, "outside": 0} for q in module.QUERY_IDS}
    late = {q: {"a": 1, "b": 0} for q in module.QUERY_IDS}
    a, b, scope = scope_labels(module, queries, early, late)
    require(scope["scoped_preservation_passed"], "outside removals improperly fail scoped preservation")
    require(len(scope["removed_full_pairs"]) == 30 and scope["counts"]["scoped_added_pairs"] == 30,
            "scope counting")
    require(all(not x["in_candidate_scope"] for x in scope["removed_full_pairs"]), "removed scope proof")
    module.equal(module.bound(["a"], ["b"], early["1"]), module.bound(["a"], ["b"], a["1"]),
                 "early scope bound invariance")
    before, after = module.bound(["a"], ["b"], a["1"]), module.bound(["a"], ["b"], b["1"])
    require(Fraction(after["width"]) < Fraction(before["width"]), "added-label narrowing")
    late["1"]["a"] = 0
    _, _, revised = scope_labels(module, queries, early, late)
    require(not revised["scoped_preservation_passed"] and len(revised["scoped_mismatches"]) == 1,
            "scoped grade revision did not fail")
    del late["1"]["a"]
    _, _, removed = scope_labels(module, queries, early, late)
    require(not removed["scoped_preservation_passed"] and len(removed["scoped_mismatches"]) == 1,
            "scoped removal did not fail")
    return {"off_scope_removal_preserved_as_evidence": True, "scoped_changes_rejected": True,
            "early_bound_invariance": True, "added_label_narrowing": True,
            "frozen_candidate_scope": True}


def custody(checkpoint, module, public):
    previous = checkpoint.custody(module, public)
    preflight = module.read_json(PREFLIGHT)
    require(preflight["schema"] == 1 and preflight["status"] == "passed", "candidate preflight failed")
    frozen = preflight["frozen"]
    require(REQUIRED <= frozen.keys(), "candidate source freeze incomplete")
    public_assertions = {}

    def check(path, info):
        path = checkpoint.recorded_path(path)
        relative = str(path.relative_to(ROOT))
        digest = info if isinstance(info, str) else info["sha256"]
        if public and relative in checkpoint.PRIVATE_TO_PUBLIC:
            public_path = ROOT / checkpoint.PRIVATE_TO_PUBLIC[relative]
            statement = module.read_json(public_path)
            require(statement["original_receipt_sha256"] == digest, "public original identity statement")
            public_assertions[relative] = module.identity(public_path)
        else:
            require(module.sha256(path) == digest, f"candidate custody changed: {relative}")
            if isinstance(info, dict):
                require(path.stat().st_size == info["bytes"], f"candidate custody byte count: {relative}")

    for path, digest in frozen.items():
        check(path, digest)
    manifest = module.read_json(OUTPUTS / "manifest.json")
    success = module.read_json(OUTPUTS / "success.json")
    require(success["status"] == "passed" and manifest["phase"] == "candidate-revelation",
            "candidate observation not passed")
    check(OUTPUTS / "manifest.json", success["manifest"])
    module.equal(manifest["frozen"], frozen, "candidate manifest frozen map")
    module.equal(manifest["tracked_before"], manifest["tracked_after"], "candidate unchanged custody")
    for path, info in manifest["tracked_after"].items():
        check(path, info)
    require(set(manifest["outputs"]) == {"early.json", "late.json", "revelation.json", "scope.json"},
            "candidate output artifact set")
    for filename, info in manifest["outputs"].items():
        check(OUTPUTS / filename, info)
    require(set(manifest["inputs"]) == {"A.run", "S.run", "docids.txt", "early.qrels", "late.qrels"},
            "candidate input set")
    for filename, info in manifest["inputs"].items():
        require(checkpoint.recorded_path(info["path"]) == checkpoint.INPUTS / filename, "candidate input path")
        check(info["path"], info)
    require(checkpoint.recorded_path(manifest["preflight"]) == PREFLIGHT, "candidate preflight path")
    require(manifest["design_primary_contrast"] == "H-S", "candidate primary contrast")
    check(checkpoint.FINAL / "prepared/policies.json", manifest["policies"])
    require(module.sha256(checkpoint.FINAL / "prepared/policies.json") == POLICY_SHA256,
            "frozen policy bytes changed")
    return {"prior_checkpoint_custody": previous, "preflight": module.identity(PREFLIGHT),
            "manifest": module.identity(OUTPUTS / "manifest.json"),
            "public_receipt_identity_statements": public_assertions,
            "mode": "public_identity_statements" if public else "full_local_receipt_bytes"}


def run(args):
    require(not args.output.exists(), "exclusive audit output already exists")
    checkpoint, module, _, _, _ = helpers()
    before = custody(checkpoint, module, args.public_custody)
    valid = module.read_docids(checkpoint.INPUTS / "docids.txt")
    a = module.read_run(checkpoint.INPUTS / "A.run", valid)
    s = module.read_run(checkpoint.INPUTS / "S.run", valid)
    queries, arithmetic = module.reconstruct(a, s)
    expected_policies = {"schema": 1, "query_ids": module.QUERY_IDS, "queries": {}}
    for q, data in queries.items():
        expected_policies["queries"][q] = data | {
            "sources": {p: module.source_schema(data["sources"][p]) for p in ("A", "S")}}
    module.equal(module.read_json(checkpoint.FINAL / "prepared/policies.json"), expected_policies,
                 "unchanged canonical policies")
    early_all = module.read_qrels(checkpoint.INPUTS / "early.qrels", valid)
    late_all = module.read_qrels(checkpoint.INPUTS / "late.qrels", valid)
    early_labels, late_labels, scope = scope_labels(module, queries, early_all, late_all)
    require(scope["scoped_preservation_passed"], "scoped label preservation failed")
    early, late = module.summaries(queries, early_labels), module.summaries(queries, late_labels)
    full_early = module.summaries(queries, early_all)
    module.equal(module.read_json(checkpoint.FINAL / "early/analysis.json"), full_early,
                 "previous complete early analysis")
    module.equal({k: v for k, v in early.items() if k != "qrels_pair_count"},
                 {k: v for k, v in full_early.items() if k != "qrels_pair_count"}, "all early fields invariant")
    scope["early_equivalence_passed"] = True
    module.equal(module.read_json(OUTPUTS / "early.json"), early, "all scoped early fields")
    module.equal(module.read_json(OUTPUTS / "late.json"), late, "all scoped late fields")
    revelation = module.revelation(early, late, early_labels, late_labels)
    revelation.update(design_primary_contrast="H-S",
                      design_primary_width_reduced=Fraction(revelation["contrasts"]["H-S"]["width_reduction"]) > 0,
                      observation_status="candidate_scope_only")
    reported_revelation = module.read_json(OUTPUTS / "revelation.json")
    for artifact in (revelation, reported_revelation):
        artifact["added_support_labels"].sort(key=lambda x: (x["contrast"], int(x["qid"]), x["docid"]))
        artifact["exchange_category_transitions"].sort(key=lambda x: (int(x["qid"]), x["policy"]))
    module.equal(reported_revelation, revelation, "all revelation fields")
    reported_scope = module.read_json(OUTPUTS / "scope.json")
    for artifact in (scope, reported_scope):
        for key in ("removed_full_pairs", "revised_full_pairs", "scoped_mismatches"):
            artifact[key].sort(key=lambda x: (int(x["qid"]), x["docid"]))
    module.equal(reported_scope, scope, "all scope fields")
    global_report = module.read_json(checkpoint.FINAL / "late/label-preservation.json")
    proofs = scope["removed_full_pairs"] + scope["revised_full_pairs"]
    original_keys = ("qid", "docid", "early_grade", "late_grade", "kind")
    rebuilt_mismatches = sorted([{k: p[k] for k in original_keys} for p in proofs],
                                key=lambda x: (int(x["qid"]), x["docid"]))
    global_report["mismatches"].sort(key=lambda x: (int(x["qid"]), x["docid"]))
    module.equal(global_report, {"passed": False, "early_pair_count": sum(map(len, early_all.values())),
                                 "mismatches": rebuilt_mismatches}, "original global failure preserved")
    after = custody(checkpoint, module, args.public_custody)
    module.equal(after, before, "candidate custody unchanged throughout audit")
    result = {
        "schema": 1, "status": "passed", "kind": "post_hoc_candidate_scope_independent_audit",
        "verifier": module.identity(__file__), "custody": after,
        "public_replay_custody": custody(checkpoint, module, True), "self_test": self_test(module),
        "verified": {"all_canonical_policy_fields": True, "all_scoped_early_and_late_fields": True,
                     "all_revelation_and_scope_fields": True, "early_invariant_except_qrels_pair_count": True,
                     "scoped_label_preservation": True, "every_query_and_aggregate_interval_nested": True,
                     "original_global_failure_preserved": True},
        "arithmetic_audit": arithmetic,
        "design_primary_contrast": "H-S", "original_effectiveness_primary": "M-H",
        "limits": ["This checks arithmetic on the same panel; it is not independent effectiveness evidence.",
                   "Candidate scope and H-S observation priority were recorded after the global failure and early outcomes.",
                   "Public custody validates raw input identities through sanitized receipt statements, not private receipt bytes.",
                   "Bounds remain conditional on the supplied judgments applying to the named query/document units."],
    }
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": "passed", "output": str(args.output), "design_primary_contrast": "H-S"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--public-custody", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUTS / "independent-check.json")
    args = parser.parse_args()
    if args.self_test:
        _, module, _, _, _ = helpers()
        print(json.dumps(self_test(module), sort_keys=True))
    else:
        run(args)


if __name__ == "__main__":
    main()
