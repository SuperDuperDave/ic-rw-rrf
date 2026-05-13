#!/usr/bin/env python3
"""
PROBE 5: Per-query diagnosis of the 19-vs-20 wall.

Question: same rho, same rankers, opposite collection-level winner.
What per-query signal — observable from ranks/scores alone — predicts
whether v5 or Vanilla wins for that query?

Approach:
1. Per-query, compute NDCG@10 for both v5 and Vanilla
2. Label: 'v5_wins' if v5 NDCG@10 > Vanilla NDCG@10; 'van_wins' otherwise
3. Extract per-query rank-distribution features
4. Test: does any feature significantly differ between v5_wins and van_wins queries?
"""
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, fuse_v4x, evaluate_ranking,
    _jaccard,
)
from probe_regime_aware_fusion import (
    ensemble_regime_jaccard, coverage_entropy,
)


def per_query_features(lists, scores_per_ranker):
    """Compute observable per-query features (no qrels needed)."""
    R = len(lists)
    feats = {}
    feats['rho'] = ensemble_regime_jaccard(lists, K=30)
    feats['h_cov'] = coverage_entropy(lists, K=100)

    # Coverage distribution at top-K
    K = 30
    seen = defaultdict(int)
    for L in lists:
        for d in L[:K]:
            seen[d] += 1
    coverage_counts = list(seen.values())
    feats['n_unique_docs_top30'] = len(coverage_counts)
    feats['frac_specialist_top30'] = sum(1 for c in coverage_counts if c == 1) / max(len(coverage_counts), 1)
    feats['frac_consensus_top30'] = sum(1 for c in coverage_counts if c == R) / max(len(coverage_counts), 1)

    # Score-distribution features (only if scores available)
    score_gaps = []
    score_vars = []
    top1_scores = []
    for sm in scores_per_ranker:
        if not sm or len(sm) < 5:
            continue
        sorted_scores = sorted(sm.values(), reverse=True)
        if len(sorted_scores) < 10:
            continue
        gap = sorted_scores[0] - statistics.median(sorted_scores)
        score_gaps.append(gap)
        score_vars.append(statistics.pstdev(sorted_scores))
        top1_scores.append(sorted_scores[0])
    feats['mean_score_gap'] = statistics.mean(score_gaps) if score_gaps else 0.0
    feats['max_score_gap'] = max(score_gaps) if score_gaps else 0.0
    feats['top1_spread'] = (max(top1_scores) - min(top1_scores)) if len(top1_scores) >= 2 else 0.0
    feats['score_var_mean'] = statistics.mean(score_vars) if score_vars else 0.0

    # Rank-disagreement: for each pair of rankers, mean rank distance of common top-30 docs
    rank_dists = []
    for i in range(R):
        for j in range(i + 1, R):
            common = set(lists[i][:50]) & set(lists[j][:50])
            if not common:
                continue
            pos_i = {d: idx for idx, d in enumerate(lists[i])}
            pos_j = {d: idx for idx, d in enumerate(lists[j])}
            dists = [abs(pos_i[d] - pos_j[d]) for d in common]
            rank_dists.append(statistics.mean(dists))
    feats['mean_rank_dist'] = statistics.mean(rank_dists) if rank_dists else 0.0

    return feats


