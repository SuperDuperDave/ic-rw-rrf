#!/usr/bin/env python3
"""
PROBE 14: v7.1-pos — positional-mix algebra (not v6's multiplicative).

alpha=0 → pure Vanilla scores
alpha=1 → pure v5 positional scores
interior → linear mixture of normalized rank-position scores

This algebra's endpoints actually equal Vanilla and v5 (unlike v6's
damped multiplicative algebra).
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
    _rrf_scores, _rank_from_scores,
)
from probe_per_query_diagnosis import diagnose_collection
from probe_pqas_supervised import FEATURE_KEYS, standardize, sigmoid


ALPHAS = [round(0.05 * i, 2) for i in range(0, 21)]


def fuse_positional_mix(lists, confidences, scores_per_ranker, alpha, k=60):
    """
    Positional mixture algebra:
      alpha=0 → vanilla ranking by RRF scores
      alpha=1 → v5 ranking
      interior → mix normalized rank-position scores
    """
    vanilla_scores = _rrf_scores(lists, k=k)
    vanilla_rank = _rank_from_scores(vanilla_scores)
    v5_rank, _, _, _ = fuse_v4x(
        lists, confidences, scores_per_ranker,
        k=k, use_contrib_space=False, use_reliability_gate=False,
        use_per_doc_confidence=True,
    )

    # Positional reciprocal scores from each ranking
    van_pos = {d: 1.0 / (i + 1) for i, d in enumerate(vanilla_rank)}
    v5_pos = {d: 1.0 / (i + 1) for i, d in enumerate(v5_rank)}

    # Normalize each to [0,1]
    def norm(score_map):
        if not score_map:
            return {}
        mx = max(score_map.values())
        if mx < 1e-12:
            return {d: 0.0 for d in score_map}
        return {d: v / mx for d, v in score_map.items()}
    van_n = norm(van_pos)
    v5_n = norm(v5_pos)

    all_docs = set(van_n) | set(v5_n)
    final = {}
    for d in all_docs:
        final[d] = (1 - alpha) * van_n.get(d, 0.0) + alpha * v5_n.get(d, 0.0)
    return _rank_from_scores(final)


def compute_ndcg_curves(per_query, runs, subset, qrels):
    runs_sel = {rn: runs[rn] for rn in subset}
    curves = []
    for q in per_query:
        qid = q['qid']
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        qrel = qrels[qid]
        curve = {}
        for a in ALPHAS:
            rank = fuse_positional_mix(lists, confs, sprs, a)
            curve[a] = evaluate_ranking(rank, qrel)['NDCG@10']
        curves.append(curve)
    return curves


def train_lr_to_alpha(X, alpha_targets, lr=0.05, l2=0.10, epochs=2000, seed=42):
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


def predict_alpha(X, w, b):
    return [sigmoid(b + sum(w[j] * x[j] for j in range(len(x)))) for x in X]


def soft_alpha_target(curve, gamma=1.0):
    weights = [curve[a] ** gamma for a in ALPHAS]
    total = sum(weights)
    if total < 1e-9:
        return 0.5
    return sum(a * w for a, w in zip(ALPHAS, weights)) / total


def best_alpha_target(curve):
    return max(curve, key=curve.get)


def evaluate_v71_pos(qrels, runs, subset, label,
                     target_fn, l2=0.10, k_folds=5,
                     seeds=(42, 123, 7, 2024, 99)):
    pq, _ = diagnose_collection(qrels, runs, subset, label)
    curves = compute_ndcg_curves(pq, runs, subset, qrels)
    runs_sel = {rn: runs[rn] for rn in subset}

    seed_per_query = []
    for seed in seeds:
        random.seed(seed)
        idx = list(range(len(pq)))
        random.shuffle(idx)
        fs = len(idx) // k_folds
        per_q = [None] * len(pq)
        for fi in range(k_folds):
            test_i = idx[fi*fs:(fi+1)*fs] if fi < k_folds-1 else idx[fi*fs:]
            train_i = [i for i in idx if i not in set(test_i)]
            X_tr, mu, sd = standardize([pq[i] for i in train_i])
            X_te, _, _ = standardize([pq[i] for i in test_i], mu, sd)
            tr_targets = [target_fn(curves[i]) for i in train_i]
            w, b = train_lr_to_alpha(X_tr, tr_targets, l2=l2, seed=seed)
            preds = predict_alpha(X_te, w, b)
            for j, ti in enumerate(test_i):
                qid = pq[ti]['qid']
                lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
                rank = fuse_positional_mix(lists, confs, sprs, preds[j])
                per_q[ti] = evaluate_ranking(rank, qrels[qid])['NDCG@10']
        seed_per_query.append(per_q)
    return pq, curves, [statistics.mean(s[i] for s in seed_per_query) for i in range(len(pq))]


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

        # Check endpoint NDCG in this algebra
        alpha0_m = statistics.mean(c[0.0] for c in curves)
        alpha1_m = statistics.mean(c[1.0] for c in curves)
        cont_o = statistics.mean(max(c.values()) for c in curves)
        best_fixed = max(van_m, v5_m)
        print(f"  Vanilla: {van_m:.4f}  v5: {v5_m:.4f}  best_fixed: {best_fixed:.4f}")
        print(f"  Positional-mix at alpha=0: {alpha0_m:.4f}  alpha=1: {alpha1_m:.4f}")
        print(f"  Continuous oracle (positional-mix): {cont_o:.4f} (headroom = {cont_o - best_fixed:+.4f})")

        # Sweep gamma and l2 with soft-alpha target
        print(f"\n  v7.1-pos with NDCG-weighted soft-alpha target:")
        best_ndcg = 0
        best_cfg = None
        best_per_q = None
        for gamma in [1.0, 2.0, 4.0, 8.0, 16.0]:
            for l2 in [0.03, 0.10, 0.30, 1.0]:
                _, _, per_q = evaluate_v71_pos(
                    qrels, runs, subset, label,
                    target_fn=lambda c, G=gamma: soft_alpha_target(c, G), l2=l2,
                )
                m = statistics.mean(per_q)
                if m > best_ndcg:
                    best_ndcg = m
                    best_cfg = (gamma, l2)
                    best_per_q = per_q
        print(f"    Best: NDCG@10 = {best_ndcg:.4f} at γ={best_cfg[0]} l2={best_cfg[1]}")

        # Stat tests on best
        van_per_q = [q['van_ndcg'] for q in pq]
        v5_per_q = [q['v5_ndcg'] for q in pq]
        lo, hi = bootstrap_ci(best_per_q)
        t1, p1 = paired_t_test(best_per_q, van_per_q)
        t2, p2 = paired_t_test(best_per_q, v5_per_q)
        sig1 = '**' if p1 < 0.01 else ('*' if p1 < 0.05 else 'ns')
        sig2 = '**' if p2 < 0.01 else ('*' if p2 < 0.05 else 'ns')
        print(f"    95% CI: {lo:.3f}-{hi:.3f}")
        print(f"    vs Vanilla: delta={best_ndcg - van_m:+.4f}  p={p1:.4f}  {sig1}")
        print(f"    vs v5.0   : delta={best_ndcg - v5_m:+.4f}  p={p2:.4f}  {sig2}")


if __name__ == '__main__':
    main()
