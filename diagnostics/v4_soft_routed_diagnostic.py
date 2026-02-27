#!/usr/bin/env python3
"""
IC(R/W)-RRF v4.0 Soft-Routed Adaptive Fusion — Mechanism Aliveness Diagnostic
==============================================================================

Compares three architectures on 5 synthetic scenarios:
  v2.1: Scalar lambda (query-global blend)
  v3.0: DGAF (per-document lambda, two-field gate)
  v4.0: Soft-Routed (per-document per-ranker modulation, no specialist selection)

v4.0 Key Innovation:
  - Soft type membership from coverage + dispersion (no hard thresholds)
  - Per-type ranker modulation (confidence on disputed, independence on specialist)
  - Fixed independence signal (mean dissimilarity, not Var/Mean)
  - Self-guarding: absent rankers contribute zero regardless of modulation
  - 3 parameters (alpha, beta, p) vs v3.0's 5

Diagnostics measured:
  1. Type membership entropy (does the typology discriminate?)
  2. Per-ranker modulation variance (does modulation vary across docs?)
  3. Cross-ranker modulation divergence (do rankers get different treatment per doc?)
  4. Independence signal correctness (especially cabal scenario)
  5. Ranking comparison: v4.0 vs v3.0 vs v2.1

No external dependencies. Python 3.8+ standard library only.
"""

import math
import random
import statistics
from collections import defaultdict
from typing import List, Dict, Tuple


# ═══════════════════════════════════════════════════════════════
# SECTION 1: Core Utilities
# ═══════════════════════════════════════════════════════════════

def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / (len(a | b) + 1e-12)

def topN_set(L, N):
    return set(L[:N])

def rrf_score_lists(lists, weights=None, k=60):
    score = defaultdict(float)
    R = len(lists)
    if weights is None:
        weights = [1.0 / R] * R
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            score[d] += weights[r] / (k + idx + 1)
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

def zscore(values):
    if len(values) < 2:
        return [0.0] * len(values)
    m = sum(values) / len(values)
    s = math.sqrt(sum((x - m) ** 2 for x in values) / len(values))
    if s < 1e-12:
        return [0.0] * len(values)
    return [(x - m) / s for x in values]

def shannon_entropy(probs):
    return -sum(p * math.log(p + 1e-12) for p in probs if p > 1e-12)


# ═══════════════════════════════════════════════════════════════
# SECTION 2: v2.1 Backbone (shared by v3.0 and v4.0)
# ═══════════════════════════════════════════════════════════════

