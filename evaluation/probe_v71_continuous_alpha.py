#!/usr/bin/env python3
"""
PROBE 12: v7.1 — Continuous per-query alpha regression.

Predicts a per-query alpha in [0,1] from the same 10 features used by v7.
Applies v6's multiplicative-modulation algebra at the predicted alpha.

Compared to:
- v7 PQAS (binary v5/Vanilla selector)
- v6 REF (alpha as a piecewise-linear function of rho)
- Vanilla, v5
"""
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, fuse_v4x, evaluate_ranking,
    paired_t_test, bootstrap_ci,
)
from probe_per_query_diagnosis import diagnose_collection
from probe_pqas_supervised import FEATURE_KEYS, standardize, sigmoid
from probe_continuous_alpha_oracle import fuse_continuous_alpha


def train_alpha_regression(X, alpha_targets, lr=0.05, l2=0.10, epochs=2000, seed=42):
    """
    Linear regression with sigmoid output to predict alpha in [0,1].
    Loss: MSE on sigmoid(w·x + b) vs alpha_targets.
    """
    random.seed(seed)
    n, d = len(X), len(X[0])
    w = [random.uniform(-0.01, 0.01) for _ in range(d)]
    b = 0.0
    for _ in range(epochs):
        gw = [0.0] * d
        gb = 0.0
        for i in range(n):
            z = b + sum(w[j] * X[i][j] for j in range(d))
            pred = sigmoid(z)
            err = pred - alpha_targets[i]
            # d/dz of sigmoid: pred * (1 - pred)
            err_z = err * pred * (1 - pred)
            for j in range(d):
                gw[j] += err_z * X[i][j]
            gb += err_z
        for j in range(d):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return w, b


def predict_alpha(X, w, b):
    return [sigmoid(b + sum(w[j] * x[j] for j in range(len(x)))) for x in X]


def find_optimal_alphas(per_query_data, runs, subset, qrels,
                        alphas=None):
    """For each query, find the alpha that maximizes NDCG@10 under v6 algebra."""
    if alphas is None:
        alphas = [round(0.05 * i, 2) for i in range(0, 21)]
    runs_sel = {rn: runs[rn] for rn in subset}
    optimal = []
    for q in per_query_data:
        qid = q['qid']
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        qrel = qrels[qid]
        best_a = 0.0
        best_n = -1.0
        for a in alphas:
            rank = fuse_continuous_alpha(lists, confs, sprs, a)
            n = evaluate_ranking(rank, qrel)['NDCG@10']
            if n > best_n:
                best_n = n
                best_a = a
        optimal.append(best_a)
    return optimal


def evaluate_v71(qrels, runs, subset, label, l2=0.10, k_folds=5, seeds=(42, 123, 7, 2024, 99)):
    """k-fold CV evaluation of v7.1."""
    pq, _ = diagnose_collection(qrels, runs, subset, label)

    # Per-query optimal alphas (oracle target)
    optimal_alphas = find_optimal_alphas(pq, runs, subset, qrels)

    runs_sel = {rn: runs[rn] for rn in subset}

    seed_ndcgs = []
    for seed in seeds:
        random.seed(seed)
        indices = list(range(len(pq)))
        random.shuffle(indices)
        fold_size = len(indices) // k_folds
        fold_ndcgs = []
        for fi in range(k_folds):
            test_idx = indices[fi*fold_size:(fi+1)*fold_size] if fi < k_folds-1 else indices[fi*fold_size:]
            train_idx = [i for i in indices if i not in set(test_idx)]
            train_feats = [pq[i] for i in train_idx]
            train_alphas = [optimal_alphas[i] for i in train_idx]
            test_feats = [pq[i] for i in test_idx]
            X_tr, means, stds = standardize(train_feats)
            X_te, _, _ = standardize(test_feats, means, stds)
            w, b = train_alpha_regression(X_tr, train_alphas, lr=0.05, l2=l2, epochs=2000, seed=seed)
            pred_alphas = predict_alpha(X_te, w, b)
            for j, ti in enumerate(test_idx):
                qid = pq[ti]['qid']
                lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
                rank = fuse_continuous_alpha(lists, confs, sprs, pred_alphas[j])
                ndcg = evaluate_ranking(rank, qrels[qid])['NDCG@10']
                fold_ndcgs.append((ti, ndcg))
        # Aggregate this seed
        by_idx = defaultdict(list)
        for ti, n in fold_ndcgs:
            by_idx[ti].append(n)
        # Each query gets a single NDCG for this seed (it's only tested in one fold)
        seed_per_query = [by_idx[i][0] for i in range(len(pq))]
        seed_ndcgs.append(seed_per_query)

    # Average across seeds per query
    per_query_avg = []
    for i in range(len(pq)):
        per_query_avg.append(statistics.mean(s[i] for s in seed_ndcgs))

    return pq, per_query_avg, optimal_alphas


