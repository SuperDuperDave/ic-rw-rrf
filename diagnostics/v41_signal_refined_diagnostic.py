#!/usr/bin/env python3
"""
IC(R/W)-RRF v4.1 Signal-Refined Soft-Routed Adaptive Fusion
Mechanism Aliveness Diagnostic + Per-Refinement Ablation
==========================================================

Extends v4.0 diagnostic with three signal refinements:
  Ref 1: Contribution-space dispersion (std/mean of 1/(k+rank+1))
  Ref 2: Reliability-gated independence (min(1, w_r/mean(w)) * z(indep))
  Ref 3: Per-document confidence (within-ranker z-scored scores)

Runs 7 scenarios x 6 fusion variants = 42 test points:
  Variants: v2.1, v3.0, v4.0, v4.0+Ref1, v4.0+Ref2, v4.1 (all three)
  Scenarios: Original 5 + Noisy Independent + Score-Aware

No external dependencies. Python 3.8+ standard library only.
"""

import math
import random
import statistics
from collections import defaultdict
from typing import List, Dict, Tuple, Optional


# ================================================================
# SECTION 1: Core Utilities
# ================================================================

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

def zscore(values, std_floor=1e-3):
    """z-score with stability floor (v4.1: floor=1e-3 instead of 1e-12)."""
    if len(values) < 2:
        return [0.0] * len(values)
    m = sum(values) / len(values)
    s = math.sqrt(sum((x - m) ** 2 for x in values) / len(values))
    s = max(s, std_floor)
    return [(x - m) / s for x in values]

def shannon_entropy(probs):
    return -sum(p * math.log(p + 1e-12) for p in probs if p > 1e-12)


# ================================================================
# SECTION 2: v2.1 Backbone
# ================================================================

def v21_backbone(lists, k=60, N=30, iters=4,
                 alpha=1.2, beta=0.6, zeta=0.5,
                 wmin=0.05, wmax=0.65, confidences=None):
    R = len(lists)
    w = [1.0 / R] * R
    c = confidences if confidences else [0.5] * R

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


# ================================================================
# SECTION 3: v3.0 DGAF
# ================================================================

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


# ================================================================
# SECTION 4: Independence Signal (shared by v4.0 and v4.1)
# ================================================================

def independence_signal(lists, N=30):
    """Mean pairwise dissimilarity (replaces v2.1 uniqueness)."""
    R = len(lists)
    top_sets = [topN_set(L, N) for L in lists]
    indep = []
    for r in range(R):
        mean_jac = sum(jaccard(top_sets[r], top_sets[s])
                       for s in range(R) if s != r) / (R - 1 + 1e-12)
        indep.append(1.0 - mean_jac)
    return indep


# ================================================================
# SECTION 5: Document Signal Computation (v4.0 and v4.1 variants)
# ================================================================

def compute_doc_signals(lists, k=60, use_contrib_space=False):
    """
    Compute per-document coverage and dispersion.

    use_contrib_space=False: v4.0 rank-space dispersion
    use_contrib_space=True:  v4.1 contribution-space dispersion (Ref 1)

    Returns: {doc_id: {'cov': float, 'disp': float, 'ranks': {r: rank}}}
    """
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
            if use_contrib_space:
                # v4.1 Ref 1: contribution-space dispersion
                contribs = [1.0 / (k + rv + 1) for rv in rank_vals]
                mu = sum(contribs) / len(contribs)
                var = sum((c - mu) ** 2 for c in contribs) / len(contribs)
                disp = math.sqrt(var) / (mu + 1e-12)
            else:
                # v4.0: rank-space dispersion
                mu = sum(rank_vals) / len(rank_vals)
                var = sum((rv - mu) ** 2 for rv in rank_vals) / len(rank_vals)
                disp = math.sqrt(var) / (mu + k)
        else:
            disp = 0.0

        signals[d] = {'cov': cov, 'disp': disp, 'ranks': dict(ranks)}

    return signals


