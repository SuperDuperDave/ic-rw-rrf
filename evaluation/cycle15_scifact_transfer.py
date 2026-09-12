#!/usr/bin/env python3
"""Frozen SciFact transfer: strict input gate, then one five-arm comparison.

Raw source text stays local. JSONL caches are consumed one query at a time;
retained candidate text references the canonical corpus's single joined string.
Only Parquet decoding needs the separately acquired, pinned PyArrow wheel.
No acquisition, retrieval, tuning, alternate input format, or retry occurs here.

CLI inputs are the passed acquisition receipt (or a JSON object mapping the five
input-plan roles to local paths).
Validation and run outputs must be fresh directories. A run requires the passed
authoritative synthetic metric-gate receipt and repeats the complete input gate.
"""

import argparse
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import importlib
import json
import math
from pathlib import Path
import platform
import signal
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import generate_diverse_runs as lexical
from evaluation.fusion_contract import canonical_rrf
from evaluation.trec_eval_harness import ndcg_at_k

ROOT = Path(__file__).resolve().parents[1]
PLAN = "_sessions/evidence/2026-09-11-cycle14-input-plan.json"
PROTOCOL = "_sessions/cycles/2026-09-11-cycle14-transfer-protocol.md"
FROZEN_SHA256 = {
    PLAN: "051aed306d99e3431aa0cf60f17b7acdf1341becc20d37259c283155c134d18a",
    PROTOCOL: "1ed94aea29e5a662f2a37f20047201c3dd4e7e3dd5f886038332ba5722342d5a",
    "evaluation/generate_diverse_runs.py": "0702155886c270c507b5c4a3f21e1145782ba25d8b4fd430fc10dac7ef0233f8",
    "evaluation/fusion_contract.py": "72dd915f052c84dc79d1e6a604778a925e38be398dabcbd66c5e5ef63e1fc38f",
    "evaluation/trec_eval_harness.py": "0b437034007e0e6ccfd8979c3eee6603374afb2234b895bccc47546347c9b85b",
}
EVALUATOR_REVISION = "ba38899cbd4de0fb699b47f39b64ef1c107e4a5c"
ROLES = ("candidate_pool", "added_source", "corpus", "query_texts", "test_qrels")
LEXICAL_NAMES = ("bm25", "bm25_tuned", "tfidf", "ql_dirichlet")
ARMS = ("P", "S", "A", "B", "H")
CONTRASTS = ("B-A", "B-S", "B-P", "A-P", "B-H")


class ContractError(ValueError):
    """A gate failed; stop without selecting another input or method."""


def file_identity(path):
    """Compute both raw SHA256 and Git blob identity without retaining bytes."""
    path = Path(path)
    size = path.stat().st_size
    sha256 = hashlib.sha256()
    blob = hashlib.sha1(("blob " + str(size) + "\0").encode("ascii"))
    consumed = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            sha256.update(chunk)
            blob.update(chunk)
            consumed += len(chunk)
    if consumed != size or path.stat().st_size != size:
        raise ContractError("input size changed while hashing: " + str(path))
    return {"bytes": size, "sha256": sha256.hexdigest(), "git-blob-sha1": blob.hexdigest()}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON field: " + key)
        result[key] = value
    return result


def read_json(path):
    with Path(path).open(encoding="utf-8") as source:
        return json.load(source, object_pairs_hook=_object)


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as destination:
        json.dump(value, destination, indent=2, sort_keys=True, allow_nan=False)
        destination.write("\n")


def _keys(value, required, optional=(), location="record"):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ContractError(location + ": unsupported schema")


def _id(value, location):
    # Numeric IDs stay strings; whitespace cannot be losslessly exported to TREC.
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        raise ContractError(location + ": ID must be a nonempty whitespace-free string")
    return value


def verify_frozen_code():
    for relative, expected in FROZEN_SHA256.items():
        if file_identity(ROOT / relative)["sha256"] != expected:
            raise ContractError("frozen code/protocol identity mismatch: " + relative)
    return dict(FROZEN_SHA256, **{"evaluation/cycle15_scifact_transfer.py": file_identity(__file__)["sha256"]})


