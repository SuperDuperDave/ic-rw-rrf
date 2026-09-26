#!/usr/bin/env python3
"""Independent Cycle20 Fraction reconstruction; synthetic until execution GO."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
import random
import signal
import sys
import tempfile
import time
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "_sessions/cycles/2026-09-25-cycle20-protocol.md"
QIDS = [str(i) for i in range(1, 31)]
SOURCES = ("A", "D", "T", "S")
CONTRASTS = ("F-C", "C-H", "C-S", "F-H", "F-S")
DRAWS = 256
SEED = "cycle20-alignment-v2"
SEED_ENCODING = "sha256(UTF-8 compact ASCII JSON [seed,replicate:int,qid:str,source:str,grade:int,mask:int]) as unsigned big-endian integer"
RR = {r: Q(1, 60 + r) for r in range(1, 101)}
THIRD = {r: Q(1, 3 * (60 + r)) for r in range(1, 101)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fraction(x):
    value = Q(x)
    return f"{value.numerator}/{value.denominator}"


def identity(path):
    body = Path(path).read_bytes()
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def read_json(path):
    return json.loads(Path(path).read_text())


def artifact_path(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def same(actual, expected, context="root"):
    require(type(actual) is type(expected), f"{context}: type differs")
    if isinstance(expected, dict):
        require(actual.keys() == expected.keys(), f"{context}: keys differ")
        for key in expected:
            same(actual[key], expected[key], f"{context}.{key}")
    elif isinstance(expected, list):
        require(len(actual) == len(expected), f"{context}: lengths differ")
        for index, (a, b) in enumerate(zip(actual, expected)):
            same(a, b, f"{context}[{index}]")
    else:
        require(actual == expected, f"{context}: value differs")


def read_labels(path):
    labels = {q: {} for q in QIDS}
    for number, line in enumerate(Path(path).read_text().splitlines(), 1):
        fields = line.split()
        require(len(fields) == 4, f"qrel line {number}: four fields required")
        q, iteration, doc, grade = fields
        require(q in labels and grade in ("0", "1", "2"), "qrel topic/grade domain")
        require(doc and all(33 <= ord(c) <= 126 for c in doc), "qrel ASCII document token")
        require(doc not in labels[q], "duplicate qrel pair")
        try:
            parsed_iteration = Decimal(iteration)
        except InvalidOperation as error:
            raise ValueError("invalid qrel iteration") from error
        require(parsed_iteration.is_finite() and parsed_iteration > 0, "qrel iteration domain")
        labels[q][doc] = int(grade)
    require(all(labels.values()), "missing qrel query")
    return labels


def seed_value(replicate, qid, source, grade, mask):
    encoded = json.dumps([SEED, replicate, qid, source, grade, mask],
                         ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest(), "big")


def symbol_profile(order, labels):
    return [("grade", labels[d]) if d in labels else ("unknown", d) for d in order]


def membership_masks(orders):
    masks = {}
    for source, bit in (("A", 1), ("D", 2), ("T", 4), ("S", 8)):
        for doc in orders[source]:
            masks[doc] = masks.get(doc, 0) | bit
    return masks


def class_mass(order, labels, masks):
    mass = {}
    for rank, doc in enumerate(order, 1):
        key = (labels.get(doc), masks[doc])
        mass[key] = mass.get(key, Q(0)) + RR[rank]
    return mass


def shuffled_order(order, labels, masks, replicate, qid, source):
    result = order.copy()
    for grade in (0, 1, 2):
        for mask in sorted(set(masks[d] for d in order)):
            positions = [i for i, d in enumerate(order) if labels.get(d) == grade and masks[d] == mask]
            documents = [order[i] for i in positions]
            random.Random(seed_value(replicate, qid, source, grade, mask)).shuffle(documents)
            for i, d in zip(positions, documents):
                result[i] = d
    require(len(result) == len(set(result)) and set(result) == set(order), "source candidate set changed")
    same(symbol_profile(result, labels), symbol_profile(order, labels), "rank grade/unknown symbols")
    same([masks[d] for d in result], [masks[d] for d in order], "rank membership classes")
    same(class_mass(result, labels, masks), class_mass(order, labels, masks), "grade/mask reciprocal mass")
    return result


def fixed_vector(orders):
    candidates = set().union(*(set(order) for order in orders.values()))
    fixed = dict.fromkeys(candidates, Q(0))
    for rank, doc in enumerate(orders["A"], 1):
        fixed[doc] += THIRD[rank]
    for rank, doc in enumerate(orders["S"], 1):
        fixed[doc] += RR[rank]
    return fixed


def score_vector(fixed, d_order, t_order):
    scores = fixed.copy()
    for order in (d_order, t_order):
        for rank, doc in enumerate(order, 1):
            scores[doc] += THIRD[rank]
    return scores


def top_ten(scores):
    return sorted(scores, key=lambda doc: (-scores[doc], doc))[:10]


def sign_and_decision(lower, upper):
    if lower > 0:
        sign = "strict_positive"
    elif upper < 0:
        sign = "strict_negative"
    elif lower == upper == 0:
        sign = "point_zero"
    elif upper == 0:
        sign = "nonpositive_with_zero"
    elif lower == 0:
        sign = "nonnegative_with_zero"
    else:
        sign = "crosses_zero"
    decision = ("all_completions_positive" if lower > 0 else
                "positive_excluded" if upper <= 0 else "sign_unresolved")
    return sign, decision


def signed_bounds(coefficients, labels):
    support = []
    positive_unknown = negative_unknown = known = Q(0)
    unknown = 0
    for doc in sorted(coefficients):
        coefficient = coefficients[doc]
        if not coefficient:
            continue
        grade = labels.get(doc)
        support.append({"docid": doc, "coefficient": fraction(coefficient), "grade": grade})
        if grade is None:
            unknown += 1
            positive_unknown += max(coefficient, 0)
            negative_unknown += min(coefficient, 0)
        elif grade > 0:
            known += coefficient
    lower, upper = known + negative_unknown, known + positive_unknown
    sign, decision = sign_and_decision(lower, upper)
    return {"known": fraction(known), "benchmark_zero": fraction(known),
            "lower": fraction(lower), "upper": fraction(upper), "width": fraction(upper - lower),
            "sign": sign, "decision": decision, "support": support, "unknown_support": unknown}


def coefficient_maps(heads, counts, draws=DRAWS):
    candidate_ids = set(counts).union(*(set(h) for h in heads.values()))
    membership = {name: set(head) for name, head in heads.items()}
    out = {name: {} for name in CONTRASTS}
    for doc in candidate_ids:
        f, h, s = (int(doc in membership[p]) for p in ("F", "H", "S"))
        control = Q(counts.get(doc, 0), draws)
        values = ((f - control) / 10, (control - h) / 10, (control - s) / 10,
                  Q(f - h, 10), Q(f - s, 10))
        for contrast, value in zip(CONTRASTS, values):
            if value:
                out[contrast][doc] = value
        require(values[3] == values[0] + values[1] and values[4] == values[0] + values[2],
                "coefficient triangle failed")
    return out


def mean_bounds(bounds):
    n = len(bounds)
    require(n > 0, "empty bound average")
    out = {key: fraction(sum((Q(row[key]) for row in bounds), Q(0)) / n)
           for key in ("known", "benchmark_zero", "lower", "upper", "width")}
    out["sign"], out["decision"] = sign_and_decision(Q(out["lower"]), Q(out["upper"]))
    out["unknown_support"] = sum(row["unknown_support"] for row in bounds)
    out["query_count"] = n
    return out


def p10(head, labels):
    return Q(sum(labels.get(d, 0) > 0 for d in head), 10)


def natural_replay(saved):
    same(saved["query_ids"], QIDS, "query cohort")
    require(set(saved["queries"]) == set(QIDS), "query object cohort")
    query_data, heads = {}, {}
    for q in QIDS:
        row = saved["queries"][q]
        orders = {s: row["sources"][s]["retained_order"] for s in SOURCES}
        for source, order in orders.items():
            require(isinstance(order, list) and len(order) == 100 and len(set(order)) == 100,
                    f"{q}/{source}: unique depth100")
            require(all(isinstance(d, str) and d and all(33 <= ord(c) <= 126 for c in d) for d in order),
                    "source document ID domain")
        fixed = fixed_vector(orders)
        scores = score_vector(fixed, orders["D"], orders["T"])
        h_scores = dict.fromkeys(scores, Q(0))
        for source in ("A", "S"):
            for rank, doc in enumerate(orders[source], 1):
                h_scores[doc] += RR[rank]
        replayed = {"F": top_ten(scores), "H": top_ten(h_scores), "S": orders["S"][:10]}
        for policy, head in replayed.items():
            same(row["policies"][policy], head, f"natural {q}/{policy} head")
        same(row["candidate_ids"], sorted(scores), "natural candidate pool")
        old_pool = set(orders["A"]) | set(orders["S"])
        same(row["original_candidate_ids"], sorted(old_pool), "natural original pool")
        require(len(row["candidates"]) == len(scores), "candidate score coverage")
        require({r["docid"] for r in row["candidates"]} == set(scores), "candidate score IDs")
        for candidate in row["candidates"]:
            doc = candidate["docid"]
            same(candidate["F"], fraction(scores[doc]), f"natural {q}/{doc} F score")
            same(candidate["H"], fraction(h_scores[doc]), f"natural {q}/{doc} H score")
        query_data[q] = {"orders": orders, "fixed": fixed, "natural_scores": scores,
                         "old_pool": old_pool, "masks": membership_masks(orders)}
        heads[q] = replayed
    return query_data, heads


def historical_identity(heads, labels, historical):
    per_query = {}
    for q in QIDS:
        per_query[q] = {}
        for contrast, right in (("F-H", "H"), ("F-S", "S")):
            left_set, right_set = set(heads[q]["F"]), set(heads[q][right])
            coefficients = {d: Q(int(d in left_set)-int(d in right_set), 10) for d in left_set ^ right_set}
            per_query[q][contrast] = signed_bounds(coefficients, labels[q])
            same(per_query[q][contrast], historical["per_query"][q]["contrasts"][contrast],
                 f"before-controls historical {q}/{contrast}")
        for policy in ("F", "H", "S"):
            same(fraction(p10(heads[q][policy], labels[q])), historical["per_query"][q]["benchmark"][policy],
                 "before-controls historical query benchmark")
    for contrast in ("F-H", "F-S"):
        same(mean_bounds([per_query[q][contrast] for q in QIDS]), historical["contrasts"][contrast],
             "before-controls historical mean contrast")
    for policy in ("F", "H", "S"):
        point = sum((p10(heads[q][policy], labels[q]) for q in QIDS), Q(0)) / len(QIDS)
        same(fraction(point), historical["benchmark"]["policies"][policy], "before-controls historical mean benchmark")


def reconstruct_controls(saved, labels, historical):
    query_data, heads = natural_replay(saved)
    historical_identity(heads, labels, historical)
    strata = {}
    for q in QIDS:
        strata[q] = {}
        for source in ("D", "T"):
            order = query_data[q]["orders"][source]
            masks = query_data[q]["masks"]
            sizes = Counter((labels[q][d], masks[d]) for d in order if d in labels[q])
            masses = class_mass(order, labels[q], masks)
            strata[q][source] = {
                "known": [{"grade": grade, "mask": mask, "size": sizes[grade, mask],
                           "reciprocal_mass": fraction(masses[grade, mask])} for grade, mask in sorted(sizes)],
                "unknown": sum(d not in labels[q] for d in order)}
    draws = []
    frequencies = {q: Counter() for q in QIDS}
    for replicate in range(DRAWS):
        draw = {"replicate": replicate, "heads": {}, "changed_slots": {}}
        for q in QIDS:
            data = query_data[q]
            d_order = shuffled_order(data["orders"]["D"], labels[q], data["masks"], replicate, q, "D")
            t_order = shuffled_order(data["orders"]["T"], labels[q], data["masks"], replicate, q, "T")
            scores = score_vector(data["fixed"], d_order, t_order)
            require(scores.keys() == data["natural_scores"].keys(), "fusion candidate set changed")
            for doc in scores:
                if doc not in labels[q]:
                    require(scores[doc] == data["natural_scores"][doc], "unknown document score changed")
            head = top_ten(scores)
            require(len(head) == len(set(head)) == 10, "control head not unique depth10")
            require(set(head) <= data["old_pool"], "outside-U0 control admission")
            draw["heads"][q] = head
            draw["changed_slots"][q] = len(set(head) - set(heads[q]["F"]))
            frequencies[q].update(head)
        draws.append(draw)
    return {"schema": 1, "query_ids": QIDS, "control_count": DRAWS, "seed": SEED,
            "membership_bits": {"A": 1, "D": 2, "T": 4, "S": 8},
            "seed_encoding": SEED_ENCODING, "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "rank_scale": str(math.lcm(*range(61, 161))), "labels_used_to_construct_controls": True,
            "natural_heads": heads, "controls": draws,
            "head_counts": {q: dict(sorted(frequencies[q].items())) for q in QIDS}, "strata": strata,
            "invariants": {"identity_replay_passed": True, "candidate_sets_preserved": True,
                           "grade_symbol_profiles_preserved": True,
                           "reciprocal_mass_by_grade_mask_preserved": True, "new_only_head_admissions": 0}}


def reconstruct_analysis(controls, labels, historical):
    per_query = {}
    draw_means = []
    global_coefficients = {c: {} for c in CONTRASTS}
    global_labels = {(q, d): grade for q in QIDS for d, grade in labels[q].items()}
    endpoint_totals = {q: {c: {e: Q(0) for e in ("known", "lower", "upper")}
                           for c in ("F-C", "C-H", "C-S")} for q in QIDS}
    for draw in controls["controls"]:
        total = Q(0)
        for q in QIDS:
            head = draw["heads"][q]
            total += p10(head, labels[q])
            maps = coefficient_maps(controls["natural_heads"][q], Counter(head), 1)
            for contrast in ("F-C", "C-H", "C-S"):
                bounded = signed_bounds(maps[contrast], labels[q])
                for endpoint in endpoint_totals[q][contrast]:
                    endpoint_totals[q][contrast][endpoint] += Q(bounded[endpoint]) / DRAWS
        draw_means.append({"replicate": draw["replicate"], "mean": fraction(total / len(QIDS))})
    for q in QIDS:
        heads = controls["natural_heads"][q]
        counts = controls["head_counts"][q]
        maps = coefficient_maps(heads, counts)
        # Direct overall numerators use 256*300; no second averaging follows.
        # Compare them to the separately formed query coefficients /30.
        for doc in set(counts).union(*(set(h) for h in heads.values())):
            f, h, s = (int(doc in heads[p]) for p in ("F", "H", "S"))
            n = counts.get(doc, 0)
            direct = (Q(DRAWS*f-n, DRAWS*300), Q(n-DRAWS*h, DRAWS*300),
                      Q(n-DRAWS*s, DRAWS*300), Q(f-h, 300), Q(f-s, 300))
            for contrast, value in zip(CONTRASTS, direct):
                require(value == Q(maps[contrast].get(doc, 0)) / 30, "per-query vs overall coefficient normalization")
                if value:
                    global_coefficients[contrast][(q, doc)] = value
        bounds = {c: signed_bounds(maps[c], labels[q]) for c in CONTRASTS}
        for contrast in endpoint_totals[q]:
            for endpoint, expected in endpoint_totals[q][contrast].items():
                require(Q(bounds[contrast][endpoint]) == expected, "actual fixed-reference endpoint identity")
        benchmark = {p: fraction(p10(heads[p], labels[q])) for p in ("F", "H", "S")}
        benchmark["C"] = fraction(Q(sum(n for d, n in counts.items() if labels[q].get(d, 0) > 0), DRAWS * 10))
        per_query[q] = {"contrasts": bounds, "benchmark": benchmark}
        for c in ("F-H", "F-S"):
            same(bounds[c], historical["per_query"][q]["contrasts"][c], f"historical {q}/{c}")
        for policy in ("F", "H", "S"):
            same(benchmark[policy], historical["per_query"][q]["benchmark"][policy], "historical query benchmark")
    contrasts = {c: mean_bounds([per_query[q]["contrasts"][c] for q in QIDS]) for c in CONTRASTS}
    for contrast in CONTRASTS:
        direct = signed_bounds(global_coefficients[contrast], global_labels)
        for key in ("known", "benchmark_zero", "lower", "upper", "width", "unknown_support", "sign", "decision"):
            same(direct[key], contrasts[contrast][key], f"direct global vs averaged query {contrast}/{key}")
    means = {p: fraction(sum((Q(per_query[q]["benchmark"][p]) for q in QIDS), Q(0)) / len(QIDS))
             for p in ("F", "C", "H", "S")}
    for c in ("F-H", "F-S"):
        same(contrasts[c], historical["contrasts"][c], f"historical aggregate {c}")
    for policy in ("F", "H", "S"):
        same(means[policy], historical["benchmark"]["policies"][policy], "historical mean benchmark")
    require(Q(means["C"]) == sum((Q(d["mean"]) for d in draw_means), Q(0)) / DRAWS,
            "control mean order of averaging")
    return {"schema": 1, "query_count": len(QIDS), "control_count": DRAWS,
            "labels_used_to_construct_controls": True,
            "contrast_definitions": {"F-C": "natural F minus mean control F", "C-H": "mean control F minus H",
                                     "C-S": "mean control F minus S", "F-H": "natural F minus H", "F-S": "natural F minus S"},
            "contrasts": contrasts, "per_query": per_query,
            "benchmark": {"convention": "binary P@10 with unknown labels assigned zero", "policies": means,
                          "control_draw_means": draw_means,
                          "control_draw_min": fraction(min(Q(d["mean"]) for d in draw_means)),
                          "control_draw_max": fraction(max(Q(d["mean"]) for d in draw_means))},
            "coefficient_checks": {"F-H=(F-C)+(C-H)": True, "F-S=(F-C)+(C-S)": True,
                                   "mean_scaled_sum_equals_query_average": True},
            "primary_decision": contrasts["F-C"]["decision"]}


def custody(args):
    preflight = read_json(args.preflight)
    require(preflight["schema"] == 1 and preflight["status"] == "passed", "preflight not passed")
    previous = ROOT / "results/cycle18-2026-09-25/run"
    previous_files = {name: previous / f"{name}.json" for name in ("policies", "analysis", "manifest", "success")}
    previous_audit = ROOT / "results/cycle18-2026-09-25/independent-check.json"
    previous_official = ROOT / "results/cycle18-2026-09-25/official-metric-check.json"
    required = {str(path.relative_to(ROOT)) for path in
                [PROTOCOL, Path(__file__).resolve(), *previous_files.values(), previous_audit, previous_official]}
    required.update({"evaluation/cycle20_alignment_control.py",
                     "evaluation/tests/test_cycle20_alignment_control.py",
                     "evaluation/cycle17_minority_exchange.py",
                     "evaluation/cycle17_minority_exchange_corrected.py",
                     "evaluation/cycle17_minority_exchange_compatible.py",
                     "evaluation/cycle17_scoped_labels.py"})
    require(required <= preflight["frozen"].keys(), "mandatory protocol/verifier/previous evidence missing from freeze")
    frozen_identities = {}
    for name, sha in preflight["frozen"].items():
        file_id = identity(artifact_path(name))
        require(file_id["sha256"] == sha, f"frozen source changed: {name}")
        frozen_identities[name] = file_id
    old_manifest = read_json(previous_files["manifest"])
    old_success = read_json(previous_files["success"])
    old_audit = read_json(previous_audit)
    old_official = read_json(previous_official)
    require(old_manifest["schema"] == 1 and old_manifest["phase"] == "cycle18", "previous phase identity")
    require(old_success["status"] == old_audit["status"] == "passed", "previous execution/audit did not pass")
    require(old_official["status"] == "passed", "previous official metric check did not pass")
    same(old_official["before"], old_official["after"], "previous official metric custody")
    same(identity(previous_files["manifest"]), old_success["manifest"], "previous success identity")
    same(identity(previous_files["manifest"]), old_audit["custody"]["manifest"], "previous audited manifest")
    for name in ("policies", "analysis"):
        file_id = identity(previous_files[name])
        same(file_id, old_manifest["outputs"][f"{name}.json"], "previous output identity")
        same(file_id, old_audit["custody"]["outputs"][f"{name}.json"], "previous audited output")
    label_info = old_manifest["inputs"]["late.qrels"]
    label_path = artifact_path(label_info["path"])
    label_id = {key: label_info[key] for key in ("bytes", "sha256")}
    same(identity(label_path), label_id, "raw late qrel identity")
    same(label_id, old_audit["custody"]["input_identities"]["late.qrels"], "previous audited late qrels")
    for path in (previous_files["policies"], previous_files["analysis"], label_path):
        item = old_official["after"]["files"][str(path.relative_to(ROOT))]
        same(identity(path), {k: item[k] for k in ("bytes", "sha256")}, "previous official metric input binding")
    paths = {"cycle18_policies.json": previous_files["policies"],
             "cycle18_analysis.json": previous_files["analysis"], "late.qrels": label_path}
    input_identities = {name: identity(path) for name, path in paths.items()}
    manifest = read_json(args.result / "manifest.json")
    success = read_json(args.result / "success.json")
    require(manifest["schema"] == 1 and manifest["phase"] == "cycle20" and success["status"] == "passed",
            "producer did not pass")
    same(identity(args.result / "manifest.json"), success["manifest"], "producer success identity")
    same(manifest["frozen"], preflight["frozen"], "producer source freeze")
    same(manifest["tracked_before"], manifest["tracked_after"], "producer before/after custody")
    for path, file_id in manifest["tracked_after"].items():
        same(identity(artifact_path(path)), file_id, f"producer tracked file {path}")
    require(set(manifest["inputs"]) == set(paths), "producer input set")
    for name, info in manifest["inputs"].items():
        require(artifact_path(info["path"]).resolve() == paths[name].resolve(), "producer input location")
        same({key: info[key] for key in ("bytes", "sha256")}, input_identities[name], "producer input identity")
    require(artifact_path(manifest["preflight"]).resolve() == args.preflight.resolve(), "producer preflight location")
    same(manifest["seed"], SEED, "producer seed")
    same(manifest["python_version"], platform.python_version(), "producer Python version")
    same(manifest["python_implementation"], platform.python_implementation(), "producer Python implementation")
    same(manifest["labels_used_to_construct_controls"], True, "explicit label use")
    require(set(manifest["outputs"]) == {"controls.json", "analysis.json"}, "producer output set")
    for name, file_id in manifest["outputs"].items():
        same(identity(args.result / name), file_id, f"producer output {name}")
    return {"paths": {name: str(path.resolve()) for name, path in paths.items()},
            "inputs": input_identities, "frozen": frozen_identities,
            "preflight": identity(args.preflight), "manifest": identity(args.result / "manifest.json"),
            "success": identity(args.result / "success.json"), "outputs": manifest["outputs"],
            "previous_manifest": identity(previous_files["manifest"]),
            "previous_success": identity(previous_files["success"]), "previous_audit": identity(previous_audit),
            "previous_official_metric": identity(previous_official)}


def verify(args):
    require(not args.output.exists(), "exclusive verifier output already exists")
    started = time.monotonic()
    before = custody(args)
    saved = read_json(before["paths"]["cycle18_policies.json"])
    historical = read_json(before["paths"]["cycle18_analysis.json"])
    labels = read_labels(before["paths"]["late.qrels"])
    controls = reconstruct_controls(saved, labels, historical)
    same(read_json(args.result / "controls.json"), controls, "every control artifact field")
    analysis = reconstruct_analysis(controls, labels, historical)
    same(read_json(args.result / "analysis.json"), analysis, "every analysis artifact field")
    after = custody(args)
    same(after, before, "independent before/after custody")
    self_tests = self_test()
    elapsed = time.monotonic() - started
    require(elapsed < 300, "independent verifier exceeded 300 seconds")
    result = {"schema": 1, "status": "passed", "command": sys.argv, "verifier": identity(__file__),
              "elapsed_seconds": elapsed, "custody": after, "self_tests": self_tests,
              "method": "own Fraction score vectors, exact grade/membership-mask shuffles, signed coefficient bounds",
              "audited_fields": {"controls.json": "every field including all 256x30 ordered control heads, changed slots, strata and inclusion counts",
                                 "analysis.json": "every field including all coefficients, label support, per-query/aggregate bounds and benchmark summaries",
                                 "identity_replay": "all natural F/H/S heads and candidate F/H scores; saved F-H/F-S bounds and F/H/S benchmarks",
                                 "invariants": "candidate sets, per-rank grade or missing-ID symbols, grade/membership-class reciprocal mass, unknown scores and zero outside-U0 admissions",
                                 "custody": "preflight sources, previous verified evidence, raw qrels and all new artifacts before/after"},
              "fixed_reference_endpoint_averaging_checked": True,
              "global_pair_vs_mean_query_normalization_checked": True,
              "coefficient_triangles_checked": True,
              "limits": ["No producer or earlier analysis/parser implementation is imported.",
                         "The generator and its evaluation deliberately use the same fixed labels.",
                         "The finite 256-control mean is the target, not the full randomization expectation.",
                         "Missing-label bounds are conditional sharp bounds, not confidence intervals.",
                         "This is arithmetic validation on reused query units, not independent performance evidence.",
                         "Official P@10 evidence is reused from Cycle18; the control heads are not individually exported to NIST.",
                         "Previous raw source runs and private acquisition receipts are not reopened; the verified Cycle18 derived inputs are pinned."]}
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": "passed", "output": str(args.output), "elapsed_seconds": elapsed,
                      "controls_all_fields": True, "analysis_all_fields": True}))


def self_test():
    encoded = b'["cycle20-alignment-v2",0,"1","D",2,15]'
    require(seed_value(0, "1", "D", 2, 15) == int.from_bytes(hashlib.sha256(encoded).digest(), "big"),
            "compact JSON seed fixture")
    require(seed_value(0, "1", "D", 2, 15) != seed_value(0, "1", "T", 2, 15), "separate source streams")
    require(seed_value(0, "1", "D", 2, 15) != seed_value(0, "1", "D", 2, 7), "separate mask streams")
    same(membership_masks({"A": ["a", "ad", "all"], "D": ["d", "ad", "all"],
                           "T": ["t", "all"], "S": ["s", "all"]}),
         {"a": 1, "ad": 3, "all": 15, "d": 2, "t": 4, "s": 8}, "distinct membership bits")
    counterexample_order = ["a", "b", "c", "d"]
    counterexample_labels = dict.fromkeys(counterexample_order, 1)
    counterexample_masks = {"a": 2, "b": 3, "c": 2, "d": 3}
    cross_class = ["d", "b", "c", "a"]
    same(symbol_profile(counterexample_order, counterexample_labels),
         symbol_profile(cross_class, counterexample_labels), "cross-mask swap preserves grade profile")
    require(class_mass(counterexample_order, counterexample_labels, counterexample_masks) !=
            class_mass(cross_class, counterexample_labels, counterexample_masks),
            "cross-mask swap changes reciprocal class mass")
    require(top_ten({"z": Q(1, 3), "a": Q(2, 6)}) == ["a", "z"], "exact score tie")
    order = [f"x{i:02}" for i in range(12)]
    labels = {d: i % 3 for i, d in enumerate(order[:9])}
    masks = {d: (6 if i < 6 else 15) for i, d in enumerate(order)}
    absent = order[9:]
    completions = 0
    for source, replicate in itertools.product(("D", "T"), (0, 1, 255)):
        permuted = shuffled_order(order, labels, masks, replicate, "1", source)
        same(permuted, shuffled_order(order, labels, masks, replicate, "1", source), "seed determinism")
        for bits in itertools.product((0, 1), repeat=len(absent)):
            completed = labels | dict(zip(absent, bits))
            require([completed[d] > 0 for d in order] == [completed[d] > 0 for d in permuted],
                    "standalone profile changed for a completion")
            completions += 1
    heads = {"F": ["a", "b"], "H": ["b", "c"], "S": ["a", "d"]}
    draws = [["a", "c"], ["b", "d"], ["c", "d"], ["a", "b"]]
    counts = Counter(d for head in draws for d in head)
    maps = coefficient_maps(heads, counts, len(draws))
    completion_checks = 0
    for table in itertools.product((None, 0, 1), repeat=4):
        docs = ["a", "b", "c", "d"]
        lab = {d: v for d, v in zip(docs, table) if v is not None}
        missing = [d for d in docs if d not in lab]
        for contrast in CONTRASTS:
            result = signed_bounds(maps[contrast], lab)
            values = []
            for bits in itertools.product((0, 1), repeat=len(missing)):
                full = lab | dict(zip(missing, bits))
                natural = p10(heads["F"], full); control = sum((p10(h, full) for h in draws), Q(0)) / len(draws)
                points = {"F-C": natural-control, "C-H": control-p10(heads["H"], full),
                          "C-S": control-p10(heads["S"], full), "F-H": natural-p10(heads["H"], full),
                          "F-S": natural-p10(heads["S"], full)}
                values.append(points[contrast]); completion_checks += 1
            require(Q(result["lower"]) == min(values) and Q(result["upper"]) == max(values),
                    "sharp common-completion bounds")
            if contrast in ("F-C", "C-H", "C-S"):
                individual = [signed_bounds(coefficient_maps(heads, Counter(h), 1)[contrast], lab) for h in draws]
                for endpoint in ("lower", "upper", "known"):
                    require(Q(result[endpoint]) == sum((Q(b[endpoint]) for b in individual), Q(0)) / len(draws),
                            "fixed-reference endpoint averaging")
    one_effect = [signed_bounds({"known": Q(1, 10), "unknown": Q(-1, 40)}, {"known": 1})]
    one_effect += [signed_bounds({}, {}) for _ in range(29)]
    normalized = mean_bounds(one_effect)
    require(Q(normalized["known"]) == Q(1, 300) and Q(normalized["lower"]) == Q(1, 400)
            and Q(normalized["upper"]) == Q(1, 300), "single-topic effect averaged exactly once")
    full_order = [f"d{i:03}" for i in range(100)]
    orders = {source: full_order.copy() for source in SOURCES}
    full_masks = membership_masks(orders)
    require(set(full_masks.values()) == {15}, "full membership-mask bits")
    grades = {doc: 1 for doc in full_order}
    fixed = fixed_vector(orders)
    natural = top_ten(score_vector(fixed, orders["D"], orders["T"]))
    changed = 0
    for replicate in range(4):
        d = shuffled_order(orders["D"], grades, full_masks, replicate, "1", "D")
        t = shuffled_order(orders["T"], grades, full_masks, replicate, "1", "T")
        changed += set(top_ten(score_vector(fixed, d, t))) != set(natural)
    require(changed > 0, "synthetic control should change fusion heads while retaining source quality")
    with tempfile.TemporaryDirectory(prefix="cycle20-independent-synthetic-") as tmp:
        path = Path(tmp) / "labels.txt"
        rows = [f"{q} 0.5 outside_inventory 2\n" for q in QIDS]
        path.write_text("".join(rows))
        require(all(v == {"outside_inventory": 2} for v in read_labels(path).values()), "literal qrel parser")
        path.write_text("".join(rows + [rows[0]]))
        try:
            read_labels(path)
        except ValueError:
            pass
        else:
            raise ValueError("duplicate qrel accepted")
    return {"seed_determinism_and_separation": True, "exact_ties": True,
            "membership_class_mass_preservation": True,
            "grade_only_cross_class_mass_counterexample": True,
            "rank_profile_completion_checks": completions, "partial_label_tables": 81,
            "contrast_completion_checks": completion_checks, "fixed_reference_endpoint_equivalence": True,
            "query_mean_normalization": True,
            "nontrivial_head_change_with_identical_marginal_profile": True,
            "literal_qrels_and_duplicate_rejection": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--result", type=Path)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return
    for name in ("result", "preflight", "output"):
        if getattr(args, name) is None:
            parser.error(f"--{name} is required")
    def alarm(signum, frame):
        raise TimeoutError("independent verifier exceeded 300 seconds")
    signal.signal(signal.SIGALRM, alarm)
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
