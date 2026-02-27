#!/usr/bin/env python3
"""
IC(R/W)-RRF v3.0 DGAF — Mechanism Aliveness Diagnostic
=======================================================

Tests whether per-document gating produces meaningful λ(d) variance
across documents within queries. This is the fundamental validation
that the gating mechanism is alive (discriminating) vs cosmetic (constant).

If λ(d) doesn't vary, the gate adds machinery to produce the same output
as v2.1's scalar λ. The mechanism is only alive if the gate discriminates.

Scenarios:
  1. Moderate disagreement — typical hybrid retrieval
  2. Specialist outlier — one ranker sees what others miss
  3. Cabal — 3 correlated + 1 independent
  4. Full agreement — gate should be inactive
  5. Full disagreement — gate should have max dynamic range

Measurements per scenario:
  - λ(d) distribution statistics (mean, std, quartiles, IQR)
  - Document type breakdown (consensus / disputed / specialist)
  - 3-signal vs 4-signal gate comparison
  - S(d)-floor guard effect
  - v2.1 scalar λ baseline reference

No external dependencies. Python 3.8+ standard library only.
"""

import math
import random
import statistics
from collections import defaultdict
from typing import List, Dict, Tuple, Optional


# ═══════════════════════════════════════════════════════════════
# SECTION 1: Core Utilities
# ═══════════════════════════════════════════════════════════════

def jaccard(a, b):
    a, b = set(a), set(b)
    inter = len(a & b)
    union = len(a | b)
    return inter / (union + 1e-12)


def topN_set(L, N):
    return set(L[:N])


def rrf_score_lists(lists, weights=None, k=60):
    score = defaultdict(float)
    R = len(lists)
    if weights is None:
        weights = [1.0 / R] * R
    for r, L in enumerate(lists):
        w = weights[r]
        for idx, d in enumerate(L):
            score[d] += w / (k + idx + 1)
    return dict(score)


def rank_from_scores(score_map):
    return [d for d, _ in sorted(score_map.items(),
                                  key=lambda x: x[1], reverse=True)]


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-20, min(20, x))))


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def softmax(xs, temp=1.0):
    if not xs:
        return []
    m = max(xs)
    exps = [math.exp((x - m) / temp) for x in xs]
    s = sum(exps) + 1e-12
    return [e / s for e in exps]


def percentile(data, pct):
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * pct / 100.0
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


# ═══════════════════════════════════════════════════════════════
# SECTION 2: v2.1 Backbone
# ═══════════════════════════════════════════════════════════════

def uniqueness_scores(lists, N=30):
    R = len(lists)
    top_sets = [topN_set(L, N) for L in lists]
    u = []
    for r in range(R):
        overlaps = [jaccard(top_sets[r], top_sets[s])
                     for s in range(R) if s != r]
        m = sum(overlaps) / (len(overlaps) + 1e-12)
        v = sum((x - m) ** 2 for x in overlaps) / (len(overlaps) + 1e-12)
        u.append(math.tanh(v / (m + 0.1)))
    return u


def disagreement_temperature(lists, N=30):
    R = len(lists)
    top_sets = [topN_set(L, N) for L in lists]
    tot, cnt = 0.0, 0
    for i in range(R):
        for j in range(i + 1, R):
            tot += 1.0 - jaccard(top_sets[i], top_sets[j])
            cnt += 1
    return tot / (cnt + 1e-12)


