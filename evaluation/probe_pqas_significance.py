#!/usr/bin/env python3
"""
PROBE 10: PQAS statistical significance — paired t-tests on the k-fold CV best config.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import parse_run_file, parse_qrels, paired_t_test, bootstrap_ci
from probe_per_query_diagnosis import diagnose_collection
from probe_pqas_kfold import kfold_cv


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

    # Use best k-fold configs from probe 9
    # 2019: l2=0.30, threshold=0.5; 2020: l2=0.05, threshold=0.5
    print("\n" + "="*80)
    print("  PQAS k-fold CV — per-query results + significance tests")
    print("  Averaging over 5 seeds for stability")
    print("="*80)

    for label, pq, l2, thr in [('2019 n=4', pq_2019, 0.30, 0.50),
                                ('2020 n=4', pq_2020, 0.05, 0.50)]:
        # Aggregate per-query NDCG across seeds (average each query's NDCG)
        pq_ndcg_acc = [[] for _ in pq]
        for seed in [42, 123, 7, 2024, 99]:
            _, _, _, per_q = kfold_cv(pq, k=5, l2=l2, threshold=thr, seed=seed,
                                       return_per_query=True)
            for i, v in enumerate(per_q):
                if v is not None:
                    pq_ndcg_acc[i].append(v)
        pqas_per_q = [statistics.mean(xs) if xs else 0 for xs in pq_ndcg_acc]

        van_per_q = [q['van_ndcg'] for q in pq]
        v5_per_q = [q['v5_ndcg'] for q in pq]

        van_mean = statistics.mean(van_per_q)
        v5_mean = statistics.mean(v5_per_q)
        pqas_mean = statistics.mean(pqas_per_q)
        oracle = statistics.mean([max(v, va) for v, va in zip(van_per_q, v5_per_q)])

        pqas_lo, pqas_hi = bootstrap_ci(pqas_per_q)

        print(f"\n  {label}:")
        print(f"    Vanilla  : NDCG@10 = {van_mean:.4f}")
        print(f"    v5.0     : NDCG@10 = {v5_mean:.4f}")
        print(f"    PQAS v7  : NDCG@10 = {pqas_mean:.4f} (95% CI {pqas_lo:.3f}-{pqas_hi:.3f})")
        print(f"    ORACLE   : NDCG@10 = {oracle:.4f}")
        print()
        print(f"    PQAS captures {100*(pqas_mean - max(van_mean, v5_mean)) / (oracle - max(van_mean, v5_mean)):.1f}% of oracle gap")
        print()

        # Paired t-tests
        t1, p1 = paired_t_test(pqas_per_q, van_per_q)
        d1 = pqas_mean - van_mean
        sig1 = '**' if p1 < 0.01 else ('*' if p1 < 0.05 else 'ns')
        print(f"    PQAS vs Vanilla: delta={d1:+.4f}  t={t1:+.3f}  p={p1:.4f}  {sig1}")

        t2, p2 = paired_t_test(pqas_per_q, v5_per_q)
        d2 = pqas_mean - v5_mean
        sig2 = '**' if p2 < 0.01 else ('*' if p2 < 0.05 else 'ns')
        print(f"    PQAS vs v5.0   : delta={d2:+.4f}  t={t2:+.3f}  p={p2:.4f}  {sig2}")


if __name__ == '__main__':
    main()
