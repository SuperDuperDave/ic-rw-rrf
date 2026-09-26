#!/usr/bin/env python3
"""Independently verify the frozen Cycle 16 support census; standard library only.

Run --self-test without touching collection inputs. Real verification requires
--result-dir and reads only the eight protocol inputs and custody metadata.
No primary implementation is imported or executed; no ranking is generated.
"""

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import heapq
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = "19139bdd061fd2e51e529d7411264014e0b093a3"
LEXICAL = ("bm25", "bm25_tuned", "tfidf", "ql_dirichlet")
RUNS = LEXICAL + ("S", "P", "B")
PARTITIONS = ("U-and-S", "U-only", "S-only", "neither")
CYCLE15 = "results/cycle15-2026-09-12"
INPUTS = {name: f"{CYCLE15}/transfer/{name}.trec" for name in RUNS}
INPUTS["qrels"] = f"{CYCLE15}/independent-audit/official.qrels"
METADATA = (
    f"{CYCLE15}/transfer/manifest.json",
    f"{CYCLE15}/independent-audit/B.official-command.json",
)
PROTOCOL = "_sessions/cycles/2026-09-25-cycle16-support-protocol.md"
PRIMARY = "evaluation/cycle16_support_census.py"
COMMON = math.lcm(*range(61, 261))
INTERPRETATION = "post hoc descriptive development; no effectiveness or relevance inferred for unjudged documents"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    size = path.stat().st_size
    sha = hashlib.sha256()
    blob = hashlib.sha1(f"blob {size}\0".encode("ascii"))
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
            blob.update(block)
    return {"bytes": size, "sha256": sha.hexdigest(), "git-blob-sha1": blob.hexdigest()}


def json_read(path):
    def unique_pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, f"duplicate JSON key: {key}")
            out[key] = value
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


def valid_id(value):
    return bool(value) and all(c.isprintable() and not c.isspace() for c in value)


def read_qrels(path):
    positives = {}
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            fields = line.split()
            require(len(fields) == 4, f"{path}:{number}: qrel fields")
            qid, iteration, docid, grade = fields
            require(valid_id(qid) and valid_id(docid), "invalid qrel ID")
            require(iteration == "0" and grade == "1", "nonbinary or invalid qrel")
            bucket = positives.setdefault(qid, set())
            require(docid not in bucket, "duplicate qrel pair")
            bucket.add(docid)
    require(bool(positives), "empty qrels")
    return positives


def read_run(path, name, cohort, full_depth=True):
    rows = {}
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            fields = line.split()
            require(len(fields) == 6, f"{path}:{number}: run fields")
            qid, iteration, docid, rank_text, score_text, tag = fields
            require(valid_id(qid) and valid_id(docid) and valid_id(tag), "invalid run ID")
            require(iteration == "Q0", "invalid run iteration")
            require(re.fullmatch(r"[0-9]+", rank_text) is not None, "noninteger rank")
            rank = int(rank_text)
            require(rank > 0, "nonpositive rank")
            try:
                score = Decimal(score_text)
            except InvalidOperation as exc:
                raise ValueError("invalid run score") from exc
            require(score.is_finite(), "nonfinite run score")
            bucket = rows.setdefault(qid, {})
            require(docid not in bucket, "duplicate run document")
            bucket[docid] = rank
    require(set(rows) == set(cohort), f"{name}: cohort mismatch")
    for qid, ranks in rows.items():
        n = len(ranks)
        require(sorted(ranks.values()) == list(range(1, n + 1)), "noncontiguous ranks")
        if name in LEXICAL:
            require(n <= 200, "lexical depth exceeds 200")
        elif name == "S":
            require(n == 1000 if full_depth else n <= 1000, "invalid S depth")
        elif name == "P":
            require(n <= 1000, "P depth exceeds 1000")
        elif name == "B":
            require(n >= 10, "B depth below 10")
    return rows


def fraction_text(numerator, denominator):
    divisor = math.gcd(numerator, denominator)
    numerator //= divisor
    denominator //= divisor
    return str(numerator) if denominator == 1 else f"{numerator}/{denominator}"


def certificate(lexical, s_ranks):
    # A fixed integer denominator is independent of Fraction-based scoring.
    totals = Counter()
    for ranks in lexical:
        for docid, rank in ranks.items():
            totals[docid] += COMMON // (60 + rank)
    outsiders = s_ranks.keys() - totals.keys()
    tenth = heapq.nlargest(10, totals.values())[-1] if len(totals) >= 10 else None
    best_rank = min((s_ranks[d] for d in outsiders), default=None)
    T = fraction_text(tenth, COMMON) if tenth is not None else None
    V = fraction_text(1, 60 + best_rank) if best_rank is not None else None
    if best_rank is None:
        reason = "no_S-only_candidates"
    elif tenth is None:
        reason = "fewer_than_ten_U_candidates"
    elif tenth * (60 + best_rank) > COMMON:
        reason = "strict_T_gt_V"
    else:
        reason = "T_le_V"
    return {"T": T, "V": V, "certified": reason == "strict_T_gt_V", "reason": reason}


