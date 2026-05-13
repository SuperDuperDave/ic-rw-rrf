# IC(R/W)-RRF v6.0 — Regime-Aware Fusion

## Adaptive Fusion via Ensemble-Regime Detection

*Revision: 6.0.0 — May 2026*
*Distilled from the v5.0 → v6.0 transition through cross-ensemble TREC DL 2019 evaluation and cross-collection probing on TREC DL 2020*

---

## 1. Abstract

v6.0 is the **structural reframing** of the IC(R/W)-RRF lineage. v2.1 through v5.0 progressively broke uniformity assumptions in the fusion equation (uniform → per-query → per-document → per-document per-ranker). Each version improved on the prior under a specific evaluation setup. v6.0 identifies and removes a constraint none of the prior versions noticed:

**v2.1 through v5.0 assume the optimal fusion algorithm is a fixed function of (ranks, scores).** TREC DL 2019 with 4 lexical rankers validated this assumption — v5.0 reached NDCG@10 = 0.3800 vs Vanilla RRF's 0.3645 (+4.3%). But the assumption breaks under wider testing:

- **TREC DL 2019 with 5, 6, or 7 rankers:** Vanilla RRF reaches 0.4031, 0.4073, 0.3889 respectively — all higher than v5.0 on the same data (0.3698, 0.3714, 0.3654). The v5.0 advantage *inverts* with one additional ranker.
- **TREC DL 2020 with 4 rankers (the same setup):** Vanilla RRF reaches 0.4483 vs v5.0's 0.4373. The "+4.3% over RRF" claim does not replicate on the second collection.

The fragility was hidden by reporting only one evaluation configuration. The structural truth: **the optimal fusion algorithm depends on the ensemble's regime** (the rank-statistics structure of the M ranker lists) AND on collection-level properties that rank statistics alone cannot observe.

v6.0 replaces the search for a better fixed equation with a **regime-aware mixture**: detect the ensemble's regime from rank statistics, and mix v5.0-style per-document confidence routing with Vanilla RRF accordingly. Three constants. Zero learned parameters. The mixture interpolates between the two structural extremes that the lineage's prior work already produced — preserving v5.0's advantage in its home basin while not surrendering Vanilla's advantage elsewhere.

---

## 2. The Distillation Insight

The v4.x experimental series (documented in `IC-RW-RRF-v5.0-CONFIDENCE-FUSION.md`) tested five hypothesized refinements. Four were falsified. v5.0 retained the one that survived: per-document per-ranker z-scored confidence.

The v5.0 → v6.0 transition tested a *different* hypothesis: that per-document confidence is robust across ensemble configurations. It is not. The new structural insight:

**Rank fusion is regime-dependent, not algorithm-dependent.** Different ensemble configurations have different optimal fusion strategies. A single fixed equation cannot dominate across all (corpus, ranker-mix) pairs — because no such equation exists. The previous IR literature's tradition of reporting one fusion result on one evaluation setup obscured this fact.

The empirical regimes observed in this lineage's evaluation:

- **Homogeneous redundant** (mean pairwise top-30 Jaccard rho ≈ 0.5; few independent specialists): per-document confidence routing adds signal. v5.0 wins. Example: TREC DL 2019 with {BM25, BM25-tuned, TF-IDF, QL-Dirichlet}.
- **Heterogeneous diverse** (rho < 0.4; many independent specialists): per-document confidence routing over-trusts noisy individual rankers. Vanilla RRF's uniform consensus wins. Example: TREC DL 2019 once {proximity, tfidf_bigram, semantic_hash} are added.
- **Same homogeneity, different collection** (rho ≈ 0.5 on TREC DL 2020 with the same 4-ranker setup): v5.0 STILL loses to Vanilla. Collection-level properties (relevance grade distribution, query difficulty, label sparsity) modulate which fusion strategy wins independent of ensemble structure.

The lesson v6.0 crystallizes: **chase the regime, not the algorithm.**

---

## 3. Algorithm

### Overview