def verify_inputs(inputs, plan):
    if set(inputs) != set(ROLES):
        raise ContractError("input paths must supply exactly the five frozen roles")
    if len({str(Path(path).resolve()) for path in inputs.values()}) != len(ROLES):
        raise ContractError("input roles must have distinct paths")
    expected_by_role = {row["role"]: row for row in plan["inputs"]}
    if sum(Path(path).stat().st_size for path in inputs.values()) > plan["raw_input_byte_cap"]:
        raise ContractError("raw input byte cap exceeded")
    identities = {}
    for role in ROLES:
        expected = expected_by_role[role]
        actual = file_identity(inputs[role])
        if actual["bytes"] != expected["expected_bytes"] or actual[expected["identity_algorithm"]] != expected["expected_digest"]:
            raise ContractError("input identity mismatch: " + role)
        identities[role] = dict(actual, source_revision=expected["revision"], source_path=expected["path"])
    return identities


@contextmanager
def pinned_decoder(decoder_path, plan, decoder_wheel=None):
    """Use the pinned extracted wheel only; never install or fetch a dependency."""
    if sys.version_info[:2] != (3, 12) or platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ContractError("pinned decoder requires CPython3.12 Linux x86_64")
    if decoder_path is None:
        raise ContractError("provide the isolated extracted pinned decoder directory")
    directory = Path(decoder_path).resolve()
    # The coordinator verifies/extracts the wheel. Require the wheel alongside
    # its extraction directory so this reader independently rechecks its bytes.
    decoder = plan["optional_parquet_decoder"]
    wheel = Path(decoder_wheel) if decoder_wheel is not None else directory.parent / decoder["filename"]
    identity = file_identity(wheel)
    if identity["bytes"] != decoder["expected_bytes"] or identity["sha256"] != decoder["expected_sha256"]:
        raise ContractError("pinned decoder wheel identity mismatch")
    if "pyarrow" in sys.modules:
        raise ContractError("decoder isolation requires a fresh process without pyarrow imported")
    # Verify extraction contents against the actual wheel, rather than trust an
    # independently changed extracted package with matching version metadata.
    import zipfile
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = directory / member.filename
            if not target.resolve().is_relative_to(directory) or not target.is_file():
                raise ContractError("pinned decoder extraction missing/unsafe member")
            with archive.open(member) as packed, target.open("rb") as unpacked:
                while True:
                    chunk = packed.read(1024 * 1024)
                    if unpacked.read(len(chunk) or 1) != chunk:
                        raise ContractError("pinned decoder extraction bytes mismatch")
                    if not chunk:
                        break
    sys.path.insert(0, str(directory))
    try:
        arrow = importlib.import_module("pyarrow")
        parquet = importlib.import_module("pyarrow.parquet")
        if arrow.__version__ != decoder["version"] or not Path(arrow.__file__).resolve().is_relative_to(directory):
            raise ContractError("wrong parquet decoder version/origin")
        yield arrow, parquet, {"version": arrow.__version__, "wheel": decoder["filename"], **identity}
    finally:
        sys.path.remove(str(directory))


def parquet_texts(path, arrow, parquet, role):
    reader = parquet.ParquetFile(path)
    schema = reader.schema_arrow
    if set(schema.names) != {"_id", "title", "text"} or len(schema.names) != 3 or any(field.type != arrow.string() for field in schema):
        raise ContractError(role + ": unsupported Parquet schema (expected three string fields)")
    result = {}
    for batch in reader.iter_batches(batch_size=256):
        for row in batch.to_pylist():
            identifier = _id(row["_id"], role)
            if identifier in result or not isinstance(row["title"], str) or not isinstance(row["text"], str):
                raise ContractError(role + ": duplicate ID or non-string text")
            result[identifier] = (row["title"], row["text"])
    if not result:
        raise ContractError(role + ": empty text source")
    return result


