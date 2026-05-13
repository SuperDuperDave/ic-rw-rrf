#!/usr/bin/env python3
"""
PROBE 11: Continuous-alpha oracle.

Question: is the continuous-alpha oracle (best alpha per query under v6's
multiplicative-modulation algebra) higher than the binary v5-or-Vanilla oracle?

If yes by >=0.01 average, v7.1 has more upside than v7.
If approximately equal, v7.1 is just a smoother v7.
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
    _rrf_scores, _rank_from_scores,
)


def fuse_continuous_alpha(lists, confidences, scores_per_ranker, alpha, k=60):
    """v6's multiplicative-modulation algebra at a specified alpha."""
    vanilla_scores = _rrf_scores(lists, k=k)
    vanilla_rank = _rank_from_scores(vanilla_scores)
    v5_rank, _, _, _ = fuse_v4x(
        lists, confidences, scores_per_ranker,
        k=k, use_contrib_space=False, use_reliability_gate=False,
        use_per_doc_confidence=True,
    )
    van_pos = {d: i for i, d in enumerate(vanilla_rank)}
    v5_pos = {d: i for i, d in enumerate(v5_rank)}
    final = {}
    for d, v in vanilla_scores.items():
        vp = van_pos.get(d, 1000)
        v5p = v5_pos.get(d, 1000)
        delta = vp - v5p
        if delta > 0:
            mod = 1.0 + alpha * math.log1p(delta) * 0.10
        else:
            mod = 1.0 + alpha * (-math.log1p(-delta)) * 0.05
        final[d] = v * mod
    return _rank_from_scores(final)


def per_query_continuous_oracle(qrels, runs, subset, alphas=None):
    """For each query, sweep alpha and find the best NDCG@10."""
    if alphas is None:
        alphas = [round(0.05 * i, 2) for i in range(0, 21)]  # 0.00, 0.05, ..., 1.00

    runs_sel = {rn: runs[rn] for rn in subset}
    common = set(qrels.keys())
    for rn in subset:
        common &= set(runs_sel[rn].keys())

    out = []
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

        # Sweep continuous alpha
        per_alpha = {}
        for a in alphas:
            rank = fuse_continuous_alpha(lists, confs, sprs, a)
            ndcg = evaluate_ranking(rank, qrel)['NDCG@10']
            per_alpha[a] = ndcg

        best_alpha = max(per_alpha, key=per_alpha.get)
        best_ndcg = per_alpha[best_alpha]

        out.append({
            'qid': qid,
            'van_ndcg': van_ndcg,
            'v5_ndcg': v5_ndcg,
            'binary_oracle': max(van_ndcg, v5_ndcg),
            'continuous_oracle': best_ndcg,
            'best_alpha': best_alpha,
            'per_alpha': per_alpha,
        })
    return out


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
        print(f"  {label}")
        print(f"{'='*80}")
        results = per_query_continuous_oracle(qrels, runs, subset)

        van_m = statistics.mean([r['van_ndcg'] for r in results])
        v5_m = statistics.mean([r['v5_ndcg'] for r in results])
        bin_oracle = statistics.mean([r['binary_oracle'] for r in results])
        cont_oracle = statistics.mean([r['continuous_oracle'] for r in results])

        print(f"  Vanilla        : {van_m:.4f}")
        print(f"  v5.0           : {v5_m:.4f}")
        print(f"  Binary oracle  : {bin_oracle:.4f}  (binary v5/Vanilla per-query)")
        print(f"  Continuous oracle: {cont_oracle:.4f}  (best alpha in [0,1] per-query)")
        print(f"  Continuous - Binary oracle: {cont_oracle - bin_oracle:+.4f}")

        # Distribution of best alphas
        alpha_dist = defaultdict(int)
        for r in results:
            alpha_dist[r['best_alpha']] += 1
        print(f"\n  Distribution of optimal per-query alphas:")
        for a in sorted(alpha_dist):
            bar = '#' * alpha_dist[a]
            print(f"    alpha={a:.2f}  n={alpha_dist[a]:>3}  {bar}")

        # How often is best_alpha in (0, 1) interior vs at the endpoints?
        n_endpoint = sum(1 for r in results if r['best_alpha'] in (0.0, 1.0))
        n_interior = len(results) - n_endpoint
        print(f"\n  Interior optima (alpha in (0,1)): {n_interior}/{len(results)} "
              f"({100*n_interior/len(results):.1f}%)")
        print(f"  Endpoint optima (alpha=0 or 1):    {n_endpoint}/{len(results)} "
              f"({100*n_endpoint/len(results):.1f}%)")

        # Of the interior optima, what's the mean NDCG improvement over the better endpoint?
        interior_lifts = []
        for r in results:
            if r['best_alpha'] not in (0.0, 1.0):
                endpoint_best = max(r['per_alpha'][0.0], r['per_alpha'][1.0])
                lift = r['continuous_oracle'] - endpoint_best
                interior_lifts.append(lift)
        if interior_lifts:
            print(f"  Mean lift for interior-optimum queries vs better endpoint: "
                  f"{statistics.mean(interior_lifts):+.4f}")


if __name__ == '__main__':
    main()