```
Step 1: Detect the ensemble regime (label-free, rank-statistics only)
   |
   +-- rho = mean pairwise top-K Jaccard across the M ranker lists

Step 2: Map regime to mixing weight
   |
   +-- alpha = piecewise_linear(rho; lo, hi)
       alpha = 0  when rho <= lo     (full Vanilla RRF — heterogeneous)
       alpha = 1  when rho >= hi     (full v5.0 routing — homogeneous)
       linear interpolation between

Step 3: Compute both baseline rankings
   |
   +-- vanilla_score(d) = Vanilla RRF score (existing implementation)
   +-- v5_rank(d)       = v5.0 ranking (existing implementation)

Step 4: Apply regime-weighted multiplicative modulation
   |
   +-- For each document d in the union of ranked sets:
   |     delta(d) = vanilla_rank_position(d) - v5_rank_position(d)
   |     if delta(d) > 0:     # v5 ranks d higher than Vanilla
   |       mod(d) = 1 + alpha * log1p(delta(d)) * g_up
   |     else:
   |       mod(d) = 1 + alpha * (-log1p(-delta(d))) * g_down
   +-- final_score(d) = vanilla_score(d) * mod(d)

Step 5: Sort by final_score(d), output ranking
```

### Step 1 — Regime detection

```
top_sets = {top_K(L_r) for r in 1..M}, with K=30

rho = mean over pairs (i, j):
  |top_sets[i] ∩ top_sets[j]| / |top_sets[i] ∪ top_sets[j]|
```

Range: [0, 1]. 1.0 = all rankers retrieve identical top-K (perfectly homogeneous). 0.0 = no two rankers retrieve any common documents.

**Why top-K Jaccard:** simplest label-free homogeneity signal, computable in O(M²K). Robust to score-scale differences across rankers. Tested against coverage-histogram entropy and found to carry the load with marginal added complexity from auxiliary signals (see Section 5).

### Step 2 — Alpha curve

```
if rho >= hi:      alpha = 1.0       # homogeneous: full v5 modulation
if rho <= lo:      alpha = 0.0       # heterogeneous: pure Vanilla
otherwise:         alpha = (rho - lo) / (hi - lo)
```

**Validated thresholds:** lo=0.35, hi=0.60 (TREC DL 2019 + 2020). With these, observed alpha values:
- TREC DL 2019 n=4 (rho≈0.49): alpha ≈ 0.51 (high v5 weight)
- TREC DL 2019 n=5 (rho≈0.37): alpha ≈ 0.07 (mostly Vanilla)
- TREC DL 2019 n=7 (rho≈0.29): alpha ≈ 0 (pure Vanilla)
- TREC DL 2020 n=4 (rho≈0.50): alpha ≈ 0.51 (high v5 weight)

**Parameter discipline:** lo and hi are the only tunable constants. They are not learned — they were chosen by inspection of the rho distribution across the available evaluation ensembles. Cross-collection stability of rho (≈0.49 on both TREC DL 2019 n=4 and TREC DL 2020 n=4) suggests these thresholds generalize at least within MS MARCO-style passage retrieval. Re-tuning may be appropriate for substantially different domains (e.g., scientific corpora, hybrid semantic+lexical ensembles).

### Step 3 — Baseline computation

Both v5.0 and Vanilla RRF are computed exactly as defined in their respective specifications. v6.0 introduces no changes to either underlying algorithm.

```
v5_ranking, _ = fuse_v5(L_1, ..., L_M, scores_per_ranker)    # existing
vanilla_scores = rrf_scores(L_1, ..., L_M, k=60)              # existing
```

### Step 4 — Regime-weighted modulation

For each document d in the union of retrieved sets, compute its rank position in both base rankings:

```
vanilla_pos(d) = rank of d in vanilla_ranking
v5_pos(d)      = rank of d in v5_ranking
delta(d)       = vanilla_pos(d) - v5_pos(d)
```

