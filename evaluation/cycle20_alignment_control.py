#!/usr/bin/env python3
"""Provisional Cycle20 label-conditioned rank-alignment intervention.

Labels construct the controls: only exact known-grade and membership-mask
strata are shuffled, preserving reciprocal mass within each support class.
Unknown document identities remain at their original source ranks. There is no
new weight, deployable control policy, label completion, or selected random draw.
"""

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import signal
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import cycle17_minority_exchange as core
from evaluation import cycle17_scoped_labels as label_parser


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "_sessions/cycles/2026-09-25-cycle20-protocol.md"
SOURCE = "evaluation/cycle20_alignment_control.py"
TESTS = "evaluation/tests/test_cycle20_alignment_control.py"
PRIOR = "results/cycle18-2026-09-25/run"
AUDIT = "results/cycle18-2026-09-25/independent-check.json"
OFFICIAL = "results/cycle18-2026-09-25/official-metric-check.json"
REQUIRED_FROZEN = {PROTOCOL, SOURCE, TESTS, AUDIT, OFFICIAL,
                   PRIOR + "/policies.json", PRIOR + "/analysis.json",
                   PRIOR + "/manifest.json", PRIOR + "/success.json",
                   "evaluation/cycle17_minority_exchange.py",
                   "evaluation/cycle17_minority_exchange_corrected.py",
                   "evaluation/cycle17_minority_exchange_compatible.py",
                   "evaluation/cycle17_scoped_labels.py"}
QUERY_IDS = core.QUERY_IDS
SOURCES = ("A", "D", "T", "S")
MEMBERSHIP_BITS = {"A": 1, "D": 2, "T": 4, "S": 8}
CONTROL_COUNT = 256
SEED = "cycle20-alignment-v2"
SEED_ENCODING = "sha256(UTF-8 compact ASCII JSON [seed,replicate:int,qid:str,source:str,grade:int,mask:int]) as unsigned big-endian integer"
SCALE = math.lcm(*range(61, 161))
RECIPROCAL = tuple(SCALE // (60 + rank) for rank in range(1, 101))
CONTRASTS = {"F-C": "natural F minus mean control F", "C-H": "mean control F minus H",
             "C-S": "mean control F minus S", "F-H": "natural F minus H", "F-S": "natural F minus S"}


def stream_seed(replicate, qid, source, grade, mask):
    payload = json.dumps([SEED, replicate, qid, source, grade, mask], ensure_ascii=True, separators=(",", ":"))
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest(), "big")


def grade_symbols(order, labels):
    return tuple(("known", labels[doc]) if doc in labels else ("unknown", doc) for doc in order)


def membership_masks(orders):
    result = {}
    for source in SOURCES:
        for doc in orders[source]:
            result[doc] = result.get(doc, 0) | MEMBERSHIP_BITS[source]
    return result


def stratum_positions(order, labels, masks):
    result = {}
    for index, doc in enumerate(order):
        if doc in labels:
            core.require(labels[doc] in (0, 1, 2), "invalid known grade")
            result.setdefault((labels[doc], masks[doc]), []).append(index)
    return dict(sorted(result.items()))


def reciprocal_mass_by_class(order, labels, masks):
    return {key: sum(RECIPROCAL[index] for index in positions)
            for key, positions in stratum_positions(order, labels, masks).items()}


def stratum_summary(order, labels, masks):
    return {"known": [{"grade": grade, "mask": mask, "size": len(positions),
                       "reciprocal_mass": core.rational(Fraction(sum(RECIPROCAL[index] for index in positions), SCALE))}
                      for (grade, mask), positions in stratum_positions(order, labels, masks).items()],
            "unknown": sum(doc not in labels for doc in order)}