def read_binary_qrels(path):
    result = {}
    with Path(path).open(encoding="utf-8", newline="") as source:
        if source.readline().rstrip("\r\n") != "query-id\tcorpus-id\tscore":
            raise ContractError("qrels: unsupported TSV header")
        for number, line in enumerate(source, 2):
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) != 3 or parts[2] not in ("0", "1"):
                raise ContractError("qrels line %d: expected IDs and integer binary grade" % number)
            qid, docid = _id(parts[0], "qrels query"), _id(parts[1], "qrels document")
            grades = result.setdefault(qid, {})
            if docid in grades:
                raise ContractError("qrels: duplicate query/document pair")
            grades[docid] = int(parts[2])
    if not result:
        raise ContractError("qrels: no judgments")
    return result


def read_cache(path, corpus, queries, all_qids):
    """Pinned raw schema; array order declares one-based ranks, no re-sorting."""
    result = {}
    canonical_ids = {identifier: identifier for identifier in corpus}
    with Path(path).open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            location = "cache line %d" % number
            try:
                record = json.loads(line, object_pairs_hook=_object)
            except (json.JSONDecodeError, UnicodeError) as error:
                raise ContractError(location + ": malformed JSON") from error
            _keys(record, ("query", "candidates"), ("invocations_history",), location)
            if "invocations_history" in record and not isinstance(record["invocations_history"], list):
                raise ContractError(location + ": invocations_history must be a list")
            query = record["query"]
            _keys(query, ("qid", "text"), location=location + " query")
            qid = _id(query["qid"], location + " query")
            if qid in result or qid not in all_qids:
                raise ContractError(location + ": duplicate or non-test query record")
            if not isinstance(query["text"], str) or query["text"] != queries[qid]:
                raise ContractError(location + ": query text mismatch")
            candidates = record["candidates"]
            if not isinstance(candidates, list) or len(candidates) > 1000:
                raise ContractError(location + ": expected candidate array of depth <=1000")
            ranking, seen, previous = [], set(), math.inf
            for candidate in candidates:
                _keys(candidate, ("docid", "score", "doc"), location=location + " candidate")
                docid = _id(candidate["docid"], location + " candidate")
                if docid in seen or docid not in corpus:
                    raise ContractError(location + ": duplicate or unknown document ID")
                doc = candidate["doc"]
                _keys(doc, ("_id", "title", "text"), ("metadata",), location + " doc")
                if "metadata" in doc and not isinstance(doc["metadata"], dict):
                    raise ContractError(location + ": doc.metadata must be an object")
                if doc["_id"] != docid or not isinstance(doc["_id"], str):
                    raise ContractError(location + ": candidate/doc._id mismatch")
                if not isinstance(doc["title"], str) or not isinstance(doc["text"], str) or (doc["title"], doc["text"]) != corpus[docid]:
                    raise ContractError(location + ": corpus/cache text mismatch")
                score = candidate["score"]
                if type(score) not in (int, float):
                    raise ContractError(location + ": source score must be numeric")
                try:
                    score = float(score)
                except OverflowError as error:
                    raise ContractError(location + ": nonfinite source score") from error
                if not math.isfinite(score) or score > previous:
                    raise ContractError(location + ": scores must be finite and nonincreasing")
                ranking.append((canonical_ids[docid], score))
                seen.add(docid)
                previous = score
            result[qid] = tuple(ranking)
    if set(result) != set(all_qids):
        raise ContractError("cache test-query coverage mismatch; missing=" + repr(sorted(set(all_qids) - set(result))))
    return result


@dataclass
class ValidatedInputs:
    qids: tuple
    qrels: dict
    queries: dict
    data: dict
    sources: dict
    stats: dict
    manifest: dict


