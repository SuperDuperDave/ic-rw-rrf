#!/usr/bin/env python3
"""Frozen Cycle17 one-slot exchange and addition-only label revelation.

The CLI deliberately separates label-free preparation, early analysis and late
analysis. This module uses only the standard library and never acquires inputs.
"""

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import signal
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "_sessions/cycles/2026-09-25-cycle17-exchange-protocol.md"
PLAN = "_sessions/cycles/2026-09-25-cycle17-input-plan.json"
SOURCE = "evaluation/cycle17_minority_exchange.py"
TESTS = "evaluation/tests/test_cycle17_minority_exchange.py"
QUERY_IDS = tuple(str(i) for i in range(1, 31))
POLICIES = ("A", "S", "H", "M", "J")
CONTRASTS = (("M", "H"), ("M", "J"), ("M", "S"), ("H", "S"), ("H", "A"))


class ContractError(ValueError):
    """A frozen gate failed; no alternate input or policy is selected."""


def require(condition, message):
    if not condition:
        raise ContractError(message)


def rational(value):
    value = Fraction(value)
    return f"{value.numerator}/{value.denominator}"


def valid_id(value):
    return bool(value) and all(33 <= ord(c) <= 126 for c in value)


def parse_docids(text):
    ids = set()
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        require(len(fields) == 1 and valid_id(fields[0]), f"docids line {number}: invalid ID")
        require(fields[0] not in ids, f"docids line {number}: duplicate ID")
        ids.add(fields[0])
    require(ids, "empty document universe")
    return ids


def decimal_number(value, description):
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ContractError(description + ": invalid numeric field") from exc
    require(number.is_finite(), description + ": nonfinite numeric field")
    return number


def parse_run(text, docids, query_ids=QUERY_IDS):
    """Canonicalize all submitted rows by exact numeric score, then string ID."""
    rows = {}
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        require(len(fields) == 6, f"run line {number}: expected six fields")
        qid, unused, doc, supplied, score, tag = fields
        require(qid in query_ids, f"run line {number}: unexpected query {qid}")
        require(doc in docids, f"run line {number}: ID outside Round1 universe")
        require(re.fullmatch(r"[1-9][0-9]*", supplied) is not None,
                f"run line {number}: supplied rank must be positive integer")
        require(valid_id(unused) and valid_id(tag), f"run line {number}: invalid token")
        numeric = decimal_number(score, f"run line {number}")
        bucket = rows.setdefault(qid, {})
        require(doc not in bucket, f"run line {number}: duplicate query/document")
        bucket[doc] = {"score": score, "supplied_rank": int(supplied), "numeric": numeric}
    require(set(rows) == set(query_ids), "run query cohort must exactly match fixed cohort")
    result = {}
    for qid in query_ids:
        bucket = rows[qid]
        require(10 <= len(bucket) <= 1000, f"query {qid}: full run depth outside 10..1000")
        # Stable sorts avoid Decimal unary minus, which can round under its context.
        ordered = sorted(bucket)
        ordered.sort(key=lambda doc: bucket[doc]["numeric"], reverse=True)
        score_counts = Counter(row["numeric"] for row in bucket.values())
        tied = [count for count in score_counts.values() if count > 1]
        details = {doc: {"score": bucket[doc]["score"],
                         "supplied_rank": bucket[doc]["supplied_rank"],
                         "canonical_rank": rank}
                   for rank, doc in enumerate(ordered, 1)}
        result[qid] = {
            "full_order": ordered, "retained_order": ordered[:100], "details": details,
            "full_depth": len(ordered), "retained_depth": min(100, len(ordered)),
            "tie_groups": len(tied), "tied_documents": sum(tied),
            "tie_excess": sum(count - 1 for count in tied),
            "supplied_rank_disagreements": sum(row["supplied_rank"] != row["canonical_rank"]
                                                for row in details.values()),
        }
    return result


