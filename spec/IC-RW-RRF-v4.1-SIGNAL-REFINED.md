# IC(R/W)-RRF v4.1 — Signal-Refined Soft-Routed Adaptive Fusion

## Higher-Fidelity Routing Through Contribution-Space Dispersion, Reliability-Gated Independence, and Per-Document Confidence

*Revision: 4.1.0 — February 2026*
*Evolved from v4.0 through cross-model analysis and iterative refinement*

---

## 1. Abstract

v4.1 preserves v4.0's architecture unchanged — soft type membership, per-ranker
modulation, single fusion equation — while sharpening three signals that drive
the routing function. Each refinement increases signal fidelity without adding
parameters.

**Refinement 1: Contribution-space dispersion.** Rank-space dispersion treats
disagreement at rank 1 vs 2 identically to disagreement at rank 90 vs 91. But
in RRF, rank 1→2 is a large score difference while rank 90→91 is negligible.
v4.1 measures dispersion in the space where scores actually live: reciprocal
rank contributions. This makes disputed-type membership proportional to the
actual impact on the fused score.

**Refinement 2: Reliability-gated independence boost.** v4.0's independence
signal correctly identifies cabal members but cannot distinguish "independent
because it sees something others miss" from "independent because it's noisy."
v4.1 gates the independence boost by the ranker's consensus weight, ensuring
that only independent AND reasonably trusted rankers receive full specialist
boost.

**Refinement 3: Per-document confidence.** v4.0 uses a single confidence
value per ranker (query-global). v4.1 uses per-result score z-scores when
available, making Type D modulation truly document-local: "trust the ranker
that's confident about THIS specific document."

All three refinements are zero-parameter changes. v4.1 retains v4.0's
3-parameter configuration (alpha, beta, p). When scores are unavailable,
Refinement 3 is inactive and v4.1 degrades to v4.0 with Refinements 1-2.
When all rankers have identical independence profiles, Refinement 2 has no
effect and v4.1 degrades to v4.0 with Refinement 1 only.

---

## 2. The Signal Fidelity Insight

v4.0 created the right architecture: a rank-2 bilinear form that routes
per-document evidence to per-ranker modulation through soft type membership.
Algebraically (as revealed by cross-model analysis):

```
mod(r,d) = 1 + A(d)·zC_r + B(d)·zI_r

Where:
  A(d) = alpha_eff · coverage(d) · dispersion(d)    [confidence routing weight]
  B(d) = beta_eff  · (1 - coverage(d))              [independence routing weight]
  zC_r = z-score of ranker r's confidence
  zI_r = z-score of ranker r's independence
```

This is the minimum bilinear structure that creates real per-ranker routing.
The rank-2 form is not a limitation — it matches the information available
from two label-free signals (coverage, dispersion) and two ranker features
(confidence, independence). Adding architectural rank without additional
signal dimensions would be decorative.

But within this architecture, three of the four signal inputs were operating
at lower fidelity than necessary:

| Signal | v4.0 Fidelity | v4.1 Fidelity | What changes |
|--------|---------------|---------------|--------------|
| Coverage | Per-document | Per-document | Unchanged |
| Dispersion | Rank-space | **Contribution-space** | Measures impact, not position |
| Confidence (zC) | Per-ranker | **Per-document per-ranker** | When scores available |
| Independence (zI) | Per-ranker | Per-ranker × **reliability gate** | Attenuates noisy independents |

v4.1 sharpens each signal to its natural resolution. The routing structure
is identical; the inputs are higher-fidelity. Same architecture, sharper eyes.

---

## 3. Algorithm

### Overview

```
Phase 1: Iterative Consensus (unchanged from v4.0)
  ├── Compute independence signal (mean dissimilarity)
  ├── Iterative weight refinement → w_r (consensus weights)
  ├── Confidence extraction → c_r (global), c_r(d) (per-doc, if scores)
  └── Query temperature → Tq

Phase 2: Signal-Refined Soft-Routed Fusion (v4.1)
  ├── Per-document signals → coverage(d), dispersion_rrf(d)       [Ref 1]
  ├── Soft type membership → [p_C(d), p_D(d), p_S(d)]
  ├── Per-type modulation:
  │     m_r(C)    = 1.0
  │     m_r(D, d) = 1 + α_eff · zConf_r(d)                       [Ref 3]
  │     m_r(S)    = 1 + β_eff · z(indep_r) · reliability_r       [Ref 2]
  ├── Blended modulation → mod(r, d)
  └── Fusion → Final(d) = sum_r w_r · mod(r,d) · contrib_r(d)
```