def permute_order(order, labels, masks, replicate, qid, source):
    result = list(order)
    core.require(source in ("D", "T") and all(masks[doc] & MEMBERSHIP_BITS[source] for doc in order),
                 "membership mask does not include source")
    for (grade, mask), positions in stratum_positions(order, labels, masks).items():
        documents = [order[index] for index in positions]
        random.Random(stream_seed(replicate, qid, source, grade, mask)).shuffle(documents)
        for index, doc in zip(positions, documents):
            result[index] = doc
    core.require(set(result) == set(order) and len(result) == len(order), "source candidate set changed")
    core.require(grade_symbols(result, labels) == grade_symbols(order, labels), "grade or unknown-identity rank profile changed")
    core.require([masks[doc] for doc in result] == [masks[doc] for doc in order], "membership-mask rank profile changed")
    core.require(reciprocal_mass_by_class(result, labels, masks) == reciprocal_mass_by_class(order, labels, masks),
                 "reciprocal mass by grade and membership mask changed")
    return result


def integer_scores(orders, weights):
    result = {}
    for source, weight in weights.items():
        for doc, value in zip(orders[source], RECIPROCAL):
            result[doc] = result.get(doc, 0) + weight * value
    return result


def head(scores):
    return sorted(scores, key=lambda doc: (-scores[doc], doc))[:10]


def validate_natural(policies, query_ids=QUERY_IDS):
    core.require(policies["query_ids"] == list(query_ids) and set(policies["queries"]) == set(query_ids),
                 "fixed query cohort differs")
    orders = {}
    for qid in query_ids:
        query = policies["queries"][qid]
        orders[qid] = {source: list(query["sources"][source]["retained_order"]) for source in SOURCES}
        for source, order in orders[qid].items():
            core.require(len(order) == len(set(order)) == 100 and all(core.valid_id(doc) for doc in order),
                         "retained source is not 100 distinct literal IDs")
            core.require(query["policies"][source] == order[:10], "natural standalone head differs")
        f_scores = integer_scores(orders[qid], {"A": 1, "D": 1, "T": 1, "S": 3})
        h_scores = integer_scores(orders[qid], {"A": 1, "S": 1})
        core.require(head(f_scores) == query["policies"]["F"], "identity control does not reproduce natural F")
        core.require(head(h_scores) == query["policies"]["H"], "natural H replay differs")
        core.require(orders[qid]["S"][:10] == query["policies"]["S"], "natural S replay differs")
        original_pool = set(orders[qid]["A"]) | set(orders[qid]["S"])
        core.require(set(query["policies"]["F"]) <= original_pool, "natural new-only head admission")
        rows = {row["docid"]: row for row in query["candidates"]}
        core.require(set(rows) == set(f_scores), "natural candidate inventory differs")
        for doc, score in f_scores.items():
            core.require(Fraction(rows[doc]["F"]) == Fraction(score, 3 * SCALE), "identity control F score differs")
            core.require(Fraction(rows[doc]["H"]) == Fraction(h_scores.get(doc, 0), SCALE), "natural H score differs")
    return orders