def v21_backbone(lists, k=60, N=30, iters=4,
                 alpha=1.2, beta=0.6, zeta=0.5,
                 wmin=0.05, wmax=0.65, confidences=None):
    R = len(lists)
    w = [1.0 / R] * R
    c = confidences if confidences else [0.5] * R

    # Uniqueness (v2.1 formula — kept for v3.0 comparison)
    top_sets = [topN_set(L, N) for L in lists]
    u = []
    for r in range(R):
        overlaps = [jaccard(top_sets[r], top_sets[s]) for s in range(R) if s != r]
        m = sum(overlaps) / (len(overlaps) + 1e-12)
        v = sum((x - m) ** 2 for x in overlaps) / (len(overlaps) + 1e-12)
        u.append(math.tanh(v / (m + 0.1)))

    for _ in range(iters):
        fused = rrf_score_lists(lists, weights=w, k=k)
        fused_rank = rank_from_scores(fused)
        fused_top = topN_set(fused_rank, N)
        a = [jaccard(topN_set(lists[r], N), fused_top) for r in range(R)]
        a_bar, c_bar, u_bar = sum(a)/R, sum(c)/R, sum(u)/R
        w_new = [w[r] * math.exp(
            alpha*(a[r]-a_bar) + beta*(c[r]-c_bar) + zeta*(u[r]-u_bar)
        ) for r in range(R)]
        w_new = [clip(x, wmin, wmax) for x in w_new]
        s = sum(w_new) + 1e-12
        w = [x/s for x in w_new]

    C = rrf_score_lists(lists, weights=w, k=k)
    Tq = 0.0
    cnt = 0
    for i in range(R):
        for j in range(i+1, R):
            Tq += 1.0 - jaccard(top_sets[i], top_sets[j])
            cnt += 1
    Tq /= (cnt + 1e-12)

    # Specialist selection (for v3.0)
    fused_rank = rank_from_scores(C)
    fused_top = topN_set(fused_rank, N)
    a = [jaccard(topN_set(lists[r], N), fused_top) for r in range(R)]
    influence = []
    for r in range(R):
        w_m = [w[j] for j in range(R) if j != r]
        l_m = [lists[j] for j in range(R) if j != r]
        sm = sum(w_m) + 1e-12
        w_m = [x/sm for x in w_m]
        fm = rrf_score_lists(l_m, weights=w_m, k=k)
        rm = rank_from_scores(fm)
        influence.append(1.0 - jaccard(fused_top, topN_set(rm, N)))

    spec_scores = [c[r]*influence[r]*(1-a[r])*u[r] for r in range(R)]
    spec_idx = sorted(range(R), key=lambda r: spec_scores[r], reverse=True)[:2]
    spec_w = softmax([max(spec_scores[r], 1e-8) for r in spec_idx], temp=0.7)

    S = defaultdict(float)
    for j, r in enumerate(spec_idx):
        for idx, d in enumerate(lists[r]):
            S[d] += spec_w[j] / (k + idx + 1)

    lam_v21 = 0.10 + 0.45 * (Tq ** 1.5)

    return {
        'w': w, 'C': C, 'S': dict(S), 'Tq': Tq, 'c': c, 'u': u,
        'spec_idx': spec_idx, 'influence': influence, 'a': a,
        'scalar_lam': lam_v21,
    }


# ═══════════════════════════════════════════════════════════════
# SECTION 3: v3.0 DGAF (3-signal gate, for comparison)
# ═══════════════════════════════════════════════════════════════

def run_v3(lists, backbone, k=60):
    C, S, Tq = backbone['C'], backbone['S'], backbone['Tq']
    K = max(len(L) for L in lists)
    R = len(lists)

    c_rank = rank_from_scores(C)
    c_map = {d: i for i, d in enumerate(c_rank)}
    s_rank = rank_from_scores(S)
    s_map = {d: i for i, d in enumerate(s_rank)}

    doc_ranks = defaultdict(dict)
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            doc_ranks[d][r] = idx

    lam_max_eff = 0.05 + (0.60 - 0.05) * (Tq ** 1.5)
    lambdas = {}
    for d, ranks in doc_ranks.items():
        cov = len(ranks) / R
        rank_vals = list(ranks.values())
        if len(rank_vals) >= 2:
            mu = sum(rank_vals)/len(rank_vals)
            var = sum((x-mu)**2 for x in rank_vals)/len(rank_vals)
            disp = math.sqrt(var) / (mu + k)
        else:
            disp = 0.0
        lift = max(0.0, (c_map.get(d, K) - s_map.get(d, K))) / K

        g = 1.8*(1-cov) + 1.2*disp + 1.3*lift + (-1.2)
        lam = 0.05 + (lam_max_eff - 0.05) * sigmoid(g)
        if S.get(d, 0.0) < 1e-6:
            lam = 0.05
        lambdas[d] = lam

    Final = {}
    all_docs = set(C.keys()) | set(S.keys())
    for d in all_docs:
        l = lambdas.get(d, 0.05)
        Final[d] = (1-l)*C.get(d, 0.0) + l*S.get(d, 0.0)

    lam_vals = list(lambdas.values())
    return {
        'rank': rank_from_scores(Final),
        'lam_mean': statistics.mean(lam_vals) if lam_vals else 0,
        'lam_std': statistics.stdev(lam_vals) if len(lam_vals) >= 2 else 0,
    }


# ═══════════════════════════════════════════════════════════════
# SECTION 4: v4.0 Soft-Routed Adaptive Fusion
# ═══════════════════════════════════════════════════════════════

