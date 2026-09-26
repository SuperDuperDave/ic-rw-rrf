#!/usr/bin/env python3
"""Frozen, post hoc retained-support census; no fusion or effectiveness scoring."""

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = "19139bdd061fd2e51e529d7411264014e0b093a3"
PROTOCOL = "_sessions/cycles/2026-09-25-cycle16-support-protocol.md"
PROTOCOL_SHA256 = "5ec795012a244b6ed698e2c85b38df89a9fece9bfaec300221866ed8eda4e7e7"
SOURCE = "evaluation/cycle16_support_census.py"
CYCLE15 = "results/cycle15-2026-09-12/"
MANIFEST = CYCLE15 + "transfer/manifest.json"
OFFICIAL = CYCLE15 + "independent-audit/B.official-command.json"
LEXICAL = ("bm25", "bm25_tuned", "tfidf", "ql_dirichlet")
RUNS = LEXICAL + ("S", "P", "B")
INPUTS = {name: CYCLE15 + "transfer/" + name + ".trec" for name in RUNS}
INPUTS["qrels"] = CYCLE15 + "independent-audit/official.qrels"
PARTITIONS = ("U-and-S", "U-only", "S-only", "neither")


class ContractError(ValueError):
    """A fixed-input contract failed; there is no fallback or retry."""


def identity(path):
    size = path.stat().st_size
    sha = hashlib.sha256()
    blob = hashlib.sha1(("blob %d\0" % size).encode("ascii"))
    consumed = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            consumed += len(chunk)
            sha.update(chunk)
            blob.update(chunk)
    if consumed != size or path.stat().st_size != size:
        raise ContractError("file changed during hashing: " + str(path))
    return {"bytes": size, "sha256": sha.hexdigest(), "git-blob-sha1": blob.hexdigest()}


