#!/usr/bin/env python3
"""
PROBE 20: v9 — Bayesian-inspired score-sharpness-weighted fusion.

Concept: each ranker's score distribution shape encodes its per-query
reliability. Sharp distributions (high top-1 vs median spread) signal
confident rankers. Flat distributions signal uncertain rankers.

Compute per-query per-ranker reliability w_r from score-distribution
sharpness. Use as weights in RRF — a per-query Bayesian-style model
averaging where the "model evidence" is the score-distribution shape.

Pure label-free (like v6); no training required.
"""
import math
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
from probe_regime_aware_fusion import fuse_ref_score_mix


def ranker_sharpness(scores_dict, K=20):
    """
    Sharpness signal: (top-1 score - K-th score) / (top-1 score - median).
    Higher = sharper distribution = more confident ranker.
    Returns a value in [0, 1] roughly.
    """
    if not scores_dict or len(scores_dict) < K + 1:
        return 0.5  # default to neutral
    sorted_scores = sorted(scores_dict.values(), reverse=True)
    top1 = sorted_scores[0]
    kth = sorted_scores[min(K-1, len(sorted_scores)-1)]
    median = sorted_scores[len(sorted_scores)//2]
    denom = top1 - median
    if abs(denom) < 1e-9:
        return 0.5
    sharp = (top1 - kth) / denom
    return max(0.0, min(2.0, sharp)) / 2.0  # squash to [0,1]


def fuse_bayesian_sharpness(lists, confidences, scores_per_ranker, k=60,
                             temp=1.0):
    """RRF with weights = softmax(sharpness / temperature)."""
    R = len(lists)
    if scores_per_ranker is None or not any(scores_per_ranker):
        # No scores — fall back to vanilla RRF
        return fuse_vanilla_rrf(lists, k=k)

    sharps = []
    for sm in scores_per_ranker:
        sharps.append(ranker_sharpness(sm))
    # Softmax with temperature
    max_s = max(sharps)
    exps = [math.exp((s - max_s) / max(temp, 1e-3)) for s in sharps]
    total = sum(exps)
    weights = [e / total for e in exps] if total > 1e-9 else [1.0 / R] * R

    return _rank_from_scores(_rrf_scores(lists, weights=weights, k=k))


def fuse_bayesian_hybrid(lists, confidences, scores_per_ranker, k=60,
                          temp=1.0, alpha_mix=0.5):
    """
    Hybrid: blend Bayesian sharpness-weighted RRF with v5's modulation.
    alpha_mix = 0 → pure Bayesian-sharpness RRF
    alpha_mix = 1 → pure v5
    """
    R = len(lists)
    bayesian_rank = fuse_bayesian_sharpness(lists, confidences, scores_per_ranker, k=k, temp=temp)
    v5_rank, _, _, _ = fuse_v4x(
        lists, confidences, scores_per_ranker,
        k=k, use_contrib_space=False, use_reliability_gate=False,
        use_per_doc_confidence=True,
    )
    # Positional-score mix
    bay_pos = {d: 1.0 / (i + 1) for i, d in enumerate(bayesian_rank)}
    v5_pos = {d: 1.0 / (i + 1) for i, d in enumerate(v5_rank)}
    # Normalize each to [0,1]
    def norm(sm):
        if not sm: return {}
        mx = max(sm.values())
        return {d: v/mx for d, v in sm.items()} if mx > 1e-12 else sm
    bay_n = norm(bay_pos)
    v5_n = norm(v5_pos)
    all_docs = set(bay_n) | set(v5_n)
    final = {}
    for d in all_docs:
        final[d] = (1-alpha_mix) * bay_n.get(d, 0.0) + alpha_mix * v5_n.get(d, 0.0)
    return _rank_from_scores(final)


def run_collection(qrels, runs, subset, label):
    runs_sel = {rn: runs[rn] for rn in subset}
    common = set(qrels.keys())
    for rn in subset:
        common &= set(runs_sel[rn].keys())

    print(f"\n{'='*80}")
    print(f"  v9 — Bayesian sharpness-weighted fusion — {label}")
    print(f"{'='*80}")

    # Reference points
    van_n = []
    v5_n = []
    v6_n = []
    v9_results = defaultdict(list)

    for qid in sorted(common):
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        if len(lists) < 2: continue
        qrel = qrels[qid]
        if not any(v > 0 for v in qrel.values()): continue

        van_n.append(evaluate_ranking(fuse_vanilla_rrf(lists), qrel)['NDCG@10'])
        v5r, _, _, _ = fuse_v4x(lists, confs, sprs,
                                use_contrib_space=False, use_reliability_gate=False,
                                use_per_doc_confidence=True)
        v5_n.append(evaluate_ranking(v5r, qrel)['NDCG@10'])
        v6r, _, _ = fuse_ref_score_mix(lists, confs, sprs, lo=0.35, hi=0.60)
        v6_n.append(evaluate_ranking(v6r, qrel)['NDCG@10'])

        # v9 variants — temperature sweep
        for temp in [0.1, 0.3, 0.5, 1.0, 2.0]:
            rank = fuse_bayesian_sharpness(lists, confs, sprs, temp=temp)
            v9_results[f'v9-bayes-T{temp}'].append(
                evaluate_ranking(rank, qrel)['NDCG@10']
            )
        # Hybrid sweep
        for alpha in [0.2, 0.4, 0.6, 0.8]:
            rank = fuse_bayesian_hybrid(lists, confs, sprs, temp=0.5, alpha_mix=alpha)
            v9_results[f'v9-hybrid-α{alpha}'].append(
                evaluate_ranking(rank, qrel)['NDCG@10']
            )

    van_m = statistics.mean(van_n)
    v5_m = statistics.mean(v5_n)
    v6_m = statistics.mean(v6_n)
    print(f"\n  Reference: Vanilla={van_m:.4f}  v5={v5_m:.4f}  v6 REF={v6_m:.4f}")

    print(f"\n  v9 variants:")
    for variant, scores in v9_results.items():
        m = statistics.mean(scores)
        # Compare to Vanilla and v6
        t1, p1 = paired_t_test(scores, van_n)
        t2, p2 = paired_t_test(scores, v6_n)
        sig_van = '**' if p1 < 0.01 else ('*' if p1 < 0.05 else '  ')
        sig_v6 = '**' if p2 < 0.01 else ('*' if p2 < 0.05 else '  ')
        print(f"    {variant:<22} : {m:.4f}  (vs Van: {m-van_m:+.4f} {sig_van}; vs v6: {m-v6_m:+.4f} {sig_v6})")


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

    run_collection(qrels_2019, runs_2019, subset, 'TREC DL 2019 n=4')
    run_collection(qrels_2020, runs_2020, subset, 'TREC DL 2020 n=4')


if __name__ == '__main__':
    main()