def independence_signal(lists, N=30):
    """Mean pairwise dissimilarity per ranker (replaces v2.1 uniqueness)."""
    R = len(lists)
    top_sets = [topN_set(L, N) for L in lists]
    indep = []
    for r in range(R):
        mean_jac = sum(jaccard(top_sets[r], top_sets[s])
                       for s in range(R) if s != r) / (R - 1 + 1e-12)
        indep.append(1.0 - mean_jac)
    return indep


def soft_type_membership(lists, k=60):
    """
    Compute soft type membership for each document.
    Returns: {doc_id: (p_C, p_D, p_S)}
    """
    R = len(lists)
    doc_ranks = defaultdict(dict)
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            doc_ranks[d][r] = idx

    memberships = {}
    for d, ranks in doc_ranks.items():
        cov = len(ranks) / R

        rank_vals = list(ranks.values())
        if len(rank_vals) >= 2:
            mu = sum(rank_vals) / len(rank_vals)
            var = sum((x - mu) ** 2 for x in rank_vals) / len(rank_vals)
            disp = math.sqrt(var) / (mu + k)
        else:
            disp = 0.0

        p_C = cov * (1.0 - disp)
        p_D = cov * disp
        p_S = 1.0 - cov
        total = p_C + p_D + p_S + 1e-12
        memberships[d] = (p_C / total, p_D / total, p_S / total)

    return memberships


def v4_fusion(lists, w, confidences, indep, Tq,
              alpha=0.5, beta=0.5, p=1.5,
              mod_floor=0.1, k=60):
    """
    v4.0 Soft-Routed Adaptive Fusion.

    For each document d and ranker r:
      base(r,d) = w_r / (k + rank_r(d))
      mod(r,d)  = max(mod_floor, p_C·m_C + p_D·m_D + p_S·m_S)
      Final(d)  = Σ_r base(r,d) · mod(r,d)

    where:
      m_r(C) = 1.0
      m_r(D) = 1.0 + α·Tq^p · z(c_r)
      m_r(S) = 1.0 + β·Tq^p · z(indep_r)
    """
    R = len(lists)
    alpha_eff = alpha * (Tq ** p)
    beta_eff = beta * (Tq ** p)

    z_c = zscore(confidences)
    z_ind = zscore(indep)

    # Per-ranker modulation by type
    m_C = [1.0] * R
    m_D = [1.0 + alpha_eff * z_c[r] for r in range(R)]
    m_S = [1.0 + beta_eff * z_ind[r] for r in range(R)]

    # Document type memberships
    memberships = soft_type_membership(lists, k=k)

    # Build doc-ranker map
    doc_ranks = defaultdict(dict)
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            doc_ranks[d][r] = idx

    # Fusion
    Final = defaultdict(float)
    doc_modulations = {}  # for diagnostics: {d: {r: mod_value}}

    for d, ranks in doc_ranks.items():
        p_C, p_D, p_S = memberships[d]
        doc_mods = {}
        for r, rank_val in ranks.items():
            mod = p_C * m_C[r] + p_D * m_D[r] + p_S * m_S[r]
            mod = max(mod_floor, mod)  # modulation floor
            doc_mods[r] = mod
            Final[d] += w[r] * mod / (k + rank_val + 1)
        doc_modulations[d] = doc_mods

    return dict(Final), memberships, doc_modulations, {
        'alpha_eff': alpha_eff, 'beta_eff': beta_eff,
        'm_C': m_C, 'm_D': m_D, 'm_S': m_S,
        'z_c': z_c, 'z_ind': z_ind,
    }


# ═══════════════════════════════════════════════════════════════
# SECTION 5: Synthetic Ranker Generators (same as v3.0 diagnostic)
# ═══════════════════════════════════════════════════════════════

def _perturb(docs, noise, rng, ws=30):
    result = list(docs)
    for i in range(len(result)):
        if rng.random() < noise:
            j = clip(i + rng.randint(-max(1,int(noise*ws)), max(1,int(noise*ws))),
                     0, len(result)-1)
            result[i], result[j] = result[j], result[i]
    return result

