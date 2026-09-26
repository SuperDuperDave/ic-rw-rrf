#!/usr/bin/env python3
"""Independent, standard-library Cycle17 reconstruction; no primary-code import.

Actual input inspection requires the coordinator's explicit execution go-ahead.
The --self-test mode uses synthetic values only.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import tempfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "_sessions/cycles/2026-09-25-cycle17-exchange-protocol.md"
PLAN = ROOT / "_sessions/cycles/2026-09-25-cycle17-input-plan.json"
QUERY_IDS = [str(i) for i in range(1, 31)]
POLICIES = ("A", "S", "H", "M", "J")
CONTRASTS = ("M-H", "M-J", "M-S", "H-S", "H-A")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def fraction_text(value):
    f = Fraction(value)
    return f"{f.numerator}/{f.denominator}"


def classification(lo, hi):
    if lo > 0:
        return "strict_positive"
    if hi < 0:
        return "strict_negative"
    if lo == hi == 0:
        return "point_zero"
    if hi == 0:
        return "nonpositive_with_zero"
    if lo == 0:
        return "nonnegative_with_zero"
    return "crosses_zero"


def decision(lo, hi):
    if lo > 0:
        return "all_completions_positive"
    if hi <= 0:
        return "positive_excluded"
    return "sign_unresolved"


def read_docids(path):
    lines = Path(path).read_text().splitlines()
    require(lines and all(len(x.split()) == 1 for x in lines), "invalid docid rows")
    ids = [x.strip() for x in lines]
    require(len(ids) == len(set(ids)), "duplicate valid docid")
    return set(ids)


def read_run(path, valid):
    by_query = {q: {} for q in QUERY_IDS}
    tags = set()
    for row, line in enumerate(Path(path).read_text().splitlines(), 1):
        fields = line.split()
        require(len(fields) == 6, f"run {path}:{row}: field count")
        q, unused, doc, rank_text, score_text, tag = fields
        require(q in by_query, f"unexpected topic {q}")
        require(unused == "Q0", f"unexpected placeholder {unused}")
        require(doc in valid, f"invalid run doc {doc}")
        require(doc not in by_query[q], f"duplicate run pair {q}/{doc}")
        require(rank_text.isdigit() and int(rank_text) > 0, "invalid positive rank")
        try:
            score = Decimal(score_text)
        except InvalidOperation as exc:
            raise ValueError("invalid score") from exc
        require(score.is_finite(), "nonfinite score")
        by_query[q][doc] = {
            "score": score,
            "score_text": score_text,
            "supplied_rank": int(rank_text),
        }
        tags.add(tag)
    require(len(tags) == 1, "inconsistent run tag")
    result = {}
    for q, docs in by_query.items():
        require(10 <= len(docs) <= 1000, f"invalid run depth {q}")
        order = sorted(docs, key=lambda d: (docs[d]["score"].copy_negate(), d))
        frequency = Counter(x["score"] for x in docs.values())
        result[q] = {
            "full_order": order,
            "retained_order": order[:100],
            "details": {
                d: {
                    "score": docs[d]["score_text"],
                    "supplied_rank": docs[d]["supplied_rank"],
                    "canonical_rank": rank,
                }
                for rank, d in enumerate(order, 1)
            },
            "diagnostics": {
                "full_depth": len(order),
                "retained_depth": min(100, len(order)),
                "tied_score_groups": sum(n > 1 for n in frequency.values()),
                "tied_rows": sum(n for n in frequency.values() if n > 1),
                "supplied_rank_disagreements": sum(
                    docs[d]["supplied_rank"] != rank
                    for rank, d in enumerate(order, 1)
                ),
            },
        }
    return result


def read_qrels(path, valid):
    labels = {q: {} for q in QUERY_IDS}
    for row, line in enumerate(Path(path).read_text().splitlines(), 1):
        fields = line.split()
        require(len(fields) == 4, f"qrels {path}:{row}: field count")
        q, iteration, doc, grade_text = fields
        require(q in labels, f"unknown qrel topic {q}")
        require(doc in valid, f"invalid qrel doc {doc}")
        require(doc not in labels[q], f"duplicate qrel pair {q}/{doc}")
        try:
            when = Decimal(iteration)
        except InvalidOperation as exc:
            raise ValueError("invalid qrel round") from exc
        require(when.is_finite() and when > 0, "nonpositive/nonfinite qrel round")
        require(grade_text in ("0", "1", "2"), "invalid qrel grade")
        labels[q][doc] = int(grade_text)
    require(all(labels[q] for q in QUERY_IDS), "incomplete qrel topic cohort")
    return labels


def reconstruct(a, s):
    """Exact integer RRF audit alongside protocol-specified floating replay."""
    denominator = math.lcm(*range(61, 161))
    output, exact_audit = {}, []
    for q in QUERY_IDS:
        ar = {d: r for r, d in enumerate(a[q]["retained_order"], 1)}
        sr = {d: r for r, d in enumerate(s[q]["retained_order"], 1)}
        candidates = set(ar) | set(sr)
        numerators, floats = {}, {}
        for d in candidates:
            terms = [60 + ranks[d] for ranks in (ar, sr) if d in ranks]
            numerators[d] = sum(denominator // term for term in terms)
            floats[d] = math.fsum(1.0 / term for term in terms)
        exact_order = sorted(candidates, key=lambda d: (-numerators[d], d))
        order = sorted(candidates, key=lambda d: (-floats[d], d))
        differences = [
            {"position": i + 1, "exact": x, "computed": y}
            for i, (x, y) in enumerate(zip(exact_order, order)) if x != y
        ]
        nonexact_inversions = []
        for first, second in zip(order, order[1:]):
            if numerators[first] < numerators[second]:
                nonexact_inversions.append([first, second])
        exact_audit.append({
            "query_id": q,
            "order_differences": differences,
            "nonexact_inversions": nonexact_inversions,
            "computed_tie_groups": sum(n > 1 for n in Counter(floats.values()).values()),
            "exact_tie_groups": sum(n > 1 for n in Counter(numerators.values()).values()),
        })
        h = order[:10]
        a10, s10 = a[q]["retained_order"][:10], s[q]["retained_order"][:10]
        outsiders = [d for d in s10 if d not in ar]
        eligible = bool(outsiders) and not any(d not in ar and d in sr for d in h)
        m = outsiders[0] if eligible else None
        j = next(d for d in s10 if d not in h) if eligible else None
        result_m = h[:9] + [m] if eligible else h.copy()
        result_j = h[:9] + [j] if eligible else h.copy()
        output[q] = {
            "sources": {"A": a[q], "S": s[q]},
            "policies": {"A": a10, "S": s10, "H": h, "M": result_m, "J": result_j},
            "hybrid_order": order,
            "hybrid_scores": floats,
            "eligible": eligible,
            "m": m,
            "j": j,
            "displaced": h[9] if eligible else None,
            "m_equals_j": result_m == result_j,
        }
    return output, {"integer_denominator": str(denominator), "queries": exact_audit}


def bound(left, right, grades):
    """Count added/removed docs directly, cancelling shared docs first."""
    added = set(left) - set(right)
    removed = set(right) - set(left)
    known_added = sum(grades[d] > 0 for d in added if d in grades)
    known_removed = sum(grades[d] > 0 for d in removed if d in grades)
    missing_added = len(added - grades.keys())
    missing_removed = len(removed - grades.keys())
    known = Fraction(known_added - known_removed, 10)
    lo = known - Fraction(missing_removed, 10)
    hi = known + Fraction(missing_added, 10)
    return {
        "lower": fraction_text(lo), "upper": fraction_text(hi),
        "width": fraction_text(hi - lo), "known": fraction_text(known),
        "benchmark_zero": fraction_text(known), "sign": classification(lo, hi),
        "decision": decision(lo, hi),
        "support": [{"docid": d, "coefficient": "1/10" if d in added else "-1/10",
                     "grade": grades.get(d)} for d in sorted(added | removed)],
        "unknown_support": missing_added + missing_removed,
    }


def p10(docs, grades):
    return Fraction(sum(grades.get(d, 0) > 0 for d in docs), 10)


def exchange(grades, admitted, displaced):
    if admitted is None:
        return "unchanged"
    if admitted not in grades or displaced not in grades:
        return "unresolved"
    good_in, good_out = grades[admitted] > 0, grades[displaced] > 0
    if good_in and not good_out:
        return "rescue"
    if good_out and not good_in:
        return "harm"
    return "neutral"


def observation(qdata, grades, doc):
    if doc is None:
        return None
    result = {"docid": doc, "grade": grades.get(doc)}
    for source in ("A", "S"):
        for view in ("full", "retained"):
            order = qdata["sources"][source][f"{view}_order"]
            rank = order.index(doc) + 1 if doc in order else None
            result[f"{source}_{view}_rank"] = rank
            result[f"{source}_{view}_member"] = rank is not None
    return result


def aggregate(per_query, qids, contrast):
    values = {
        key: sum((Fraction(per_query[q]["contrasts"][contrast][key]) for q in qids), Fraction()) / len(qids)
        for key in ("lower", "upper", "width", "known", "benchmark_zero")
    }
    out = {key: fraction_text(value) for key, value in values.items()}
    out.update(sign=classification(values["lower"], values["upper"]),
               decision=decision(values["lower"], values["upper"]),
               query_count=len(qids),
               unknown_support=sum(per_query[q]["contrasts"][contrast]["unknown_support"] for q in qids))
    return out


def summaries(queries, labels):
    per_query = {}
    benchmark = {}
    for q in QUERY_IDS:
        policies = queries[q]["policies"]
        contrasts = {
            name: bound(policies[name.split("-")[0]], policies[name.split("-")[1]], labels[q])
            for name in CONTRASTS
        }
        benchmark[q] = {p: fraction_text(p10(policies[p], labels[q])) for p in POLICIES}
        per_query[q] = {"contrasts": contrasts, "benchmark": benchmark[q]}
    means = {name: aggregate(per_query, QUERY_IDS, name) for name in CONTRASTS}
    benchmark_means = {
        p: fraction_text(sum((Fraction(benchmark[q][p]) for q in QUERY_IDS), Fraction()) / 30)
        for p in POLICIES
    }
    eligible = [q for q in QUERY_IDS if queries[q]["eligible"]]
    ledger = []
    flags = ("known_positive_admission", "explicit_negative_admission", "known_positive_displacement")
    categories = ("unchanged", "unresolved", "rescue", "harm", "neutral")
    counts = {p: dict.fromkeys(categories + flags, 0) for p in ("M", "J")}
    for q in QUERY_IDS:
        qdata = queries[q]
        for policy in ("M", "J"):
            doc = qdata[policy.lower()]
            displaced = qdata["displaced"]
            grades = labels[q]
            category = exchange(grades, doc, displaced)
            row = {
                "qid": q, "policy": policy, "changed": qdata["eligible"],
                "category": category, "admitted": observation(qdata, grades, doc),
                "displaced": observation(qdata, grades, displaced),
                "known_positive_admission": doc is not None and grades.get(doc, 0) > 0,
                "explicit_negative_admission": doc is not None and grades.get(doc) == 0,
                "known_positive_displacement": displaced is not None and grades.get(displaced, 0) > 0,
            }
            ledger.append(row)
            counts[policy][category] += 1
            for flag in flags:
                counts[policy][flag] += row[flag]
    return {
        "schema": 1, "query_count": 30, "eligible_query_ids": eligible,
        "eligible_count": len(eligible),
        "m_equals_j_count": sum(queries[q]["m_equals_j"] for q in QUERY_IDS),
        "eligible_m_equals_j_count": sum(queries[q]["m_equals_j"] for q in eligible),
        "contrasts": means,
        "triggered_only_contrasts": {n: aggregate(per_query, eligible, n) for n in CONTRASTS} if eligible else None,
        "per_query": per_query, "exchange_ledger": ledger, "exchange_counts": counts,
        "benchmark": {"convention": "binary P@10 with unknown labels assigned zero", "policies": benchmark_means},
        "primary_decision": means["M-H"]["decision"] if eligible else "no_opportunity",
        "qrels_pair_count": sum(len(x) for x in labels.values()),
    }


def label_addition(early, late):
    failures = []
    added = {}
    for q in QUERY_IDS:
        for d, grade in early[q].items():
            if late[q].get(d) != grade:
                failures.append({"query_id": q, "doc_id": d, "early": grade,
                                 "late": late[q].get(d)})
        added[q] = sorted(late[q].keys() - early[q].keys())
    return failures, added


def revelation(early_result, late_result, early_labels, late_labels):
    added_records, transitions, contrasts = [], [], {}
    for name in CONTRASTS:
        total = 0
        for q in QUERY_IDS:
            old = early_result["per_query"][q]["contrasts"][name]
            new = late_result["per_query"][q]["contrasts"][name]
            lower_shift = Fraction(new["lower"]) - Fraction(old["lower"])
            upper_shift = Fraction(old["upper"]) - Fraction(new["upper"])
            require(lower_shift >= 0 and upper_shift >= 0, "non-nested query bounds")
            for support in old["support"]:
                d = support["docid"]
                if d not in early_labels[q] and d in late_labels[q]:
                    c = Fraction(support["coefficient"])
                    y = int(late_labels[q][d] > 0)
                    raises = c * y > min(c, 0)
                    added_records.append({
                        "contrast": name, "qid": q, "docid": d,
                        "grade": late_labels[q][d], "coefficient": fraction_text(c),
                        "query_lower_increase": fraction_text(c * y - min(c, 0)),
                        "query_upper_decrease": fraction_text(max(c, 0) - c * y),
                        "influence": "raises_lower" if raises else "lowers_upper",
                    })
                    total += 1
        old, new = early_result["contrasts"][name], late_result["contrasts"][name]
        reduction = Fraction(old["width"]) - Fraction(new["width"])
        require(reduction >= 0, "non-nested mean bounds")
        contrasts[name] = {
            "early_width": old["width"], "late_width": new["width"],
            "width_reduction": fraction_text(reduction),
            "early_sign": old["sign"], "late_sign": new["sign"],
            "sign_changed": old["sign"] != new["sign"],
            "early_decision": old["decision"], "late_decision": new["decision"],
            "added_labels_on_support": total,
        }
    old_ledger = {(x["qid"], x["policy"]): x for x in early_result["exchange_ledger"]}
    for row in late_result["exchange_ledger"]:
        old = old_ledger[row["qid"], row["policy"]]
        transitions.append({"qid": row["qid"], "policy": row["policy"],
                            "early_category": old["category"], "late_category": row["category"]})
    return {
        "contrasts": contrasts, "added_support_labels": added_records,
        "exchange_category_transitions": transitions,
        "added_qrels_pairs": sum(len(late_labels[q]) - len(early_labels[q]) for q in QUERY_IDS),
        "any_width_reduced": any(Fraction(x["width_reduction"]) > 0 for x in contrasts.values()),
        "primary_width_reduced": Fraction(contrasts["M-H"]["width_reduction"]) > 0,
    }


def equal(actual, expected, context):
    """Strict recursive field audit; report first differing leaf without outcomes."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict), f"{context}: expected object")
        require(actual.keys() == expected.keys(),
                f"{context}: keys differ actual={sorted(actual)} expected={sorted(expected)}")
        for key in expected:
            equal(actual[key], expected[key], f"{context}.{key}")
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected),
                f"{context}: list length/type differs")
        for i, (a, b) in enumerate(zip(actual, expected)):
            equal(a, b, f"{context}[{i}]")
    else:
        require(type(actual) is type(expected) and actual == expected,
                f"{context}: value/type differs")