def soft_type_membership(cov, disp):
    """Compute soft type membership from coverage and dispersion."""
    p_C = cov * (1.0 - disp)
    p_D = cov * disp
    p_S = 1.0 - cov
    total = p_C + p_D + p_S + 1e-12
    return p_C / total, p_D / total, p_S / total


# ================================================================
# SECTION 6: Per-Document Confidence (v4.1 Ref 3)
# ================================================================

def compute_per_doc_confidence(lists, scores_per_ranker, std_floor=1e-3):
    """
    Compute within-ranker z-scored confidence for each (ranker, document).

    scores_per_ranker: list of dicts, one per ranker.
        Each dict maps doc_id -> score. None if no scores for that ranker.

    Returns: {ranker_idx: {doc_id: z_conf}}
    """
    result = {}
    for r, score_map in enumerate(scores_per_ranker):
        if score_map is None:
            continue
        scores = list(score_map.values())
        if len(scores) < 2:
            continue
        mu = sum(scores) / len(scores)
        var = sum((s - mu) ** 2 for s in scores) / len(scores)
        std = max(math.sqrt(var), std_floor)
        result[r] = {d: (s - mu) / std for d, s in score_map.items()}
    return result


# ================================================================
# SECTION 7: Unified Fusion Engine (all variants)
# ================================================================

def run_fusion(lists, w, confidences, indep, Tq,
               scores_per_ranker=None,
               alpha=0.5, beta=0.5, p=1.5,
               mod_floor=0.1, k=60,
               use_contrib_space=False,
               use_reliability_gate=False,
               use_per_doc_confidence=False):
    """
    Unified fusion engine supporting all v4.x variants through flags.

    Flags:
      use_contrib_space:      Ref 1 (contribution-space dispersion)
      use_reliability_gate:   Ref 2 (reliability-gated independence)
      use_per_doc_confidence: Ref 3 (per-document confidence)

    v4.0 = all flags False
    v4.0+Ref1 = use_contrib_space=True
    v4.0+Ref2 = use_reliability_gate=True
    v4.1 = all flags True (requires scores for Ref 3 to activate)
    """
    R = len(lists)
    alpha_eff = alpha * (Tq ** p)
    beta_eff = beta * (Tq ** p)

    # z-scored ranker features
    z_c = zscore(confidences)
    z_ind = zscore(indep)

    # Reliability gate (Ref 2)
    mean_w = 1.0 / R  # since weights sum to 1
    reliability = [min(1.0, w[r] / mean_w) for r in range(R)]

    # Per-document confidence (Ref 3)
    per_doc_conf = None
    score_aware = False
    if use_per_doc_confidence and scores_per_ranker is not None:
        per_doc_conf = compute_per_doc_confidence(lists, scores_per_ranker)
        score_aware = len(per_doc_conf) > 0

    # Per-type modulation (per-ranker, not per-doc — except Type D with Ref 3)
    m_C = [1.0] * R

    # Type D: per-ranker global (v4.0) or per-doc (v4.1 Ref 3)
    # We'll compute per-doc below if Ref 3 is active
    m_D_global = [1.0 + alpha_eff * z_c[r] for r in range(R)]

    # Type S: with or without reliability gate
    if use_reliability_gate:
        m_S = [1.0 + beta_eff * z_ind[r] * reliability[r] for r in range(R)]
    else:
        m_S = [1.0 + beta_eff * z_ind[r] for r in range(R)]

    # Document signals
    doc_signals = compute_doc_signals(lists, k=k,
                                       use_contrib_space=use_contrib_space)

    # Fusion
    Final = defaultdict(float)
    doc_modulations = {}
    memberships = {}

    for d, sig in doc_signals.items():
        cov, disp, ranks = sig['cov'], sig['disp'], sig['ranks']
        p_C, p_D, p_S = soft_type_membership(cov, disp)
        memberships[d] = (p_C, p_D, p_S)

        doc_mods = {}
        for r, rank_val in ranks.items():
            # Type D modulation: per-doc if Ref 3 active, else per-ranker
            if score_aware and per_doc_conf is not None and r in per_doc_conf:
                z_conf_rd = per_doc_conf[r].get(d, 0.0)
                m_D_r = 1.0 + alpha_eff * z_conf_rd
            else:
                m_D_r = m_D_global[r]

            mod = p_C * m_C[r] + p_D * m_D_r + p_S * m_S[r]
            mod = max(mod_floor, mod)
            doc_mods[r] = mod
            Final[d] += w[r] * mod / (k + rank_val + 1)

        doc_modulations[d] = doc_mods

    return dict(Final), memberships, doc_modulations, {
        'alpha_eff': alpha_eff, 'beta_eff': beta_eff,
        'm_C': m_C, 'm_D_global': m_D_global, 'm_S': m_S,
        'z_c': z_c, 'z_ind': z_ind,
        'reliability': reliability,
        'score_aware': score_aware,
    }


