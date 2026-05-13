#!/usr/bin/env python3
"""
PROBE 18: v8.0 — 3-class PQAS over {Vanilla, v5.0, v6.0 REF}.

Multinomial logistic regression with K=3 classes. Same 10 per-query features
as v7. Target: per-query argmax over {Vanilla NDCG, v5 NDCG, v6 REF NDCG}.
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
from probe_pqas_supervised import FEATURE_KEYS, standardize
from probe_regime_aware_fusion import fuse_ref_score_mix


CLASSES = ['Vanilla', 'v5', 'v6_REF']
K = 3


def compute_per_query_ndcgs(per_query, runs, subset, qrels):
    """For each query, compute NDCG@10 of {Vanilla, v5, v6 REF}."""
    runs_sel = {rn: runs[rn] for rn in subset}
    out = []
    for q in per_query:
        qid = q['qid']
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        qrel = qrels[qid]
        van = evaluate_ranking(fuse_vanilla_rrf(lists), qrel)['NDCG@10']
        v5r, _, _, _ = fuse_v4x(
            lists, confs, sprs,
            use_contrib_space=False, use_reliability_gate=False,
            use_per_doc_confidence=True,
        )
        v5 = evaluate_ranking(v5r, qrel)['NDCG@10']
        v6r, _, _ = fuse_ref_score_mix(lists, confs, sprs, lo=0.35, hi=0.60)
        v6 = evaluate_ranking(v6r, qrel)['NDCG@10']
        out.append({'Vanilla': van, 'v5': v5, 'v6_REF': v6, 'qid': qid})
    return out


def make_3class_labels(ndcg_per_query):
    """Label = index of argmax NDCG among {Vanilla, v5, v6_REF}. Tiebreak by preference order
    (Vanilla > v5 > v6) so the model can't game ties."""
    labels = []
    for q in ndcg_per_query:
        vals = [q[c] for c in CLASSES]
        best = vals.index(max(vals))  # first occurrence wins ties
        labels.append(best)
    return labels


def softmax(zs):
    m = max(zs)
    exps = [math.exp(z - m) for z in zs]
    s = sum(exps)
    return [e / s for e in exps]


def train_multinomial_lr(X, y, K=3, lr=0.05, l2=0.10, epochs=800, seed=42):
    """Multinomial LR via batch gradient descent + L2.
    Weights W[K][d]; biases b[K]. Softmax cross-entropy loss."""
    random.seed(seed)
    n, d = len(X), len(X[0])
    W = [[random.uniform(-0.01, 0.01) for _ in range(d)] for _ in range(K)]
    b = [0.0 for _ in range(K)]
    for _ in range(epochs):
        gW = [[0.0] * d for _ in range(K)]
        gb = [0.0] * K
        for i in range(n):
            zs = [b[k] + sum(W[k][j] * X[i][j] for j in range(d)) for k in range(K)]
            probs = softmax(zs)
            # Cross-entropy gradient: dL/dz_k = p_k - y_k
            for k in range(K):
                yk = 1.0 if y[i] == k else 0.0
                err = probs[k] - yk
                for j in range(d):
                    gW[k][j] += err * X[i][j]
                gb[k] += err
        for k in range(K):
            for j in range(d):
                W[k][j] -= lr * (gW[k][j] / n + l2 * W[k][j])
            b[k] -= lr * gb[k] / n
    return W, b


def predict_multinomial(X, W, b):
    """Returns list of (predicted_class_idx, probabilities)."""
    out = []
    K = len(W)
    d = len(X[0])
    for x in X:
        zs = [b[k] + sum(W[k][j] * x[j] for j in range(d)) for k in range(K)]
        probs = softmax(zs)
        out.append((probs.index(max(probs)), probs))
    return out


