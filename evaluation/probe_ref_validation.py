#!/usr/bin/env python3
"""
PROBE: REF validation with the winning config (lo=0.35, hi=0.60).

- Full metric panel + bootstrap CIs
- Paired t-tests vs both baselines (Vanilla, v5.0)
- TREC DL 2019 (n=4,5,6,7) + TREC DL 2020 (n=4 only, cross-collection probe)
"""
import argparse
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, fuse_v4x, evaluate_ranking,
    bootstrap_ci, paired_t_test,
)
from probe_regime_aware_fusion import (
    ensemble_regime_jaccard, regime_alpha, fuse_ref_score_mix,
)


def evaluate_panel(qrels, runs, run_subset, label, lo=0.35, hi=0.60):
    """Full metric panel + per-query scores for stat tests."""
    runs_sel = {rn: runs[rn] for rn in run_subset}
    common = set(qrels.keys())
    for rn in run_subset:
        common &= set(runs_sel[rn].keys())

    pq = defaultdict(lambda: defaultdict(list))
    rhos, alphas = [], []

    for qid in sorted(common):
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        if len(lists) < 2:
            continue
        qrel = qrels[qid]
        if not any(v > 0 for v in qrel.values()):
            continue

        for m, s in evaluate_ranking(fuse_vanilla_rrf(lists), qrel).items():
            pq['Vanilla'][m].append(s)

        rank_v5, _, _, _ = fuse_v4x(
            lists, confs, sprs,
            use_contrib_space=False, use_reliability_gate=False,
            use_per_doc_confidence=True,
        )
        for m, s in evaluate_ranking(rank_v5, qrel).items():
            pq['v5.0'][m].append(s)

        rank_ref, rho, alpha = fuse_ref_score_mix(lists, confs, sprs, lo=lo, hi=hi)
        rhos.append(rho)
        alphas.append(alpha)
        for m, s in evaluate_ranking(rank_ref, qrel).items():
            pq['REF-mod'][m].append(s)

    print(f"\n{'='*80}")
    print(f"  {label}   (n_rankers={len(run_subset)}, queries={len(pq['Vanilla']['NDCG@10'])})")
    print(f"  Regime: rho={statistics.mean(rhos):.3f}  alpha={statistics.mean(alphas):.3f}")
    print(f"{'='*80}")

    # Metric table with CIs
    print(f"\n  {'Variant':<10} {'NDCG@10':>22} {'NDCG@20':>22} {'MAP@100':>22} {'MRR':>22}")
    for vn in ('Vanilla', 'v5.0', 'REF-mod'):
        line = f"  {vn:<10}"
        for m in ('NDCG@10', 'NDCG@20', 'MAP@100', 'MRR'):
            scores = pq[vn][m]
            mean = statistics.mean(scores)
            lo_ci, hi_ci = bootstrap_ci(scores)
            line += f"  {mean:.4f} ({lo_ci:.3f}-{hi_ci:.3f})"
        print(line)

    # Paired t-tests for NDCG@10 and MRR
    print(f"\n  Paired t-tests (REF-mod vs baseline):")
    for baseline in ('Vanilla', 'v5.0'):
        for m in ('NDCG@10', 'MRR'):
            a = pq['REF-mod'][m]
            b = pq[baseline][m]
            if len(a) == len(b) and len(a) > 1:
                t, p = paired_t_test(a, b)
                delta = statistics.mean(a) - statistics.mean(b)
                sig = '**' if p < 0.01 else ('*' if p < 0.05 else '')
                print(f"    REF-mod vs {baseline:<8} on {m:<8}: delta={delta:+.4f}  t={t:+.3f}  p={p:.4f}  {sig}")

    return pq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lo', type=float, default=0.35)
    ap.add_argument('--hi', type=float, default=0.60)
    args = ap.parse_args()

    print(f"\nREF validation probe — alpha curve (lo={args.lo}, hi={args.hi})")

    # TREC DL 2019 — full ensemble sweep
    qrels_2019 = parse_qrels('data/trec-dl-2019/2019qrels-pass.txt')
    runs_2019 = {}
    for rf in sorted(Path('data/trec-dl-2019/runs').glob('*.txt')):
        runs_2019[rf.stem] = parse_run_file(str(rf))

    sweeps = [
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet'], 'TREC DL 2019 — n=4 lexical-core'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity'], 'TREC DL 2019 — n=5'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity', 'tfidf_bigram'], 'TREC DL 2019 — n=6'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity', 'tfidf_bigram', 'semantic_hash'], 'TREC DL 2019 — n=7'),
    ]
    summary_2019 = []
    for subset, label in sweeps:
        if not all(s in runs_2019 for s in subset):
            continue
        pq = evaluate_panel(qrels_2019, runs_2019, subset, label, lo=args.lo, hi=args.hi)
        summary_2019.append((label, pq))

    # TREC DL 2020 — only n=4 available
    print("\n\n" + "="*80)
    print("  CROSS-COLLECTION PROBE: TREC DL 2020")
    print("="*80)
    try:
        qrels_2020 = parse_qrels('data/trec-dl-2020/2020qrels-pass.txt')
        runs_2020 = {}
        for rf in sorted(Path('data/trec-dl-2020/runs').glob('*.txt')):
            runs_2020[rf.stem] = parse_run_file(str(rf))
        subset = ['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet']
        if all(s in runs_2020 for s in subset):
            evaluate_panel(qrels_2020, runs_2020, subset, 'TREC DL 2020 — n=4 lexical-core', lo=args.lo, hi=args.hi)
    except Exception as e:
        print(f"  TREC DL 2020 probe failed: {e}")

    # Summary
    print("\n\n" + "="*80)
    print("  SUMMARY — NDCG@10 across TREC DL 2019 sweeps")
    print("="*80)
    print(f"  {'Sweep':<35} {'Vanilla':>10} {'v5.0':>10} {'REF-mod':>10}")
    for label, pq in summary_2019:
        van = statistics.mean(pq['Vanilla']['NDCG@10'])
        v5 = statistics.mean(pq['v5.0']['NDCG@10'])
        ref = statistics.mean(pq['REF-mod']['NDCG@10'])
        print(f"  {label:<35} {van:>10.4f} {v5:>10.4f} {ref:>10.4f}")
    van_m = statistics.mean([statistics.mean(pq['Vanilla']['NDCG@10']) for _, pq in summary_2019])
    v5_m = statistics.mean([statistics.mean(pq['v5.0']['NDCG@10']) for _, pq in summary_2019])
    ref_m = statistics.mean([statistics.mean(pq['REF-mod']['NDCG@10']) for _, pq in summary_2019])
    print(f"  {'Cross-ensemble mean':<35} {van_m:>10.4f} {v5_m:>10.4f} {ref_m:>10.4f}")


if __name__ == '__main__':
    main()