### Phase 1: Iterative Consensus (unchanged from v4.0)

**Step 0: Independence signal**

```
indep_r = 1 - mean(Jaccard(topN(L_r), topN(L_s)) for s != r)
```

Unchanged. Mean pairwise dissimilarity. Range [0, 1].


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

Unchanged from v4.0. Produces consensus weights w_r and query temperature Tq.


**Step 2: Query temperature**

```
Tq = mean(1 - Jaccard(topN(L_i), topN(L_j)) for all i < j)
```

Unchanged.


**Step 3: Confidence extraction (v4.1 addition)**

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
automatically normalizes across different score scales (BM25 scores vs cosine
similarity vs proprietary scores). A document with a high z-score is one that
THIS ranker is unusually confident about, relative to its own distribution.

**Fallback behavior:** When no ranker provides scores, zConf_r(d) = 0 for all
(r, d) pairs. The Type D modulation becomes inactive (m_r(D,d) = 1.0 for
all r, d). Disputed documents are treated as consensus. This is identical to
v4.0's fallback behavior — safe, not harmful.

**Partial score availability:** If some rankers provide scores and others
don't, each ranker uses its own path (z-scored or zero). No cross-ranker
normalization is needed because z-scoring is within-ranker.


### Phase 2: Signal-Refined Soft-Routed Fusion

**Step 1: Per-document signals**

For each document d in the union of all ranked lists:

```
coverage(d) = |{r : d in L_r}| / R
```

**Contribution-space dispersion (Refinement 1):**

```
contribs_d = {1/(k + rank_r(d) + 1) : r where d in L_r}

If |contribs_d| >= 2:
  dispersion(d) = std(contribs_d) / (mean(contribs_d) + epsilon)
Else:
  dispersion(d) = 0
```

Where epsilon = 1e-12 (numerical stability only; mean(contribs) is always
positive for valid ranked lists).

**Why contribution-space:** Rank-space dispersion treats all rank differences
equally. But the fusion equation operates in reciprocal-rank space, where
rank 1→2 changes the contribution by ~2% while rank 90→91 changes it by
~0.04%. Measuring dispersion in contribution space makes "disagreement"
proportional to its actual impact on the fused score.

**Scale comparison with rank-space dispersion:**

```
Document at ranks [3, 15, 40, 80] with k=60:
  Rank-space:   std=33.2, mean=34.5, disp = 33.2/(34.5+60) = 0.35
  Contrib-space: std=0.0037, mean=0.0115, disp = 0.0037/0.0115 = 0.33

Document at ranks [1, 2] with k=60:
  Rank-space:   disp = 0.71/(1.5+60) = 0.012
  Contrib-space: disp = 0.00015/0.016 = 0.009

Document at ranks [90, 91] with k=60:
  Rank-space:   disp = 0.71/(90.5+60) = 0.005
  Contrib-space: disp = 0.000004/0.0066 = 0.0006
```

