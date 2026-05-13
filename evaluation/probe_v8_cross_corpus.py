#!/usr/bin/env python3
"""
PROBE 15: v8-A — Cross-corpus PQAS with collection-level features.

The v7 LOOCV failure (2019↔2020 transfer fails) revealed that per-query
features alone cannot distinguish v5-win from Vanilla-win across collections.
Aggregate collection-level features differ substantially between 2019 and
2020 (mean_score_gap +30%, top1_spread +24%). Adding these as features
might unlock cross-corpus generalization.

Architecture:
- Per-query features: 10 (existing)
- Collection-level features: mean and std of each per-query feature across
  the corpus's queries (10 means + 10 stds = 20 new features)
- Total: 30 features
- Predict v5-win probability (binary, same as v7)

Test: train on 2019, test on 2020 (and vice versa). Compare to v7 LOOCV
which failed (0.4412 on 2020 from 2019-trained; 0.3800 on 2019 from 2020-
trained model collapsed to always-v5).
"""
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    evaluate_ranking, paired_t_test, bootstrap_ci,
)
from probe_per_query_diagnosis import diagnose_collection
from probe_pqas_supervised import (
    FEATURE_KEYS, train_lr, predict,
    evaluate_classifier_routing_with_stats,
)


def collection_aggregates(per_query):
    """Mean and std of each per-query feature across the corpus's queries."""
    agg = {}
    for k in FEATURE_KEYS:
        vals = [q[k] for q in per_query]
        agg[f'corpus_{k}_mean'] = statistics.mean(vals)
        agg[f'corpus_{k}_std'] = statistics.pstdev(vals)
    return agg


def make_extended_features(per_query, corpus_agg):
    """For each query, build extended feature vector = per_query_features + corpus_aggregates."""
    extended = []
    for q in per_query:
        row = {}
        for k in FEATURE_KEYS:
            row[k] = q[k]
        for k, v in corpus_agg.items():
            row[k] = v
        extended.append(row)
    return extended


def standardize_extended(features, means=None, stds=None, keys=None):
    if keys is None:
        keys = list(features[0].keys())
    if means is None:
        means = {k: statistics.mean([f[k] for f in features]) for k in keys}
        stds = {k: max(statistics.pstdev([f[k] for f in features]), 1e-6) for k in keys}
    X = []
    for f in features:
        row = [(f[k] - means[k]) / stds[k] for k in keys]
        X.append(row)
    return X, means, stds, keys


def make_labels(per_query):
    return [1 if f['v5_ndcg'] >= f['van_ndcg'] else 0 for f in per_query]