def parse_qrels(text, docids, query_ids=QUERY_IDS):
    labels = {}
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        require(len(fields) == 4, f"qrels line {number}: expected four fields")
        qid, iteration, doc, grade = fields
        require(qid in query_ids, f"qrels line {number}: unexpected query {qid}")
        require(doc in docids, f"qrels line {number}: ID outside Round1 universe")
        require(grade in ("0", "1", "2"), f"qrels line {number}: invalid grade")
        require(decimal_number(iteration, f"qrels line {number}") > 0,
                f"qrels line {number}: judgment round must be positive")
        bucket = labels.setdefault(qid, {})
        require(doc not in bucket, f"qrels line {number}: duplicate query/document")
        bucket[doc] = int(grade)
    require(set(labels) == set(query_ids), "qrels query cohort must exactly match fixed cohort")
    return labels


def build_query(a, s):
    """Construct all five policies without consulting labels."""
    a_order, s_order = a["retained_order"], s["retained_order"]
    ranks_a = {doc: rank for rank, doc in enumerate(a_order, 1)}
    ranks_s = {doc: rank for rank, doc in enumerate(s_order, 1)}
    union = sorted(set(a_order) | set(s_order))
    scores = {doc: math.fsum(1.0 / (60 + ranks[doc]) if doc in ranks else 0.0
                             for ranks in (ranks_a, ranks_s)) for doc in union}
    hybrid = sorted(union, key=lambda doc: (-scores[doc], doc))
    h = hybrid[:10]
    s_only = set(s_order) - set(a_order)
    minority_head = [doc for doc in s_order[:10] if doc in s_only]
    eligible = not (set(h) & s_only) and bool(minority_head)
    m = minority_head[0] if eligible else None
    j = next((doc for doc in s_order[:10] if doc not in h), None) if eligible else None
    require(not eligible or (m not in h and j is not None), "eligible policy feasibility failed")
    policies = {"A": a_order[:10], "S": s_order[:10], "H": h,
                "M": h[:9] + [m] if eligible else list(h),
                "J": h[:9] + [j] if eligible else list(h)}
    require(all(len(items) == 10 and len(set(items)) == 10 for items in policies.values()),
            "policy head is not ten unique documents")
    return {"sources": {"A": a, "S": s}, "policies": policies,
            "hybrid_order": hybrid, "hybrid_scores": scores,
            "eligible": eligible, "m": m, "j": j,
            "displaced": h[9] if eligible else None, "m_equals_j": policies["M"] == policies["J"]}


def prepare_policies(a, s, query_ids=QUERY_IDS):
    return {"schema": 1, "query_ids": list(query_ids),
            "queries": {qid: build_query(a[qid], s[qid]) for qid in query_ids}}


def interval_fields(known, lower, upper):
    if lower > 0:
        sign, decision = "strict_positive", "all_completions_positive"
    elif upper < 0:
        sign, decision = "strict_negative", "positive_excluded"
    elif lower == upper == 0:
        sign, decision = "point_zero", "positive_excluded"
    elif upper == 0:
        sign, decision = "nonpositive_with_zero", "positive_excluded"
    elif lower == 0:
        sign, decision = "nonnegative_with_zero", "sign_unresolved"
    else:
        sign, decision = "crosses_zero", "sign_unresolved"
    return {"known": rational(known), "benchmark_zero": rational(known),
            "lower": rational(lower), "upper": rational(upper), "width": rational(upper - lower),
            "sign": sign, "decision": decision}


def contrast_bounds(left, right, labels):
    """Sharp bounds after cancellation; each unknown pair is a free binary variable."""
    require(len(left) == len(right) == 10, "P@10 contrast requires ten entries per policy")
    require(len(set(left)) == len(set(right)) == 10, "duplicate policy document")
    plus, minus = set(left) - set(right), set(right) - set(left)
    support = []
    known, lower_unknown, upper_unknown = Fraction(0), Fraction(0), Fraction(0)
    for doc in sorted(plus | minus):
        coefficient = Fraction(1 if doc in plus else -1, 10)
        grade = labels.get(doc)
        require(grade is None or grade in (0, 1, 2), "invalid label")
        if grade is None:
            lower_unknown += min(coefficient, 0)
            upper_unknown += max(coefficient, 0)
        else:
            known += coefficient * int(grade > 0)
        support.append({"docid": doc, "coefficient": rational(coefficient), "grade": grade})
    result = interval_fields(known, known + lower_unknown, known + upper_unknown)
    result.update(support=support, unknown_support=sum(row["grade"] is None for row in support))
    return result


