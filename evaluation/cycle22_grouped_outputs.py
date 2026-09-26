"""Provisional submission-group fusion experiment; no acquisition capability.

Inputs are already canonical retained rank orders. Build policies before passing
labels to analyze. Team membership is a fixed submission census, not an inferred
dependence class. All arithmetic used for ranks, metrics, and bounds is exact.
"""

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
from math import lcm
from pathlib import Path
import re
import signal
import sys
import time


DEPTH = 100
K = 60
HEAD = 10
UNITS = lcm(*range(K + 1, K + DEPTH + 1))
POLICY_SCHEMA = "cycle22-grouped-policies-v1-provisional"
ANALYSIS_SCHEMA = "cycle22-grouped-analysis-v1-provisional"
ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "_sessions/cycles/2026-09-26-cycle22-protocol.md"
PLAN = "_sessions/cycles/2026-09-26-cycle22-input-plan.json"
SOURCE = "evaluation/cycle22_grouped_outputs.py"
TESTS = "evaluation/tests/test_cycle22_grouped_outputs.py"
ACQUIRER = "_sessions/tools/acquire_cycle22_inputs.py"
ACQUIRER_TESTS = "evaluation/tests/test_cycle22_acquisition.py"
CHECKER = "_sessions/tools/check_cycle22_grouped_outputs.py"
QUERY_IDS = [str(i) for i in range(1, 31)]


def _token(value):
    return isinstance(value, str) and bool(value) and all(33 <= ord(c) <= 126 for c in value)


def _check_inputs(groups, runs, s_orders, query_ids):
    if not isinstance(query_ids, list) or not query_ids or any(not _token(q) for q in query_ids):
        raise ValueError("query_ids must be a nonempty list of printable tokens")
    if len(set(query_ids)) != len(query_ids):
        raise ValueError("duplicate query ID")
    if not isinstance(groups, dict) or not groups or any(not _token(t) for t in groups):
        raise ValueError("groups must contain named teams")
    members = []
    for team, names in groups.items():
        if not isinstance(names, list) or len(names) < 2 or any(not _token(r) for r in names):
            raise ValueError(f"team {team}: require at least two named members")
        members.extend(names)
    if len(set(members)) != len(members):
        raise ValueError("duplicate member ID within or across teams")
    if not isinstance(runs, dict) or set(runs) != set(members):
        raise ValueError("runs must match the complete declared member census")
    for name, orders, is_s in [("S", s_orders, True), *((r, o, False) for r, o in runs.items())]:
        if not isinstance(orders, dict) or set(orders) != set(query_ids):
            raise ValueError(f"source {name}: query cohort mismatch")
        for qid, docs in orders.items():
            if (not isinstance(docs, list) or not 1 <= len(docs) <= DEPTH
                    or (is_s and len(docs) != DEPTH)
                    or any(not _token(d) for d in docs) or len(set(docs)) != len(docs)):
                raise ValueError(f"source {name}, query {qid}: require unique retained tokens (S=100, members=1..100)")


