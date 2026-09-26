#!/usr/bin/env python3
"""Recorded candidate-scope revelation after the preserved global nesting failure.

No rankings are rebuilt. Both judgment files are restricted to the same saved
A100-union-S100 candidate sets. Early analyses must agree in every field except
the count of parsed label pairs; scoped early grades must be exactly preserved.
"""

import argparse
from fractions import Fraction
import json
from pathlib import Path
import signal
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import cycle17_minority_exchange as original
from evaluation import cycle17_scoped_labels as scoped


PROTOCOL = "_sessions/cycles/2026-09-25-cycle17-candidate-revelation-protocol.md"
SOURCE = "evaluation/cycle17_candidate_revelation.py"
TESTS = "evaluation/tests/test_cycle17_candidate_revelation.py"
VERIFIER = "_sessions/tools/check_cycle17_candidate_revelation.py"
PREPARED = "results/cycle17-2026-09-25/final/prepared"
EARLY = "results/cycle17-2026-09-25/final/early"
GLOBAL_LATE = "results/cycle17-2026-09-25/final/late"
LATE_ACQUISITION = "_sessions/evidence/2026-09-25-cycle17-late-acquisition.json"
LATE_INPUT = "_sessions/local/cycle17/inputs/late.qrels"
POLICY_SHA256 = "888b101919af30f36bc1d12d15c3c7c028bb42a017d71c417cf5bd02360a14cd"
REQUIRED_FROZEN = frozenset((
    PROTOCOL, SOURCE, TESTS, VERIFIER,
    "_sessions/evidence/2026-09-25-cycle17-scoped-preflight.json",
    "_sessions/evidence/2026-09-25-cycle17-scoped-initial-acquisition.json",
    PREPARED + "/policies.json", PREPARED + "/manifest.json", PREPARED + "/success.json",
    EARLY + "/analysis.json", EARLY + "/manifest.json", EARLY + "/success.json",
    LATE_ACQUISITION, GLOBAL_LATE + "/failure.json", GLOBAL_LATE + "/label-preservation.json",
))


class CandidateScopeError(original.ContractError):
    """Carries the observed scope ledger when its preservation gate fails."""

    def __init__(self, message, scope):
        super().__init__(message)
        self.scope = scope


def scope_observations(policies, early_labels, late_labels):
    qids = policies["query_ids"]
    original.require(set(qids) == set(early_labels) == set(late_labels), "candidate label cohort differs")
    scopes, early, late, per_query = {}, {}, {}, {}
    for qid in qids:
        query = policies["queries"][qid]
        scopes[qid] = set(query["hybrid_order"])
        union = set(query["sources"]["A"]["retained_order"]) | set(query["sources"]["S"]["retained_order"])
        original.require(scopes[qid] == union, "saved hybrid candidate set differs from source union")
        original.require(all(set(head) <= scopes[qid] for head in query["policies"].values()),
                         "saved policy contains document outside saved candidate set")
        early[qid] = {doc: grade for doc, grade in early_labels[qid].items() if doc in scopes[qid]}
        late[qid] = {doc: grade for doc, grade in late_labels[qid].items() if doc in scopes[qid]}
        per_query[qid] = {"candidate_ids": sorted(scopes[qid]), "early_global": len(early_labels[qid]),
                          "late_global": len(late_labels[qid]), "early_scoped": len(early[qid]),
                          "late_scoped": len(late[qid])}
    proofs = []
    for row in original.label_mismatches(early_labels, late_labels):
        qid, doc = row["qid"], row["docid"]
        query = policies["queries"][qid]
        proofs.append({**row, "in_candidate_scope": doc in scopes[qid],
                       "in_A_retained": doc in query["sources"]["A"]["retained_order"],
                       "in_S_retained": doc in query["sources"]["S"]["retained_order"]})
    counts = {key: sum(row[key] for row in per_query.values())
              for key in ("early_global", "late_global", "early_scoped", "late_scoped")}
    counts.update(early_excluded=counts["early_global"] - counts["early_scoped"],
                  late_excluded=counts["late_global"] - counts["late_scoped"],
                  scoped_added_pairs=sum(len(set(late[qid]) - set(early[qid])) for qid in qids))
    mismatches = original.label_mismatches(early, late)
    scope = {"schema": 1, "scope_definition": "per-query frozen A100 union S100 (hybrid_order)",
             "query_ids": list(qids), "per_query": per_query, "counts": counts,
             "removed_full_pairs": [row for row in proofs if row["kind"] == "removed"],
             "revised_full_pairs": [row for row in proofs if row["kind"] == "revised"],
             "scoped_mismatches": mismatches, "scoped_preservation_passed": not mismatches,
             "early_equivalence_passed": False}
    return early, late, scope