# ================================================================
# SECTION 8: Synthetic Scenarios
# ================================================================

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
    return lists, [0.7, 0.5, 0.8, 0.6], None  # no scores

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
    return lists, [0.6, 0.6, 0.6, 0.85], None

def scenario_cabal(D=200, K=100, R=4, seed=42):
    rng = random.Random(seed)
    truth = list(range(D)); rng.shuffle(truth)
    base = truth[:K]
    lists = [_perturb(list(base), 0.08, rng, ws=3) for _ in range(3)]
    indep = list(truth); rng.shuffle(indep)
    lists.append(indep[:K])
    return lists, [0.6, 0.6, 0.6, 0.7], None

def scenario_agreement(D=200, K=100, R=4, seed=42):
    rng = random.Random(seed)
    truth = list(range(D)); rng.shuffle(truth)
    base = truth[:K]
    return [_perturb(list(base), 0.05, rng, ws=2) for _ in range(R)], [0.6]*4, None

def scenario_disagreement(D=300, K=100, R=4, seed=42):
    rng = random.Random(seed)
    truth = list(range(D))
    lists = []
    for r in range(R):
        pool = truth[r*60:r*60+160]; rng.shuffle(pool)
        lists.append(pool[:K])
    return lists, [0.5, 0.7, 0.6, 0.8], None


# ── NEW v4.1 Scenarios ──

def scenario_noisy_independent(D=200, K=100, R=4, seed=42):
    """
    NEW: One ranker is independent but NOISY (random quality).
    v4.0: boosts the noisy ranker on specialist docs (potentially harmful).
    v4.1 Ref 2: attenuates via reliability gate (safer).
    """
    rng = random.Random(seed)
    truth = list(range(D)); rng.shuffle(truth)
    base = truth[:K]
    # Three consensus rankers with moderate noise
    lists = [_perturb(list(base), 0.15, rng, ws=8) for _ in range(3)]
    # One noisy-independent ranker: partially overlapping, heavily shuffled
    noisy = rng.sample(range(D), K)  # random sample from full doc space
    lists.append(noisy)
    return lists, [0.7, 0.65, 0.7, 0.3], None  # noisy ranker has LOW confidence


def scenario_score_aware(D=200, K=100, R=4, seed=42):
    """
    NEW: Same as moderate disagreement but WITH score data.
    Tests per-document confidence routing (Ref 3).
    Ranker 0 has high scores on specific docs, low on others.
    Ranker 2 has uniform-ish scores.
    """
    rng = random.Random(seed)
    truth = list(range(D)); rng.shuffle(truth)
    cfgs = [(0.75,0.25), (0.65,0.40), (0.80,0.20), (0.60,0.45)]
    lists = []
    for cov, noise in cfgs:
        vis = [truth[i] for i in sorted(rng.sample(range(D), int(D*cov)))]
        lists.append(_perturb(vis, noise, rng)[:K])

    confidences = [0.7, 0.5, 0.8, 0.6]

    # Generate synthetic scores with varying confidence patterns
    scores_per_ranker = []
    for r in range(R):
        score_map = {}
        for idx, d in enumerate(lists[r]):
            # Base score: decaying with rank
            base = 1.0 / (1 + idx * 0.05)
            if r == 0:
                # Ranker 0: high variance — very confident on some docs
                noise_val = rng.gauss(0, 0.3)
                score_map[d] = base + noise_val
            elif r == 2:
                # Ranker 2: low variance — uniform confidence
                noise_val = rng.gauss(0, 0.02)
                score_map[d] = base + noise_val
            else:
                # Others: moderate variance
                noise_val = rng.gauss(0, 0.1)
                score_map[d] = base + noise_val
        scores_per_ranker.append(score_map)

    return lists, confidences, scores_per_ranker


