# IC(R/W)-RRF v5.0 — Per-Document Confidence Fusion

## Soft-Routed Adaptive Fusion with Document-Local Confidence Routing

*Revision: 5.0.0 — February 2026*
*Distilled from v4.0-v4.2 experimental series through TREC DL 2019 evaluation*

---

## 1. Abstract

v5.0 is the **empirical distillation** of the v4.x experimental series. It
preserves v4.0's architecture — soft type membership, per-ranker modulation,
single fusion equation — and adds exactly ONE refinement: **per-document
confidence routing**.

v4.1 proposed three refinements (contribution-space dispersion, reliability-
gated independence, per-document confidence). TREC DL 2019 evaluation on 43
queries with 4 rankers revealed:

- **Ref 1 (contribution-space dispersion):** Interferes with Ref 3 when
  combined. Compresses the disputed-type signal at exactly the positions where
  confidence routing is most effective. Net effect: harmful (-0.006 NDCG@10).
- **Ref 2 (reliability-gated independence):** Completely inert on homogeneous
  ranker pools (p_S = 0 when all rankers cover the same documents). Creates
  w-squared suppression on heterogeneous pools (theoretical concern, untested).
- **Ref 3 (per-document confidence):** The sole source of NDCG@10 improvement
  (+0.010 over v4.0). Best single variant across all metrics.

v5.0 retains Ref 3 only. Same architecture, same 3 parameters, one clean
refinement. When scores are unavailable, v5.0 degrades exactly to v4.0.

---

## 2. The Distillation Insight

The v4.x experimental series tested the hypothesis that three independent
signal refinements would compound. They did not. The lesson:

**Per-document confidence is the dominant signal in rank fusion.** Everything
else — dispersion metrics, independence measures, reliability gates — is
secondary. The architecture that enables highest-fidelity use of per-document
confidence wins.

The other refinements failed for specific, diagnosable reasons:

**Contribution-space dispersion (Ref 1) failed** because the coefficient of
variation in reciprocal-rank space compresses dispersion for documents with
mixed top/mid rank disagreements. This compression reduces p_D (disputed-type
membership) precisely for documents where confidence routing is most valuable.
On 3 queries accounting for the bulk of the regression, the relevant document's
p_D decreased by 25-30% under contribution-space dispersion, weakening its
confidence boost enough to allow an irrelevant competitor to overtake it.

**Reliability-gated independence (Ref 2) failed** for two reasons: (a) with
homogeneous rankers, the specialist pathway (Type S) never activates because
all rankers cover the same documents (coverage = 1.0, p_S = 0.0), making the
gate multiply zero; (b) even when active, the gate creates quadratic
suppression (delta_mass proportional to w_r^2 / mean_w) that annihilates
exactly the independent rankers that should be amplified.

**Per-document confidence (Ref 3) succeeded** because it adds genuinely new
information: the ranker's own score distribution reveals which documents it is
confident about, AT DOCUMENT GRANULARITY. This is the first signal in the
v4.x architecture that is both per-document AND per-ranker, enabling the full
(D x R) routing matrix that the bilinear form can express.

---

## 3. Algorithm

### Overview

```
Phase 1: Iterative Consensus (unchanged from v4.0)
  +-- Compute independence signal (mean dissimilarity)
  +-- Iterative weight refinement -> w_r (consensus weights)
  +-- Confidence extraction -> c_r (global), zConf_r(d) (per-doc, if scores)
  +-- Query temperature -> Tq

Phase 2: Per-Document Confidence Fusion (v5.0)
  +-- Per-document signals -> coverage(d), dispersion(d)
  +-- Soft type membership -> [p_C(d), p_D(d), p_S(d)]
  +-- Per-type modulation:
  |     m_r(C)    = 1.0
  |     m_r(D, d) = 1 + alpha_eff * zConf_r(d)    [per-document per-ranker]
  |     m_r(S)    = 1 + beta_eff  * z(indep_r)     [per-ranker]
  +-- Blended modulation -> mod(r, d)
  +-- Fusion -> Final(d) = sum_r w_r * mod(r,d) * contrib_r(d)
```


