#!/usr/bin/env python3
"""
PROBE 5: v8.0 (provisional) — k-Tuned RRF with honest cross-validation

Session 2026-05-13-002, Probe 5.

Probe 4 discovered that RRF's hardcoded k=60 is suboptimal. Best k on TREC DL
2019 is ~100-200 (+0.008 NDCG@10 cross-ensemble mean); best k on TREC DL 2020 is
~10 (+0.006). This probe makes the result honest: select k via cross-validation
on labeled training queries, then evaluate on held-out test queries. If the
CV-selected k still beats k=60 on held-out folds, v8.0 is real.

Protocol:
  - 5-fold split on queries per corpus (deterministic, seed 42)
  - For each fold: train_qids = 4 folds, test_qids = 1 fold
  - For each ensemble:
    - On train_qids, evaluate RRF with each k ∈ {1, 5, 10, 30, 60, 100, 200, 500}
    - Pick the k that maximizes mean NDCG@10 on train_qids
    - Evaluate THAT k on test_qids (held-out)
  - Concatenate per-query NDCG@10 across all 5 test folds
  - Compare to Vanilla RRF (k=60) on the same per-query NDCG@10 list via paired t-test

If CV-selected k significantly beats k=60 on per-query basis, v8.0 IS the basin
escape session 002 was searching for.

Three additional honest disclosures:
  1. Bias-corrected reporting: show train-best k vs held-out NDCG@10
  2. Cross-corpus transfer: select k on 2019, apply to 2020, vice versa
  3. Significance vs vanilla and vs the post-hoc oracle k (the upper bound)
"""
import argparse
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    evaluate_ranking, paired_t_test,
)


K_GRID = [1, 5, 10, 30, 60, 100, 200, 500]


def _rrf_fuse(lists, k_smooth):
    rank_of = [{d: i for i, d in enumerate(L)} for L in lists]
    all_docs = set()
    for L in lists:
        all_docs.update(L)
    final = {}
    for d in all_docs:
        s = 0.0
        for r_lookup in rank_of:
            if d in r_lookup:
                s += 1.0 / (k_smooth + r_lookup[d])
        final[d] = s
    return sorted(final, key=lambda d: (-final[d], d))


def eval_qids(qids, runs, qrels, k_smooth):
    """Return per-query NDCG@10 list for the given k."""
    out = []
    for qid in qids:
        if qid not in qrels:
            continue
        lists, _, _ = runs_to_ranked_lists(runs, qid)
        if len(lists) < 2:
            continue
        ranked = _rrf_fuse(lists, k_smooth)
        m = evaluate_ranking(ranked, qrels[qid])
        out.append(m['NDCG@10'])
    return out


def kfold_split(qids, n_folds=5, seed=42):
    shuffled = list(qids)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    return [shuffled[i::n_folds] for i in range(n_folds)]


def cv_evaluate(label, runs, qrels, ens_files, n_folds=5, seed=42):
    """5-fold CV: pick best k on train folds, evaluate on held-out fold. Concatenate test scores."""
    ens_runs = {f: runs[f] for f in ens_files if f in runs}
    qids_all = sorted(qrels.keys())
    folds = kfold_split(qids_all, n_folds=n_folds, seed=seed)

    held_out_v8 = []          # CV-selected k held-out scores
    held_out_van = []         # k=60 held-out scores
    held_out_oracle = []      # post-hoc oracle k held-out scores
    selected_ks = []
    oracle_ks = []

    for fi in range(n_folds):
        test_qids = set(folds[fi])
        train_qids = [q for q in qids_all if q not in test_qids]
        # Evaluate each k on train fold
        train_means = {}
        for k in K_GRID:
            scores = eval_qids(train_qids, ens_runs, qrels, k)
            train_means[k] = statistics.mean(scores)
        best_k = max(train_means.items(), key=lambda x: x[1])[0]
        selected_ks.append(best_k)
        # Evaluate selected k AND k=60 AND oracle-k on held-out
        held_out_v8.extend(eval_qids(folds[fi], ens_runs, qrels, best_k))
        held_out_van.extend(eval_qids(folds[fi], ens_runs, qrels, 60))
        # Oracle: best k on test fold (cheating — for upper bound only)
        test_means = {k: statistics.mean(eval_qids(folds[fi], ens_runs, qrels, k)) for k in K_GRID}
        ok = max(test_means.items(), key=lambda x: x[1])[0]
        oracle_ks.append(ok)
        held_out_oracle.extend(eval_qids(folds[fi], ens_runs, qrels, ok))

    v8_mean = statistics.mean(held_out_v8)
    van_mean = statistics.mean(held_out_van)
    oracle_mean = statistics.mean(held_out_oracle)
    _t, p_vs_van = paired_t_test(held_out_v8, held_out_van)
    _t, p_vs_oracle = paired_t_test(held_out_v8, held_out_oracle)
    print(f"\n  {label}")
    print(f"    selected k per fold: {selected_ks}")
    print(f"    oracle k per fold:   {oracle_ks}")
    print(f"    Vanilla (k=60):  {van_mean:.4f}")
    print(f"    v8 (CV-selected):  {v8_mean:.4f}   Δ vs Vanilla = {v8_mean - van_mean:+.4f}   p = {p_vs_van:.4f}")
    print(f"    Oracle (test-best k): {oracle_mean:.4f}   Δ vs v8 = {oracle_mean - v8_mean:+.4f}   p = {p_vs_oracle:.4f}")
    return {
        'v8_mean': v8_mean, 'van_mean': van_mean, 'oracle_mean': oracle_mean,
        'p_vs_van': p_vs_van, 'p_vs_oracle': p_vs_oracle,
        'selected_ks': selected_ks, 'oracle_ks': oracle_ks,
        'per_q': {'v8': held_out_v8, 'van': held_out_van, 'oracle': held_out_oracle},
    }


