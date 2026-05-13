#!/usr/bin/env python3
"""
PROBE 17: Multi-class oracle.

Is the per-query oracle of {Vanilla, v3.0 DGAF, v4.0, v5.0, v6.0 REF} much
higher than {Vanilla, v5.0}? If yes, expanding the selection space gives
v7 more room to grow.
"""
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, fuse_v21, fuse_v3, fuse_v4x, evaluate_ranking,
    _rrf_scores, _rank_from_scores, _jaccard,
)
from probe_regime_aware_fusion import fuse_ref_score_mix


def get_v3_ranking(lists, confidences, scores_per_ranker, k=60):
    """v3.0 DGAF — needs v2.1 backbone."""
    rank_v21, w_v21, Tq_v21 = fuse_v21(lists, confidences, k=k)
    C_v21 = _rrf_scores(lists, weights=w_v21, k=k)
    R = len(lists)
    import math
    top_sets = [set(L[:30]) for L in lists]
    u = []
    for r in range(R):
        overlaps = [_jaccard(top_sets[r], top_sets[s]) for s in range(R) if s != r]
        m_ov = sum(overlaps) / (len(overlaps) + 1e-12)
        v_ov = sum((x - m_ov) ** 2 for x in overlaps) / (len(overlaps) + 1e-12)
        u.append(math.tanh(v_ov / (m_ov + 0.1)))
    fused_top = set(_rank_from_scores(C_v21)[:30])
    a = [_jaccard(set(L[:30]), fused_top) for L in lists]
    influence = []
    for r in range(R):
        w_m = [w_v21[j] for j in range(R) if j != r]
        l_m = [lists[j] for j in range(R) if j != r]
        sm = sum(w_m) + 1e-12
        w_m = [x/sm for x in w_m]
        fm = _rrf_scores(l_m, weights=w_m, k=k)
        rm = _rank_from_scores(fm)
        influence.append(1.0 - _jaccard(fused_top, set(rm[:30])))
    spec_scores = [confidences[r]*influence[r]*(1-a[r])*u[r] for r in range(R)]
    from trec_eval_harness import _softmax
    spec_idx = sorted(range(R), key=lambda r: spec_scores[r], reverse=True)[:2]
    spec_w = _softmax([max(spec_scores[r], 1e-8) for r in spec_idx], temp=0.7)
    from collections import defaultdict
    S_v21 = defaultdict(float)
    for j, r in enumerate(spec_idx):
        for idx, d in enumerate(lists[r]):
            S_v21[d] += spec_w[j] / (k + idx + 1)
    return fuse_v3(lists, w_v21, Tq_v21, C_v21, dict(S_v21), k=k)


def run_collection(qrels, runs, subset, label):
    runs_sel = {rn: runs[rn] for rn in subset}
    common = set(qrels.keys())
    for rn in subset:
        common &= set(runs_sel[rn].keys())

    per_q = []
    for qid in sorted(common):
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        if len(lists) < 2:
            continue
        qrel = qrels[qid]
        if not any(v > 0 for v in qrel.values()):
            continue

        ndcgs = {}
        ndcgs['Vanilla'] = evaluate_ranking(fuse_vanilla_rrf(lists), qrel)['NDCG@10']
        rank_v21, _, _ = fuse_v21(lists, confs, k=60)
        ndcgs['v2.1'] = evaluate_ranking(rank_v21, qrel)['NDCG@10']
        rank_v3 = get_v3_ranking(lists, confs, sprs)
        ndcgs['v3.0 DGAF'] = evaluate_ranking(rank_v3, qrel)['NDCG@10']
        rank_v4, _, _, _ = fuse_v4x(lists, confs, sprs)
        ndcgs['v4.0'] = evaluate_ranking(rank_v4, qrel)['NDCG@10']
        rank_v5, _, _, _ = fuse_v4x(lists, confs, sprs,
                                     use_contrib_space=False, use_reliability_gate=False,
                                     use_per_doc_confidence=True)
        ndcgs['v5.0'] = evaluate_ranking(rank_v5, qrel)['NDCG@10']
        rank_v6, _, _ = fuse_ref_score_mix(lists, confs, sprs, lo=0.35, hi=0.60)
        ndcgs['v6.0 REF'] = evaluate_ranking(rank_v6, qrel)['NDCG@10']

        per_q.append(ndcgs)

    print(f"\n=== {label} ({len(per_q)} queries) ===")
    print(f"\n  Mean NDCG@10 by variant:")
    variants = ['Vanilla', 'v2.1', 'v3.0 DGAF', 'v4.0', 'v5.0', 'v6.0 REF']
    for v in variants:
        m = statistics.mean(q[v] for q in per_q)
        print(f"    {v:<12}: {m:.4f}")

    print(f"\n  Oracles:")
    # 2-class oracle: best of {Vanilla, v5}
    oracle2 = statistics.mean(max(q['Vanilla'], q['v5.0']) for q in per_q)
    # 3-class oracle: best of {Vanilla, v5, v6}
    oracle3 = statistics.mean(max(q['Vanilla'], q['v5.0'], q['v6.0 REF']) for q in per_q)
    # 4-class oracle: + v3
    oracle4 = statistics.mean(max(q['Vanilla'], q['v3.0 DGAF'], q['v5.0'], q['v6.0 REF']) for q in per_q)
    # 5-class oracle: + v4
    oracle5 = statistics.mean(max(q['Vanilla'], q['v3.0 DGAF'], q['v4.0'], q['v5.0'], q['v6.0 REF']) for q in per_q)
    # 6-class oracle: + v2.1
    oracle6 = statistics.mean(max(q[v] for v in variants) for q in per_q)
    print(f"    Binary  oracle (Vanilla, v5)          : {oracle2:.4f}")
    print(f"    3-class oracle (+v6 REF)               : {oracle3:.4f}  (+{oracle3-oracle2:.4f})")
    print(f"    4-class oracle (+v3 DGAF)              : {oracle4:.4f}  (+{oracle4-oracle3:.4f})")
    print(f"    5-class oracle (+v4)                   : {oracle5:.4f}  (+{oracle5-oracle4:.4f})")
    print(f"    6-class oracle (+v2.1)                 : {oracle6:.4f}  (+{oracle6-oracle5:.4f})")
    print(f"    Total gain (6-class vs binary)         : +{oracle6-oracle2:.4f}")

    # Per-query winner distribution in 6-class
    winners = Counter()
    for q in per_q:
        best_v = max(variants, key=lambda v: q[v])
        winners[best_v] += 1
    print(f"\n  Per-query 6-class winner distribution:")
    for v in variants:
        n = winners[v]
        bar = '#' * n
        print(f"    {v:<12}: {n:>3}  {bar}")


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