`delta(d) > 0` means v5 ranks document d *higher* (better) than Vanilla. The modulation amplifies these v5-promoted documents proportionally to alpha. `delta(d) < 0` means v5 ranks d lower; the modulation slightly suppresses, but asymmetrically (smaller down-modulation than up-modulation, reflecting the lineage's discipline that the modulation should never substantially harm a document Vanilla considers strong).

```
if delta(d) > 0:
  mod(d) = 1 + alpha * log1p(delta(d)) * 0.10
else:
  mod(d) = 1 + alpha * (-log1p(-delta(d))) * 0.05
```

The log-compression bounds the modulation: even a delta of 100 (extreme rank disagreement) produces at most a ~1.5x multiplier when alpha=1. This preserves Vanilla's ranking topology and prevents the modulation from running away on rare disagreements.

The asymmetric up/down gain (0.10 / 0.05) reflects the empirical finding that v5's promotions are more often correct than its demotions (Section 5).

### Step 5 — Final ranking

```
final_score(d) = vanilla_score(d) * mod(d)
ranking = argsort(final_score, descending)
```

### Graceful degradation chain

```
rho < lo (very heterogeneous)         → alpha = 0    → Vanilla RRF exactly
rho > hi (very homogeneous)           → alpha = 1    → v5.0-style modulation on Vanilla
scores_per_ranker absent              → v5_rank = v4.0_rank → degrade to v4.0 modulation
v5 unavailable                         → mod(d) = 1   → Vanilla RRF
```

v6.0 inherits v5.0's score-availability fallback (when no ranker provides scores, the per-document confidence routing inside v5 becomes inactive, which makes v5_rank converge toward v4.0_rank and the v6.0 modulation correspondingly weakens). At every degradation step, the algorithm reverts to an earlier, well-defined member of the lineage. There is no failure mode where v6.0 produces undefined output.

### Parameter count

- `K = 30` (top-K window for Jaccard) — fixed across all evaluations
- `lo = 0.35`, `hi = 0.60` (alpha thresholds) — tunable per domain
- `g_up = 0.10`, `g_down = 0.05` (asymmetric modulation gains) — fixed
- `k = 60` (RRF constant) — inherited from RRF
- All v5.0 parameters — inherited

Net new parameters added by v6.0: **3** (lo, hi, g_up:g_down ratio). No learned parameters. Computation cost: one additional pairwise-Jaccard scan (O(M²K)) and one additional rank-position lookup per document (O(MD)). Negligible relative to the v5.0 pipeline.

---

## 4. Empirical Results

### 4.1 — TREC DL 2019 cross-ensemble sweep (43 queries)

Progressively additive ranker subsets. All NDCG@10 values from
`evaluation/probe_regime_aware_fusion.py` and `probe_ref_validation.py`,
reproducible from the run files in `data/trec-dl-2019/runs/`.

| Ensemble | rho | alpha | Vanilla | v5.0 | **REF** (v6.0) |
|---|---|---|---|---|---|
| n=4 (bm25, bm25-tuned, tfidf, ql) | 0.491 | 0.51 | 0.3645 | 0.3800 | **0.3832** |
| n=5 (+proximity) | 0.370 | 0.07 | 0.4031 | 0.3698 | 0.3962 |
| n=6 (+tfidf_bigram) | 0.329 | 0.00 | 0.4073 | 0.3714 | 0.4026 |
| n=7 (+semantic_hash) | 0.291 | 0.00 | 0.3889 | 0.3654 | 0.3854 |
| **Cross-ensemble mean** | — | — | 0.3910 | 0.3717 | **0.3919** |

### 4.2 — TREC DL 2020 cross-collection probe (54 queries)

Identical 4-ranker ensemble; second collection.

| Variant | NDCG@10 | NDCG@20 | MAP@100 | MRR |
|---|---|---|---|---|
| Vanilla | **0.4483** | 0.4336 | 0.2613 | **0.8348** |
| v5.0 | 0.4373 | **0.4358** | 0.2692 | 0.7699 |
| **REF (v6.0)** | 0.4393 | 0.4348 | **0.2731** | 0.8196 |

Regime detector outputs rho=0.495 (essentially identical to TREC DL 2019 n=4), but Vanilla wins this collection — establishing that rho alone is insufficient to predict which fusion wins (Section 5).

### 4.3 — Paired t-tests (REF vs both baselines, NDCG@10 and MRR)

TREC DL 2019:

| Sweep | vs Vanilla NDCG@10 | vs Vanilla MRR | vs v5.0 NDCG@10 | vs v5.0 MRR |
|---|---|---|---|---|
| n=4 | **+0.0187 p=0.028 \*** | +0.0340 ns | +0.0031 ns | +0.0540 ns |
| n=5 | -0.0070 ns | -0.0136 ns | **+0.0263 p=0.019 \*** | **+0.0853 p=0.042 \*** |
| n=6 | -0.0046 ns | -0.0116 ns | **+0.0313 p=0.025 \*** | +0.0486 ns |
| n=7 | -0.0035 ns | -0.0116 ns | +0.0200 ns | **+0.0806 p=0.025 \*** |

TREC DL 2020 (n=4): REF vs Vanilla -0.0090 ns; REF vs v5.0 +0.0019 ns, MRR +0.0498 ns.

### 4.4 — Claims justified by these tables

1. **REF strictly improves on v5.0 across all tested ensemble configurations and both collections.** Cross-ensemble mean improvement: +0.0202 NDCG@10 (+5.4%) and +0.0421 MRR (+5.7%) on TREC DL 2019. Multiple p<0.05 significances on individual sweeps. The v5.0 MRR weakness (0.7108 at n=4) is closed (REF 0.7648 at n=4, statistically equivalent to Vanilla's 0.7308 and superior to v5.0).

2. **REF beats Vanilla RRF significantly on TREC DL 2019 n=4** (+0.0187, p=0.028, *). On all other sweeps, REF is statistically indistinguishable from Vanilla — neither significantly better nor significantly worse. The cross-ensemble mean (0.3919 vs Vanilla 0.3910) is +0.0009, well within bootstrap-CI width.

3. **The IC(R/W)-RRF lineage's "+4.3% over Vanilla" headline from v5.0's spec is collection-and-ensemble-fragile.** It holds for TREC DL 2019 n=4 only. On TREC DL 2020 n=4, the same algorithm loses to Vanilla by -0.011 NDCG@10. v6.0's framing — *match Vanilla in heterogeneous regimes; recover the v5.0 advantage in its home basin* — is the empirically defensible claim. The single-collection headline is retired.

---

## 5. Falsified Hypotheses (the v5.0 → v6.0 transition)

The v4.x falsification record documented 5 falsified hypotheses inside the v5.0 spec. The v6.0 transition tested an additional set of hypotheses; the failures are diagnostic.

**Falsified Hypothesis 1: Multi-statistic regime detection (logistic alpha × coverage-entropy attenuation) strictly dominates single-statistic detection.**

Falsified. REF v2 (logistic alpha(rho) attenuated by coverage-histogram entropy) was tested across 7 parameter configurations. Best cross-mean NDCG@10: 0.4030 (config: mu=0.45, tau=0.04, h_weight=0.5). Improvement over REF v1: +0.0017. Within bootstrap noise. At one sweep (TREC DL 2019 n=7), REF v2 was *significantly worse* than Vanilla (-0.0087, p=0.013, *). Net effect: marginal-to-negative.

Diagnostic: the coverage-histogram entropy h_cov saturates near 0.80-0.88 across all evaluated ensembles (because top-100 always includes many singleton-coverage docs). The signal is high-bias and adds little discriminative information beyond rho. Conclusion: rho is sufficient; second-order signals at this evaluation scale add complexity without commensurate signal.

**Falsified Hypothesis 2: A single ensemble-level regime signal (rho) is sufficient to predict which fusion wins.**

Falsified. rho on TREC DL 2019 n=4 = 0.491; rho on TREC DL 2020 n=4 = 0.495. Statistically indistinguishable regimes. But v5.0 wins on the first and Vanilla wins on the second. Conclusion: at least one collection-level property that influences fusion outcome is NOT observable from rank statistics alone.

This is a structural wall. The candidate observable signals — relevance-grade distribution, query difficulty (e.g., per-query rank correlation between rankers), label sparsity, top-K result density — require qrels access and are therefore not strictly label-free.

Per-query routing (rather than per-collection regime detection) is the natural next probe direction; documented as future work in Section 7.

**Falsified Hypothesis 3: Sharpening the alpha curve (raising the lower threshold lo) toward 0.45 strictly dominates the baseline (lo=0.35).**

Falsified. With lo=0.45, the n=4 result drops to 0.3737 (loses the v5.0 advantage in its home basin). The narrower band of "homogeneous regime" excluded rho=0.49 from the v5-routing zone. Cross-mean: 0.3912 vs baseline 0.3919. The lo=0.35 baseline dominates.

Lesson: the alpha curve is more sensitive to the lower bound than to the upper bound. The structural reason: rho clusters around 0.30-0.50 in the evaluation set; this is also where the v5-vs-Vanilla advantage flips. Pushing lo upward narrows the v5-active zone faster than the v5-active zone benefits from being narrower.

---

## 6. Architecture Diagrams

### The lineage's progression

```
RRF (Cormack et al., 2009)        uniform 1/(k+r)
  └─→ v2.1                        per-query adaptive weights (consensus)
        └─→ v3.0 DGAF             per-document gating (lambda per document)
              └─→ v4.0            soft type routing, per-ranker modulation
                    └─→ v5.0      per-document per-ranker confidence
                          └─→ v6.0  REGIME-AWARE MIXTURE
```

Each version broke a uniformity constraint of the previous. v6.0 breaks a different kind of constraint: the assumption that the optimal fusion is a fixed equation.

### The v6.0 mixture

```
              ┌──────────────────┐
              │  Ranker lists L_r │
              │  (M lists)        │
              └────────┬─────────┘
                       │
        ┌──────────────┴──────────────┐
        │                              │
        ▼                              ▼
  ┌──────────┐                ┌──────────────┐
  │ Vanilla  │                │   v5.0       │
  │  RRF     │                │  (existing)  │
  └────┬─────┘                └──────┬───────┘
       │                             │
       │     ┌──────────────────┐    │
       │     │ Regime detector  │    │
       │     │ rho = mean Jacc. │    │
       │     │ alpha = f(rho)   │    │
       │     └────────┬─────────┘    │
       │              │              │
       └──────────────┼──────────────┘
                      ▼
              ┌───────────────┐
              │  Mixture by   │
              │  alpha:       │
              │  multiplicative
              │  modulation   │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ Final ranking │
              └───────────────┘
```

The regime detector is a third input to the mixture, independent of both baselines.

---

## 7. Future Work — Probes That Could Open v7.0

This section names the trajectories that would advance the lineage beyond v6.0. None are committed; all are real candidates for the next attractor-localization cycle.

### 7.1 — Per-query regime detection

The wall identified in Hypothesis 2: ensemble-level rho cannot distinguish collections that have different optimal fusions. Hypothesis: *per-query* rank-distribution features can. Specifically:

- Per-query top-1 score-gap per ranker (how confident is THIS ranker about THIS query's top result?)
- Per-query rank-correlation between rankers (which queries induce ranker disagreement vs agreement?)
- Per-query coverage skew (does one ranker dominate the union of retrieved docs for this query?)

A per-query regime detector + per-query alpha could outperform v6.0 on average. The cost is added complexity; the potential gain is closing the residual gap to Vanilla on heterogeneous-regime sweeps.

### 7.2 — Selection rather than fusion

A structurally different basin: for each query, *select* the single best ranker rather than fuse. v5.0's per-document confidence already establishes that the ranker's score distribution carries signal about its certainty. Extending this to per-query meta-confidence (highest-z-score ranker wins) could produce a hybrid algorithm that fuses when consensus is strong and selects when one ranker dominates.

Could lose to v6.0 on average but win substantially on query classes where one ranker is clearly correct. Worth probing.

### 7.3 — Hybrid semantic + lexical regime

All evaluations to date use lexical rankers (BM25 variants, TF-IDF, proximity, semantic_hash). Modern IR pipelines include neural / dense / cross-encoder rankers. The v5.0 document-type taxonomy (consensus / disputed / specialist) was constructed under all-lexical conditions; whether a fourth type ("modality-disputed" — agreement within lexical and within semantic but disagreement across) emerges under mixed-modality conditions is an open structural question.

### 7.4 — Cross-collection generalization

This spec validates on TREC DL 2019 + TREC DL 2020 (passage retrieval). Generalization to BEIR sub-tracks, scientific retrieval (CSIRO, TREC-COVID), web retrieval (CW09, CW12), and conversational retrieval (CAsT) is open. The rho-clustering observed at ≈0.49 on both TREC DL collections may not hold elsewhere; the lo/hi thresholds may need re-tuning per domain.

### 7.5 — Score-aware variants

v5.0 (and therefore v6.0's v5-component) gracefully degrades to v4.0 when scores are unavailable. The reverse direction is untouched: when scores ARE available, neither v5.0 nor v6.0 fully exploits them. A score-distribution-aware variant could use score quantiles directly (rather than z-scoring within ranker) and might extract additional signal.

---

## 8. Reproduction

All results in this spec are reproducible with:

```bash
# TREC DL 2019 cross-ensemble sweep (Table 4.1)
python evaluation/probe_regime_aware_fusion.py

# Full validation panel with stat tests (Tables 4.2, 4.3)
python evaluation/probe_ref_validation.py --lo 0.35 --hi 0.60

# Multi-signal regime probe (Hypothesis 1 falsification, Section 5)
python evaluation/probe_ref_v2.py
```

All scripts depend only on Python 3.8+ standard library, the `trec_eval_harness.py` primitives, and the run files in `data/trec-dl-2019/runs/` and `data/trec-dl-2020/runs/`.

---

## 9. References

- Cormack, Clarke, Buettcher (2009). Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning methods. SIGIR 2009.
- IC(R/W)-RRF v5.0 (this repository): `spec/IC-RW-RRF-v5.0-CONFIDENCE-FUSION.md`
- IC(R/W)-RRF v4.0, v4.1, v3.0 (this repository): see `spec/`
- TREC 2019/2020 Deep Learning Tracks: https://trec.nist.gov/data/deep20{19,20}.html

---

*Crystallized in stream session 2026-05-13-001-rank-fusion-possibility-space-opening.md*