def validate_components(corpus, query_rows, qrels, candidate_path, added_path):
    """Body validation shared with synthetic tests; no effectiveness calculation."""
    all_qids = tuple(sorted(qrels))
    if not all_qids or not corpus:
        raise ContractError("empty corpus or official query vector")
    queries = {qid: row[1] for qid, row in query_rows.items()}
    for qid, grades in qrels.items():
        if qid not in queries:
            raise ContractError("official query missing from query text source: " + qid)
        if not grades or any(type(grade) is not int or grade not in (0, 1) for grade in grades.values()):
            raise ContractError("entire qrel domain must contain integer binary grades")
        if any(docid not in corpus for docid in grades):
            raise ContractError("qrel document missing from corpus: " + qid)
    qids = tuple(qid for qid in all_qids if any(qrels[qid].values()))
    excluded = tuple(qid for qid in all_qids if qid not in qids)
    if not qids:
        raise ContractError("official cohort has no positive-IDCG queries")
    for qid in qids:
        if not lexical.tokenize(queries[qid]):
            raise ContractError("tokenized-empty query requires contract revision: " + qid)
    # Both complete caches must validate before even pooled statistics are built.
    sources = {
        "P": read_cache(candidate_path, corpus, queries, all_qids),
        "S": read_cache(added_path, corpus, queries, all_qids),
    }
    joined = {docid: title + "\n" + body for docid, (title, body) in corpus.items()}
    data = {qid: [(docid, joined[docid]) for docid, _ in sources["P"][qid]] for qid in qids}
    stats = lexical.build_collection_stats(data)
    union = {docid for rows in data.values() for docid, _ in rows}
    if stats["N"] != len(union) or stats["total_terms"] != sum(stats["cf"].values()) or not math.isfinite(stats["avg_dl"]):
        raise ContractError("invalid pooled corpus statistics")
    manifest = {
        "status": "validated_before_effectiveness", "official_test_qids": list(all_qids),
        "qids": list(qids), "excluded_zero_idcg_qids": list(excluded),
        "n_queries": len(qids), "grade_domain": sorted({grade for row in qrels.values() for grade in row.values()}),
        "corpus_documents": len(corpus), "query_text_records": len(queries),
        "source_depths": {name: {qid: len(rows[qid]) for qid in all_qids} for name, rows in sources.items()},
        "P_candidate_union": len(union), "P_candidate_union_over_corpus": len(union) / len(corpus),
        "collection_statistics": {key: stats[key] for key in ("N", "avg_dl", "total_terms")},
        "collection_statistics_sha256": hashlib.sha256(json.dumps(stats, sort_keys=True, allow_nan=False).encode()).hexdigest(),
        "source_order": "supplied arrays; one-based implicit ranks; finite nonincreasing scores; exact ties retained",
        "lexical_order": "unchanged generate_lexical_run stable descending raw scores; P order on exact ties",
        "text_construction": "candidate.doc.title + newline + candidate.doc.text; exact pinned corpus identity",
        "schema": {"cache": "query(qid,text), candidates(docid,score,doc(_id,title,text[,metadata]))[,invocations_history]",
                   "parquet": "_id,title,text strings", "qrels": "query-id,corpus-id,score TSV; integer binary"},
    }
    return ValidatedInputs(qids, qrels, queries, data, sources, stats, manifest)


def load_validate(inputs, decoder_path=None, acquisition_manifest=None, decoder_wheel=None):
    """Validate identities of all five inputs, then both complete cache bodies."""
    started = time.monotonic()
    code_hashes = verify_frozen_code()
    plan = read_json(ROOT / PLAN)
    if "inputs" in inputs:
        if inputs.get("status") != "passed" or inputs.get("input_plan_sha256") != FROZEN_SHA256[PLAN]:
            raise ContractError("acquisition receipt incomplete or input-plan identity differs")
        inputs = inputs["inputs"]
    identities = verify_inputs(inputs, plan)
    with pinned_decoder(decoder_path, plan, decoder_wheel) as (arrow, parquet, decoder_identity):
        corpus = parquet_texts(inputs["corpus"], arrow, parquet, "corpus")
        queries = parquet_texts(inputs["query_texts"], arrow, parquet, "query_texts")
    qrels = read_binary_qrels(inputs["test_qrels"])
    validated = validate_components(corpus, queries, qrels, inputs["candidate_pool"], inputs["added_source"])
    validated.manifest.update(input_identities=identities, code_sha256=code_hashes,
                              decoder=decoder_identity, validation_elapsed_seconds=time.monotonic() - started)
    if acquisition_manifest is not None:
        validated.manifest["acquisition_receipt_sha256"] = file_identity(acquisition_manifest)["sha256"]
    return validated


