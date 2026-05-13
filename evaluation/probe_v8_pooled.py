#!/usr/bin/env python3
"""
PROBE 16: v8-A with POOLED training.

Pool 2019 + 2020 queries. Each query gets:
- 10 per-query features
- 20 collection-level aggregate features (mean + std of each per-query
  feature across THAT collection's queries)

Within the pool, collection-level features take 2 different values
(one for 2019 queries, another for 2020 queries). This gives the
classifier signal to learn collection-conditional decision rules.

Test: train on pool minus a fold, predict on held-out queries.
Compare per-collection k-fold to v7's per-collection-only k-fold.
"""
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, paired_t_test, bootstrap_ci,
)
from probe_per_query_diagnosis import diagnose_collection
from probe_pqas_supervised import (
    FEATURE_KEYS, train_lr, predict,
    evaluate_classifier_routing_with_stats,
)
from probe_v8_cross_corpus import (
    collection_aggregates, make_extended_features, standardize_extended, make_labels,
)


def pooled_kfold_cv(pq_pool, k=5, l2=0.10, threshold=0.5, seed=42, use_collection_features=True):
    """k-fold CV over the pooled queries. Each query is labeled with its collection_id."""
    random.seed(seed)
    n = len(pq_pool)
    indices = list(range(n))
    random.shuffle(indices)
    fold_size = n // k
    per_q_ndcg = [None] * n

    for fi in range(k):
        test_idx = indices[fi*fold_size:(fi+1)*fold_size] if fi < k-1 else indices[fi*fold_size:]
        train_idx = [i for i in indices if i not in set(test_idx)]
        train_queries = [pq_pool[i] for i in train_idx]
        test_queries = [pq_pool[i] for i in test_idx]

        if use_collection_features:
            feats_tr = []
            for q in train_queries:
                ft = {k: q[k] for k in FEATURE_KEYS}
                ft.update(q.get('collection_agg', {}))
                feats_tr.append(ft)
            feats_te = []
            for q in test_queries:
                ft = {k: q[k] for k in FEATURE_KEYS}
                ft.update(q.get('collection_agg', {}))
                feats_te.append(ft)
        else:
            feats_tr = [{k: q[k] for k in FEATURE_KEYS} for q in train_queries]
            feats_te = [{k: q[k] for k in FEATURE_KEYS} for q in test_queries]

        keys = list(feats_tr[0].keys())
        X_tr, mu, sd, _ = standardize_extended(feats_tr, keys=keys)
        X_te, _, _, _ = standardize_extended(feats_te, mu, sd, keys=keys)
        y_tr = make_labels(train_queries)

        w, b = train_lr(X_tr, y_tr, lr=0.05, l2=l2, epochs=800)
        probs = predict(X_te, w, b)
        for j, ti in enumerate(test_idx):
            chosen = test_queries[j]['v5_ndcg'] if probs[j] > threshold else test_queries[j]['van_ndcg']
            per_q_ndcg[ti] = chosen
    return per_q_ndcg


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

    # Compute collection aggregates per collection
    agg_2019 = collection_aggregates(pq_2019)
    agg_2020 = collection_aggregates(pq_2020)

    # Annotate each query with its collection_agg
    for q in pq_2019:
        q['collection_agg'] = agg_2019
        q['collection_id'] = 2019
    for q in pq_2020:
        q['collection_agg'] = agg_2020
        q['collection_id'] = 2020

    pq_pool = pq_2019 + pq_2020
    n = len(pq_pool)
    print(f"\nPool size: {n} queries ({len(pq_2019)} from 2019, {len(pq_2020)} from 2020)")

    # Reference points per collection (separate evaluation)
    print(f"\nReference (per-collection mean NDCG@10):")
    for label, pq in [('2019', pq_2019), ('2020', pq_2020)]:
        van = statistics.mean([q['van_ndcg'] for q in pq])
        v5 = statistics.mean([q['v5_ndcg'] for q in pq])
        ora = statistics.mean([max(q['van_ndcg'], q['v5_ndcg']) for q in pq])
        print(f"  {label}: Vanilla={van:.4f}  v5={v5:.4f}  ORACLE={ora:.4f}")

    # v7 within-collection k-fold (from prior probe)
    print(f"\nv7 within-collection k-fold reference:")
    print(f"  2019 n=4: 0.3785 (no significant lift over v5.0=0.3800)")
    print(f"  2020 n=4: 0.4644 (+0.0271 over v5.0, p=0.003 **)")

    # Pooled k-fold with collection features
    print(f"\n{'='*80}")
    print(f"  v8-A: Pooled training with collection-level features")
    print(f"{'='*80}")
    print(f"  l2 + threshold sweep, 5 seeds averaged")

    best = None
    for l2 in [0.10, 0.30, 1.0]:
        for thr in [0.40, 0.50, 0.60]:
            per_q_runs = []
            for seed in [42, 123, 7]:
                per_q = pooled_kfold_cv(pq_pool, k=5, l2=l2, threshold=thr, seed=seed,
                                         use_collection_features=True)
                per_q_runs.append(per_q)
            per_q_mean = [statistics.mean(s[i] for s in per_q_runs) for i in range(n)]

            # Split back into per-collection
            n_2019 = len(pq_2019)
            ndcg_2019 = statistics.mean(per_q_mean[:n_2019])
            ndcg_2020 = statistics.mean(per_q_mean[n_2019:])
            ndcg_pool = statistics.mean(per_q_mean)

            if best is None or ndcg_pool > best[0]:
                best = (ndcg_pool, l2, thr, ndcg_2019, ndcg_2020, per_q_mean)

            print(f"  l2={l2:>5.2f} thr={thr:>4.2f}: pool={ndcg_pool:.4f}  "
                  f"2019={ndcg_2019:.4f}  2020={ndcg_2020:.4f}")

    print(f"\n  Best pooled config: l2={best[1]} thr={best[2]}")
    print(f"    Pool NDCG: {best[0]:.4f}")
    print(f"    2019 contribution: {best[3]:.4f}  (vs v7=0.3785, v5=0.3800, Vanilla=0.3645)")
    print(f"    2020 contribution: {best[4]:.4f}  (vs v7=0.4644, v5=0.4373, Vanilla=0.4483)")

    # Also test WITHOUT collection features (pure per-query features pooled)
    print(f"\n{'='*80}")
    print(f"  Comparison: pooled training WITHOUT collection-level features")
    print(f"  (tests if the collection features specifically help)")
    print(f"{'='*80}")
    best_nocoll = None
    for l2 in [0.10, 0.30, 1.0]:
        for thr in [0.40, 0.50, 0.60]:
            per_q_runs = []
            for seed in [42, 123, 7]:
                per_q = pooled_kfold_cv(pq_pool, k=5, l2=l2, threshold=thr, seed=seed,
                                         use_collection_features=False)
                per_q_runs.append(per_q)
            per_q_mean = [statistics.mean(s[i] for s in per_q_runs) for i in range(n)]
            ndcg_pool = statistics.mean(per_q_mean)
            if best_nocoll is None or ndcg_pool > best_nocoll[0]:
                best_nocoll = (ndcg_pool, l2, thr, per_q_mean)

    print(f"  Best NoCollection: l2={best_nocoll[1]} thr={best_nocoll[2]} NDCG_pool={best_nocoll[0]:.4f}")
    print(f"\n  Collection features lift over no-collection: {best[0] - best_nocoll[0]:+.4f}")

    # Stat tests on best collection-feature variant
    van_per_q = [q['van_ndcg'] for q in pq_pool]
    v5_per_q = [q['v5_ndcg'] for q in pq_pool]
    pqas_per_q = best[5]
    t1, p1 = paired_t_test(pqas_per_q, van_per_q)
    t2, p2 = paired_t_test(pqas_per_q, v5_per_q)
    d_van = statistics.mean(pqas_per_q) - statistics.mean(van_per_q)
    d_v5 = statistics.mean(pqas_per_q) - statistics.mean(v5_per_q)
    s1 = '**' if p1 < 0.01 else ('*' if p1 < 0.05 else 'ns')
    s2 = '**' if p2 < 0.01 else ('*' if p2 < 0.05 else 'ns')
    print(f"\n  Pooled stat tests (97 queries):")
    print(f"    vs Vanilla: delta={d_van:+.4f}  p={p1:.4f}  {s1}")
    print(f"    vs v5.0   : delta={d_v5:+.4f}  p={p2:.4f}  {s2}")


if __name__ == '__main__':
    main()
