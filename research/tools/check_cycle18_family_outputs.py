#!/usr/bin/env python3
"""Independent Cycle18 reconstruction: own parsers, integer RRF, set bounds.

No Cycle18 producer or Cycle17 parser/analysis implementation is imported.
Actual new source files must remain unopened until coordinator execution GO.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import signal
import sys
import tempfile
import time
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "_sessions/cycles/2026-09-25-cycle18-protocol.md"
PLAN = ROOT / "_sessions/cycles/2026-09-25-cycle18-input-plan.json"
QIDS = [str(i) for i in range(1, 31)]
SOURCES = ("A", "D", "T", "S")
POLICIES = ("A", "D", "T", "S", "H", "F")
CONTRASTS = ("F-H", "F-S", "F-A", "F-D", "F-T", "H-S")
CATEGORIES = ("shared", "arrival", "departure", "absent")
LCM = math.lcm(*range(61, 161))


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def ratio(value):
    value = Fraction(value)
    return f"{value.numerator}/{value.denominator}"


def json_read(path):
    return json.loads(Path(path).read_text())


def identity(path):
    data = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def exact(actual, expected, path="root"):
    if isinstance(expected, dict):
        need(isinstance(actual, dict), f"{path}: object required")
        need(actual.keys() == expected.keys(), f"{path}: keys differ")
        for key in expected:
            exact(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        need(isinstance(actual, list) and len(actual) == len(expected), f"{path}: list length/type")
        for i, (a, b) in enumerate(zip(actual, expected)):
            exact(a, b, f"{path}[{i}]")
    else:
        need(type(actual) is type(expected) and actual == expected, f"{path}: value/type differs")


def inventory(path):
    lines = Path(path).read_bytes().split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    need(bool(lines), "empty ID inventory")
    for line in lines:
        need(line and line.strip(b" "), "empty inventory key")
        need(all(32 <= b <= 126 for b in line), "non-printable inventory key")
    return {line.decode("ascii") for line in lines}


def decimal_value(token, context):
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {context}") from exc
    need(value.is_finite(), f"nonfinite {context}")
    return value


def run_read(path, allowed):
    """Decode all rows, then compare exact numeric scores without context rounding."""
    rows = {q: {} for q in QIDS}
    tags = set()
    for line_number, line in enumerate(Path(path).read_text().splitlines(), 1):
        fields = line.split()
        need(len(fields) == 6, f"run fields at {path}:{line_number}")
        q, q0, doc, supplied, score, tag = fields
        need(q in rows and q0 == "Q0", "run query/Q0")
        need(doc in allowed and doc not in rows[q], "run unknown or repeated document")
        need(supplied.isascii() and supplied.isdigit(), "nonnegative supplied rank required")
        rows[q][doc] = (decimal_value(score, "source score"), int(supplied))
        tags.add(tag)
    need(len(tags) == 1, "run tags inconsistent")
    parsed = {}
    for q, documents in rows.items():
        need(100 <= len(documents) <= 1000, f"source depth invalid for topic {q}")
        order = sorted(documents, key=lambda d: (documents[d][0].copy_negate(), d))
        ties = Counter(score for score, _ in documents.values())
        tie_sizes = [n for n in ties.values() if n > 1]
        parsed[q] = {
            "full_depth": len(order), "retained_depth": 100,
            "tie_groups": len(tie_sizes), "tied_documents": sum(tie_sizes),
            "tie_excess": sum(n - 1 for n in tie_sizes),
            "supplied_rank_disagreements": sum(documents[d][1] != i for i, d in enumerate(order, 1)),
            "retained_order": order[:100],
        }
    return parsed


def labels_read(path):
    labels = {q: {} for q in QIDS}
    for line_number, line in enumerate(Path(path).read_text().splitlines(), 1):
        fields = line.split()
        need(len(fields) == 4, f"qrel fields at {path}:{line_number}")
        q, round_text, doc, grade = fields
        need(q in labels, "qrel query")
        need(doc and all(33 <= ord(c) <= 126 for c in doc), "qrel document token")
        need(doc not in labels[q], "duplicate qrel pair")
        need(decimal_value(round_text, "judgment round") > 0, "nonpositive judgment round")
        need(grade in ("0", "1", "2"), "qrel grade domain")
        labels[q][doc] = int(grade)
    need(all(labels[q] for q in QIDS), "qrel topic cohort incomplete")
    return labels


def integer_vectors(source_orders):
    ranks = {p: {d: r for r, d in enumerate(source_orders[p], 1)} for p in SOURCES}
    candidates = sorted(set().union(*(set(r) for r in ranks.values())))
    units = {p: {d: LCM // (60 + r) for d, r in ranks[p].items()} for p in SOURCES}
    old_pool = sorted(set(ranks["A"]) | set(ranks["S"]))
    h = {d: 3 * units["A"].get(d, 0) + 3 * units["S"].get(d, 0) for d in candidates}
    f = {d: sum(units[p].get(d, 0) for p in ("A", "D", "T")) +
         3 * units["S"].get(d, 0) for d in candidates}
    h_order = sorted(candidates, key=lambda d: (-h[d], d))
    f_order = sorted(candidates, key=lambda d: (-f[d], d))
    return ranks, units, candidates, old_pool, h, f, h_order, f_order


def intersect_scalar(head, old_pool, au, su):
    """Intersect linear inequalities using independent integer coefficient vectors."""
    outside = sorted(set(head) - set(old_pool))
    if outside:
        return {"feasible": False, "lower": Fraction(0), "lower_open": False,
                "upper": None, "upper_open": False, "outside": outside,
                "lower_sources": [], "upper_sources": [], "zero_failures": [], "pareto": [],
                "constraint_count": 0}
    lower, lower_open, upper, upper_open = Fraction(0), False, None, False
    lower_sources, upper_sources, zero_failures, pareto = [], [], [], []
    excluded = sorted(set(old_pool) - set(head))
    for x in sorted(set(head)):
        for y in excluded:
            slope = au.get(x, 0) - au.get(y, 0)
            rhs = su.get(y, 0) - su.get(x, 0)
            strict = y < x
            witness = {"head": x, "nonhead": y, "slope": slope, "rhs": rhs, "strict": strict}
            if au.get(y, 0) > au.get(x, 0) and su.get(y, 0) > su.get(x, 0):
                pareto.append(witness)
            if slope == 0:
                if rhs > 0 or (rhs == 0 and strict):
                    zero_failures.append(witness)
            elif slope > 0:
                boundary = Fraction(rhs, slope)
                if boundary > lower:
                    lower, lower_open, lower_sources = boundary, strict, [witness]
                elif boundary == lower:
                    lower_open = lower_open or strict
                    lower_sources.append(witness)
            else:
                boundary = Fraction(rhs, slope)
                if upper is None or boundary < upper:
                    upper, upper_open, upper_sources = boundary, strict, [witness]
                elif boundary == upper:
                    upper_open = upper_open or strict
                    upper_sources.append(witness)
    feasible = not outside and not zero_failures and (
        upper is None or lower < upper or (lower == upper and not lower_open and not upper_open))
    return {"feasible": feasible, "lower": lower, "lower_open": lower_open,
            "upper": upper, "upper_open": upper_open, "outside": outside,
            "lower_sources": lower_sources, "upper_sources": upper_sources,
            "zero_failures": zero_failures, "pareto": pareto,
            "constraint_count": len(set(head)) * len(excluded)}


def constraint_schema(witness):
    return {"head": witness["head"], "excluded": witness["nonhead"],
            "delta_a": ratio(Fraction(witness["slope"], LCM)),
            "rhs": ratio(Fraction(witness["rhs"], LCM)), "strict": witness["strict"],
            "threshold": ratio(Fraction(witness["rhs"], witness["slope"])) if witness["slope"] else None}


def interval_schema(result):
    return {"lower": ratio(result["lower"]), "lower_closed": not result["lower_open"],
            "upper": ratio(result["upper"]) if result["upper"] is not None else None,
            "upper_closed": not result["upper_open"] if result["upper"] is not None else None}


def scalar_schema(result):
    if result["outside"]:
        return {"feasible": False, "reason": "coverage", "coverage_outside": result["outside"],
                "interval": None, "lower_witness": None, "upper_witness": None,
                "zero_slope_witness": None, "pareto_witness": None, "constraint_count": 0}
    if result["lower_open"]:
        lower = constraint_schema(next(x for x in result["lower_sources"] if x["strict"]))
    elif result["lower"] == 0:
        lower = {"kind": "nonnegative_weight"}
    else:
        lower = constraint_schema(result["lower_sources"][0])
    if result["upper"] is None:
        upper = None
    elif result["upper_open"]:
        upper = constraint_schema(next(x for x in result["upper_sources"] if x["strict"]))
    else:
        upper = constraint_schema(result["upper_sources"][0])
    reason = ("coverage" if result["outside"] else "zero_slope" if result["zero_failures"]
              else "feasible" if result["feasible"] else "empty_interval")
    return {"feasible": result["feasible"], "reason": reason,
            "coverage_outside": result["outside"], "interval": interval_schema(result),
            "lower_witness": lower, "upper_witness": upper,
            "zero_slope_witness": constraint_schema(result["zero_failures"][0]) if result["zero_failures"] else None,
            "pareto_witness": {"head": result["pareto"][0]["head"], "excluded": result["pareto"][0]["nonhead"]}
                              if result["pareto"] else None,
            "constraint_count": result["constraint_count"]}


def common_scalar(scalars):
    infeasible = [q for q in QIDS if not scalars[q]["feasible"]]
    if infeasible:
        return {"feasible": False, "reason": "query_infeasible", "infeasible_query_ids": infeasible,
                "interval": None, "lower_witness": None, "upper_witness": None}
    lower, lower_open, upper, upper_open = Fraction(0), False, None, False
    lower_witness, upper_witness = None, None
    for q in QIDS:
        row = scalars[q]
        lo, hi = Fraction(row["interval"]["lower"]), row["interval"]["upper"]
        lo_open = not row["interval"]["lower_closed"]
        if lower_witness is None or lo > lower or (lo == lower and lo_open and not lower_open):
            lower, lower_open = lo, lo_open
            lower_witness = {"qid": q, "witness": row["lower_witness"]}
        if hi is not None:
            hi = Fraction(hi)
            hi_open = not row["interval"]["upper_closed"]
            if upper is None or hi < upper or (hi == upper and hi_open and not upper_open):
                upper, upper_open = hi, hi_open
                upper_witness = {"qid": q, "witness": row["upper_witness"]}
    feasible = upper is None or lower < upper or (lower == upper and not lower_open and not upper_open)
    return {"feasible": feasible, "reason": "feasible" if feasible else "empty_common",
            "infeasible_query_ids": [], "interval": interval_schema({"lower": lower, "upper": upper,
              "lower_open": lower_open, "upper_open": upper_open}),
            "lower_witness": lower_witness, "upper_witness": upper_witness}


def own_policy_queries(sources):
    queries, scalar_internal = {}, {}
    totals = {p: {category: Fraction() for category in CATEGORIES} for p in ("D", "T")}
    for q in QIDS:
        orders = {p: sources[p][q]["retained_order"] for p in SOURCES}
        ranks, units, candidates, old_pool, h, f, h_order, f_order = integer_vectors(orders)
        policies = {p: orders[p][:10] for p in SOURCES} | {"H": h_order[:10], "F": f_order[:10]}
        candidate_rows = []
        for doc in candidates:
            decomposition = {}
            for p in ("D", "T"):
                a_present, p_present = doc in ranks["A"], doc in ranks[p]
                category = ("shared" if a_present and p_present else "arrival" if p_present
                            else "departure" if a_present else "absent")
                value = Fraction(units[p].get(doc, 0) - units["A"].get(doc, 0), 3 * LCM)
                decomposition[p] = {"category": category, "value": ratio(value)}
                totals[p][category] += value
            delta = Fraction(f[doc] - h[doc], 3 * LCM)
            need(sum((Fraction(x["value"]) for x in decomposition.values()), Fraction()) == delta,
                 "independent decomposition identity")
            candidate_rows.append({
                "docid": doc, "ranks": {p: ranks[p].get(doc) for p in SOURCES},
                "contributions": {p: ratio(Fraction(units[p].get(doc, 0), LCM)) for p in SOURCES},
                "H": ratio(Fraction(h[doc], 3 * LCM)), "F": ratio(Fraction(f[doc], 3 * LCM)),
                "delta": ratio(delta), "in_original_pool": doc in old_pool,
                "decomposition": decomposition,
            })
        entrants = sorted(set(policies["F"]) - set(policies["H"]))
        exits = sorted(set(policies["H"]) - set(policies["F"]))
        need(len(entrants) == len(exits), "unequal exchanges")
        scalar_internal[q] = intersect_scalar(policies["F"], old_pool, units["A"], units["S"])
        queries[q] = {"sources": {p: sources[p][q] for p in SOURCES},
                      "candidate_ids": candidates, "original_candidate_ids": old_pool,
                      "policies": policies, "candidates": candidate_rows,
                      "entrants": entrants, "exits": exits, "changed_slots": len(entrants)}
    return queries, scalar_internal, {p: {c: ratio(v) for c, v in t.items()} for p, t in totals.items()}


def signs(lo, hi):
    if lo > 0:
        return "strict_positive", "all_completions_positive"
    if hi < 0:
        return "strict_negative", "positive_excluded"
    if lo == hi == 0:
        return "point_zero", "positive_excluded"
    if hi == 0:
        return "nonpositive_with_zero", "positive_excluded"
    if lo == 0:
        return "nonnegative_with_zero", "sign_unresolved"
    return "crosses_zero", "sign_unresolved"


def canceled_bound(left, right, labels):
    added, removed = set(left) - set(right), set(right) - set(left)
    known = Fraction(sum(labels[d] > 0 for d in added if d in labels) -
                     sum(labels[d] > 0 for d in removed if d in labels), 10)
    missing_plus, missing_minus = len(added - labels.keys()), len(removed - labels.keys())
    lower, upper = known - Fraction(missing_minus, 10), known + Fraction(missing_plus, 10)
    sign, decision = signs(lower, upper)
    return {"known": ratio(known), "benchmark_zero": ratio(known), "lower": ratio(lower),
            "upper": ratio(upper), "width": ratio(upper - lower), "unknown_support": missing_plus + missing_minus,
            "sign": sign, "decision": decision,
            "support": [{"docid": d, "coefficient": "1/10" if d in added else "-1/10", "grade": labels.get(d)}
                        for d in sorted(added | removed)]}


def policies_schema(queries, scalars, totals):
    out = {q: row | {"scalar": scalar_schema(scalars[q])} for q, row in queries.items()}
    d = sum(row["changed_slots"] for row in queries.values())
    formatted_scalars = {q: out[q]["scalar"] for q in QIDS}
    return {
        "schema": 1, "query_ids": QIDS, "queries": out,
        "structural": {"changed_slots_total": d,
                       "changed_query_count": sum(bool(row["changed_slots"]) for row in queries.values()),
                       "absolute_effect_bound": ratio(Fraction(d, 300)),
                       "scalar": {"per_query_feasible_count": sum(x["feasible"] for x in formatted_scalars.values()),
                                  "coverage_failure_count": sum(bool(x["coverage_outside"]) for x in formatted_scalars.values()),
                                  "pareto_witness_count": sum(x["pareto_witness"] is not None for x in formatted_scalars.values()),
                                  "common": common_scalar(formatted_scalars)}},
        "decomposition_totals": totals,
    }


def analyze(queries, labels):
    per_query, ledger = {}, []
    counts = dict.fromkeys(("entrant_total", "exit_total", "entrant_known_positive", "entrant_explicit_negative",
                           "entrant_unknown", "exit_known_positive", "exit_explicit_negative", "exit_unknown",
                           "entrant_outside_original_pool"), 0)
    for q in QIDS:
        row = queries[q]
        qpolicies = row["policies"]
        per_query[q] = {
            "contrasts": {name: canceled_bound(qpolicies[name.split("-")[0]], qpolicies[name.split("-")[1]], labels[q])
                          for name in CONTRASTS},
            "benchmark": {p: ratio(Fraction(sum(labels[q].get(d, 0) > 0 for d in qpolicies[p]), 10)) for p in POLICIES},
        }
        candidates = {x["docid"]: x for x in row["candidates"]}
        for role, docs in (("entrant", row["entrants"]), ("exit", row["exits"])):
            for doc in docs:
                candidate = candidates[doc]
                grade = labels[q].get(doc)
                ledger.append({"qid": q, "role": role, "docid": doc, "ranks": candidate["ranks"],
                               "grade": grade, "in_original_pool": candidate["in_original_pool"],
                               "coefficient": "1/10" if role == "entrant" else "-1/10"})
                counts[f"{role}_total"] += 1
                suffix = "unknown" if grade is None else "known_positive" if grade > 0 else "explicit_negative"
                counts[f"{role}_{suffix}"] += 1
                if role == "entrant" and not candidate["in_original_pool"]:
                    counts["entrant_outside_original_pool"] += 1
    aggregate = {}
    for name in CONTRASTS:
        values = {key: sum((Fraction(per_query[q]["contrasts"][name][key]) for q in QIDS), Fraction()) / 30
                  for key in ("known", "benchmark_zero", "lower", "upper", "width")}
        sign, decision = signs(values["lower"], values["upper"])
        aggregate[name] = {key: ratio(value) for key, value in values.items()} | {
            "sign": sign, "decision": decision, "query_count": 30,
            "unknown_support": sum(per_query[q]["contrasts"][name]["unknown_support"] for q in QIDS)}
    means = {p: ratio(sum((Fraction(per_query[q]["benchmark"][p]) for q in QIDS), Fraction()) / 30) for p in POLICIES}
    return {"schema": 1, "query_count": 30, "contrasts": aggregate, "per_query": per_query,
            "benchmark": {"convention": "binary P@10 with unknown labels assigned zero", "policies": means},
            "exchange_ledger": ledger, "exchange_counts": counts, "primary_decision": aggregate["F-H"]["decision"]}


def artifact_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def custody(args):
    preflight, acquisition = json_read(args.preflight), json_read(args.acquisition)
    need(preflight["schema"] == 1 and preflight["status"] == "passed", "preflight not passed")
    need(acquisition["schema"] == 1 and acquisition["status"] == "passed" and
         acquisition["phase"] == "initial", "acquisition not passed")
    exact(acquisition["frozen"], preflight["frozen"], "acquisition source freeze")
    need(acquisition["preflight_sha256"] == identity(args.preflight)["sha256"], "acquisition preflight hash")
    required = {str(p.relative_to(ROOT)) for p in (PROTOCOL, PLAN, Path(__file__).resolve())}
    historical = ROOT / "results/cycle17-2026-09-25/final/prepared/policies.json"
    required.add(str(historical.relative_to(ROOT)))
    need(required <= preflight["frozen"].keys(), "mandatory verifier/protocol/plan/history not frozen")
    for name, digest in preflight["frozen"].items():
        need(identity(artifact_path(name))["sha256"] == digest, f"frozen file changed: {name}")
    plan = json_read(PLAN)
    paths, input_identities = {}, {}
    for name, info in plan["cached"].items():
        path = artifact_path(info["path"])
        expected = {"bytes": info["bytes"], "sha256": info["sha256"]}
        exact(identity(path), expected, f"cached identity {name}")
        paths[name], input_identities[name] = path, expected
    need(set(acquisition["inputs"]) == {"D.run", "T.run"}, "new source input set")
    new_bytes = 0
    for key, item in plan["items"].items():
        name = item["filename"]
        path = args.inputs / name
        expected = acquisition["inputs"][name]
        need(expected["bytes"] == item["expected_bytes"] and expected["bytes"] <= item["max_bytes"],
             f"unexpected new source size {key}")
        exact(identity(path), expected, f"new source identity {key}")
        paths[name], input_identities[name] = path, expected
        new_bytes += expected["bytes"]
    need(new_bytes <= plan["max_total_bytes"], "new input total ceiling")
    manifest = json_read(args.result / "manifest.json")
    success = json_read(args.result / "success.json")
    need(success["status"] == "passed" and manifest["schema"] == 1 and manifest["phase"] == "cycle18",
         "producer phase did not pass")
    exact(identity(args.result / "manifest.json"), success["manifest"], "success manifest identity")
    exact(manifest["frozen"], preflight["frozen"], "manifest frozen map")
    exact(manifest["tracked_before"], manifest["tracked_after"], "producer before/after identities")
    for name, info in manifest["tracked_after"].items():
        exact(identity(artifact_path(name)), info, f"producer tracked file {name}")
    need(set(manifest["inputs"]) == set(paths), "producer input identity set")
    for name, info in manifest["inputs"].items():
        need(artifact_path(info["path"]).resolve() == paths[name].resolve(), f"input path {name}")
        exact({"bytes": info["bytes"], "sha256": info["sha256"]}, input_identities[name], f"producer input {name}")
    need(artifact_path(manifest["preflight"]).resolve() == args.preflight.resolve(), "producer preflight location")
    need(artifact_path(manifest["acquisition"]).resolve() == args.acquisition.resolve(), "producer acquisition location")
    need(set(manifest["outputs"]) == {"policies.json", "analysis.json"}, "producer output set")
    for name, info in manifest["outputs"].items():
        exact(identity(args.result / name), info, f"producer output {name}")
    need(manifest["labels_joined_after_policies_sha256"] == identity(args.result / "policies.json")["sha256"],
         "saved policy/label boundary identity")
    return {
        "paths": {k: str(v.resolve()) for k, v in paths.items()}, "input_identities": input_identities,
        "preflight": identity(args.preflight), "acquisition": identity(args.acquisition),
        "manifest": identity(args.result / "manifest.json"), "success": identity(args.result / "success.json"),
        "outputs": manifest["outputs"], "frozen": preflight["frozen"],
        "historical_policies": identity(historical), "new_input_bytes": new_bytes,
    }


def historical_check(queries):
    path = ROOT / "results/cycle17-2026-09-25/final/prepared/policies.json"
    saved = json_read(path)
    exact(saved["query_ids"], QIDS, "historical query cohort")
    for q in QIDS:
        for policy in ("A", "S", "H"):
            exact(queries[q]["policies"][policy], saved["queries"][q]["policies"][policy],
                  f"historical {q}/{policy} head")


def verify(args):
    need(not args.output.exists(), "exclusive verifier output exists")
    started = time.monotonic()
    before = custody(args)
    paths = {k: Path(v) for k, v in before["paths"].items()}
    valid = inventory(paths["docids.txt"])
    sources = {p: run_read(paths[f"{p}.run"], valid) for p in SOURCES}
    queries, scalars, totals = own_policy_queries(sources)
    historical_check(queries)
    policies = policies_schema(queries, scalars, totals)
    exact(json_read(args.result / "policies.json"), policies, "all policy artifact fields")
    labels = labels_read(paths["late.qrels"])
    analysis = analyze(queries, labels)
    exact(json_read(args.result / "analysis.json"), analysis, "all analysis artifact fields")
    after = custody(args)
    exact(after, before, "verifier before/after custody")
    elapsed = time.monotonic() - started
    need(elapsed < 300, "independent 300-second limit exceeded")
    result = {
        "schema": 1, "status": "passed", "verifier": identity(__file__),
        "method": "independent Decimal input ordering; integer LCM units; canceled-set label bounds; rational scalar constraints",
        "custody": after, "elapsed_seconds": elapsed, "self_tests": self_test(),
        "audited_fields": {"policies.json": "every field including all scalar endpoints and certificate witnesses",
                           "analysis.json": "every field including all query metrics, support labels, ledger and aggregates",
                           "historical_heads": "A, S and H ordered top10 on every query",
                           "producer_and_verifier_custody": "source, raw input, receipt and artifact hashes before/after"},
        "arithmetic": {"rrf_integer_lcm": str(LCM), "common_score_denominator": str(3 * LCM),
                       "F_numerator": "a_units+d_units+t_units+3*s_units",
                       "H_numerator": "3*a_units+3*s_units"},
        "query_count": 30, "policy_count": 6, "contrast_count": 6,
        "limits": ["No producer or Cycle17 parser/analysis implementation is imported.",
                   "Scalar feasibility is a capability diagnostic; no scalar weight is chosen or evaluated for effectiveness.",
                   "Missing-label intervals condition on the supplied official grades and are not confidence intervals.",
                   "The same development panel is reused; this is arithmetic validation, not independent performance evidence."],
    }
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": "passed", "output": str(args.output), "elapsed_seconds": elapsed,
                      "policies_all_fields": True, "analysis_all_fields": True}))


def self_test():
    assignments = 0
    for table in itertools.product((None, 0, 1), repeat=4):
        docs = ("a", "b", "c", "d")
        labels = {d: v for d, v in zip(docs, table) if v is not None}
        missing = [d for d, v in zip(docs, table) if v is None]
        result = canceled_bound(["a", "b", "c"], ["b", "d"], labels)
        values = []
        for bits in itertools.product((0, 1), repeat=len(missing)):
            full = labels | dict(zip(missing, bits))
            values.append(Fraction(full["a"] + full["c"] - full["d"], 10))
            assignments += 1
        need(Fraction(result["lower"]) == min(values) and Fraction(result["upper"]) == max(values),
             "sharp completion bounds")
    # x beats y iff w>=1; tie orientation makes that endpoint closed.
    closed = intersect_scalar(["a"], ["a", "b"], {"a": 2, "b": 1}, {"a": 0, "b": 1})
    need(closed["feasible"] and closed["lower"] == 1 and not closed["lower_open"], "closed lower bound")
    opened = intersect_scalar(["b"], ["a", "b"], {"b": 2, "a": 1}, {"b": 0, "a": 1})
    need(opened["feasible"] and opened["lower"] == 1 and opened["lower_open"], "open ID-tie lower bound")
    zero = intersect_scalar(["b"], ["a", "b"], {"a": 1, "b": 1}, {"a": 1, "b": 1})
    need(not zero["feasible"] and zero["zero_failures"], "zero slope strict tie")
    coverage = intersect_scalar(["outside"], ["a", "b"], {}, {})
    need(not coverage["feasible"] and coverage["outside"] == ["outside"], "coverage failure")
    dominated = intersect_scalar(["a"], ["a", "b"], {"a": 1, "b": 2}, {"a": 1, "b": 2})
    need(not dominated["feasible"] and dominated["pareto"], "strict Pareto certificate")
    singleton = intersect_scalar(["a"], ["a", "b", "c"], {"a": 1, "b": 0, "c": 2},
                                 {"a": 1, "b": 2, "c": 0})
    need(singleton["feasible"] and singleton["lower"] == singleton["upper"] == 1 and
         not singleton["lower_open"] and not singleton["upper_open"], "closed singleton")
    empty = intersect_scalar(["b"], ["a", "b", "c"], {"b": 1, "a": 0, "c": 2},
                             {"b": 1, "a": 2, "c": 0})
    need(not empty["feasible"] and empty["lower"] == empty["upper"] == 1 and empty["lower_open"],
         "open singleton is empty")
    lower_two = scalar_schema(intersect_scalar(["a"], ["a", "b"], {"a": 1, "b": 0}, {"a": 0, "b": 2}))
    upper_one = scalar_schema(intersect_scalar(["a"], ["a", "b"], {"a": 0, "b": 1}, {"a": 1, "b": 0}))
    independent_intervals = {q: lower_two if q == "1" else upper_one for q in QIDS}
    need(all(x["feasible"] for x in independent_intervals.values()) and
         common_scalar(independent_intervals)["reason"] == "empty_common", "common vs query-dependent interval")
    order = [f"d{i:03d}" for i in range(100)]
    identical_sources = {p: {q: {"retained_order": order.copy()} for q in QIDS} for p in SOURCES}
    queries, _, totals = own_policy_queries(identical_sources)
    need(all(x["policies"]["F"] == x["policies"]["H"] and x["changed_slots"] == 0 for x in queries.values()),
         "identical variants preserve hybrid")
    need(all(Fraction(value) == 0 for t in totals.values() for value in t.values()), "zero decomposition")
    for q in QIDS:
        identical_sources["D"][q]["retained_order"][-2:] = reversed(order[-2:])
    changed, _, _ = own_policy_queries(identical_sources)
    need(all(x["changed_slots"] == 0 and any(Fraction(c["delta"]) != 0 for c in x["candidates"])
             for x in changed.values()), "score change without head change")
    with tempfile.TemporaryDirectory(prefix="cycle18-independent-synthetic-") as temporary:
        directory = Path(temporary)
        inventory_path = directory / "docids.txt"
        inventory_path.write_bytes(b"same\nsame\nopaque word\n")
        need(inventory(inventory_path) == {"same", "opaque word"}, "opaque ID semantics")
        run_path = directory / "run.txt"
        scores = ["2.0", "2.00", "1." + "0" * 30 + "1", "1." + "0" * 30 + "2"] + ["0"] * 96
        rows = [f"{q} Q0 {d} {i} {scores[i]} synthetic" for q in QIDS for i, d in enumerate(order)]
        run_path.write_text("\n".join(rows) + "\n")
        parsed = run_read(run_path, set(order))
        need(parsed["1"]["retained_order"][:4] == ["d000", "d001", "d003", "d002"],
             "exact Decimal and ID tie canonical sorting")
        run_path.write_text("\n".join(rows + [rows[0]]) + "\n")
        try:
            run_read(run_path, set(order))
        except ValueError:
            pass
        else:
            raise ValueError("duplicate source pair accepted")
        labels_path = directory / "labels.txt"
        labels_path.write_text("".join(f"{q} 0.5 outside_inventory 2\n" for q in QIDS))
        parsed_labels = labels_read(labels_path)
        need(all(x == {"outside_inventory": 2} for x in parsed_labels.values()), "literal qrel retention")
    return {"partial_label_tables": 81, "binary_completions": assignments,
            "scalar_closed_open_zero_coverage_pareto": True,
            "scalar_singleton_empty_and_common_intersection": True,
            "identical_variants_and_decomposition": True, "changed_scores_unchanged_heads": True,
            "exact_decimal_sorting_ties_nonnegative_ranks": True, "opaque_ids_literal_qrels": True,
            "duplicate_rejection": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--result", type=Path)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--acquisition", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
    else:
        for field in ("result", "preflight", "acquisition", "inputs", "output"):
            if getattr(args, field) is None:
                parser.error(f"--{field} is required")
        def time_limit(signum, frame):
            raise TimeoutError("independent verifier exceeded 300 seconds")
        signal.signal(signal.SIGALRM, time_limit)
        signal.alarm(300)
        try:
            verify(args)
        except Exception as error:
            if not args.output.exists() and args.output.parent.is_dir():
                with args.output.open("x") as handle:
                    json.dump({"schema": 1, "status": "failed", "verifier": identity(__file__),
                               "command": sys.argv, "error_type": type(error).__name__,
                               "error": str(error)}, handle, indent=2, sort_keys=True)
                    handle.write("\n")
            raise
        finally:
            signal.alarm(0)


if __name__ == "__main__":
    main()