def reconstruct(runs, positives):
    perquery, perpositive = [], []
    for qid in sorted(positives):
        local = {name: runs[name][qid] for name in RUNS}
        U = set().union(*(local[name] for name in LEXICAL))
        require(U <= local["P"].keys(), f"{qid}: lexical candidate missing from P")
        s_only = local["S"].keys() - U
        row = {
            "qid": qid, "known_positives": len(positives[qid]),
            "positive_partition": dict.fromkeys(PARTITIONS, 0),
            "depths": {name: len(local[name]) for name in RUNS},
            "U_candidates": len(U), "S_only_candidates": len(s_only),
            "S_only_positive_head": 0, "S_only_positive_deep": 0,
            "S_only_positive_inside_P": 0, "S_only_positive_outside_P": 0,
            "B_top10_S_only_entries": [],
            "exclusion_certificate": certificate([local[name] for name in LEXICAL], local["S"]),
        }
        for docid in sorted(positives[qid]):
            in_u, in_s = docid in U, docid in local["S"]
            partition = {(True, True): "U-and-S", (True, False): "U-only",
                         (False, True): "S-only", (False, False): "neither"}[in_u, in_s]
            row["positive_partition"][partition] += 1
            if partition == "S-only":
                band = "head" if local["S"][docid] <= 10 else "deep"
                access = "inside_P" if docid in local["P"] else "outside_P"
                row[f"S_only_positive_{band}"] += 1
                row[f"S_only_positive_{access}"] += 1
            perpositive.append({
                "qid": qid, "docid": docid, "partition": partition,
                "in_P": docid in local["P"],
                "S_rank": local["S"].get(docid), "P_rank": local["P"].get(docid),
                "B_rank": local["B"].get(docid),
                "lexical_ranks": {name: local[name].get(docid) for name in LEXICAL},
            })
        for docid in sorted(local["B"], key=local["B"].get):
            rank = local["B"][docid]
            if rank <= 10 and docid in s_only:
                row["B_top10_S_only_entries"].append({
                    "docid": docid, "B_rank": rank, "S_rank": local["S"][docid],
                    "in_P": docid in local["P"],
                    "explicit_qrel_positive": docid in positives[qid],
                })
        require(not (row["exclusion_certificate"]["certified"] and
                     row["B_top10_S_only_entries"]), "B contradicts strict exclusion certificate")
        perquery.append(row)
    return perquery, perpositive


def aggregate(rows, interpretation):
    partition = {p: sum(r["positive_partition"][p] for r in rows) for p in PARTITIONS}
    entries = [entry for row in rows for entry in row["B_top10_S_only_entries"]]
    judged = sum(entry["explicit_qrel_positive"] for entry in entries)
    out = {
        "interpretation": interpretation, "query_count": len(rows),
        "known_positive_pairs": sum(r["known_positives"] for r in rows),
        "positive_partition": partition,
        "positive_partition_query_counts": {
            p: sum(r["positive_partition"][p] > 0 for r in rows) for p in PARTITIONS},
        "B_top10": {"denominator": 10 * len(rows), "S_only_entries": len(entries),
                    "queries_with_S_only": sum(bool(r["B_top10_S_only_entries"]) for r in rows),
                    "explicit_qrel_positive_entries": judged, "unjudged_entries": len(entries) - judged},
        "certificate": {
            "queries_with_S_only_candidates": sum(r["S_only_candidates"] > 0 for r in rows),
            "certified_queries": sum(r["exclusion_certificate"]["certified"] for r in rows),
            "reason_counts": dict(Counter(r["exclusion_certificate"]["reason"] for r in rows))},
        "decision": ("preserve finite development feasibility set; stop after independent verification"
                     if partition["S-only"] else
                     "park this panel for the S-only rescue rule; no observed positive examples at retained depths"),
    }
    for suffix in ("head", "deep", "inside_P", "outside_P"):
        key = "S_only_positive_" + suffix
        out[key] = {"pairs": sum(r[key] for r in rows), "queries": sum(r[key] > 0 for r in rows)}
    return out


def same(actual, expected, label):
    # JSON equality alone accepts True == 1; compare canonical serializations.
    require(json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True),
            f"independent reconstruction mismatch: {label}")


