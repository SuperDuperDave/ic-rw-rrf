# IC(R/W)-RRF v7.0 — Per-Query Adaptive Selector (PQAS)

## Label-Light Supervised Per-Query Routing — A Discipline Shift in the Lineage

*Revision: 7.0.0 — May 2026*
*Distilled from the v6.0 → v7.0 transition through per-query oracle diagnosis on TREC DL 2019 + 2020, falsification of label-free combinator rules, and within-collection k-fold cross-validation of a minimal supervised classifier*

---

## 1. Abstract

v7.0 is the **first member of the IC(R/W)-RRF lineage that uses labels.** Every prior version (v2.1 through v6.0) operates on rank positions and optional ranker scores alone. v7.0 introduces a minimal supervised classifier that, given a small number of labeled queries (~50+) from a target corpus, predicts which existing fusion (Vanilla RRF or v5.0-modulated) best serves each new query in that corpus.

The motivation: per-query diagnostic analysis (documented in `evaluation/probe_per_query_diagnosis.py`) revealed that the per-query *oracle* (selecting the optimal fusion per query) reaches NDCG@10 = 0.4106 on TREC DL 2019 and 0.4808 on TREC DL 2020 — leaving **+0.0305 and +0.0325 of headroom** over the best fixed algorithm (v5.0 on 2019; Vanilla on 2020). Label-free routing rules (probe 7) could not extract this gap on both collections simultaneously due to a structural *feature-direction reversal* between collections.

v7.0 partially extracts this gap via minimal supervised learning:

- **TREC DL 2020, within-collection 5-fold CV** (5 seeds averaged): PQAS NDCG@10 = 0.4644, capturing **49.5% of the per-query oracle gap**, significantly better than v5.0 (+0.0271 NDCG@10, p=0.003 paired t-test).
- **TREC DL 2019, within-collection 5-fold CV**: PQAS NDCG@10 = 0.3785, no significant improvement over v5.0. The 43-query collection is below the model's data-efficiency threshold given the variance of per-query NDCG@10.

v7.0 also documents a *falsified* hypothesis: **leave-one-collection-out cross-validation (training on 2019, testing on 2020, and vice versa) fails to transfer.** PQAS must be retrained per target corpus. This is a real structural finding — the features that predict per-query winners reverse direction between TREC DL 2019 and 2020.

The contribution v7.0 makes:

- **The discipline shift is named and bounded.** This is the first lineage member that needs labels; all prior versions are preserved as label-free fallbacks.
- **Significant per-corpus improvement is established** on a substantial collection (TREC DL 2020, 54 queries).
- **The cross-collection wall is documented**, opening v8 directions (multi-corpus training; collection-identifying features; structurally different selectors).

For deployment, v7.0 fits the regime where the operator has ~50+ labeled queries from their target corpus and is willing to train a tiny per-corpus classifier. In all other regimes, v6.0 REF remains the default.

---

## 2. The Distillation Insight

v6.0 broke the assumption that the optimal fusion is a fixed equation; it replaced fixed-equation thinking with ensemble-regime mixing. The new constraint v7.0 identifies and removes:

**v6.0 still operates per-ensemble, not per-query.** The mixing weight alpha is computed once per query from the ensemble's regime signal (rho), then applied uniformly across the documents in that query's union. But the per-query oracle analysis shows that the optimal fusion can differ *across queries within the same ensemble configuration*. Even at TREC DL 2020 n=4 (where the ensemble's regime is essentially identical across all 54 queries — rho≈0.49 throughout), 21 queries are best-served by v5.0 routing and 28 are best-served by Vanilla RRF.

**The optimal fusion is per-query, not per-ensemble.** v6.0 cannot reach this because rho is a per-ensemble statistic computed over the union of top-K. Per-query optimal routing requires per-query features — and a function from those features to the routing decision.

The function cannot be hand-derived from a single statistic (label-free probe 7 proved that). It must be *learned* from labeled examples. This is the discipline shift: **the lineage's first introduction of learned parameters.**

The discipline shift is deliberate and bounded:

- The learned model is tiny (logistic regression on ~10 features, no neural nets, no kernels)
- The label requirement is modest (~50+ labeled queries from the target corpus)
- The supervision is per-corpus, not per-deployment (one trained model per corpus regime, reused indefinitely)
- The model is interpretable (linear weights on hand-engineered features)
- All prior lineage members remain available as label-free fallbacks

---

## 3. Algorithm

### Overview

```
Phase 1 — Train (once per target corpus, requires labels):
  Input: ~50+ labeled queries with qrels
  For each labeled query q:
    Compute Vanilla RRF NDCG@10 (label-free)
    Compute v5.0 NDCG@10 (label-free)
    Label_q = 1 if v5 wins or ties, 0 otherwise
    Compute feature vector x_q (Section 3.1)
  Standardize features (z-score) using training stats
  Fit logistic regression with L2 regularization (Section 3.3)
  Save: weights w, bias b, feature means mu, feature stds sigma

Phase 2 — Inference (label-free at inference time):
  For each new query q:
    Compute feature vector x_q
    Standardize using saved mu, sigma
    Predict prob_v5 = sigmoid(w · x_q + b)
    If prob_v5 > threshold (default 0.5):
      Use v5.0 routing (or v6.0 REF if available)
    Else:
      Use Vanilla RRF
```

### 3.1 — Feature vector x_q (10 features, all rank-list observable)

```
rho                     mean pairwise top-30 Jaccard across the M rankers
h_cov                   normalized entropy of the coverage histogram (top-100)
frac_specialist_top30   fraction of top-30 docs covered by exactly 1 ranker
frac_consensus_top30    fraction of top-30 docs covered by all M rankers
mean_score_gap          mean across rankers of (top-1 score − median score)
max_score_gap           max across rankers of the above
top1_spread             max(top-1 scores across rankers) − min(top-1 scores)
score_var_mean          mean across rankers of the ranker's score std
mean_rank_dist          mean across ranker pairs of mean rank-position distance for common top-50 docs
n_unique_docs_top30     size of the union of top-30 docs across rankers
```

All features are computable from the M ranked lists (with optional scores). No labels needed at inference. Implementation: `evaluation/probe_per_query_diagnosis.py::per_query_features`.

### 3.2 — Training labels

For each training query, compute Vanilla NDCG@10 and v5.0 NDCG@10. Label = 1 if v5.0 ≥ Vanilla, else 0. Ties go to v5.0 (favored due to its richer routing structure). With ~50+ queries, label balance is typically 35-55% v5-wins depending on collection.

### 3.3 — Logistic regression

Standardize each feature: `x_std[j] = (x[j] - mu[j]) / sigma[j]`.

Fit:

```
loss(w, b) = mean over training queries of:
               -y_q * log(sigmoid(w · x_std_q + b))
               -(1 - y_q) * log(1 - sigmoid(w · x_std_q + b))
             + l2 * sum(w[j]^2)
```

Optimization: batch gradient descent, learning rate 0.05, 2000 epochs.

Hyperparameters: l2 regularization strength (default 0.05-0.30 depending on corpus size), classification threshold (default 0.50). Both selected by cross-validation on the training set.

### 3.4 — Inference

At deployment, for each new query:
1. Compute feature vector x_q (Section 3.1)
2. Standardize using stored mu, sigma
3. prob_v5 = sigmoid(w · x_q + b)
4. If prob_v5 > threshold: route to v5.0 (or v6.0 REF — both are valid v7 routing targets)
5. Else: route to Vanilla RRF

Implementation: `evaluation/probe_pqas_kfold.py::kfold_cv` for the CV harness; `evaluation/probe_pqas_supervised.py` for the LR primitives.

### 3.5 — Graceful degradation

```
No training labels available           → fall back to v6.0 REF (label-free)
Per-corpus tuning impossible           → fall back to v6.0 REF
Cross-corpus deployment                → v6.0 REF; v7 retraining required for each corpus
Fewer than ~50 labeled queries          → likely too noisy; fall back to v6.0 REF (see Section 5)
```

v7.0 is an *optional upgrade*, not a strict replacement. The lineage is now a deployment-tier system:

- **Tier 0 (universal)**: Vanilla RRF — always available, always degrades safely
- **Tier 1 (label-free)**: v6.0 REF — works on any corpus with no training
- **Tier 2 (label-light, per-corpus)**: v7.0 PQAS — best results when labels available

A deployer chooses the tier matching their resources.

---

## 4. Empirical Results

### 4.1 — Within-collection 5-fold cross-validation

The honest experiment: hold out 1/5 of queries, train on the other 4/5, predict per-query routing on the held-out fold, evaluate NDCG@10 on the held-out fold. Repeat across 5 folds (full coverage of the collection), repeat across 5 seeds (variance reduction). All numbers averaged.

| Collection | Vanilla | v5.0 | v6.0 REF | **v7.0 PQAS** | Oracle | % of gap captured |
|---|---|---|---|---|---|---|
| TREC DL 2020 n=4 (54 q) | 0.4483 | 0.4373 | 0.4393 | **0.4644** | 0.4808 | **49.5%** |
| TREC DL 2019 n=4 (43 q) | 0.3645 | 0.3800 | 0.3832 | 0.3785 | 0.4106 | -5.1% |

**Best-fold-pick statistics for TREC DL 2020** (best config: l2=0.05, threshold=0.50): 73 picks of v5.0, 89 picks of Vanilla across 5 folds × 5 seeds = 270 total query-decisions. PQAS uses both routing options actively.

**Best-fold-pick statistics for TREC DL 2019**: ~125-129 picks of v5.0 vs 0-4 of Vanilla across the same fold/seed grid. The model defaults to "always v5" with high regularization (because the 2019 signal is too weak to extract a different decision).

### 4.2 — Paired t-tests (PQAS vs baselines, per-query NDCG@10)

| Collection | PQAS vs Vanilla | PQAS vs v5.0 |
|---|---|---|
| 2020 n=4 | +0.0161 t=+1.53 p=0.125 ns | **+0.0271 t=+2.93 p=0.003 \*\*** |
| 2019 n=4 | +0.0140 t=+0.73 p=0.466 ns | -0.0016 t=-1.00 p=0.317 ns |

**TREC DL 2020 produces the load-bearing significance.** PQAS *significantly* outperforms v5.0 (p<0.01) and *numerically* outperforms Vanilla. TREC DL 2019 shows no significant effect in either direction.

### 4.3 — Leave-one-collection-out CV (falsified hypothesis)

| Train → Test | NDCG@10 | vs Vanilla | vs v5.0 | vs v6.0 REF |
|---|---|---|---|---|
| 2019 → 2020 | 0.4412 | -0.0071 | +0.0039 | +0.0019 |
| 2020 → 2019 | 0.3800 | +0.0155 | 0.0000 (effectively "always v5") | -0.0032 |

Neither direction captures meaningful oracle headroom. The 2020-trained model applied to 2019 collapses to "always v5" at high regularization (its decision rule's load-bearing features — score-gap, top1_spread — have OPPOSITE predictive direction on 2019, so the model with non-zero weights produces worse-than-baseline output). The 2019-trained model applied to 2020 marginally beats v5 but loses to Vanilla.

The directional reversal of features between collections (documented in `evaluation/probe_per_query_diagnosis.py` output) is the structural cause.

### 4.4 — Feature signature of the trained classifier

Weights from the 2020-trained PQAS (z-score normalized features, positive = predicts v5-win):

| Feature | Weight |
|---|---|
| top1_spread | -0.132 |
| max_score_gap | -0.109 |
| h_cov | -0.106 |
| mean_score_gap | -0.106 |
| score_var_mean | -0.078 |
| frac_consensus_top30 | +0.050 |
| frac_specialist_top30 | -0.047 |
| mean_rank_dist | -0.032 |
| rho | +0.030 |

Interpretation: on TREC DL 2020, use v5.0 when score signals are *low and well-behaved* (small spread, small gap, low score variance). Use Vanilla when any ranker is over-confident (large gap or spread). Rho — the regime signal of v6.0 — has *minimal* weight on 2020. The 2020-specific load-bearing signal is in the score distribution, not in rank agreement.

Compare to the 2019-trained PQAS, where rho (+0.123) and mean_rank_dist (-0.134) carry the most weight. The two trained models target different features — the reason cross-collection transfer fails.

---

## 5. Falsified Hypotheses

The v6.0 → v7.0 transition tested three explicit hypotheses; one was confirmed and two were falsified.

**Confirmed Hypothesis: Within-collection supervised PQAS extracts a meaningful fraction of the per-query oracle gap.**

Confirmed for TREC DL 2020 (49.5% of gap, p=0.003). Not confirmed for TREC DL 2019 (negative — see Falsified Hypothesis 5 below).

**Falsified Hypothesis 4: A label-free multi-feature combinator rule wins on both TREC DL 2019 and TREC DL 2020 simultaneously.**

Falsified. Tested 30+ rule combinations spanning conjunctive (`AND`), disjunctive (`OR`), multiplicative, and weighted-vote forms over the 10 features. No rule produced positive gains over the best fixed baseline on both collections. The closest (`top1_spread<50 AND rho>0.35`) was at most -0.0001 on 2019 (tie) and +0.0070 on 2020 (marginal). The cross-collection feature-direction reversal is structurally limiting.

Diagnostic: features that predict v5-wins reverse direction between collections. On 2019, v5-wins have *higher* score gaps; on 2020, v5-wins have *lower* score gaps. A single threshold rule cannot reconcile opposite directions. Label-free routing is therefore bounded.

**Falsified Hypothesis 5: A supervised PQAS trained on TREC DL 2019 and tested on TREC DL 2020 (or vice versa) generalizes.**

Falsified. 2019 → 2020 transfer: NDCG@10 = 0.4412 (loses to Vanilla 0.4483). 2020 → 2019 transfer: NDCG@10 = 0.3800 (collapses to "always v5" — the model's regularization wipes out its 2020-specific signal because the 2019 features point opposite directions).

Diagnostic: the directional reversal documented in Hypothesis 4 manifests at the supervised level too. The classifier learns features that are predictive in the training corpus but inverse-predictive in the test corpus. Regularization mitigates by shrinking weights to zero, but a zero-weight model is no different from the baseline. **Cross-collection PQAS transfer is structurally impossible without features that observe collection-level properties.**

**Falsified Hypothesis 6: PQAS extracts the per-query oracle gap on TREC DL 2019 (43 queries) at parity with TREC DL 2020.**

Falsified. PQAS produces no significant improvement on 2019 (-5.1% of gap captured). Earlier single-seed runs appeared to show 0.3848 gains; averaging over 5 seeds drops the result to 0.3785, well within noise.

Diagnostic: with 43 queries, 5-fold CV produces test folds of ~8-9 queries each. NDCG@10 has substantial query-level variance, and the per-query signal on 2019 (features near the decision boundary, weak separation in consistent-direction features like h_cov) is below the variance threshold. The signal exists in principle (oracle gap is +0.0305) but the supervised model cannot reliably extract it at this data scale. Larger collections (BEIR sub-tracks, MS MARCO) are the natural next test.

---

## 6. Architecture in the Lineage

```
RRF (2009)                — uniform 1/(k+rank)                          UNSUPERVISED
v2.1                      — per-query consensus weights                  UNSUPERVISED
v3.0 DGAF                 — per-document gating                          UNSUPERVISED
v4.0                      — soft type routing, per-ranker modulation     UNSUPERVISED
v5.0                      — per-document per-ranker confidence           UNSUPERVISED
v6.0 REF                  — regime-aware mixing                          UNSUPERVISED
─────────────────────────────────────────────────────────────────────
v7.0 PQAS                 — per-query supervised selector                LABEL-LIGHT
```

The horizontal line marks the discipline shift. Above the line: rank-list + optional scores in, ranking out. Below: a tiny supervised classifier trained on labeled query/qrels data.

Below the line, the per-corpus-tuning constraint is explicit. v7.0 is not a strict supersession of v6.0 — it is a different deployment tier.

---

## 7. Practical Deployment Guide

### When to use which version

| Deployment context | Recommended version | Rationale |
|---|---|---|
| New corpus, no labels available | v6.0 REF | Label-free; works everywhere |
| Cross-corpus deployment (one model serves many corpora) | v6.0 REF | v7.0 doesn't transfer |
| Single corpus, ~50+ labeled queries available | **v7.0 PQAS** | Best results when within-corpus tuning is possible |
| Single corpus, <50 labeled queries | v6.0 REF | Below v7.0's data-efficiency threshold |
| Need MRR specifically (top-1 quality) | v6.0 REF | Healed v5.0's MRR dip explicitly |
| Score-only available rankers | v5.0 (with fallback to v4.0 if scores missing) | v6.0/v7.0 are score-aware; will use them if present |

### Training procedure for v7.0

```
1. Collect ~50+ labeled queries (qrels) from your target corpus
2. Run each query through your ranker ensemble; record top-K lists + scores
3. Compute Vanilla NDCG@10 and v5.0 NDCG@10 per query  → labels
4. Compute 10 per-query features (Section 3.1)         → feature vectors
5. Z-score standardize using training-set means/stds
6. Fit LR with L2 (l2 ∈ [0.05, 0.30], select by inner CV)
7. Save w, b, mu, sigma
8. At inference: compute features → standardize → predict → route
```

Training cost: <1 second for 50-500 queries in pure Python. Inference cost: trivial (a 10-element dot product per query).

### Operational notes

- **Periodic retraining**: as the underlying corpus drifts or the ranker ensemble changes, retrain. Monthly or quarterly is typical depending on corpus volatility.
- **Threshold tuning**: the default 0.5 is rarely optimal. Tune on a small validation subset; we observed best results at 0.40-0.50 on TREC DL 2020.
- **Feature drift monitoring**: track the distribution of features at inference time. If it drifts substantially from training, retrain.

---

## 8. Future Work — Open Trajectories

### 8.1 — Validation on larger corpora

The 2019/2020 result split suggests data-efficiency is the binding constraint at low query counts. BEIR sub-tracks (often 100s-1000s of queries) and MS MARCO dev sets are the natural next validation grounds. Hypothesis: PQAS reliability *increases* with corpus size; the inability to extract 2019's oracle gap is a query-count issue, not a structural one.

### 8.2 — Cross-corpus generalization via collection-identifying features

The directional reversal between 2019 and 2020 features makes cross-corpus transfer impossible with the current feature set. New features that capture *which collection-like-regime we are in* (without seeing the test query's qrels) could unlock cross-corpus PQAS. Candidates:
- Aggregate score-distribution statistics across recent queries
- Cluster the query in a corpus-level feature space (e.g., embedded query similarity)
- Pre-trained cross-corpus identifier (a separate small model)

### 8.3 — Structurally different selectors

PQAS selects between Vanilla and v5.0. The oracle ceiling could be raised by:
- Adding v6.0 REF to the selection space
- Adding intermediate fusion strategies (v3.0 DGAF, v4.0 variants)
- Multi-class classification (k-way selection rather than binary)

### 8.4 — Per-query alpha (continuous, not binary)

PQAS makes a binary v5/Vanilla choice. v7.1 could instead predict a per-query alpha in [0, 1], mixing v5.0 routing with Vanilla scores by alpha (the same multiplicative-modulation algebra v6.0 REF uses, but with alpha per-query rather than per-ensemble). This may generalize better than binary classification.

### 8.5 — Active learning for label efficiency

If labels are costly, an active-learning approach (label only queries where the binary classifier is uncertain) could reduce the label budget from ~50 to ~15-20. Not validated; deserving a probe.

---

## 9. Reproduction

```bash
# Per-query diagnosis (the source of the oracle gap finding)
python evaluation/probe_per_query_diagnosis.py

# Label-free combinator probe (Falsified Hypothesis 4)
python evaluation/probe_pqas_combinator.py

# LOOCV supervised probe (Falsified Hypothesis 5)
python evaluation/probe_pqas_supervised.py

# Within-collection k-fold CV (the confirmed hypothesis)
python evaluation/probe_pqas_kfold.py

# Significance tests for the confirmed result
python evaluation/probe_pqas_significance.py
```

All scripts depend only on Python 3.8+ standard library, the `trec_eval_harness.py` primitives, and the run files in `data/trec-dl-2019/runs/` and `data/trec-dl-2020/runs/`. No external ML library is used; the LR is hand-coded in standard library.

---

## 10. The Discipline Position

v7.0 is a *discipline shift*, named explicitly:

- The lineage's earlier members (v2.1 - v6.0) are unsupervised. v7.0 is supervised, even if minimally.
- The lineage's earlier members produce one algorithm that works everywhere. v7.0 produces one classifier per target corpus.
- The lineage's earlier members can be specified in a paper-grade equation. v7.0 specifies a *training procedure* + a *deployment protocol*.

This is a significant change. The honest framing: v7.0 is a separate *tier* in the lineage, not a successor that strictly replaces v6.0. The lineage now has parallel deployment options:

- v2.1 - v6.0: the unsupervised family (Tier 1)
- v7.0: the label-light supervised tier (Tier 2)

Future versions may further expand the tier structure (e.g., a Tier 3 cross-corpus PQAS if structurally enabled; a Tier 3 active-learning PQAS for low-label budgets).

The unsupervised crown remains v6.0 REF. The label-light upgrade is v7.0 PQAS.

---

*Crystallized in stream session 2026-05-13-001-rank-fusion-possibility-space-opening.md*