# ================================================================
# SECTION 9: Diagnostic Pipeline
# ================================================================

VARIANT_CONFIGS = {
    'v4.0':       {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': False},
    'v4.0+Ref1':  {'use_contrib_space': True,  'use_reliability_gate': False, 'use_per_doc_confidence': False},
    'v4.0+Ref2':  {'use_contrib_space': False, 'use_reliability_gate': True,  'use_per_doc_confidence': False},
    'v4.0+Ref3':  {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': True},
    'v4.1':       {'use_contrib_space': True,  'use_reliability_gate': True,  'use_per_doc_confidence': True},
}


def compute_diagnostics(doc_mods, memberships, R):
    """Compute diagnostic metrics from fusion output."""
    # Per-ranker modulation stats
    ranker_mod_vals = {r: [] for r in range(R)}
    for d, mods in doc_mods.items():
        for r, mv in mods.items():
            ranker_mod_vals[r].append(mv)
    ranker_mod_std = {r: statistics.stdev(vals) if len(vals) >= 2 else 0.0
                      for r, vals in ranker_mod_vals.items()}

    # Cross-ranker divergence
    cross_ranker_stds = []
    for d, mods in doc_mods.items():
        if len(mods) >= 2:
            cross_ranker_stds.append(statistics.stdev(mods.values()))
    mean_cross_std = statistics.mean(cross_ranker_stds) if cross_ranker_stds else 0.0

    # Type membership stats
    all_p_C = [m[0] for m in memberships.values()]
    all_p_D = [m[1] for m in memberships.values()]
    all_p_S = [m[2] for m in memberships.values()]

    max_mod_std = max(ranker_mod_std.values()) if ranker_mod_std else 0.0

    return {
        'max_mod_std': max_mod_std,
        'mean_cross_std': mean_cross_std,
        'ranker_mod_std': ranker_mod_std,
        'mean_pC': statistics.mean(all_p_C) if all_p_C else 0,
        'mean_pD': statistics.mean(all_p_D) if all_p_D else 0,
        'mean_pS': statistics.mean(all_p_S) if all_p_S else 0,
    }


def run_scenario(name, lists, confidences, scores_per_ranker=None):
    R = len(lists)
    K = max(len(L) for L in lists)

    # Shared backbone
    bb = v21_backbone(lists, confidences=confidences)
    w, Tq = bb['w'], bb['Tq']

    # v2.1 baseline
    C, S = bb['C'], bb['S']
    lam_v21 = bb['scalar_lam']
    v21_Final = {}
    for d in set(C.keys()) | set(S.keys()):
        v21_Final[d] = (1-lam_v21)*C.get(d, 0) + lam_v21*S.get(d, 0)
    v21_rank = rank_from_scores(v21_Final)

    # v3.0
    v3 = run_v3(lists, bb)

    # Independence (shared by all v4.x)
    indep = independence_signal(lists)

    # Run all v4.x variants
    variant_results = {}
    for vname, cfg in VARIANT_CONFIGS.items():
        scores, memberships, doc_mods, meta = run_fusion(
            lists, w, confidences, indep, Tq,
            scores_per_ranker=scores_per_ranker,
            **cfg
        )
        rank = rank_from_scores(scores)
        diag = compute_diagnostics(doc_mods, memberships, R)

        v4_top30 = set(rank[:30])
        v21_top30 = set(v21_rank[:30])
        v3_top30 = set(v3['rank'][:30])

        variant_results[vname] = {
            'rank': rank,
            'diag': diag,
            'meta': meta,
            'memberships': memberships,
            'top30_v21': len(v4_top30 & v21_top30),
            'top30_v3': len(v4_top30 & v3_top30),
        }

    return {
        'name': name,
        'R': R,
        'Tq': Tq,
        'w': [round(x, 4) for x in w],
        'indep': [(r, indep[r], zscore(indep)[r]) for r in range(R)],
        'v21_uniqueness': [round(x, 4) for x in bb['u']],
        'v3_lam_std': v3['lam_std'],
        'v3_v21_top30': len(set(v3['rank'][:30]) & set(v21_rank[:30])),
        'variants': variant_results,
        'reliability': [min(1.0, w[r] / (1.0/R)) for r in range(R)],
        'score_aware': scores_per_ranker is not None,
    }


# ================================================================
# SECTION 10: Report
# ================================================================

def verdict(mod_std, cross_std):
    if mod_std < 0.003 and cross_std < 0.003:
        return "INERT"
    elif cross_std < 0.005:
        return "PER-DOC ONLY"
    else:
        return "FULLY ALIVE"


def print_report(results):
    print()
    print("=" * 100)
    print(" IC(R/W)-RRF v4.1 Signal-Refined Soft-Routed Adaptive Fusion ".center(100))
    print(" Mechanism Aliveness Diagnostic + Per-Refinement Ablation ".center(100))
    print("=" * 100)

    # ── Per-scenario detail ──
    for r in results:
        print(f"\n{'─'*100}")
        print(f"  {r['name']}")
        print(f"{'─'*100}")
        print(f"  Tq={r['Tq']:.3f}  w={r['w']}  score_aware={r['score_aware']}")

        # Independence signal
        print(f"\n  INDEPENDENCE + RELIABILITY:")
        print(f"  {'Ranker':<8} {'indep':>7} {'z(ind)':>8} {'v21_u':>7} {'reliability':>12}")
        for rank_r, ind, z_i in r['indep']:
            rel = r['reliability'][rank_r]
            print(f"  R{rank_r:<7} {ind:>7.4f} {z_i:>8.4f} {r['v21_uniqueness'][rank_r]:>7.4f} {rel:>12.4f}")

        # Variant comparison table
        print(f"\n  VARIANT COMPARISON:")
        print(f"  {'Variant':<14} {'mod_std':>8} {'x-ranker':>9} {'pC':>6} {'pD':>6} {'pS':>6} "
              f"{'vs v2.1':>8} {'vs v3.0':>8} {'Verdict':<14}")
        print(f"  {'-'*90}")

        # v3.0 baseline row
        print(f"  {'v3.0':<14} {'lam='+format(r['v3_lam_std'],'.5f'):>8} {'N/A':>9} "
              f"{'':>6} {'':>6} {'':>6} {r['v3_v21_top30']:>5}/30 {'---':>8} {'---':<14}")

        for vname in ['v4.0', 'v4.0+Ref1', 'v4.0+Ref2', 'v4.0+Ref3', 'v4.1']:
            vr = r['variants'].get(vname)
            if vr is None:
                continue
            d = vr['diag']
            v = verdict(d['max_mod_std'], d['mean_cross_std'])
            # Only show Ref3 if score-aware
            if vname == 'v4.0+Ref3' and not r['score_aware']:
                continue
            print(f"  {vname:<14} {d['max_mod_std']:>8.5f} {d['mean_cross_std']:>9.5f} "
                  f"{d['mean_pC']:>6.3f} {d['mean_pD']:>6.3f} {d['mean_pS']:>6.3f} "
                  f"{vr['top30_v21']:>5}/30 {vr['top30_v3']:>5}/30 {v:<14}")

    # ── Summary table ──
    print(f"\n{'='*120}")
    print("SUMMARY: All Variants Across All Scenarios")
    print(f"{'='*120}")
    header = f"{'Scenario':<22} {'Tq':>5}"
    for vname in ['v3.0', 'v4.0', 'v4.0+R1', 'v4.0+R2', 'v4.1']:
        header += f" | {vname:>10}"
    print(header)
    print(f"{'':22} {'':>5}", end="")
    for _ in range(5):
        print(f" | {'mod/xrank':>10}", end="")
    print()
    print("-" * 120)

    for r in results:
        row = f"{r['name']:<22} {r['Tq']:>5.3f}"
        # v3.0
        row += f" | {'lam:'+format(r['v3_lam_std'],'.3f'):>10}"
        # v4.0
        v40 = r['variants']['v4.0']['diag']
        row += f" | {v40['max_mod_std']:.3f}/{v40['mean_cross_std']:.3f}"
        # v4.0+Ref1
        v41r1 = r['variants']['v4.0+Ref1']['diag']
        row += f" | {v41r1['max_mod_std']:.3f}/{v41r1['mean_cross_std']:.3f}"
        # v4.0+Ref2
        v41r2 = r['variants']['v4.0+Ref2']['diag']
        row += f" | {v41r2['max_mod_std']:.3f}/{v41r2['mean_cross_std']:.3f}"
        # v4.1
        v41 = r['variants']['v4.1']['diag']
        row += f" | {v41['max_mod_std']:.3f}/{v41['mean_cross_std']:.3f}"
        print(row)

    # ── Refinement Impact Analysis ──
    print(f"\n{'='*100}")
    print("REFINEMENT IMPACT ANALYSIS (v4.1 delta vs v4.0)")
    print(f"{'='*100}")
    print(f"{'Scenario':<22} {'Ref1: disp':>12} {'Ref2: gate':>12} {'Ref1+2 (v4.1)':>14} {'Score?':>7}")
    print("-" * 70)

    for r in results:
        v40_ms = r['variants']['v4.0']['diag']['max_mod_std']
        v40_xs = r['variants']['v4.0']['diag']['mean_cross_std']
        r1_ms = r['variants']['v4.0+Ref1']['diag']['max_mod_std']
        r1_xs = r['variants']['v4.0+Ref1']['diag']['mean_cross_std']
        r2_ms = r['variants']['v4.0+Ref2']['diag']['max_mod_std']
        r2_xs = r['variants']['v4.0+Ref2']['diag']['mean_cross_std']
        v41_ms = r['variants']['v4.1']['diag']['max_mod_std']
        v41_xs = r['variants']['v4.1']['diag']['mean_cross_std']

        d_r1 = r1_xs - v40_xs
        d_r2 = r2_xs - v40_xs
        d_v41 = v41_xs - v40_xs

        print(f"{r['name']:<22} {d_r1:>+12.5f} {d_r2:>+12.5f} {d_v41:>+14.5f} "
              f"{'Yes' if r['score_aware'] else 'No':>7}")

    # ── Noisy Independent Deep Dive ──
    noisy = [r for r in results if r['name'] == 'Noisy Independent']
    if noisy:
        r = noisy[0]
        print(f"\n{'='*100}")
        print("NOISY INDEPENDENT SCENARIO: Reliability Gate Validation")
        print(f"{'='*100}")
        print(f"\n  This scenario has 3 consensus rankers + 1 noisy independent ranker (R3).")
        print(f"  R3 is independent (random) but low quality (confidence=0.3).")
        print(f"  v4.0 boosts R3 on specialist docs. v4.1 Ref2 should attenuate.\n")

        for vname in ['v4.0', 'v4.0+Ref2', 'v4.1']:
            meta = r['variants'][vname]['meta']
            print(f"  {vname}:")
            print(f"    m_S values: {['R'+str(i)+'='+format(meta['m_S'][i], '.4f') for i in range(r['R'])]}")
            if 'reliability' in meta:
                print(f"    reliability: {['R'+str(i)+'='+format(meta['reliability'][i], '.4f') for i in range(r['R'])]}")
            print()

    # ── Score-Aware Deep Dive ──
    score = [r for r in results if r['name'] == 'Score-Aware']
    if score:
        r = score[0]
        print(f"{'='*100}")
        print("SCORE-AWARE SCENARIO: Per-Document Confidence Validation")
        print(f"{'='*100}")
        print(f"\n  This scenario includes synthetic scores per ranker.")
        print(f"  R0: high score variance (confident on some, not others)")
        print(f"  R2: low score variance (uniform confidence)\n")

        # Compare v4.0 (global confidence) vs v4.1 (per-doc confidence)
        v40_diag = r['variants']['v4.0']['diag']
        v41_diag = r['variants']['v4.1']['diag']

        # Intra-document modulation variance for v4.0 vs v4.1
        for vname in ['v4.0', 'v4.0+Ref3', 'v4.1']:
            vr = r['variants'].get(vname)
            if vr is None:
                continue
            d = vr['diag']
            print(f"  {vname}:")
            print(f"    cross-ranker divergence: {d['mean_cross_std']:.5f}")
            print(f"    max ranker mod std:      {d['max_mod_std']:.5f}")
            # Check if Ref3 made a difference
            if vname in ('v4.0+Ref3', 'v4.1'):
                meta = vr['meta']
                print(f"    score_aware:             {meta['score_aware']}")
            print()

    # ── Expectations Check ──
    print(f"{'='*100}")
    print("EXPECTATIONS CHECK")
    print(f"{'='*100}")

    checks = [
        ("Full Agreement: v4.1 INERT",
         any(r['name'] == "Full Agreement" and
             r['variants']['v4.1']['diag']['max_mod_std'] < 0.003
             for r in results)),
        ("Full Disagreement: v4.1 FULLY ALIVE",
         any(r['name'] == "Full Disagreement" and
             r['variants']['v4.1']['diag']['mean_cross_std'] > 0.005
             for r in results)),
        ("Cabal: independent ranker highest z(indep)",
         any(r['name'] == "Cabal" and
             r['indep'][3][2] > r['indep'][0][2]
             for r in results)),
        ("v4.1 degrades to v2.1 on Full Agreement (top-30 = 30)",
         any(r['name'] == "Full Agreement" and
             r['variants']['v4.1']['top30_v21'] == 30
             for r in results)),
        ("Noisy Independent: v4.1 attenuates noisy ranker vs v4.0",
         any(r['name'] == "Noisy Independent" and
             abs(r['variants']['v4.0+Ref2']['meta']['m_S'][3] -1.0) <
             abs(r['variants']['v4.0']['meta']['m_S'][3] - 1.0)
             for r in results)),
        ("Score-Aware: Ref3 alone increases cross-ranker divergence vs v4.0",
         any(r['name'] == "Score-Aware" and
             r['variants']['v4.0+Ref3']['diag']['mean_cross_std'] >
             r['variants']['v4.0']['diag']['mean_cross_std']
             for r in results)),
        ("Score-Aware: Ref2 reduces cross-ranker divergence (bounds modulation)",
         any(r['name'] == "Score-Aware" and
             r['variants']['v4.0+Ref2']['diag']['mean_cross_std'] <
             r['variants']['v4.0']['diag']['mean_cross_std']
             for r in results)),
        ("Ref1 changes type membership on Specialist Outlier",
         any(r['name'] == "Specialist Outlier" and
             abs(r['variants']['v4.0+Ref1']['diag']['mean_pD'] -
                 r['variants']['v4.0']['diag']['mean_pD']) > 0.001
             for r in results)),
    ]
    for desc, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {desc}")

    print(f"\n{'='*100}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'='*100}")


# ================================================================
# SECTION 11: Main
# ================================================================

def main():
    scenarios = [
        ("Full Agreement",        scenario_agreement),
        ("Moderate Disagreement",  scenario_moderate),
        ("Specialist Outlier",     scenario_specialist_outlier),
        ("Cabal",                  scenario_cabal),
        ("Full Disagreement",      scenario_disagreement),
        ("Noisy Independent",      scenario_noisy_independent),
        ("Score-Aware",            scenario_score_aware),
    ]

    results = []
    for name, gen_fn in scenarios:
        lists, confs, scores = gen_fn()
        results.append(run_scenario(name, lists, confs, scores))

    print_report(results)


if __name__ == "__main__":
    main()