def v21_backbone(lists, k=60, N=30, iters=4,
                 alpha=1.2, beta=0.6, zeta=0.5,
                 wmin=0.05, wmax=0.65, specialists=2):
    """
    v2.1 Steps 0-2: iterative consensus weight refinement + specialist selection.
    Returns consensus field C(d), specialist field S(d), metadata.
    """
    R = len(lists)
    w = [1.0 / R] * R
    c = [0.5] * R  # neutral confidence (no internal scores available)
    u = uniqueness_scores(lists, N=N)

    # Iterative consensus
    for _ in range(iters):
        fused_scores = rrf_score_lists(lists, weights=w, k=k)
        fused_rank = rank_from_scores(fused_scores)
        fused_top = topN_set(fused_rank, N)

        a = [jaccard(topN_set(lists[r], N), fused_top) for r in range(R)]
        a_bar, c_bar, u_bar = sum(a) / R, sum(c) / R, sum(u) / R

        w_new = [w[r] * math.exp(
            alpha * (a[r] - a_bar) +
            beta * (c[r] - c_bar) +
            zeta * (u[r] - u_bar)
        ) for r in range(R)]
        w_new = [clip(x, wmin, wmax) for x in w_new]
        s = sum(w_new) + 1e-12
        w = [x / s for x in w_new]

    # Final consensus ranking
    C = rrf_score_lists(lists, weights=w, k=k)
    fused_rank = rank_from_scores(C)
    fused_top = topN_set(fused_rank, N)
    a = [jaccard(topN_set(lists[r], N), fused_top) for r in range(R)]

    # Leave-one-out influence
    influence = []
    for r in range(R):
        w_minus = [w[j] for j in range(R) if j != r]
        lists_minus = [lists[j] for j in range(R) if j != r]
        sm = sum(w_minus) + 1e-12
        w_minus = [x / sm for x in w_minus]
        fused_minus = rrf_score_lists(lists_minus, weights=w_minus, k=k)
        rank_minus = rank_from_scores(fused_minus)
        top_minus = topN_set(rank_minus, N)
        influence.append(1.0 - jaccard(fused_top, top_minus))

    # Specialist selection: confident × influential × dissenting × unique
    spec_scores = [c[r] * influence[r] * (1.0 - a[r]) * u[r] for r in range(R)]
    spec_idx = sorted(range(R), key=lambda r: spec_scores[r],
                       reverse=True)[:max(1, specialists)]
    spec_w_raw = [max(spec_scores[r], 1e-8) for r in spec_idx]
    spec_w = softmax(spec_w_raw, temp=0.7)

    # Specialist field
    S = defaultdict(float)
    for j, r in enumerate(spec_idx):
        for idx, d in enumerate(lists[r]):
            S[d] += spec_w[j] / (k + idx + 1)

    Tq = disagreement_temperature(lists, N=N)

    # v2.1 scalar lambda (for baseline comparison)
    lam_min, lam_max, p = 0.10, 0.55, 1.5
    scalar_lam = lam_min + (lam_max - lam_min) * (Tq ** p)

    return {
        'w': w, 'C': C, 'S': dict(S),
        'spec_idx': spec_idx, 'spec_scores': spec_scores,
        'Tq': Tq, 'consensus_rank': fused_rank,
        'a': a, 'u': u, 'influence': influence,
        'scalar_lam': scalar_lam,
    }


# ═══════════════════════════════════════════════════════════════
# SECTION 3: DGAF Per-Document Gating Layer
# ═══════════════════════════════════════════════════════════════

def compute_signals_3(lists, c_rank_map, s_rank_map, k=60, K=200):
    """3-signal: coverage, dispersion, lift."""
    R = len(lists)
    doc_ranks = defaultdict(dict)
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            doc_ranks[d][r] = idx

    signals = {}
    for d, ranks in doc_ranks.items():
        cov = len(ranks) / R

        rank_vals = list(ranks.values())
        if len(rank_vals) >= 2:
            mu = sum(rank_vals) / len(rank_vals)
            var = sum((x - mu) ** 2 for x in rank_vals) / len(rank_vals)
            disp = math.sqrt(var) / (mu + k)
        else:
            disp = 0.0

        c_r = c_rank_map.get(d, K)
        s_r = s_rank_map.get(d, K)
        lift = max(0.0, (c_r - s_r)) / K

        signals[d] = {'cov': cov, 'disp': disp, 'lift': lift}
    return signals


