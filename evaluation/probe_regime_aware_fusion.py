#!/usr/bin/env python3
"""
PROBE: Regime-Aware Fusion (REF)

Stream session 2026-05-13-001. Tests the hypothesis that the optimal fusion
strategy depends on the ensemble's regime (homogeneous vs heterogeneous), and
that a regime-detector mixing v5.0 + Vanilla beats either alone on average.

No new training data. No learned parameters. Three-line core idea:
  1. Diagnose regime from rank-statistics alone (mean pairwise top-K Jaccard)
  2. Mix v5.0 and Vanilla scores by an alpha derived from regime
  3. Compare per-ranker-count to v5.0 and Vanilla in isolation
"""
import argparse
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from trec_eval_harness import (
    parse_run_file, parse_qrels, runs_to_ranked_lists,
    _rrf_scores, _rank_from_scores, _jaccard,
    fuse_vanilla_rrf, fuse_v4x, evaluate_ranking, bootstrap_ci,
)


def ensemble_regime_jaccard(lists, K=30):
    """
    Mean pairwise top-K Jaccard across the ranker lists.
    1.0 = perfectly homogeneous (rankers agree); 0.0 = fully diverse.
    """
    R = len(lists)
    if R < 2:
        return 1.0
    top_sets = [set(L[:K]) for L in lists]
    total = 0.0
    cnt = 0
    for i in range(R):
        for j in range(i + 1, R):
            total += _jaccard(top_sets[i], top_sets[j])
            cnt += 1
    return total / max(cnt, 1)


def regime_alpha(rho, lo=0.25, hi=0.55):
    """
    Map mean pairwise Jaccard rho -> mixing weight alpha in [0, 1].
    rho >= hi: alpha = 1 (homogeneous, use v5.0)
    rho <= lo: alpha = 0 (heterogeneous, use Vanilla)
    Linear in between. Three parameters total (lo, hi implicit; alpha derived).
    """
    if rho >= hi:
        return 1.0
    if rho <= lo:
        return 0.0
    return (rho - lo) / (hi - lo)


def _normalize_scores(scores):
    """Min-max normalize a score dict to [0,1]. Preserves rank order."""
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    rng = hi - lo
    if rng < 1e-12:
        return {d: 1.0 for d in scores}
    return {d: (v - lo) / rng for d, v in scores.items()}


def fuse_ref(lists, confidences, scores_per_ranker, k=60, lo=0.25, hi=0.55):
    """
    Regime-Aware Fusion. Mixes v5.0 (v4.0+Ref3) scores with Vanilla RRF scores
    based on the ensemble's homogeneity regime.
    """
    rho = ensemble_regime_jaccard(lists, K=30)
    alpha = regime_alpha(rho, lo=lo, hi=hi)

    vanilla_scores = _rrf_scores(lists, k=k)

    # v5.0 = v4.0+Ref3: per-document confidence with the contrib-space/reliability
    # gates OFF (as in the spec)
    v5_rank, _, _, _ = fuse_v4x(
        lists, confidences, scores_per_ranker,
        k=k,
        use_contrib_space=False,
        use_reliability_gate=False,
        use_per_doc_confidence=True,
    )
    # Reconstruct v5.0 scores from rank by re-running the engine and pulling
    # the internal Final dict — but fuse_v4x doesn't expose it. Cheaper path:
    # re-derive a positional score from the v5 ranking (1/(rank+1)) and mix.
    v5_scores = {d: 1.0 / (i + 1) for i, d in enumerate(v5_rank)}

    # Min-max normalize both so the mixture is meaningful
    v5_norm = _normalize_scores(v5_scores)
    van_norm = _normalize_scores(vanilla_scores)

    all_docs = set(v5_norm) | set(van_norm)
    final = {}
    for d in all_docs:
        final[d] = alpha * v5_norm.get(d, 0.0) + (1.0 - alpha) * van_norm.get(d, 0.0)

    return _rank_from_scores(final), rho, alpha


def coverage_entropy(lists, K=100):
    """
    Normalized entropy of the coverage histogram (how many rankers retrieve
    each doc in the union of top-K). High = many specialist docs (heterogeneous);
    low = most docs retrieved by all rankers (homogeneous).
    Returns [0, 1].
    """
    import math
    R = len(lists)
    if R < 2:
        return 0.0
    seen = defaultdict(int)
    for L in lists:
        for d in L[:K]:
            seen[d] += 1
    # histogram over coverage counts 1..R
    hist = [0] * R
    for c in seen.values():
        hist[c - 1] += 1
    total = sum(hist)
    if total == 0:
        return 0.0
    H = 0.0
    for h in hist:
        if h > 0:
            p = h / total
            H -= p * math.log(p)
    return H / math.log(R)  # normalize to [0,1]


def sigmoid(x):
    import math
    return 1.0 / (1.0 + math.exp(-x))


