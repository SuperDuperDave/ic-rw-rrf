#!/usr/bin/env python3
"""Independently verify cycle02 conversion and core membership observations.

Uses only the standard library; imports neither acquisition nor observation code.
Query/passage text is never printed or written. Qrel grades are never interpreted.
Run from any cwd with --receipt PATH to write a fresh receipt, or --check-only.
The raw source cache is required for this independent conversion check.
"""

import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OBS = "results/cycle02-2026-09-10/observations"
LEXICAL = ("bm25", "bm25_tuned", "tfidf", "ql_dirichlet")
GROUPS = ("tail_supported", "isolated")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_json(relative):
    return json.loads((ROOT / relative).read_bytes())


def inventory(documents, judged):
    n, j = len(documents), len(documents & judged)
    return {"n_candidates": n, "n_judged": j, "n_unjudged": n - j,
            "judged_fraction": j / n if n else None}


def check_conversion(selection, manifest):
    reports = {}
    for item in selection["files"]:
        year = item["year"]
        derived = next(run for run in manifest["derived_runs"] if run["year"] == year)
        original = next(raw for raw in manifest["original_inputs"] if raw["year"] == year)
        raw = ROOT / "_sessions/local/cycle02/source-cache" / (item["expected_sha256"] + "-" + item["filename"])
        run = ROOT / derived["path"]
        require(raw.stat().st_size == item["expected_bytes"] == original["bytes"], "Raw byte count mismatch")
        require(digest(raw) == item["expected_sha256"] == original["sha256"], "Raw SHA256 mismatch")
        require(original["url"] == item["url"] and original["filename"] == item["filename"], "Original provenance mismatch")
        require(run.stat().st_size == derived["bytes"] and digest(run) == derived["sha256"], "Derived artifact mismatch")
        query_ids, depths = set(), []
        n_rows = n_ties = queries_with_ties = 0
        reconstruction = hashlib.sha256()
        with raw.open("rb") as input_stream, run.open("r", encoding="utf-8") as output_stream:
            for raw_line in input_stream:
                record = json.loads(raw_line)
                qid = str(record["query"]["qid"])
                require(qid not in query_ids, "Duplicate raw query ID")
                query_ids.add(qid)
                docs, scores = [], []
                for rank, candidate in enumerate(record["candidates"], 1):
                    docid, score = str(candidate["docid"]), candidate["score"]
                    require(type(score) in (int, float) and math.isfinite(score), "Invalid raw numeric score")
                    require(not any(c.isspace() or not c.isprintable() for c in qid + docid)
                            and bool(qid) and bool(docid), "Invalid raw ID")
                    columns = output_stream.readline().split()
                    require(len(columns) == 6, "Derived TREC row missing or malformed")
                    require(columns[:3] == [qid, "Q0", docid]
                            and int(columns[3]) == rank
                            and Decimal(columns[4]) == Decimal(str(score))
                            and columns[5] == selection["source_id"], "Numeric TREC tuple differs from raw array")
                    reconstruction.update(f"{qid} Q0 {docid} {rank} {str(score)} {selection['source_id']}\n".encode())
                    docs.append(docid)
                    scores.append(score)
                    n_rows += 1
                require(len(docs) == len(set(docs)) and bool(docs), "Duplicate or missing raw candidates")
                require(all(a >= b for a, b in zip(scores, scores[1:])), "Raw scores ascend")
                query_ties = sum(a == b for a, b in zip(scores, scores[1:]))
                n_ties += query_ties
                queries_with_ties += bool(query_ties)
                depths.append(len(docs))
            require(output_stream.readline() == "", "Derived TREC contains extra rows")
        observed = {"query_count": len(query_ids), "row_count": n_rows,
                    "depth_min": min(depths), "depth_max": max(depths),
                    "adjacent_score_ties": n_ties, "queries_with_score_ties": queries_with_ties}
        require(all(derived[key] == value for key, value in observed.items()), "Conversion inventory mismatch")
        require(reconstruction.hexdigest() == derived["sha256"], "Reconstructed TREC bytes differ")
        require(derived["rank_origin"] == 1 and derived["tie_policy"] == "preserve candidate array order", "Rank contract mismatch")
        reports[str(year)] = {**observed, "all_numeric_tuples_and_serialized_bytes_match": True,
                              "raw_sha256": original["sha256"], "raw_bytes": original["bytes"],
                              "derived_sha256": derived["sha256"], "derived_bytes": derived["bytes"]}
    return reports


