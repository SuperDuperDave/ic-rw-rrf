#!/usr/bin/env python3
"""
PROBE 4: Aggregation-Operator Landscape — closing the basin map

Session 2026-05-13-002, Probe 4.

Probes 1-3 showed Vanilla RRF sits near a remarkable peak in the label-free
family. Each alternative we tested fails for a structurally diagnosable reason:
MC4 fails under ranker disagreement; score-aware fails on coverage interactions;
empirical f(r) fails by naive-Bayes overcounting of correlated rankers.

One axis is still unmapped: AGGREGATION OPERATOR. RRF uses SUM. The other
classical options are MAX, MEDIAN, GEOMETRIC-MEAN, RANK-PRODUCT. Keeping
RRF's decay function `1/(60+k)` fixed, this probe asks: is the basin's
peak also robust to changes in aggregation operator?

This is the final diagnostic before crystallization. After this we will have
mapped four dimensions around Vanilla RRF:
  - Decay function alternatives (Probe 3: empirical f(r))
  - Information modality (Probe 2: score-aware)
  - Aggregation paradigm (Probe 1: Markov chain stationary distribution)
  - Aggregation operator (Probe 4: this probe)

Plus the smoothing constant k-sweep: is k=60 itself near-optimal?
"""
import argparse
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, evaluate_ranking, paired_t_test,
)


def _rrf_term(rank, k_smooth=60):
    return 1.0 / (k_smooth + rank)


def fuse_with_operator(lists, op='sum', k_smooth=60):
    """Fuse using RRF's 1/(k+rank) decay but with the specified aggregation operator.

    For missing rankers, contribute nothing (skip from the aggregation list).
    """
    rank_of = [{d: i for i, d in enumerate(L)} for L in lists]
    all_docs = set()
    for L in lists:
        all_docs.update(L)

    final = {}
    for d in all_docs:
        contribs = []
        for r_lookup in rank_of:
            if d in r_lookup:
                contribs.append(_rrf_term(r_lookup[d], k_smooth=k_smooth))
        if not contribs:
            final[d] = 0.0
            continue
        if op == 'sum':
            final[d] = sum(contribs)
        elif op == 'max':
            final[d] = max(contribs)
        elif op == 'median':
            final[d] = statistics.median(contribs)
        elif op == 'geomean':
            prod = 1.0
            for v in contribs:
                prod *= v
            final[d] = prod ** (1.0 / len(contribs))
        elif op == 'rank_prod':
            # Use rank-product: smaller is better, so score = -log(prod_r(rank+1))
            # We want larger=better, so negative log.
            lp = 0.0
            for r_lookup in rank_of:
                if d in r_lookup:
                    lp += math.log(r_lookup[d] + 1)
            final[d] = -lp
        elif op == 'harmonic':
            # Harmonic mean of contribs (penalizes worst ranker most)
            inv_sum = sum(1.0 / c for c in contribs)
            final[d] = len(contribs) / inv_sum if inv_sum > 0 else 0.0
        elif op == 'sum_normalized':
            # Sum normalized by sqrt(coverage) — between SUM (M weight) and MEAN (1 weight)
            final[d] = sum(contribs) / math.sqrt(len(contribs))
        else:
            raise ValueError(f"Unknown op: {op}")
    return sorted(final, key=lambda d: (-final[d], d))