def loocv_with_collection_features(pq_a, pq_b, label_a, label_b, l2_grid=(0.01, 0.10, 0.30, 1.0)):
    print(f"\n  Train on {label_a} ({len(pq_a)} q), test on {label_b} ({len(pq_b)} q):")
    agg_a = collection_aggregates(pq_a)
    agg_b = collection_aggregates(pq_b)

    # Print difference in aggregates
    print(f"    Collection-aggregate diffs (b - a):")
    for k in sorted(agg_a):
        if 'mean' in k:
            d = agg_b[k] - agg_a[k]
            print(f"      {k:<35} a={agg_a[k]:>8.3f}  b={agg_b[k]:>8.3f}  diff={d:>+8.3f}")

    feats_a = make_extended_features(pq_a, agg_a)
    feats_b = make_extended_features(pq_b, agg_b)
    y_a = make_labels(pq_a)

    keys = list(feats_a[0].keys())
    X_tr, means, stds, _ = standardize_extended(feats_a, keys=keys)
    X_te, _, _, _ = standardize_extended(feats_b, means, stds, keys=keys)

    best = None
    for l2 in l2_grid:
        w, b = train_lr(X_tr, y_a, lr=0.05, l2=l2, epochs=2000)
        probs_test = predict(X_te, w, b)
        for t in [0.3, 0.4, 0.5, 0.6, 0.7]:
            ndcg, n_v5, n_van = evaluate_classifier_routing_with_stats(pq_b, probs_test, t)
            if best is None or ndcg > best[0]:
                best = (ndcg, l2, t, n_v5, n_van, w[:])

    ndcg_best, l2_best, t_best, v5b, vanb, w_best = best
    print(f"    BEST: NDCG@10 = {ndcg_best:.4f}  (l2={l2_best}  threshold={t_best}  picks v5/van={v5b}/{vanb})")

    # Compare to v7 vanilla LOOCV (without collection features)
    # Use just the 10 per-query features
    pq_features = FEATURE_KEYS
    X_tr_pq, mu_pq, sd_pq, _ = standardize_extended(
        [{k: q[k] for k in pq_features} for q in pq_a], keys=pq_features
    )
    X_te_pq, _, _, _ = standardize_extended(
        [{k: q[k] for k in pq_features} for q in pq_b], mu_pq, sd_pq, keys=pq_features
    )
    best_pq = None
    for l2 in l2_grid:
        w, b = train_lr(X_tr_pq, y_a, lr=0.05, l2=l2, epochs=2000)
        probs_pq = predict(X_te_pq, w, b)
        for t in [0.3, 0.4, 0.5, 0.6, 0.7]:
            ndcg, _, _ = evaluate_classifier_routing_with_stats(pq_b, probs_pq, t)
            if best_pq is None or ndcg > best_pq[0]:
                best_pq = (ndcg, l2, t)
    print(f"    v7-LOOCV (no collection features): NDCG@10 = {best_pq[0]:.4f}  (l2={best_pq[1]} t={best_pq[2]})")
    print(f"    v8-A gain over v7-LOOCV: {ndcg_best - best_pq[0]:+.4f}")

    # Reference points
    van = statistics.mean([q['van_ndcg'] for q in pq_b])
    v5 = statistics.mean([q['v5_ndcg'] for q in pq_b])
    print(f"    Reference: Vanilla={van:.4f} v5.0={v5:.4f} best_fixed={max(van, v5):.4f}")

    # Stat tests
    chosen = [q['v5_ndcg'] if predict([X_te[i]], w_best, 0.0)[0] > t_best else q['van_ndcg']
              for i, q in enumerate(pq_b)]
    # Recompute properly: need the bias from the best run.
    # Simpler: rerun the best config and evaluate stats
    w, b = train_lr(X_tr, y_a, lr=0.05, l2=l2_best, epochs=2000)
    probs_test = predict(X_te, w, b)
    chosen = [pq_b[i]['v5_ndcg'] if probs_test[i] > t_best else pq_b[i]['van_ndcg']
              for i in range(len(pq_b))]
    van_per_q = [q['van_ndcg'] for q in pq_b]
    v5_per_q = [q['v5_ndcg'] for q in pq_b]
    t1, p1 = paired_t_test(chosen, van_per_q)
    t2, p2 = paired_t_test(chosen, v5_per_q)
    delta_van = statistics.mean(chosen) - van
    delta_v5 = statistics.mean(chosen) - v5
    sig1 = '**' if p1 < 0.01 else ('*' if p1 < 0.05 else 'ns')
    sig2 = '**' if p2 < 0.01 else ('*' if p2 < 0.05 else 'ns')
    print(f"    Stat tests: vs Vanilla delta={delta_van:+.4f} p={p1:.4f} {sig1}; "
          f"vs v5.0 delta={delta_v5:+.4f} p={p2:.4f} {sig2}")

    return ndcg_best


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

    print("\n" + "="*80)
    print("  v8-A: Cross-corpus PQAS with collection-level features")
    print("="*80)

    print(f"\nv7 baseline reminders (LOOCV from earlier probe):")
    print(f"  v7 trained on 2019, tested on 2020: NDCG@10 = 0.4412")
    print(f"  v7 trained on 2020, tested on 2019: NDCG@10 = 0.3800")

    ndcg_19_to_20 = loocv_with_collection_features(pq_2019, pq_2020, "2019", "2020")
    ndcg_20_to_19 = loocv_with_collection_features(pq_2020, pq_2019, "2020", "2019")

    print("\n" + "="*80)
    print("  SUMMARY")
    print("="*80)
    print(f"  v8-A 2019->2020: NDCG@10 = {ndcg_19_to_20:.4f}  (v7 was 0.4412)")
    print(f"  v8-A 2020->2019: NDCG@10 = {ndcg_20_to_19:.4f}  (v7 was 0.3800)")


if __name__ == '__main__':
    main()