def average_bounds(rows):
    require(rows, "cannot average empty query set")
    def mean(key):
        return sum((Fraction(row[key]) for row in rows), Fraction()) / len(rows)
    result = interval_fields(mean("known"), mean("lower"), mean("upper"))
    result.update(query_count=len(rows), unknown_support=sum(row["unknown_support"] for row in rows))
    return result


def document_observation(doc, query, labels):
    if doc is None:
        return None
    result = {"docid": doc, "grade": labels.get(doc)}
    for source in ("A", "S"):
        data = query["sources"][source]
        details = data["details"].get(doc)
        rank = details["canonical_rank"] if details else None
        result[source + "_full_rank"] = rank
        result[source + "_full_member"] = rank is not None
        result[source + "_retained_rank"] = rank if doc in data["retained_order"] else None
        result[source + "_retained_member"] = doc in data["retained_order"]
    return result


def exchange_row(qid, policy, query, labels):
    changed = query["eligible"]
    admitted = document_observation(query["m" if policy == "M" else "j"], query, labels)
    displaced = document_observation(query["displaced"], query, labels)
    category = "unchanged"
    if changed:
        positive, old = admitted["grade"], displaced["grade"]
        if positive is None or old is None:
            category = "unresolved"
        elif positive > 0 and old == 0:
            category = "rescue"
        elif positive == 0 and old > 0:
            category = "harm"
        else:
            category = "neutral"
    return {"qid": qid, "policy": policy, "changed": changed, "category": category,
            "admitted": admitted, "displaced": displaced,
            "known_positive_admission": bool(admitted and admitted["grade"] in (1, 2)),
            "explicit_negative_admission": bool(admitted and admitted["grade"] == 0),
            "known_positive_displacement": bool(displaced and displaced["grade"] in (1, 2))}


def analyze(policies, labels):
    qids, queries = policies["query_ids"], policies["queries"]
    require(set(qids) == set(labels), "analysis label cohort differs from saved policies")
    per_query, ledger = {}, []
    eligible = [qid for qid in qids if queries[qid]["eligible"]]
    for qid in qids:
        query, qlabels = queries[qid], labels[qid]
        per_query[qid] = {
            "contrasts": {left + "-" + right: contrast_bounds(query["policies"][left],
                                                              query["policies"][right], qlabels)
                          for left, right in CONTRASTS},
            "benchmark": {policy: rational(Fraction(sum(qlabels.get(doc, 0) > 0 for doc in head), 10))
                          for policy, head in query["policies"].items()},
        }
        ledger.extend(exchange_row(qid, policy, query, qlabels) for policy in ("M", "J"))
    contrasts = {left + "-" + right: average_bounds(
        [per_query[qid]["contrasts"][left + "-" + right] for qid in qids]) for left, right in CONTRASTS}
    triggered = {name: average_bounds([per_query[qid]["contrasts"][name] for qid in eligible])
                 for name in contrasts} if eligible else None
    counts = {}
    for policy in ("M", "J"):
        rows = [row for row in ledger if row["policy"] == policy]
        counts[policy] = {category: sum(row["category"] == category for row in rows)
                          for category in ("unchanged", "rescue", "harm", "neutral", "unresolved")}
        counts[policy].update({key: sum(row[key] for row in rows)
                               for key in ("known_positive_admission", "explicit_negative_admission",
                                           "known_positive_displacement")})
    benchmark = {policy: rational(sum((Fraction(per_query[qid]["benchmark"][policy]) for qid in qids),
                                      Fraction()) / len(qids)) for policy in POLICIES}
    return {"schema": 1, "query_count": len(qids), "eligible_query_ids": eligible,
            "eligible_count": len(eligible),
            "m_equals_j_count": sum(queries[qid]["m_equals_j"] for qid in qids),
            "eligible_m_equals_j_count": sum(queries[qid]["m_equals_j"] for qid in eligible),
            "contrasts": contrasts, "triggered_only_contrasts": triggered,
            "per_query": per_query, "exchange_ledger": ledger, "exchange_counts": counts,
            "benchmark": {"convention": "binary P@10 with unknown labels assigned zero", "policies": benchmark},
            "primary_decision": "no_opportunity" if not eligible else contrasts["M-H"]["decision"],
            "qrels_pair_count": sum(len(bucket) for bucket in labels.values())}