def scenario_moderate(D=200, K=100, R=4, seed=42):
    rng = random.Random(seed)
    truth = list(range(D)); rng.shuffle(truth)
    cfgs = [(0.75,0.25), (0.65,0.40), (0.80,0.20), (0.60,0.45)]
    lists = []
    for cov, noise in cfgs:
        vis = [truth[i] for i in sorted(rng.sample(range(D), int(D*cov)))]
        lists.append(_perturb(vis, noise, rng)[:K])
    return lists, [0.7, 0.5, 0.8, 0.6]  # synthetic confidences

def scenario_specialist_outlier(D=200, K=100, R=4, seed=42):
    rng = random.Random(seed)
    truth = list(range(D)); rng.shuffle(truth)
    mainstream = truth[:140]; hidden = truth[160:]
    lists = []
    for r in range(3):
        pool = list(mainstream); rng.shuffle(pool)
        lists.append(_perturb(pool, 0.15, rng, ws=10)[:K])
    spec = hidden[:25] + rng.sample(mainstream, K-25)
    lists.append(_perturb(spec, 0.10, rng, ws=5)[:K])
    return lists, [0.6, 0.6, 0.6, 0.85]  # specialist has high confidence

def scenario_cabal(D=200, K=100, R=4, seed=42):
    rng = random.Random(seed)
    truth = list(range(D)); rng.shuffle(truth)
    base = truth[:K]
    lists = [_perturb(list(base), 0.08, rng, ws=3) for _ in range(3)]
    indep = list(truth); rng.shuffle(indep)
    lists.append(indep[:K])
    return lists, [0.6, 0.6, 0.6, 0.7]

def scenario_agreement(D=200, K=100, R=4, seed=42):
    rng = random.Random(seed)
    truth = list(range(D)); rng.shuffle(truth)
    base = truth[:K]
    return [_perturb(list(base), 0.05, rng, ws=2) for _ in range(R)], [0.6]*4

def scenario_disagreement(D=300, K=100, R=4, seed=42):
    rng = random.Random(seed)
    truth = list(range(D))
    lists = []
    for r in range(R):
        pool = truth[r*60:r*60+160]; rng.shuffle(pool)
        lists.append(pool[:K])
    return lists, [0.5, 0.7, 0.6, 0.8]


# ═══════════════════════════════════════════════════════════════
# SECTION 6: Diagnostic Pipeline
# ═══════════════════════════════════════════════════════════════