def compute_signals_4(lists, c_rank_map, s_rank_map, k=60, K=200):
    """4-signal: coverage, dispersion, lift, entropy."""
    R = len(lists)
    doc_ranks = defaultdict(dict)
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            doc_ranks[d][r] = idx

    signals = {}
    for d, ranks in doc_ranks.items():
        cov = len(ranks) / R

        rank_vals = list(ranks.values())
        if len(rank_vals) >= 2:
            mu = sum(rank_vals) / len(rank_vals)
            var = sum((x - mu) ** 2 for x in rank_vals) / len(rank_vals)
            disp = math.sqrt(var) / (mu + k)
        else:
            disp = 0.0

        c_r = c_rank_map.get(d, K)
        s_r = s_rank_map.get(d, K)
        lift = max(0.0, (c_r - s_r)) / K

        # Rank entropy
        p = [1.0 / (k + ranks[r] + 1) if r in ranks else 0.0
             for r in range(R)]
        p_sum = sum(p) + 1e-12
        q = [x / p_sum for x in p]
        ent = -sum(qi * math.log(qi + 1e-12) for qi in q if qi > 1e-12)
        ent_norm = ent / (math.log(R) + 1e-12)

        signals[d] = {'cov': cov, 'disp': disp, 'lift': lift, 'ent': ent_norm}
    return signals


def gate_3sig(signals, Tq, w_cov=1.8, w_disp=1.2, w_lift=1.3,
              bias=-1.2, lam_min=0.05, lam_max=0.60, p=1.5):
    """3-signal per-document gate."""
    lam_max_eff = lam_min + (lam_max - lam_min) * (Tq ** p)
    lam = {}
    gate_raw = {}
    for d, sig in signals.items():
        g = (w_cov * (1.0 - sig['cov'])
             + w_disp * sig['disp']
             + w_lift * sig['lift']
             + bias)
        raw = sigmoid(g)
        lam[d] = lam_min + (lam_max_eff - lam_min) * raw
        gate_raw[d] = g
    return lam, gate_raw


def gate_4sig(signals, Tq, w_cov=1.5, w_disp=1.0, w_lift=1.2, w_ent=0.6,
              bias=-1.0, lam_min=0.05, lam_max=0.60, p=1.5):
    """4-signal per-document gate (original spec)."""
    lam_max_eff = lam_min + (lam_max - lam_min) * (Tq ** p)
    lam = {}
    gate_raw = {}
    for d, sig in signals.items():
        g = (w_cov * (1.0 - sig['cov'])
             + w_disp * sig['disp']
             + w_lift * sig['lift']
             + w_ent * (1.0 - sig['ent'])
             + bias)
        raw = sigmoid(g)
        lam[d] = lam_min + (lam_max_eff - lam_min) * raw
        gate_raw[d] = g
    return lam, gate_raw


def apply_floor_guard(lambdas, S, lam_min=0.05, epsilon=1e-6):
    """S(d)-floor guard: if specialist has no signal, default to consensus."""
    guarded = {}
    n_guarded = 0
    for d, lam_d in lambdas.items():
        if S.get(d, 0.0) < epsilon:
            guarded[d] = lam_min
            n_guarded += 1
        else:
            guarded[d] = lam_d
    return guarded, n_guarded


def dgaf_fuse(C, S, lambdas, lam_min=0.05):
    """Per-document fusion: Final(d) = (1-λ(d))·C(d) + λ(d)·S(d)."""
    Final = {}
    all_docs = set(C.keys()) | set(S.keys())
    for d in all_docs:
        lam_d = lambdas.get(d, lam_min)
        Final[d] = (1.0 - lam_d) * C.get(d, 0.0) + lam_d * S.get(d, 0.0)
    return Final


# ═══════════════════════════════════════════════════════════════
# SECTION 4: Synthetic Ranker Generators
# ═══════════════════════════════════════════════════════════════

def _perturb(docs, noise, rng, window_scale=30):
    """Apply rank perturbation: swap elements within a window."""
    result = list(docs)
    for i in range(len(result)):
        if rng.random() < noise:
            window = max(1, int(noise * window_scale))
            j = clip(i + rng.randint(-window, window), 0, len(result) - 1)
            result[i], result[j] = result[j], result[i]
    return result