def regime_alpha_v2(rho, h_cov, mu=0.42, tau=0.08, h_weight=0.7):
    """
    Logistic on rho, attenuated by coverage entropy.
    rho >> mu: alpha -> 1; rho << mu: alpha -> 0
    h_cov high (heterogeneous coverage) further suppresses alpha.
    """
    base = sigmoid((rho - mu) / tau)
    # h_cov in [0,1]; high h_cov should reduce alpha
    return base * (1.0 - h_weight * h_cov)


def fuse_ref_v2(lists, confidences, scores_per_ranker, k=60,
                mu=0.42, tau=0.08, h_weight=0.7):
    """REF v2: logistic alpha + coverage-entropy attenuation."""
    rho = ensemble_regime_jaccard(lists, K=30)
    h_cov = coverage_entropy(lists, K=100)
    alpha = regime_alpha_v2(rho, h_cov, mu=mu, tau=tau, h_weight=h_weight)

    vanilla_scores = _rrf_scores(lists, k=k)
    vanilla_rank = _rank_from_scores(vanilla_scores)
    v5_rank, _, _, _ = fuse_v4x(
        lists, confidences, scores_per_ranker,
        k=k, use_contrib_space=False, use_reliability_gate=False,
        use_per_doc_confidence=True,
    )

    import math
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

    return _rank_from_scores(final), rho, h_cov, alpha


def fuse_ref_score_mix(lists, confidences, scores_per_ranker, k=60, lo=0.25, hi=0.55):
    """
    Variant of REF: instead of mixing v5's positional re-score with vanilla,
    mix vanilla scores with vanilla scores TIMES v5's per-document confidence
    modulation. This is closer to v5's actual algebra and avoids the rank->score
    information loss of fuse_ref.

    Strategy: compute the per-document v5-vs-vanilla rank delta. Positive delta
    (v5 ranks doc higher than vanilla) = v5 sees something vanilla doesn't.
    Apply that delta scaled by alpha as a multiplicative modulation on vanilla.
    """
    rho = ensemble_regime_jaccard(lists, K=30)
    alpha = regime_alpha(rho, lo=lo, hi=hi)

    vanilla_scores = _rrf_scores(lists, k=k)
    vanilla_rank = _rank_from_scores(vanilla_scores)

    v5_rank, _, _, _ = fuse_v4x(
        lists, confidences, scores_per_ranker,
        k=k,
        use_contrib_space=False,
        use_reliability_gate=False,
        use_per_doc_confidence=True,
    )

    van_pos = {d: i for i, d in enumerate(vanilla_rank)}
    v5_pos = {d: i for i, d in enumerate(v5_rank)}

    # delta_d = van_pos - v5_pos. Positive = v5 promoted the doc above vanilla.
    # Use a log-scaled signed modulation, scaled by alpha.
    import math
    final = {}
    for d, v in vanilla_scores.items():
        vp = van_pos.get(d, 1000)
        v5p = v5_pos.get(d, 1000)
        delta = vp - v5p  # positive if v5 ranks doc higher than vanilla
        # Bound and log-compress; alpha controls how aggressively we trust v5
        if delta > 0:
            mod = 1.0 + alpha * math.log1p(delta) * 0.10
        else:
            mod = 1.0 + alpha * (-math.log1p(-delta)) * 0.05  # softer down-mod
        final[d] = v * mod

    return _rank_from_scores(final), rho, alpha