def diagnose_collection(qrels, runs, subset, label):
    runs_sel = {rn: runs[rn] for rn in subset}
    common = set(qrels.keys())
    for rn in subset:
        common &= set(runs_sel[rn].keys())

    per_query = []
    for qid in sorted(common):
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        if len(lists) < 2:
            continue
        qrel = qrels[qid]
        if not any(v > 0 for v in qrel.values()):
            continue

        van_ndcg = evaluate_ranking(fuse_vanilla_rrf(lists), qrel)['NDCG@10']
        v5_rank, _, _, _ = fuse_v4x(
            lists, confs, sprs,
            use_contrib_space=False, use_reliability_gate=False,
            use_per_doc_confidence=True,
        )
        v5_ndcg = evaluate_ranking(v5_rank, qrel)['NDCG@10']

        feats = per_query_features(lists, sprs)
        feats['qid'] = qid
        feats['van_ndcg'] = van_ndcg
        feats['v5_ndcg'] = v5_ndcg
        feats['delta'] = v5_ndcg - van_ndcg  # positive = v5 wins
        feats['winner'] = 'v5' if v5_ndcg > van_ndcg else ('van' if van_ndcg > v5_ndcg else 'tie')
        per_query.append(feats)

    n_v5 = sum(1 for q in per_query if q['winner'] == 'v5')
    n_van = sum(1 for q in per_query if q['winner'] == 'van')
    n_tie = sum(1 for q in per_query if q['winner'] == 'tie')
    print(f"\n=== {label} ({len(per_query)} queries) ===")
    print(f"  Per-query NDCG@10 winners: v5={n_v5}  Vanilla={n_van}  tie={n_tie}")
    avg_v5 = statistics.mean([q['v5_ndcg'] for q in per_query])
    avg_van = statistics.mean([q['van_ndcg'] for q in per_query])
    print(f"  Mean NDCG@10: Vanilla={avg_van:.4f}  v5={avg_v5:.4f}  delta={avg_v5 - avg_van:+.4f}")

    # Feature comparison: v5-winning queries vs Vanilla-winning queries
    v5_wins = [q for q in per_query if q['winner'] == 'v5']
    van_wins = [q for q in per_query if q['winner'] == 'van']
    if not v5_wins or not van_wins:
        return per_query

    print(f"\n  Feature comparison (v5-wins vs Vanilla-wins):")
    print(f"    {'feature':<25} {'v5_wins mean':>14} {'van_wins mean':>14} {'diff':>10}")
    feat_keys = ['rho', 'h_cov', 'frac_specialist_top30', 'frac_consensus_top30',
                 'mean_score_gap', 'max_score_gap', 'top1_spread', 'score_var_mean',
                 'mean_rank_dist', 'n_unique_docs_top30']
    diffs = {}
    for fk in feat_keys:
        m_v5 = statistics.mean([q[fk] for q in v5_wins])
        m_van = statistics.mean([q[fk] for q in van_wins])
        diff = m_v5 - m_van
        diffs[fk] = (m_v5, m_van, diff)
        print(f"    {fk:<25} {m_v5:>14.4f} {m_van:>14.4f} {diff:>+10.4f}")
    return per_query, diffs


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
    pq_2019, diffs_2019 = diagnose_collection(qrels_2019, runs_2019, subset, 'TREC DL 2019 n=4')
    pq_2020, diffs_2020 = diagnose_collection(qrels_2020, runs_2020, subset, 'TREC DL 2020 n=4')

    # Cross-collection comparison: do the per-query feature signatures of
    # v5-winning queries look similar between collections?
    print("\n\n=== Cross-collection feature signatures (v5-winning queries) ===")
    print(f"  {'feature':<25} {'2019 v5-wins':>14} {'2020 v5-wins':>14} {'diff':>10}")
    for fk, (m19_v5, _, _) in diffs_2019.items():
        m20_v5, _, _ = diffs_2020[fk]
        print(f"  {fk:<25} {m19_v5:>14.4f} {m20_v5:>14.4f} {m19_v5 - m20_v5:>+10.4f}")

    # Compute an oracle: pick v5 when delta > 0, else Vanilla
    print("\n\n=== Oracle vs Achievable ===")
    for pq, label in [(pq_2019, '2019 n=4'), (pq_2020, '2020 n=4')]:
        oracle_ndcg = statistics.mean([max(q['v5_ndcg'], q['van_ndcg']) for q in pq])
        v5_mean = statistics.mean([q['v5_ndcg'] for q in pq])
        van_mean = statistics.mean([q['van_ndcg'] for q in pq])
        print(f"  {label}: Vanilla={van_mean:.4f}  v5={v5_mean:.4f}  ORACLE={oracle_ndcg:.4f}  "
              f"oracle-gap-over-best-fixed={oracle_ndcg - max(v5_mean, van_mean):+.4f}")


if __name__ == '__main__':
    main()