def identity(path):
    return {"sha256": sha256(path), "bytes": Path(path).stat().st_size}


def check_identity(path, record, context):
    equal(identity(path), {"sha256": record["sha256"], "bytes": record["bytes"]}, context)


def check_custody(args):
    """Verify all acquired and frozen identities before interpreting input rows."""
    preflight = Path(args.preflight)
    receipts = {}
    frozen = None
    for phase, receipt_path, expected_files in (
        ("initial", args.initial_acquisition, {"A.run", "S.run", "docids.txt", "early.qrels"}),
        ("late", args.late_acquisition, {"late.qrels"}),
    ):
        receipt = read_json(receipt_path)
        require(receipt["schema"] == 1 and receipt["status"] == "passed" and
                receipt["phase"] == phase, f"{phase} acquisition failed")
        require(receipt["preflight_sha256"] == sha256(preflight), "preflight hash differs")
        require(set(receipt["inputs"]) == expected_files, "acquisition file set differs")
        if frozen is None:
            frozen = receipt["frozen"]
        else:
            equal(receipt["frozen"], frozen, "late acquisition frozen identities")
        for name, info in receipt["inputs"].items():
            check_identity(Path(args.inputs) / name, info, f"{phase} acquired {name}")
        receipts[phase] = receipt
    required_frozen = {str(p.relative_to(ROOT)) for p in (PROTOCOL, PLAN, Path(__file__).resolve())}
    require(required_frozen <= frozen.keys(), "required protocol/plan/verifier not frozen")
    for path, digest in frozen.items():
        require(sha256(ROOT / path) == digest, f"frozen identity changed: {path}")
    plan = read_json(PLAN)
    total_bytes = 0
    for phase, names in (("initial", plan["initial_keys"]), ("late", plan["late_keys"])):
        for key in names:
            item = plan["items"][key]
            record = receipts[phase]["inputs"][item["filename"]]
            require(record["bytes"] <= item["max_bytes"], f"byte ceiling {key}")
            if "expected_bytes" in item:
                require(record["bytes"] == item["expected_bytes"], f"unexpected byte length {key}")
            total_bytes += record["bytes"]
    require(total_bytes <= plan["max_total_bytes"], "total byte ceiling")
    manifests = {}
    for phase, directory, filenames in (
        ("prepare", args.prepared, {"policies.json"}),
        ("early", args.early, {"analysis.json"}),
        ("late", args.late, {"analysis.json", "revelation.json", "label-preservation.json"}),
    ):
        directory = Path(directory)
        manifest = read_json(directory / "manifest.json")
        success = read_json(directory / "success.json")
        require(success["status"] == "passed", f"{phase} not passed")
        check_identity(directory / "manifest.json", success["manifest"], f"{phase} success custody")
        require(manifest["schema"] == 1 and manifest["phase"] == phase, f"{phase} manifest")
        equal(manifest["frozen"], frozen, f"{phase} frozen identities")
        equal(manifest["tracked_before"], manifest["tracked_after"], f"{phase} before/after custody")
        for path, info in manifest["tracked_after"].items():
            check_identity(path, info, f"{phase} tracked {path}")
        require(set(manifest["outputs"]) == filenames, f"{phase} output set")
        for filename, info in manifest["outputs"].items():
            check_identity(directory / filename, info, f"{phase} output {filename}")
        for filename, info in manifest["inputs"].items():
            require(Path(info["path"]).resolve() == (Path(args.inputs) / filename).resolve(),
                    f"{phase} input path")
            check_identity(info["path"], info, f"{phase} manifest input {filename}")
        if phase != "prepare":
            check_identity(Path(args.prepared) / "policies.json", manifest["policies"],
                           f"{phase} frozen policies")
        else:
            require(manifest["labels_parsed"] is False, "prepare label boundary")
        manifests[phase] = manifest
    require(receipts["late"]["early_manifest_sha256"] == sha256(Path(args.early) / "manifest.json"),
            "late acquisition did not bind early manifest")
    return {"frozen": frozen, "downloaded_bytes": total_bytes,
            "acquisitions": {p: sha256(v) for p, v in
                             (("initial", args.initial_acquisition), ("late", args.late_acquisition))},
            "phase_manifests": {p: sha256(Path(v) / "manifest.json") for p, v in
                                (("prepare", args.prepared), ("early", args.early), ("late", args.late))}}