def lexical_rankings(validated):
    """Keep original generator order while capturing pre-serialization scores."""
    runs = {name: {} for name in LEXICAL_NAMES}
    for name in LEXICAL_NAMES:
        scorer = lexical.LEXICAL_RANKERS[name]
        for qid in validated.qids:
            captured = []

            def capture(query_tokens, doc_tokens, stats):
                score = scorer(query_tokens, doc_tokens, stats)
                if not math.isfinite(score):
                    raise ContractError("nonfinite lexical score: " + name + "/" + qid)
                captured.append(score)
                return score

            candidates = validated.data[qid]
            lines = lexical.generate_lexical_run({qid: candidates}, validated.queries,
                                                validated.stats, capture, name, top_k=200)
            if len(captured) != len(candidates):
                raise ContractError("lexical scorer call count differs from P depth")
            raw = {docid: score for (docid, _), score in zip(candidates, captured)}
            ranking = []
            for rank, line in enumerate(lines):
                parts = line.split()
                if len(parts) != 6 or parts[0] != qid or parts[1] != "Q0" or parts[3] != str(rank) or parts[5] != name or parts[2] not in raw:
                    raise ContractError("unexpected original lexical generator output")
                ranking.append((parts[2], raw[parts[2]]))
            expected = sorted(zip((docid for docid, _ in candidates), captured), key=lambda row: row[1], reverse=True)[:200]
            if ranking != expected:
                raise ContractError("lexical output changed raw-score stable order or depth")
            runs[name][qid] = ranking
    return runs


def fused_scores(lists):
    ranking = canonical_rrf(lists, k=60)
    contributions = defaultdict(list)
    for source in lists:
        for rank, docid in enumerate(source, 1):
            contributions[docid].append(1.0 / (60.0 + rank))
    return [(docid, math.fsum(contributions[docid])) for docid in ranking]


def rbp10(ranking, qrels):
    p = 4 / 5
    return math.fsum((1 - p) * p ** (rank - 1) * qrels.get(docid, 0)
                     for rank, docid in enumerate(ranking[:10], 1))


def paired_summary(values):
    return {"mean_delta": math.fsum(values) / len(values), "n_queries": len(values),
            "positive": sum(value > 0 for value in values), "zero": sum(value == 0 for value in values),
            "negative": sum(value < 0 for value in values), "minimum": min(values), "maximum": max(values)}


def analyze(validated, arms, on_query=None):
    rows = {}
    for qid in validated.qids:
        grades = validated.qrels[qid]
        rankings = {name: [docid for docid, _ in arms[name][qid]] for name in ARMS}
        metrics = {name: ndcg_at_k(rankings[name], grades, 10) for name in ARMS}
        rbp = {name: rbp10(rankings[name], grades) for name in ("A", "B")}
        pool = {docid for docid, _ in validated.sources["P"][qid]}
        deltas = {name: metrics[name[0]] - metrics[name[2]] for name in CONTRASTS}
        rows[qid] = {
            "ndcg10": metrics, "ndcg10_deltas": deltas,
            "ndcg10_delta_signs": {name: (value > 0) - (value < 0) for name, value in deltas.items()},
            "rbp10_p_4_5": rbp, "rbp10_B-A": rbp["B"] - rbp["A"],
            "candidate_count": len(pool), "source_candidate_counts": {name: len(validated.sources[name][qid]) for name in ("P", "S")},
            "arm_depths": {name: len(rankings[name]) for name in ARMS},
            "B_top10_outside_P": {"count": sum(docid not in pool for docid in rankings["B"][:10]), "returned_top10": len(rankings["B"][:10])},
            "top10_without_explicit_qrel": {name: {"count": sum(docid not in grades for docid in rankings[name][:10]), "returned_top10": len(rankings[name][:10])} for name in ARMS},
        }
        if on_query is not None:
            on_query(qid, rows[qid])
    n = len(validated.qids)
    summary = {
        "n_queries": n, "qids": list(validated.qids), "primary": "B-A", "metric": "binary nDCG@10; absent qrels zero; complete qrels IDCG",
        "means_ndcg10": {name: math.fsum(rows[qid]["ndcg10"][name] for qid in validated.qids) / n for name in ARMS},
        "contrasts_ndcg10": {name: paired_summary([rows[qid]["ndcg10_deltas"][name] for qid in validated.qids]) for name in CONTRASTS},
        "means_rbp10_p_4_5": {name: math.fsum(rows[qid]["rbp10_p_4_5"][name] for qid in validated.qids) / n for name in ("A", "B")},
        "contrast_rbp10_B-A": paired_summary([rows[qid]["rbp10_B-A"] for qid in validated.qids]),
        "P_candidate_union_over_corpus": validated.manifest["P_candidate_union_over_corpus"],
        "judgedness_totals": {name: {key: sum(rows[qid]["top10_without_explicit_qrel"][name][key] for qid in validated.qids) for key in ("count", "returned_top10")} for name in ARMS},
        "B_top10_outside_P_totals": {key: sum(rows[qid]["B_top10_outside_P"][key] for qid in validated.qids) for key in ("count", "returned_top10")},
        "inference": "fixed finite panel; no p-values, confidence intervals, or population-significance claim",
    }
    return rows, summary