def cross_corpus_evaluate(label, runs_train, qrels_train, runs_test, qrels_test, ens_files):
    """Train: pick best k on all of train corpus. Test: evaluate on full test corpus."""
    ens_runs_train = {f: runs_train[f] for f in ens_files if f in runs_train}
    ens_runs_test = {f: runs_test[f] for f in ens_files if f in runs_test}
    if len(ens_runs_train) != len(ens_files) or len(ens_runs_test) != len(ens_files):
        return None
    train_qids = sorted(qrels_train.keys())
    test_qids = sorted(qrels_test.keys())
    train_means = {k: statistics.mean(eval_qids(train_qids, ens_runs_train, qrels_train, k))
                    for k in K_GRID}
    best_k = max(train_means.items(), key=lambda x: x[1])[0]
    v8_test = eval_qids(test_qids, ens_runs_test, qrels_test, best_k)
    van_test = eval_qids(test_qids, ens_runs_test, qrels_test, 60)
    _t, p = paired_t_test(v8_test, van_test)
    v8_mean = statistics.mean(v8_test); van_mean = statistics.mean(van_test)
    print(f"  {label}: train-best k = {best_k}   v8: {v8_mean:.4f}   Vanilla: {van_mean:.4f}   Δ = {v8_mean - van_mean:+.4f}   p = {p:.4f}")
    return v8_mean, van_mean, p, best_k


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-2019', default='data/trec-dl-2019')
    parser.add_argument('--data-2020', default='data/trec-dl-2020')
    args = parser.parse_args()

    runs_2019 = {p.name: parse_run_file(str(p))
                  for p in sorted((Path(args.data_2019) / 'runs').glob('*.txt'))}
    qrels_2019 = parse_qrels(str(Path(args.data_2019) / '2019qrels-pass.txt'))
    runs_2020 = {p.name: parse_run_file(str(p))
                  for p in sorted((Path(args.data_2020) / 'runs').glob('*.txt'))}
    qrels_2020 = parse_qrels(str(Path(args.data_2020) / '2020qrels-pass.txt'))

    print("=" * 78)
    print("PROBE 5: v8.0 PROVISIONAL — k-Tuned RRF (honest 5-fold CV)")
    print("=" * 78)
    print(f"k grid: {K_GRID}")
    print(f"Vanilla RRF default: k = 60")

    base4 = ['bm25.txt', 'bm25_tuned.txt', 'ql_dirichlet.txt', 'tfidf.txt']
    ens_19 = [
        ('n=4 (lexical core)', base4),
        ('n=5 (+proximity)', base4 + ['proximity.txt']),
        ('n=6 (+tfidf_bigram)', base4 + ['proximity.txt', 'tfidf_bigram.txt']),
        ('n=7 (+semantic_hash)', base4 + ['proximity.txt', 'tfidf_bigram.txt', 'semantic_hash.txt']),
    ]
    ens_20 = [('n=4 (lexical core)', base4)]

    print("\n" + "=" * 78)
    print("PART A — Within-corpus 5-fold CV (seed 42)")
    print("=" * 78)

    all_results_19 = []
    for ens_name, files in ens_19:
        r = cv_evaluate(f"2019 {ens_name}", runs_2019, qrels_2019, files)
        all_results_19.append(r)

    all_results_20 = []
    for ens_name, files in ens_20:
        r = cv_evaluate(f"2020 {ens_name}", runs_2020, qrels_2020, files)
        all_results_20.append(r)

    # Cross-ensemble mean (concatenate all per-query NDCG@10 across ensembles)
    print("\n" + "=" * 78)
    print("CROSS-ENSEMBLE TOTALS — TREC DL 2019 (concat per-query)")
    print("=" * 78)
    v8_all = []
    van_all = []
    oracle_all = []
    for r in all_results_19:
        v8_all.extend(r['per_q']['v8'])
        van_all.extend(r['per_q']['van'])
        oracle_all.extend(r['per_q']['oracle'])
    v8_m = statistics.mean(v8_all); van_m = statistics.mean(van_all); or_m = statistics.mean(oracle_all)
    _t, p_v_v = paired_t_test(v8_all, van_all)
    _t, p_v_o = paired_t_test(v8_all, oracle_all)
    print(f"  Vanilla RRF (k=60):      NDCG@10 = {van_m:.4f}   (n_per_query = {len(van_all)})")
    print(f"  v8 (CV-selected k):       NDCG@10 = {v8_m:.4f}   Δ = {v8_m - van_m:+.4f}   p = {p_v_v:.4f}")
    print(f"  Oracle (post-hoc test k): NDCG@10 = {or_m:.4f}   Δ vs v8 = {or_m - v8_m:+.4f}   p = {p_v_o:.4f}")

    # Cross-corpus transfer (only n=4 available in both)
    print("\n" + "=" * 78)
    print("PART B — Cross-corpus transfer (n=4 lexical core)")
    print("=" * 78)
    cross_corpus_evaluate("train 2019 -> test 2020", runs_2019, qrels_2019, runs_2020, qrels_2020, base4)
    cross_corpus_evaluate("train 2020 -> test 2019", runs_2020, qrels_2020, runs_2019, qrels_2019, base4)


if __name__ == '__main__':
    main()