def generate_controls(policies, labels, control_count=CONTROL_COUNT, query_ids=QUERY_IDS):
    core.require(control_count > 0, "empty control panel")
    core.require(set(labels) == set(query_ids), "label cohort differs")
    orders = validate_natural(policies, query_ids)
    masks = {qid: membership_masks(orders[qid]) for qid in query_ids}
    natural = {qid: {name: list(policies["queries"][qid]["policies"][name]) for name in ("F", "H", "S")}
               for qid in query_ids}
    original_scores = {qid: integer_scores(orders[qid], {"A": 1, "D": 1, "T": 1, "S": 3}) for qid in query_ids}
    unknown = {qid: set(original_scores[qid]) - set(labels[qid]) for qid in query_ids}
    strata = {qid: {source: stratum_summary(orders[qid][source], labels[qid], masks[qid])
                     for source in ("D", "T")} for qid in query_ids}
    counts = {qid: Counter() for qid in query_ids}
    controls = []
    for replicate in range(control_count):
        heads, changed = {}, {}
        for qid in query_ids:
            shuffled = {"A": orders[qid]["A"], "S": orders[qid]["S"]}
            shuffled.update({source: permute_order(orders[qid][source], labels[qid], masks[qid], replicate, qid, source)
                             for source in ("D", "T")})
            scores = integer_scores(shuffled, {"A": 1, "D": 1, "T": 1, "S": 3})
            core.require(all(scores[doc] == original_scores[qid][doc] for doc in unknown[qid]), "unknown candidate score changed")
            fused = head(scores)
            core.require(len(fused) == len(set(fused)) == 10, "control head is not ten unique IDs")
            core.require(set(fused) <= set(shuffled["A"]) | set(shuffled["S"]), "control new-only head admission")
            heads[qid] = fused
            changed[qid] = len(set(fused) - set(natural[qid]["F"]))
            counts[qid].update(fused)
        controls.append({"replicate": replicate, "heads": heads, "changed_slots": changed})
    return {"schema": 1, "query_ids": list(query_ids), "control_count": control_count, "seed": SEED,
            "membership_bits": dict(MEMBERSHIP_BITS),
            "seed_encoding": SEED_ENCODING, "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(), "rank_scale": str(SCALE),
            "labels_used_to_construct_controls": True, "natural_heads": natural,
            "controls": controls, "head_counts": {qid: dict(sorted(counts[qid].items())) for qid in query_ids},
            "strata": strata, "invariants": {"identity_replay_passed": True,
                "candidate_sets_preserved": True, "grade_symbol_profiles_preserved": True,
                "reciprocal_mass_by_grade_mask_preserved": True, "new_only_head_admissions": 0}}


def coefficients(left, right):
    return {doc: (left.get(doc, Fraction()) - right.get(doc, Fraction())) / 10
            for doc in sorted(set(left) | set(right)) if left.get(doc, Fraction()) != right.get(doc, Fraction())}


def coefficient_bounds(values, labels):
    known, lower_unknown, upper_unknown = Fraction(), Fraction(), Fraction()
    support = []
    for doc, coefficient in sorted(values.items()):
        if not coefficient:
            continue
        grade = labels.get(doc)
        core.require(grade is None or grade in (0, 1, 2), "invalid label grade")
        if grade is None:
            lower_unknown += min(coefficient, 0)
            upper_unknown += max(coefficient, 0)
        else:
            known += coefficient * int(grade > 0)
        support.append({"docid": doc, "coefficient": core.rational(coefficient), "grade": grade})
    result = core.interval_fields(known, known + lower_unknown, known + upper_unknown)
    result.update(support=support, unknown_support=sum(row["grade"] is None for row in support))
    return result


def mean_scaled_bounds(controls, labels):
    """Direct pair coefficients divide by controls * ten * queries exactly once."""
    count, qids = controls["control_count"], controls["query_ids"]
    values = {name: {} for name in CONTRASTS}
    pair_labels = {}
    for qid in qids:
        integer_weights = {name: {doc: count for doc in controls["natural_heads"][qid][name]}
                           for name in ("F", "H", "S")}
        integer_weights["C"] = controls["head_counts"][qid]
        for doc, grade in labels[qid].items():
            pair_labels[(qid, doc)] = grade
        for name in CONTRASTS:
            left, right = integer_weights[name[0]], integer_weights[name[2]]
            for doc in set(left) | set(right):
                numerator = left.get(doc, 0) - right.get(doc, 0)
                if numerator:
                    values[name][(qid, doc)] = Fraction(numerator, count * 10 * len(qids))
    return {name: coefficient_bounds(pairs, pair_labels) for name, pairs in values.items()}


