#!/usr/bin/env python3
"""PROBE 4: REF v2 — logistic alpha + coverage entropy. Test if multi-signal
regime detection unlocks strict Vanilla dominance."""
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, fuse_v4x, evaluate_ranking,
    paired_t_test,
)
from probe_regime_aware_fusion import (
    fuse_ref_v2, fuse_ref_score_mix, ensemble_regime_jaccard, coverage_entropy,
)


def eval_sweep(qrels, runs, subset, label, mu, tau, h_weight):
    runs_sel = {rn: runs[rn] for rn in subset}
    common = set(qrels.keys())
    for rn in subset:
        common &= set(runs_sel[rn].keys())

    pq = defaultdict(lambda: defaultdict(list))
    rhos, h_covs, alphas = [], [], []

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
            use_contrib_space=False, use_reliability_gate=False, use_per_doc_confidence=True,
        )
        for m, s in evaluate_ranking(rank_v5, qrel).items():
            pq['v5.0'][m].append(s)

        # REF v1 (winning baseline lo=0.35, hi=0.60)
        rank_v1, _, _ = fuse_ref_score_mix(lists, confs, sprs, lo=0.35, hi=0.60)
        for m, s in evaluate_ranking(rank_v1, qrel).items():
            pq['REF-v1'][m].append(s)

        # REF v2 with the swept params
        rank_v2, rho, h_cov, alpha = fuse_ref_v2(
            lists, confs, sprs, mu=mu, tau=tau, h_weight=h_weight,
        )
        rhos.append(rho)
        h_covs.append(h_cov)
        alphas.append(alpha)
        for m, s in evaluate_ranking(rank_v2, qrel).items():
            pq['REF-v2'][m].append(s)

    ndcg = {vn: statistics.mean(pq[vn]['NDCG@10']) for vn in ('Vanilla', 'v5.0', 'REF-v1', 'REF-v2')}
    mrr = {vn: statistics.mean(pq[vn]['MRR']) for vn in ('Vanilla', 'v5.0', 'REF-v1', 'REF-v2')}
    return ndcg, mrr, pq, statistics.mean(rhos), statistics.mean(h_covs), statistics.mean(alphas)


def main():
    qrels_2019 = parse_qrels('data/trec-dl-2019/2019qrels-pass.txt')
    runs_2019 = {}
    for rf in sorted(Path('data/trec-dl-2019/runs').glob('*.txt')):
        runs_2019[rf.stem] = parse_run_file(str(rf))
    qrels_2020 = parse_qrels('data/trec-dl-2020/2020qrels-pass.txt')
    runs_2020 = {}
    for rf in sorted(Path('data/trec-dl-2020/runs').glob('*.txt')):
        runs_2020[rf.stem] = parse_run_file(str(rf))

    sweeps_2019 = [
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet'], '19/n=4'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity'], '19/n=5'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity', 'tfidf_bigram'], '19/n=6'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity', 'tfidf_bigram', 'semantic_hash'], '19/n=7'),
    ]
    sweeps_2020 = [
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet'], '20/n=4'),
    ]

    param_configs = [
        (0.42, 0.08, 0.7,  "v2-default"),
        (0.42, 0.04, 0.7,  "sharper-tau"),
        (0.45, 0.04, 0.5,  "softer-h"),
        (0.42, 0.08, 1.0,  "full-h-weight"),
        (0.40, 0.06, 0.7,  "lower-mu"),
        (0.45, 0.08, 0.7,  "higher-mu"),
        (0.42, 0.04, 0.9,  "sharper-tau+stronger-h"),
    ]

    print(f"\n{'='*90}")
    print(f"  REF v2 parameter sweep (logistic alpha × coverage-entropy attenuation)")
    print(f"{'='*90}")
    print(f"  {'Config':<28} {'mu':>5} {'tau':>5} {'h_w':>4} {'mean Van':>9} {'mean v5':>9} {'mean v1':>9} {'mean v2':>9}")

    for (mu, tau, h_weight, name) in param_configs:
        ndcg_collected = {'Vanilla': [], 'v5.0': [], 'REF-v1': [], 'REF-v2': []}
        for subset, label in sweeps_2019 + sweeps_2020:
            collection_runs = runs_2019 if label.startswith('19') else runs_2020
            collection_qrels = qrels_2019 if label.startswith('19') else qrels_2020
            if not all(s in collection_runs for s in subset):
                continue
            ndcg, mrr, pq, rho, h_cov, alpha = eval_sweep(
                collection_qrels, collection_runs, subset, label,
                mu=mu, tau=tau, h_weight=h_weight,
            )
            for vn in ndcg_collected:
                ndcg_collected[vn].append(ndcg[vn])
        means = {vn: statistics.mean(ndcg_collected[vn]) for vn in ndcg_collected}
        print(f"  {name:<28} {mu:>5.2f} {tau:>5.2f} {h_weight:>4.2f} "
              f"{means['Vanilla']:>9.4f} {means['v5.0']:>9.4f} "
              f"{means['REF-v1']:>9.4f} {means['REF-v2']:>9.4f}")

    # Detailed view of v2-default per sweep
    print(f"\n{'='*90}")
    print(f"  Per-sweep detail for v2-default (mu=0.42, tau=0.08, h_weight=0.7)")
    print(f"{'='*90}")
    print(f"  {'Sweep':<10} {'rho':>6} {'h_cov':>6} {'alpha':>6} "
          f"{'Vanilla':>9} {'v5.0':>9} {'REF-v1':>9} {'REF-v2':>9}")
    for subset, label in sweeps_2019 + sweeps_2020:
        collection_runs = runs_2019 if label.startswith('19') else runs_2020
        collection_qrels = qrels_2019 if label.startswith('19') else qrels_2020
        if not all(s in collection_runs for s in subset):
            continue
        ndcg, mrr, pq, rho, h_cov, alpha = eval_sweep(
            collection_qrels, collection_runs, subset, label,
            mu=0.42, tau=0.08, h_weight=0.7,
        )
        print(f"  {label:<10} {rho:>6.3f} {h_cov:>6.3f} {alpha:>6.3f} "
              f"{ndcg['Vanilla']:>9.4f} {ndcg['v5.0']:>9.4f} "
              f"{ndcg['REF-v1']:>9.4f} {ndcg['REF-v2']:>9.4f}")

        # Stat test: REF-v2 vs Vanilla on NDCG@10
        t, p = paired_t_test(pq['REF-v2']['NDCG@10'], pq['Vanilla']['NDCG@10'])
        delta_van = statistics.mean(pq['REF-v2']['NDCG@10']) - statistics.mean(pq['Vanilla']['NDCG@10'])
        sig_van = '**' if p < 0.01 else ('*' if p < 0.05 else '')
        t2, p2 = paired_t_test(pq['REF-v2']['NDCG@10'], pq['v5.0']['NDCG@10'])
        delta_v5 = statistics.mean(pq['REF-v2']['NDCG@10']) - statistics.mean(pq['v5.0']['NDCG@10'])
        sig_v5 = '**' if p2 < 0.01 else ('*' if p2 < 0.05 else '')
        print(f"    REF-v2 vs Van: {delta_van:+.4f} (p={p:.3f} {sig_van})   "
              f"vs v5: {delta_v5:+.4f} (p={p2:.3f} {sig_v5})")


if __name__ == '__main__':
    main()