Contribution-space dispersion naturally attenuates tail disagreements (which
don't affect fusion) while preserving sensitivity to top-rank disagreements
(which do). The coefficient of variation (std/mean) is a natural measure in
contribution space because all values are positive and bounded.


**Step 2: Soft type membership**

```
p_C(d) = coverage(d) * (1 - dispersion(d))
p_D(d) = coverage(d) * dispersion(d)
p_S(d) = 1 - coverage(d)
```

Mathematically, p_C + p_D + p_S = 1 exactly (proof: p_C + p_D = cov*(1-disp)
+ cov*disp = cov; cov + p_S = cov + 1 - cov = 1). Normalization is
redundant but retained for numerical safety:

```
total = p_C + p_D + p_S + epsilon
p_C /= total;  p_D /= total;  p_S /= total
```

Type semantics unchanged from v4.0:

| Type | Condition | Meaning | Modulation Strategy |
|------|-----------|---------|---------------------|
| C (Consensus) | High cov, low disp | Rankers agree | Trust base weights |
| D (Disputed) | High cov, high disp | Rankers disagree on position | Trust confident voice |
| S (Specialist) | Low cov | Few rankers see it | Trust independent voice |


**Step 3: Per-type ranker modulation**

Temperature-scaled modulation strengths:
```
alpha_eff = alpha * Tq^p
beta_eff  = beta  * Tq^p
```

**Reliability gate (Refinement 2):**
```
reliability_r = min(1.0, w_r / mean(w))
```

Where w_r is ranker r's consensus weight from Phase 1 and mean(w) = 1/R
(since weights sum to 1). Range: [0, R]. In practice, with w_min = 0.05
and R=4, min reliability = 0.05/(1/4) = 0.2.

Interpretation: a ranker with average or above-average consensus weight
gets reliability = 1.0 (full independence boost). A ranker with below-
average consensus weight gets proportionally attenuated. A ranker at w_min
still gets 20% of the independence boost — suppressed, not silenced.

**Per-type modulation:**
```
m_r(C)    = 1.0                                          # consensus: base
m_r(D, d) = 1.0 + alpha_eff * zConf_r(d)                # disputed: per-doc
m_r(S)    = 1.0 + beta_eff  * z(indep_r) * reliability_r # specialist: gated
```

Where z(x) = (x - mean(x)) / max(std(x), 1e-3) across rankers (stability
floor prevents z-score explosion when all values are near-identical).

**Key difference from v4.0:** The Type D modulation now depends on (r, d)
jointly, not just r. When ranker r has a high score for document d relative
to its own distribution, it gets boosted on that document specifically.
This is the per-document confidence routing.

When zConf is unavailable (no scores), m_r(D, d) = 1.0 and Type D
documents are treated as Type C. This is safe degradation.


**Step 4: Blended modulation with floor**

For each document d and ranker r where d is in L_r:

```
mod(r, d) = p_C(d) * m_r(C) + p_D(d) * m_r(D, d) + p_S(d) * m_r(S)
mod(r, d) = max(mod_floor, mod(r, d))
```

The modulation floor (default 0.1) prevents inversion or silencing. Under
default parameters, the floor rarely activates.


**Step 5: Fusion**

```
Final(d) = sum_r  w_r * mod(r, d) * (1 / (k + rank_r(d) + 1))
           for all r where d in L_r
```

Rank by Final(d) descending.

Self-guarding property unchanged from v4.0: absent rankers contribute zero.

---

## 4. The Expanded Bilinear Form

v4.0's modulation was a pure rank-2 bilinear form:

```
v4.0: mod(r,d) = 1 + A(d)·zC_r + B(d)·zI_r
      Where A, B are document features; zC, zI are ranker features.
```

v4.1's modulation has a richer structure:

```
v4.1: mod(r,d) = 1 + A(d)·zConf_r(d) + B(d)·zI_r·rel_r

      Where:
        A(d) = alpha_eff · cov(d) · disp(d)     [per-document]
        B(d) = beta_eff  · (1 - cov(d))          [per-document]
        zConf_r(d) = per-document per-ranker      [full D×R matrix]
        zI_r · rel_r = per-ranker (gated)         [R-dimensional]
```

The confidence term is no longer an outer product — it's a full (D × R)
matrix weighted by the scalar field A(d). The independence term remains
rank-1 (per-ranker only) but is now modulated by the reliability gate.

This means v4.1 can express:
- **v4.0's capabilities** (per-ranker routing based on document type)
- **Per-document confidence routing** (trust ranker r MORE on document d
  where r has high confidence, LESS on document d' where r has low confidence)
- **Reliability-bounded independence** (prevent noisy-independent rankers
  from dominating specialist documents)

The architectural expressiveness increases while the parameter count stays
fixed at 3. The additional information comes from EXISTING data (scores,
consensus weights) used at higher resolution.

---

## 5. Configuration

### Parameters (unchanged from v4.0)

| Parameter | Default | Range | Role |
|-----------|---------|-------|------|
| alpha | 0.5 | [0.2, 1.5] | Confidence boost strength on disputed documents |
| beta | 0.5 | [0.2, 1.5] | Independence boost strength on specialist documents |
| p | 1.5 | [1.0, 2.5] | Temperature exponent (superlinear scaling) |

Three parameters. Same as v4.0. Each has a clear semantic role.

### Inherited from consensus backbone (unchanged)

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

**Change from v4.0:** z_std_floor replaces v4.0's epsilon (1e-12) in the
z-score denominator. This prevents z-score explosion when all values are
near-identical (e.g., all rankers have similar independence). At 1e-3, the
maximum z-score from near-identical values is bounded at ~1000/std_range
rather than ~1e12.


### Default behavior at operating points

**Easy query (Tq = 0.1):**
```
alpha_eff = 0.5 * 0.032 = 0.016
beta_eff  = 0.5 * 0.032 = 0.016
All modulations ≈ 1.0. Result ≈ v2.1 consensus.
(Identical to v4.0 — refinements have no effect at low Tq.)
```

**Hard query (Tq = 0.9), ranker r with high confidence on doc d:**
```
alpha_eff = 0.5 * 0.854 = 0.427
If zConf_r(d) = +2.0 (top-of-distribution score for this ranker):
  m_r(D, d) = 1 + 0.427 * 2.0 = 1.854
If zConf_r(d) = -1.0 (below-average score):
  m_r(D, d) = 1 + 0.427 * (-1.0) = 0.573

On the SAME document, different rankers get different Type D modulations
based on how confident THEY are about THIS document.
```

**Hard query, independent but low-weight ranker:**
```
beta_eff = 0.427, z(indep_r) = +1.73, w_r = 0.05 (minimum)
reliability_r = min(1.0, 0.05 / 0.25) = 0.2
m_r(S) = 1 + 0.427 * 1.73 * 0.2 = 1.148

Without reliability gate (v4.0):
m_r(S) = 1 + 0.427 * 1.73 = 1.739

The gate attenuated the boost from +74% to +15%. Still positive (the
ranker IS independent) but bounded by its low consensus trust.
```

---

## 6. Diagnostic Validation

### Expected behavior changes from v4.0

**Contribution-space dispersion:**
- Type D membership should be more concentrated on documents where top-rank
  disagreement exists, less on documents where disagreement is only in the tail.
- Overall p_D distribution should have higher variance (more separation between
  truly-disputed and merely-noisy documents).
- On Full Agreement scenarios: dispersion remains zero (unchanged).

**Reliability-gated independence:**
- Cabal scenario: independent ranker still boosted (z = +1.73) but now
  scaled by its reliability. If the independent ranker also has good
  consensus weight, the boost is preserved. If it has minimum weight
  (w_min = 0.05), the boost is attenuated to ~20% of v4.0 value.
- New test case needed: "Noisy Independent" scenario where one ranker is
  independent AND unreliable (random rankings). v4.1 should attenuate its
  boost; v4.0 would fully boost it.

**Per-document confidence:**
- On scenarios with score data: cross-ranker divergence should increase
  (different rankers get different modulations on the SAME document based
  on their per-result confidence).
- New metric: intra-document modulation variance. For a given document d,
  measure var({mod(r, d) for r where d in L_r}). This should increase
  relative to v4.0, especially on Type D documents.
- Without scores: v4.1 = v4.0 on all metrics (verified by comparison).

### Required diagnostic scenarios

| Scenario | Purpose | Key metric |
|----------|---------|------------|
| Full Agreement | Safe degradation | All mod = 1.0 (INERT) |
| Cabal (3+1) | Independence fix | Independent ranker boosted, reliability-gated |
| Noisy Independent | NEW: Reliability gate | Noisy ranker's boost attenuated |
| Moderate Disagreement | Type D activation | Contribution-space disp effect |
| Specialist Outlier | Cross-ranker divergence | v4.1 >= v4.0 divergence |
| Full Disagreement | Maximum adaptation | v4.1 >= v4.0 ranking changes |
| Score-Aware | NEW: Per-doc confidence | Intra-document mod variance |

### Diagnostic artifact

```
projects/rrf-research/diagnostics/v41_signal_refined_diagnostic.py
```

Should extend v4.0 diagnostic with:
- Contribution-space vs rank-space dispersion comparison
- Reliability gate effect measurement
- Score-aware scenario with per-document confidence metrics
- Side-by-side v4.0 vs v4.1 comparison on all scenarios

---

## 7. Comparison with v4.0

| Dimension | v4.0 | v4.1 |
|-----------|------|------|
| Architecture | Soft-routed, per-ranker modulation | **Identical** |
| Fusion equation | Single equation | **Same structure** |
| Parameters | 3 (alpha, beta, p) | **3 (identical)** |
| Signals | 2 (coverage, rank-space dispersion) | 2 (coverage, **contribution-space** dispersion) |
| Confidence resolution | Per-ranker (global) | **Per-document per-ranker** (when scores avail) |
| Independence guard | None | **Reliability-gated** |
| z-score stability | epsilon = 1e-12 | **std floor = 1e-3** |
| Bilinear form | Rank-2 (two outer products) | Rank-2 + **full D×R confidence** |
| Degradation | → v2.1 → RRF | → v4.0 → v2.1 → RRF |
| New failure modes | None removed | **Noisy-independent attenuated** |

v4.1 is not a new architecture. It is v4.0 with higher-resolution optics.
The routing mechanism is identical; the signals it routes on are sharper.

---

## 8. Known Limitations

### 8.1 Confidence Signal Availability (inherited, partially addressed)

When ranker scores are unavailable, the per-document confidence refinement
is inactive. v4.1 falls back to v4.0 behavior (Type D treated as Type C).
This limitation is inherent — without scores, there is no per-document
confidence signal to extract.

Partially addressed: when SOME rankers provide scores, those rankers
participate in per-document confidence while others default to neutral.
No all-or-nothing requirement.

### 8.2 Minimum Ranker Count (inherited)

With R=2: coverage is binary, dispersion has minimal variation, reliability
gate has limited effect. v4.1 provides marginal benefit at R=2. Designed
for R >= 3, optimal at R = 4-6.

### 8.3 Reliability Gate Conservatism

The reliability gate uses consensus weight as a quality proxy. But consensus
weight reflects agreement with the ensemble, which may itself be wrong
(especially in cabal scenarios where the majority is colluding). An
independent ranker that correctly disagrees with a cabal will have low
consensus weight AND high independence — the gate attenuates exactly the
ranker we should trust most.

Mitigation: the gate uses min(1.0, w_r / mean(w)), not a hard threshold.
Even at minimum weight, 20% of the independence boost passes through. And
in cabal scenarios with R=4, the independent ranker's consensus weight is
typically above w_min (the iterative consensus process gives it SOME credit
through the zeta * indep_r term).

This is a known tension between "trust the ensemble's quality estimate"
and "trust the outlier." v4.1 leans toward the ensemble but doesn't fully
silence outliers. Monitoring the diagnostic's cabal scenario behavior is
the recommended safety check.

### 8.4 Dispersion Scale in Contribution Space

Contribution-space dispersion uses the coefficient of variation (std/mean).
For documents where all including rankers place it at similar ranks, the
CV is near zero regardless of the rank level. For documents with wide rank
spread, the CV can approach 1.0+ in extreme cases.

The scale is well-behaved for typical retrieval scenarios (CV in [0, 0.5])
but could produce large values if one ranker places d at rank 1 and another
at rank K. The type membership formula handles this gracefully (p_D grows,
p_C shrinks) but extreme dispersion values should be monitored in
production diagnostics.

### 8.5 Score Distribution Assumptions

Per-document confidence uses z-scoring within each ranker's score
distribution. This assumes the distribution is unimodal and roughly
symmetric. Highly skewed or bimodal score distributions (common in some
neural retrievers) could produce misleading z-scores.

Mitigation: percentile-based normalization is an alternative when
distribution shape is unknown. But percentile ranking within a list is
equivalent to using the rank itself as the confidence signal, which removes
most of the benefit. z-scoring is the right default; distribution monitoring
is recommended for production deployment.

---

## 9. Implementation Guide (TypeScript)

### Module Structure

```
src/utils/
  rrf-algorithm.ts            ← existing vanilla RRF (unchanged)
  rrf-adaptive.ts             ← v4.1 signal-refined adaptive fusion
```

Single file, same as v4.0 target. The v4.1 refinements affect internal
computation only — the public API is unchanged from v4.0.


### Type Definitions

```typescript
// ── Configuration ──

interface AdaptiveFusionConfig {
  // RRF base
  k?: number;                  // RRF constant (default: 60)

  // Consensus backbone
  N?: number;                  // top-N for overlap (default: 30)
  iters?: number;              // consensus iterations (default: 4)
  wMin?: number;               // min ranker weight (default: 0.05)
  wMax?: number;               // max ranker weight (default: 0.65)

  // v4.1 modulation (same params as v4.0)
  alpha?: number;              // confidence boost (default: 0.5)
  beta?: number;               // independence boost (default: 0.5)
  tempExponent?: number;       // Tq exponent (default: 1.5)
  modFloor?: number;           // modulation floor (default: 0.1)
}

// ── Inputs ──

interface RankedList {
  id: string;                  // ranker identifier
  results: Array<{
    docId: string;
    rank: number;              // 0-indexed position
    score?: number;            // optional internal score (enables Ref 3)
  }>;
}

// ── Outputs ──

interface AdaptiveFusionResult {
  rankings: Array<{
    docId: string;
    score: number;             // final fused score
    rank: number;              // 0-indexed final position
    type: {                    // soft type membership
      consensus: number;
      disputed: number;
      specialist: number;
    };
    modulations: Record<string, number>;  // ranker_id → mod value
    sources: string[];         // which rankers included this doc
  }>;
  diagnostics: {
    Tq: number;
    consensusWeights: Record<string, number>;
    independence: Record<string, number>;
    reliability: Record<string, number>;       // v4.1: per-ranker
    alphaEff: number;
    betaEff: number;
    scoreAware: boolean;                       // v4.1: true if any scores
    typeCounts: {
      consensus: number;
      disputed: number;
      specialist: number;
    };
  };
}
```


### Core Implementation Skeleton

```typescript
export function adaptiveFusion(
  rankedLists: RankedList[],
  config: AdaptiveFusionConfig = {}
): AdaptiveFusionResult {
  const R = rankedLists.length;
  const k = config.k ?? 60;
  const N = config.N ?? 30;
  const Z_STD_FLOOR = 1e-3;

  // ── Phase 1: Consensus backbone ──
  const indep = computeIndependence(rankedLists, N);
  const { weights, Tq } = iterativeConsensus(rankedLists, indep, config);

  // Reliability gate (Refinement 2)
  const meanW = 1 / R;
  const reliability = weights.map(w => Math.min(1.0, w / meanW));

  // Per-document confidence extraction (Refinement 3)
  const scoreAware = rankedLists.some(rl =>
    rl.results.some(r => r.score !== undefined)
  );
  const perDocConf = scoreAware
    ? computePerDocConfidence(rankedLists, Z_STD_FLOOR)
    : null;  // null = fallback to neutral

  // ── Phase 2: Soft-routed fusion ──
  const alphaEff = (config.alpha ?? 0.5) * Math.pow(Tq, config.tempExponent ?? 1.5);
  const betaEff  = (config.beta  ?? 0.5) * Math.pow(Tq, config.tempExponent ?? 1.5);

  // z-scored independence (gated by reliability)
  const zI = zScore(indep, Z_STD_FLOOR);
  const gatedZI = zI.map((z, i) => z * reliability[i]);

  // Per-document fusion
  const docSignals = computeDocumentSignals(rankedLists, k);  // contribution-space
  const results = new Map<string, FusionEntry>();

  for (const [docId, signal] of docSignals) {
    const { coverage, dispersion, rankerEntries } = signal;

    // Soft type membership
    const pC = coverage * (1 - dispersion);
    const pD = coverage * dispersion;
    const pS = 1 - coverage;
    const total = pC + pD + pS + 1e-12;

    let score = 0;
    const mods: Record<string, number> = {};
    const sources: string[] = [];

    for (const { rankerIdx, rank } of rankerEntries) {
      // Per-document confidence for Type D
      const zConf = perDocConf
        ? (perDocConf.get(rankerIdx)?.get(docId) ?? 0)
        : 0;

      // Per-type modulation
      const mC = 1.0;
      const mD = 1.0 + alphaEff * zConf;
      const mS = 1.0 + betaEff * gatedZI[rankerIdx];

      // Blended
      const mod = Math.max(
        config.modFloor ?? 0.1,
        (pC / total) * mC + (pD / total) * mD + (pS / total) * mS
      );

      const contribution = weights[rankerIdx] * mod / (k + rank + 1);
      score += contribution;
      mods[rankedLists[rankerIdx].id] = mod;
      sources.push(rankedLists[rankerIdx].id);
    }

    results.set(docId, {
      score,
      type: { consensus: pC/total, disputed: pD/total, specialist: pS/total },
      mods,
      sources,
    });
  }

  // Sort and return
  const sorted = [...results.entries()]
    .sort(([,a], [,b]) => b.score - a.score);

  return {
    rankings: sorted.map(([docId, data], idx) => ({
      docId, score: data.score, rank: idx,
      type: data.type, modulations: data.mods, sources: data.sources,
    })),
    diagnostics: {
      Tq,
      consensusWeights: Object.fromEntries(
        rankedLists.map((rl, i) => [rl.id, weights[i]])
      ),
      independence: Object.fromEntries(
        rankedLists.map((rl, i) => [rl.id, indep[i]])
      ),
      reliability: Object.fromEntries(
        rankedLists.map((rl, i) => [rl.id, reliability[i]])
      ),
      alphaEff,
      betaEff,
      scoreAware,
      typeCounts: countTypes(sorted),
    },
  };
}


// ── Signal computation (Refinement 1: contribution-space) ──

function computeDocumentSignals(
  rankedLists: RankedList[],
  k: number
): Map<string, DocumentSignal> {
  const docMap = new Map<string, Array<{ rankerIdx: number; rank: number }>>();

  for (let i = 0; i < rankedLists.length; i++) {
    for (const result of rankedLists[i].results) {
      if (!docMap.has(result.docId)) docMap.set(result.docId, []);
      docMap.get(result.docId)!.push({ rankerIdx: i, rank: result.rank });
    }
  }

  const R = rankedLists.length;
  const signals = new Map<string, DocumentSignal>();

  for (const [docId, entries] of docMap) {
    const coverage = entries.length / R;

    let dispersion = 0;
    if (entries.length >= 2) {
      // Contribution-space dispersion
      const contribs = entries.map(e => 1 / (k + e.rank + 1));
      const mean = contribs.reduce((s, c) => s + c, 0) / contribs.length;
      const variance = contribs.reduce((s, c) => s + (c - mean) ** 2, 0)
                       / contribs.length;
      const std = Math.sqrt(variance);
      dispersion = std / (mean + 1e-12);
    }

    signals.set(docId, { coverage, dispersion, rankerEntries: entries });
  }

  return signals;
}


// ── Per-document confidence (Refinement 3) ──

function computePerDocConfidence(
  rankedLists: RankedList[],
  stdFloor: number
): Map<number, Map<string, number>> {
  const result = new Map<number, Map<string, number>>();

  for (let i = 0; i < rankedLists.length; i++) {
    const scores = rankedLists[i].results
      .filter(r => r.score !== undefined)
      .map(r => r.score!);

    if (scores.length < 2) continue;

    const mean = scores.reduce((s, v) => s + v, 0) / scores.length;
    const variance = scores.reduce((s, v) => s + (v - mean) ** 2, 0)
                     / scores.length;
    const std = Math.max(Math.sqrt(variance), stdFloor);

    const docConf = new Map<string, number>();
    for (const r of rankedLists[i].results) {
      if (r.score !== undefined) {
        docConf.set(r.docId, (r.score - mean) / std);
      }
      // Documents without scores get zConf = 0 (implicit via ?? 0)
    }
    result.set(i, docConf);
  }

  return result;
}


// ── Utilities ──

function zScore(values: number[], stdFloor: number): number[] {
  const mean = values.reduce((s, v) => s + v, 0) / values.length;
  const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0)
                   / values.length;
  const std = Math.max(Math.sqrt(variance), stdFloor);
  return values.map(v => (v - mean) / std);
}
```

---

## 10. Complexity Analysis

| Component | Time | Space | Notes |
|-----------|------|-------|-------|
| Independence signal | O(R^2 * N) | O(R) | Unchanged |
| Iterative consensus | O(T * R * K) | O(R * K) | Unchanged |
| Document signals | O(R * K) | O(D) | Contribution-space: same cost |
| Per-doc confidence | O(R * K) | O(R * D) | NEW: z-score per result |
| Type membership | O(D) | O(D) | Unchanged |
| z-score + reliability | O(R) | O(R) | Unchanged |
| Per-doc modulation | O(D * R_avg) | O(D) | Unchanged |
| **Total** | **O(T*R*K)** | **O(R*D)** | Space: R*D from per-doc conf |

Per-document confidence adds O(R * D) space (storing z-scores for each
ranker-document pair). For typical K=100, R=4: 400 entries. Negligible.
Time complexity unchanged — the per-document z-scoring is a single pass
over each ranked list, already dominated by the iterative consensus step.

---

## 11. Falsification Criteria

Inherited from v4.0, with additions:

1. **v4.1 <= v4.0 on NDCG@10** across evaluation datasets. If the signal
   refinements don't improve relevance, they add complexity without benefit.

2. **Contribution-space dispersion produces identical type distributions**
   to rank-space dispersion on >90% of queries. If both dispersion measures
   produce the same routing, the change is cosmetic.

3. **Reliability gate attenuates ALL independent rankers equally.** If the
   gate doesn't differentiate trusted-independent from noisy-independent,
   it uniformly reduces the independence boost without adding information.

4. **Per-document confidence z-scores are uniform within each ranker** (no
   variance in zConf_r(d) across documents). If scores don't discriminate
   within a ranker's list, per-document confidence adds nothing over
   per-ranker confidence.

**Minimal disconfirming experiment:** Run v4.1 and v4.0 on identical
synthetic and TREC scenarios. Per-refinement ablation:
- v4.0 baseline
- v4.0 + Ref 1 only (contribution-space dispersion)
- v4.0 + Ref 2 only (reliability gate)
- v4.0 + Ref 3 only (per-document confidence)
- v4.1 (all three)

If no individual refinement produces measurable change AND the combined
v4.1 doesn't either, all three refinements are falsified.

---

## 12. Evolution Trace

```
RRF (2009)
  → Uniform 1/(k+rank) across all rankers and documents
  → Intention: per-item adaptive fusion. Mechanism: per-query uniform.

v2.1 IC(R/W)-RRF
  → Per-query adaptive weighting (iterative consensus)
  → Gap: query-global lambda, broken uniqueness

v3.0 DGAF
  → Per-document lambda gating, 3 signals, impedance architecture
  → Gap: two-field bottleneck, no per-ranker differentiation

v4.0 Soft-Routed
  → Per-ranker modulation, soft type membership, independence fix
  → 3 parameters, 2 signals, 1 equation
  → Gap: signals at lower fidelity than architecture can use

v4.1 Signal-Refined
  → Same architecture, sharper signals
  → Contribution-space dispersion (measures impact, not position)
  → Reliability-gated independence (quality-bounds the diversity signal)
  → Per-document confidence (when scores exist)
  → Still 3 parameters. Still 1 equation. Higher-fidelity routing.
```

---

## Appendix A: The Fusion Equation (Complete, v4.1)

One equation. Per document, per ranker. Three refinements marked.

```
For each document d in union(L_1, ..., L_R):

  coverage(d) = |{r : d in L_r}| / R

  contribs(d) = {1/(k + rank_r(d) + 1) for r where d in L_r}       ← [Ref 1]
  dispersion(d) = std(contribs(d)) / (mean(contribs(d)) + epsilon)  ← [Ref 1]

  p_C(d) = coverage * (1 - dispersion) / Z
  p_D(d) = coverage * dispersion / Z
  p_S(d) = (1 - coverage) / Z
  where Z = p_C + p_D + p_S + epsilon

  reliability_r = min(1.0, w_r / mean(w))                           ← [Ref 2]

  mod(r, d) = max(mod_floor,
    p_C(d) * 1.0 +
    p_D(d) * (1 + alpha * Tq^p * zConf_r(d)) +                     ← [Ref 3]
    p_S(d) * (1 + beta  * Tq^p * z(indep_r) * reliability_r)       ← [Ref 2]
  )

  Final(d) = sum over r where d in L_r:
    w_r * mod(r, d) / (k + rank_r(d) + 1)
```

**Inputs:** R ranked lists, optional scores.
**Parameters:** alpha, beta, p (3 total, unchanged from v4.0).
**Output:** Ranked list with type membership, modulations, reliability diagnostics.

---

## Appendix B: Signal Flow Diagram

```
R ranked lists (+ optional scores) ─────────────────────────────────────────┐
                                                                             │
    ┌────────────────────────────────────────────────────────────────────────┤
    │              PHASE 1: CONSENSUS BACKBONE                              │
    │                                                                       │
    │  Independence: indep_r = 1 - mean(Jaccard_pairwise)                  │
    │  Iterative consensus: w_r (with independence)                        │
    │  Temperature: Tq = mean(pairwise dissimilarity)                      │
    │  Reliability: rel_r = min(1, w_r/mean(w))         ◄── [Ref 2]       │
    │  Per-doc confidence: zConf_r(d) from scores       ◄── [Ref 3]       │
    │                                                                       │
    │  Outputs: w_r, Tq, indep_r, rel_r, zConf_r(d)                       │
    └───────┬───────────────────────────────────────────────────────────────┘
            │
    ┌───────▼───────────────────────────────────────────────────────────────┐
    │              PHASE 2: SIGNAL-REFINED SOFT-ROUTED FUSION              │
    │                                                                       │
    │  Per-doc signals:                                                     │
    │    coverage(d) ◄── raw lists                                         │
    │    dispersion(d) ◄── contribution-space CV           [Ref 1]         │
    │         │                                                             │
    │         ▼                                                             │
    │  Soft type membership: [p_C(d), p_D(d), p_S(d)]                     │
    │         │                                                             │
    │         ├── Type C: m_r = 1.0                                        │
    │         ├── Type D: m_r = 1 + α·Tq^p · zConf_r(d)       [Ref 3]    │
    │         └── Type S: m_r = 1 + β·Tq^p · z(indep)·rel_r   [Ref 2]    │
    │                │                                                      │
    │                ▼                                                      │
    │  Blended: mod(r,d) = max(floor, Σ p_T(d) · m_r(T, d))              │
    │                │                                                      │
    │                ▼                                                      │
    │  Final(d) = Σ_r  w_r · mod(r,d) · 1/(k + rank_r(d) + 1)           │
    │                │                                                      │
    │                ▼                                                      │
    │  Ranked output + type labels + modulation diagnostics                │
    │  + reliability scores + score-awareness flag                          │
    └───────────────────────────────────────────────────────────────────────┘
```

---

*IC(R/W)-RRF v4.1 Signal-Refined Soft-Routed Adaptive Fusion*
*Same architecture. Sharper signals. Zero new parameters.*
*The routing structure was right. Now it sees more clearly.*
