#!/usr/bin/env python3
"""
PROBE 13: v7.1 with smarter loss functions.

The MSE-on-optimal-alpha approach collapsed to mean because the optimal
alpha distribution is bimodal. Three alternatives tested:

LOSS A: NDCG-weighted soft alpha
   target = sum_a alpha * NDCG(a) / sum_a NDCG(a)
   (center of mass of the per-query NDCG curve over alpha)

LOSS B: NDCG-loss direct gradient
   Loss(alpha_pred) = NDCG_max - NDCG(alpha_pred), interpolated from curve
   Gradient: dNDCG/dalpha approximated from the curve

LOSS C: Best-of-bucket classification then mid-point output
   Bucket alphas into {0.0, 0.5, 1.0}, predict 3-way, output bucket center
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
    evaluate_ranking, paired_t_test, bootstrap_ci,
)
from probe_per_query_diagnosis import diagnose_collection
from probe_pqas_supervised import FEATURE_KEYS, standardize, sigmoid
from probe_continuous_alpha_oracle import fuse_continuous_alpha


ALPHAS = [round(0.05 * i, 2) for i in range(0, 21)]


def compute_ndcg_curves(per_query, runs, subset, qrels):
    """For each query, compute NDCG@10 at every alpha. Returns list of dicts."""
    runs_sel = {rn: runs[rn] for rn in subset}
    curves = []
    for q in per_query:
        qid = q['qid']
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        qrel = qrels[qid]
        curve = {}
        for a in ALPHAS:
            rank = fuse_continuous_alpha(lists, confs, sprs, a)
            curve[a] = evaluate_ranking(rank, qrel)['NDCG@10']
        curves.append(curve)
    return curves


def soft_alpha_target(curve, gamma=1.0):
    """NDCG-weighted soft target. Higher gamma sharpens around the peak."""
    weights = [curve[a] ** gamma for a in ALPHAS]
    total = sum(weights)
    if total < 1e-9:
        return 0.5
    return sum(a * w for a, w in zip(ALPHAS, weights)) / total


def train_lr_to_alpha(X, alpha_targets, lr=0.05, l2=0.10, epochs=2000, seed=42):
    """Linear regression with sigmoid output. MSE loss on alpha targets."""
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
            err_z = err * pred * (1 - pred)
            for j in range(d):
                gw[j] += err_z * X[i][j]
            gb += err_z
        for j in range(d):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return w, b


def train_lr_ndcg_loss(X, curves, lr=0.05, l2=0.10, epochs=2000, seed=42):
    """
    Direct NDCG-loss gradient. For each query:
    - Compute alpha_pred
    - Compute NDCG_at_pred (interpolated from curve)
    - Loss = NDCG_max - NDCG_at_pred
    - Gradient: -dNDCG/dalpha at alpha_pred, times dalpha/dz
    """
    random.seed(seed)
    n, d = len(X), len(X[0])
    w = [random.uniform(-0.01, 0.01) for _ in range(d)]
    b = 0.0

    # Precompute NDCG derivatives per query
    def ndcg_at(curve, alpha):
        # Linear interpolation
        if alpha <= ALPHAS[0]:
            return curve[ALPHAS[0]]
        if alpha >= ALPHAS[-1]:
            return curve[ALPHAS[-1]]
        for j in range(len(ALPHAS) - 1):
            if ALPHAS[j] <= alpha <= ALPHAS[j+1]:
                t = (alpha - ALPHAS[j]) / (ALPHAS[j+1] - ALPHAS[j])
                return (1-t) * curve[ALPHAS[j]] + t * curve[ALPHAS[j+1]]
        return curve[ALPHAS[-1]]

    def dndcg_dalpha(curve, alpha):
        # Numerical derivative; piecewise linear
        if alpha <= ALPHAS[0]:
            return (curve[ALPHAS[1]] - curve[ALPHAS[0]]) / (ALPHAS[1] - ALPHAS[0])
        if alpha >= ALPHAS[-1]:
            return (curve[ALPHAS[-1]] - curve[ALPHAS[-2]]) / (ALPHAS[-1] - ALPHAS[-2])
        for j in range(len(ALPHAS) - 1):
            if ALPHAS[j] <= alpha <= ALPHAS[j+1]:
                return (curve[ALPHAS[j+1]] - curve[ALPHAS[j]]) / (ALPHAS[j+1] - ALPHAS[j])
        return 0.0

    for _ in range(epochs):
        gw = [0.0] * d
        gb = 0.0
        for i in range(n):
            z = b + sum(w[j] * X[i][j] for j in range(d))
            pred = sigmoid(z)
            grad_alpha = -dndcg_dalpha(curves[i], pred)  # want to MAX ndcg, so descend on -ndcg
            grad_z = grad_alpha * pred * (1 - pred)
            for j in range(d):
                gw[j] += grad_z * X[i][j]
            gb += grad_z
        for j in range(d):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return w, b


def predict_alpha(X, w, b):
    return [sigmoid(b + sum(w[j] * x[j] for j in range(len(x)))) for x in X]


def kfold_eval(pq, curves, train_fn, runs, qrels, subset,
               k_folds=5, seeds=(42, 123, 7, 2024, 99), **train_kwargs):
    """k-fold CV evaluation. train_fn(X, y_or_curves, **kwargs) -> (w, b)."""
    runs_sel = {rn: runs[rn] for rn in subset}
    seed_per_query = []
    for seed in seeds:
        random.seed(seed)
        idx = list(range(len(pq)))
        random.shuffle(idx)
        fs = len(idx) // k_folds
        per_q_this_seed = [None] * len(pq)
        for fi in range(k_folds):
            test_i = idx[fi*fs:(fi+1)*fs] if fi < k_folds-1 else idx[fi*fs:]
            train_i = [i for i in idx if i not in set(test_i)]
            train_feats = [pq[i] for i in train_i]
            X_tr, mu, sd = standardize(train_feats)
            X_te, _, _ = standardize([pq[i] for i in test_i], mu, sd)
            if train_fn == train_lr_to_alpha:
                tr_targets = [train_kwargs['target_fn'](curves[i]) for i in train_i]
                w, b = train_lr_to_alpha(X_tr, tr_targets,
                                          lr=0.05, l2=train_kwargs.get('l2', 0.1),
                                          epochs=2000, seed=seed)
            else:
                tr_curves = [curves[i] for i in train_i]
                w, b = train_lr_ndcg_loss(X_tr, tr_curves,
                                           lr=0.05, l2=train_kwargs.get('l2', 0.1),
                                           epochs=2000, seed=seed)
            preds = predict_alpha(X_te, w, b)
            for j, ti in enumerate(test_i):
                qid = pq[ti]['qid']
                lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
                rank = fuse_continuous_alpha(lists, confs, sprs, preds[j])
                per_q_this_seed[ti] = evaluate_ranking(rank, qrels[qid])['NDCG@10']
        seed_per_query.append(per_q_this_seed)

    per_q_mean = [statistics.mean(s[i] for s in seed_per_query) for i in range(len(pq))]
    return per_q_mean


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
        pq, _ = diagnose_collection(qrels, runs, subset, label)
        curves = compute_ndcg_curves(pq, runs, subset, qrels)

        van_m = statistics.mean([q['van_ndcg'] for q in pq])
        v5_m = statistics.mean([q['v5_ndcg'] for q in pq])
        cont_o = statistics.mean([max(c.values()) for c in curves])
        best_fixed = max(van_m, v5_m)
        print(f"  Vanilla: {van_m:.4f}  v5: {v5_m:.4f}  best_fixed: {best_fixed:.4f}")
        print(f"  Continuous oracle: {cont_o:.4f}  (headroom = {cont_o - best_fixed:+.4f})")

        # LOSS A — Soft alpha target (NDCG-weighted) with varying gamma
        print(f"\n  Loss A — NDCG-weighted soft alpha (γ controls sharpness):")
        for gamma in [1.0, 2.0, 4.0, 8.0]:
            best_ndcg_g = 0
            best_l2_g = None
            for l2 in [0.03, 0.10, 0.30, 1.0]:
                per_q = kfold_eval(
                    pq, curves, train_lr_to_alpha, runs, qrels, subset,
                    target_fn=lambda c, G=gamma: soft_alpha_target(c, gamma=G), l2=l2,
                )
                m = statistics.mean(per_q)
                if m > best_ndcg_g:
                    best_ndcg_g = m
                    best_l2_g = l2
            print(f"    γ={gamma:>4.1f}  best NDCG@10 = {best_ndcg_g:.4f}  (l2={best_l2_g})")

        # LOSS B — Direct NDCG-loss gradient
        print(f"\n  Loss B — Direct NDCG-loss gradient:")
        best_ndcg_b = 0
        best_l2_b = None
        best_per_q = None
        for l2 in [0.03, 0.10, 0.30, 1.0]:
            per_q = kfold_eval(
                pq, curves, train_lr_ndcg_loss, runs, qrels, subset, l2=l2,
            )
            m = statistics.mean(per_q)
            print(f"    l2={l2:>5.2f}  NDCG@10 = {m:.4f}")
            if m > best_ndcg_b:
                best_ndcg_b = m
                best_l2_b = l2
                best_per_q = per_q

        print(f"\n  BEST overall this collection: ", end='')
        if best_per_q:
            lo, hi = bootstrap_ci(best_per_q)
            print(f"v7.1-ndcg-loss NDCG@10 = {best_ndcg_b:.4f} (95% CI {lo:.3f}-{hi:.3f}) at l2={best_l2_b}")
            # Stat tests
            v5_per_q = [q['v5_ndcg'] for q in pq]
            van_per_q = [q['van_ndcg'] for q in pq]
            t1, p1 = paired_t_test(best_per_q, van_per_q)
            t2, p2 = paired_t_test(best_per_q, v5_per_q)
            print(f"    vs Vanilla: delta={best_ndcg_b - van_m:+.4f}  p={p1:.4f}")
            print(f"    vs v5.0   : delta={best_ndcg_b - v5_m:+.4f}  p={p2:.4f}")


if __name__ == '__main__':
    main()