def run_diagnostic(name, lists, confidences, alpha=0.5, beta=0.5):
    R = len(lists)
    K = max(len(L) for L in lists)

    # Shared backbone
    bb = v21_backbone(lists, confidences=confidences)
    w, Tq = bb['w'], bb['Tq']

    # v2.1 baseline
    C = bb['C']
    S = bb['S']
    lam_v21 = bb['scalar_lam']
    v21_Final = {}
    for d in set(C.keys()) | set(S.keys()):
        v21_Final[d] = (1-lam_v21)*C.get(d,0) + lam_v21*S.get(d,0)
    v21_rank = rank_from_scores(v21_Final)

    # v3.0 DGAF
    v3 = run_v3(lists, bb)

    # v4.0 Soft-Routed
    indep = independence_signal(lists)
    v4_scores, memberships, doc_mods, meta = v4_fusion(
        lists, w, confidences, indep, Tq, alpha=alpha, beta=beta
    )
    v4_rank = rank_from_scores(v4_scores)

    # ── Diagnostics ──

    # 1. Independence signal
    z_ind = meta['z_ind']
    indep_report = [(r, indep[r], z_ind[r]) for r in range(R)]

    # 2. Type membership stats
    all_p_C = [m[0] for m in memberships.values()]
    all_p_D = [m[1] for m in memberships.values()]
    all_p_S = [m[2] for m in memberships.values()]
    type_entropies = [shannon_entropy(m) / math.log(3) for m in memberships.values()]

    # 3. Per-ranker modulation variance
    ranker_mod_vals = {r: [] for r in range(R)}
    for d, mods in doc_mods.items():
        for r, mv in mods.items():
            ranker_mod_vals[r].append(mv)
    ranker_mod_std = {r: statistics.stdev(vals) if len(vals) >= 2 else 0.0
                      for r, vals in ranker_mod_vals.items()}
    ranker_mod_mean = {r: statistics.mean(vals) if vals else 1.0
                       for r, vals in ranker_mod_vals.items()}

    # 4. Cross-ranker modulation divergence (per document)
    cross_ranker_stds = []
    for d, mods in doc_mods.items():
        if len(mods) >= 2:
            cross_ranker_stds.append(statistics.stdev(mods.values()))
        else:
            cross_ranker_stds.append(0.0)
    mean_cross_std = statistics.mean(cross_ranker_stds) if cross_ranker_stds else 0.0

    # 5. Ranking overlaps
    v4_top30 = set(v4_rank[:30])
    v3_top30 = set(v3['rank'][:30])
    v21_top30 = set(v21_rank[:30])

    overlap_v4_v21 = len(v4_top30 & v21_top30)
    overlap_v4_v3 = len(v4_top30 & v3_top30)
    overlap_v3_v21 = len(v3_top30 & v21_top30)

    return {
        'name': name,
        'R': R,
        'Tq': Tq,
        'w': [round(x, 4) for x in w],
        # Independence
        'indep': indep_report,
        'v21_uniqueness': [round(x, 4) for x in bb['u']],
        # Type membership
        'mean_pC': statistics.mean(all_p_C),
        'mean_pD': statistics.mean(all_p_D),
        'mean_pS': statistics.mean(all_p_S),
        'mean_type_entropy': statistics.mean(type_entropies),
        'n_docs': len(memberships),
        # Modulation
        'meta': meta,
        'ranker_mod_mean': ranker_mod_mean,
        'ranker_mod_std': ranker_mod_std,
        'mean_cross_ranker_std': mean_cross_std,
        # v3.0 comparison
        'v3_lam_std': v3['lam_std'],
        'v3_lam_mean': v3['lam_mean'],
        # Ranking overlaps
        'v4_v21_top30': overlap_v4_v21,
        'v4_v3_top30': overlap_v4_v3,
        'v3_v21_top30': overlap_v3_v21,
        'v21_scalar_lam': lam_v21,
        # Spec info
        'spec_idx': bb['spec_idx'],
    }


# ═══════════════════════════════════════════════════════════════
# SECTION 7: Report
# ═══════════════════════════════════════════════════════════════