def eval_per_query(qids, runs, qrels, fusion_fn):
    out = []
    for qid in qids:
        if qid not in qrels:
            continue
        lists, _, _ = runs_to_ranked_lists(runs, qid)
        if len(lists) < 2:
            continue
        ranked = fusion_fn(lists)
        m = evaluate_ranking(ranked, qrels[qid])
        out.append(m['NDCG@10'])
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-2019', default='data/trec-dl-2019')
    parser.add_argument('--data-2020', default='data/trec-dl-2020')
    args = parser.parse_args()

    runs_2019 = {p.name: parse_run_file(str(p))
                  for p in sorted((Path(args.data_2019) / 'runs').glob('*.txt'))}
    qrels_2019 = parse_qrels(str(Path(args.data_2019) / '2019qrels-pass.txt'))
    runs_2020 = {p.name: parse_run_file(str(p))
                  for p in sorted((Path(args.data_2020) / 'runs').glob('*.txt'))}
    qrels_2020 = parse_qrels(str(Path(args.data_2020) / '2020qrels-pass.txt'))

    print("=" * 78)
    print("PROBE 4: AGGREGATION-OPERATOR LANDSCAPE")
    print("=" * 78)

    base4 = ['bm25.txt', 'bm25_tuned.txt', 'ql_dirichlet.txt', 'tfidf.txt']
    ens_19 = [
        ('n=4', base4),
        ('n=5', base4 + ['proximity.txt']),
        ('n=6', base4 + ['proximity.txt', 'tfidf_bigram.txt']),
        ('n=7', base4 + ['proximity.txt', 'tfidf_bigram.txt', 'semantic_hash.txt']),
    ]
    ens_20 = [('n=4', base4)]

    operators = ['sum', 'max', 'median', 'geomean', 'rank_prod', 'harmonic', 'sum_normalized']

    # === Part 1: aggregation operator sweep (k_smooth=60 fixed) ===
    print("\n" + "=" * 78)
    print("PART 1 — Aggregation operators with RRF decay 1/(60+k)")
    print("=" * 78)

    results = {}  # results[collection][ens_name][op] = mean NDCG@10
    for collection, runs, qrels, ens in [
        ('TREC DL 2019', runs_2019, qrels_2019, ens_19),
        ('TREC DL 2020', runs_2020, qrels_2020, ens_20),
    ]:
        results[collection] = {}
        for ens_name, ens_files in ens:
            runs_sub = {f: runs[f] for f in ens_files if f in runs}
            if len(runs_sub) != len(ens_files):
                continue
            qids = sorted(qrels.keys())
            results[collection][ens_name] = {}
            for op in operators:
                scores = eval_per_query(qids, runs_sub, qrels,
                                          lambda L, _op=op: fuse_with_operator(L, op=_op, k_smooth=60))
                results[collection][ens_name][op] = (statistics.mean(scores), scores)

    # Print
    header = f"\n{'Collection / Ensemble':<22}" + "".join(f"{op:>16}" for op in operators)
    print(header)
    print("-" * len(header))
    for collection in ['TREC DL 2019', 'TREC DL 2020']:
        for ens_name, _ in ens_19 if collection == 'TREC DL 2019' else ens_20:
            if ens_name not in results[collection]:
                continue
            row = f"{collection[-4:]} {ens_name:<16}"
            for op in operators:
                mean_, _ = results[collection][ens_name][op]
                row += f"{mean_:>16.4f}"
            print(row)

    # Cross-ensemble mean for 2019
    print("\nCross-ensemble mean TREC DL 2019:")
    for op in operators:
        m = statistics.mean([results['TREC DL 2019'][e][op][0] for e, _ in ens_19])
        sum_m = statistics.mean([results['TREC DL 2019'][e]['sum'][0] for e, _ in ens_19])
        delta = m - sum_m
        print(f"  {op:<18}  NDCG@10 = {m:.4f}   vs SUM (Vanilla RRF) = {delta:+.4f}")

    # Significance tests on 2019 cross-ensemble (concat per-query lists across all ensembles)
    print("\nSignificance vs SUM (Vanilla RRF) — concatenated 2019 per-query NDCG@10:")
    sum_all = []
    for e, _ in ens_19:
        sum_all.extend(results['TREC DL 2019'][e]['sum'][1])
    for op in operators:
        if op == 'sum':
            continue
        op_all = []
        for e, _ in ens_19:
            op_all.extend(results['TREC DL 2019'][e][op][1])
        _t, p = paired_t_test(op_all, sum_all)
        m_op = statistics.mean(op_all); m_sum = statistics.mean(sum_all)
        sig = '**' if p < 0.01 else ('*' if p < 0.05 else 'ns')
        print(f"  {op:<18}  delta = {m_op - m_sum:+.4f}    p = {p:.4f}  {sig}")

    # === Part 2: smoothing constant k sweep with SUM ===
    print("\n" + "=" * 78)
    print("PART 2 — Smoothing constant k sweep (SUM aggregation)")
    print("=" * 78)

    k_values = [0.5, 1, 5, 10, 30, 60, 100, 200, 500, 1000]
    print(f"\n{'Collection / Ensemble':<22}" + "".join(f"{f'k={k}':>10}" for k in k_values))
    print("-" * (22 + len(k_values) * 10))

    k_results = {}
    for collection, runs, qrels, ens in [
        ('TREC DL 2019', runs_2019, qrels_2019, ens_19),
        ('TREC DL 2020', runs_2020, qrels_2020, ens_20),
    ]:
        k_results[collection] = {}
        for ens_name, ens_files in ens:
            runs_sub = {f: runs[f] for f in ens_files if f in runs}
            if len(runs_sub) != len(ens_files):
                continue
            qids = sorted(qrels.keys())
            row = f"{collection[-4:]} {ens_name:<16}"
            k_results[collection][ens_name] = {}
            for k in k_values:
                scores = eval_per_query(qids, runs_sub, qrels,
                                          lambda L, _k=k: fuse_with_operator(L, op='sum', k_smooth=_k))
                m = statistics.mean(scores)
                k_results[collection][ens_name][k] = m
                row += f"{m:>10.4f}"
            print(row)

    # Find best k for each ensemble
    print("\nBest smoothing constant k per ensemble (SUM aggregation):")
    for collection in ['TREC DL 2019', 'TREC DL 2020']:
        for ens_name in k_results[collection]:
            best_k = max(k_results[collection][ens_name].items(), key=lambda x: x[1])
            std_k_60 = k_results[collection][ens_name][60]
            print(f"  {collection} {ens_name}:  best k = {best_k[0]:>5} (NDCG@10 = {best_k[1]:.4f})   "
                  f"vs k=60: {std_k_60:.4f}  Δ = {best_k[1] - std_k_60:+.4f}")

    # Cross-ensemble mean for each k (2019)
    print("\nCross-ensemble mean — TREC DL 2019:")
    for k in k_values:
        m = statistics.mean([k_results['TREC DL 2019'][e][k] for e, _ in ens_19 if e in k_results['TREC DL 2019']])
        marker = "  <-- RRF default" if k == 60 else ""
        print(f"  k = {k:>5}:  NDCG@10 = {m:.4f}{marker}")


if __name__ == '__main__':
    main()