def label_mismatches(early, late):
    return [{"qid": qid, "docid": doc, "early_grade": grade,
             "late_grade": late.get(qid, {}).get(doc),
             "kind": "removed" if doc not in late.get(qid, {}) else "revised"}
            for qid in early for doc, grade in sorted(early[qid].items())
            if late.get(qid, {}).get(doc) != grade]


def compare_phases(early, late, early_labels, late_labels):
    require(not label_mismatches(early_labels, late_labels), "early grades removed or revised")
    changes, added_support = {}, []
    for name, before in early["contrasts"].items():
        after = late["contrasts"][name]
        require(Fraction(before["lower"]) <= Fraction(after["lower"]) <= Fraction(after["upper"]) <=
                Fraction(before["upper"]), "late interval does not nest: " + name)
        influenced = []
        for qid, query in early["per_query"].items():
            old, new = query["contrasts"][name], late["per_query"][qid]["contrasts"][name]
            require(Fraction(old["lower"]) <= Fraction(new["lower"]) <= Fraction(new["upper"]) <=
                    Fraction(old["upper"]), "late query interval does not nest")
            for row in old["support"]:
                doc = row["docid"]
                if row["grade"] is None and doc in late_labels[qid]:
                    coefficient, grade = Fraction(row["coefficient"]), late_labels[qid][doc]
                    value = coefficient * int(grade > 0)
                    item = {"contrast": name, "qid": qid, "docid": doc, "grade": grade,
                            "coefficient": row["coefficient"],
                            "query_lower_increase": rational(value - min(coefficient, 0)),
                            "query_upper_decrease": rational(max(coefficient, 0) - value),
                            "influence": "raises_lower" if value > min(coefficient, 0) else "lowers_upper"}
                    influenced.append(item)
                    added_support.append(item)
        changes[name] = {"early_width": before["width"], "late_width": after["width"],
                         "width_reduction": rational(Fraction(before["width"]) - Fraction(after["width"])),
                         "early_sign": before["sign"], "late_sign": after["sign"],
                         "sign_changed": before["sign"] != after["sign"],
                         "early_decision": before["decision"], "late_decision": after["decision"],
                         "added_labels_on_support": len(influenced)}
    before_rows = {(row["qid"], row["policy"]): row for row in early["exchange_ledger"]}
    transitions = [{"qid": row["qid"], "policy": row["policy"],
                    "early_category": before_rows[(row["qid"], row["policy"])]["category"],
                    "late_category": row["category"]} for row in late["exchange_ledger"]]
    return {"contrasts": changes, "added_support_labels": added_support,
            "exchange_category_transitions": transitions,
            "added_qrels_pairs": sum(len(late_labels[qid]) - len(early_labels[qid]) for qid in early_labels),
            "any_width_reduced": any(Fraction(row["width_reduction"]) > 0 for row in changes.values()),
            "primary_width_reduced": Fraction(changes["M-H"]["width_reduction"]) > 0}


def identity(path):
    path = Path(path)
    before = path.stat()
    digest = hashlib.sha256()
    consumed = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            consumed += len(chunk)
            digest.update(chunk)
    after = path.stat()
    require(consumed == before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
            "file changed during hashing: " + str(path))
    return {"sha256": digest.hexdigest(), "bytes": consumed}


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as output:
        json.dump(value, output, sort_keys=True, indent=2, allow_nan=False)
        output.write("\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_frozen(frozen):
    require(set((PROTOCOL, PLAN, SOURCE, TESTS)) <= set(frozen), "acquisition omitted required frozen identities")
    tracked = {}
    for name, expected in frozen.items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT) and not Path(name).is_absolute(), "frozen path escapes repository")
        observed = identity(path)
        require(observed["sha256"] == expected, "frozen identity changed: " + name)
        tracked[str(path)] = observed
    return tracked