def read_run(path, origin):
    runs, scores = defaultdict(list), defaultdict(list)
    with path.open() as stream:
        for line in stream:
            qid, unused, docid, rank, score, tag = line.split()
            require(int(rank) == len(runs[qid]) + origin, "Input rank sequence mismatch")
            runs[qid].append(docid)
            scores[qid].append(Decimal(score))
    for qid, documents in runs.items():
        require(len(documents) == len(set(documents)), "Duplicate input document")
        require(all(a >= b for a, b in zip(scores[qid], scores[qid][1:])), "Input scores ascend")
    return dict(runs)


def owner_summary(qids, cohorts, judgments):
    per_query = {qid: {group: inventory(cohorts[qid][group], judgments[qid])
                       for group in GROUPS} for qid in qids}
    groups = {}
    for group in GROUPS:
        n = sum(per_query[qid][group]["n_candidates"] for qid in qids)
        j = sum(per_query[qid][group]["n_judged"] for qid in qids)
        groups[group] = {"n_candidates": n, "n_judged": j, "n_unjudged": n - j,
                         "judged_fraction": j / n if n else None,
                         "n_queries_with_candidates": sum(bool(cohorts[qid][group]) for qid in qids),
                         "n_queries_with_judgments": sum(bool(cohorts[qid][group] & judgments[qid]) for qid in qids)}
    eligibility_sets = {
        "with_candidates": [q for q in qids if any(cohorts[q][g] for g in GROUPS)],
        "with_both_groups": [q for q in qids if all(cohorts[q][g] for g in GROUPS)],
        "with_judged_both_groups": [q for q in qids if all(cohorts[q][g] & judgments[q] for g in GROUPS)]}
    return {"groups": groups, "eligibility": {key: {"n_queries": len(value), "qids": value}
                                              for key, value in eligibility_sets.items()},
            "n_queries_total": len(qids), "per_query_denominators": per_query}