def kfold_3class(per_query_feat, ndcg_per_query, runs, qrels, subset,
                  l2=0.10, k_folds=5, seeds=(42, 123, 7, 2024, 99)):
    """k-fold CV for 3-class PQAS."""
    n = len(per_query_feat)
    seed_per_query = []
    for seed in seeds:
        random.seed(seed)
        idx = list(range(n))
        random.shuffle(idx)
        fs = n // k_folds
        per_q = [None] * n
        for fi in range(k_folds):
            test_i = idx[fi*fs:(fi+1)*fs] if fi < k_folds-1 else idx[fi*fs:]
            train_i = [i for i in idx if i not in set(test_i)]
            X_tr, mu, sd = standardize([per_query_feat[i] for i in train_i])
            X_te, _, _ = standardize([per_query_feat[i] for i in test_i], mu, sd)
            y_tr = make_3class_labels([ndcg_per_query[i] for i in train_i])
            W, b = train_multinomial_lr(X_tr, y_tr, K=K, lr=0.05, l2=l2, epochs=800, seed=seed)
            preds = predict_multinomial(X_te, W, b)
            for j, ti in enumerate(test_i):
                pred_class, _ = preds[j]
                cls_name = CLASSES[pred_class]
                per_q[ti] = ndcg_per_query[ti][cls_name]
        seed_per_query.append(per_q)
    return [statistics.mean(s[i] for s in seed_per_query) for i in range(n)]


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
        print(f"  v8.0 — 3-class PQAS — {label}")
        print(f"{'='*80}")
        pq, _ = diagnose_collection(qrels, runs, subset, label)
        ndcg_per_q = compute_per_query_ndcgs(pq, runs, subset, qrels)

        # Reference points
        van = statistics.mean(q['Vanilla'] for q in ndcg_per_q)
        v5 = statistics.mean(q['v5'] for q in ndcg_per_q)
        v6 = statistics.mean(q['v6_REF'] for q in ndcg_per_q)
        bin_oracle = statistics.mean(max(q['Vanilla'], q['v5']) for q in ndcg_per_q)
        oracle3 = statistics.mean(max(q['Vanilla'], q['v5'], q['v6_REF']) for q in ndcg_per_q)

        print(f"\n  Reference points:")
        print(f"    Vanilla              : {van:.4f}")
        print(f"    v5.0                 : {v5:.4f}")
        print(f"    v6.0 REF             : {v6:.4f}")
        print(f"    Binary oracle (V/v5)  : {bin_oracle:.4f}")
        print(f"    3-class oracle        : {oracle3:.4f}")
        print(f"    3-class headroom over best fixed: {oracle3 - max(van, v5, v6):+.4f}")

        # Class label distribution
        labels = make_3class_labels(ndcg_per_q)
        n_per_class = [labels.count(k) for k in range(3)]
        print(f"\n  Class distribution (argmax of NDCG@10 per query):")
        for k, c in enumerate(CLASSES):
            bar = '#' * n_per_class[k]
            print(f"    {c:<10}: {n_per_class[k]:>3} ({100*n_per_class[k]/len(labels):>5.1f}%)  {bar}")

        # k-fold CV across l2 sweep
        print(f"\n  v8.0 3-class PQAS k-fold CV (5 folds, 5 seeds averaged):")
        best = None
        for l2 in [0.05, 0.10, 0.30, 1.0, 3.0]:
            per_q_feats = [{k: q[k] for k in FEATURE_KEYS} for q in pq]
            per_q_ndcg_pred = kfold_3class(per_q_feats, ndcg_per_q, runs, qrels, subset, l2=l2)
            mean = statistics.mean(per_q_ndcg_pred)
            print(f"    l2={l2:>5.2f}  v8 NDCG@10 = {mean:.4f}")
            if best is None or mean > best[0]:
                best = (mean, l2, per_q_ndcg_pred)

        print(f"\n  BEST l2={best[1]}: v8.0 NDCG@10 = {best[0]:.4f}")
        v8_per_q = best[2]
        lo, hi = bootstrap_ci(v8_per_q)
        print(f"  Bootstrap 95% CI: {lo:.3f}-{hi:.3f}")

        # Stat tests
        van_per_q = [q['Vanilla'] for q in ndcg_per_q]
        v5_per_q = [q['v5'] for q in ndcg_per_q]
        v6_per_q = [q['v6_REF'] for q in ndcg_per_q]

        t1, p1 = paired_t_test(v8_per_q, van_per_q)
        d1 = best[0] - van
        sig1 = '**' if p1 < 0.01 else ('*' if p1 < 0.05 else 'ns')
        t2, p2 = paired_t_test(v8_per_q, v5_per_q)
        d2 = best[0] - v5
        sig2 = '**' if p2 < 0.01 else ('*' if p2 < 0.05 else 'ns')
        t3, p3 = paired_t_test(v8_per_q, v6_per_q)
        d3 = best[0] - v6
        sig3 = '**' if p3 < 0.01 else ('*' if p3 < 0.05 else 'ns')

        print(f"\n  Stat tests:")
        print(f"    v8 vs Vanilla : delta={d1:+.4f}  p={p1:.4f}  {sig1}")
        print(f"    v8 vs v5.0    : delta={d2:+.4f}  p={p2:.4f}  {sig2}")
        print(f"    v8 vs v6.0 REF: delta={d3:+.4f}  p={p3:.4f}  {sig3}")
        # Headroom captured
        if oracle3 - max(van, v5, v6) > 1e-9:
            cap = 100 * (best[0] - max(van, v5, v6)) / (oracle3 - max(van, v5, v6))
            print(f"\n  3-class oracle gap captured: {cap:.1f}%")


if __name__ == '__main__':
    main()