def scenario_moderate(D=200, K=100, R=4, seed=42):
    """
    Moderate disagreement — typical hybrid retrieval.
    4 rankers with different coverage and noise profiles:
      R0 (BM25-like): 75% coverage, low noise
      R1 (Dense-like): 65% coverage, moderate noise
      R2 (Sparse-like): 80% coverage, low noise
      R3 (Reranker-like): 60% coverage, higher noise on unfamiliar docs
    """
    rng = random.Random(seed)
    truth = list(range(D))
    rng.shuffle(truth)

    configs = [
        (0.75, 0.25),  # BM25: good coverage, decent ranking
        (0.65, 0.40),  # Dense: moderate coverage, noisier
        (0.80, 0.20),  # Sparse: best coverage, least noise
        (0.60, 0.45),  # Reranker: narrow, noisiest on tail
    ]
    lists = []
    for cov, noise in configs:
        n_vis = int(D * cov)
        visible = [truth[i] for i in sorted(rng.sample(range(D), n_vis))]
        lists.append(_perturb(visible, noise, rng)[:K])
    return lists


def scenario_specialist_outlier(D=200, K=100, R=4, seed=42):
    """
    Specialist outlier — R0-R2 agree on mainstream docs,
    R3 discovers hidden gems in the long tail that others miss entirely.
    """
    rng = random.Random(seed)
    truth = list(range(D))
    rng.shuffle(truth)

    mainstream = truth[:140]  # docs most rankers see
    hidden_gems = truth[160:]  # docs only specialist finds

    # R0-R2: mainstream with mild variation
    for r in range(3):
        pool = list(mainstream)
        rng.shuffle(pool)
        pool = _perturb(pool, 0.15, rng, window_scale=10)
        yield_list = pool[:K]
        if r == 0:
            lists = [yield_list]
        else:
            lists.append(yield_list)

    # R3 (specialist): finds hidden gems + some mainstream
    specialist = list(hidden_gems[:25])  # 25 hidden gems ranked high
    filler = rng.sample(mainstream, K - 25)
    specialist_list = specialist + filler
    specialist_list = _perturb(specialist_list, 0.10, rng, window_scale=5)
    lists.append(specialist_list[:K])

    return lists


def scenario_cabal(D=200, K=100, R=4, seed=42):
    """
    Cabal — R0-R2 are nearly identical (same base ranking, tiny noise).
    R3 is fully independent.
    """
    rng = random.Random(seed)
    truth = list(range(D))
    rng.shuffle(truth)

    cabal_base = truth[:K]
    lists = []

    # R0-R2: cabal members
    for _ in range(3):
        lists.append(_perturb(list(cabal_base), 0.08, rng, window_scale=3))

    # R3: independent
    independent = list(truth)
    rng.shuffle(independent)
    lists.append(independent[:K])

    return lists


def scenario_full_agreement(D=200, K=100, R=4, seed=42):
    """
    Full agreement — all rankers see the same docs, nearly same order.
    Gate should be effectively inactive (Tq near 0).
    """
    rng = random.Random(seed)
    truth = list(range(D))
    rng.shuffle(truth)

    base = truth[:K]
    lists = [_perturb(list(base), 0.05, rng, window_scale=2) for _ in range(R)]
    return lists


def scenario_full_disagreement(D=300, K=100, R=4, seed=42):
    """
    Full disagreement — each ranker has a substantially different view.
    Minimal overlap. Gate should have maximum dynamic range.
    """
    rng = random.Random(seed)
    truth = list(range(D))

    lists = []
    for r in range(R):
        # Each ranker draws from a different region with some shared overlap
        offset = r * 60
        pool = truth[offset:offset + 160]
        rng.shuffle(pool)
        lists.append(pool[:K])
    return lists


# ═══════════════════════════════════════════════════════════════
# SECTION 5: Full Diagnostic Pipeline
# ═══════════════════════════════════════════════════════════════