def write_json(path, value):
    with path.open("x", encoding="utf-8") as target:
        json.dump(value, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")


def verify_custody(root):
    """Hash raw bytes only; no benchmark rows are parsed during this gate."""
    pinned = [MANIFEST, OFFICIAL] + list(INPUTS.values())
    blobs = subprocess.run(
        ["git", "rev-parse"] + [CHECKPOINT + ":" + path for path in pinned],
        cwd=root, check=True, capture_output=True, text=True, timeout=10,
    ).stdout.splitlines()
    if len(blobs) != len(pinned):
        raise ContractError("incomplete checkpoint identities")
    identities = {path: identity(root / path) for path in pinned + [PROTOCOL, SOURCE]}
    for path, expected in zip(pinned, blobs):
        if identities[path]["git-blob-sha1"] != expected:
            raise ContractError("checkpoint identity mismatch: " + path)
    if identities[PROTOCOL]["sha256"] != PROTOCOL_SHA256:
        raise ContractError("frozen protocol identity mismatch")
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    official = json.loads((root / OFFICIAL).read_text(encoding="utf-8"))
    for name, path in INPUTS.items():
        expected = (official["qrels_sha256"] if name == "qrels" else
                    manifest["outputs"][name + ".trec"]["sha256"])
        if identities[path]["sha256"] != expected:
            raise ContractError("recorded SHA256 mismatch: " + name)
    return identities, manifest


def valid_id(value):
    return bool(value) and all(33 <= ord(char) <= 126 for char in value)


def read_rows(path, qrels=False):
    """Read explicit ranks in file order; retain IDs as strings, never sort scores."""
    result = {}
    with path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            fields = line.split()
            if len(fields) != (4 if qrels else 6):
                raise ContractError("%s:%d: wrong field count" % (path, number))
            qid, iteration, docid = fields[:3]
            if not all(valid_id(value) for value in (qid, docid)):
                raise ContractError("invalid ID")
            docs = result.setdefault(qid, {})
            if docid in docs:
                raise ContractError("duplicate query/document row")
            if qrels:
                if iteration != "0" or fields[3] != "1":
                    raise ContractError("qrels must have iteration 0 and positive binary grade 1")
                docs[docid] = 1
            else:
                if iteration != "Q0" or not valid_id(fields[5]):
                    raise ContractError("invalid TREC iteration or run ID")
                if fields[3] != str(len(docs) + 1):
                    raise ContractError("noncontiguous one-based ranks")
                try:
                    finite = math.isfinite(float(fields[4]))
                except ValueError:
                    finite = False
                if not finite:
                    raise ContractError("nonfinite or invalid score")
                docs[docid] = len(docs) + 1
    if not result:
        raise ContractError("empty input")
    return result


def validate_panel(runs, qrels, manifest, expected_queries=300):
    qids = set(qrels)
    if (len(qids) != expected_queries or manifest["n_queries"] != expected_queries
            or len(manifest["qids"]) != expected_queries or set(manifest["qids"]) != qids):
        raise ContractError("qrel/manifest query cohort mismatch")
    for name in RUNS:
        if set(runs[name]) != qids:
            raise ContractError("run query cohort mismatch: " + name)
        declared = (manifest["lexical_depths"][name] if name in LEXICAL else
                    manifest["arm_depths"][name])
        if set(declared) != qids:
            raise ContractError("manifest depth cohort mismatch")
        for qid, docs in runs[name].items():
            depth = len(docs)
            valid = (1 <= depth <= 200 if name in LEXICAL else
                     depth == 1000 if name == "S" else
                     1 <= depth <= 1000 if name == "P" else depth >= 10)
            if not valid or declared[qid] != depth:
                raise ContractError("unexpected depth: " + name + "/" + qid)
    for qid in qids:
        union = set().union(*(runs[name][qid] for name in LEXICAL))
        if not union <= runs["P"][qid].keys():
            raise ContractError("lexical candidate absent from P: " + qid)


def certificate(lexical, specialist):
    sums = {}
    for ranking in lexical:
        for docid, rank in ranking.items():
            sums[docid] = sums.get(docid, Fraction(0)) + Fraction(1, 60 + rank)
    only = specialist.keys() - sums.keys()
    t = sorted(sums.values(), reverse=True)[9] if len(sums) >= 10 else None
    v = max((Fraction(1, 60 + specialist[doc]) for doc in only), default=None)
    certified = t is not None and v is not None and t > v
    return {"T": str(t) if t is not None else None,
            "V": str(v) if v is not None else None, "certified": certified,
            "reason": ("no_S-only_candidates" if v is None else
                       "fewer_than_ten_U_candidates" if t is None else
                       "strict_T_gt_V" if certified else "T_le_V")}


def analyze_query(qid, runs, positives):
    lexical = [runs[name] for name in LEXICAL]
    union = set().union(*lexical)
    specialist, pool, b = runs["S"], runs["P"], runs["B"]
    only = specialist.keys() - union
    support = []
    for docid in sorted(positives):
        partition = ("U-and-S" if docid in specialist else "U-only") if docid in union else (
            "S-only" if docid in specialist else "neither")
        support.append({"qid": qid, "docid": docid, "partition": partition,
                        "in_P": docid in pool, "S_rank": specialist.get(docid),
                        "P_rank": pool.get(docid), "B_rank": b.get(docid),
                        "lexical_ranks": {name: runs[name].get(docid) for name in LEXICAL}})
    counts = dict.fromkeys(PARTITIONS, 0)
    for row in support:
        counts[row["partition"]] += 1
    s_positives = [row for row in support if row["partition"] == "S-only"]
    entries = [{"docid": docid, "B_rank": rank, "S_rank": specialist[docid],
                "in_P": docid in pool, "explicit_qrel_positive": docid in positives}
               for docid, rank in sorted(b.items(), key=lambda item: item[1])
               if rank <= 10 and docid in only]
    cert = certificate(lexical, specialist)
    if cert["certified"] and entries:
        raise ContractError("exclusion certificate contradicts frozen B top10")
    query = {"qid": qid, "known_positives": len(positives), "positive_partition": counts,
             "depths": {name: len(runs[name]) for name in RUNS}, "U_candidates": len(union),
             "S_only_candidates": len(only), "S_only_positive_head": sum(row["S_rank"] <= 10 for row in s_positives),
             "S_only_positive_deep": sum(row["S_rank"] > 10 for row in s_positives),
             "S_only_positive_inside_P": sum(row["in_P"] for row in s_positives),
             "S_only_positive_outside_P": sum(not row["in_P"] for row in s_positives),
             "B_top10_S_only_entries": entries, "exclusion_certificate": cert}
    return query, support


def summarize(queries):
    partition = {name: sum(q["positive_partition"][name] for q in queries) for name in PARTITIONS}
    summary = {"interpretation": "post hoc descriptive development; no effectiveness or relevance inferred for unjudged documents",
               "query_count": len(queries), "known_positive_pairs": sum(partition.values()),
               "positive_partition": partition,
               "positive_partition_query_counts": {name: sum(q["positive_partition"][name] > 0 for q in queries) for name in PARTITIONS}}
    for key in ("S_only_positive_head", "S_only_positive_deep", "S_only_positive_inside_P", "S_only_positive_outside_P"):
        summary[key] = {"pairs": sum(q[key] for q in queries), "queries": sum(q[key] > 0 for q in queries)}
    entries = [entry for q in queries for entry in q["B_top10_S_only_entries"]]
    summary["B_top10"] = {"denominator": 10 * len(queries), "S_only_entries": len(entries),
                          "queries_with_S_only": sum(bool(q["B_top10_S_only_entries"]) for q in queries),
                          "explicit_qrel_positive_entries": sum(e["explicit_qrel_positive"] for e in entries),
                          "unjudged_entries": sum(not e["explicit_qrel_positive"] for e in entries)}
    summary["certificate"] = {"queries_with_S_only_candidates": sum(q["S_only_candidates"] > 0 for q in queries),
                              "certified_queries": sum(q["exclusion_certificate"]["certified"] for q in queries),
                              "reason_counts": dict(Counter(q["exclusion_certificate"]["reason"] for q in queries))}
    summary["decision"] = ("preserve finite development feasibility set; stop after independent verification"
                           if partition["S-only"] else
                           "park this panel for the S-only rescue rule; no observed positive examples at retained depths")
    return summary


def run_census(output, root=ROOT):
    output.mkdir(parents=True, exist_ok=False)
    try:
        identities, historical = verify_custody(root)
        receipt = {"schema": 1, "phase": "before_input_row_parsing", "checkpoint": CHECKPOINT,
                   "protocol": PROTOCOL, "source": SOURCE, "inputs": INPUTS,
                   "identities": identities, "wall_ceiling_seconds": 300,
                   "command": ["python3", SOURCE, "--output", str(output)]}
        write_json(output / "execution-start.json", receipt)
        qrels = read_rows(root / INPUTS["qrels"], qrels=True)
        runs = {name: read_rows(root / INPUTS[name]) for name in RUNS}
        validate_panel(runs, qrels, historical)
        queries, positives = [], []
        for qid in sorted(qrels):
            query, rows = analyze_query(qid, {name: runs[name][qid] for name in RUNS}, qrels[qid])
            queries.append(query)
            positives.extend(rows)
        for relative, expected in identities.items():
            if identity(root / relative) != expected:
                raise ContractError("file changed after custody receipt: " + relative)
        artifacts = {"perquery.json": queries, "positive-support.json": positives,
                     "summary.json": summarize(queries)}
        for name, value in artifacts.items():
            write_json(output / name, value)
        write_json(output / "manifest.json", dict(receipt, status="completed", outputs={
            name: identity(output / name) for name in ["execution-start.json"] + list(artifacts)}))
        return artifacts["summary.json"]
    except Exception as error:
        write_json(output / "failure.json", {"status": "failed", "error": str(error), "error_type": type(error).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    def timeout(_signum, _frame):
        raise TimeoutError("five-minute census ceiling exceeded")
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    try:
        summary = run_census(args.output)
        print(json.dumps(summary, sort_keys=True))
    except Exception as error:
        print("Census stopped: " + str(error), file=sys.stderr)
        return 1
    finally:
        signal.alarm(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
