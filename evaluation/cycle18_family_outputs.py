#!/usr/bin/env python3
"""Cycle18: exact family-mean substitution at fixed lexical weight.

Rankings and structural diagnostics are serialized before the one label snapshot
is parsed. This producer acquires no data and never chooses a scalar weight.
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

from evaluation import cycle17_minority_exchange as core
from evaluation import cycle17_minority_exchange_corrected as doc_parser
from evaluation import cycle17_minority_exchange_compatible as run_parser
from evaluation import cycle17_scoped_labels as label_parser


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "_sessions/cycles/2026-09-25-cycle18-protocol.md"
PLAN = "_sessions/cycles/2026-09-25-cycle18-input-plan.json"
SOURCE = "evaluation/cycle18_family_outputs.py"
TESTS = "evaluation/tests/test_cycle18_family_outputs.py"
HISTORICAL = "results/cycle17-2026-09-25/final/prepared/policies.json"
HISTORICAL_SHA256 = "888b101919af30f36bc1d12d15c3c7c028bb42a017d71c417cf5bd02360a14cd"
REQUIRED_FROZEN = {PROTOCOL, PLAN, SOURCE, TESTS, HISTORICAL,
                   "evaluation/cycle17_minority_exchange.py",
                   "evaluation/cycle17_minority_exchange_corrected.py",
                   "evaluation/cycle17_minority_exchange_compatible.py",
                   "evaluation/cycle17_scoped_labels.py"}
SOURCES = ("A", "D", "T", "S")
POLICIES = SOURCES + ("H", "F")
CONTRASTS = (("F", "H"), ("F", "S"), ("F", "A"), ("F", "D"), ("F", "T"), ("H", "S"))
CATEGORIES = ("shared", "arrival", "departure", "absent")
SUMMARY_KEYS = ("full_depth", "retained_depth", "tie_groups", "tied_documents", "tie_excess",
                "supplied_rank_disagreements", "retained_order")


def interval(lower=Fraction(0), lower_closed=True, upper=None, upper_closed=None):
    return {"lower": core.rational(lower), "lower_closed": lower_closed,
            "upper": None if upper is None else core.rational(upper), "upper_closed": upper_closed}


def interval_feasible(bounds):
    lower = Fraction(bounds["lower"])
    upper = None if bounds["upper"] is None else Fraction(bounds["upper"])
    return upper is None or lower < upper or (lower == upper and bounds["lower_closed"] and bounds["upper_closed"])


def scalar_interval(head, a, s, universe):
    """Intersect exact head/nonhead inequalities; preserve active witnesses."""
    head, universe = set(head), set(universe)
    outside = sorted(head - universe)
    if outside:
        return {"feasible": False, "reason": "coverage", "coverage_outside": outside,
                "interval": None, "lower_witness": None, "upper_witness": None,
                "zero_slope_witness": None, "pareto_witness": None, "constraint_count": 0}
    lower, upper, lower_closed, upper_closed = Fraction(0), None, True, None
    lower_witness, upper_witness = {"kind": "nonnegative_weight"}, None
    zero_witness, pareto, count = None, None, 0
    for x in sorted(head):
        for y in sorted(universe - head):
            ax, ay, sx, sy = (Fraction(a.get(x, 0)), Fraction(a.get(y, 0)),
                              Fraction(s.get(x, 0)), Fraction(s.get(y, 0)))
            delta, rhs, strict = ax - ay, sy - sx, y < x
            threshold = rhs / delta if delta else None
            witness = {"head": x, "excluded": y, "delta_a": core.rational(delta),
                       "rhs": core.rational(rhs), "strict": strict,
                       "threshold": None if threshold is None else core.rational(threshold)}
            count += 1
            if pareto is None and ay > ax and sy > sx:
                pareto = {"head": x, "excluded": y}
            if not delta:
                if zero_witness is None and (rhs > 0 or (rhs == 0 and strict)):
                    zero_witness = witness
            elif delta > 0:
                if threshold > lower or (threshold == lower and strict and lower_closed):
                    lower, lower_closed, lower_witness = threshold, not strict, witness
            elif upper is None or threshold < upper or (threshold == upper and strict and upper_closed):
                upper, upper_closed, upper_witness = threshold, not strict, witness
    bounds = interval(lower, lower_closed, upper, upper_closed)
    reason = ("zero_slope" if zero_witness else
              "empty_interval" if not interval_feasible(bounds) else "feasible")
    return {"feasible": reason == "feasible", "reason": reason, "coverage_outside": outside,
            "interval": bounds, "lower_witness": lower_witness, "upper_witness": upper_witness,
            "zero_slope_witness": zero_witness, "pareto_witness": pareto, "constraint_count": count}


def common_scalar_interval(results):
    infeasible = [qid for qid, result in results.items() if not result["feasible"]]
    if infeasible:
        return {"feasible": False, "reason": "query_infeasible", "infeasible_query_ids": infeasible,
                "interval": None, "lower_witness": None, "upper_witness": None}
    lower, upper, lower_closed, upper_closed = Fraction(0), None, True, None
    lower_witness = upper_witness = None
    for qid, result in results.items():
        bounds = result["interval"]
        candidate_lower = Fraction(bounds["lower"])
        if (lower_witness is None or candidate_lower > lower or
                (candidate_lower == lower and not bounds["lower_closed"] and lower_closed)):
            lower, lower_closed = candidate_lower, bounds["lower_closed"]
            lower_witness = {"qid": qid, "witness": result["lower_witness"]}
        if bounds["upper"] is not None:
            candidate_upper = Fraction(bounds["upper"])
            if (upper is None or candidate_upper < upper or
                    (candidate_upper == upper and not bounds["upper_closed"] and upper_closed)):
                upper, upper_closed = candidate_upper, bounds["upper_closed"]
                upper_witness = {"qid": qid, "witness": result["upper_witness"]}
    bounds = interval(lower, lower_closed, upper, upper_closed)
    feasible = interval_feasible(bounds)
    return {"feasible": feasible, "reason": "feasible" if feasible else "empty_common",
            "infeasible_query_ids": [], "interval": bounds,
            "lower_witness": lower_witness, "upper_witness": upper_witness}


def component(a_rank, variant_rank):
    a = Fraction(1, 60 + a_rank) if a_rank is not None else Fraction()
    variant = Fraction(1, 60 + variant_rank) if variant_rank is not None else Fraction()
    category = ("shared" if a_rank is not None and variant_rank is not None else
                "arrival" if variant_rank is not None else "departure" if a_rank is not None else "absent")
    return {"category": category, "value": core.rational((variant - a) / 3)}


def build_query(sources):
    core.require(set(sources) == set(SOURCES), "source inventory differs")
    for name, source in sources.items():
        core.require(100 <= source["full_depth"] <= 1000 and len(source["retained_order"]) == 100,
                     "source depth outside frozen bounds: " + name)
    ranks = {name: {doc: rank for rank, doc in enumerate(source["retained_order"], 1)}
             for name, source in sources.items()}
    union = set().union(*(set(ranks[name]) for name in SOURCES))
    original_pool = set(ranks["A"]) | set(ranks["S"])
    reciprocal = {name: {doc: Fraction(1, 60 + rank) for doc, rank in ranks[name].items()} for name in SOURCES}
    candidates, h_scores, f_scores = [], {}, {}
    for doc in sorted(union):
        values = {name: reciprocal[name].get(doc, Fraction()) for name in SOURCES}
        h = values["A"] + values["S"]
        f = (values["A"] + values["D"] + values["T"]) / 3 + values["S"]
        doc_ranks = {name: ranks[name].get(doc) for name in SOURCES}
        decomposition = {variant: component(doc_ranks["A"], doc_ranks[variant]) for variant in ("D", "T")}
        core.require(sum((Fraction(term["value"]) for term in decomposition.values()), Fraction()) == f - h,
                     "score decomposition identity failed")
        h_scores[doc], f_scores[doc] = h, f
        candidates.append({"docid": doc, "ranks": doc_ranks,
                           "contributions": {name: core.rational(value) for name, value in values.items()},
                           "H": core.rational(h), "F": core.rational(f), "delta": core.rational(f - h),
                           "in_original_pool": doc in original_pool, "decomposition": decomposition})
    policies = {name: sources[name]["retained_order"][:10] for name in SOURCES}
    policies.update(H=sorted(union, key=lambda doc: (-h_scores[doc], doc))[:10],
                    F=sorted(union, key=lambda doc: (-f_scores[doc], doc))[:10])
    entrants = sorted(set(policies["F"]) - set(policies["H"]))
    exits = sorted(set(policies["H"]) - set(policies["F"]))
    core.require(len(entrants) == len(exits), "unequal exchange cardinalities")
    return {"sources": {name: {key: sources[name][key] for key in SUMMARY_KEYS} for name in SOURCES},
            "candidate_ids": sorted(union), "original_candidate_ids": sorted(original_pool),
            "policies": policies, "candidates": candidates, "entrants": entrants, "exits": exits,
            "changed_slots": len(entrants),
            "scalar": scalar_interval(policies["F"], reciprocal["A"], reciprocal["S"], original_pool)}


def build_policies(runs, historical, query_ids=core.QUERY_IDS):
    core.require(all(set(run) == set(query_ids) for run in runs.values()), "run cohort differs")
    queries, totals = {}, {variant: {category: Fraction() for category in CATEGORIES} for variant in ("D", "T")}
    for qid in query_ids:
        query = build_query({name: runs[name][qid] for name in SOURCES})
        for policy in ("A", "S", "H"):
            core.require(query["policies"][policy] == historical["queries"][qid]["policies"][policy],
                         f"historical {policy} top ten differ on query {qid}")
        for row in query["candidates"]:
            for variant, term in row["decomposition"].items():
                totals[variant][term["category"]] += Fraction(term["value"])
        queries[qid] = query
    changed = sum(query["changed_slots"] for query in queries.values())
    scalars = {qid: query["scalar"] for qid, query in queries.items()}
    return {"schema": 1, "query_ids": list(query_ids), "queries": queries,
            "decomposition_totals": {variant: {category: core.rational(value) for category, value in terms.items()}
                                     for variant, terms in totals.items()},
            "structural": {"changed_slots_total": changed,
                           "changed_query_count": sum(query["changed_slots"] > 0 for query in queries.values()),
                           "absolute_effect_bound": core.rational(Fraction(changed, 10 * len(query_ids))),
                           "scalar": {"per_query_feasible_count": sum(row["feasible"] for row in scalars.values()),
                                      "coverage_failure_count": sum(bool(row["coverage_outside"]) for row in scalars.values()),
                                      "pareto_witness_count": sum(row["pareto_witness"] is not None for row in scalars.values()),
                                      "common": common_scalar_interval(scalars)}}}


def analyze(policies, labels):
    qids = policies["query_ids"]
    core.require(set(qids) == set(labels), "label cohort differs")
    per_query, ledger = {}, []
    for qid in qids:
        query, grades = policies["queries"][qid], labels[qid]
        per_query[qid] = {
            "contrasts": {left + "-" + right: core.contrast_bounds(query["policies"][left], query["policies"][right], grades)
                          for left, right in CONTRASTS},
            "benchmark": {name: core.rational(Fraction(sum(grades.get(doc, 0) > 0 for doc in head), 10))
                          for name, head in query["policies"].items()},
        }
        candidates = {row["docid"]: row for row in query["candidates"]}
        for role, documents, coefficient in (("entrant", query["entrants"], "1/10"), ("exit", query["exits"], "-1/10")):
            for doc in documents:
                row = candidates[doc]
                ledger.append({"qid": qid, "role": role, "docid": doc, "ranks": row["ranks"],
                               "grade": grades.get(doc), "in_original_pool": row["in_original_pool"],
                               "coefficient": coefficient})
    contrasts = {left + "-" + right: core.average_bounds(
        [per_query[qid]["contrasts"][left + "-" + right] for qid in qids]) for left, right in CONTRASTS}
    counts = {}
    for role in ("entrant", "exit"):
        rows = [row for row in ledger if row["role"] == role]
        counts.update({role + "_total": len(rows), role + "_known_positive": sum(row["grade"] in (1, 2) for row in rows),
                       role + "_explicit_negative": sum(row["grade"] == 0 for row in rows),
                       role + "_unknown": sum(row["grade"] is None for row in rows)})
    counts["entrant_outside_original_pool"] = sum(row["role"] == "entrant" and not row["in_original_pool"] for row in ledger)
    absolute = Fraction(policies["structural"]["absolute_effect_bound"])
    core.require(-absolute <= Fraction(contrasts["F-H"]["lower"]) <= Fraction(contrasts["F-H"]["upper"]) <= absolute,
                 "changed-slot bound violated")
    benchmark = {name: core.rational(sum((Fraction(per_query[qid]["benchmark"][name]) for qid in qids), Fraction()) / len(qids))
                 for name in POLICIES}
    return {"schema": 1, "query_count": len(qids), "contrasts": contrasts, "per_query": per_query,
            "benchmark": {"convention": "binary P@10 with unknown labels assigned zero", "policies": benchmark},
            "exchange_ledger": ledger, "exchange_counts": counts, "primary_decision": contrasts["F-H"]["decision"]}


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
        stream.write("\n")


def artifact_path(path):
    """Serialize checkout-contained custody paths without machine-specific roots."""
    path = Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def input_custody(preflight_path, acquisition_path, inputs_dir):
    tracked = {}
    def track(path):
        path = Path(path).resolve()
        observed = core.identity(path)
        core.require(str(path) not in tracked or tracked[str(path)] == observed, "conflicting file identity")
        tracked[str(path)] = observed
        return observed
    preflight_path, acquisition_path = Path(preflight_path).resolve(), Path(acquisition_path).resolve()
    track(preflight_path)
    preflight = core.read_json(preflight_path)
    core.require(preflight.get("status") == "passed", "preflight did not pass")
    frozen = preflight["frozen"]
    core.require(REQUIRED_FROZEN <= set(frozen), "missing required frozen dependency")
    for name, digest in frozen.items():
        path = (ROOT / name).resolve()
        core.require(path.is_relative_to(ROOT) and not Path(name).is_absolute(), "frozen path escapes repository")
        core.require(track(path)["sha256"] == digest, "frozen identity changed: " + name)
    core.require(frozen[HISTORICAL] == HISTORICAL_SHA256, "historical policy pin differs")
    plan = core.read_json(ROOT / PLAN)
    inputs = {}
    core.require(set(plan["cached"]) == {"A.run", "S.run", "docids.txt", "late.qrels"}, "cached input inventory differs")
    for name, expected in plan["cached"].items():
        path = (ROOT / expected["path"]).resolve()
        core.require(path.is_relative_to(ROOT), "cached path escapes repository")
        observed = track(path)
        core.require(observed == {key: expected[key] for key in ("bytes", "sha256")}, "cached input changed: " + name)
        inputs[name] = {"path": str(path), **observed}
    track(acquisition_path)
    receipt = core.read_json(acquisition_path)
    core.require(receipt.get("status") == "passed" and receipt.get("frozen") == frozen, "acquisition preflight differs or failed")
    core.require(set(receipt["inputs"]) == {"D.run", "T.run"}, "acquisition inventory differs")
    total = 0
    for key in ("D", "T"):
        spec = plan["items"][key]
        name = key + ".run"
        core.require(spec["filename"] == name, "new input filename differs")
        path = (Path(inputs_dir) / name).resolve()
        observed = track(path)
        core.require(observed == {field: receipt["inputs"][name][field] for field in ("bytes", "sha256")}, "acquired input changed: " + name)
        core.require(observed["bytes"] == spec["expected_bytes"] and observed["bytes"] <= spec["max_bytes"], "acquired byte bounds failed")
        inputs[name] = {"path": str(path), **observed}
        total += observed["bytes"]
    core.require(total <= plan["max_total_bytes"], "acquisition total byte cap exceeded")
    return frozen, inputs, tracked


def produce(args, output):
    frozen, inputs, tracked = input_custody(args.preflight, args.acquisition, args.inputs)
    docids = doc_parser.parse_docids(Path(inputs["docids.txt"]["path"]).read_text(encoding="utf-8"))
    runs = {name: run_parser.parse_run(Path(inputs[name + ".run"]["path"]).read_text(encoding="utf-8"), docids)
            for name in SOURCES}
    policies = build_policies(runs, core.read_json(ROOT / HISTORICAL))
    write_json(output / "policies.json", policies)
    # Save and hash every ranking and label-free structural diagnostic before joining labels.
    policy_identity = core.identity(output / "policies.json")
    tracked[str((output / "policies.json").resolve())] = policy_identity
    core.verify_tracked(tracked)
    labels = label_parser.parse_qrels(Path(inputs["late.qrels"]["path"]).read_text(encoding="utf-8"), docids)
    write_json(output / "analysis.json", analyze(policies, labels))
    after = core.verify_tracked(tracked)
    manifest = {"schema": 1, "phase": "cycle18", "command": sys.argv, "frozen": frozen,
                "inputs": {name: {**value, "path": artifact_path(value["path"])} for name, value in inputs.items()},
                "preflight": artifact_path(args.preflight), "acquisition": artifact_path(args.acquisition),
                "tracked_before": {artifact_path(path): value for path, value in tracked.items()},
                "tracked_after": {artifact_path(path): value for path, value in after.items()},
                "labels_joined_after_policies_sha256": policy_identity["sha256"],
                "outputs": {name: core.identity(output / name) for name in ("policies.json", "analysis.json")}}
    write_json(output / "manifest.json", manifest)
    write_json(output / "success.json", {"status": "passed", "manifest": core.identity(output / "manifest.json")})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("preflight", "acquisition", "inputs", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    created, started = False, time.monotonic()
    def timeout(signum, frame):
        raise core.ContractError("cycle18 exceeded 300 seconds")
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    try:
        output.mkdir(parents=True, exist_ok=False)
        created = True
        produce(args, output)
        print(json.dumps({"status": "passed", "output": str(output)}))
        return 0
    except Exception as exc:
        failure = {"status": "failed", "phase": "cycle18", "error_type": type(exc).__name__, "error": str(exc),
                   "command": sys.argv, "elapsed_seconds": time.monotonic() - started}
        path = output / "failure.json" if created else output.parent / (output.name + f".failure-{time.time_ns()}.json")
        try:
            write_json(path, failure)
            failure["failure_artifact"] = str(path)
        except OSError as error:
            failure["failure_artifact_error"] = str(error)
        print(json.dumps(failure), file=sys.stderr)
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == "__main__":
    raise SystemExit(main())