def run_one(lists, n_signals=3, floor_guard=False):
    """Run full DGAF pipeline and return diagnostic dict."""
    K = max(len(L) for L in lists)

    # Phase 1: v2.1 backbone
    v21 = v21_backbone(lists)
    C, S, Tq = v21['C'], v21['S'], v21['Tq']

    # Rank maps for signal computation
    c_rank = rank_from_scores(C)
    c_map = {d: i for i, d in enumerate(c_rank)}
    s_rank = rank_from_scores(S)
    s_map = {d: i for i, d in enumerate(s_rank)}

    # Phase 2: Per-document signals + gating
    if n_signals == 4:
        signals = compute_signals_4(lists, c_map, s_map, K=K)
        lambdas, gate_raw = gate_4sig(signals, Tq)
    else:
        signals = compute_signals_3(lists, c_map, s_map, K=K)
        lambdas, gate_raw = gate_3sig(signals, Tq)

    n_guarded = 0
    if floor_guard:
        lambdas, n_guarded = apply_floor_guard(lambdas, S)

    # Phase 3: Fusion
    Final = dgaf_fuse(C, S, lambdas)
    final_rank = rank_from_scores(Final)

    # Also compute v2.1 fusion for comparison
    v21_Final = {}
    all_docs = set(C.keys()) | set(S.keys())
    scalar_lam = v21['scalar_lam']
    for d in all_docs:
        v21_Final[d] = (1.0 - scalar_lam) * C.get(d, 0.0) + scalar_lam * S.get(d, 0.0)
    v21_rank = rank_from_scores(v21_Final)

    # Collect lambda values
    lam_vals = sorted(lambdas.values())

    # Classify documents by lambda
    lam_low_thresh = 0.07   # near λ_min
    lam_high_thresh = 0.15  # elevated specialist trust
    n_consensus = sum(1 for l in lam_vals if l <= lam_low_thresh)
    n_specialist = sum(1 for l in lam_vals if l >= lam_high_thresh)
    n_disputed = len(lam_vals) - n_consensus - n_specialist

    # Signal statistics
    cov_vals = [s['cov'] for s in signals.values()]
    disp_vals = [s['disp'] for s in signals.values()]
    lift_vals = [s['lift'] for s in signals.values()]

    # Rank correlation: DGAF vs v2.1 (Kendall tau on top-30)
    dgaf_top30 = set(final_rank[:30])
    v21_top30 = set(v21_rank[:30])
    top30_overlap = len(dgaf_top30 & v21_top30)

    return {
        'n_signals': n_signals,
        'floor_guard': floor_guard,
        'Tq': Tq,
        'scalar_lam': scalar_lam,
        'n_docs': len(lam_vals),
        'n_guarded': n_guarded,
        # Lambda distribution
        'lam_mean': statistics.mean(lam_vals) if lam_vals else 0,
        'lam_std': statistics.stdev(lam_vals) if len(lam_vals) >= 2 else 0,
        'lam_min': min(lam_vals) if lam_vals else 0,
        'lam_p25': percentile(lam_vals, 25),
        'lam_median': statistics.median(lam_vals) if lam_vals else 0,
        'lam_p75': percentile(lam_vals, 75),
        'lam_max': max(lam_vals) if lam_vals else 0,
        'lam_iqr': percentile(lam_vals, 75) - percentile(lam_vals, 25),
        'lam_values': lam_vals,
        # Document types
        'n_consensus': n_consensus,
        'n_disputed': n_disputed,
        'n_specialist': n_specialist,
        # v2.1 metadata
        'weights': [round(w, 4) for w in v21['w']],
        'spec_idx': v21['spec_idx'],
        'uniqueness': [round(u, 4) for u in v21['u']],
        'influence': [round(i, 4) for i in v21['influence']],
        'affinity': [round(a, 4) for a in v21['a']],
        # Signal stats
        'cov_mean': statistics.mean(cov_vals) if cov_vals else 0,
        'disp_mean': statistics.mean(disp_vals) if disp_vals else 0,
        'lift_mean': statistics.mean(lift_vals) if lift_vals else 0,
        # DGAF vs v2.1
        'top30_overlap': top30_overlap,
    }


# ═══════════════════════════════════════════════════════════════
# SECTION 6: Report Generation
# ═══════════════════════════════════════════════════════════════

def ascii_histogram(values, bins=20, width=40, label=""):
    """Render an ASCII histogram of values."""
    if not values:
        return "  (no data)"
    lo, hi = min(values), max(values)
    if hi - lo < 1e-8:
        return f"  all values = {lo:.4f}"

    bin_width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = min(int((v - lo) / bin_width), bins - 1)
        counts[idx] += 1

    max_count = max(counts) if counts else 1
    lines = []
    for i, cnt in enumerate(counts):
        edge = lo + i * bin_width
        bar_len = int(cnt / max_count * width) if max_count > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {edge:6.4f} |{bar:<{width}} {cnt}")
    return "\n".join(lines)


