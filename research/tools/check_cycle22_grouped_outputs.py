#!/usr/bin/env python3
"""Independent Cycle22 parser, Fraction policies, pooled sharp bounds, and custody.

This module imports no research producer, parser, or analysis implementation.
Execution against research inputs requires the coordinator's explicit GO.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
import re
import signal
import sys
import tempfile
import time
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = "_sessions/cycles/2026-09-26-cycle22-input-plan.json"
PROTOCOL = "_sessions/cycles/2026-09-26-cycle22-protocol.md"
SOURCE = "_sessions/tools/check_cycle22_grouped_outputs.py"
QIDS = [str(i) for i in range(1, 31)]
RR = {r: Q(1, 60 + r) for r in range(1, 101)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected, context="root"):
    require(type(actual) is type(expected), f"{context}: type differs")
    if isinstance(expected, dict):
        require(actual.keys() == expected.keys(), f"{context}: keys differ: {actual.keys()} versus {expected.keys()}")
        for key in expected:
            same(actual[key], expected[key], f"{context}.{key}")
    elif isinstance(expected, list):
        require(len(actual) == len(expected), f"{context}: lengths differ")
        for i, (a, b) in enumerate(zip(actual, expected)):
            same(a, b, f"{context}[{i}]")
    else:
        require(actual == expected, f"{context}: value differs: {actual!r} versus {expected!r}")


def fraction(x):
    x = Q(x)
    return f"{x.numerator}/{x.denominator}"


def rat(x):
    x = Q(x)
    return {"fraction": fraction(x), "value": float(x)}


def identity(path, md5=False):
    h = hashlib.sha256()
    m = hashlib.md5()
    size = 0
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
            m.update(block)
            size += len(block)
    result = {"bytes": size, "sha256": h.hexdigest()}
    if md5:
        result["md5"] = m.hexdigest()
    return result


def artifact_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def portable(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_docids(path):
    lines = Path(path).read_bytes().split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    require(lines, "empty inventory")
    result = set()
    for line in lines:
        require(line and line.strip(b" ") and all(32 <= c <= 126 for c in line),
                "inventory line must be nonblank printable ASCII, without stripping")
        result.add(line.decode("ascii"))
    return result


def ascii_token(value):
    return bool(value) and all(33 <= ord(c) <= 126 for c in value)


def read_run(path, tag, docids, qids=QIDS):
    rows = {q: {} for q in qids}
    count = 0
    with Path(path).open(encoding="ascii") as handle:
        for number, line in enumerate(handle, 1):
            fields = line.split()
            require(len(fields) == 6, f"{tag} line {number}: six fields required")
            q, iteration, doc, supplied, token, row_tag = fields
            require(q in rows, f"{tag}: query outside cohort")
            require(row_tag == tag, f"{tag}: wrong run tag")
            require(doc in docids and ascii_token(doc), f"{tag}: document outside inventory")
            require(doc not in rows[q], f"{tag}: duplicate query/document")
            require(re.fullmatch(r"\+?[0-9]+", supplied) is not None, f"{tag}: invalid supplied rank")
            try:
                score = Decimal(token)
            except InvalidOperation as error:
                raise ValueError(f"{tag}: invalid score") from error
            require(score.is_finite(), f"{tag}: nonfinite score")
            rows[q][doc] = (score, token, int(supplied))
            require(len(rows[q]) <= 1000, f"{tag}: excessive query depth")
            count += 1
    orders, diagnostic = {}, {}
    for q, documents in rows.items():
        require(documents, f"{tag}: missing query {q}")
        # Stable doc-ID then exact Decimal descending avoids precision rounding.
        order = sorted(documents)
        order.sort(key=lambda d: documents[d][0], reverse=True)
        orders[q] = order[:100]
        ties = Counter(item[0] for item in documents.values())
        tied = [n for n in ties.values() if n > 1]
        diagnostic[q] = {
            "full_depth": len(order), "retained_depth": len(orders[q]),
            "retained_order": orders[q], "tie_groups": len(tied),
            "tied_documents": sum(tied), "tie_excess": sum(n - 1 for n in tied),
            "supplied_rank_disagreements": sum(documents[d][2] != r for r, d in enumerate(order, 1)),
            "retained_details": [{"doc_id": d, "score": documents[d][1],
                                  "supplied_rank": documents[d][2], "canonical_rank": r}
                                 for r, d in enumerate(orders[q], 1)],
        }
    return orders, {"run_tag": tag, "row_count": count, "queries": diagnostic}


def read_labels(path, qids=QIDS):
    labels = {q: {} for q in qids}
    with Path(path).open(encoding="ascii") as handle:
        for number, line in enumerate(handle, 1):
            fields = line.split()
            require(len(fields) == 4, f"qrels line {number}: four fields required")
            q, iteration, doc, grade = fields
            require(q in labels and grade in ("0", "1", "2"), "qrels topic/grade domain")
            require(ascii_token(doc), "qrels document token")
            require(doc not in labels[q], "duplicate qrels pair, including inert labels")
            try:
                parsed_iteration = Decimal(iteration)
            except InvalidOperation as error:
                raise ValueError("qrels iteration malformed") from error
            require(parsed_iteration.is_finite() and parsed_iteration > 0, "qrels iteration domain")
            labels[q][doc] = int(grade)
    require(all(labels.values()), "missing qrels query")
    return labels


def vector(order):
    require(1 <= len(order) <= 100 and len(set(order)) == len(order), "invalid retained order")
    return {d: RR[r] for r, d in enumerate(order, 1)}


def head(scores):
    result = sorted(scores, key=lambda d: (-scores[d], d))[:10]
    require(len(result) == 10 and len(set(result)) == 10, "invalid fusion head")
    return result


def build_policies(groups, s_orders, orders, qids=QIDS):
    teams = sorted(groups)
    require(set(orders) == {r for runs in groups.values() for r in runs}, "member frame differs")
    group_lcm = math.lcm(*(len(groups[t]) for t in teams))
    queries = {}
    for q in qids:
        s = vector(s_orders[q])
        require(len(s) == 100, "fixed S depth")
        qteams = {}
        for t in teams:
            group = s.copy()
            hybrids = {}
            m = len(groups[t])
            for run in groups[t]:
                v = vector(orders[run][q])
                hybrid = s.copy()
                for d, value in v.items():
                    hybrid[d] = hybrid.get(d, Q(0)) + value
                    group[d] = group.get(d, Q(0)) + value / m
                hybrids[run] = head(hybrid)
            qteams[t] = {"G": head(group), "members": hybrids}
        queries[q] = {"S": s_orders[q][:10], "teams": qteams,
                      "retained_depths": {"S": 100, "members": {r: len(orders[r][q]) for r in sorted(orders)}}}
    return {
        "schema": "cycle22-grouped-policies-v1-provisional", "query_ids": list(qids),
        "teams": teams, "groups": groups,
        "parameters": {"depth_cap": 100, "s_depth": 100, "k": 60, "head": 10,
                       "reciprocal_units": str(math.lcm(*range(61, 161))), "group_size_lcm": group_lcm},
        "retained": {"S": s_orders, "members": orders}, "queries": queries,
    }


def clean(coefficients):
    return {pair: value for pair, value in coefficients.items() if value}


def add_scaled(destination, source, scale=Q(1)):
    for pair, value in source.items():
        destination[pair] += value * scale


def contrast_vectors(q, row, s_head):
    primary, contextual = defaultdict(Q), defaultdict(Q)
    m = len(row["members"])
    for d in row["G"]:
        primary[q, d] += Q(1, 10)
        contextual[q, d] += Q(1, 10)
    for h in row["members"].values():
        for d in h:
            primary[q, d] -= Q(1, 10 * m)
    for d in s_head:
        contextual[q, d] -= Q(1, 10)
    return clean(primary), clean(contextual)


def bounds(coefficients, labels):
    known = Q(0)
    low = Q(0)
    high = Q(0)
    unknown = 0
    for (q, d), c in coefficients.items():
        if not c:
            continue
        if d in labels[q]:
            known += c * (labels[q][d] > 0)
        else:
            unknown += 1
            low += min(Q(0), c)
            high += max(Q(0), c)
    low += known
    high += known
    sign = ("positive" if low > 0 else "negative" if high < 0 else "zero" if low == high == 0
            else "nonnegative" if low == 0 else "nonpositive" if high == 0 else "unresolved")
    decision = "positive" if low > 0 else "nonpositive" if high <= 0 else "unresolved"
    return {"known": rat(known), "lower": rat(low), "upper": rat(high), "width": rat(high - low),
            "unknown_support": unknown, "sign": sign, "decision": decision}


def bench(h, qlabels):
    return Q(sum(qlabels.get(d, 0) > 0 for d in h), 10)


def build_analysis(policies, labels):
    qids, teams, groups = policies["query_ids"], policies["teams"], policies["groups"]
    nq, nt = len(qids), len(teams)
    primary, contextual = defaultdict(Q), defaultdict(Q)
    team_vectors = {t: [defaultdict(Q), defaultdict(Q)] for t in teams}
    team_bench = {t: {"G": Q(0), "meanH": Q(0), "S": Q(0),
                      "members": {r: Q(0) for r in groups[t]}} for t in teams}
    global_bench = {"G": Q(0), "meanH": Q(0), "S": Q(0)}
    per_query = {}
    for q in qids:
        qp, qc = defaultdict(Q), defaultdict(Q)
        qb = {"G": Q(0), "meanH": Q(0), "S": Q(0)}
        tq = {}
        s_head = policies["queries"][q]["S"]
        for t in teams:
            row = policies["queries"][q]["teams"][t]
            p, c = contrast_vectors(q, row, s_head)
            require(sum(p.values()) == sum(c.values()) == 0, "team coefficient sums")
            add_scaled(qp, p, Q(1, nt))
            add_scaled(qc, c, Q(1, nt))
            add_scaled(team_vectors[t][0], p, Q(1, nq))
            add_scaled(team_vectors[t][1], c, Q(1, nq))
            mb = {r: bench(h, labels[q]) for r, h in row["members"].items()}
            b = {"G": bench(row["G"], labels[q]), "meanH": sum(mb.values()) / len(mb),
                 "S": bench(s_head, labels[q])}
            tq[t] = {"G-meanH": bounds(p, labels), "G-S": bounds(c, labels),
                     "benchmark": {**{k: rat(v) for k, v in b.items()},
                                   "members": {r: rat(v) for r, v in mb.items()}}}
            for name, value in b.items():
                qb[name] += value / nt
                team_bench[t][name] += value / nq
            for r, value in mb.items():
                team_bench[t]["members"][r] += value / nq
        require(sum(qp.values()) == sum(qc.values()) == 0, "query coefficient sums")
        add_scaled(primary, qp, Q(1, nq))
        add_scaled(contextual, qc, Q(1, nq))
        per_query[q] = {"primary": bounds(qp, labels), "G-S": bounds(qc, labels),
                        "benchmark": {k: rat(v) for k, v in qb.items()}, "teams": tq}
        for name, value in qb.items():
            global_bench[name] += value / nq
    per_team = {}
    for t in teams:
        per_team[t] = {"G-meanH": bounds(team_vectors[t][0], labels),
                       "G-S": bounds(team_vectors[t][1], labels),
                       "benchmark": {k: ({r: rat(v) for r, v in value.items()} if k == "members" else rat(value))
                                     for k, value in team_bench[t].items()}}
    bp, bc = bounds(primary, labels), bounds(contextual, labels)
    require(sum(primary.values()) == sum(contextual.values()) == 0, "global coefficient sums")
    require(Q(bp["known"]["fraction"]) == global_bench["G"] - global_bench["meanH"], "primary benchmark")
    require(Q(bc["known"]["fraction"]) == global_bench["G"] - global_bench["S"], "context benchmark")
    for name, actual in (("primary", bp), ("G-S", bc)):
        pooled = defaultdict(Q)
        which = 0 if name == "primary" else 1
        for t in teams:
            add_scaled(pooled, team_vectors[t][which], Q(1, nt))
        same(clean(pooled), clean(primary if which == 0 else contextual), "two aggregation routes")
        # Sharp known values average over queries; query IDs are disjoint labels.
        for field in ("known", "lower", "upper", "width"):
            require(Q(actual[field]["fraction"]) == sum(Q(per_query[q][name][field]["fraction"]) for q in qids) / nq,
                    "global versus query-average normalization")
    average_team_width = sum(Q(per_team[t]["G-meanH"]["width"]["fraction"]) for t in teams) / nt
    require(Q(bp["width"]["fraction"]) <= average_team_width, "pooled sharpness versus team bound")
    for field in ("lower", "upper"):
        require(Q(bc[field]["fraction"]) == sum(Q(per_team[t]["G-S"][field]["fraction"]) for t in teams) / nt,
                "fixed-S sign consistency")
    group_lcm = policies["parameters"]["group_size_lcm"]
    denominator = group_lcm * 10 * nt * nq
    pairs = []
    for q in qids:
        docs = sorted({d for qq, d in primary if qq == q and primary[qq, d]}
                      | {d for qq, d in contextual if qq == q and contextual[qq, d]})
        for d in docs:
            p, c = primary.get((q, d), Q(0)), contextual.get((q, d), Q(0))
            numerator = p * denominator
            require(numerator.denominator == 1, "common primary denominator")
            grade = labels[q].get(d)
            pairs.append({"query_id": q, "doc_id": d, "primary_numerator": numerator.numerator,
                          "primary": rat(p), "G-S": rat(c), "grade": grade,
                          "binary": None if grade is None else int(grade > 0)})
    benchmark = {k: rat(v) for k, v in global_bench.items()}
    benchmark["G-meanH"] = rat(global_bench["G"] - global_bench["meanH"])
    benchmark["G-S"] = rat(global_bench["G"] - global_bench["S"])
    signs = ("positive", "negative", "zero", "nonnegative", "nonpositive", "unresolved")
    sign_counts = {name: {s: sum(per_team[t][field]["sign"] == s for t in teams) for s in signs}
                   for name, field in (("primary", "G-meanH"), ("G-S", "G-S"))}
    return {
        "schema": "cycle22-grouped-analysis-v1-provisional", "query_ids": list(qids), "teams": teams,
        "primary": bp, "G-S": bc, "team_sign_counts": sign_counts,
        "per_query": per_query, "per_team": per_team, "benchmark_missing_zero": benchmark,
        "benchmark_convention": "binary P@10; missing labels assigned zero",
        "pair_coefficients": pairs,
        "denominators": {"group_size_lcm": group_lcm, "primary_mean": denominator,
                         "primary_per_query": denominator // nq},
        "qrels_pair_count": sum(map(len, labels.values())),
        "checks": {"global_equals_query_average": True, "coefficient_sums_zero": True,
                   "benchmark_matches_known_term": True, "pooled_width_no_larger_than_team_mean": True},
    }


REQUIRED = {PROTOCOL, PLAN, SOURCE, "_sessions/tools/acquire_cycle22_inputs.py",
            "evaluation/cycle22_grouped_outputs.py", "evaluation/tests/test_cycle22_grouped_outputs.py",
            "evaluation/tests/test_cycle22_acquisition.py"}
SAFE_HEADERS = {"Content-Type", "Content-Length", "ETag", "Last-Modified", "Content-Encoding"}


def validate_frame(plan):
    groups = plan["groups"]
    require(len(groups) == 29 and Counter(map(len, groups.values())) == {2: 6, 3: 23}, "29-team/81-member frame")
    members = [r for runs in groups.values() for r in runs]
    require(len(members) == len(set(members)) == 81 and set(members) == set(plan["items"]), "unique member IDs")
    same(plan["query_ids"], QIDS, "query cohort")
    require(all(runs == sorted(runs) for runs in groups.values()), "sorted member IDs")
    inventory = read_json(artifact_path(plan["inventory"]["path"]))
    require(len({row["team"] for row in inventory["teams"]}) == len(inventory["teams"]), "duplicate inventory team")
    require(all(len(row["automatic_runs"]) == len(set(row["automatic_runs"])) for row in inventory["teams"]),
            "duplicate automatic run within inventory team")
    expected = {row["team"]: sorted(row["automatic_runs"]) for row in inventory["teams"] if row["eligible"]}
    same(groups, expected, "complete metadata-defined grouping")
    index = {row["run"]: row for row in inventory["runs"]}
    require(len(index) == len(inventory["runs"]), "duplicate inventory run ID")
    names = set()
    for run, item in plan["items"].items():
        require(item["filename"] == Path(item["filename"]).name and item["filename"] not in names, "safe unique file name")
        names.add(item["filename"])
        require(index[run]["type"] == "automatic" and index[run]["team"] in groups, "member metadata domain")
        require(run in groups[index[run]["team"]], "member metadata ownership")
        require(item["url"] == index[run]["url"] == "https://ir.nist.gov/trec-covid/archive/round1/" + run,
                "exact official URL")
        require(item["publisher_md5"] == index[run]["publisher_md5"], "publisher MD5 metadata")


def check_acquisition(plan, preflight, acquisition, inputs_dir):
    require(acquisition["schema"] == 1 and acquisition["status"] == "passed", "acquisition did not pass")
    same(acquisition["frozen"], preflight["frozen"], "acquisition frozen map")
    require(acquisition["plan_sha256"] == identity(artifact_path(PLAN))["sha256"], "acquisition plan hash")
    require(set(acquisition["inputs"]) == set(plan["items"]), "acquisition member completeness")
    require(set(acquisition["transport"]) == set(plan["items"]), "transport member completeness")
    require(acquisition["max_attempts_per_file"] == 1 and acquisition["byte_limit_sentinel"] == 1, "acquisition limits")
    require(0 <= acquisition["elapsed_seconds"] <= plan["max_acquisition_seconds"], "acquisition wall cap")
    total_raw = total_expanded = 0
    tracked = set()
    verified = {}
    for run in sorted(plan["items"]):
        item, receipt = plan["items"][run], acquisition["inputs"][run]
        require(receipt["filename"] == item["filename"] and receipt["raw_filename"] == item["filename"] + ".download",
                "acquisition file names")
        path = inputs_dir / item["filename"]
        raw_path = inputs_dir / receipt["raw_filename"]
        decoded, raw = identity(path, True), identity(raw_path, True)
        same({k: receipt[k] for k in decoded}, decoded, f"{run} decoded identity")
        same(receipt["raw"], raw, f"{run} raw identity")
        require(0 < raw["bytes"] <= min(item["max_bytes"], 16 * 1024 * 1024), "raw byte cap")
        require(0 < decoded["bytes"] <= plan["max_expanded_per_run"], "expanded byte cap")
        with raw_path.open("rb") as stream:
            compressed = stream.read(2) == b"\x1f\x8b"
        same(receipt["gzip"], compressed, "gzip magic detection")
        expected_md5 = item["publisher_md5"]
        require(receipt["publisher_md5"] == expected_md5, "publisher identity")
        matches = [name for name, value in (("raw", raw), ("expanded", decoded)) if value["md5"] == expected_md5]
        require(matches, "no representation matches publisher MD5")
        same(receipt["matched_representation"], matches, "publisher MD5 representation")
        if compressed:
            sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
            with gzip.open(raw_path, "rb") as stream:
                while block := stream.read(min(1024 * 1024, plan["max_expanded_per_run"] - size + 1)):
                    size += len(block)
                    require(size <= plan["max_expanded_per_run"], "independent gzip expansion cap")
                    sha.update(block)
                    md5.update(block)
            same({"bytes": size, "sha256": sha.hexdigest(), "md5": md5.hexdigest()}, decoded, "raw gzip decoded identity")
        else:
            same(raw, decoded, "plain raw decoded identity")
        transport = acquisition["transport"][run]
        require(transport["url"] == transport["effective_url"] == item["url"], "transport exact URL")
        require(transport["http_code"] == 200, "transport HTTP status")
        require(set(transport["headers"]) <= SAFE_HEADERS, "nonpublic HTTP header")
        require(transport["headers"].get("Content-Encoding", "identity") == "identity", "transport encoding")
        require("html" not in transport["headers"].get("Content-Type", "").lower(), "HTML instead of body")
        if "Content-Length" in transport["headers"]:
            require(int(transport["headers"]["Content-Length"]) == raw["bytes"], "transport content length")
        tracked.update((path.resolve(), raw_path.resolve()))
        verified[run] = {"path": portable(path), **decoded, "raw_path": portable(raw_path), "raw": raw,
                         "gzip": compressed, "matched_representation": matches, "publisher_md5": expected_md5}
        total_raw += raw["bytes"]
        total_expanded += decoded["bytes"]
    require(total_raw <= plan["max_total_bytes"] and total_expanded <= plan["max_total_expanded_bytes"], "total byte caps")
    require(acquisition["transfer_bytes_complete_bodies"] == total_raw, "transferred byte total")
    require(acquisition["expanded_bytes_complete_bodies"] == total_expanded, "expanded byte total")
    return verified, tracked


def check_frozen(preflight):
    require(preflight.get("status") == "passed" and preflight.get("schema") == 1, "preflight status/schema")
    frozen = preflight["frozen"]
    require(REQUIRED <= set(frozen), "missing mandatory frozen contract/code")
    for name, sha in frozen.items():
        path = artifact_path(name).resolve()
        require(path.is_relative_to(ROOT.resolve()) and not Path(name).is_absolute(), "frozen path escapes repository")
        require(identity(path)["sha256"] == sha, "changed frozen identity: " + name)
    return {artifact_path(p).resolve() for p in frozen}


def verify(args):
    started = time.monotonic()
    preflight, acquisition = read_json(args.preflight), read_json(args.acquisition)
    tracked = check_frozen(preflight)
    plan = read_json(artifact_path(PLAN))
    cached = {}
    for key in ("inventory", "S", "prior_verification", "docids", "qrels"):
        item = plan[key]
        path = artifact_path(item["path"]).resolve()
        value = identity(path, True)
        require(value["sha256"] == item["sha256"], f"cached {key} SHA mismatch")
        if "bytes" in item:
            require(value["bytes"] == item["bytes"], f"cached {key} bytes mismatch")
        cached[key] = {"path": portable(path), **value}
        tracked.add(path)
    validate_frame(plan)
    require(acquisition["preflight_sha256"] == identity(args.preflight)["sha256"], "acquisition preflight identity")
    inputs, raw_paths = check_acquisition(plan, preflight, acquisition, args.inputs)
    tracked.update(raw_paths)
    tracked.update((args.preflight.resolve(), args.acquisition.resolve()))
    result_files = {name: args.result / name for name in ("policies.json", "analysis.json", "sources.json", "manifest.json", "success.json")}
    tracked.update(p.resolve() for p in result_files.values())
    before = {portable(p): identity(p, True) for p in sorted(tracked)}
    manifest, success = read_json(result_files["manifest.json"]), read_json(result_files["success.json"])
    require(set(manifest) == {"schema", "phase", "frozen", "preflight", "acquisition", "inputs", "cached",
                              "tracked_before", "tracked_after", "labels_joined_after_policies_sha256", "outputs", "elapsed_seconds"},
            "producer manifest schema fields")
    require(manifest["schema"] == 1 and manifest["phase"] == "cycle22", "producer manifest phase")
    same(success, {"status": "passed", "manifest": identity(result_files["manifest.json"], True)}, "producer success")
    same(manifest["frozen"], preflight["frozen"], "producer frozen map")
    for key in ("preflight", "acquisition"):
        path = getattr(args, key)
        same(manifest[key], {"path": portable(path), **identity(path, True)}, "producer " + key)
    same(manifest["inputs"], inputs, "producer complete input identities")
    same(manifest["cached"], cached, "producer cached input identities")
    for row in cached.values():
        same(before[row["path"]], {k: row[k] for k in ("bytes", "sha256", "md5")}, "cached identity at audit start")
    for row in inputs.values():
        same(before[row["path"]], {k: row[k] for k in ("bytes", "sha256", "md5")}, "input identity at audit start")
        same(before[row["raw_path"]], row["raw"], "raw identity at audit start")
    same(manifest["outputs"], {name: identity(result_files[name], True) for name in ("sources.json", "policies.json", "analysis.json")},
         "producer output identities")
    require(manifest["labels_joined_after_policies_sha256"] == identity(result_files["policies.json"])["sha256"],
            "policy-before-labels identity gate")
    same(manifest["tracked_after"], manifest["tracked_before"], "producer tracked custody unchanged")
    expected_tracked = {artifact_path(p).resolve() for p in preflight["frozen"]}
    expected_tracked.update(raw_paths)
    expected_tracked.update(artifact_path(p["path"]).resolve() for p in cached.values())
    expected_tracked.update((args.preflight.resolve(), args.acquisition.resolve(), result_files["policies.json"].resolve()))
    actual_tracked = {artifact_path(p).resolve() for p in manifest["tracked_before"]}
    require(expected_tracked <= actual_tracked, "producer custody omits required paths")
    for name, value in manifest["tracked_before"].items():
        same(identity(artifact_path(name), True), value, "producer tracked identity " + name)
    require(0 <= manifest["elapsed_seconds"] <= 300, "producer wall cap")
    docids = read_docids(artifact_path(plan["docids"]["path"]))
    old = read_json(artifact_path(plan["S"]["path"]))
    same(old["query_ids"], QIDS, "prior query cohort")
    prior_receipt = read_json(artifact_path(plan["prior_verification"]["path"]))
    require(prior_receipt["status"] == "passed", "prior independent verification")
    s_orders = {}
    for q in QIDS:
        order = old["queries"][q]["sources"]["S"]["retained_order"]
        require(len(order) == len(set(order)) == 100 and set(order) <= docids, "fixed S100 domain")
        same(order[:10], old["queries"][q]["policies"]["S"], "fixed S reference head")
        s_orders[q] = order
    orders, diagnostics = {}, {}
    for run in sorted(plan["items"]):
        orders[run], diagnostics[run] = read_run(args.inputs / plan["items"][run]["filename"], run, docids)
    policies = build_policies(plan["groups"], s_orders, orders)
    sources = {"schema": "cycle22-grouped-sources-v1-provisional", "query_ids": QIDS, "runs": diagnostics}
    same(read_json(result_files["policies.json"]), policies, "all policy fields")
    same(read_json(result_files["sources.json"]), sources, "all source fields")
    # Open label body only after complete identity, format, retained-order and
    # policy reconstruction. Hashing labels above never parses them.
    labels = read_labels(artifact_path(plan["qrels"]["path"]))
    analysis = build_analysis(policies, labels)
    same(read_json(result_files["analysis.json"]), analysis, "all analysis fields")
    check_frozen(preflight)
    after = {portable(p): identity(p, True) for p in sorted(tracked)}
    same(after, before, "independent before/after custody")
    return {"schema": 1, "status": "passed", "method": "standalone Decimal parsers and Fraction fusion/bounds; no producer imports",
            "audited_fields": {"sources.json": "all", "policies.json": "all", "analysis.json": "all",
                               "manifest.json": "identities, phase, frozen set, complete inputs/cached/outputs, label gate, custody and wall cap",
                               "success.json": "all"},
            "query_count": 30, "team_count": 29, "member_count": 81, "heads_checked": 3300,
            "primary": analysis["primary"], "G-S": analysis["G-S"],
            "denominators": analysis["denominators"], "team_sign_counts": analysis["team_sign_counts"],
            "before": before, "after": after, "elapsed_seconds": time.monotonic() - started,
            "limits": ["Execution validates saved custody claims and immutable outputs, not an operating-system trace of producer label-read timing.",
                       "Same 30 development queries and fixed label snapshot; no population or source-independence inference."]}


def expect_failure(operation, message):
    try:
        operation()
    except (ValueError, UnicodeError):
        return
    raise AssertionError("failed rejection test: " + message)


def witness_orders():
    p = [f"p{i:02d}" for i in range(1, 10)]
    f = [f"f{i:02d}" for i in range(88)]
    return {
        "S": p + ["z", "x", "y"] + f,
        "R0": p + ["x", "z"] + f + ["y"],
        "R1": p + ["z", "x"] + f + ["y"],
        "R2": p + ["x"] + f + ["y", "z"],
        "R3": p + ["y", "f00", "z"] + f[1:] + ["x"],
    }


def self_test():
    start = time.monotonic()
    checked = []
    w = witness_orders()
    qs = ["1"]
    def make(groups, mapped=None):
        mapped = mapped or {r: r for runs in groups.values() for r in runs}
        return build_policies(groups, {"1": w["S"]}, {r: {"1": w[s]} for r, s in mapped.items()}, qs)
    positive = make({"pair": ["R0", "R3"]})
    require(positive["queries"]["1"]["teams"]["pair"]["G"][-1] == "z", "common-S group witness")
    require({h[-1] for h in positive["queries"]["1"]["teams"]["pair"]["members"].values()} == {"x", "y"},
            "common-S member witness")
    for label, expected in (({"x": 0, "y": 0, "z": 2}, Q(1, 10)),
                            ({"x": 1, "y": 2, "z": 0}, Q(-1, 10))):
        a = build_analysis(positive, {"1": label})
        require(Q(a["primary"]["lower"]["fraction"]) == Q(a["primary"]["upper"]["fraction"]) == expected,
                "both common-S effect signs")
    checked.append("common-S positive and negative exact witnesses")
    cancel = make({"one": ["a", "b"], "two": ["c", "d"]}, {"a": "R0", "b": "R1", "c": "R1", "d": "R2"})
    a = build_analysis(cancel, {"1": {"x": 0}})
    require(a["primary"]["width"] == rat(0) and a["primary"]["unknown_support"] == 0, "cross-team cancellation")
    require(sum(Q(row["G-meanH"]["width"]["fraction"]) for row in a["per_team"].values()) > 0,
            "loose uncanceled team bounds")
    checked.append("opposed shared unknown cancels across teams before bounding")
    cross_query = bounds({("1", "x"): Q(1, 10), ("2", "x"): Q(-1, 10)}, {"1": {}, "2": {}})
    require(cross_query["lower"] == rat(Q(-1, 10)) and cross_query["upper"] == rat(Q(1, 10))
            and cross_query["unknown_support"] == 2, "document IDs across queries are distinct unknowns")
    checked.append("same document ID on different queries remains two unknown labels")
    clone = make({"clone": ["a", "b", "c"]}, {"a": "R0", "b": "R0", "c": "R0"})
    a = build_analysis(clone, {"1": {}})
    require(a["primary"]["lower"] == a["primary"]["upper"] == rat(0), "literal-copy zero")
    checked.append("literal-copy identity independent of labels")
    # Direct abstract heads isolate pair/triple weighting without assuming a
    # synthetic ranking construction can realize every possible head pattern.
    common = [f"p{i:02d}" for i in range(1, 10)]
    toy = {"query_ids": ["1"], "teams": ["pair", "triple"],
           "groups": {"pair": ["a", "b"], "triple": ["c", "d", "e"]},
           "parameters": {"group_size_lcm": 6}, "queries": {"1": {"S": common + ["x"], "teams": {
               "pair": {"G": common + ["z"], "members": {r: common + ["x"] for r in ("a", "b")}},
               "triple": {"G": common + ["x"], "members": {r: common + ["z"] for r in ("c", "d", "e")}}
           }}}}
    a = build_analysis(toy, {"1": {"x": 0, "z": 1}})
    require(a["primary"]["known"] == rat(0), "equal teams despite unequal members")
    require(Q(2, 5) * Q(1, 10) + Q(3, 5) * Q(-1, 10) == Q(-1, 50), "incorrect pooled-member control")
    checked.append("equal-team versus pooled-member normalization")
    # Exhaust every binary label completion for every coefficient triple on a
    # small grid, including zero and shared-pair cancellation.
    tables, completions = 0, 0
    for weights in itertools.product((-2, -1, 0, 1, 2), repeat=3):
        coeff = {("1", d): Q(c, 10) for d, c in zip(("x", "y", "z"), weights)}
        b = bounds(coeff, {"1": {}})
        actual = [sum(coeff["1", d] * y for d, y in zip(("x", "y", "z"), ys))
                  for ys in itertools.product((0, 1), repeat=3)]
        require(rat(min(actual)) == b["lower"] and rat(max(actual)) == b["upper"], "sharp endpoints attained")
        tables += 1
        completions += len(actual)
    checked.append(f"exhaustive sharpness: {tables} coefficient tables, {completions} completions")
    with tempfile.TemporaryDirectory(prefix="cycle22-independent-") as directory:
        base = Path(directory)
        inv = base / "docids"
        inv.write_bytes(b"a\nb\na\n A.; Bennett \n")
        require(read_docids(inv) == {"a", "b", " A.; Bennett "}, "opaque inventory exact dedup")
        for bad in (b"", b" \n", b"a\n\n", b"a\r\n", b"a\v\nb", b"\xff\n"):
            inv.write_bytes(bad)
            expect_failure(lambda: read_docids(inv), "inventory control/empty")
        path = base / "run"
        # A difference past Decimal's default context precision must survive.
        valid = "1 Q0 b 0 1.00000000000000000000000000000000001 run\n1 Q0 a 8 1 run\n"
        path.write_text(valid)
        order, diag = read_run(path, "run", {"a", "b"}, qs)
        require(order["1"] == ["b", "a"] and diag["queries"]["1"]["supplied_rank_disagreements"] == 2,
                "exact Decimal and ignored nonnegative rank")
        path.write_text("1 Q0 b +01 1.0 run\n1 Q0 a 000 1 run\n")
        order, diag = read_run(path, "run", {"a", "b"}, qs)
        require(order["1"] == ["a", "b"] and diag["queries"]["1"]["tie_excess"] == 1, "exact ties by ID")
        short = build_policies({"pair": ["a", "b"]}, {"1": w["S"]},
                               {"a": {"1": ["x"]}, "b": {"1": ["y", "z"]}}, qs)
        require(short["queries"]["1"]["retained_depths"]["members"] == {"a": 1, "b": 2}, "valid short retained sources")
        for bad in (valid + valid.splitlines()[0] + "\n", valid.replace(" run", " wrong"),
                    valid.replace(" 0 ", " -1 "), valid.replace(" 0 ", " 1.0 "),
                    valid.replace("1.00000000000000000000000000000000001", "NaN"),
                    valid.replace("1.00000000000000000000000000000000001", "Infinity"),
                    "1 Q0 a 1 1\n", valid.replace("1 Q0", "2 Q0"), valid.replace(" b ", " outside "), ""):
            path.write_text(bad)
            expect_failure(lambda: read_run(path, "run", {"a", "b"}, qs), "malformed run")
        path.write_text(valid)
        expect_failure(lambda: read_run(path, "run", {"a", "b"}, ["1", "2"]), "missing run query")
        depthdocs = {f"d{i:04d}" for i in range(1001)}
        deep = "".join(f"1 Q0 d{i:04d} {i} {1001-i} run\n" for i in range(1001))
        path.write_text(deep)
        expect_failure(lambda: read_run(path, "run", depthdocs, qs), "excessive source depth")
        path.write_text("\n".join(deep.splitlines()[:1000]) + "\n")
        order, diag = read_run(path, "run", depthdocs, qs)
        require(len(order["1"]) == 100 and diag["queries"]["1"]["full_depth"] == 1000, "1000-row valid cap and retention")
        qrel = base / "qrels"
        qrel.write_text("1 0.5 inert 0\n1 1 a 1\n1 2 b 2\n")
        require(read_labels(qrel, qs) == {"1": {"inert": 0, "a": 1, "b": 2}}, "literal grades and inert label")
        for bad in ("1 1 inert 0\n1 1 inert 0\n", "1 1 a 1.0\n", "1 1 a 3\n", "1 NaN a 1\n", "1 0 a 1\n"):
            qrel.write_text(bad)
            expect_failure(lambda: read_labels(qrel, qs), "qrel domain or duplicate")
    checked.extend(("whole-line inventory semantics, no control or blank keys",
                    "Decimal precision, canonical ties, ignored rank, valid short lists",
                    "malformed, duplicate, missing-query, invalid-tag, nonfinite parser rejections",
                    "literal qrel grades, positive finite iteration, inert-label duplicate rejection"))
    # Fraction kernels never receive labels; changing labels changes only analysis.
    same(make({"pair": ["R0", "R3"]}), positive, "policy replay without labels")
    checked.append("label-free policy construction and replay")
    return {"status": "passed", "tests": checked, "elapsed_seconds": time.monotonic() - start}


def timed_out(signum, frame):
    raise TimeoutError("independent verifier exceeded 300-second wall cap")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    for name in ("result", "preflight", "inputs", "acquisition", "output"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(300)
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    require(all(getattr(args, name) is not None for name in ("result", "preflight", "inputs", "acquisition", "output")),
            "all execution paths are required")
    require(not args.output.exists(), "refusing to overwrite verifier receipt")
    started = time.monotonic()
    try:
        receipt = verify(args)
        receipt["command"] = sys.argv
    except Exception as error:
        receipt = {"schema": 1, "status": "failed", "error_type": type(error).__name__, "error": str(error),
                   "command": sys.argv, "elapsed_seconds": time.monotonic() - started}
    finally:
        signal.alarm(0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({k: receipt[k] for k in ("status", "elapsed_seconds")}))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
