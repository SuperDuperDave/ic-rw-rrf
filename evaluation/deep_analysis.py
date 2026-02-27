#!/usr/bin/env python3
"""
Deep analysis of RRF evaluation results.
Investigates per-query patterns, Ref2/Ref3 interaction, MRR degradation.
"""

import math
import statistics
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional

# Import from harness (same directory)
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, fuse_v21, fuse_v4x,
    evaluate_ranking, paired_t_test,
    _rrf_scores, _rank_from_scores, _jaccard, _zscore
)


def per_query_comparison(runs, qrels, k=60):
    """Compare v4.0+Ref3 vs v4.1 per query to find where Ref2 hurts."""
    run_names = list(runs.keys())
    common_qids = set(qrels.keys())
    for rn in run_names:
        common_qids &= set(runs[rn].keys())

    print(f"\n{'='*100}")
    print("PER-QUERY ANALYSIS: v4.0+Ref3 vs v4.1")
    print(f"{'='*100}")
    print(f"\nComparing per-document confidence ALONE (v4.0+Ref3) vs ALL refinements (v4.1)")
    print(f"Goal: identify WHERE Ref2 (reliability gate) hurts when combined with Ref3\n")

    deltas = []  # (qid, ndcg_ref3, ndcg_v41, delta, Tq)
    query_details = []

    for qid in sorted(common_qids):
        lists, confidences, scores_per_ranker = runs_to_ranked_lists(runs, qid)
        if len(lists) < 2:
            continue
        qrel = qrels[qid]
        if not any(r > 0 for r in qrel.values()):
            continue

        # v4.0+Ref3 (per-doc confidence only)
        rank_ref3, w_ref3, Tq_ref3, indep_ref3 = fuse_v4x(
            lists, confidences, scores_per_ranker, k=k,
            use_contrib_space=False, use_reliability_gate=False, use_per_doc_confidence=True
        )
        metrics_ref3 = evaluate_ranking(rank_ref3, qrel)

        # v4.1 (all three)
        rank_v41, w_v41, Tq_v41, indep_v41 = fuse_v4x(
            lists, confidences, scores_per_ranker, k=k,
            use_contrib_space=True, use_reliability_gate=True, use_per_doc_confidence=True
        )
        metrics_v41 = evaluate_ranking(rank_v41, qrel)

        # v2.1 baseline
        rank_v21, w_v21, Tq_v21 = fuse_v21(lists, confidences, k=k)
        metrics_v21 = evaluate_ranking(rank_v21, qrel)

        # Vanilla RRF
        rank_vanilla = fuse_vanilla_rrf(lists, k=k)
        metrics_vanilla = evaluate_ranking(rank_vanilla, qrel)

        delta = metrics_v41['NDCG@10'] - metrics_ref3['NDCG@10']
        deltas.append((qid, metrics_ref3['NDCG@10'], metrics_v41['NDCG@10'],
                       delta, Tq_ref3,
                       metrics_ref3['MRR'], metrics_v41['MRR'],
                       metrics_v21['NDCG@10'], metrics_vanilla['NDCG@10']))

        # Compute reliability for analysis
        R = len(lists)
        mean_w = 1.0 / R
        reliability = [min(1.0, w_v41[r] / mean_w) for r in range(R)]

        # Independence
        top_sets = [set(L[:30]) for L in lists]
        indep = []
        for r in range(R):
            mean_jac = sum(_jaccard(top_sets[r], top_sets[s])
                          for s in range(R) if s != r) / (R - 1 + 1e-12)
            indep.append(1.0 - mean_jac)

        query_details.append({
            'qid': qid,
            'Tq': Tq_ref3,
            'weights': w_v41,
            'reliability': reliability,
            'indep': indep,
            'ndcg_ref3': metrics_ref3['NDCG@10'],
            'ndcg_v41': metrics_v41['NDCG@10'],
            'ndcg_v21': metrics_v21['NDCG@10'],
            'mrr_ref3': metrics_ref3['MRR'],
            'mrr_v41': metrics_v41['MRR'],
            'delta': delta,
        })

    # Sort by delta (worst v4.1 degradation first)
    deltas.sort(key=lambda x: x[3])

    print(f"{'qid':<10} {'Tq':>5} {'Vanilla':>8} {'v2.1':>8} {'Ref3':>8} {'v4.1':>8} "
          f"{'delta':>8} {'MRR_R3':>8} {'MRR_41':>8}")
    print("-" * 85)

    for qid, ndcg_ref3, ndcg_v41, delta, Tq, mrr_ref3, mrr_v41, ndcg_v21, ndcg_vanilla in deltas:
        marker = " ***" if abs(delta) > 0.05 else ""
        print(f"{qid:<10} {Tq:>5.3f} {ndcg_vanilla:>8.4f} {ndcg_v21:>8.4f} "
              f"{ndcg_ref3:>8.4f} {ndcg_v41:>8.4f} {delta:>+8.4f} "
              f"{mrr_ref3:>8.4f} {mrr_v41:>8.4f}{marker}")

    # Summary stats
    pos_deltas = [d for d in deltas if d[3] > 0]
    neg_deltas = [d for d in deltas if d[3] < 0]
    zero_deltas = [d for d in deltas if d[3] == 0]

    print(f"\n  v4.1 BETTER than Ref3 alone: {len(pos_deltas)} queries "
          f"(mean delta: {statistics.mean([d[3] for d in pos_deltas]):+.4f})" if pos_deltas else "")
    print(f"  v4.1 WORSE than Ref3 alone:  {len(neg_deltas)} queries "
          f"(mean delta: {statistics.mean([d[3] for d in neg_deltas]):+.4f})" if neg_deltas else "")
    print(f"  v4.1 EQUAL to Ref3 alone:    {len(zero_deltas)} queries")

    # Correlation with Tq
    tqs = [d[4] for d in deltas]
    delta_vals = [d[3] for d in deltas]
    if len(tqs) >= 3:
        # Spearman rank correlation (simple version)
        n = len(tqs)
        tq_ranks = [sorted(tqs).index(t) for t in tqs]
        d_ranks = [sorted(delta_vals).index(d) for d in delta_vals]
        d_diff = [(tq_ranks[i] - d_ranks[i])**2 for i in range(n)]
        rho = 1 - 6 * sum(d_diff) / (n * (n**2 - 1))
        print(f"\n  Tq-delta correlation (Spearman rho): {rho:.3f}")
        print(f"  (Positive = v4.1 helps more on harder queries)")

    # MRR analysis
    print(f"\n{'='*100}")
    print("MRR DEGRADATION ANALYSIS")
    print(f"{'='*100}")

    mrr_ref3_vals = [d[5] for d in deltas]
    mrr_v41_vals = [d[6] for d in deltas]
    mrr_delta = [m41 - mr3 for mr3, m41 in zip(mrr_ref3_vals, mrr_v41_vals)]

    mrr_worse = sum(1 for d in mrr_delta if d < 0)
    mrr_better = sum(1 for d in mrr_delta if d > 0)
    mrr_equal = sum(1 for d in mrr_delta if d == 0)

    print(f"  MRR: v4.1 better on {mrr_better}, worse on {mrr_worse}, equal on {mrr_equal} queries")
    print(f"  Mean MRR delta: {statistics.mean(mrr_delta):+.4f}")

    # Queries where MRR drops the most
    mrr_drops = [(d[0], d[5], d[6], d[6]-d[5], d[4]) for d in deltas if d[6] < d[5]]
    mrr_drops.sort(key=lambda x: x[3])
    if mrr_drops:
        print(f"\n  Worst MRR drops (v4.1 vs Ref3 alone):")
        print(f"  {'qid':<10} {'MRR_R3':>8} {'MRR_41':>8} {'delta':>8} {'Tq':>5}")
        for qid, mrr_r3, mrr_41, delta_mrr, tq in mrr_drops[:10]:
            print(f"  {qid:<10} {mrr_r3:>8.4f} {mrr_41:>8.4f} {delta_mrr:>+8.4f} {tq:>5.3f}")

    # Tq distribution analysis
    print(f"\n{'='*100}")
    print("QUERY TEMPERATURE DISTRIBUTION")
    print(f"{'='*100}")

    tq_vals = [d['Tq'] for d in query_details]
    print(f"  Tq range: [{min(tq_vals):.3f}, {max(tq_vals):.3f}]")
    print(f"  Tq mean: {statistics.mean(tq_vals):.3f}")
    print(f"  Tq median: {statistics.median(tq_vals):.3f}")

    # Bin by Tq
    easy = [d for d in query_details if d['Tq'] < 0.5]
    medium = [d for d in query_details if 0.5 <= d['Tq'] < 0.7]
    hard = [d for d in query_details if d['Tq'] >= 0.7]

    for label, group in [('Easy (Tq<0.5)', easy), ('Medium (0.5<=Tq<0.7)', medium), ('Hard (Tq>=0.7)', hard)]:
        if not group:
            continue
        mean_v21 = statistics.mean([d['ndcg_v21'] for d in group])
        mean_ref3 = statistics.mean([d['ndcg_ref3'] for d in group])
        mean_v41 = statistics.mean([d['ndcg_v41'] for d in group])
        print(f"\n  {label} ({len(group)} queries):")
        print(f"    v2.1:     {mean_v21:.4f}")
        print(f"    Ref3:     {mean_ref3:.4f} (delta vs v2.1: {mean_ref3-mean_v21:+.4f})")
        print(f"    v4.1:     {mean_v41:.4f} (delta vs v2.1: {mean_v41-mean_v21:+.4f})")

    # Reliability gate impact
    print(f"\n{'='*100}")
    print("RELIABILITY GATE ANALYSIS")
    print(f"{'='*100}")

    for d in query_details[:5]:
        print(f"\n  Query {d['qid']} (Tq={d['Tq']:.3f}):")
        R = len(d['weights'])
        for r in range(R):
            print(f"    Ranker {r}: w={d['weights'][r]:.4f}, "
                  f"rel={d['reliability'][r]:.4f}, indep={d['indep'][r]:.4f}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deep RRF analysis")
    parser.add_argument('--qrels', type=str, required=True)
    parser.add_argument('--run-dir', type=str, required=True)
    args = parser.parse_args()

    # Load runs
    import glob as globmod
    runs = {}
    for path in sorted(globmod.glob(os.path.join(args.run_dir, '*.txt'))):
        name = os.path.splitext(os.path.basename(path))[0]
        runs[name] = parse_run_file(path)

    # Load qrels
    qrels = parse_qrels(args.qrels)

    print(f"Loaded {len(runs)} runs, {len(qrels)} queries with judgments")
    per_query_comparison(runs, qrels)


if __name__ == "__main__":
    main()