def self_test():
    short = {str(i): i + 1 for i in range(9)}
    ten = {str(i): i + 1 for i in range(10)}
    require(certificate([ten] * 4, {"x": 1})["certified"], "strict fixture")
    # Four disjoint lists give four rank-one and four rank-two competitors;
    # their tenth contribution equals an outsider at S rank three.
    disjoint = [{f"{j}-{i}": i for i in range(1, 4)} for j in range(4)]
    eq = certificate(disjoint, {"x": 3})
    same(eq, {"T": "1/63", "V": "1/63", "certified": False, "reason": "T_le_V"}, "equality fixture")
    require(certificate([short] * 4, {"x": 1})["reason"] == "fewer_than_ten_U_candidates", "short fixture")
    require(certificate([ten] * 4, ten)["reason"] == "no_S-only_candidates", "no outsider fixture")
    lex = {f"l{i}": i + 1 for i in range(10)}
    s = {f"s{i}": i + 1 for i in range(10)}
    s.update({"deep_in": 11, "deep_out": 12, "l0": 13})
    p = dict(lex, deep_in=11)
    runs = {name: {"q": dict(lex)} for name in LEXICAL}
    runs.update(S={"q": s}, P={"q": p}, B={"q": lex})
    pos = {"q": {"l0", "l1", "deep_in", "deep_out", "missing"}}
    rows, positives = reconstruct(runs, pos)
    same(rows[0]["positive_partition"], {"U-and-S": 1, "U-only": 1, "S-only": 2, "neither": 1}, "partition fixture")
    summary = aggregate(rows, "synthetic")
    require(summary["S_only_positive_head"]["pairs"] == 0, "zero head fixture")
    require(summary["S_only_positive_deep"]["pairs"] == 2, "deeper positives fixture")
    require(summary["S_only_positive_inside_P"]["pairs"] == 1, "inside P fixture")
    require(summary["S_only_positive_outside_P"]["pairs"] == 1, "outside P fixture")
    require(len(positives) == 5, "positive rows fixture")
    sparse = {f"l{i}": i + 1 for i in range(9)}
    admission = {name: {"q": dict(sparse)} for name in LEXICAL}
    admission.update(S={"q": {"positive": 1, "unknown": 2}},
                     P={"q": dict(sparse, positive=10)},
                     B={"q": {"positive": 1, "unknown": 2,
                                **{f"l{i}": i + 3 for i in range(8)}}})
    rows, _ = reconstruct(admission, {"q": {"positive"}})
    same(rows[0]["B_top10_S_only_entries"], [
        {"docid": "positive", "B_rank": 1, "S_rank": 1, "in_P": True,
         "explicit_qrel_positive": True},
        {"docid": "unknown", "B_rank": 2, "S_rank": 2, "in_P": False,
         "explicit_qrel_positive": False}], "B admission fixture")
    same(aggregate(rows, "synthetic")["B_top10"], {
        "denominator": 10, "S_only_entries": 2, "queries_with_S_only": 1,
        "explicit_qrel_positive_entries": 1, "unjudged_entries": 1}, "B aggregate fixture")
    try:
        same({"n": True}, {"n": 1}, "type distinction fixture")
    except ValueError:
        pass
    else:
        raise ValueError("accepted bool as integer")
    with tempfile.TemporaryDirectory(prefix="cycle16-independent-") as scratch:
        path = Path(scratch) / "input"
        path.write_text("q 0 r 1\n", encoding="utf-8")
        require(read_qrels(path) == {"q": {"r"}}, "qrels parser fixture")
        for bad in ("q 0 r 1\nq 0 r 1\n", "q 0 r 0\n", "q 0 r 2\n"):
            path.write_text(bad, encoding="utf-8")
            try:
                read_qrels(path)
            except ValueError:
                pass
            else:
                raise ValueError("accepted bad qrels fixture")
        for bad in ("q Q0 r 1 NaN tag\n", "q Q0 r 0 1 tag\n",
                    "q Q0 r 2 1 tag\n", "q Q0 r 1 1 tag\nq Q0 r 2 0 tag\n",
                    "q Q0 r 1 1 tag\nq Q0 s 1 0 tag\n", "x Q0 r 1 1 tag\n"):
            path.write_text(bad, encoding="utf-8")
            try:
                read_run(path, "bm25", {"q"})
            except ValueError:
                pass
            else:
                raise ValueError("accepted bad run fixture")
        path.write_text("q Q0 s 2 0 tag\nq Q0 r 1 1 tag\n", encoding="utf-8")
        same(read_run(path, "bm25", {"q"}), {"q": {"r": 1, "s": 2}}, "rank-column order fixture")
    print("Independent synthetic membership, certificate and parser checks passed.")