def source_schema(source):
    diag = source["diagnostics"]
    return {
        "full_order": source["full_order"], "retained_order": source["retained_order"],
        "details": source["details"], "full_depth": diag["full_depth"],
        "retained_depth": diag["retained_depth"], "tie_groups": diag["tied_score_groups"],
        "tied_documents": diag["tied_rows"],
        "tie_excess": diag["tied_rows"] - diag["tied_score_groups"],
        "supplied_rank_disagreements": diag["supplied_rank_disagreements"],
    }


def verify(args):
    require(not Path(args.output).exists(), "output exists; exclusive creation required")
    custody = check_custody(args)
    valid = read_docids(Path(args.inputs) / "docids.txt")
    a = read_run(Path(args.inputs) / "A.run", valid)
    s = read_run(Path(args.inputs) / "S.run", valid)
    queries, arithmetic = reconstruct(a, s)
    expected_policies = {"schema": 1, "query_ids": QUERY_IDS, "queries": {}}
    for q, data in queries.items():
        expected_policies["queries"][q] = data | {
            "sources": {p: source_schema(data["sources"][p]) for p in ("A", "S")}}
    equal(read_json(Path(args.prepared) / "policies.json"), expected_policies, "policies")
    early_labels = read_qrels(Path(args.inputs) / "early.qrels", valid)
    late_labels = read_qrels(Path(args.inputs) / "late.qrels", valid)
    mismatch, _ = label_addition(early_labels, late_labels)
    require(not mismatch, "early labels not preserved; audit stops")
    early = summaries(queries, early_labels)
    late = summaries(queries, late_labels)
    equal(read_json(Path(args.early) / "analysis.json"), early, "early analysis")
    equal(read_json(Path(args.late) / "analysis.json"), late, "late analysis")
    preservation = {"passed": True, "early_pair_count": sum(map(len, early_labels.values())),
                    "mismatches": []}
    equal(read_json(Path(args.late) / "label-preservation.json"), preservation, "preservation")
    predicted_revelation = revelation(early, late, early_labels, late_labels)
    reported_revelation = read_json(Path(args.late) / "revelation.json")
    # Object-key serialization may make query traversal lexical; records are keyed units.
    for artifact in (predicted_revelation, reported_revelation):
        artifact["added_support_labels"].sort(key=lambda x: (x["contrast"], int(x["qid"]), x["docid"]))
        artifact["exchange_category_transitions"].sort(key=lambda x: (int(x["qid"]), x["policy"]))
    equal(reported_revelation, predicted_revelation, "revelation")
    require(custody == check_custody(args), "custody changed during independent audit")
    receipt = {
        "schema": 1, "status": "passed", "verifier": identity(__file__),
        "custody": custody, "self_test": self_test(),
        "verified": {"canonical_sources": 2, "query_count": 30,
                     "policies_per_query": 5, "analysis_phases": 2,
                     "all_policy_and_analysis_fields": True,
                     "label_preservation": True, "revelation_fields": True},
        "arithmetic_audit": arithmetic,
        "limits": ["No primary algorithm imported or inspected; source bytes hashed only.",
                   "Protocol floating RRF determines saved policies; exact integer order is audited separately.",
                   "Label bounds remain conditional on the supplied official query/document grades.",
                   "This reproduces one fixed panel and is not an independent effectiveness sample."],
    }
    with Path(args.output).open("x") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return receipt