def check_observations(selection, source_manifest, summary):
    reports = {}
    source = selection["source_id"]
    sources = (*LEXICAL, source)
    for year in (2019, 2020):
        published = summary["years"][str(year)]
        judged = defaultdict(set)
        with (ROOT / f"data/trec-dl-{year}/{year}qrels-pass.txt").open() as stream:
            for line in stream:
                columns = line.split()
                require(len(columns) == 4, "Invalid qrel row")
                judged[columns[0]].add(columns[2])  # Deliberately never parse the grade.
        new_path = next(r["path"] for r in source_manifest["derived_runs"] if r["year"] == year)
        runs = {name: read_run(ROOT / f"data/trec-dl-{year}/runs/{name}.txt", 0) for name in LEXICAL}
        runs[source] = read_run(ROOT / new_path, 1)
        qids = sorted(q for q in judged if all(runs[name].get(q) for name in sources))
        require(qids == published["eligible_qids"] and len(qids) == published["n_eligible_queries"], "Eligible query mismatch")
        require(len(judged) == published["n_qrel_queries"], "Qrel query count mismatch")
        fixed = {name: {q: {g: set() for g in GROUPS} for q in qids} for name in sources}
        for qid in qids:
            for owner in sources:
                others = [name for name in sources if name != owner]
                other_heads = set().union(*(set(runs[name][qid][:30]) for name in others))
                other_full = set().union(*(set(runs[name][qid]) for name in others))
                for docid in runs[owner][qid][:10]:
                    if docid not in other_heads:
                        fixed[owner][qid]["tail_supported" if docid in other_full else "isolated"].add(docid)
            lexical_union = set().union(*(set(runs[name][qid]) for name in LEXICAL))
            require(fixed[source][qid]["isolated"] == set(runs[source][qid][:10]) - lexical_union,
                    "Isolated new-source specialists differ from top10 outside lexical full union")
        depths = {q: min(200, *(len(runs[name][q]) for name in sources)) for q in qids}
        receipt_arms, visible_eligibility = {}, {}
        for arm in ("full", "shared_depth"):
            active = {name: {q: runs[name][q] if arm == "full" else runs[name][q][:depths[q]]
                             for q in qids} for name in sources}
            outside_n = outside_j = 0
            for q in qids:
                lexical_union = set().union(*(set(runs[name][q]) for name in LEXICAL))
                outside = set(active[source][q][:10]) - lexical_union
                outside_n += len(outside)
                outside_j += len(outside & judged[q])
            outside_counts = {"n_candidates": outside_n, "n_judged": outside_j,
                              "n_unjudged": outside_n - outside_j,
                              "judged_fraction": outside_j / outside_n if outside_n else None}
            require(outside_counts == published["arms"][arm]["new_source_top10_outside_lexical_full_union"], "Outside lexical union counts differ")
            compact_owners = {}
            for visibility in ("fixed_cohort", "visible_only"):
                owner_cohorts = {}
                for owner in sources:
                    owner_cohorts[owner] = {
                        q: {g: fixed[owner][q][g] if visibility == "fixed_cohort"
                            else fixed[owner][q][g] & set(active[owner][q]) for g in GROUPS} for q in qids}
                owner_cohorts["pooled_lexical"] = {
                    q: {g: set().union(*(owner_cohorts[name][q][g] for name in LEXICAL)) for g in GROUPS} for q in qids}
                expected_owners = published["arms"][arm]["owners"][visibility]
                compact_owners[visibility] = {}
                for owner, cohorts in owner_cohorts.items():
                    observed = owner_summary(qids, cohorts, judged)
                    expected = (expected_owners["new_source"] if owner == source else
                                expected_owners["pooled_lexical"] if owner == "pooled_lexical" else
                                expected_owners["individual_lexical"][owner])
                    require(observed == expected, f"Specialist denominator or eligibility mismatch: {year}/{arm}/{visibility}/{owner}")
                    compact_owners[visibility][owner] = {"groups": observed["groups"],
                        "eligibility_queries": {k: v["n_queries"] for k, v in observed["eligibility"].items()}}
                    if visibility == "visible_only":
                        visible_eligibility[(arm, owner)] = observed["eligibility"]
            receipt_arms[arm] = {"new_source_top10_outside_lexical_full_union": outside_counts,
                                 "owners": compact_owners}
        for owner in (*sources, "pooled_lexical"):
            expected = published["same_query_paired_observability_across_arms"]
            expected = (expected["new_source"] if owner == source else expected["pooled_lexical"]
                        if owner == "pooled_lexical" else expected["individual_lexical"][owner])
            for key, values in expected.items():
                common = sorted(set(visible_eligibility[("full", owner)][key]["qids"])
                                & set(visible_eligibility[("shared_depth", owner)][key]["qids"]))
                require(values == {"n_queries": len(common), "qids": common}, "Paired query eligibility mismatch")
        cohort_counts_unchanged = all(
            receipt_arms[arm]["owners"][visibility] == receipt_arms["full"]["owners"]["fixed_cohort"]
            for arm in ("full", "shared_depth") for visibility in ("fixed_cohort", "visible_only"))
        compact_counts = {owner: {"groups": {g: {"candidates": values["n_candidates"],
                                                  "judged": values["n_judged"]}
                                             for g, values in data["groups"].items()},
                                  "eligibility_queries": data["eligibility_queries"]}
                          for owner, data in receipt_arms["full"]["owners"]["fixed_cohort"].items()}
        differing_counts = {}
        for arm in ("full", "shared_depth"):
            for visibility in ("fixed_cohort", "visible_only"):
                for owner, data in receipt_arms[arm]["owners"][visibility].items():
                    if data != receipt_arms["full"]["owners"]["fixed_cohort"][owner]:
                        differing_counts[f"{arm}/{visibility}/{owner}"] = {
                            "groups": {g: {"candidates": v["n_candidates"], "judged": v["n_judged"]}
                                       for g, v in data["groups"].items()},
                            "eligibility_queries": data["eligibility_queries"]}
        reports[str(year)] = {"eligible_queries": len(qids), "all_per_query_group_denominators_match": True,
                              "all_group_and_paired_eligibility_query_ids_match": True,
                              "shared_depth_min": min(depths.values()), "shared_depth_max": max(depths.values()),
                              "isolated_new_source_equals_top10_outside_lexical_full_union_for_every_query": True,
                              "specialist_counts_identical_across_arms_and_visibility": cohort_counts_unchanged,
                              "specialist_counts_full_fixed": compact_counts,
                              "specialist_counts_differing_from_full_fixed": differing_counts,
                              "new_source_top10_outside_lexical_full_union": {
                                  arm: receipt_arms[arm]["new_source_top10_outside_lexical_full_union"]
                                  for arm in ("full", "shared_depth")}}
    return reports