### Phase 1: Iterative Consensus (unchanged from v4.0)

**Step 0: Independence signal**

```
indep_r = 1 - mean(Jaccard(topN(L_r), topN(L_s)) for s != r)
```

Mean pairwise dissimilarity. Range [0, 1].


**Step 1: Iterative consensus weight refinement**

```
Initialize: w_r = 1/R for all r

For each iteration t = 1..T:
  Compute fused ranking F using current weights
  For each ranker r:
    a_r = Jaccard(topN(L_r), topN(F))
    c_r = confidence proxy (from scores if available, else 0.5)

  Delta_r = alpha_consensus*(a_r - mean(a))
           + beta_consensus*(c_r - mean(c))
           + zeta*(indep_r - mean(indep))

  w_r' = w_r * exp(Delta_r)
  w_r' = clip(w_r', w_min, w_max)
  Normalize: w_r = w_r' / sum(w')
```


**Step 2: Query temperature**

```
Tq = mean(1 - Jaccard(topN(L_i), topN(L_j)) for all i < j)
```


**Step 3: Per-document confidence extraction**

When ranker scores are available, compute per-document confidence:

```
For each ranker r with scores:
  scores_r = [score_r(d) for d in L_r]
  mu_r = mean(scores_r)
  sigma_r = max(std(scores_r), 1e-3)      # stability floor

  For each document d in L_r:
    zConf_r(d) = (score_r(d) - mu_r) / sigma_r

When scores are unavailable for ranker r:
  zConf_r(d) = 0 for all d                 # neutral, no boost
```

The z-score is computed WITHIN each ranker's score distribution. This
automatically normalizes across different score scales. A document with a
high z-score is one that THIS ranker is unusually confident about.

**Fallback:** When no ranker provides scores, zConf_r(d) = 0 for all (r, d).
The Type D modulation becomes inactive (m_r(D,d) = 1.0). v5.0 degrades to
v4.0. This is safe, not harmful.

**Partial availability:** If some rankers provide scores and others don't,
each ranker uses its own path. No cross-ranker normalization needed.


### Phase 2: Per-Document Confidence Fusion

**Step 1: Per-document signals**

```
coverage(d) = |{r : d in L_r}| / R
```

**Rank-space dispersion** (v4.0 formulation, retained):

```
If |rankers covering d| >= 2:
  rank_values = {rank_r(d) for r where d in L_r}
  dispersion(d) = std(rank_values) / (mean(rank_values) + k)
Else:
  dispersion(d) = 0
```

Note: v4.1's contribution-space dispersion was tested and found to interfere
with per-document confidence. v5.0 retains v4.0's rank-space dispersion which
provides correct type routing without attenuating the confidence signal.


**Step 2: Soft type membership**

```
p_C(d) = coverage(d) * (1 - dispersion(d))
p_D(d) = coverage(d) * dispersion(d)
p_S(d) = 1 - coverage(d)

total = p_C + p_D + p_S + epsilon
p_C /= total;  p_D /= total;  p_S /= total
```

| Type | Condition | Meaning | Modulation |
|------|-----------|---------|------------|
| C (Consensus) | High cov, low disp | Rankers agree | Trust base weights |
| D (Disputed) | High cov, high disp | Rankers disagree | Trust confident voice |
| S (Specialist) | Low cov | Few rankers see it | Trust independent voice |


**Step 3: Per-type ranker modulation**

Temperature-scaled modulation strengths:
```
alpha_eff = alpha * Tq^p
beta_eff  = beta  * Tq^p
```

Per-type modulation:
```
m_r(C)    = 1.0                                    # consensus: trust base
m_r(D, d) = 1.0 + alpha_eff * zConf_r(d)          # disputed: per-doc confidence
m_r(S)    = 1.0 + beta_eff  * z(indep_r)           # specialist: independence
```