def analyze(controls, labels):
    qids, count = controls["query_ids"], controls["control_count"]
    core.require(len(controls["controls"]) == count and set(labels) == set(qids), "control or label inventory differs")
    per_query = {}
    for qid in qids:
        values = {name: {doc: Fraction(1) for doc in controls["natural_heads"][qid][name]} for name in ("F", "H", "S")}
        values["C"] = {doc: Fraction(frequency, count) for doc, frequency in controls["head_counts"][qid].items()}
        core.require(sum(values["C"].values()) == 10, "control head frequency sum differs")
        contrasts = {name: coefficients(values[name[0]], values[name[2]]) for name in CONTRASTS}
        for first, second, total in (("F-C", "C-H", "F-H"), ("F-C", "C-S", "F-S")):
            union = set(contrasts[first]) | set(contrasts[second]) | set(contrasts[total])
            core.require(all(contrasts[first].get(doc, 0) + contrasts[second].get(doc, 0) == contrasts[total].get(doc, 0)
                             for doc in union), "contrast coefficient triangle failed")
        per_query[qid] = {"contrasts": {name: coefficient_bounds(coeffs, labels[qid]) for name, coeffs in contrasts.items()},
                          "benchmark": {name: core.rational(sum((value * int(labels[qid].get(doc, 0) > 0)
                                              for doc, value in weights.items()), Fraction()) / 10)
                                        for name, weights in values.items()}}
    aggregate = {name: core.average_bounds([per_query[qid]["contrasts"][name] for qid in qids]) for name in CONTRASTS}
    mean_scaled = mean_scaled_bounds(controls, labels)
    for name, result in aggregate.items():
        core.require(all(mean_scaled[name][key] == value for key, value in result.items() if key != "query_count"),
                     "mean-scaled sum and per-query average normalization differ")
    benchmark = {name: core.rational(sum((Fraction(per_query[qid]["benchmark"][name]) for qid in qids), Fraction()) / len(qids))
                 for name in ("F", "C", "H", "S")}
    draw_means = [{"replicate": row["replicate"], "mean": core.rational(Fraction(sum(
        labels[qid].get(doc, 0) > 0 for qid in qids for doc in row["heads"][qid]), 10 * len(qids)))}
                  for row in controls["controls"]]
    core.require(sum((Fraction(row["mean"]) for row in draw_means), Fraction()) / count == Fraction(benchmark["C"]),
                 "mean of control metrics differs from head-frequency metric")
    return {"schema": 1, "query_count": len(qids), "control_count": count, "labels_used_to_construct_controls": True,
            "contrast_definitions": dict(CONTRASTS), "contrasts": aggregate, "per_query": per_query,
            "benchmark": {"convention": "binary P@10 with unknown labels assigned zero", "policies": benchmark,
                          "control_draw_means": draw_means,
                          "control_draw_min": core.rational(min(Fraction(row["mean"]) for row in draw_means)),
                          "control_draw_max": core.rational(max(Fraction(row["mean"]) for row in draw_means))},
            "coefficient_checks": {"F-H=(F-C)+(C-H)": True, "F-S=(F-C)+(C-S)": True,
                                   "mean_scaled_sum_equals_query_average": True},
            "primary_decision": aggregate["F-C"]["decision"]}


def verify_saved_reference(analysis, reference):
    for name in ("F-H", "F-S"):
        core.require(analysis["contrasts"][name] == reference["contrasts"][name], "saved natural aggregate contrast differs")
        for qid in analysis["per_query"]:
            core.require(analysis["per_query"][qid]["contrasts"][name] == reference["per_query"][qid]["contrasts"][name],
                         "saved natural per-query contrast differs")
    for name in ("F", "H", "S"):
        core.require(analysis["benchmark"]["policies"][name] == reference["benchmark"]["policies"][name],
                     "saved natural benchmark differs")


def replay_saved_reference(policies, labels, reference):
    """Check the already observed natural metrics before any randomized control."""
    qids = policies["query_ids"]
    natural = {qid: {name: list(policies["queries"][qid]["policies"][name]) for name in ("F", "H", "S")} for qid in qids}
    identity = {"query_ids": qids, "control_count": 1, "natural_heads": natural,
                "head_counts": {qid: {doc: 1 for doc in natural[qid]["F"]} for qid in qids},
                "controls": [{"replicate": 0, "heads": {qid: natural[qid]["F"] for qid in qids}}]}
    verify_saved_reference(analyze(identity, labels), reference)