def verify():
    selection_path = "data/cycle02/source-selection.json"
    manifest_path = "data/cycle02/acquired/source-manifest.json"
    selection, manifest = read_json(selection_path), read_json(manifest_path)
    observation_manifest = read_json(OBS + "/manifest.json")
    summary = read_json(OBS + "/summary.json")
    paths = set(observation_manifest["input_sha256_start"]) | set(observation_manifest["source_sha256_start"])
    paths |= {OBS + "/" + p for p in observation_manifest["output_sha256"]}
    paths |= {OBS + "/manifest.json", "_sessions/tools/acquire_cycle02_source.py", str(Path(__file__).relative_to(ROOT))}
    for item in selection["files"]:
        paths.add("_sessions/local/cycle02/source-cache/" + item["expected_sha256"] + "-" + item["filename"])
    before = {p: digest(ROOT / p) for p in sorted(paths)}
    require(before[selection_path] == manifest["selection_sha256"], "Frozen selection hash mismatch")
    require(before["_sessions/tools/acquire_cycle02_source.py"] == manifest["script_sha256"], "Acquisition script hash mismatch")
    for key in ("source_id", "dataset_id", "dataset_revision"):
        require(selection[key] == manifest[key], "Selection provenance metadata mismatch")
    require(len(manifest["original_inputs"]) == len(manifest["derived_runs"]) == len(selection["files"]), "File inventory mismatch")
    for collection in ("input_sha256_start", "input_sha256_end", "source_sha256_start", "source_sha256_end"):
        require(all(before[p] == expected for p, expected in observation_manifest[collection].items()), "Observation manifest input/source hash mismatch")
    require(all(before[OBS + "/" + p] == expected for p, expected in observation_manifest["output_sha256"].items()), "Observation output hash mismatch")
    converted = check_conversion(selection, manifest)
    observed = check_observations(selection, manifest, summary)
    after = {p: digest(ROOT / p) for p in sorted(paths)}
    require(before == after, "An input artifact changed during verification")
    return {"schema_version": 1, "status": "verified", "verification_date": "2026-09-10",
            "source_id": selection["source_id"], "input_artifact_sha256": before,
            "input_artifacts_unchanged_during_check": True,
            "claims": [
                "Every raw candidate matches its derived query/document/rank/score/source tuple and serialized order, including ties.",
                "Independent serialization reconstructs both derived TREC byte hashes; raw bytes/hashes and URL identities match the frozen selection and source manifest.",
                "Core observation counts were independently rebuilt from actual run IDs and qrel membership without importing production acquisition or observation code.",
                "Both arms, fixed and visible cohorts, all owners, every query-level group denominator, and both-group/with-judgment eligibility match the published summary.",
                "For every query, isolated new-source specialists equal new-source top10 outside the original lexical full union; this support label exactly encodes that candidate-access indicator within the new-source specialist cohort.",
                "All start/end input, source, and output hashes in the observation manifest match the current artifacts."],
            "conversion": converted, "observations": observed,
            "limits": ["No relevance grades, retrieval-effect metrics, or power claims were evaluated.",
                       "Provenance verification establishes agreement with the frozen metadata, not undocumented historical generation details.",
                       "Candidate-union/intersection and all source-depth judgment-coverage tables were outside this bounded count cross-check."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--receipt", help="Fresh JSON receipt path, relative to repository or absolute")
    output.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    result = verify()
    if args.receipt:
        path = Path(args.receipt)
        path = path if path.is_absolute() else ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    count = sum(year["row_count"] for year in result["conversion"].values())
    print(f"Verified all {count} conversion tuples and both years' core observation counts.")


if __name__ == "__main__":
    main()