def verdict(lam_std):
    if lam_std < 0.003:
        return "INERT", "gate not discriminating"
    elif lam_std < 0.01:
        return "MARGINAL", "weak discrimination"
    elif lam_std < 0.03:
        return "ALIVE", "moderate discrimination"
    else:
        return "STRONG", "clear per-document discrimination"


def print_scenario(name, runs):
    """Print detailed results for one scenario."""
    w = 86
    print(f"  {'=' * w}")
    print(f"  {name:^{w}}")
    print(f"  {'=' * w}")

    for r in runs:
        tag = f"{r['n_signals']}-signal"
        if r['floor_guard']:
            tag += " + S(d)-floor-guard"

        v, desc = verdict(r['lam_std'])

        print(f"\n  --- {tag} ---")
        print(f"  Tq (query temperature): {r['Tq']:.4f}")
        print(f"  v2.1 scalar lambda:     {r['scalar_lam']:.4f}  (all docs get this)")
        print(f"  Consensus weights:      {r['weights']}")
        print(f"  Specialists selected:   R{r['spec_idx']}  "
              f"(uniqueness={r['uniqueness']}, influence={r['influence']})")
        print()
        print(f"  lambda(d) Distribution ({r['n_docs']} documents):")
        print(f"    mean   = {r['lam_mean']:.5f}")
        print(f"    std    = {r['lam_std']:.5f}   <-- PRIMARY ALIVENESS METRIC")
        print(f"    min    = {r['lam_min']:.5f}")
        print(f"    p25    = {r['lam_p25']:.5f}")
        print(f"    median = {r['lam_median']:.5f}")
        print(f"    p75    = {r['lam_p75']:.5f}")
        print(f"    max    = {r['lam_max']:.5f}")
        print(f"    IQR    = {r['lam_iqr']:.5f}")
        if r['floor_guard']:
            print(f"    guarded= {r['n_guarded']} docs (S(d)~0, forced to lam_min)")
        print()
        print(f"  Signal means: cov={r['cov_mean']:.3f}  disp={r['disp_mean']:.4f}  lift={r['lift_mean']:.4f}")
        print(f"  Doc types: consensus={r['n_consensus']}  disputed={r['n_disputed']}  specialist={r['n_specialist']}")
        print(f"  DGAF vs v2.1 top-30 overlap: {r['top30_overlap']}/30")
        print()
        print(f"  VERDICT: [{v}] {desc}")
        print()
        print(f"  lambda(d) histogram:")
        print(ascii_histogram(r['lam_values'], bins=15, width=35))
        print()


def print_summary(all_results):
    """Print compact summary table."""
    print()
    print("=" * 100)
    print("SUMMARY TABLE: lambda(d) Variance — Mechanism Aliveness")
    print("=" * 100)
    header = (f"{'Scenario':<25s} {'Config':<16s} {'Tq':>6s} "
              f"{'v2.1 lam':>8s} {'DGAF mean':>9s} {'DGAF std':>8s} "
              f"{'IQR':>7s} {'top30':>5s} {'Verdict':>10s}")
    print(header)
    print("-" * 100)

    for scenario_name, runs in all_results:
        for r in runs:
            tag = f"{r['n_signals']}-sig"
            if r['floor_guard']:
                tag += "+guard"
            v, _ = verdict(r['lam_std'])
            print(f"{scenario_name:<25s} {tag:<16s} {r['Tq']:>6.3f} "
                  f"{r['scalar_lam']:>8.4f} {r['lam_mean']:>9.5f} "
                  f"{r['lam_std']:>8.5f} {r['lam_iqr']:>7.5f} "
                  f"{r['top30_overlap']:>3d}/30 {v:>10s}")