def require_metric_gate(path):
    receipt = read_json(path)
    if receipt.get("status") != "passed" or receipt.get("evaluator_revision") != EVALUATOR_REVISION or receipt.get("local_metric_sha256") != FROZEN_SHA256["evaluation/trec_eval_harness.py"]:
        raise ContractError("authoritative synthetic metric gate missing or incompatible")
    if receipt.get("tolerance") != {"official_absolute": 0.0000500001, "local_absolute": 1e-12, "relative": 0.0}:
        raise ContractError("authoritative synthetic metric gate tolerance differs")
    return {"sha256": file_identity(path)["sha256"], "evaluator_revision": receipt["evaluator_revision"], "tolerance": receipt["tolerance"]}


def require_preflight(path):
    if path is None:
        raise ContractError("run requires the passed pre-acquisition source preflight")
    receipt = read_json(path)
    hashes = receipt.get("source_sha256")
    required = set(FROZEN_SHA256) | {"evaluation/cycle15_scifact_transfer.py", "evaluation/tests/test_cycle15_scifact_transfer.py"}
    if receipt.get("status") != "passed" or not isinstance(hashes, dict) or not required <= set(hashes):
        raise ContractError("source preflight missing required source identities")
    for relative, expected in hashes.items():
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT) or not isinstance(expected, str) or file_identity(source)["sha256"] != expected:
            raise ContractError("source preflight identity mismatch: " + str(relative))
    return {"sha256": file_identity(path)["sha256"], "source_sha256": hashes}