def acquisition_inputs(receipt_path, input_paths, frozen=None):
    receipt_path = Path(receipt_path).resolve()
    receipt_identity = identity(receipt_path)
    receipt = read_json(receipt_path)
    require(receipt.get("status") == "passed", "acquisition receipt did not pass")
    require(frozen is None or receipt["frozen"] == frozen, "late acquisition used different frozen identities")
    tracked = check_frozen(receipt["frozen"])
    tracked[str(receipt_path)] = receipt_identity
    require(set(receipt["inputs"]) == set(input_paths), "acquisition input inventory differs")
    inputs = {}
    plan = read_json(ROOT / PLAN)
    specs = {spec["filename"]: spec for spec in plan["items"].values()}
    for name, path in input_paths.items():
        path = Path(path).resolve()
        observed = identity(path)
        require(observed == {key: receipt["inputs"][name][key] for key in ("sha256", "bytes")},
                "acquired input identity changed: " + name)
        spec = specs[name]
        require(0 < observed["bytes"] <= spec["max_bytes"], "input byte cap failed: " + name)
        require("expected_bytes" not in spec or observed["bytes"] == spec["expected_bytes"],
                "input declared byte length changed: " + name)
        inputs[name] = {"path": str(path), **observed}
        tracked[str(path)] = observed
    return receipt, inputs, tracked


def verify_tracked(tracked):
    current = {path: identity(path) for path in tracked}
    require(current == tracked, "tracked source, receipt, input, or prior artifact changed")
    return current


def load_phase(directory, expected_phase):
    directory = Path(directory).resolve()
    manifest_path, success_path = directory / "manifest.json", directory / "success.json"
    manifest, success = read_json(manifest_path), read_json(success_path)
    require(success.get("status") == "passed" and success["manifest"] == identity(manifest_path),
            "prior phase success/manifest integrity failed")
    require(manifest["phase"] == expected_phase, "incorrect prior phase")
    tracked = dict(manifest["tracked_after"])
    verify_tracked(tracked)
    tracked[str(manifest_path)] = identity(manifest_path)
    tracked[str(success_path)] = identity(success_path)
    for filename, expected in manifest["outputs"].items():
        path = directory / filename
        require(identity(path) == expected, "prior output changed: " + filename)
        tracked[str(path)] = expected
    return manifest, tracked


def finish_phase(output, phase, tracked, metadata, artifacts):
    after = verify_tracked(tracked)
    outputs = {name: identity(output / name) for name in artifacts}
    manifest = {"schema": 1, "phase": phase, "command": sys.argv,
                "tracked_before": tracked, "tracked_after": after, "outputs": outputs, **metadata}
    write_json(output / "manifest.json", manifest)
    write_json(output / "success.json", {"status": "passed", "manifest": identity(output / "manifest.json")})


def run_prepare(args, output):
    inputs_dir = Path(args.inputs)
    names = ("A.run", "S.run", "docids.txt", "early.qrels")
    receipt, inputs, tracked = acquisition_inputs(args.acquisition, {name: inputs_dir / name for name in names})
    # Identity-only reading of early.qrels above is intentional; no label parsing here.
    docids = parse_docids(Path(inputs["docids.txt"]["path"]).read_text(encoding="utf-8"))
    a = parse_run(Path(inputs["A.run"]["path"]).read_text(encoding="utf-8"), docids)
    s = parse_run(Path(inputs["S.run"]["path"]).read_text(encoding="utf-8"), docids)
    write_json(output / "policies.json", prepare_policies(a, s))
    finish_phase(output, "prepare", tracked, {"frozen": receipt["frozen"], "inputs": inputs,
                  "acquisition": str(Path(args.acquisition).resolve()), "labels_parsed": False}, ["policies.json"])


def run_early(args, output):
    prepared = Path(args.prepared).resolve()
    manifest, tracked = load_phase(prepared, "prepare")
    check_frozen(manifest["frozen"])
    # All label-free policy artifacts already exist and have been rehashed.
    policies = read_json(prepared / "policies.json")
    docids = parse_docids(Path(manifest["inputs"]["docids.txt"]["path"]).read_text(encoding="utf-8"))
    labels = parse_qrels(Path(manifest["inputs"]["early.qrels"]["path"]).read_text(encoding="utf-8"), docids)
    write_json(output / "analysis.json", analyze(policies, labels))
    finish_phase(output, "early", tracked, {"frozen": manifest["frozen"], "inputs": manifest["inputs"],
                 "prepared": str(prepared), "policies": identity(prepared / "policies.json")}, ["analysis.json"])