def analyze_candidates(policies, early_labels, late_labels, reference_early):
    early_labels, late_labels, scope = scope_observations(policies, early_labels, late_labels)
    if not scope["scoped_preservation_passed"]:
        raise CandidateScopeError("candidate-scoped early grades removed or revised", scope)
    early = original.analyze(policies, early_labels)
    expected = {key: value for key, value in reference_early.items() if key != "qrels_pair_count"}
    observed = {key: value for key, value in early.items() if key != "qrels_pair_count"}
    if expected != observed:
        raise CandidateScopeError("scoped early analysis differs beyond qrels_pair_count", scope)
    scope["early_equivalence_passed"] = True
    late = original.analyze(policies, late_labels)
    revelation = original.compare_phases(early, late, early_labels, late_labels)
    revelation.update(design_primary_contrast="H-S", observation_status="candidate_scope_only",
                      design_primary_width_reduced=Fraction(revelation["contrasts"]["H-S"]["width_reduction"]) > 0)
    return {"early.json": early, "late.json": late, "revelation.json": revelation, "scope.json": scope}


def run_observation(preflight_path, output):
    preflight_path = Path(preflight_path).resolve()
    preflight_identity = original.identity(preflight_path)
    preflight = original.read_json(preflight_path)
    original.require(preflight.get("status") == "passed", "candidate preflight did not pass")
    frozen = preflight["frozen"]
    original.require(REQUIRED_FROZEN <= set(frozen), "candidate preflight omitted required frozen identities")
    with scoped.scoped_runtime():
        tracked = original.check_frozen(frozen)
        tracked[str(preflight_path)] = preflight_identity
        prepared_path, early_path = original.ROOT / PREPARED, original.ROOT / EARLY
        prepared, prepared_tracked = original.load_phase(prepared_path, "prepare")
        early_manifest, early_tracked = original.load_phase(early_path, "early")
        original.require(all(frozen.get(name) == digest for name, digest in prepared["frozen"].items()),
                         "candidate preflight did not preserve original frozen map")
        original.require(early_manifest["prepared"] == str(prepared_path.resolve()), "early preparation differs")
        policy_identity = original.identity(prepared_path / "policies.json")
        original.require(policy_identity["sha256"] == POLICY_SHA256, "fixed policy bytes differ")
        original.require(early_manifest["policies"] == policy_identity, "early policy identity differs")
        receipt, late_inputs, late_tracked = original.acquisition_inputs(
            original.ROOT / LATE_ACQUISITION, {"late.qrels": original.ROOT / LATE_INPUT},
            frozen=prepared["frozen"])
        original.require(receipt.get("early_manifest_sha256") == original.identity(early_path / "manifest.json")["sha256"],
                         "late acquisition refers to different early analysis")
        for observed in (prepared_tracked, early_tracked, late_tracked):
            for path, value in observed.items():
                original.require(path not in tracked or tracked[path] == value, "conflicting tracked identity")
                tracked[path] = value
        policies = original.read_json(prepared_path / "policies.json")
        inputs = prepared["inputs"]
        docids = original.parse_docids(Path(inputs["docids.txt"]["path"]).read_text(encoding="utf-8"))
        early_labels = original.parse_qrels(Path(inputs["early.qrels"]["path"]).read_text(encoding="utf-8"), docids)
        late_labels = original.parse_qrels((original.ROOT / LATE_INPUT).read_text(encoding="utf-8"), docids)
        preservation = original.read_json(original.ROOT / GLOBAL_LATE / "label-preservation.json")
        original.require(preservation.get("passed") is False, "global preservation failure not recorded")
        original.require(preservation["mismatches"] == original.label_mismatches(early_labels, late_labels),
                         "recorded global mismatches differ from pinned raw labels")
        original.require(preservation["early_pair_count"] == sum(map(len, early_labels.values())),
                         "recorded global early pair count differs")
        artifacts = analyze_candidates(policies, early_labels, late_labels,
                                       original.read_json(early_path / "analysis.json"))
        for name, contents in artifacts.items():
            original.write_json(output / name, contents)
        original.finish_phase(output, "candidate-revelation", tracked,
            {"frozen": frozen, "prepared": str(prepared_path.resolve()), "early": str(early_path.resolve()),
             "policies": policy_identity, "inputs": {**inputs, **late_inputs},
             "preflight": str(preflight_path), "design_primary_contrast": "H-S"}, list(artifacts))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    created = False
    started = time.monotonic()
    def timeout(signum, frame):
        raise original.ContractError("candidate phase exceeded 300 seconds")
    old_handler = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    try:
        output.mkdir(parents=True, exist_ok=False)
        created = True
        run_observation(args.preflight, output)
        print(json.dumps({"status": "passed", "phase": "candidate-revelation", "output": str(output)}))
        return 0
    except Exception as exc:
        failure = {"status": "failed", "phase": "candidate-revelation", "error_type": type(exc).__name__,
                   "error": str(exc), "command": sys.argv, "elapsed_seconds": time.monotonic() - started}
        path = output / "failure.json" if created else output.parent / (output.name + f".failure-{time.time_ns()}.json")
        try:
            if created and isinstance(exc, CandidateScopeError):
                original.write_json(output / "scope-failure.json", exc.scope)
            original.write_json(path, failure)
            failure["failure_artifact"] = str(path)
        except OSError as write_error:
            failure["failure_artifact_error"] = str(write_error)
        print(json.dumps(failure), file=sys.stderr)
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


if __name__ == "__main__":
    raise SystemExit(main())