def evaluate_subset(qrels, runs, run_subset, label, verbose=False):
    """Evaluate Vanilla, v5.0, REF, REF-mix on the given ranker subset."""
    runs_sel = {rn: runs[rn] for rn in run_subset}
    common = set(qrels.keys())
    for rn in run_subset:
        common &= set(runs_sel[rn].keys())

    scores = defaultdict(lambda: defaultdict(list))
    rho_values = []
    alpha_values = []

    for qid in sorted(common):
        lists, confidences, scores_per_ranker = runs_to_ranked_lists(runs_sel, qid)
        if len(lists) < 2:
            continue
        qrel = qrels[qid]
        if not any(v > 0 for v in qrel.values()):
            continue

        # Vanilla
        rank_v = fuse_vanilla_rrf(lists)
        for m, s in evaluate_ranking(rank_v, qrel).items():
            scores['Vanilla'][m].append(s)

        # v5.0 (v4.0+Ref3)
        rank_v5, _, _, _ = fuse_v4x(
            lists, confidences, scores_per_ranker,
            use_contrib_space=False, use_reliability_gate=False,
            use_per_doc_confidence=True,
        )
        for m, s in evaluate_ranking(rank_v5, qrel).items():
            scores['v5.0'][m].append(s)

        # REF (positional-mix variant)
        rank_ref, rho, alpha = fuse_ref(lists, confidences, scores_per_ranker)
        rho_values.append(rho)
        alpha_values.append(alpha)
        for m, s in evaluate_ranking(rank_ref, qrel).items():
            scores['REF-pos'][m].append(s)

        # REF (multiplicative-modulation variant)
        rank_ref2, _, _ = fuse_ref_score_mix(lists, confidences, scores_per_ranker)
        for m, s in evaluate_ranking(rank_ref2, qrel).items():
            scores['REF-mod'][m].append(s)

    print(f"\n=== {label} (n_rankers={len(run_subset)}, {len(scores['Vanilla']['NDCG@10'])} queries) ===")
    print(f"  Regime signal: mean rho = {statistics.mean(rho_values):.3f}  "
          f"mean alpha = {statistics.mean(alpha_values):.3f}")
    print(f"  {'Variant':<10} {'NDCG@10':>10} {'NDCG@20':>10} {'MAP@100':>10} {'MRR':>10}")
    for vn in ('Vanilla', 'v5.0', 'REF-pos', 'REF-mod'):
        row = scores[vn]
        line = f"  {vn:<10}"
        for m in ('NDCG@10', 'NDCG@20', 'MAP@100', 'MRR'):
            line += f" {statistics.mean(row[m]):>10.4f}"
        print(line)
    return scores, statistics.mean(rho_values), statistics.mean(alpha_values)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--qrels', default='data/trec-dl-2019/2019qrels-pass.txt')
    ap.add_argument('--run-dir', default='data/trec-dl-2019/runs')
    args = ap.parse_args()

    print("Loading qrels...")
    qrels = parse_qrels(args.qrels)
    print(f"  {len(qrels)} queries with judgments")

    print("Loading run files...")
    run_dir = Path(args.run_dir)
    runs = {}
    for rf in sorted(run_dir.glob('*.txt')):
        runs[rf.stem] = parse_run_file(str(rf))
        print(f"  {rf.stem}: {len(runs[rf.stem])} queries")

    # The progressively-additive sweeps
    sweeps = [
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet'], 'n=4 lexical-core'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity'], 'n=5 +proximity'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity', 'tfidf_bigram'], 'n=6 +bigram'),
        (['bm25', 'bm25_tuned', 'tfidf', 'ql_dirichlet', 'proximity', 'tfidf_bigram', 'semantic_hash'], 'n=7 +semhash'),
    ]

    all_ndcg = {'Vanilla': [], 'v5.0': [], 'REF-pos': [], 'REF-mod': []}
    for subset, label in sweeps:
        # Only use subsets where all rankers loaded
        if not all(s in runs for s in subset):
            print(f"\nSkipping {label}: missing rankers")
            continue
        scores, _, _ = evaluate_subset(qrels, runs, subset, label)
        for vn in all_ndcg:
            all_ndcg[vn].append(statistics.mean(scores[vn]['NDCG@10']))

    print("\n=== Cross-ensemble summary (NDCG@10) ===")
    print(f"  {'Variant':<10} {'n=4':>8} {'n=5':>8} {'n=6':>8} {'n=7':>8} {'mean':>8}")
    for vn in ('Vanilla', 'v5.0', 'REF-pos', 'REF-mod'):
        ndcgs = all_ndcg[vn]
        line = f"  {vn:<10}"
        for v in ndcgs:
            line += f" {v:>8.4f}"
        line += f" {statistics.mean(ndcgs):>8.4f}"
        print(line)

    # Probe 2: tuned regime curves
    print("\n\n=== Probe 2: alpha-curve sweep (sharper thresholds) ===")
    print("Goal: push alpha to 0 faster in heterogeneous regimes so REF-mod = Vanilla there.")
    curve_sweeps = [
        (0.25, 0.55, "current (baseline)"),
        (0.40, 0.55, "lo=0.40 (predicted optimum)"),
        (0.45, 0.55, "lo=0.45 (sharper)"),
        (0.40, 0.50, "lo=0.40 hi=0.50 (narrow band)"),
        (0.35, 0.60, "wider band, biased toward vanilla"),
    ]
    for lo_p, hi_p, label in curve_sweeps:
        print(f"\n--- {label} (lo={lo_p}, hi={hi_p}) ---")
        ref_mod_ndcg = []
        for subset, slabel in sweeps:
            if not all(s in runs for s in subset):
                continue
            runs_sel = {rn: runs[rn] for rn in subset}
            common = set(qrels.keys())
            for rn in subset:
                common &= set(runs_sel[rn].keys())
            ndcg_list = []
            alpha_list = []
            for qid in sorted(common):
                lists, confs, sprs = runs_to_ranked_lists(runs_sel, qid)
                if len(lists) < 2:
                    continue
                qrel = qrels[qid]
                if not any(v > 0 for v in qrel.values()):
                    continue
                rank, _, alpha = fuse_ref_score_mix(lists, confs, sprs, lo=lo_p, hi=hi_p)
                alpha_list.append(alpha)
                ndcg_list.append(evaluate_ranking(rank, qrel)['NDCG@10'])
            mean_ndcg = statistics.mean(ndcg_list)
            mean_alpha = statistics.mean(alpha_list)
            print(f"  {slabel:<18} alpha={mean_alpha:.3f}  REF-mod NDCG@10 = {mean_ndcg:.4f}")
            ref_mod_ndcg.append(mean_ndcg)
        print(f"  --> mean REF-mod NDCG@10 across n=4..7 = {statistics.mean(ref_mod_ndcg):.4f}")


if __name__ == '__main__':
    main()