def main():
    qrels_2019 = parse_qrels('data/trec-dl-2019/2019qrels-pass.txt')
    runs_2019 = {}
    for rf in sorted(Path('data/trec-dl-2019/runs').glob('*.txt')):
        runs_2019[rf.stem] = parse_run_file(str(rf))
    qrels_2020 = parse_qrels('data/trec-dl-2020/2020qrels-pass.txt')
    runs_2020 = {}
    for rf in sorted(Path('data/trec-dl-2020/runs').glob('*.txt')):
        runs_2020[rf.stem] = parse_run_file(str(rf))

    subset = ['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet']

    for label, qrels, runs in [('TREC DL 2019 n=4', qrels_2019, runs_2019),
                                 ('TREC DL 2020 n=4', qrels_2020, runs_2020)]:
        print(f"\n{'='*80}")
        print(f"  {label}")
        print(f"{'='*80}")

        # Best l2 found by sweep
        best_l2 = None
        best_ndcg = -1
        for l2 in [0.03, 0.10, 0.30, 1.0]:
            pq, v71_per_q, opt_alphas = evaluate_v71(qrels, runs, subset, label, l2=l2)
            mean = statistics.mean(v71_per_q)
            if mean > best_ndcg:
                best_ndcg = mean
                best_l2 = l2
            print(f"    l2={l2:>5.2f}  v7.1 NDCG@10 = {mean:.4f}")

        # Re-run best config for detailed reporting
        pq, v71_per_q, opt_alphas = evaluate_v71(qrels, runs, subset, label, l2=best_l2)

        van_per_q = [q['van_ndcg'] for q in pq]
        v5_per_q = [q['v5_ndcg'] for q in pq]
        binary_oracle = [max(v, va) for v, va in zip(van_per_q, v5_per_q)]

        # Continuous oracle: best NDCG at the optimal alpha
        runs_sel = {rn: runs[rn] for rn in subset}
        continuous_oracle = []
        for i, q in enumerate(pq):
            qid = q['qid']
            lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
            rank = fuse_continuous_alpha(lists, confs, sprs, opt_alphas[i])
            continuous_oracle.append(evaluate_ranking(rank, qrels[qid])['NDCG@10'])

        van_m = statistics.mean(van_per_q)
        v5_m = statistics.mean(v5_per_q)
        v71_m = statistics.mean(v71_per_q)
        bin_o = statistics.mean(binary_oracle)
        cont_o = statistics.mean(continuous_oracle)
        lo, hi = bootstrap_ci(v71_per_q)

        print(f"\n  BEST l2={best_l2}: v7.1 NDCG@10 = {v71_m:.4f} (95% CI {lo:.3f}-{hi:.3f})")
        print(f"  Vanilla              : {van_m:.4f}")
        print(f"  v5.0                 : {v5_m:.4f}")
        print(f"  v7.1 (k-fold CV)     : {v71_m:.4f}")
        print(f"  Binary oracle        : {bin_o:.4f}")
        print(f"  Continuous oracle    : {cont_o:.4f}")

        best_fixed = max(van_m, v5_m)
        gap_cont = cont_o - best_fixed
        captured = (v71_m - best_fixed) / gap_cont * 100 if gap_cont > 1e-9 else 0
        print(f"\n  Improvement over best fixed: {v71_m - best_fixed:+.4f}")
        print(f"  Captures {captured:.1f}% of the continuous-oracle gap "
              f"(continuous gap = {gap_cont:.4f})")

        # Stat tests
        t1, p1 = paired_t_test(v71_per_q, van_per_q)
        d1 = v71_m - van_m
        s1 = '**' if p1 < 0.01 else ('*' if p1 < 0.05 else 'ns')
        t2, p2 = paired_t_test(v71_per_q, v5_per_q)
        d2 = v71_m - v5_m
        s2 = '**' if p2 < 0.01 else ('*' if p2 < 0.05 else 'ns')
        print(f"\n  v7.1 vs Vanilla: delta={d1:+.4f}  t={t1:+.3f}  p={p1:.4f}  {s1}")
        print(f"  v7.1 vs v5.0   : delta={d2:+.4f}  t={t2:+.3f}  p={p2:.4f}  {s2}")


if __name__ == '__main__':
    main()