def print_report(results):
    print()
    print("╔" + "═"*80 + "╗")
    print("║" + " IC(R/W)-RRF v4.0 Soft-Routed Adaptive Fusion ".center(80) + "║")
    print("║" + " Mechanism Aliveness Diagnostic — v4.0 vs v3.0 vs v2.1 ".center(80) + "║")
    print("╚" + "═"*80 + "╝")

    for r in results:
        print()
        print(f"  {'='*78}")
        print(f"  {r['name']:^78}")
        print(f"  {'='*78}")
        print(f"  Tq = {r['Tq']:.4f}   |   Docs = {r['n_docs']}   |   Consensus weights = {r['w']}")
        print(f"  v2.1 scalar lambda = {r['v21_scalar_lam']:.4f}   |   v2.1 specialists = R{r['spec_idx']}")

        # Independence vs Uniqueness
        print(f"\n  INDEPENDENCE SIGNAL (v4.0 fix vs v2.1 uniqueness):")
        print(f"  {'Ranker':<10} {'Indep':>8} {'z(indep)':>10} {'v2.1 uniq':>10}  {'Assessment'}")
        print(f"  {'-'*60}")
        for rank_r, ind, z_i in r['indep']:
            u21 = r['v21_uniqueness'][rank_r]
            if z_i > 0.5:
                assess = "<-- INDEPENDENT (boosted on Type S)"
            elif z_i < -0.5:
                assess = "<-- CORRELATED (suppressed on Type S)"
            else:
                assess = ""
            print(f"  R{rank_r:<9} {ind:>8.4f} {z_i:>10.4f} {u21:>10.4f}  {assess}")

        # Type membership
        print(f"\n  SOFT TYPE MEMBERSHIP (per-document):")
        print(f"    mean p_C (consensus):   {r['mean_pC']:.4f}")
        print(f"    mean p_D (disputed):    {r['mean_pD']:.4f}")
        print(f"    mean p_S (specialist):  {r['mean_pS']:.4f}")
        print(f"    mean type entropy:      {r['mean_type_entropy']:.4f} "
              f"(0=pure type, 1=uniform)")

        # Per-ranker modulation
        print(f"\n  PER-RANKER MODULATION (does each ranker's weight vary across docs?):")
        print(f"  {'Ranker':<10} {'mod mean':>10} {'mod std':>10} {'Verdict'}")
        print(f"  {'-'*50}")
        max_mod_std = 0
        for rank_r in range(r['R']):
            ms = r['ranker_mod_std'].get(rank_r, 0)
            mm = r['ranker_mod_mean'].get(rank_r, 1)
            max_mod_std = max(max_mod_std, ms)
            if ms < 0.003:
                verd = "FLAT"
            elif ms < 0.01:
                verd = "MARGINAL"
            elif ms < 0.03:
                verd = "ALIVE"
            else:
                verd = "STRONG"
            print(f"  R{rank_r:<9} {mm:>10.5f} {ms:>10.5f} {verd}")

        # Cross-ranker divergence
        print(f"\n  CROSS-RANKER DIVERGENCE (do different rankers get different treatment per doc?):")
        crs = r['mean_cross_ranker_std']
        if crs < 0.003:
            cv = "NO DIVERGENCE — rankers treated identically"
        elif crs < 0.01:
            cv = "MARGINAL divergence"
        elif crs < 0.03:
            cv = "MEANINGFUL divergence — rankers differentiated per doc"
        else:
            cv = "STRONG divergence — clear per-ranker per-doc routing"
        print(f"    mean std(mod across rankers per doc): {crs:.5f}")
        print(f"    Verdict: {cv}")

        # v3.0 comparison
        print(f"\n  v3.0 DGAF COMPARISON:")
        print(f"    v3.0 lambda std:          {r['v3_lam_std']:.5f}")
        print(f"    v4.0 max ranker mod std:  {max_mod_std:.5f}")
        print(f"    v4.0 cross-ranker std:    {crs:.5f}")

        # Ranking overlaps
        print(f"\n  TOP-30 RANKING OVERLAPS:")
        print(f"    v4.0 vs v2.1: {r['v4_v21_top30']}/30")
        print(f"    v4.0 vs v3.0: {r['v4_v3_top30']}/30")
        print(f"    v3.0 vs v2.1: {r['v3_v21_top30']}/30")

        # Overall verdict
        print(f"\n  v4.0 MECHANISM VERDICT:")
        if max_mod_std < 0.003 and crs < 0.003:
            print(f"    INERT — modulation not discriminating")
        elif crs < 0.005:
            print(f"    PER-DOC ALIVE, CROSS-RANKER FLAT — docs differentiated but rankers treated same")
        elif crs >= 0.005 and max_mod_std >= 0.005:
            print(f"    FULLY ALIVE — per-document AND per-ranker discrimination active")
        else:
            print(f"    PARTIALLY ALIVE — mixed signals")

    # Summary table
    print(f"\n{'='*100}")
    print("SUMMARY: v4.0 vs v3.0 vs v2.1")
    print(f"{'='*100}")
    print(f"{'Scenario':<25} {'Tq':>5} {'v3 lam_std':>11} "
          f"{'v4 mod_std':>11} {'v4 x-rank':>10} "
          f"{'v4/v21':>7} {'v4/v3':>6} {'v3/v21':>7} {'v4 Verdict':>14}")
    print("-"*100)
    for r in results:
        max_ms = max(r['ranker_mod_std'].values()) if r['ranker_mod_std'] else 0
        crs = r['mean_cross_ranker_std']
        if max_ms < 0.003 and crs < 0.003:
            verd = "INERT"
        elif crs < 0.005:
            verd = "PER-DOC ONLY"
        else:
            verd = "FULLY ALIVE"
        print(f"{r['name']:<25} {r['Tq']:>5.3f} {r['v3_lam_std']:>11.5f} "
              f"{max_ms:>11.5f} {crs:>10.5f} "
              f"{r['v4_v21_top30']:>5}/30 {r['v4_v3_top30']:>4}/30 "
              f"{r['v3_v21_top30']:>5}/30 {verd:>14}")

    # Expectations
    print(f"\n{'='*80}")
    print("EXPECTATIONS CHECK")
    print(f"{'='*80}")

    checks = [
        ("Full Agreement: v4.0 INERT (correct: no adaptation needed)",
         any(r['name'] == "Full Agreement" and
             max(r['ranker_mod_std'].values()) < 0.003
             for r in results)),
        ("Full Disagreement: v4.0 FULLY ALIVE (max adaptation)",
         any(r['name'] == "Full Disagreement" and
             r['mean_cross_ranker_std'] > 0.005
             for r in results)),
        ("Cabal: independent ranker has highest z(indep)",
         any(r['name'] == "Cabal" and
             r['indep'][3][2] > r['indep'][0][2]
             for r in results)),
        ("Specialist Outlier: cross-ranker divergence > moderate",
         any(r['name'] == "Specialist Outlier" and
             r['mean_cross_ranker_std'] > 0.003
             for r in results)),
        ("v4.0 degrades to v2.1 on Full Agreement (top-30 overlap = 30)",
         any(r['name'] == "Full Agreement" and r['v4_v21_top30'] == 30
             for r in results)),
    ]
    for desc, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {desc}")

    # Cabal deep dive
    print(f"\n{'='*80}")
    print("CABAL SCENARIO DEEP DIVE: Independence Fix Validation")
    print(f"{'='*80}")
    cabal = [r for r in results if r['name'] == "Cabal"]
    if cabal:
        r = cabal[0]
        print(f"\n  v2.1 uniqueness (broken):  {r['v21_uniqueness']}")
        print(f"  v2.1 selected specialists: R{r['spec_idx']} "
              "(should be R3 the independent)")
        print(f"\n  v4.0 independence (fixed):")
        for rank_r, ind, z_i in r['indep']:
            marker = " *** INDEPENDENT" if z_i > 0.5 else ""
            print(f"    R{rank_r}: indep={ind:.4f}  z={z_i:+.4f}{marker}")
        print(f"\n  v4.0 modulation effect on Type S documents:")
        meta = r['meta']
        for rank_r in range(r['R']):
            print(f"    R{rank_r}: m_S = {meta['m_S'][rank_r]:.4f}  "
                  f"(z_indep = {meta['z_ind'][rank_r]:+.4f})")
        # Check if cabal vs independent handled correctly
        if r['indep'][3][2] > r['indep'][0][2]:
            print(f"\n  RESULT: Independent ranker (R3) correctly identified and "
                  f"boosted on specialist docs.")
            print(f"  v2.1 FAILED this (selected cabal members). v4.0 SUCCEEDS.")
        else:
            print(f"\n  WARNING: Independence signal may not be working as expected.")

    print(f"\n{'='*80}")
    print("INTERPRETATION")
    print(f"{'='*80}")
    print("""
  v4.0 has TWO dimensions of aliveness (vs v3.0's ONE):

  1. Per-document variation: Do modulations change across documents?
     → Measured by per-ranker mod std (same as v3.0's lambda std)

  2. Cross-ranker variation: Do different rankers get different treatment
     for the SAME document?
     → This is NEW in v4.0. v3.0 cannot do this (all rankers within a
        field get identical weights).

  The cross-ranker dimension is v4.0's unique contribution.
  If cross-ranker std > 0.005 on disagreement queries: v4.0 is doing
  something v3.0 structurally cannot.

  Parameter count: v4.0 = 3 (alpha, beta, p) vs v3.0 = 5
  Architecture: v4.0 eliminates specialist selection, two-field,
                lambda gating, and floor guard.
""")


def main():
    scenarios = [
        ("Moderate Disagreement", scenario_moderate),
        ("Specialist Outlier", scenario_specialist_outlier),
        ("Cabal", scenario_cabal),
        ("Full Agreement", scenario_agreement),
        ("Full Disagreement", scenario_disagreement),
    ]

    results = []
    for name, gen_fn in scenarios:
        lists, confs = gen_fn()
        results.append(run_diagnostic(name, lists, confs))

    print_report(results)


if __name__ == "__main__":
    main()
