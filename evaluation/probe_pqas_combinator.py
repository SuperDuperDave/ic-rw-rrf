#!/usr/bin/env python3
"""
PROBE 7: PQAS (Per-Query Adaptive Selector) — label-free multi-feature combinator.

Tests multi-feature rules that try to win on BOTH TREC DL 2019 and 2020
simultaneously. The oracle headroom is +0.0305 (2019) and +0.0325 (2020)
over the best fixed algorithm. Goal: capture meaningful fraction of both.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import parse_run_file, parse_qrels
from probe_per_query_diagnosis import diagnose_collection


def apply_rule(per_query, rule_fn):
    """Apply rule_fn(query_dict) -> bool; True = use v5, False = use Vanilla."""
    return statistics.mean(
        q['v5_ndcg'] if rule_fn(q) else q['van_ndcg']
        for q in per_query
    )


def safe_div(a, b):
    return a / b if b > 1e-12 else 0.0


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

    # Reference points
    print("\n\n" + "="*80)
    print("  REFERENCE POINTS (per-query mean NDCG@10)")
    print("="*80)
    for label, pq in [('2019 n=4', pq_2019), ('2020 n=4', pq_2020)]:
        van = statistics.mean([q['van_ndcg'] for q in pq])
        v5 = statistics.mean([q['v5_ndcg'] for q in pq])
        ora = statistics.mean([max(q['v5_ndcg'], q['van_ndcg']) for q in pq])
        print(f"  {label}: Vanilla={van:.4f}  v5={v5:.4f}  ORACLE={ora:.4f}  "
              f"best_fixed={max(van, v5):.4f}  headroom={ora-max(van,v5):+.4f}")

    # Rule sweep
    print("\n\n" + "="*80)
    print("  RULE SWEEP — looking for cross-collection generalization")
    print("="*80)
    print(f"  {'Rule':<55} {'2019':>8} {'2020':>8}  {'gain over best fixed'}")

    rules = []

    # R0 baselines
    rules.append(("Always v5", lambda q: True))
    rules.append(("Always Vanilla", lambda q: False))

    # R1: rho × score_gap gating
    for tr in [0.40, 0.45, 0.50]:
        for tg in [8.0, 10.0, 12.0]:
            rules.append((f"rho>{tr} AND max_gap<{tg}",
                          lambda q, R=tr, G=tg: q['rho'] > R and q['max_score_gap'] < G))

    # R2: h_cov (cross-collection-consistent direction)
    for th in [0.86, 0.88, 0.90]:
        rules.append((f"h_cov<{th}", lambda q, T=th: q['h_cov'] < T))

    # R3: combined h_cov AND rho
    for th in [0.86, 0.88]:
        for tr in [0.40, 0.45]:
            rules.append((f"h_cov<{th} AND rho>{tr}",
                          lambda q, H=th, R=tr: q['h_cov'] < H and q['rho'] > R))

    # R4: top1_spread (the 2020-winner) crossed with rho (the 2019-winner)
    for ts in [40, 50, 60]:
        for tr in [0.35, 0.40, 0.45]:
            rules.append((f"top1_spread<{ts} AND rho>{tr}",
                          lambda q, S=ts, R=tr: q['top1_spread'] < S and q['rho'] > R))
            rules.append((f"top1_spread<{ts} OR rho>{tr}",
                          lambda q, S=ts, R=tr: q['top1_spread'] < S or q['rho'] > R))

    # R5: multiplicative gating — all signals must agree
    # alpha ∈ [0,1]: high rho × low h_cov × low score_gap × low top1_spread
    def rule_multiplicative(q, threshold=0.30):
        rho_term = max(0.0, (q['rho'] - 0.25) / 0.30)         # 0 below rho=0.25, 1 above rho=0.55
        h_term = max(0.0, (0.92 - q['h_cov']) / 0.10)         # 0 above h=0.92, 1 below h=0.82
        gap_term = max(0.0, (15.0 - q['max_score_gap']) / 10.0)  # 0 above gap=15, 1 below gap=5
        score = rho_term * h_term * gap_term
        return score > threshold

    for thr in [0.10, 0.20, 0.30, 0.40]:
        rules.append((f"multiplicative score > {thr}",
                      lambda q, T=thr: rule_multiplicative(q, T)))

    # R6: weighted-vote derived signal (sums of normalized features)
    def rule_voting(q, threshold):
        rho_norm = (q['rho'] - 0.30) / 0.30
        h_norm = (0.90 - q['h_cov']) / 0.10
        gap_norm = (12.0 - q['max_score_gap']) / 8.0
        spread_norm = (50.0 - q['top1_spread']) / 30.0
        score = rho_norm + h_norm + 0.5 * gap_norm + 0.5 * spread_norm
        return score > threshold

    for thr in [0.0, 0.5, 1.0, 1.5]:
        rules.append((f"vote(rho+h+0.5*gap+0.5*spread) > {thr}",
                      lambda q, T=thr: rule_voting(q, T)))

    # Best-of fixed reference
    ref_2019 = max(statistics.mean([q['van_ndcg'] for q in pq_2019]),
                   statistics.mean([q['v5_ndcg'] for q in pq_2019]))
    ref_2020 = max(statistics.mean([q['van_ndcg'] for q in pq_2020]),
                   statistics.mean([q['v5_ndcg'] for q in pq_2020]))

    # Run and rank
    results = []
    for name, rule in rules:
        n19 = apply_rule(pq_2019, rule)
        n20 = apply_rule(pq_2020, rule)
        results.append((name, n19, n20, n19 - ref_2019, n20 - ref_2020))

    # Print sorted by sum of gains
    results.sort(key=lambda r: r[3] + r[4], reverse=True)
    print()
    for name, n19, n20, g19, g20 in results:
        marker = "  "
        if g19 > 0 and g20 > 0:
            marker = "**"  # wins on both
        elif g19 > 0 or g20 > 0:
            marker = " *"
        print(f"  {marker} {name:<55} {n19:>.4f} {n20:>.4f}  ({g19:+.4f}, {g20:+.4f})")

    print("\n  ** = wins on both collections vs best fixed")
    print("   * = wins on at least one")


if __name__ == '__main__':
    main()