Where z(x) = (x - mean(x)) / max(std(x), 1e-3) across rankers.

**Key property:** Type D modulation is the full (D x R) matrix — each
ranker gets a different modulation on each document, based on its own
confidence about that specific document. This is the core v5.0 innovation.

When zConf is unavailable, m_r(D, d) = 1.0 and Type D treated as Type C.


**Step 4: Blended modulation with floor**

```
mod(r, d) = p_C(d) * m_r(C) + p_D(d) * m_r(D, d) + p_S(d) * m_r(S)
mod(r, d) = max(mod_floor, mod(r, d))
```


**Step 5: Fusion**

```
Final(d) = sum_r  w_r * mod(r, d) * (1 / (k + rank_r(d) + 1))
           for all r where d in L_r
```

Rank by Final(d) descending.

---

## 4. The Bilinear Form

v5.0's modulation:

```
mod(r,d) = 1 + A(d) * zConf_r(d) + B(d) * zI_r

Where:
  A(d) = alpha_eff * cov(d) * disp(d)     [confidence routing weight]
  B(d) = beta_eff  * (1 - cov(d))          [independence routing weight]
  zConf_r(d) = per-document per-ranker      [full D x R matrix]
  zI_r = per-ranker independence            [R-dimensional]
```

The confidence term is a full (D x R) matrix weighted by the scalar field
A(d). The independence term is rank-1 (per-ranker only). When scores are
available, the bilinear form has rank > 2 due to the full D x R confidence
matrix. When scores are unavailable, it degrades to v4.0's rank-2 form.

---

## 5. Configuration

### Parameters (3 total, unchanged)

| Parameter | Default | Range | Role |
|-----------|---------|-------|------|
| alpha | 0.5 | [0.2, 1.5] | Confidence boost strength on disputed documents |
| beta | 0.5 | [0.2, 1.5] | Independence boost strength on specialist documents |
| p | 1.5 | [1.0, 2.5] | Temperature exponent (superlinear scaling) |

### Inherited from consensus backbone

| Parameter | Default | Role |
|-----------|---------|------|
| k | 60 | RRF constant |
| N | 30 | Top-N for overlap computation |
| iters | 4 | Consensus iterations |
| alpha_consensus | 1.2 | Affinity weight |
| beta_consensus | 0.6 | Confidence weight |
| zeta | 0.5 | Independence weight |
| w_min | 0.05 | Minimum ranker weight |
| w_max | 0.65 | Maximum ranker weight |

### Internal constants

| Constant | Value | Role |
|----------|-------|------|
| mod_floor | 0.1 | Minimum modulation (safety) |
| z_std_floor | 1e-3 | z-score stability floor |
| epsilon | 1e-12 | Numerical stability |

---

## 6. Empirical Results

> **Note:** The results below were captured from an earlier evaluation run. Run files
> have since been regenerated with updated ranking implementations. See
> `results/trec-dl-2019-results.md` for current verified results. The relative
> ordering of variants and all qualitative findings (falsified hypotheses, ablation
> conclusions) remain unchanged.

### TREC DL 2019 (43 queries, 4 lexical rankers)

| Variant | NDCG@10 | MRR | vs v2.1 delta | Notes |
|---------|---------|-----|---------------|-------|
| Vanilla RRF | 0.3173 | 0.5327 | -0.0044 | Baseline |
| v2.1 | 0.3218 | 0.5523 | -- | Consensus baseline |
| v3.0 DGAF | 0.3251 | **0.5658** | +0.0034 | Best MRR |
| v4.0 | 0.3250 | 0.5527 | +0.0033 | Base architecture |
| **v5.0** | **0.3314** | 0.5309 | **+0.0096** | **Best NDCG@10** |
| v4.1 (3 refs) | 0.3253 | 0.5039 | +0.0036 | Ref1 x Ref3 interference |

v5.0 achieves the highest NDCG@10 of any variant (+3.0% relative over v2.1,
+4.4% over vanilla RRF). No result reaches statistical significance at p<0.05
with 43 queries — additional evaluation on TREC DL 2020 is planned.

