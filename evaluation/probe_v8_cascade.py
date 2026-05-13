#!/usr/bin/env python3
"""
PROBE 19: v8.0-cascade — binary PQAS + v6 REF fallback on low confidence.

Architecture:
- Train binary classifier (Vanilla vs v5), same as v7
- At inference: if classifier confidence is HIGH, use the binary prediction
- If classifier confidence is LOW (probability near 0.5), use v6 REF as fallback

Rationale: v6 REF is structurally a smooth interpolation between v5 and
Vanilla. It is the right routing target precisely when the binary decision
is ambiguous.
"""
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    fuse_vanilla_rrf, fuse_v4x, evaluate_ranking,
    paired_t_test, bootstrap_ci,
)
from probe_per_query_diagnosis import diagnose_collection
from probe_pqas_supervised import (
    FEATURE_KEYS, standardize, sigmoid,
    train_lr, predict, make_labels,
)
from probe_regime_aware_fusion import fuse_ref_score_mix


def compute_3_ndcgs(per_query, runs, subset, qrels):
    runs_sel = {rn: runs[rn] for rn in subset}
    out = []
    for q in per_query:
        qid = q['qid']
        lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
        qrel = qrels[qid]
        van = evaluate_ranking(fuse_vanilla_rrf(lists), qrel)['NDCG@10']
        v5r, _, _, _ = fuse_v4x(
            lists, confs, sprs,
            use_contrib_space=False, use_reliability_gate=False,
            use_per_doc_confidence=True,
        )
        v5 = evaluate_ranking(v5r, qrel)['NDCG@10']
        v6r, _, _ = fuse_ref_score_mix(lists, confs, sprs, lo=0.35, hi=0.60)
        v6 = evaluate_ranking(v6r, qrel)['NDCG@10']
        out.append({'Vanilla': van, 'v5': v5, 'v6': v6, 'qid': qid})
    return out


def kfold_cascade(pq, ndcg_per_q, l2=0.30, lo_th=0.35, hi_th=0.65,
                   k_folds=5, seeds=(42, 123, 7, 2024, 99)):
    """
    Cascade: binary LR predicts p_v5. If lo_th < p_v5 < hi_th, route to v6 REF.
    Else route based on p_v5 > 0.5.
    """
    n = len(pq)
    seed_per_query = []
    for seed in seeds:
        random.seed(seed)
        idx = list(range(n))
        random.shuffle(idx)
        fs = n // k_folds
        per_q = [None] * n
        for fi in range(k_folds):
            test_i = idx[fi*fs:(fi+1)*fs] if fi < k_folds-1 else idx[fi*fs:]
            train_i = [i for i in idx if i not in set(test_i)]
            train = [pq[i] for i in train_i]
            test = [pq[i] for i in test_i]
            X_tr, mu, sd = standardize(train)
            X_te, _, _ = standardize(test, mu, sd)
            y_tr = make_labels(train)
            w, b = train_lr(X_tr, y_tr, lr=0.05, l2=l2, epochs=2000)
            probs = predict(X_te, w, b)
            for j, ti in enumerate(test_i):
                p = probs[j]
                if lo_th < p < hi_th:
                    per_q[ti] = ndcg_per_q[ti]['v6']
                elif p > 0.5:
                    per_q[ti] = ndcg_per_q[ti]['v5']
                else:
                    per_q[ti] = ndcg_per_q[ti]['Vanilla']
        seed_per_query.append(per_q)
    return [statistics.mean(s[i] for s in seed_per_query) for i in range(n)]


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
        print(f"  v8.0-cascade — {label}")
        print(f"{'='*80}")
        pq, _ = diagnose_collection(qrels, runs, subset, label)
        ndcg = compute_3_ndcgs(pq, runs, subset, qrels)

        van = statistics.mean(q['Vanilla'] for q in ndcg)
        v5 = statistics.mean(q['v5'] for q in ndcg)
        v6 = statistics.mean(q['v6'] for q in ndcg)
        oracle3 = statistics.mean(max(q['Vanilla'], q['v5'], q['v6']) for q in ndcg)

        print(f"\n  Reference: Vanilla={van:.4f}  v5={v5:.4f}  v6={v6:.4f}  3-class oracle={oracle3:.4f}")

        # Sweep cascade threshold and l2
        print(f"\n  Cascade threshold band [lo_th, hi_th] sweep:")
        best = None
        for l2 in [0.10, 0.30, 1.0]:
            for lo_th, hi_th in [(0.35, 0.65), (0.40, 0.60), (0.45, 0.55), (0.30, 0.70), (0.25, 0.75)]:
                per_q = kfold_cascade(pq, ndcg, l2=l2, lo_th=lo_th, hi_th=hi_th)
                m = statistics.mean(per_q)
                if best is None or m > best[0]:
                    best = (m, l2, lo_th, hi_th, per_q)
                print(f"    l2={l2:>4.2f} band=[{lo_th},{hi_th}] -> NDCG@10 = {m:.4f}")
        print(f"\n  BEST: NDCG@10 = {best[0]:.4f}  (l2={best[1]}, band=[{best[2]},{best[3]}])")

        v8c_per_q = best[4]
        lo_ci, hi_ci = bootstrap_ci(v8c_per_q)
        print(f"  95% CI: {lo_ci:.3f}-{hi_ci:.3f}")

        van_per_q = [q['Vanilla'] for q in ndcg]
        v5_per_q = [q['v5'] for q in ndcg]
        v6_per_q = [q['v6'] for q in ndcg]

        for name, pq2 in [('Vanilla', van_per_q), ('v5.0', v5_per_q), ('v6.0 REF', v6_per_q)]:
            t, p = paired_t_test(v8c_per_q, pq2)
            d = best[0] - statistics.mean(pq2)
            sig = '**' if p < 0.01 else ('*' if p < 0.05 else 'ns')
            print(f"    v8-cascade vs {name:<10}: delta={d:+.4f}  p={p:.4f}  {sig}")


if __name__ == '__main__':
    main()