@contextmanager
def scoring_deadline(seconds=600):
    if not hasattr(signal, "setitimer") or signal.getitimer(signal.ITIMER_REAL)[0] != 0:
        raise ContractError("cannot establish exclusive scoring wall timer")

    def expired(signum, frame):
        raise ContractError("frozen local scoring wall cap exceeded")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def execute(validated, output_dir, metric_gate_receipt, preflight=None):
    """One frozen comparison. Preserve failed/partial outputs; never overwrite."""
    gate = require_metric_gate(metric_gate_receipt)
    source_gate = require_preflight(preflight)
    verify_frozen_code()
    if validated.manifest.get("status") != "validated_before_effectiveness":
        raise ContractError("complete input validation is required before scoring")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(validated.manifest, status="scoring_started", metric_gate=gate,
                    source_preflight=source_gate, command=sys.argv, scoring_wall_cap_seconds=600,
                    phase="lexical_scoring", effectiveness_started=False, effectiveness_completed=False)
    write_json(output / "validation.json", validated.manifest)
    write_json(output / "execution-start.json", manifest)
    started = time.monotonic()
    try:
        with scoring_deadline():
            runs = lexical_rankings(validated)
            arms = {name: {qid: list(validated.sources[name][qid]) for qid in validated.qids} for name in ("P", "S")}
            arms.update({name: {} for name in ("A", "B", "H")})
            manifest["phase"] = "fusion"
            for qid in validated.qids:
                lists = [[docid for docid, _ in runs[name][qid]] for name in LEXICAL_NAMES]
                primitive, sparse = ([docid for docid, _ in arms[name][qid]] for name in ("P", "S"))
                arms["A"][qid] = fused_scores(lists)
                arms["B"][qid] = fused_scores(lists + [sparse])
                arms["H"][qid] = fused_scores([primitive, sparse])
            manifest["phase"] = "numeric_ranking_output"
            for name, run in {**runs, **arms}.items():
                with (output / (name + ".trec")).open("x", encoding="utf-8") as destination:
                    for qid in validated.qids:
                        for rank, (docid, score) in enumerate(run[qid], 1):
                            destination.write("%s Q0 %s %d %s %s\n" % (qid, docid, rank, repr(score), name))
            manifest.update(phase="effectiveness", effectiveness_started=True)
            write_json(output / "effectiveness-start.json", manifest)
            with (output / "per-query.jsonl").open("x", encoding="utf-8") as stream:

                def preserve_query(qid, row):
                    stream.write(json.dumps({"qid": qid, **row}, sort_keys=True, allow_nan=False) + "\n")
                    stream.flush()

                rows, summary = analyze(validated, arms, on_query=preserve_query)
            manifest.update(phase="effectiveness_output", effectiveness_completed=True)
            write_json(output / "per-query.json", rows)
            write_json(output / "summary.json", summary)
        manifest.update(status="completed", phase="completed", scoring_elapsed_seconds=time.monotonic() - started,
                        lexical_depths={name: {qid: len(run[qid]) for qid in validated.qids} for name, run in runs.items()},
                        arm_depths={name: {qid: len(run[qid]) for qid in validated.qids} for name, run in arms.items()})
        manifest["outputs"] = {path.name: file_identity(path) for path in sorted(output.iterdir())}
        write_json(output / "manifest.json", manifest)
        return summary
    except BaseException as error:
        manifest.update(status="failed_preserve_partial_outputs", failure_type=type(error).__name__,
                        failure=str(error), scoring_elapsed_seconds=time.monotonic() - started)
        write_json(output / "failure.json", manifest)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("validate", "run"))
    parser.add_argument("--inputs", required=True, type=Path, help="JSON mapping frozen roles to local paths")
    parser.add_argument("--decoder-path", required=True, type=Path, help="extracted wheel directory; pinned wheel must be alongside")
    parser.add_argument("--decoder-wheel", type=Path, help="explicit path to the retained pinned decoder wheel")
    parser.add_argument("--acquisition-manifest", type=Path)
    parser.add_argument("--metric-gate", type=Path)
    parser.add_argument("--preflight", type=Path, help="passed source-hash preflight; required for run")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a fresh directory")
    if args.mode == "run" and (args.metric_gate is None or args.preflight is None):
        parser.error("run requires --metric-gate and --preflight")
    try:
        if args.mode == "run":
            require_metric_gate(args.metric_gate)
            require_preflight(args.preflight)
        config = read_json(args.inputs)
        acquisition_manifest = args.acquisition_manifest or (args.inputs if "inputs" in config else None)
        validated = load_validate(config, args.decoder_path, acquisition_manifest, args.decoder_wheel)
        if args.mode == "validate":
            args.output.mkdir(parents=True, exist_ok=False)
            write_json(args.output / "validation.json", dict(validated.manifest, command=sys.argv))
            print(json.dumps({"status": "validated_before_effectiveness", "n_queries": len(validated.qids)}))
        else:
            summary = execute(validated, args.output, args.metric_gate, args.preflight)
            print(json.dumps({"status": "completed", "n_queries": len(validated.qids), "primary_B-A": summary["contrasts_ndcg10"]["B-A"]}))
    except (ValueError, OSError, ImportError) as error:
        # Input-gate failures are evidence too; never include raw source lines.
        if not args.output.exists():
            args.output.mkdir(parents=True, exist_ok=False)
            write_json(args.output / "failure.json", {"status": "gate_failed_before_scoring", "type": type(error).__name__, "failure": str(error), "command": sys.argv})
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