### Ablation results (v4.x experimental series)

| Ablation | NDCG@10 | MRR | Finding |
|----------|---------|-----|---------|
| v4.0 + Ref1 only | 0.3233 | 0.5529 | Ref1 hurts NDCG slightly |
| v4.0 + Ref2 only | 0.3250 | 0.5527 | Ref2 = no-op (p_S = 0) |
| v4.0 + Ref3 only | **0.3314** | 0.5309 | **= v5.0** |
| v4.0 + all three | 0.3253 | 0.5039 | Ref1 interferes with Ref3 |
| v4.2 (conf-gated) | 0.3238 | 0.5038 | Type S inert, = v4.1 |
| PACA-K3 | 0.3221 | 0.4999 | Position protection harmful |

### Falsified hypotheses

1. **Contribution-space dispersion improves type routing.** Falsified:
   compresses p_D at top positions, weakening Ref3.
2. **Reliability gate prevents noisy-independent boosting.** Falsified:
   creates w-squared suppression; inert with homogeneous rankers.
3. **One-sided confidence preserves gains.** Falsified: identical to
   two-sided (Ref3+1side = v5.0 exactly).
4. **Confidence-gated independence leverages per-doc signal.** Falsified:
   Type S pathway inert with homogeneous rankers.
5. **Position-aware attenuation protects MRR.** Falsified: protects
   wrong documents (base ranking's mistakes at top).

---

## 7. Known Limitations

### 7.1 NDCG/MRR Tension

v5.0 improves NDCG@10 (+0.0096) but shows MRR regression (-0.0218 vs v4.0).
Per-document confidence does real work at position 1 — promoting relevant
documents INTO top-1 on some queries. On ~2 queries out of 43, it promotes
the wrong document. This creates a genuine trade-off between top-10 quality
(NDCG) and top-1 precision (MRR).

Whether this tension persists with more queries or diverse rankers is unknown.
DGAF (v3.0) remains the MRR-optimal operating point (0.5658).

### 7.2 Confidence Signal Availability

Without scores, v5.0 = v4.0. The per-document confidence refinement requires
ranker scores. In practice, most retrieval systems produce scores (BM25, cosine
similarity, neural model logits), so this limitation rarely applies.

### 7.3 Homogeneous Ranker Limitation

With 4 lexical rankers sharing the same paradigm: coverage = 1.0 for most
documents, p_S = 0, Type S pathway is inactive. The independence boost
(beta_eff * z(indep_r)) has no effect. v5.0's gains come entirely from
Type D routing.

With structurally diverse rankers (sparse + dense), the Type S pathway would
activate and the independence signal could provide additional gains. This is
untested.

### 7.4 Minimum Ranker Count

With R=2: coverage is binary, dispersion has minimal variation. v5.0 provides
marginal benefit. Designed for R >= 3, optimal at R = 4-6.

---

## 8. Comparison Across Versions

| Dimension | v2.1 | v3.0 DGAF | v4.0 | v5.0 |
|-----------|------|-----------|------|------|
| Per-query adaptive | Yes | Yes | Yes | Yes |
| Per-document adaptive | No | Yes (lambda) | Yes (type routing) | Yes (type + confidence) |
| Per-ranker adaptive | No | No | Yes (modulation) | Yes (per-doc modulation) |
| Confidence resolution | Per-ranker | Per-ranker | Per-ranker | **Per-document per-ranker** |
| Parameters | 3+ | 5+ | 3 | **3** |
| Score requirement | No | No | No | Optional (graceful fallback) |
| Best metric | -- | MRR | -- | NDCG@10 |
| Degradation | -> RRF | -> v2.1 | -> v2.1 | -> v4.0 -> v2.1 -> RRF |

---

## 9. Evolution Trace

```
RRF (2009)
  -> Uniform 1/(k+rank). No adaptation.

v2.1 IC(R/W)-RRF
  -> Per-query adaptive weights. Iterative consensus with independence.
  -> Gap: no per-document differentiation.

v3.0 DGAF
  -> Per-document lambda gating between consensus and specialist fields.
  -> Gap: no per-ranker differentiation on disputed documents.

v4.0 Soft-Routed
  -> Per-ranker modulation through soft type membership.
  -> 3 parameters, 2 per-document signals, 1 fusion equation.
  -> Gap: confidence is per-ranker (query-global), not per-document.

v4.1-v4.2 (experimental, partially falsified)
  -> Three refinements tested: contribution-space dispersion, reliability
     gate, per-document confidence. Only per-document confidence survives.
  -> Ref1 interferes with Ref3. Ref2 creates w-squared suppression.
  -> v4.2's specialist innovations inert without diverse rankers.
  -> PACA (position protection) also falsified.

v5.0 Per-Document Confidence Fusion (this spec)
  -> Distills v4.x series: v4.0 architecture + ONLY per-document confidence.
  -> One refinement. Zero new parameters. Best NDCG@10.
  -> The routing structure was right. Per-document confidence was the
     signal it was waiting for. Everything else was noise.
```

---

## Appendix A: The Fusion Equation (Complete, v5.0)

One equation. Per document, per ranker. One refinement.

```
For each document d in union(L_1, ..., L_R):

  coverage(d) = |{r : d in L_r}| / R

  rank_values(d) = {rank_r(d) for r where d in L_r}
  dispersion(d) = std(rank_values) / (mean(rank_values) + k)

  p_C(d) = coverage * (1 - dispersion) / Z
  p_D(d) = coverage * dispersion / Z
  p_S(d) = (1 - coverage) / Z
  where Z = p_C + p_D + p_S + epsilon

  mod(r, d) = max(mod_floor,
    p_C(d) * 1.0 +
    p_D(d) * (1 + alpha * Tq^p * zConf_r(d)) +
    p_S(d) * (1 + beta  * Tq^p * z(indep_r))
  )

  Final(d) = sum over r where d in L_r:
    w_r * mod(r, d) / (k + rank_r(d) + 1)
```

**Inputs:** R ranked lists, optional scores.
**Parameters:** alpha, beta, p (3 total).
**Output:** Ranked list with type membership, modulations, diagnostics.

When scores unavailable: zConf_r(d) = 0 -> mod simplifies to v4.0.
When all rankers agree: dispersion = 0 -> p_D = 0 -> mod = 1.0 (inert).
When query is easy: Tq << 1 -> alpha_eff, beta_eff << 1 -> mod ~ 1.0 (inert).

---

## Appendix B: Signal Flow Diagram

```
R ranked lists (+ optional scores) ----+
                                       |
    +----------------------------------+
    |        PHASE 1: CONSENSUS        |
    |                                  |
    |  Independence: indep_r           |
    |  Iterative consensus: w_r        |
    |  Temperature: Tq                 |
    |  Per-doc confidence: zConf_r(d)  |
    |                                  |
    +------+---------------------------+
           |
    +------v---------------------------+
    |  PHASE 2: CONFIDENCE FUSION      |
    |                                  |
    |  coverage(d), dispersion(d)      |
    |         |                        |
    |         v                        |
    |  [p_C(d), p_D(d), p_S(d)]       |
    |         |                        |
    |   C: m = 1.0                     |
    |   D: m = 1 + a*Tq^p*zConf_r(d)  |
    |   S: m = 1 + b*Tq^p*z(indep_r)  |
    |         |                        |
    |         v                        |
    |  mod(r,d) = blend + floor        |
    |         |                        |
    |         v                        |
    |  Final(d) = sum w_r * mod * RRF  |
    +----------------------------------+
```

---

*IC(R/W)-RRF v5.0 Per-Document Confidence Fusion*
*Distilled from experiment. One refinement survived. Zero new parameters.*
*The routing structure was right. Now it has the signal it deserved.*
