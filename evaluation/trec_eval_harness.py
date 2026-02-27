#!/usr/bin/env python3
"""
IC(R/W)-RRF TREC Evaluation Harness
====================================

Evaluates all fusion variants against TREC-format run files and qrels.
Supports TREC DL 2019/2020 and any dataset with standard run/qrel format.

Fusion variants evaluated:
  - Vanilla RRF (baseline)
  - v2.1 IC(R/W)-RRF (iterative consensus)
  - v3.0 DGAF (per-document gating)
  - v4.0 Soft-Routed (per-ranker modulation)
  - v4.1 Signal-Refined (contribution-space disp, reliability gate, per-doc conf)
  - v4.1 ablations (Ref1 only, Ref2 only, Ref3 only)

Metrics: NDCG@10, NDCG@20, MAP@100, MRR
Statistical testing: paired t-test, bootstrap confidence intervals

Usage:
  python trec_eval_harness.py --qrels path/to/qrels --runs run1.txt run2.txt ...
  python trec_eval_harness.py --qrels qrels.txt --run-dir ./runs/ --pattern "*.txt"
  python trec_eval_harness.py --demo  (synthetic demo with built-in data)

No external dependencies. Python 3.8+ standard library only.
(Optional: pytrec_eval for cross-validation of metrics.)
"""

import argparse
import glob
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set


# ================================================================
# SECTION 1: TREC I/O
# ================================================================

def parse_run_file(path: str) -> Dict[str, List[Tuple[str, int, float]]]:
    """
    Parse a TREC run file.
    Format: qid Q0 docid rank score run_name
    Returns: {qid: [(docid, rank, score), ...]} sorted by rank ascending.
    """
    results = defaultdict(list)
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 6:
                continue
            qid, _, docid, rank, score, _ = parts[0], parts[1], parts[2], int(parts[3]), float(parts[4]), parts[5]
            results[qid].append((docid, rank, score))

    # Sort each query's results by rank
    for qid in results:
        results[qid].sort(key=lambda x: x[1])

    return dict(results)


def parse_qrels(path: str) -> Dict[str, Dict[str, int]]:
    """
    Parse TREC qrels file.
    Format: qid 0 docid relevance
    Returns: {qid: {docid: relevance}}
    """
    qrels = defaultdict(dict)
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 4:
                continue
            qid, _, docid, rel = parts[0], parts[1], parts[2], int(parts[3])
            qrels[qid][docid] = rel

    return dict(qrels)


def runs_to_ranked_lists(runs: Dict[str, Dict[str, List[Tuple[str, int, float]]]],
                          qid: str) -> Tuple[List[List[str]], List[float],
                                              Optional[List[Dict[str, float]]]]:
    """
    Convert multiple run files for a single query into fusion input format.

    Returns:
      lists: list of ranked doc ID lists (one per ranker)
      confidences: ranker-level confidence (mean score, normalized)
      scores_per_ranker: [{docid: score}, ...] for per-doc confidence
    """
    lists = []
    confidences = []
    scores_per_ranker = []

    for run_name, run_data in runs.items():
        if qid not in run_data:
            continue
        entries = run_data[qid]
        doc_list = [docid for docid, rank, score in entries]
        score_map = {docid: score for docid, rank, score in entries}

        lists.append(doc_list)

        # Ranker-level confidence: mean absolute score (higher = more confident)
        scores = [score for _, _, score in entries]
        if scores:
            confidences.append(statistics.mean(scores))
        else:
            confidences.append(0.5)

        scores_per_ranker.append(score_map)

    # Normalize confidences to [0, 1]
    if confidences:
        mn, mx = min(confidences), max(confidences)
        rng = mx - mn if mx - mn > 1e-12 else 1.0
        confidences = [0.3 + 0.4 * (c - mn) / rng for c in confidences]

    return lists, confidences, scores_per_ranker


# ================================================================
# SECTION 2: Evaluation Metrics (built-in, no dependencies)
# ================================================================

def dcg(rels: List[int], k: int) -> float:
    """Discounted Cumulative Gain at k."""
    total = 0.0
    for i, r in enumerate(rels[:k]):
        total += (2 ** r - 1) / math.log2(i + 2)  # i+2 because log2(1) = 0
    return total


