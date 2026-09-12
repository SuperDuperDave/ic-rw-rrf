#!/usr/bin/env python3
"""One independent reconstruction of the completed frozen Cycle15 comparison.

Imports no production driver, fusion, lexical generator, or metric harness.
Reads raw data only after completed-result and synthetic-gate receipts pass.
No downloads, retrieval, fitting, parameter selection, or repair/retry runs.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "_sessions/evidence/2026-09-11-cycle14-input-plan.json"
PLAN_SHA = "051aed306d99e3431aa0cf60f17b7acdf1341becc20d37259c283155c134d18a"
REVISION = "ba38899cbd4de0fb699b47f39b64ef1c107e4a5c"
FROZEN_SOURCES = {
    "evaluation/generate_diverse_runs.py": "0702155886c270c507b5c4a3f21e1145782ba25d8b4fd430fc10dac7ef0233f8",
    "evaluation/fusion_contract.py": "72dd915f052c84dc79d1e6a604778a925e38be398dabcbd66c5e5ef63e1fc38f",
    "evaluation/trec_eval_harness.py": "0b437034007e0e6ccfd8979c3eee6603374afb2234b895bccc47546347c9b85b",
    "_sessions/cycles/2026-09-11-cycle14-transfer-protocol.md": "1ed94aea29e5a662f2a37f20047201c3dd4e7e3dd5f886038332ba5722342d5a",
}
NAMES = ("bm25", "bm25_tuned", "tfidf", "ql_dirichlet")
ARMS = ("P", "S", "A", "B", "H")
CONTRASTS = ("B-A", "B-S", "B-P", "A-P", "B-H")
ATOL = 1e-12
SCORE_RTOL = 1e-12
OFFICIAL_ATOL = 0.0000500001
STOPWORDS = set("""a an and are as at be but by for from has have he her his how i in is it its
me my no not of on or our she so than that the their them then there these they
this to too us was we were what when where which who will with you your""".split())


def need(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        need(key not in obj, "duplicate JSON field: " + key)
        obj[key] = value
    return obj


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=unique_object)


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def resolve(path):
    return (ROOT / Path(path)).resolve()


def identity(path):
    path = Path(path)
    size = path.stat().st_size
    sha = hashlib.sha256()
    blob = hashlib.sha1(f"blob {size}\0".encode())
    consumed = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            sha.update(chunk)
            blob.update(chunk)
            consumed += len(chunk)
    need(consumed == size == path.stat().st_size, "file changed while hashing")
    return {"bytes": size, "sha256": sha.hexdigest(), "git-blob-sha1": blob.hexdigest()}


def token_id(value):
    need(isinstance(value, str) and value and not any(char.isspace() for char in value), "invalid string identifier")
    return value


def tokenize(text):
    # Python's Unicode word class is str.isalnum plus '_'; excluding '_' gives
    # the original character-loop token boundaries through a separate path.
    return [word for word in re.findall(r"[^\W_]+", text.lower()) if len(word) > 1 and word not in STOPWORDS]


def prepare_terms(corpus, candidate_union):
    terms = {doc: Counter(tokenize(corpus[doc][0] + "\n" + corpus[doc][1])) for doc in candidate_union}
    lengths = {doc: sum(counts.values()) for doc, counts in terms.items()}
    df, cf = Counter(), Counter()
    for counts in terms.values():
        df.update(counts.keys())
        cf.update(counts)
    n = len(terms)
    total = sum(lengths.values())
    return terms, lengths, {"N": n, "avg_dl": total / max(1, n), "total_terms": total, "df": df, "cf": cf}


def document_scores(query_tokens, counts, dl, statistics):
    """Same stipulated formulas, independently combined in one term traversal.

    Keep query occurrence order and arithmetic grouping; duplicates count twice.
    Term counts and length were cached once per canonical document, unlike the
    original generator's per-ranker repeated tokenization.
    """
    if dl == 0:
        return (0.0, 0.0, 0.0, -1e10)
    n, average = statistics["N"], statistics["avg_dl"]
    scores = [0.0, 0.0, 0.0, 0.0]
    for term in query_tokens:
        tf = counts.get(term, 0)
        if tf:
            df = statistics["df"].get(term, 0)
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
            for index, (k1, b) in enumerate(((1.2, .75), (.9, .4))):
                normalized = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / average))
                scores[index] += idf * normalized
            scores[2] += (1 + math.log(tf)) * math.log(n / (df + 1))
        collection_probability = statistics["cf"].get(term, 0) / max(statistics["total_terms"], 1)
        probability = (tf + 2000 * collection_probability) / (dl + 2000)
        if probability > 0:
            scores[3] += math.log(probability)
    scores[2] /= math.sqrt(dl)
    return tuple(scores)


def reconstruct(qids, corpus, queries, sources):
    union = {doc for qid in qids for doc, _ in sources["P"][qid]}
    terms, lengths, stats = prepare_terms(corpus, union)
    runs = {name: {} for name in NAMES + ARMS}
    for qid in qids:
        query = tokenize(queries[qid])
        need(query, "empty tokenized query")
        full = {name: [] for name in NAMES}
        for doc, _ in sources["P"][qid]:
            scores = document_scores(query, terms[doc], lengths[doc], stats)
            for name, score in zip(NAMES, scores):
                need(math.isfinite(score), "nonfinite reconstructed lexical score")
                full[name].append((doc, score))
        for name in NAMES:
            runs[name][qid] = sorted(full[name], key=lambda row: -row[1])[:200]
        runs["P"][qid], runs["S"][qid] = sources["P"][qid], sources["S"][qid]
        four = [runs[name][qid] for name in NAMES]
        runs["A"][qid] = fuse(four)
        runs["B"][qid] = fuse(four + [runs["S"][qid]])
        runs["H"][qid] = fuse([runs["P"][qid], runs["S"][qid]])
    return runs, stats, union


def fuse(rankings):
    votes = {}
    for ranking in rankings:
        for rank, (doc, _) in enumerate(ranking, 1):
            votes.setdefault(doc, []).append(1 / (60 + rank))
    scores = [(doc, math.fsum(contributions)) for doc, contributions in votes.items()]
    return sorted(scores, key=lambda row: (-row[1], row[0]))


def binary_ndcg(ranking, grades):
    positives = sum(grade == 1 for grade in grades.values())
    ideal = math.fsum(1 / math.log2(rank + 1) for rank in range(1, min(positives, 10) + 1))
    actual = math.fsum(1 / math.log2(rank + 1) for rank, (doc, _) in enumerate(ranking[:10], 1) if grades.get(doc, 0) == 1)
    return actual / ideal if ideal else 0.0


def rbp(ranking, grades):
    p = 4 / 5
    return math.fsum((1 - p) * p ** index for index, (doc, _) in enumerate(ranking[:10]) if grades.get(doc, 0) == 1)


def paired(values):
    return {"mean_delta": math.fsum(values) / len(values), "n_queries": len(values),
            "positive": sum(value > 0 for value in values), "negative": sum(value < 0 for value in values),
            "zero": sum(value == 0 for value in values), "minimum": min(values), "maximum": max(values)}


def numeric_results(qids, grades, runs, union_fraction):
    rows = {}
    for qid in qids:
        ranking = {name: runs[name][qid] for name in ARMS}
        metrics = {name: binary_ndcg(ranking[name], grades[qid]) for name in ARMS}
        deltas = {name: metrics[name[0]] - metrics[name[2]] for name in CONTRASTS}
        rbps = {name: rbp(ranking[name], grades[qid]) for name in ("A", "B")}
        pool = {doc for doc, _ in ranking["P"]}
        rows[qid] = {
            "ndcg10": metrics, "ndcg10_deltas": deltas,
            "ndcg10_delta_signs": {name: (value > 0) - (value < 0) for name, value in deltas.items()},
            "rbp10_p_4_5": rbps, "rbp10_B-A": rbps["B"] - rbps["A"],
            "candidate_count": len(pool), "source_candidate_counts": {name: len(ranking[name]) for name in ("P", "S")},
            "arm_depths": {name: len(ranking[name]) for name in ARMS},
            "B_top10_outside_P": {"count": sum(doc not in pool for doc, _ in ranking["B"][:10]),
                                  "returned_top10": min(10, len(ranking["B"]))},
            "top10_without_explicit_qrel": {name: {"count": sum(doc not in grades[qid] for doc, _ in ranking[name][:10]),
                                                  "returned_top10": min(10, len(ranking[name]))} for name in ARMS}}
    summary = {
        "n_queries": len(qids), "qids": qids, "primary": "B-A",
        "means_ndcg10": {name: math.fsum(rows[qid]["ndcg10"][name] for qid in qids) / len(qids) for name in ARMS},
        "contrasts_ndcg10": {name: paired([rows[qid]["ndcg10_deltas"][name] for qid in qids]) for name in CONTRASTS},
        "means_rbp10_p_4_5": {name: math.fsum(rows[qid]["rbp10_p_4_5"][name] for qid in qids) / len(qids) for name in ("A", "B")},
        "contrast_rbp10_B-A": paired([rows[qid]["rbp10_B-A"] for qid in qids]),
        "P_candidate_union_over_corpus": union_fraction,
        "judgedness_totals": {name: {field: sum(rows[qid]["top10_without_explicit_qrel"][name][field] for qid in qids)
                                      for field in ("count", "returned_top10")} for name in ARMS},
        "B_top10_outside_P_totals": {field: sum(rows[qid]["B_top10_outside_P"][field] for qid in qids)
                                     for field in ("count", "returned_top10")}}
    return rows, summary


def compare_tree(expected, actual, location="value"):
    if isinstance(expected, dict):
        need(isinstance(actual, dict) and set(expected) == set(actual), "object keys differ: " + location)
        return max((compare_tree(value, actual[key], location + "/" + str(key)) for key, value in expected.items()), default=0.0)
    if isinstance(expected, list):
        need(isinstance(actual, list) and len(expected) == len(actual), "list shape differs: " + location)
        return max((compare_tree(a, b, location + "/" + str(i)) for i, (a, b) in enumerate(zip(expected, actual))), default=0.0)
    if type(expected) is float:
        need(type(actual) in (float, int) and math.isfinite(actual) and abs(expected - actual) <= ATOL,
             "numeric value differs: " + location)
        return abs(expected - actual)
    need(type(expected) is type(actual) and expected == actual, "exact value differs: " + location)
    return 0.0


def read_trec(path, name, qids):
    runs = {qid: [] for qid in qids}
    previous_qid = None
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            fields = line.split()
            need(len(fields) == 6 and fields[1] == "Q0" and fields[5] == name, "malformed saved TREC row: " + name)
            qid, doc = fields[0], token_id(fields[2])
            need(qid in runs and (previous_qid is None or qid >= previous_qid), "TREC query order/coverage differs: " + name)
            previous_qid = qid
            need(fields[3] == str(len(runs[qid]) + 1), "saved TREC ranks are not contiguous one-based: " + name)
            value = float(fields[4])
            need(math.isfinite(value), "nonfinite saved score: " + name)
            runs[qid].append((doc, value))
    for ranking in runs.values():
        need(len(ranking) == len({doc for doc, _ in ranking}), "duplicate saved document: " + name)
    return runs


def compare_rankings(expected, actual, name):
    maximum = 0.0
    need(set(expected) == set(actual), "saved query vector differs: " + name)
    for qid, ranking in expected.items():
        need([doc for doc, _ in ranking] == [doc for doc, _ in actual[qid]], "ranking order/depth differs: " + name + "/" + qid)
        for (_, wanted), (_, got) in zip(ranking, actual[qid]):
            require_equal = name in ("P", "S")
            need(wanted == got if require_equal else math.isclose(wanted, got, abs_tol=ATOL, rel_tol=SCORE_RTOL),
                 "full precision ranking score differs: " + name + "/" + qid)
            maximum = max(maximum, abs(wanted - got))
    return {"queries": len(expected), "rows": sum(len(ranking) for ranking in expected.values()),
            "exact_document_order_and_depth": True, "maximum_absolute_score_difference": maximum}


def read_binary_qrels(path):
    result = {}
    with Path(path).open(encoding="utf-8") as stream:
        need(next(stream).rstrip("\r\n") == "query-id\tcorpus-id\tscore", "wrong qrel header")
        for line in stream:
            fields = line.rstrip("\r\n").split("\t")
            need(len(fields) == 3 and fields[2] in ("0", "1"), "qrel grade/schema differs")
            qid, doc = token_id(fields[0]), token_id(fields[1])
            need(doc not in result.setdefault(qid, {}), "duplicate qrel pair")
            result[qid][doc] = int(fields[2])
    need(result, "empty qrels")
    return result


def read_cache(path, corpus, queries, all_qids):
    result = {}
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line, object_pairs_hook=unique_object)
            need(set(row) in ({"query", "candidates"}, {"query", "candidates", "invocations_history"}), "cache top-level schema differs")
            need("invocations_history" not in row or isinstance(row["invocations_history"], list), "cache invocation history schema differs")
            need(set(row["query"]) == {"qid", "text"}, "cache query schema differs")
            qid = token_id(row["query"]["qid"])
            need(qid in all_qids and qid not in result and row["query"]["text"] == queries[qid], "cache query identity/text/coverage differs")
            candidates = row["candidates"]
            need(isinstance(candidates, list) and len(candidates) <= 1000, "cache candidates/depth differs")
            ranking, seen, previous = [], set(), math.inf
            for item in candidates:
                need(set(item) == {"docid", "score", "doc"}, "cache candidate schema differs")
                docid, doc = token_id(item["docid"]), item["doc"]
                need(docid in corpus and docid not in seen, "cache document identity differs")
                need(set(doc) in ({"_id", "title", "text"}, {"_id", "title", "text", "metadata"}), "cache document schema differs")
                need("metadata" not in doc or isinstance(doc["metadata"], dict), "cache metadata schema differs")
                need(doc["_id"] == docid and (doc["title"], doc["text"]) == corpus[docid], "cache canonical document text differs")
                need(type(item["score"]) in (int, float), "cache score is not numeric")
                score = float(item["score"])
                need(math.isfinite(score) and score <= previous, "cache score finiteness/order differs")
                seen.add(docid)
                ranking.append((docid, score))
                previous = score
            result[qid] = ranking
    need(set(result) == set(all_qids), "cache complete query vector differs")
    return result


def read_canonical(paths, build, acquisition, plan):
    decoder = plan["optional_parquet_decoder"]
    wheel_row = next(row for row in acquisition["files"] if row["role"] == "decoder")
    wheel = resolve(wheel_row["path"])
    wheel_identity = identity(wheel)
    need(wheel_identity["sha256"] == decoder["expected_sha256"] and wheel_identity["bytes"] == decoder["expected_bytes"], "decoder wheel identity differs")
    directory = resolve(build["decoder_path"])
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            extracted = (directory / member.filename).resolve()
            need(extracted.is_relative_to(directory), "decoder extraction path escapes")
            with archive.open(member) as original, extracted.open("rb") as copied:
                while True:
                    chunk = original.read(1024 * 1024)
                    need(copied.read(len(chunk) or 1) == chunk, "decoder extracted bytes differ")
                    if not chunk:
                        break
    need("pyarrow" not in sys.modules, "audit requires isolated decoder import")
    sys.path.insert(0, str(directory))
    arrow = importlib.import_module("pyarrow")
    parquet = importlib.import_module("pyarrow.parquet")
    need(arrow.__version__ == decoder["version"] and Path(arrow.__file__).resolve().is_relative_to(directory), "decoder import version/origin differs")
    result = {}
    for role in ("corpus", "query_texts"):
        reader = parquet.ParquetFile(paths[role])
        schema = reader.schema_arrow
        need(set(schema.names) == {"_id", "title", "text"} and len(schema.names) == 3
             and all(arrow.types.is_string(field.type) or arrow.types.is_large_string(field.type) for field in schema), "canonical Parquet schema differs")
        rows = {}
        for batch in reader.iter_batches(batch_size=256):
            for row in batch.to_pylist():
                doc = token_id(row["_id"])
                need(doc not in rows and isinstance(row["title"], str) and isinstance(row["text"], str), "canonical row identity/text differs")
                rows[doc] = (row["title"], row["text"])
        result[role] = rows
    return result["corpus"], result["query_texts"]


def official_check(binary, qids, grades, runs, expected_rows, expected_summary, artifacts):
    qrels_path = artifacts / "official.qrels"
    with qrels_path.open("x") as stream:
        for qid in qids:
            for doc, grade in sorted(grades[qid].items()):
                stream.write(f"{qid} 0 {doc} {grade}\n")
    receipt = {}
    for arm in ARMS:
        run_path = artifacts / (arm + ".rank-proxy.trec")
        with run_path.open("x") as stream:
            for qid in qids:
                for rank, (doc, _) in enumerate(runs[arm][qid], 1):
                    stream.write(f"{qid} Q0 {doc} {rank} {-rank} {arm}\n")
        command = [str(binary), "-q", "-c", "-m", "ndcg_cut.10", str(qrels_path), str(run_path)]
        write_json(artifacts / (arm + ".official-command.json"), {"command": command, "absolute_tolerance": OFFICIAL_ATOL,
                   "timeout_seconds": 30, "qrels_sha256": identity(qrels_path)["sha256"], "run_sha256": identity(run_path)["sha256"]})
        completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30, env={**os.environ, "LC_ALL": "C"})
        (artifacts / (arm + ".official.stdout.txt")).write_text(completed.stdout)
        (artifacts / (arm + ".official.stderr.txt")).write_text(completed.stderr)
        need(completed.returncode == 0 and not completed.stderr.strip(), "official evaluator process failed: " + arm)
        official = parse_official(completed.stdout, qids)
        errors = {qid: abs(official[qid] - expected_rows[qid]["ndcg10"][arm]) for qid in qids}
        aggregate_error = abs(official["all"] - expected_summary["means_ndcg10"][arm])
        need(max(errors.values()) <= OFFICIAL_ATOL and aggregate_error <= OFFICIAL_ATOL, "official metric differs: " + arm)
        receipt[arm] = {"query_count": len(qids), "aggregate_denominator": len(qids), "official_mean": official["all"],
                        "maximum_per_query_absolute_difference": max(errors.values()), "aggregate_absolute_difference": aggregate_error,
                        "stdout_sha256": identity(artifacts / (arm + ".official.stdout.txt"))["sha256"], "command": command}
    return receipt


def parse_official(output, qids):
    result = {}
    for line in output.splitlines():
        parts = line.split()
        need(len(parts) == 3 and parts[0] == "ndcg_cut_10" and parts[1] not in result, "official row schema/duplicate differs")
        value = float(parts[2])
        need(math.isfinite(value) and 0 <= value <= 1, "official value invalid")
        result[parts[1]] = value
    need(set(result) == set(qids) | {"all"}, "official query denominator differs")
    return result


@contextmanager
def deadline(seconds):
    def expired(signum, frame):
        raise TimeoutError("independent audit reconstruction wall limit exceeded")
    need(signal.getitimer(signal.ITIMER_REAL)[0] == 0, "audit cannot replace an active timer")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def audit(args):
    output, artifacts, results = args.output.resolve(), args.artifacts.resolve(), args.results.resolve()
    need(not output.exists() and not artifacts.exists(), "audit outputs must be fresh")
    artifacts.mkdir(parents=True)
    evidence = {"status": "failed", "new_experiment": False, "production_code_imports": [],
                "source_sha256": identity(__file__)["sha256"], "evaluator_revision": REVISION,
                "tolerance": {"numeric_absolute": ATOL, "ranking_score_relative": SCORE_RTOL,
                              "source_scores": "exact", "rank_order": "exact", "official_absolute": OFFICIAL_ATOL}}
    started = time.monotonic()
    try:
        # These small receipt checks precede all collection-body/qrel reads.
        completed = read_json(results / "manifest.json")
        gate = read_json(args.metric_gate)
        build = read_json(args.build_receipt)
        acquisition = read_json(args.acquisition)
        need(completed["status"] == "completed" and completed["effectiveness_completed"] is True, "original comparison is not completed")
        need(gate["status"] == "passed" and gate["evaluator_revision"] == REVISION, "synthetic metric gate has not passed")
        need(completed["metric_gate"]["sha256"] == identity(args.metric_gate)["sha256"], "result metric gate linkage differs")
        need(build["status"] == "passed" and build["evaluator_revision"] == REVISION, "evaluator build has not passed")
        binary = resolve(build["binary_path"])
        need(identity(binary)["sha256"] == build["binary_sha256"] == gate["binary_sha256"], "official binary identity differs")
        need(gate["build_receipt_sha256"] == identity(args.build_receipt)["sha256"], "metric/build linkage differs")
        need(acquisition["status"] == "passed" and acquisition["input_plan_sha256"] == PLAN_SHA, "acquisition receipt differs")
        need(identity(PLAN)["sha256"] == PLAN_SHA, "frozen input plan differs")
        for relative, expected in FROZEN_SOURCES.items():
            need(identity(ROOT / relative)["sha256"] == expected, "frozen specification/source differs: " + relative)
        for relative, expected in completed["source_preflight"]["source_sha256"].items():
            source = resolve(relative)
            need(source.is_relative_to(ROOT) and identity(source)["sha256"] == expected, "executed source preflight differs")
        if args.preflight is not None:
            need(identity(args.preflight)["sha256"] == completed["source_preflight"]["sha256"], "requested preflight linkage differs")
        plan = read_json(PLAN)
        protocol = {**evidence, "status": "frozen_before_raw_input_reads", "command": sys.argv,
                    "hypothesis": "Independent frozen-formula reconstruction reproduces every ranking and reported result.",
                    "prediction": "Exact document order/depth and stipulated numerical tolerances hold for all queries and arms.",
                    "stopping_rule": "One complete reconstruction and one official invocation per fixed arm; preserve any discrepancy.",
                    "rng_used": False, "reconstruction_wall_cap_seconds": 600, "official_timeout_seconds_per_arm": 30,
                    "floating_point_policy": "Query occurrence order/grouping retained for scores; independent nDCG sums use math.fsum. Ranking order must match exactly.",
                    "result_manifest_sha256": identity(results / "manifest.json")["sha256"],
                    "acquisition_sha256": identity(args.acquisition)["sha256"], "build_receipt_sha256": identity(args.build_receipt)["sha256"]}
        write_json(artifacts / "audit-protocol.json", protocol)
        evidence.update({key: protocol[key] for key in ("result_manifest_sha256", "acquisition_sha256", "build_receipt_sha256")})
        with deadline(600):
            paths = {role: resolve(path) for role, path in acquisition["inputs"].items()}
            need(set(paths) == {row["role"] for row in plan["inputs"]}, "input role map differs")
            actual_identities = {}
            for item in plan["inputs"]:
                actual = identity(paths[item["role"]])
                need(actual["bytes"] == item["expected_bytes"] and actual[item["identity_algorithm"]] == item["expected_digest"], "raw input differs: " + item["role"])
                actual_identities[item["role"]] = actual
            evidence["raw_input_identities"] = actual_identities
            for name, expected in completed["outputs"].items():
                need(Path(name).name == name and identity(results / name) == {key: expected[key] for key in ("bytes", "sha256", "git-blob-sha1")}, "saved output identity differs: " + name)
            corpus, query_rows = read_canonical(paths, build, acquisition, plan)
            qrels = read_binary_qrels(paths["test_qrels"])
            queries = {qid: text for qid, (_, text) in query_rows.items()}
            all_qids = sorted(qrels)
            need(set(all_qids) <= set(queries) and all(doc in corpus for grades in qrels.values() for doc in grades), "canonical query/document coverage differs")
            qids = [qid for qid in all_qids if any(qrels[qid].values())]
            excluded = [qid for qid in all_qids if qid not in qids]
            need(qids and qids == completed["qids"] and excluded == completed["excluded_zero_idcg_qids"], "frozen cohort differs")
            sources = {"P": read_cache(paths["candidate_pool"], corpus, queries, all_qids),
                       "S": read_cache(paths["added_source"], corpus, queries, all_qids)}
            validation = read_json(results / "validation.json")
            compare_tree({name: {qid: len(rows[qid]) for qid in all_qids} for name, rows in sources.items()}, validation["source_depths"], "source depths")
            runs, stats, union = reconstruct(qids, corpus, queries, sources)
            need(len(corpus) == validation["corpus_documents"] and len(query_rows) == validation["query_text_records"]
                 and len(union) == validation["P_candidate_union"], "canonical/pooled counts differ")
            compare_tree({key: stats[key] for key in ("N", "avg_dl", "total_terms")}, validation["collection_statistics"], "pooled statistics")
            stats_sha = hashlib.sha256(json.dumps(stats, sort_keys=True, allow_nan=False).encode()).hexdigest()
            need(stats_sha == validation["collection_statistics_sha256"], "complete pooled term statistics differ")
            evidence["ranking_checks"] = {name: compare_rankings(runs[name], read_trec(results / (name + ".trec"), name, qids), name) for name in NAMES + ARMS}
            compare_tree({name: {qid: len(runs[name][qid]) for qid in qids} for name in NAMES}, completed["lexical_depths"], "lexical depths")
            compare_tree({name: {qid: len(runs[name][qid]) for qid in qids} for name in ARMS}, completed["arm_depths"], "arm depths")
            rows, summary = numeric_results(qids, qrels, runs, len(union) / len(corpus))
            evidence["maximum_per_query_numeric_difference"] = compare_tree(rows, read_json(results / "per-query.json"), "per-query")
            saved_stream = {}
            with (results / "per-query.jsonl").open() as stream:
                for line in stream:
                    row = json.loads(line, object_pairs_hook=unique_object)
                    qid = row.pop("qid")
                    need(qid not in saved_stream, "duplicate per-query JSONL key")
                    saved_stream[qid] = row
            compare_tree(rows, saved_stream, "per-query stream")
            original_summary = read_json(results / "summary.json")
            need(set(original_summary) == set(summary) | {"metric", "inference"}, "summary keys differ")
            evidence["maximum_summary_numeric_difference"] = compare_tree(summary, {key: original_summary[key] for key in summary}, "summary")
            write_json(artifacts / "reconstructed-per-query.json", rows)
            write_json(artifacts / "reconstructed-summary.json", summary)
            evidence.update(query_count=len(qids), query_vector=qids, excluded_zero_idcg_qids=excluded,
                            pooled_document_count=len(union), corpus_documents=len(corpus),
                            collection_statistics_sha256=stats_sha, reconstructed_summary=summary,
                            reconstruction_elapsed_seconds=time.monotonic() - started)
        evidence["official_checks"] = official_check(binary, qids, qrels, runs, rows, summary, artifacts)
        evidence["status"] = "passed"
    except BaseException as error:
        evidence.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        evidence["elapsed_seconds"] = time.monotonic() - started
        evidence["artifacts"] = {path.name: identity(path) for path in sorted(artifacts.iterdir()) if path.is_file()}
        output.parent.mkdir(parents=True, exist_ok=True)
        write_json(output, evidence)
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", required=True, type=Path)
    parser.add_argument("--build-receipt", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--metric-gate", required=True, type=Path)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(args)
    except (Exception, KeyboardInterrupt) as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__, "error": str(error)}))
        return 1
    print(json.dumps({"status": result["status"], "query_count": result["query_count"], "receipt": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
