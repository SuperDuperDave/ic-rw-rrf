#!/usr/bin/env python3
"""
PROBE 9: PQAS within-collection k-fold CV.

After LOOCV showed cross-collection transfer fails, test the more modest
claim: given N labeled queries from a corpus, can PQAS predict the
per-query optimum on the remaining queries from the SAME corpus?

Honest framing: "label-light supervision with per-corpus tuning."
"""
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import parse_run_file, parse_qrels
from probe_per_query_diagnosis import diagnose_collection
from probe_pqas_supervised import (
    FEATURE_KEYS, standardize, make_labels, train_lr, predict,
    evaluate_classifier_routing_with_stats,
)


def kfold_cv(per_query, k=5, l2=0.10, threshold=0.5, seed=42, return_per_query=False):
    """k-fold CV. Returns mean NDCG@10 across held-out folds."""
    random.seed(seed)
    indices = list(range(len(per_query)))
    random.shuffle(indices)
    fold_size = len(indices) // k
    fold_ndcgs = []
    fold_n_v5 = 0
    fold_n_van = 0
    per_q_ndcg = [None] * len(per_query)
    for fi in range(k):
        test_idx = indices[fi*fold_size:(fi+1)*fold_size] if fi < k-1 else indices[fi*fold_size:]
        train_idx = [i for i in indices if i not in set(test_idx)]
        train = [per_query[i] for i in train_idx]
        test = [per_query[i] for i in test_idx]
        X_tr, means, stds = standardize(train)
        y_tr = make_labels(train)
        X_te, _, _ = standardize(test, means, stds)
        w, b = train_lr(X_tr, y_tr, lr=0.05, l2=l2, epochs=2000)
        probs = predict(X_te, w, b)
        ndcg, n_v5, n_van = evaluate_classifier_routing_with_stats(test, probs, threshold)
        fold_ndcgs.append(ndcg)
        fold_n_v5 += n_v5
        fold_n_van += n_van
        for j, idx in enumerate(test_idx):
            chosen = test[j]['v5_ndcg'] if probs[j] > threshold else test[j]['van_ndcg']
            per_q_ndcg[idx] = chosen
    if return_per_query:
        return statistics.mean(fold_ndcgs), fold_n_v5, fold_n_van, per_q_ndcg
    return statistics.mean(fold_ndcgs), fold_n_v5, fold_n_van


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
    pq_2019, _ = diagnose_collection(qrels_2019, runs_2019, subset, '2019')
    pq_2020, _ = diagnose_collection(qrels_2020, runs_2020, subset, '2020')

    print("\n\n" + "="*80)
    print("  REFERENCE POINTS")
    print("="*80)
    for label, pq in [('2019 n=4', pq_2019), ('2020 n=4', pq_2020)]:
        van = statistics.mean([q['van_ndcg'] for q in pq])
        v5 = statistics.mean([q['v5_ndcg'] for q in pq])
        ora = statistics.mean([max(q['v5_ndcg'], q['van_ndcg']) for q in pq])
        print(f"  {label}: Vanilla={van:.4f}  v5={v5:.4f}  ORACLE={ora:.4f}")

    print("\n\n" + "="*80)
    print("  K-FOLD CV (within-collection) — l2 + threshold sweep")
    print("="*80)
    for label, pq in [('2019', pq_2019), ('2020', pq_2020)]:
        print(f"\n  Collection: {label} (k=5, averaged over 3 seeds for stability)")
        print(f"  {'l2':>6} {'threshold':>10} {'mean NDCG@10':>14} {'v5/van picks':>16}")
        for l2 in [0.05, 0.10, 0.30, 1.0]:
            for thr in [0.40, 0.50, 0.60]:
                ndcgs = []
                v5s, vans = 0, 0
                for seed in [42, 123, 7]:
                    n, v, vn = kfold_cv(pq, k=5, l2=l2, threshold=thr, seed=seed)
                    ndcgs.append(n)
                    v5s += v
                    vans += vn
                m = statistics.mean(ndcgs)
                marker = ""
                ref = max(
                    statistics.mean([q['van_ndcg'] for q in pq]),
                    statistics.mean([q['v5_ndcg'] for q in pq])
                )
                if m > ref + 0.005:
                    marker = " ***"
                elif m > ref:
                    marker = " *"
                print(f"  {l2:>6.2f} {thr:>10.2f} {m:>14.4f} {v5s:>5}/{vans:>5} {marker}")


if __name__ == '__main__':
    main()
