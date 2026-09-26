#!/usr/bin/env python3
"""Audit frozen Cycle17 early outputs and reproduce its global late-label stop.

No later effectiveness metrics are computed. --public-custody uses sanitized
receipt identity statements instead of the three private HTTP receipt bodies.
That mode can reproduce numeric checks, but cannot rehash original private
receipt bytes; this distinction is recorded in the audit result.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCOPED = ROOT / "_sessions/tools/check_cycle17_scoped_labels.py"
SCOPED_SHA256 = "f9af55892a9b0345b297941c418f4c23fea070991e5c9ad1ce98364106b197fe"
INPUTS = ROOT / "_sessions/local/cycle17/inputs"
EVIDENCE = ROOT / "_sessions/evidence"
FINAL = ROOT / "results/cycle17-2026-09-25/final"
PLAN = ROOT / "_sessions/cycles/2026-09-25-cycle17-input-plan.json"
PRIVATE_TO_PUBLIC = {
    f"_sessions/evidence/2026-09-25-cycle17-{name}.json":
    f"_sessions/evidence/2026-09-25-cycle17-{name}-public.json"
    for name in ("initial-acquisition", "corrected-initial-acquisition",
                 "compatible-initial-acquisition")
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_helpers():
    require(hashlib.sha256(SCOPED.read_bytes()).hexdigest() == SCOPED_SHA256,
            "frozen scoped verifier changed")
    spec = importlib.util.spec_from_file_location("cycle17_scoped_independent", SCOPED)
    scoped = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scoped)
    compatible = scoped.load_compatible()
    corrected = compatible.load_corrected()
    module = corrected.load_original()
    compatible.adapt_own_run_parser(module)
    scoped.adapt_own_qrel_parser(module)
    module.read_docids = corrected.read_docids
    return module, scoped, compatible, corrected


def recorded_path(path):
    """Resolve repository-relative records without requiring the original clone path."""
    candidate = Path(path)
    if not candidate.is_absolute():
        return ROOT / candidate
    try:
        return ROOT / candidate.relative_to(ROOT)
    except ValueError:
        for marker in ("/_sessions/", "/evaluation/", "/results/"):
            if marker in str(candidate):
                return ROOT / (marker[1:] + str(candidate).split(marker, 1)[1])
    raise ValueError("recorded path is outside the audited repository")


def custody(module, public=False):
    substitutions = {}

    def check_file(path, digest, byte_count=None):
        resolved = recorded_path(path)
        relative = str(resolved.relative_to(ROOT))
        if public and relative in PRIVATE_TO_PUBLIC:
            counterpart = ROOT / PRIVATE_TO_PUBLIC[relative]
            published = module.read_json(counterpart)
            require(published["original_receipt_sha256"] == digest,
                    "public statement does not bind the expected private receipt")
            require(published["status"] == "passed", "public acquisition status")
            substitutions[relative] = {
                "public_path": str(counterpart.relative_to(ROOT)),
                "public_sha256": module.sha256(counterpart),
                "asserted_original_sha256": digest,
                "original_bytes_rehashed": False,
            }
        else:
            require(module.sha256(resolved) == digest, f"custody hash changed: {relative}")
            if byte_count is not None:
                require(resolved.stat().st_size == byte_count, f"custody size changed: {relative}")

    initial_path = EVIDENCE / "2026-09-25-cycle17-scoped-initial-acquisition.json"
    late_path = EVIDENCE / "2026-09-25-cycle17-late-acquisition.json"
    preflight_path = EVIDENCE / "2026-09-25-cycle17-scoped-preflight.json"
    initial, late = module.read_json(initial_path), module.read_json(late_path)
    frozen = initial["frozen"]
    module.equal(late["frozen"], frozen, "late source freeze")
    for phase, receipt, expected in (
        ("initial", initial, {"A.run", "S.run", "docids.txt", "early.qrels"}),
        ("late", late, {"late.qrels"}),
    ):
        require(receipt["schema"] == 1 and receipt["phase"] == phase and
                receipt["status"] == "passed", f"failed {phase} acquisition")
        require(receipt["preflight_sha256"] == module.sha256(preflight_path), "preflight identity")
        require(set(receipt["inputs"]) == expected, "received input set")
        for name, info in receipt["inputs"].items():
            check_file(INPUTS / name, info["sha256"], info["bytes"])
    module.equal(module.read_json(preflight_path)["frozen"], frozen, "preflight frozen map")
    for path, digest in frozen.items():
        check_file(path, digest)
    # Public receipts state identical acquired bytes; full mode additionally rehashes originals.
    for original, published in PRIVATE_TO_PUBLIC.items():
        receipt = module.read_json(ROOT / (published if public else original))
        module.equal(receipt["inputs"], initial["inputs"], "all corrections retain initial bytes")
        if not public:
            public_copy = module.read_json(ROOT / published)
            require(public_copy["original_receipt_sha256"] == module.sha256(ROOT / original),
                    "sanitized receipt does not bind original bytes")
            module.equal(public_copy["inputs"], receipt["inputs"], "public input identity retention")
    plan = module.read_json(PLAN)
    total = 0
    for key, item in plan["items"].items():
        receipt = late if key == "late" else initial
        info = receipt["inputs"][item["filename"]]
        require(info["bytes"] <= item["max_bytes"], "input ceiling exceeded")
        if "expected_bytes" in item:
            require(info["bytes"] == item["expected_bytes"], "unexpected run bytes")
        total += info["bytes"]
    require(total <= plan["max_total_bytes"], "total download ceiling")
    for phase, dirname, expected_outputs in (
        ("prepare", "prepared", {"policies.json"}), ("early", "early", {"analysis.json"})
    ):
        directory = FINAL / dirname
        manifest = module.read_json(directory / "manifest.json")
        success = module.read_json(directory / "success.json")
        require(success["status"] == "passed" and manifest["phase"] == phase,
                f"{phase} did not pass")
        check_file(directory / "manifest.json", success["manifest"]["sha256"], success["manifest"]["bytes"])
        module.equal(manifest["frozen"], frozen, f"{phase} frozen map")
        module.equal(manifest["tracked_before"], manifest["tracked_after"], f"{phase} unchanged inputs")
        for path, info in manifest["tracked_after"].items():
            check_file(path, info["sha256"], info["bytes"])
        require(set(manifest["outputs"]) == expected_outputs, f"{phase} output set")
        for filename, info in manifest["outputs"].items():
            check_file(directory / filename, info["sha256"], info["bytes"])
        require(set(manifest["inputs"]) == set(initial["inputs"]), f"{phase} source set")
        for filename, info in manifest["inputs"].items():
            require(recorded_path(info["path"]) == INPUTS / filename, "manifest input location")
            check_file(info["path"], info["sha256"], info["bytes"])
        if phase == "prepare":
            require(manifest["labels_parsed"] is False, "preparation label boundary")
        else:
            check_file(FINAL / "prepared/policies.json", manifest["policies"]["sha256"],
                       manifest["policies"]["bytes"])
    require(late["early_manifest_sha256"] == module.sha256(FINAL / "early/manifest.json"),
            "later acquisition did not bind completed early phase")
    prior_policy = ROOT / "results/cycle17-2026-09-25/compatible/prepared/policies.json"
    require(module.sha256(FINAL / "prepared/policies.json") == module.sha256(prior_policy),
            "scoped label adapter changed policy bytes")
    failure = module.read_json(FINAL / "late/failure.json")
    require(failure["status"] == "failed" and failure["phase"] == "late" and
            "removed or revised early grades" in failure["error"], "unexpected late stop")
    require(not (FINAL / "late/analysis.json").exists() and not (FINAL / "late/success.json").exists(),
            "global late phase contains unapproved analysis/success")
    return {
        "mode": "public_identity_statements" if public else "full_local_receipt_bytes",
        "all_raw_input_hashes_verified": True, "received_bytes": total,
        "policies_sha256": module.sha256(FINAL / "prepared/policies.json"),
        "early_manifest_sha256": module.sha256(FINAL / "early/manifest.json"),
        "late_acquisition_sha256": module.sha256(late_path),
        "late_failure_sha256": module.sha256(FINAL / "late/failure.json"),
        "late_preservation_sha256": module.sha256(FINAL / "late/label-preservation.json"),
        "private_receipt_substitutions": substitutions,
        "limitation": ("Original private HTTP receipt bytes are not rehashed; sanitized statements bind their "
                       "claimed hashes and preserve the checked raw input identities." if public else None),
    }


def run(args):
    require(not args.output.exists(), "exclusive audit output already exists")
    module, scoped, compatible, corrected = load_helpers()
    before = custody(module, args.public_custody)
    public_check = custody(module, True)
    valid = module.read_docids(INPUTS / "docids.txt")
    a, s = module.read_run(INPUTS / "A.run", valid), module.read_run(INPUTS / "S.run", valid)
    queries, arithmetic = module.reconstruct(a, s)
    policies = {"schema": 1, "query_ids": module.QUERY_IDS, "queries": {}}
    for q, data in queries.items():
        policies["queries"][q] = data | {
            "sources": {p: module.source_schema(data["sources"][p]) for p in ("A", "S")}}
    module.equal(module.read_json(FINAL / "prepared/policies.json"), policies, "all policy fields")
    early = module.read_qrels(INPUTS / "early.qrels", valid)
    analysis = module.summaries(queries, early)
    module.equal(module.read_json(FINAL / "early/analysis.json"), analysis, "all early analysis fields")
    late = module.read_qrels(INPUTS / "late.qrels", valid)
    mismatches = []
    for q in module.QUERY_IDS:
        for d, grade in early[q].items():
            if late[q].get(d) != grade:
                mismatches.append({"qid": q, "docid": d, "early_grade": grade,
                                   "late_grade": late[q].get(d),
                                   "kind": "revised" if d in late[q] else "removed"})
    preservation = {"passed": not mismatches, "early_pair_count": sum(map(len, early.values())),
                    "mismatches": mismatches}
    reported = module.read_json(FINAL / "late/label-preservation.json")
    for record in (preservation, reported):
        record["mismatches"].sort(key=lambda x: (int(x["qid"]), x["docid"]))
    module.equal(reported, preservation, "full global preservation failure")
    require(mismatches, "expected global preservation failure not reproduced")
    outside_candidates = []
    for mismatch in mismatches:
        q, d = mismatch["qid"], mismatch["docid"]
        candidates = set(queries[q]["hybrid_order"])
        outside_candidates.append(mismatch | {"in_valid_inventory": d in valid,
                                               "in_frozen_candidate_union": d in candidates})
    after = custody(module, args.public_custody)
    module.equal(after, before, "custody unchanged during audit")
    result = {
        "schema": 1, "status": "passed", "kind": "early_complete_global_late_stop_audit",
        "verifier": module.identity(__file__), "custody": after,
        "public_numerical_replay_custody": public_check,
        "synthetic_checks": scoped.self_test(module, corrected, compatible),
        "verified": {"canonical_sources": 2, "queries": 30, "policies_per_query": 5,
                     "all_early_policy_and_analysis_fields": True,
                     "unchanged_policy_bytes_across_label_scope_correction": True,
                     "global_late_preservation_failure": True},
        "preservation": preservation, "mismatch_candidate_membership": outside_candidates,
        "arithmetic_audit": arithmetic,
        "late_effectiveness_metrics_computed": False,
        "limits": ["Independent audit reuses only frozen independent helpers; no primary algorithm imported.",
                   "Late labels are read solely to reproduce preservation, not to compute later effectiveness.",
                   "Any candidate-scoped later-label analysis requires a separately recorded amendment.",
                   "Exact integer RRF ordering is audited separately from the saved floating-point policy order."],
    }
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": "passed", "output": str(args.output),
                      "global_mismatches": len(mismatches), "late_metrics_computed": False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-custody", action="store_true")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/cycle17-2026-09-25/checkpoint-audit.json")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