def verify(result_dir, output):
    started = time.monotonic()
    result_dir = result_dir.resolve()
    output = output.resolve()
    require(not output.exists(), "independent receipt already exists")
    start = json_read(result_dir / "execution-start.json")
    manifest = json_read(result_dir / "manifest.json")
    require(start["schema"] == 1 and type(start["schema"]) is int, "receipt schema")
    require(start["phase"] == "before_input_row_parsing", "receipt phase")
    require(start["checkpoint"] == CHECKPOINT, "receipt checkpoint")
    require(start["protocol"] == PROTOCOL and start["source"] == PRIMARY, "receipt source paths")
    require(start["wall_ceiling_seconds"] == 300, "receipt time ceiling")
    same(start["inputs"], INPUTS, "fixed input paths")
    require(isinstance(start["command"], list) and start["command"] and
            all(isinstance(arg, str) for arg in start["command"]), "receipt command")
    require(any(arg == PRIMARY or arg.endswith("/" + PRIMARY) for arg in start["command"]),
            "receipt command lacks primary source")
    expected_paths = set(INPUTS.values()) | set(METADATA) | {PROTOCOL, PRIMARY}
    require(set(start["identities"]) == expected_paths, "receipt identity coverage")
    before = {path: identity(ROOT / path) for path in sorted(expected_paths)}
    same(start["identities"], before, "pre-row identities")
    for path in set(INPUTS.values()) | set(METADATA):
        blob = subprocess.check_output(
            ["git", "rev-parse", f"{CHECKPOINT}:{path}"], cwd=ROOT, text=True).strip()
        require(blob == before[path]["git-blob-sha1"], f"checkpoint mismatch: {path}")
    old_manifest = json_read(ROOT / METADATA[0])
    for name in RUNS:
        recorded = old_manifest["outputs"][name + ".trec"]
        for key in ("bytes", "sha256", "git-blob-sha1"):
            require(recorded[key] == before[INPUTS[name]][key], f"cycle15 output custody: {name}/{key}")
    official = json_read(ROOT / METADATA[1])
    require(official["qrels_sha256"] == before[INPUTS["qrels"]]["sha256"], "official qrel custody")
    artifact_names = ("execution-start.json", "perquery.json", "positive-support.json", "summary.json")
    artifact_ids = {name: identity(result_dir / name) for name in artifact_names}
    same(manifest, dict(start, status="completed", outputs=artifact_ids), "completion manifest")
    observed = {name: json_read(result_dir / name) for name in artifact_names[1:]}
    receipt_snapshot = {
        "phase": "before_independent_input_row_parsing",
        "identities": before,
        "primary_artifacts": dict(artifact_ids, **{"manifest.json": identity(result_dir / "manifest.json")}),
        "verifier": identity(Path(__file__)),
    }
    # All byte identities and the committed custody chain have now passed.
    positives = read_qrels(ROOT / INPUTS["qrels"])
    require(len(positives) == 300, "expected exactly 300 qrel queries")
    runs = {name: read_run(ROOT / INPUTS[name], name, positives) for name in RUNS}
    rows, positive_rows = reconstruct(runs, positives)
    summary = aggregate(rows, INTERPRETATION)
    same(observed["perquery.json"], rows, "every perquery field/order/type")
    same(observed["positive-support.json"], positive_rows, "every positive support field/order/type")
    same(observed["summary.json"], summary, "every summary field/type")
    for path, recorded in before.items():
        same(identity(ROOT / path), recorded, f"post-read custody: {path}")
    for name, recorded in receipt_snapshot["primary_artifacts"].items():
        same(identity(result_dir / name), recorded, f"post-read artifact custody: {name}")
    same(identity(Path(__file__)), receipt_snapshot["verifier"], "verifier stable during execution")
    elapsed = time.monotonic() - started
    require(elapsed <= 300, "five-minute independent verification ceiling exceeded")
    receipt = {
        "schema": 1, "status": "passed", "checkpoint": CHECKPOINT,
        "command": [sys.executable] + sys.argv,
        "pre_row_snapshot": receipt_snapshot,
        "method": "Independent TREC rank-column reconstruction; set membership; exact integer common-denominator exclusion certificates; no primary code import or new fusion.",
        "checked": {"input_run_rows": {name: sum(map(len, runs[name].values())) for name in RUNS},
                    "query_rows": len(rows), "positive_rows": len(positive_rows),
                    "primary_outputs": list(artifact_names[1:]),
                    "exact_all_fields": True, "benchmark_effectiveness_computed": False},
        "summary": summary, "elapsed_seconds": elapsed,
    }
    with output.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps({"status": "passed", "receipt": str(output),
                      "query_rows": len(rows), "positive_rows": len(positive_rows)}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--result-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        require(args.output is None, "--output is only for real verification")
        self_test()
    else:
        require(args.output is not None, "real verification requires an exclusive --output path")
        verify(args.result_dir, args.output)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