def artifact_path(path):
    path = Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def resolve_path(path):
    path = Path(path)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
        stream.write("\n")


def load_inputs(preflight_path):
    preflight_path = Path(preflight_path).resolve()
    tracked = {str(preflight_path): core.identity(preflight_path)}
    preflight = core.read_json(preflight_path)
    core.require(preflight.get("status") == "passed", "preflight did not pass")
    frozen = preflight["frozen"]
    core.require(REQUIRED_FROZEN <= set(frozen), "missing required frozen dependency")
    for name, digest in frozen.items():
        path = resolve_path(name)
        core.require(path.is_relative_to(ROOT) and not Path(name).is_absolute(), "frozen path escapes repository")
        observed = core.identity(path)
        core.require(observed["sha256"] == digest, "frozen identity changed: " + name)
        tracked[str(path)] = observed
    directory = ROOT / PRIOR
    manifest = core.read_json(directory / "manifest.json")
    success = core.read_json(directory / "success.json")
    core.require(success.get("status") == "passed" and success["manifest"] == core.identity(directory / "manifest.json"),
                 "saved Cycle18 success or manifest identity differs")
    inputs = {}
    for name in ("policies.json", "analysis.json"):
        path = directory / name
        observed = core.identity(path)
        core.require(observed == manifest["outputs"][name], "saved Cycle18 output changed")
        inputs["cycle18_" + name] = {"path": artifact_path(path), **observed}
    expected = manifest["inputs"]["late.qrels"]
    qrels_path = resolve_path(expected["path"])
    observed = core.identity(qrels_path)
    core.require(observed == {key: expected[key] for key in ("bytes", "sha256")}, "pinned late qrels changed")
    tracked[str(qrels_path)] = observed
    inputs["late.qrels"] = {"path": artifact_path(qrels_path), **observed}
    policies = core.read_json(directory / "policies.json")
    validate_natural(policies)
    universe = {doc for query in policies["queries"].values() for source in SOURCES for doc in query["sources"][source]["retained_order"]}
    # This diagnostic explicitly uses labels to construct its controls.
    labels = label_parser.parse_qrels(qrels_path.read_text(encoding="utf-8"), universe)
    return frozen, inputs, tracked, policies, labels, core.read_json(directory / "analysis.json")


def produce(args, output):
    frozen, inputs, tracked, policies, labels, reference = load_inputs(args.preflight)
    replay_saved_reference(policies, labels, reference)
    controls = generate_controls(policies, labels, CONTROL_COUNT)
    write_json(output / "controls.json", controls)
    analysis = analyze(controls, labels)
    verify_saved_reference(analysis, reference)
    write_json(output / "analysis.json", analysis)
    after = core.verify_tracked(tracked)
    manifest = {"schema": 1, "phase": "cycle20", "command": sys.argv, "frozen": frozen, "inputs": inputs,
                "preflight": artifact_path(args.preflight),
                "tracked_before": {artifact_path(path): value for path, value in tracked.items()},
                "tracked_after": {artifact_path(path): value for path, value in after.items()},
                "seed": SEED, "python_version": platform.python_version(), "python_implementation": platform.python_implementation(),
                "labels_used_to_construct_controls": True,
                "outputs": {name: core.identity(output / name) for name in ("controls.json", "analysis.json")}}
    write_json(output / "manifest.json", manifest)
    write_json(output / "success.json", {"status": "passed", "manifest": core.identity(output / "manifest.json")})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    created, started = False, time.monotonic()
    def timeout(signum, frame):
        raise core.ContractError("cycle20 exceeded 300 seconds")
    old_handler = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    try:
        output.mkdir(parents=True, exist_ok=False)
        created = True
        produce(args, output)
        print(json.dumps({"status": "passed", "output": str(output)}))
        return 0
    except Exception as exc:
        failure = {"status": "failed", "phase": "cycle20", "error_type": type(exc).__name__, "error": str(exc),
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
        signal.signal(signal.SIGALRM, old_handler)


if __name__ == "__main__":
    raise SystemExit(main())