def print_expectations(all_results):
    """Check expectations against results."""
    flat = [r for _, runs in all_results for r in runs]
    print()
    print("=" * 80)
    print("EXPECTATIONS CHECK")
    print("=" * 80)

    checks = [
        ("Full Agreement: gate near-inactive (std < 0.01)",
         any(n == "Full Agreement" and r['lam_std'] < 0.01
             for n, runs in all_results for r in runs
             if r['n_signals'] == 3 and not r['floor_guard'])),

        ("Full Disagreement: gate has range (std > 0.01)",
         any(n == "Full Disagreement" and r['lam_std'] > 0.01
             for n, runs in all_results for r in runs
             if r['n_signals'] == 3 and not r['floor_guard'])),

        ("Specialist Outlier: some docs get elevated lambda",
         any(n == "Specialist Outlier" and r['n_specialist'] > 0
             for n, runs in all_results for r in runs
             if r['n_signals'] == 3 and not r['floor_guard'])),

        ("Moderate: gate discriminates (std > 0.005)",
         any(n == "Moderate Disagreement" and r['lam_std'] > 0.005
             for n, runs in all_results for r in runs
             if r['n_signals'] == 3 and not r['floor_guard'])),

        ("Floor guard reduces lambda variance",
         any(r1['lam_std'] >= r2['lam_std']
             for n, runs in all_results
             for r1 in runs if r1['n_signals'] == 3 and not r1['floor_guard']
             for r2 in runs if r2['n_signals'] == 3 and r2['floor_guard'])),
    ]

    for desc, passed in checks:
        sym = "PASS" if passed else "FAIL"
        print(f"  [{sym}] {desc}")

    # 3-sig vs 4-sig comparison
    print()
    print("  3-SIGNAL vs 4-SIGNAL COMPARISON:")
    for scenario_name, runs in all_results:
        s3 = [r for r in runs if r['n_signals'] == 3 and not r['floor_guard']]
        s4 = [r for r in runs if r['n_signals'] == 4 and not r['floor_guard']]
        if s3 and s4:
            d = abs(s3[0]['lam_std'] - s4[0]['lam_std'])
            bigger = "4-sig" if s4[0]['lam_std'] > s3[0]['lam_std'] else "3-sig"
            print(f"    {scenario_name:<25s}  "
                  f"3-sig std={s3[0]['lam_std']:.5f}  "
                  f"4-sig std={s4[0]['lam_std']:.5f}  "
                  f"delta={d:.5f}  ({bigger} wider)")


# ═══════════════════════════════════════════════════════════════
# SECTION 7: Main Execution
# ═══════════════════════════════════════════════════════════════

def main():
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " IC(R/W)-RRF v3.0 DGAF — MECHANISM ALIVENESS DIAGNOSTIC ".center(78) + "║")
    print("║" + " Per-document gating: alive or cosmetic? ".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    scenarios = [
        ("Moderate Disagreement", scenario_moderate),
        ("Specialist Outlier", scenario_specialist_outlier),
        ("Cabal", scenario_cabal),
        ("Full Agreement", scenario_full_agreement),
        ("Full Disagreement", scenario_full_disagreement),
    ]

    all_results = []

    for name, gen_fn in scenarios:
        lists = gen_fn()
        runs = [
            run_one(lists, n_signals=3, floor_guard=False),
            run_one(lists, n_signals=4, floor_guard=False),
            run_one(lists, n_signals=3, floor_guard=True),
        ]
        all_results.append((name, runs))
        print_scenario(name, runs)

    print_summary(all_results)
    print_expectations(all_results)

    print()
    print("=" * 80)
    print("INTERPRETATION GUIDE")
    print("=" * 80)
    print("""
  std(lambda) is the primary aliveness metric:
    < 0.003  →  INERT: gate produces effectively constant lambda
    < 0.01   →  MARGINAL: weak per-document variation
    < 0.03   →  ALIVE: meaningful per-document discrimination
    >= 0.03  →  STRONG: clear bimodal or multimodal gate behavior

  Expected pattern for a healthy gate:
    Full Agreement     →  INERT or MARGINAL (correct: gate should be inactive)
    Moderate           →  ALIVE (gate discriminates where it matters)
    Specialist Outlier →  ALIVE to STRONG (specialist docs get higher lambda)
    Cabal              →  ALIVE (anti-cabal weighting visible)
    Full Disagreement  →  STRONG (maximum dynamic range)

  If gate is INERT on ALL scenarios: mechanism is cosmetic, abandon.
  If gate is INERT on easy queries + ALIVE on hard queries: mechanism is working.

  top30 overlap measures how much DGAF changes the ranking vs v2.1.
  30/30 = identical rankings. <25/30 = meaningful reranking.
""")


if __name__ == "__main__":
    main()