def run_late(args, output):
    prepared, early_dir = Path(args.prepared).resolve(), Path(args.early).resolve()
    prepared_manifest, prepared_tracked = load_phase(prepared, "prepare")
    early_manifest, tracked = load_phase(early_dir, "early")
    require(early_manifest["prepared"] == str(prepared), "early phase belongs to different preparation")
    require(early_manifest["policies"] == identity(prepared / "policies.json"), "early policy identity mismatch")
    receipt, late_inputs, late_tracked = acquisition_inputs(
        args.late_acquisition, {"late.qrels": Path(args.late_input)}, frozen=prepared_manifest["frozen"])
    require(receipt.get("early_manifest_sha256") == identity(early_dir / "manifest.json")["sha256"],
            "late acquisition did not bind this completed early phase")
    tracked.update(prepared_tracked)
    tracked.update(late_tracked)
    # Loading frozen bytes is the only policy path in this phase; no reconstruction.
    policies = read_json(prepared / "policies.json")
    inputs = prepared_manifest["inputs"]
    docids = parse_docids(Path(inputs["docids.txt"]["path"]).read_text(encoding="utf-8"))
    early_labels = parse_qrels(Path(inputs["early.qrels"]["path"]).read_text(encoding="utf-8"), docids)
    late_labels = parse_qrels(Path(args.late_input).read_text(encoding="utf-8"), docids)
    mismatches = label_mismatches(early_labels, late_labels)
    write_json(output / "label-preservation.json", {"passed": not mismatches,
               "early_pair_count": sum(map(len, early_labels.values())), "mismatches": mismatches})
    require(not mismatches, "late qrels removed or revised early grades; see label-preservation.json")
    late_analysis = analyze(policies, late_labels)
    write_json(output / "analysis.json", late_analysis)
    write_json(output / "revelation.json", compare_phases(read_json(early_dir / "analysis.json"),
                                                           late_analysis, early_labels, late_labels))
    finish_phase(output, "late", tracked, {"frozen": prepared_manifest["frozen"],
                 "inputs": {**inputs, **late_inputs}, "prepared": str(prepared), "early": str(early_dir),
                 "policies": identity(prepared / "policies.json"),
                 "acquisition": str(Path(args.late_acquisition).resolve())},
                 ["analysis.json", "revelation.json", "label-preservation.json"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="phase", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--inputs", required=True)
    prepare.add_argument("--acquisition", required=True)
    early = subparsers.add_parser("early")
    early.add_argument("--prepared", required=True)
    late = subparsers.add_parser("late")
    late.add_argument("--prepared", required=True)
    late.add_argument("--early", required=True)
    late.add_argument("--late-input", required=True)
    late.add_argument("--late-acquisition", required=True)
    for subparser in (prepare, early, late):
        subparser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    created = False
    started = time.monotonic()
    def timeout(signum, frame):
        raise ContractError("phase exceeded 300 seconds")
    old_handler = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    try:
        output.mkdir(parents=True, exist_ok=False)
        created = True
        {"prepare": run_prepare, "early": run_early, "late": run_late}[args.phase](args, output)
        print(json.dumps({"status": "passed", "phase": args.phase, "output": str(output)}))
        return 0
    except Exception as exc:
        failure = {"status": "failed", "phase": args.phase, "error_type": type(exc).__name__,
                   "error": str(exc), "command": sys.argv, "elapsed_seconds": time.monotonic() - started}
        failure_path = (output / "failure.json" if created else
                        output.parent / (output.name + f".failure-{time.time_ns()}.json"))
        try:
            write_json(failure_path, failure)
            failure["failure_artifact"] = str(failure_path)
        except OSError as failure_error:
            failure["failure_artifact_error"] = str(failure_error)
        print(json.dumps(failure), file=sys.stderr)
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


if __name__ == "__main__":
    raise SystemExit(main())
