#!/usr/bin/env python3
"""
PROBE 6: Per-query selector rules.

Test simple if-then routing rules that pick v5 vs Vanilla per-query
based on the cross-collection-consistent features. Compare to oracle.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import parse_run_file, parse_qrels
from probe_per_query_diagnosis import diagnose_collection


def apply_rule(per_query, rule_fn):
    """Apply a per-query rule and compute mean NDCG@10."""
    chosen = []
    for q in per_query:
        if rule_fn(q):
            chosen.append(q['v5_ndcg'])
        else:
            chosen.append(q['van_ndcg'])
    return statistics.mean(chosen)


def rule_always_v5(q):
    return True


def rule_always_van(q):
    return False


def rule_rho(q, threshold):
    return q['rho'] > threshold


def rule_h_cov(q, threshold):
    return q['h_cov'] < threshold  # v5 when h_cov is LOW


def rule_score_gap(q, threshold):
    return q['max_score_gap'] < threshold  # v5 when score-gap is LOW


def rule_top1_spread(q, threshold):
    return q['top1_spread'] < threshold  # v5 when top1-spread is LOW


def rule_combined(q):
    # h_cov low AND top1_spread low -> use v5
    return q['h_cov'] < 0.89 and q['top1_spread'] < 45


def sweep_rule(per_query, rule_template, thresholds, name):
    print(f"  --- {name} ---")
    for t in thresholds:
        ndcg = apply_rule(per_query, lambda q, T=t: rule_template(q, T))
        print(f"    threshold={t:>6.2f}  -> NDCG@10 = {ndcg:.4f}")


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

    print("\n\n" + "="*80)
    print("  PER-QUERY SELECTOR RULES — TREC DL 2019 n=4")
    print("="*80)
    print(f"  Always v5         : {apply_rule(pq_2019, rule_always_v5):.4f}")
    print(f"  Always Vanilla    : {apply_rule(pq_2019, rule_always_van):.4f}")
    print(f"  Oracle (per-query): {statistics.mean([max(q['v5_ndcg'], q['van_ndcg']) for q in pq_2019]):.4f}")
    print()
    sweep_rule(pq_2019, rule_rho, [0.35, 0.40, 0.45, 0.50, 0.55], "rho > T (v5 when homogeneous)")
    sweep_rule(pq_2019, rule_h_cov, [0.85, 0.87, 0.89, 0.91, 0.93], "h_cov < T (v5 when LOW)")
    sweep_rule(pq_2019, rule_score_gap, [6, 8, 10, 12, 14], "max_score_gap < T (v5 when LOW)")
    sweep_rule(pq_2019, rule_top1_spread, [30, 40, 50, 60, 70], "top1_spread < T (v5 when LOW)")
    print(f"\n  Combined h_cov<0.89 AND top1_spread<45 : "
          f"{apply_rule(pq_2019, rule_combined):.4f}")

    print("\n\n" + "="*80)
    print("  PER-QUERY SELECTOR RULES — TREC DL 2020 n=4")
    print("="*80)
    print(f"  Always v5         : {apply_rule(pq_2020, rule_always_v5):.4f}")
    print(f"  Always Vanilla    : {apply_rule(pq_2020, rule_always_van):.4f}")
    print(f"  Oracle (per-query): {statistics.mean([max(q['v5_ndcg'], q['van_ndcg']) for q in pq_2020]):.4f}")
    print()
    sweep_rule(pq_2020, rule_rho, [0.35, 0.40, 0.45, 0.50, 0.55], "rho > T")
    sweep_rule(pq_2020, rule_h_cov, [0.85, 0.87, 0.89, 0.91, 0.93], "h_cov < T")
    sweep_rule(pq_2020, rule_score_gap, [6, 8, 10, 12, 14], "max_score_gap < T")
    sweep_rule(pq_2020, rule_top1_spread, [30, 40, 50, 60, 70], "top1_spread < T")
    print(f"\n  Combined h_cov<0.89 AND top1_spread<45 : "
          f"{apply_rule(pq_2020, rule_combined):.4f}")


if __name__ == '__main__':
    main()