def _vector(order):
    return {doc: UNITS // (K + rank) for rank, doc in enumerate(order, 1)}


def _head(scores):
    return sorted(scores, key=lambda doc: (-scores[doc], doc))[:HEAD]


def build_policies(groups, runs, s_orders, query_ids):
    """Fuse normalized retained orders, without any label argument or access.

    G uses average member reciprocal contribution plus S. A member H uses that
    member plus S. Identical outputs under distinct run IDs retain multiplicity.
    """
    _check_inputs(groups, runs, s_orders, query_ids)
    teams = sorted(groups)
    group_lcm = lcm(*(len(groups[t]) for t in teams))
    queries = {}
    for qid in query_ids:
        s = _vector(s_orders[qid])
        team_heads = {}
        for team in teams:
            names = groups[team]
            group_scores = defaultdict(int, {d: len(names) * v for d, v in s.items()})
            member_heads = {}
            for name in names:
                a = _vector(runs[name][qid])
                member_scores = dict(s)
                for doc, value in a.items():
                    member_scores[doc] = member_scores.get(doc, 0) + value
                    group_scores[doc] += value
                member_heads[name] = _head(member_scores)
            team_heads[team] = {"G": _head(group_scores), "members": member_heads}
        queries[qid] = {"S": list(s_orders[qid][:HEAD]), "teams": team_heads,
                        "retained_depths": {"S": len(s_orders[qid]),
                                            "members": {r: len(runs[r][qid]) for t in teams for r in groups[t]}}}
    return {
        "schema": POLICY_SCHEMA,
        "query_ids": list(query_ids),
        "teams": teams,
        "groups": {t: list(groups[t]) for t in teams},
        "parameters": {"depth_cap": DEPTH, "s_depth": DEPTH, "k": K, "head": HEAD,
                       "reciprocal_units": str(UNITS), "group_size_lcm": group_lcm},
        "retained": {"S": {q: list(s_orders[q]) for q in query_ids},
                     "members": {r: {q: list(runs[r][q]) for q in query_ids}
                                 for t in teams for r in groups[t]}},
        "queries": queries,
    }


def _check_policies(policies):
    if policies.get("schema") != POLICY_SCHEMA:
        raise ValueError("unsupported policy schema")
    groups, qids = policies["groups"], policies["query_ids"]
    retained = policies["retained"]
    _check_inputs(groups, retained["members"], retained["S"], qids)
    if policies["teams"] != sorted(groups) or set(policies["queries"]) != set(qids):
        raise ValueError("policy team/query cohort mismatch")
    expected = {"depth_cap": DEPTH, "s_depth": DEPTH, "k": K, "head": HEAD,
                "reciprocal_units": str(UNITS),
                "group_size_lcm": lcm(*(len(names) for names in groups.values()))}
    if policies["parameters"] != expected:
        raise ValueError("policy parameters mismatch")
    for qid in qids:
        row = policies["queries"][qid]
        if row["S"] != retained["S"][qid][:HEAD] or set(row["teams"]) != set(groups):
            raise ValueError("fixed S replay or team cohort mismatch")
        depths = {"S": len(retained["S"][qid]),
                  "members": {r: len(retained["members"][r][qid]) for names in groups.values() for r in names}}
        if row["retained_depths"] != depths:
            raise ValueError("retained depth metadata mismatch")
        for team, names in groups.items():
            entry = row["teams"][team]
            if set(entry["members"]) != set(names):
                raise ValueError("member head census mismatch")
            group_pool = set(retained["S"][qid])
            for name in names:
                member_pool = set(retained["members"][name][qid]) | set(retained["S"][qid])
                group_pool.update(member_pool)
                _check_head(entry["members"][name], member_pool)
            _check_head(entry["G"], group_pool)


def _check_head(head, pool):
    if not isinstance(head, list) or len(head) != HEAD or len(set(head)) != HEAD or not set(head) <= pool:
        raise ValueError("head must contain ten unique allowed documents")


def _add(target, source, scale=Fraction(1)):
    for pair, coefficient in source.items():
        target[pair] += coefficient * scale


def _clean(coefficients):
    return {pair: value for pair, value in coefficients.items() if value}


def _bounds(coefficients, labels):
    known = Fraction()
    lower_unknown = upper_unknown = Fraction()
    unknown_support = 0
    for pair, coefficient in coefficients.items():
        if not coefficient:
            continue
        if pair in labels:
            known += coefficient * (labels[pair] > 0)
        else:
            unknown_support += 1
            lower_unknown += min(coefficient, 0)
            upper_unknown += max(coefficient, 0)
    lower, upper = known + lower_unknown, known + upper_unknown
    if lower > 0:
        sign = "positive"
    elif upper < 0:
        sign = "negative"
    elif lower == upper == 0:
        sign = "zero"
    elif lower == 0:
        sign = "nonnegative"
    elif upper == 0:
        sign = "nonpositive"
    else:
        sign = "unresolved"
    return {"known": known, "lower": lower, "upper": upper, "width": upper - lower,
            "unknown_support": unknown_support, "sign": sign,
            "decision": "positive" if lower > 0 else "nonpositive" if upper <= 0 else "unresolved"}


def _p10(qid, head, labels):
    return Fraction(sum(labels.get((qid, d), 0) > 0 for d in head), HEAD)


def _mean(values):
    return sum(values, Fraction()) / len(values)


def _encode(value):
    if isinstance(value, Fraction):
        return {"fraction": f"{value.numerator}/{value.denominator}", "value": float(value)}
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    return value


def analyze(policies, labels):
    """Evaluate frozen heads with shared-pair exact sharp binary P@10 bounds.

    Missing labels are unknown for bounds, and zero only for the separately
    named benchmark. Labels outside all policy support are inert.
    """
    _check_policies(policies)
    if not isinstance(labels, dict):
        raise ValueError("labels must map (query, document) tuples to exact grades")
    for pair, grade in labels.items():
        if (not isinstance(pair, tuple) or len(pair) != 2 or any(not _token(x) for x in pair)
                or type(grade) is not int or grade not in (0, 1, 2)):
            raise ValueError("invalid label pair or grade")
    teams, qids, groups = policies["teams"], policies["query_ids"], policies["groups"]
    nt, nq = len(teams), len(qids)
    gm = policies["parameters"]["group_size_lcm"]
    denominator = HEAD * nt * nq * gm
    integer_primary = defaultdict(int)
    global_context = defaultdict(Fraction)
    primary_by_query = defaultdict(Fraction)
    team_coeff = {t: defaultdict(Fraction) for t in teams}
    team_context = {t: defaultdict(Fraction) for t in teams}
    per_query = {}
    team_benchmarks = {t: [] for t in teams}
    for qid in qids:
        row = policies["queries"][qid]
        qcoeff, qcontext = defaultdict(Fraction), defaultdict(Fraction)
        qteams = {}
        for team in teams:
            names, entry = groups[team], row["teams"][team]
            coefficients, context = defaultdict(Fraction), defaultdict(Fraction)
            for doc in entry["G"]:
                coefficients[qid, doc] += Fraction(1, HEAD)
                context[qid, doc] += Fraction(1, HEAD)
                integer_primary[qid, doc] += gm
            for name in names:
                for doc in entry["members"][name]:
                    coefficients[qid, doc] -= Fraction(1, HEAD * len(names))
                    integer_primary[qid, doc] -= gm // len(names)
            for doc in row["S"]:
                context[qid, doc] -= Fraction(1, HEAD)
            assert sum(coefficients.values()) == sum(context.values()) == 0
            _add(qcoeff, coefficients, Fraction(1, nt))
            _add(qcontext, context, Fraction(1, nt))
            _add(team_coeff[team], coefficients, Fraction(1, nq))
            _add(team_context[team], context, Fraction(1, nq))
            members = {name: _p10(qid, entry["members"][name], labels) for name in names}
            benchmark = {"G": _p10(qid, entry["G"], labels),
                         "meanH": _mean(list(members.values())),
                         "S": _p10(qid, row["S"], labels), "members": members}
            qteams[team] = {"G-meanH": _bounds(coefficients, labels),
                            "G-S": _bounds(context, labels), "benchmark": benchmark}
            team_benchmarks[team].append(benchmark)
        _add(primary_by_query, qcoeff, Fraction(1, nq))
        _add(global_context, qcontext, Fraction(1, nq))
        qbenchmark = {key: _mean([qteams[t]["benchmark"][key] for t in teams])
                      for key in ("G", "meanH", "S")}
        per_query[qid] = {"primary": _bounds(qcoeff, labels),
                          "G-S": _bounds(qcontext, labels), "benchmark": qbenchmark,
                          "teams": qteams}
    primary_coeff = {pair: Fraction(value, denominator) for pair, value in integer_primary.items() if value}
    assert primary_coeff == _clean(primary_by_query)
    context_coeff = _clean(global_context)
    per_team = {}
    for team in teams:
        rows = team_benchmarks[team]
        benchmark = {key: _mean([b[key] for b in rows]) for key in ("G", "meanH", "S")}
        benchmark["members"] = {r: _mean([b["members"][r] for b in rows]) for r in groups[team]}
        per_team[team] = {"G-meanH": _bounds(team_coeff[team], labels),
                          "G-S": _bounds(team_context[team], labels), "benchmark": benchmark}
    benchmark = {key: _mean([per_team[t]["benchmark"][key] for t in teams])
                 for key in ("G", "meanH", "S")}
    benchmark["G-meanH"] = benchmark["G"] - benchmark["meanH"]
    benchmark["G-S"] = benchmark["G"] - benchmark["S"]
    primary, context = _bounds(primary_coeff, labels), _bounds(context_coeff, labels)
    assert primary["known"] == benchmark["G-meanH"]
    assert context["known"] == benchmark["G-S"]
    assert primary["width"] <= _mean([per_team[t]["G-meanH"]["width"] for t in teams])
    ledger = []
    for qid in qids:
        docs = sorted({d for q, d in primary_coeff.keys() | context_coeff.keys() if q == qid})
        for doc in docs:
            pair = qid, doc
            grade = labels.get(pair)
            ledger.append({"query_id": qid, "doc_id": doc,
                           "primary_numerator": integer_primary.get(pair, 0),
                           "primary": primary_coeff.get(pair, Fraction()),
                           "G-S": context_coeff.get(pair, Fraction()),
                           "grade": grade, "binary": None if grade is None else int(grade > 0)})
    return _encode({
        "schema": ANALYSIS_SCHEMA, "query_ids": list(qids), "teams": list(teams),
        "qrels_pair_count": len(labels),
        "denominators": {"group_size_lcm": gm, "primary_mean": denominator,
                         "primary_per_query": denominator // nq},
        "primary": primary, "G-S": context, "benchmark_missing_zero": benchmark,
        "benchmark_convention": "binary P@10; missing labels assigned zero",
        "team_sign_counts": {contrast: {sign: sum(per_team[t][key]["sign"] == sign for t in teams)
                                         for sign in ("positive", "negative", "zero", "nonnegative", "nonpositive", "unresolved")}
                             for contrast, key in (("primary", "G-meanH"), ("G-S", "G-S"))},
        "per_query": per_query, "per_team": per_team, "pair_coefficients": ledger,
        "checks": {"global_equals_query_average": True, "coefficient_sums_zero": True,
                   "benchmark_matches_known_term": True, "pooled_width_no_larger_than_team_mean": True},
    })


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def parse_docids(text):
    """Opaque printable ASCII lines; deduplicate full keys without splitting."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    _need(bool(lines), "empty document inventory")
    for number, line in enumerate(lines, 1):
        _need(bool(line.strip()) and all(32 <= ord(c) <= 126 for c in line),
              f"docids line {number}: invalid opaque ID")
    return set(lines)


def _decimal(token, location):
    _need(_token(token), f"{location}: invalid numeric token")
    try:
        number = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError(f"{location}: invalid number") from exc
    _need(number.is_finite(), f"{location}: nonfinite number")
    return number


def parse_run(text, docids, run_tag, query_ids=QUERY_IDS):
    """Validate full submitted depth, then canonicalize and retain at most100."""
    rows = {q: {} for q in query_ids}
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        location = f"run {run_tag}, line {number}"
        _need(len(fields) == 6, location + ": expected six fields")
        qid, unused, doc, supplied, score, tag = fields
        _need(qid in rows, location + ": unexpected query")
        _need(_token(doc) and doc in docids, location + ": ID outside inventory")
        _need(_token(unused) and tag == run_tag, location + ": invalid token or run tag")
        _need(re.fullmatch(r"\+?[0-9]+", supplied) is not None,
              location + ": supplied rank must be an ASCII nonnegative integer")
        numeric = _decimal(score, location)
        _need(doc not in rows[qid], location + ": duplicate query/document")
        rows[qid][doc] = (numeric, score, int(supplied))
        _need(len(rows[qid]) <= 1000, location + ": depth exceeds1000")
    queries = {}
    for qid in query_ids:
        bucket = rows[qid]
        _need(1 <= len(bucket) <= 1000, f"run {run_tag}, query {qid}: depth outside1..1000")
        order = sorted(bucket, key=lambda d: (bucket[d][0].copy_negate(), d))
        ties = [n for n in Counter(v[0] for v in bucket.values()).values() if n > 1]
        queries[qid] = {
            "full_depth": len(order), "retained_depth": min(DEPTH, len(order)),
            "retained_order": order[:DEPTH], "tie_groups": len(ties),
            "tied_documents": sum(ties), "tie_excess": sum(n - 1 for n in ties),
            "supplied_rank_disagreements": sum(bucket[d][2] != rank for rank, d in enumerate(order, 1)),
            "retained_details": [{"doc_id": d, "score": bucket[d][1], "supplied_rank": bucket[d][2],
                                  "canonical_rank": rank} for rank, d in enumerate(order[:DEPTH], 1)],
        }
    return {"run_tag": run_tag, "row_count": sum(len(v) for v in rows.values()), "queries": queries}


def parse_qrels(text, query_ids=QUERY_IDS):
    labels = {}
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        location = f"qrels line {number}"
        _need(len(fields) == 4, location + ": expected four fields")
        qid, iteration, doc, grade = fields
        _need(qid in query_ids and _token(doc), location + ": invalid query or document")
        _need(grade in ("0", "1", "2"), location + ": invalid grade")
        _need(_decimal(iteration, location) > 0, location + ": iteration must be positive")
        _need((qid, doc) not in labels, location + ": duplicate query/document")
        labels[qid, doc] = int(grade)
    _need({q for q, _ in labels} == set(query_ids), "qrels query cohort mismatch")
    return labels


def identity(path):
    sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": sha.hexdigest(), "md5": md5.hexdigest()}


def _display(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, data):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(data, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
        handle.write("\n")


def execute(preflight_path, inputs, acquisition_path, output):
    """One exclusive producer attempt. Caller supplies an external300s cap too."""
    preflight_path, inputs, acquisition_path, output = map(Path, (preflight_path, inputs, acquisition_path, output))
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    tracked = {}
    stage = "custody"

    def track(path, expected=None):
        path = Path(path).resolve()
        found = identity(path)
        if expected is not None:
            for key in ("sha256", "bytes", "md5"):
                if key in expected:
                    _need(found[key] == expected[key], f"identity mismatch: {_display(path)} ({key})")
        tracked[str(path)] = found
        return found

    def after():
        result = {}
        for path in tracked:
            try:
                result[_display(path)] = identity(path)
            except OSError as exc:
                result[_display(path)] = {"error": type(exc).__name__}
        return result

    def elapsed_gate():
        _need(time.monotonic() - started < 300, "producer300-second limit exceeded")

    try:
        preflight_id = track(preflight_path)
        acquisition_id = track(acquisition_path)
        preflight, acquisition = _json(preflight_path), _json(acquisition_path)
        frozen = preflight.get("frozen", {})
        _need(preflight.get("status") == "passed" and isinstance(frozen, dict), "preflight failed")
        _need({PROTOCOL, PLAN, SOURCE, TESTS, ACQUIRER, ACQUIRER_TESTS, CHECKER} <= set(frozen), "required frozen keys absent")
        for name, sha in frozen.items():
            track(ROOT / name, {"sha256": sha})
        _need(acquisition.get("schema") == 1 and acquisition.get("status") == "passed" and acquisition.get("frozen") == frozen,
              "acquisition failed or frozen map differs")
        _need(acquisition.get("preflight_sha256") == preflight_id["sha256"], "acquisition preflight differs")
        plan = _json(ROOT / PLAN)
        _need(acquisition.get("plan_sha256") == identity(ROOT / PLAN)["sha256"], "acquisition plan differs")
        _need(plan["query_ids"] == QUERY_IDS, "planned query cohort differs")
        groups = plan["groups"]
        names = [r for members in groups.values() for r in members]
        _need(len(groups) == 29 and len(names) == len(set(names)) == 81
              and Counter(map(len, groups.values())) == {2: 6, 3: 23}, "planned group census differs")
        _need(set(plan["items"]) == set(names) == set(acquisition["inputs"]), "acquired member census differs")
        cached = {}
        for key in ("inventory", "S", "prior_verification", "docids", "qrels"):
            spec = plan[key]
            path = ROOT / spec["path"]
            cached[key] = {"path": _display(path), **track(path, spec)}
        decoded_paths = {}
        input_ids = {}
        for name in sorted(names):
            spec, receipt = plan["items"][name], acquisition["inputs"][name]
            filename = spec["filename"]
            _need(Path(filename).name == filename and receipt["filename"] == filename, "unsafe or changed input filename")
            path = inputs / filename
            info = track(path, receipt)
            _need(receipt["publisher_md5"] == spec["publisher_md5"], "publisher MD5 changed")
            raw = receipt["raw"]
            _need(receipt["raw_filename"] == filename + ".download", "raw filename differs")
            raw_path = inputs / receipt["raw_filename"]
            raw_info = track(raw_path, raw)
            with raw_path.open("rb") as handle:
                _need(receipt["gzip"] == (handle.read(2) == b"\x1f\x8b"), "compression flag differs")
            matched = [key for key, layer in (("raw", raw_info), ("expanded", info))
                       if layer["md5"] == spec["publisher_md5"]]
            _need(bool(matched) and matched == receipt["matched_representation"], "publisher MD5 representation differs")
            _need(raw_info["bytes"] <= spec["max_bytes"] and info["bytes"] <= plan["max_expanded_per_run"], "input byte cap exceeded")
            decoded_paths[name] = path
            input_ids[name] = {"path": _display(path), **info, "raw_path": _display(raw_path),
                               "raw": raw, "gzip": receipt["gzip"], "matched_representation": matched,
                               "publisher_md5": spec["publisher_md5"]}
        _need(sum(info["raw"]["bytes"] for info in input_ids.values()) <= plan["max_total_bytes"], "total transfer cap exceeded")
        _need(sum(info["bytes"] for info in input_ids.values()) <= plan["max_total_expanded_bytes"], "total expanded cap exceeded")
        _need(acquisition["transfer_bytes_complete_bodies"] == sum(info["raw"]["bytes"] for info in input_ids.values())
              and acquisition["expanded_bytes_complete_bodies"] == sum(info["bytes"] for info in input_ids.values()),
              "acquisition byte totals differ")
        elapsed_gate()
        stage = "rankings"
        inventory = _json(ROOT / plan["inventory"]["path"])
        eligible = [row for row in inventory["teams"] if row["eligible"]]
        _need(all(len(row["automatic_runs"]) == len(set(row["automatic_runs"])) for row in eligible),
              "duplicate member in metadata group")
        inventory_groups = {row["team"]: sorted(row["automatic_runs"]) for row in eligible}
        _need(len(inventory_groups) == len(eligible)
              and inventory_groups == {t: sorted(names) for t, names in groups.items()}
              and inventory["eligible_teams"] == 29 and inventory["eligible_runs"] == 81,
              "metadata group census differs")
        _need(inventory["archive_metadata_team_and_run_match"] is True and inventory["run_bodies_fetched"] is False,
              "metadata census validation flags differ")
        records = {row["run"]: row for row in inventory["runs"]}
        _need(len(records) == len(inventory["runs"]), "duplicate metadata run ID")
        for team, members in groups.items():
            for name in members:
                row, spec = records[name], plan["items"][name]
                _need(row["team"] == team and row["type"] == "automatic"
                      and row["publisher_md5"] == spec["publisher_md5"] and row["url"] == spec["url"],
                      "metadata member identity differs")
        prior = _json(ROOT / plan["prior_verification"]["path"])
        _need(prior.get("status") == "passed", "prior S verification failed")
        _need(prior["custody"]["outputs"]["policies.json"]["sha256"] == plan["S"]["sha256"],
              "prior S verification binding differs")
        historical = _json(ROOT / plan["S"]["path"])
        _need(historical["query_ids"] == QUERY_IDS, "historical S query cohort differs")
        s_orders = {q: historical["queries"][q]["sources"]["S"]["retained_order"] for q in QUERY_IDS}
        docids = parse_docids((ROOT / plan["docids"]["path"]).read_bytes().decode("ascii"))
        _need(all(d in docids for order in s_orders.values() for d in order), "S ID outside inventory")
        source_rows = {}
        for name in sorted(names):
            source_rows[name] = parse_run(decoded_paths[name].read_bytes().decode("ascii"), docids, name)
            elapsed_gate()
        runs = {name: {q: source_rows[name]["queries"][q]["retained_order"] for q in QUERY_IDS} for name in names}
        policies = build_policies(groups, runs, s_orders, QUERY_IDS)
        for q in QUERY_IDS:
            _need(policies["queries"][q]["S"] == historical["queries"][q]["policies"]["S"], "S head replay differs")
        sources = {"schema": "cycle22-grouped-sources-v1-provisional", "query_ids": QUERY_IDS,
                   "runs": source_rows}
        _write(output / "sources.json", sources)
        _write(output / "policies.json", policies)
        policy_id = track(output / "policies.json")
        stage = "labels"
        labels = parse_qrels((ROOT / plan["qrels"]["path"]).read_bytes().decode("ascii"))
        _write(output / "analysis.json", analyze(policies, labels))
        elapsed_gate()
        _need(identity(output / "policies.json") == policy_id, "frozen policy bytes changed")
        before = {_display(path): info for path, info in tracked.items()}
        final = after()
        _need(final == before, "tracked source/input bytes changed during execution")
        manifest = {"schema": 1, "phase": "cycle22", "frozen": frozen,
                    "preflight": {"path": _display(preflight_path), **preflight_id},
                    "acquisition": {"path": _display(acquisition_path), **acquisition_id},
                    "inputs": input_ids, "cached": cached, "tracked_before": before, "tracked_after": final,
                    "labels_joined_after_policies_sha256": policy_id["sha256"],
                    "outputs": {name: identity(output / name) for name in ("sources.json", "policies.json", "analysis.json")},
                    "elapsed_seconds": time.monotonic() - started}
        _write(output / "manifest.json", manifest)
        _write(output / "success.json", {"status": "passed", "manifest": identity(output / "manifest.json")})
        return manifest
    except Exception as exc:
        _write(output / "failure.json", {"status": "failed", "phase": "cycle22", "stage": stage,
                                        "error_type": type(exc).__name__, "error": str(exc),
                                        "tracked_before": {_display(p): i for p, i in tracked.items()},
                                        "tracked_after": after(), "elapsed_seconds": time.monotonic() - started})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("preflight", "inputs", "acquisition", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)

    def timeout(signum, frame):
        raise TimeoutError("producer300-second wall limit exceeded")

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    try:
        execute(args.preflight, args.inputs, args.acquisition, args.output)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}))
        return 1
    finally:
        signal.alarm(0)
    print(json.dumps({"status": "passed", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
