#!/usr/bin/env python3
"""
PROBE: Basin-Escape MC4 — Markov Chain Rank Aggregation (Dwork-Kumar-Naor 2001)

Session 2026-05-13-002. First probe OUTSIDE RRF's basin.

Session 001 established: the entire IC-RRF lineage (v2.1-v7.0) is a perturbation
of `score(d) = sum_r 1/(k+rank_r(d))`. On TREC DL 2019 cross-ensemble mean,
Vanilla RRF (0.3910) and v6.0 REF (0.3919) are statistically tied. The basin is
exhausted.

This probe leaves the basin entirely. MC4 has no decay function and no linear
sum. Instead, documents are nodes in a Markov chain whose transition probabilities
encode pairwise rank preferences. The stationary distribution IS the fused
ranking. Eigenvector centrality. The same math as PageRank, applied to rankings.

Pre-test predictions (for falsification discipline):
  - MC4 should match-or-exceed Vanilla on heterogeneous ensembles (n=5,6,7
    where ranker disagreement is high) — that is the regime Markov chain methods
    are designed for.
  - MC4 may underperform Vanilla on homogeneous ensembles (n=4 lexical core)
    where Vanilla's variance-reduction is already strong.
  - If the pattern reverses — MC4 wins/loses exactly where Vanilla does — the
    basin escape is illusory and we pivot to Basin 2 (information-theoretic f(r)).
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
    paired_t_test, bootstrap_ci,
)


def fuse_mc4(lists, pool_K=100, damping=0.15, max_iters=80, tol=1e-7):
    """
    MC4 — Dwork-Kumar-Naor 2001, §3.

    Construct a Markov chain on a candidate pool of documents. Transition
    rule: from state d, propose d' uniformly at random from the pool. If a
    strict majority of rankers that rank BOTH d and d' place d' above d,
    move to d'. Otherwise stay at d. A PageRank-style damping term
    distributes a small amount of mass uniformly to ensure the chain is
    irreducible.

    Returns: ranked list of doc IDs (length = pool size), sorted by
    stationary probability descending.

    Parameters:
      pool_K   — top-K per ranker forms the candidate pool (union)
      damping  — PageRank-style teleportation probability (1-damping kept)
      max_iters — power iteration cap
      tol       — L1 convergence tolerance on the stationary distribution
    """
    # Candidate pool = union of top-K from each ranker
    pool = set()
    for L in lists:
        pool.update(L[:pool_K])
    pool = sorted(pool)  # stable iteration order
    N = len(pool)
    if N == 0:
        return []
    if N == 1:
        return list(pool)

    # Per-ranker rank lookup. Documents NOT in a ranker's list -> None.
    # We use the position in the ranker's full list (not truncated to pool_K)
    # so all available preference information is used.
    rank_of = []  # list of {docid: rank} per ranker
    for L in lists:
        rank_of.append({d: i for i, d in enumerate(L)})

    # For each ordered pair (d, d') in pool: does d' BEAT d?
    # "Beats" = strict majority of rankers that rank BOTH place d' above d.
    # Building the preference list as adjacency: beats_d[d] = set of d' that beat d
    pool_index = {d: i for i, d in enumerate(pool)}
    beats_d = [[] for _ in range(N)]  # beats_d[i] = list of j such that pool[j] beats pool[i]

    for i, d in enumerate(pool):
        for j, dp in enumerate(pool):
            if i == j:
                continue
            both_count = 0
            dp_above = 0
            for r_lookup in rank_of:
                rd = r_lookup.get(d)
                rdp = r_lookup.get(dp)
                if rd is None or rdp is None:
                    continue
                both_count += 1
                if rdp < rd:
                    dp_above += 1
            if both_count > 0 and dp_above * 2 > both_count:
                beats_d[i].append(j)

    # Transition matrix (sparse representation). From state i:
    #   With probability (1 - damping):
    #     Pick d' uniformly from pool (prob 1/N each).
    #     If d' beats d, move to d'. Else stay at d.
    #     -> P_move(i->j) = (1-damping) / N      for each j in beats_d[i]
    #     -> P_stay(i->i) = (1-damping) * (1 - |beats_d[i]| / N)
    #   With probability damping: teleport uniformly -> damping / N to every j.
    #
    # Combined:
    #   P(i->j) = damping/N + (1-damping)/N           if j in beats_d[i]
    #   P(i->j) = damping/N                            if j != i and j NOT in beats_d[i]
    #   P(i->i) = damping/N + (1-damping)*(1 - |beats_d[i]|/N)
    #
    # Power iteration: pi <- pi * P  (row vector left-multiplication)
    #   pi_new[j] = sum_i pi[i] * P(i->j)
    #
    # For efficiency, decompose:
    #   pi_new[j] = damping/N * sum_i pi[i]               -> = damping/N  (since pi sums to 1)
    #              + (1-damping)/N * sum_{i: j in beats_d[i]} pi[i]
    #              + (1-damping)*(1 - |beats_d[i]|/N) * pi[i] if i==j  -> handled separately
    #
    # Simpler equivalent form (cleaner):
    #   move_prob[i] = (1-damping) * |beats_d[i]| / N        # total prob of MOVING out
    #   stay_prob[i] = 1 - move_prob[i] - damping*(N-1)/N    # stay at i (no teleport elsewhere)
    # ...the full PageRank power iteration handles this naturally if we just
    # build the transition adjacency and iterate. We'll use the explicit
    # decomposition for clarity:
    #
    # pi_new[j] = damping / N
    #           + (1 - damping) * sum_{i: j in beats_d[i]} pi[i] / N
    #           + (1 - damping) * (1 - |beats_d[i]| / N) * pi[i] * [i == j]
    #
    # We need the "incoming" structure: for each j, which i's have j in beats_d[i]?
    incoming = [[] for _ in range(N)]
    for i in range(N):
        for j in beats_d[i]:
            incoming[j].append(i)
    out_degree = [len(beats_d[i]) for i in range(N)]

    # Initialize uniformly
    pi = [1.0 / N for _ in range(N)]
    inv_N = 1.0 / N
    one_minus_d = 1.0 - damping
    base = damping * inv_N

    for _iter in range(max_iters):
        pi_new = [base] * N
        # Contribution from "move" transitions: pi[i] flows to each j in beats_d[i] with prob (1-damping)/N
        # Aggregated incoming: pi_new[j] += (1-damping)/N * sum_{i in incoming[j]} pi[i]
        for j in range(N):
            if incoming[j]:
                s = 0.0
                for i in incoming[j]:
                    s += pi[i]
                pi_new[j] += one_minus_d * inv_N * s
        # Contribution from "stay" transitions: pi[i] * (1-damping) * (1 - out_deg[i]/N) stays at i
        for i in range(N):
            stay = one_minus_d * (1.0 - out_degree[i] * inv_N)
            pi_new[i] += pi[i] * stay

        # Normalize (numerical hygiene)
        s = sum(pi_new)
        if s > 0:
            pi_new = [v / s for v in pi_new]

        # Convergence
        delta = sum(abs(pi_new[i] - pi[i]) for i in range(N))
        pi = pi_new
        if delta < tol:
            break

    # Rank by pi descending; tiebreak by doc id for determinism
    indexed = sorted(range(N), key=lambda i: (-pi[i], pool[i]))
    return [pool[i] for i in indexed]


def evaluate_fusion_across_queries(qids, runs, qrels, fusion_fn, **fusion_kwargs):
    """Evaluate a fusion function across queries; return per-query NDCG@10 list + summary."""
    per_query_ndcg = []
    per_query_mrr = []
    per_query_ndcg20 = []
    per_query_map = []
    for qid in qids:
        if qid not in qrels:
            continue
        lists, confidences, scores_per_ranker = runs_to_ranked_lists(runs, qid)
        if len(lists) < 2:
            continue
        ranked = fusion_fn(lists, **fusion_kwargs)
        m = evaluate_ranking(ranked, qrels[qid])
        per_query_ndcg.append(m['NDCG@10'])
        per_query_mrr.append(m['MRR'])
        per_query_ndcg20.append(m['NDCG@20'])
        per_query_map.append(m['MAP@100'])
    return {
        'NDCG@10': per_query_ndcg,
        'NDCG@20': per_query_ndcg20,
        'MAP@100': per_query_map,
        'MRR':     per_query_mrr,
    }


def _summary(metrics_dict):
    """Mean for each metric in the per-query dict."""
    return {k: statistics.mean(v) if v else 0.0 for k, v in metrics_dict.items()}


def fuse_vanilla_rrf_wrapper(lists, **_):
    return fuse_vanilla_rrf(lists, k=60)


def fuse_v5_wrapper(lists, scores_per_ranker=None, confidences=None, **_):
    """Wrap v5.0 (v4.0+Ref3 config) to match the simple fusion signature."""
    # Need scores_per_ranker + confidences from outside — handled in main loop
    ranked, _, _, _ = fuse_v4x(
        lists, confidences, scores_per_ranker,
        k=60,
        use_contrib_space=False,
        use_reliability_gate=False,
        use_per_doc_confidence=True,
    )
    return ranked


def run_ensemble_sweep(runs_2019, qrels_2019, runs_2020, qrels_2020):
    """
    Run the cross-ensemble basin-escape probe.

    Configurations:
      TREC DL 2019: n=4 (homogeneous lexical), n=5 (+proximity), n=6 (+tfidf_bigram), n=7 (+semantic_hash)
      TREC DL 2020: n=4 (homogeneous lexical, only ensemble available)
    """
    base4_2019 = ['bm25.txt', 'bm25_tuned.txt', 'ql_dirichlet.txt', 'tfidf.txt']
    ensembles_2019 = [
        ('n=4 (lexical core)',  base4_2019),
        ('n=5 (+proximity)',     base4_2019 + ['proximity.txt']),
        ('n=6 (+tfidf_bigram)',  base4_2019 + ['proximity.txt', 'tfidf_bigram.txt']),
        ('n=7 (+semantic_hash)', base4_2019 + ['proximity.txt', 'tfidf_bigram.txt', 'semantic_hash.txt']),
    ]
    base4_2020 = ['bm25.txt', 'bm25_tuned.txt', 'ql_dirichlet.txt', 'tfidf.txt']
    ensembles_2020 = [('n=4 (lexical core)', base4_2020)]

    results = []
    for collection, runs_all, qrels, ensembles in [
        ('TREC DL 2019', runs_2019, qrels_2019, ensembles_2019),
        ('TREC DL 2020', runs_2020, qrels_2020, ensembles_2020),
    ]:
        for ens_name, ens_files in ensembles:
            runs_sub = {f: runs_all[f] for f in ens_files if f in runs_all}
            if len(runs_sub) != len(ens_files):
                print(f"WARN: missing runs for {collection} {ens_name}: have {list(runs_sub.keys())}")
                continue
            qids = sorted(qrels.keys())
            # Vanilla
            van_metrics = evaluate_fusion_across_queries(qids, runs_sub, qrels, fuse_vanilla_rrf_wrapper)
            # MC4
            mc4_metrics = evaluate_fusion_across_queries(qids, runs_sub, qrels, fuse_mc4,
                                                         pool_K=100, damping=0.15, max_iters=80)
            # v5.0 needs the rich signature — call manually
            v5_per_query = {'NDCG@10': [], 'MRR': [], 'NDCG@20': [], 'MAP@100': []}
            for qid in qids:
                if qid not in qrels:
                    continue
                lists, confs, sprs = runs_to_ranked_lists(runs_sub, qid)
                if len(lists) < 2:
                    continue
                ranked, _, _, _ = fuse_v4x(lists, confs, sprs, k=60,
                                            use_contrib_space=False,
                                            use_reliability_gate=False,
                                            use_per_doc_confidence=True)
                m = evaluate_ranking(ranked, qrels[qid])
                v5_per_query['NDCG@10'].append(m['NDCG@10'])
                v5_per_query['MRR'].append(m['MRR'])
                v5_per_query['NDCG@20'].append(m['NDCG@20'])
                v5_per_query['MAP@100'].append(m['MAP@100'])

            row = {
                'collection': collection,
                'ensemble':   ens_name,
                'n_queries':  len(van_metrics['NDCG@10']),
                'vanilla':    _summary(van_metrics),
                'v5':         _summary(v5_per_query),
                'mc4':        _summary(mc4_metrics),
                'mc4_vs_van_pq': (mc4_metrics['NDCG@10'], van_metrics['NDCG@10']),
                'mc4_vs_v5_pq':  (mc4_metrics['NDCG@10'], v5_per_query['NDCG@10']),
            }
            results.append(row)
            print(f"\n{collection} | {ens_name}  (n_queries = {row['n_queries']})")
            print(f"  Vanilla NDCG@10 = {row['vanilla']['NDCG@10']:.4f}   MRR = {row['vanilla']['MRR']:.4f}")
            print(f"  v5.0    NDCG@10 = {row['v5']['NDCG@10']:.4f}   MRR = {row['v5']['MRR']:.4f}")
            print(f"  MC4     NDCG@10 = {row['mc4']['NDCG@10']:.4f}   MRR = {row['mc4']['MRR']:.4f}")
            t_v, p_v = paired_t_test(mc4_metrics['NDCG@10'], van_metrics['NDCG@10'])
            t_5, p_5 = paired_t_test(mc4_metrics['NDCG@10'], v5_per_query['NDCG@10'])
            print(f"  MC4 vs Vanilla: delta = {row['mc4']['NDCG@10'] - row['vanilla']['NDCG@10']:+.4f}  (p = {p_v:.3f})")
            print(f"  MC4 vs v5.0:    delta = {row['mc4']['NDCG@10'] - row['v5']['NDCG@10']:+.4f}  (p = {p_5:.3f})")

    return results


def main():
    parser = argparse.ArgumentParser(description="MC4 basin-escape probe")
    parser.add_argument('--data-2019', default='data/trec-dl-2019')
    parser.add_argument('--data-2020', default='data/trec-dl-2020')
    args = parser.parse_args()

    # Load 2019
    runs_2019 = {}
    runs_dir_2019 = Path(args.data_2019) / 'runs'
    for p in sorted(runs_dir_2019.glob('*.txt')):
        runs_2019[p.name] = parse_run_file(str(p))
    qrels_2019 = parse_qrels(str(Path(args.data_2019) / '2019qrels-pass.txt'))

    # Load 2020
    runs_2020 = {}
    runs_dir_2020 = Path(args.data_2020) / 'runs'
    for p in sorted(runs_dir_2020.glob('*.txt')):
        runs_2020[p.name] = parse_run_file(str(p))
    qrels_2020 = parse_qrels(str(Path(args.data_2020) / '2020qrels-pass.txt'))

    print("=" * 72)
    print("PROBE: BASIN-ESCAPE MC4 — Markov Chain Rank Aggregation (DKN 2001)")
    print("=" * 72)
    print(f"Loaded {len(runs_2019)} runs / {len(qrels_2019)} queries for TREC DL 2019")
    print(f"Loaded {len(runs_2020)} runs / {len(qrels_2020)} queries for TREC DL 2020")

    results = run_ensemble_sweep(runs_2019, qrels_2019, runs_2020, qrels_2020)

    # Cross-ensemble mean for TREC DL 2019 (the session-001 headline number)
    rows_2019 = [r for r in results if r['collection'] == 'TREC DL 2019']
    if rows_2019:
        van_mean = statistics.mean([r['vanilla']['NDCG@10'] for r in rows_2019])
        v5_mean  = statistics.mean([r['v5']['NDCG@10'] for r in rows_2019])
        mc4_mean = statistics.mean([r['mc4']['NDCG@10'] for r in rows_2019])
        print("\n" + "=" * 72)
        print("CROSS-ENSEMBLE MEAN (TREC DL 2019, n=4,5,6,7)")
        print("=" * 72)
        print(f"  Vanilla RRF: {van_mean:.4f}")
        print(f"  v5.0:        {v5_mean:.4f}")
        print(f"  MC4 (DKN):   {mc4_mean:.4f}")
        print(f"  MC4 vs Vanilla: {mc4_mean - van_mean:+.4f}")


if __name__ == '__main__':
    main()