def ndcg_at_k(ranked_docs: List[str], qrel: Dict[str, int], k: int) -> float:
    """Normalized DCG at k."""
    rels = [qrel.get(d, 0) for d in ranked_docs[:k]]
    ideal_rels = sorted(qrel.values(), reverse=True)[:k]

    dcg_val = dcg(rels, k)
    idcg_val = dcg(ideal_rels, k)

    if idcg_val == 0:
        return 0.0
    return dcg_val / idcg_val


def average_precision(ranked_docs: List[str], qrel: Dict[str, int], k: int) -> float:
    """Average Precision at k."""
    num_rel = 0
    sum_prec = 0.0
    total_rel = sum(1 for r in qrel.values() if r > 0)

    if total_rel == 0:
        return 0.0

    for i, d in enumerate(ranked_docs[:k]):
        if qrel.get(d, 0) > 0:
            num_rel += 1
            sum_prec += num_rel / (i + 1)

    return sum_prec / total_rel


def mrr(ranked_docs: List[str], qrel: Dict[str, int]) -> float:
    """Mean Reciprocal Rank (reciprocal rank of first relevant doc)."""
    for i, d in enumerate(ranked_docs):
        if qrel.get(d, 0) > 0:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_ranking(ranked_docs: List[str], qrel: Dict[str, int]) -> Dict[str, float]:
    """Compute all metrics for a single query."""
    return {
        'NDCG@10': ndcg_at_k(ranked_docs, qrel, 10),
        'NDCG@20': ndcg_at_k(ranked_docs, qrel, 20),
        'MAP@100': average_precision(ranked_docs, qrel, 100),
        'MRR': mrr(ranked_docs, qrel),
    }


# ================================================================
# SECTION 3: Statistical Testing
# ================================================================

def paired_t_test(scores_a: List[float], scores_b: List[float]) -> Tuple[float, float]:
    """
    Paired t-test. Returns (t_statistic, p_value).
    Approximation using standard library only.
    """
    n = len(scores_a)
    if n < 2:
        return 0.0, 1.0

    diffs = [a - b for a, b in zip(scores_a, scores_b)]
    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    se = math.sqrt(var_d / n) if var_d > 0 else 1e-12

    t = mean_d / se

    # Two-sided p-value approximation using normal distribution
    # (valid for n >= 30; for smaller n, this is approximate)
    z = abs(t)
    p = 2 * (1 - _normal_cdf(z))

    return t, p