def self_test():
    """Every unknown-label assignment for 81 partial binary label tables."""
    docs = ("a", "b", "c", "d")
    left, right = ("a", "b", "c"), ("b", "d")
    completions = 0
    for table in itertools.product((None, 0, 1), repeat=4):
        known = {d: v for d, v in zip(docs, table) if v is not None}
        unknown = [d for d, v in zip(docs, table) if v is None]
        deltas = []
        interval = bound(left, right, known)
        for values in itertools.product((0, 1), repeat=len(unknown)):
            full = known | dict(zip(unknown, values))
            deltas.append(p10(left, full) - p10(right, full))
            completions += 1
        require(Fraction(interval["lower"]) == min(deltas), "sharp lower failed")
        require(Fraction(interval["upper"]) == max(deltas), "sharp upper failed")
        require(Fraction(interval["lower"]) <= Fraction(interval["known"]) <=
                Fraction(interval["upper"]), "zero convention outside bounds")
        for d in unknown:
            for value in (0, 1, 2):
                extended = bound(left, right, known | {d: value})
                require(Fraction(extended["lower"]) >= Fraction(interval["lower"]), "lower widened")
                require(Fraction(extended["upper"]) <= Fraction(interval["upper"]), "upper widened")
    require(bound(("x",), ("x",), {})["width"] == "0/1", "shared cancellation")
    require(exchange({"x": 1, "y": 0}, "x", "y") == "rescue", "rescue")
    require(exchange({"x": 0, "y": 2}, "x", "y") == "harm", "harm")
    require(exchange({"x": 1, "y": 2}, "x", "y") == "neutral", "neutral")
    require(exchange({"x": 1}, "x", "y") == "unresolved", "unknown")
    aa = [f"a{i:03d}" for i in range(100)]
    def synthetic_source(order):
        return {q: {"full_order": order.copy(), "retained_order": order.copy()}
                for q in QUERY_IDS}
    identical, _ = reconstruct(synthetic_source(aa), synthetic_source(aa))
    require(all(not identical[q]["eligible"] for q in QUERY_IDS), "no opportunity")
    generic_first = [aa[-1], "minority"] + aa[:-1]
    separated, _ = reconstruct(synthetic_source(aa), synthetic_source(generic_first[:100]))
    require(all(separated[q]["eligible"] for q in QUERY_IDS), "expected opportunity")
    require(all(separated[q]["m"] == "minority" and separated[q]["j"] == aa[-1]
                for q in QUERY_IDS), "generic vs minority admissions")
    require(all(not separated[q]["m_equals_j"] for q in QUERY_IDS), "distinct exchanges")
    labels = {q: {"minority": 1, separated[q]["displaced"]: 0} for q in QUERY_IDS}
    summary = summaries(separated, labels)
    require(summary["contrasts"]["M-H"]["lower"] == "1/10" and
            summary["contrasts"]["M-H"]["upper"] == "1/10", "aggregate exact rescue")
    require(summary["exchange_counts"]["M"]["rescue"] == 30 and
            summary["exchange_counts"]["J"]["unresolved"] == 30, "ledger aggregate")
    minority_first = ["minority"] + aa[:99]
    same, _ = reconstruct(synthetic_source(aa), synthetic_source(minority_first))
    require(all(same[q]["eligible"] and same[q]["m_equals_j"] for q in QUERY_IDS),
            "matched minority/generic exchange")
    synthetic_docs = ["z", "a", "p0", "p1"] + [f"x{i}" for i in range(6)]
    synthetic_scores = ["2.0", "2.00", "1." + "0" * 30 + "1",
                        "1." + "0" * 30 + "2"] + ["0"] * 6
    rows = [f"{q} Q0 {d} {r} {score} synthetic"
            for q in QUERY_IDS
            for r, (d, score) in enumerate(zip(synthetic_docs, synthetic_scores), 1)]
    with tempfile.TemporaryDirectory(prefix="cycle17-independent-selftest-") as temp:
        path = Path(temp) / "synthetic.run"
        path.write_text("\n".join(rows) + "\n")
        parsed = read_run(path, set(synthetic_docs))
        require(parsed["1"]["full_order"][:4] == ["a", "z", "p1", "p0"],
                "exact decimal precision and tie order")
        path.write_text("\n".join(rows + [rows[0]]) + "\n")
        try:
            read_run(path, set(synthetic_docs))
        except ValueError as exc:
            require("duplicate run pair" in str(exc), "wrong duplicate rejection")
        else:
            raise ValueError("duplicate run accepted")
        qpath = Path(temp) / "synthetic.qrels"
        qpath.write_text("".join(f"{q} 0.5 a 0\n{q} 1 z 2\n" for q in QUERY_IDS))
        early = read_qrels(qpath, set(synthetic_docs))
        late = {q: grades | {"p0": 1} for q, grades in early.items()}
        failures, added = label_addition(early, late)
        require(not failures and all(v == ["p0"] for v in added.values()),
                "addition preservation")
        late["1"]["a"] = 1
        del late["2"]["z"]
        failures, _ = label_addition(early, late)
        require(len(failures) == 2, "label revision/removal detection")
    return {"partial_tables": 81, "binary_completions": completions,
            "shared_cancellation": True, "addition_nesting": True,
            "exchange_categories": True, "no_eligibility": True,
            "m_equals_j_and_differs": True, "exact_decimal_ties": True,
            "duplicate_rejection": True, "qrel_preservation_gate": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--inputs")
    parser.add_argument("--prepared")
    parser.add_argument("--early")
    parser.add_argument("--late")
    parser.add_argument("--output")
    parser.add_argument("--initial-acquisition", default=str(ROOT / "_sessions/evidence/2026-09-25-cycle17-initial-acquisition.json"))
    parser.add_argument("--late-acquisition", default=str(ROOT / "_sessions/evidence/2026-09-25-cycle17-late-acquisition.json"))
    parser.add_argument("--preflight", default=str(ROOT / "_sessions/evidence/2026-09-25-cycle17-preflight.json"))
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
    else:
        for field in ("inputs", "prepared", "early", "late", "output"):
            if getattr(args, field) is None:
                parser.error(f"--{field} is required for actual-input verification")
        receipt = verify(args)
        print(json.dumps({"status": receipt["status"], "output": args.output,
                          "verified": receipt["verified"]}, sort_keys=True))


if __name__ == "__main__":
    main()