def _normal_cdf(z):
    """Standard normal CDF using math.erf (exact)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def bootstrap_ci(scores: List[float], n_boot=1000, ci=0.95, seed=42) -> Tuple[float, float]:
    """Bootstrap confidence interval for the mean."""
    rng = random.Random(seed)
    n = len(scores)
    if n < 2:
        m = scores[0] if scores else 0.0
        return m, m

    means = []
    for _ in range(n_boot):
        sample = [scores[rng.randint(0, n-1)] for _ in range(n)]
        means.append(sum(sample) / n)

    means.sort()
    lo_idx = int((1 - ci) / 2 * n_boot)
    hi_idx = int((1 + ci) / 2 * n_boot) - 1
    return means[lo_idx], means[hi_idx]


# ================================================================
# SECTION 4: Fusion Implementations (self-contained)
# ================================================================

def _jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / (len(a | b) + 1e-12)

def _clip(x, lo, hi):
    return max(lo, min(hi, x))

def _zscore(values, std_floor=1e-3):
    if len(values) < 2:
        return [0.0] * len(values)
    m = sum(values) / len(values)
    s = math.sqrt(sum((x - m) ** 2 for x in values) / len(values))
    s = max(s, std_floor)
    return [(x - m) / s for x in values]

def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-20, min(20, x))))

def _softmax(xs, temp=1.0):
    if not xs:
        return []
    m = max(xs)
    exps = [math.exp((x - m) / temp) for x in xs]
    s = sum(exps) + 1e-12
    return [e / s for e in exps]

def _rrf_scores(lists, weights=None, k=60):
    score = defaultdict(float)
    R = len(lists)
    if weights is None:
        weights = [1.0 / R] * R
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            score[d] += weights[r] / (k + idx + 1)
    return dict(score)

def _rank_from_scores(score_map):
    return [d for d, _ in sorted(score_map.items(), key=lambda x: x[1], reverse=True)]


# ── Vanilla RRF ──

def fuse_vanilla_rrf(lists, k=60):
    scores = _rrf_scores(lists, k=k)
    return _rank_from_scores(scores)


# ── v2.1 IC(R/W)-RRF ──

def fuse_v21(lists, confidences, k=60, N=30, iters=4):
    R = len(lists)
    w = [1.0 / R] * R
    c = confidences

    top_sets = [set(L[:N]) for L in lists]

    # Uniqueness (original v2.1 formula)
    u = []
    for r in range(R):
        overlaps = [_jaccard(top_sets[r], top_sets[s]) for s in range(R) if s != r]
        m = sum(overlaps) / (len(overlaps) + 1e-12)
        v = sum((x - m) ** 2 for x in overlaps) / (len(overlaps) + 1e-12)
        u.append(math.tanh(v / (m + 0.1)))

    for _ in range(iters):
        fused = _rrf_scores(lists, weights=w, k=k)
        fused_top = set(_rank_from_scores(fused)[:N])
        a = [_jaccard(set(L[:N]), fused_top) for L in lists]
        a_bar, c_bar, u_bar = sum(a)/R, sum(c)/R, sum(u)/R
        w_new = [w[r] * math.exp(1.2*(a[r]-a_bar) + 0.6*(c[r]-c_bar) + 0.5*(u[r]-u_bar))
                 for r in range(R)]
        w_new = [_clip(x, 0.05, 0.65) for x in w_new]
        s = sum(w_new) + 1e-12
        w = [x/s for x in w_new]

    C = _rrf_scores(lists, weights=w, k=k)

    # Temperature
    Tq = 0.0
    cnt = 0
    for i in range(R):
        for j in range(i+1, R):
            Tq += 1.0 - _jaccard(top_sets[i], top_sets[j])
            cnt += 1
    Tq /= (cnt + 1e-12)

    # Specialist selection
    fused_rank = _rank_from_scores(C)
    fused_top = set(fused_rank[:N])
    a = [_jaccard(set(L[:N]), fused_top) for L in lists]

    influence = []
    for r in range(R):
        w_m = [w[j] for j in range(R) if j != r]
        l_m = [lists[j] for j in range(R) if j != r]
        sm = sum(w_m) + 1e-12
        w_m = [x/sm for x in w_m]
        fm = _rrf_scores(l_m, weights=w_m, k=k)
        rm = _rank_from_scores(fm)
        influence.append(1.0 - _jaccard(fused_top, set(rm[:N])))

    spec_scores = [c[r]*influence[r]*(1-a[r])*u[r] for r in range(R)]
    spec_idx = sorted(range(R), key=lambda r: spec_scores[r], reverse=True)[:2]
    spec_w = _softmax([max(spec_scores[r], 1e-8) for r in spec_idx], temp=0.7)

    S = defaultdict(float)
    for j, r in enumerate(spec_idx):
        for idx, d in enumerate(lists[r]):
            S[d] += spec_w[j] / (k + idx + 1)

    lam = 0.10 + 0.45 * (Tq ** 1.5)
    Final = {}
    for d in set(C.keys()) | set(S.keys()):
        Final[d] = (1-lam)*C.get(d, 0) + lam*S.get(d, 0)

    return _rank_from_scores(Final), w, Tq


# ── v3.0 DGAF ──

def fuse_v3(lists, w, Tq, C, S, k=60):
    R = len(lists)
    K = max(len(L) for L in lists)
    c_rank = _rank_from_scores(C)
    c_map = {d: i for i, d in enumerate(c_rank)}
    s_rank = _rank_from_scores(S)
    s_map = {d: i for i, d in enumerate(s_rank)}

    doc_ranks = defaultdict(dict)
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            doc_ranks[d][r] = idx

    lam_max_eff = 0.05 + (0.60 - 0.05) * (Tq ** 1.5)
    Final = {}
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
        lam = 0.05 + (lam_max_eff - 0.05) * _sigmoid(g)
        if S.get(d, 0.0) < 1e-6:
            lam = 0.05
        Final[d] = (1-lam)*C.get(d, 0) + lam*S.get(d, 0)

    return _rank_from_scores(Final)


# ── v4.0 / v4.1 Soft-Routed ──

def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-20, min(20, x))))


def fuse_v4x(lists, confidences, scores_per_ranker=None,
             k=60, N=30, iters=4,
             alpha=0.5, beta=0.5, p=1.5, mod_floor=0.1,
             use_contrib_space=False,
             use_reliability_gate=False,
             use_per_doc_confidence=False,
             # v4.2 flags
             one_sided_confidence=False,
             one_sided_independence=False,
             conf_gated_independence=False,
             conf_gate_type='sigmoid',
             # PACA: Position-Aware Confidence Attenuation
             position_aware_attenuation=False,
             k_protect=3):
    """
    Unified v4.x fusion with configurable refinements.

    v4.0: all flags False
    v4.1: use_contrib_space + use_reliability_gate + use_per_doc_confidence
    v4.2: use_contrib_space + use_per_doc_confidence
           + one_sided_confidence + one_sided_independence + conf_gated_independence

    conf_gate_type: 'sigmoid' | 'relu' | 'bounded_relu'
      How to gate Type S independence by per-doc confidence.

    Returns: (ranked_docs, w, Tq, indep)
    """
    R = len(lists)
    w = [1.0 / R] * R
    c = confidences
    top_sets = [set(L[:N]) for L in lists]

    # Independence (v4.0 fix)
    indep = []
    for r in range(R):
        mean_jac = sum(_jaccard(top_sets[r], top_sets[s])
                       for s in range(R) if s != r) / (R - 1 + 1e-12)
        indep.append(1.0 - mean_jac)

    # Iterative consensus (with independence)
    for _ in range(iters):
        fused = _rrf_scores(lists, weights=w, k=k)
        fused_top = set(_rank_from_scores(fused)[:N])
        a = [_jaccard(set(L[:N]), fused_top) for L in lists]
        a_bar, c_bar, i_bar = sum(a)/R, sum(c)/R, sum(indep)/R
        w_new = [w[r] * math.exp(1.2*(a[r]-a_bar) + 0.6*(c[r]-c_bar) + 0.5*(indep[r]-i_bar))
                 for r in range(R)]
        w_new = [_clip(x, 0.05, 0.65) for x in w_new]
        s = sum(w_new) + 1e-12
        w = [x/s for x in w_new]

    # Temperature
    Tq = 0.0
    cnt = 0
    for i in range(R):
        for j in range(i+1, R):
            Tq += 1.0 - _jaccard(top_sets[i], top_sets[j])
            cnt += 1
    Tq /= (cnt + 1e-12)

    alpha_eff = alpha * (Tq ** p)
    beta_eff = beta * (Tq ** p)

    z_c = _zscore(c)
    z_ind = _zscore(indep)

    # One-sided independence (v4.2): only boost independents, don't penalize followers
    if one_sided_independence:
        z_ind_eff = [max(0, z) for z in z_ind]
    else:
        z_ind_eff = z_ind

    # Reliability gate (v4.1 Ref 2) — skipped in v4.2
    mean_w = 1.0 / R
    reliability = [min(1.0, w[r] / mean_w) for r in range(R)]

    # Per-doc confidence (Ref 3)
    per_doc_conf = {}
    if use_per_doc_confidence and scores_per_ranker:
        for r, score_map in enumerate(scores_per_ranker):
            if not score_map:
                continue
            scores = list(score_map.values())
            if len(scores) < 2:
                continue
            mu = sum(scores) / len(scores)
            var = sum((sv - mu) ** 2 for sv in scores) / len(scores)
            std = max(math.sqrt(var), 1e-3)
            per_doc_conf[r] = {d: (sv - mu) / std for d, sv in score_map.items()}

    # Pre-compute per-ranker Type S modulation (for non-doc-local variants)
    m_C = [1.0] * R
    m_D_global = [1.0 + alpha_eff * z_c[r] for r in range(R)]
    if use_reliability_gate:
        m_S_global = [1.0 + beta_eff * z_ind_eff[r] * reliability[r] for r in range(R)]
    else:
        m_S_global = [1.0 + beta_eff * z_ind_eff[r] for r in range(R)]

    # Build document data
    doc_ranks = defaultdict(dict)
    for r, L in enumerate(lists):
        for idx, d in enumerate(L):
            doc_ranks[d][r] = idx

    # PACA: compute base ranking from consensus-weighted RRF (Phase 1 output)
    base_rank_map = {}
    if position_aware_attenuation:
        base_scores = _rrf_scores(lists, weights=w, k=k)
        base_ranked = _rank_from_scores(base_scores)
        base_rank_map = {d: i for i, d in enumerate(base_ranked)}

    # Fusion
    Final = defaultdict(float)
    for d, ranks in doc_ranks.items():
        cov = len(ranks) / R

        rank_vals = list(ranks.values())
        if len(rank_vals) >= 2:
            if use_contrib_space:
                contribs = [1.0 / (k + rv + 1) for rv in rank_vals]
                mu = sum(contribs) / len(contribs)
                var = sum((cv - mu) ** 2 for cv in contribs) / len(contribs)
                disp = math.sqrt(var) / (mu + 1e-12)
            else:
                mu = sum(rank_vals) / len(rank_vals)
                var = sum((rv - mu) ** 2 for rv in rank_vals) / len(rank_vals)
                disp = math.sqrt(var) / (mu + k)
        else:
            disp = 0.0

        p_C = cov * (1 - disp)
        p_D = cov * disp
        p_S = 1 - cov
        total = p_C + p_D + p_S + 1e-12

        # PACA: position factor for this document
        pos_factor = 1.0
        if position_aware_attenuation and k_protect > 0:
            br = base_rank_map.get(d, k_protect)  # unranked docs get full modulation
            pos_factor = min(1.0, br / k_protect)

        for r, rank_val in ranks.items():
            # ── Type D modulation ──
            z_conf = 0.0
            if per_doc_conf and r in per_doc_conf:
                z_conf = per_doc_conf[r].get(d, 0.0)
                if one_sided_confidence:
                    m_D_r = 1.0 + alpha_eff * max(0, z_conf) * pos_factor
                else:
                    m_D_r = 1.0 + alpha_eff * z_conf * pos_factor
            else:
                m_D_r = m_D_global[r] if pos_factor >= 1.0 else (
                    1.0 + (m_D_global[r] - 1.0) * pos_factor
                )

            # ── Type S modulation ──
            if conf_gated_independence and per_doc_conf:
                # v4.2: gate independence by per-doc confidence
                if r in per_doc_conf:
                    raw_conf = per_doc_conf[r].get(d, 0.0)
                    if conf_gate_type == 'sigmoid':
                        gate = _sigmoid(raw_conf)
                    elif conf_gate_type == 'relu':
                        gate = max(0, raw_conf)
                    elif conf_gate_type == 'bounded_relu':
                        gate = min(1.0, max(0, raw_conf))
                    else:
                        gate = _sigmoid(raw_conf)
                else:
                    gate = 1.0  # score-less ranker: full independence boost
                m_S_r = 1.0 + beta_eff * z_ind_eff[r] * gate
            else:
                m_S_r = m_S_global[r]

            mod = (p_C/total) * m_C[r] + (p_D/total) * m_D_r + (p_S/total) * m_S_r
            mod = max(mod_floor, mod)
            Final[d] += w[r] * mod / (k + rank_val + 1)

    return _rank_from_scores(dict(Final)), w, Tq, indep


# ================================================================
# SECTION 5: Evaluation Runner
# ================================================================

VARIANTS = {
    'Vanilla RRF': {},
    'v2.1':        {},
    'v3.0 DGAF':   {},
    'v4.0':        {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': False},
    'v4.0+Ref1':   {'use_contrib_space': True,  'use_reliability_gate': False, 'use_per_doc_confidence': False},
    'v4.0+Ref2':   {'use_contrib_space': False, 'use_reliability_gate': True,  'use_per_doc_confidence': False},
    'v4.0+Ref3':   {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': True},
    'v4.1':        {'use_contrib_space': True,  'use_reliability_gate': True,  'use_per_doc_confidence': True},
    # v4.2 variants: confidence-gated independence, one-sided modulation
    'v4.2-sig':    {'use_contrib_space': True,  'use_reliability_gate': False, 'use_per_doc_confidence': True,
                    'one_sided_confidence': True, 'one_sided_independence': True,
                    'conf_gated_independence': True, 'conf_gate_type': 'sigmoid'},
    'v4.2-relu':   {'use_contrib_space': True,  'use_reliability_gate': False, 'use_per_doc_confidence': True,
                    'one_sided_confidence': True, 'one_sided_independence': True,
                    'conf_gated_independence': True, 'conf_gate_type': 'relu'},
    'v4.2-brelu':  {'use_contrib_space': True,  'use_reliability_gate': False, 'use_per_doc_confidence': True,
                    'one_sided_confidence': True, 'one_sided_independence': True,
                    'conf_gated_independence': True, 'conf_gate_type': 'bounded_relu'},
    # Ablations: isolate one-sided vs confidence-gating
    'Ref3+1side':  {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': True,
                    'one_sided_confidence': True, 'one_sided_independence': False,
                    'conf_gated_independence': False},
    'Ref3+cgate':  {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': True,
                    'one_sided_confidence': False, 'one_sided_independence': True,
                    'conf_gated_independence': True, 'conf_gate_type': 'sigmoid'},
    # PACA: Position-Aware Confidence Attenuation (Ref3 + position protection)
    'PACA-K1':     {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': True,
                    'position_aware_attenuation': True, 'k_protect': 1},
    'PACA-K3':     {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': True,
                    'position_aware_attenuation': True, 'k_protect': 3},
    'PACA-K5':     {'use_contrib_space': False, 'use_reliability_gate': False, 'use_per_doc_confidence': True,
                    'position_aware_attenuation': True, 'k_protect': 5},
}


def evaluate_query(lists, confidences, scores_per_ranker, qrel, k=60):
    """Run all fusion variants on a single query, return per-variant metrics."""
    R = len(lists)
    results = {}

    # Vanilla RRF
    rank = fuse_vanilla_rrf(lists, k=k)
    results['Vanilla RRF'] = evaluate_ranking(rank, qrel)

    # v2.1
    rank_v21, w_v21, Tq_v21 = fuse_v21(lists, confidences, k=k)
    results['v2.1'] = evaluate_ranking(rank_v21, qrel)

    # v3.0 (needs v2.1 backbone output)
    C_v21 = _rrf_scores(lists, weights=w_v21, k=k)
    # Reconstruct specialist field for v3.0
    top_sets = [set(L[:30]) for L in lists]
    u = []
    for r in range(R):
        overlaps = [_jaccard(top_sets[r], top_sets[s]) for s in range(R) if s != r]
        m_ov = sum(overlaps) / (len(overlaps) + 1e-12)
        v_ov = sum((x - m_ov) ** 2 for x in overlaps) / (len(overlaps) + 1e-12)
        u.append(math.tanh(v_ov / (m_ov + 0.1)))

    fused_top = set(_rank_from_scores(C_v21)[:30])
    a = [_jaccard(set(L[:30]), fused_top) for L in lists]
    influence = []
    for r in range(R):
        w_m = [w_v21[j] for j in range(R) if j != r]
        l_m = [lists[j] for j in range(R) if j != r]
        sm = sum(w_m) + 1e-12
        w_m = [x/sm for x in w_m]
        fm = _rrf_scores(l_m, weights=w_m, k=k)
        rm = _rank_from_scores(fm)
        influence.append(1.0 - _jaccard(fused_top, set(rm[:30])))

    spec_scores = [confidences[r]*influence[r]*(1-a[r])*u[r] for r in range(R)]
    spec_idx = sorted(range(R), key=lambda r: spec_scores[r], reverse=True)[:2]
    spec_w = _softmax([max(spec_scores[r], 1e-8) for r in spec_idx], temp=0.7)

    S_v21 = defaultdict(float)
    for j, r in enumerate(spec_idx):
        for idx, d in enumerate(lists[r]):
            S_v21[d] += spec_w[j] / (k + idx + 1)

    rank_v3 = fuse_v3(lists, w_v21, Tq_v21, C_v21, dict(S_v21), k=k)
    results['v3.0 DGAF'] = evaluate_ranking(rank_v3, qrel)

    # v4.x variants (including v4.2)
    v4_variants = [v for v in VARIANTS if v not in ('Vanilla RRF', 'v2.1', 'v3.0 DGAF')]
    for vname in v4_variants:
        cfg = VARIANTS[vname]
        rank_v4, _, _, _ = fuse_v4x(
            lists, confidences, scores_per_ranker,
            k=k, **cfg
        )
        results[vname] = evaluate_ranking(rank_v4, qrel)

    return results


# ================================================================
# SECTION 6: Aggregate Evaluation
# ================================================================

def run_evaluation(runs: Dict[str, Dict[str, List[Tuple[str, int, float]]]],
                   qrels: Dict[str, Dict[str, int]],
                   k: int = 60) -> Dict:
    """
    Run full evaluation across all queries and variants.
    Returns aggregate metrics + per-query scores for statistical testing.
    """
    run_names = list(runs.keys())
    # Only evaluate queries present in both runs and qrels
    common_qids = set(qrels.keys())
    for rn in run_names:
        common_qids &= set(runs[rn].keys())

    if not common_qids:
        print("WARNING: No common query IDs between runs and qrels!")
        return {}

    print(f"  Evaluating {len(common_qids)} queries with {len(run_names)} rankers: {run_names}")

    # Per-query per-variant scores
    all_scores = defaultdict(lambda: defaultdict(list))  # {variant: {metric: [scores]}}
    n_queries = 0

    for qid in sorted(common_qids):
        lists, confidences, scores_per_ranker = runs_to_ranked_lists(runs, qid)
        if len(lists) < 2:
            continue

        qrel = qrels[qid]
        if not any(r > 0 for r in qrel.values()):
            continue  # skip queries with no relevant docs

        query_results = evaluate_query(lists, confidences, scores_per_ranker, qrel, k=k)
        for vname, metrics in query_results.items():
            for mname, val in metrics.items():
                all_scores[vname][mname].append(val)
        n_queries += 1

    # Aggregate
    aggregate = {}
    for vname in VARIANTS:
        if vname not in all_scores:
            continue
        agg = {}
        for mname in ['NDCG@10', 'NDCG@20', 'MAP@100', 'MRR']:
            scores = all_scores[vname][mname]
            if scores:
                lo, hi = bootstrap_ci(scores)
                agg[mname] = {
                    'mean': statistics.mean(scores),
                    'std': statistics.stdev(scores) if len(scores) >= 2 else 0,
                    'ci_lo': lo,
                    'ci_hi': hi,
                }
        aggregate[vname] = agg

    return {
        'aggregate': aggregate,
        'per_query': dict(all_scores),
        'n_queries': n_queries,
        'n_rankers': len(run_names),
        'run_names': run_names,
    }


# ================================================================
# SECTION 7: Report
# ================================================================

def print_evaluation_report(eval_result: Dict):
    agg = eval_result['aggregate']
    n_q = eval_result['n_queries']
    n_r = eval_result['n_rankers']

    print(f"\n{'='*100}")
    print(f" IC(R/W)-RRF Evaluation Report ".center(100))
    print(f"{'='*100}")
    print(f"  Queries: {n_q}  |  Rankers: {n_r}  |  Runs: {eval_result['run_names']}")

    # Main metrics table
    print(f"\n  {'Variant':<14}", end="")
    for m in ['NDCG@10', 'NDCG@20', 'MAP@100', 'MRR']:
        print(f" | {m:>18}", end="")
    print()
    print(f"  {'-'*90}")

    variant_order = ['Vanilla RRF', 'v2.1', 'v3.0 DGAF', 'v4.0',
                     'v4.0+Ref1', 'v4.0+Ref2', 'v4.0+Ref3', 'v4.1',
                     'v4.2-sig', 'v4.2-relu', 'v4.2-brelu',
                     'Ref3+1side', 'Ref3+cgate',
                     'PACA-K1', 'PACA-K3', 'PACA-K5']

    for vname in variant_order:
        if vname not in agg:
            continue
        print(f"  {vname:<14}", end="")
        for m in ['NDCG@10', 'NDCG@20', 'MAP@100', 'MRR']:
            if m in agg[vname]:
                v = agg[vname][m]
                print(f" | {v['mean']:.4f} ({v['ci_lo']:.3f}-{v['ci_hi']:.3f})", end="")
            else:
                print(f" | {'N/A':>18}", end="")
        print()

    # Statistical significance vs baseline (v2.1)
    pq = eval_result['per_query']
    if 'v2.1' in pq and 'NDCG@10' in pq['v2.1']:
        baseline = pq['v2.1']['NDCG@10']
        print(f"\n  STATISTICAL SIGNIFICANCE vs v2.1 (paired t-test on NDCG@10):")
        print(f"  {'Variant':<14} {'delta':>8} {'t-stat':>8} {'p-value':>10} {'Sig?':>6}")
        print(f"  {'-'*50}")

        for vname in variant_order:
            if vname == 'v2.1' or vname not in pq:
                continue
            scores = pq[vname].get('NDCG@10', [])
            if len(scores) != len(baseline):
                continue
            delta = statistics.mean(scores) - statistics.mean(baseline)
            t, p_val = paired_t_test(scores, baseline)
            sig = "**" if p_val < 0.01 else ("*" if p_val < 0.05 else "")
            print(f"  {vname:<14} {delta:>+8.4f} {t:>8.3f} {p_val:>10.4f} {sig:>6}")

    print(f"\n{'='*100}")


# ================================================================
# SECTION 8: Demo Mode (synthetic TREC-like data)
# ================================================================

def generate_demo_data(n_queries=50, n_docs=1000, k=100, R=4, seed=42):
    """
    Generate synthetic TREC-like data for demonstration.
    Creates a ground truth relevance, then generates R rankers with
    varying quality that partially recover the ground truth.
    """
    rng = random.Random(seed)

    qrels = {}
    runs = {f'ranker_{r}': {} for r in range(R)}

    ranker_qualities = [0.7, 0.5, 0.8, 0.4]  # ranker 2 is best, ranker 3 is worst

    for q in range(n_queries):
        qid = f'q{q:03d}'

        # Generate relevance judgments (graded: 0-3)
        doc_rels = {}
        for d in range(n_docs):
            did = f'd{d:04d}'
            # Power-law: few highly relevant, more somewhat relevant, most irrelevant
            p = rng.random()
            if p < 0.02:
                doc_rels[did] = 3
            elif p < 0.06:
                doc_rels[did] = 2
            elif p < 0.15:
                doc_rels[did] = 1
            else:
                doc_rels[did] = 0

        qrels[qid] = doc_rels

        # Generate ranker outputs
        relevant_docs = [(did, rel) for did, rel in doc_rels.items() if rel > 0]
        irrelevant_docs = [did for did, rel in doc_rels.items() if rel == 0]

        for r in range(R):
            quality = ranker_qualities[r]
            retrieved = []

            # Each ranker retrieves k docs: mix of relevant and irrelevant
            # Higher quality = more relevant docs at top
            rel_copy = list(relevant_docs)
            rng.shuffle(rel_copy)
            irr_copy = list(irrelevant_docs)
            rng.shuffle(irr_copy)

            for pos in range(k):
                # Probability of placing a relevant doc decreases with rank
                # Modified by ranker quality
                p_rel = quality * (1 - pos / k) * 0.6
                if rng.random() < p_rel and rel_copy:
                    did, rel = rel_copy.pop()
                    # Score correlates with relevance + noise
                    score = rel * 3 + rng.gauss(0, 1.0 / quality)
                    retrieved.append((did, pos, score))
                elif irr_copy:
                    did = irr_copy.pop()
                    score = rng.gauss(0, 0.5)
                    retrieved.append((did, pos, score))

            runs[f'ranker_{r}'][qid] = retrieved

    return runs, qrels


def run_demo():
    """Run evaluation on synthetic demo data."""
    print("Generating synthetic TREC-like data...")
    runs, qrels = generate_demo_data(n_queries=50, n_docs=500, k=100, R=4)

    print(f"  Generated {len(qrels)} queries, {len(runs)} rankers")
    print(f"  Relevant docs per query: "
          f"{statistics.mean(sum(1 for r in q.values() if r > 0) for q in qrels.values()):.1f} avg")

    result = run_evaluation(runs, qrels)
    if result:
        print_evaluation_report(result)
    return result


# ================================================================
# SECTION 9: CLI
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="IC(R/W)-RRF TREC Evaluation Harness")
    parser.add_argument('--qrels', type=str, help='Path to qrels file')
    parser.add_argument('--runs', nargs='+', type=str,
                        help='Paths to TREC run files')
    parser.add_argument('--run-dir', type=str,
                        help='Directory containing run files')
    parser.add_argument('--pattern', type=str, default='*.txt',
                        help='Glob pattern for run files in --run-dir')
    parser.add_argument('--k', type=int, default=60,
                        help='RRF constant k (default: 60)')
    parser.add_argument('--demo', action='store_true',
                        help='Run with synthetic demo data')

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.qrels:
        print("ERROR: --qrels required (or use --demo)")
        parser.print_help()
        sys.exit(1)

    # Collect run files
    run_paths = []
    if args.runs:
        run_paths.extend(args.runs)
    if args.run_dir:
        run_paths.extend(glob.glob(os.path.join(args.run_dir, args.pattern)))

    if len(run_paths) < 2:
        print(f"ERROR: Need at least 2 run files, got {len(run_paths)}")
        sys.exit(1)

    print(f"Loading {len(run_paths)} run files...")
    runs = {}
    for path in run_paths:
        name = Path(path).stem
        runs[name] = parse_run_file(path)
        n_queries = len(runs[name])
        print(f"  {name}: {n_queries} queries")

    print(f"\nLoading qrels from {args.qrels}...")
    qrels = parse_qrels(args.qrels)
    print(f"  {len(qrels)} queries with judgments")

    result = run_evaluation(runs, qrels, k=args.k)
    if result:
        print_evaluation_report(result)


if __name__ == "__main__":
    main()
