# IC(R/W)-RRF: Adaptive Rank Fusion — Two-Tier Lineage

Exploratory research into rank fusion that adapts per-query, per-document, per-ranker, and by ensemble regime. The lineage includes unsupervised methods and label-light per-corpus selection experiments, with useful negative results alongside local improvements.

**September 2026 research checkpoint:** an Opus5 coordinator closely reproduced
20 fully supplied Bayesian reference probabilities. A follow-up with uncertain
provenance returned three near-reference probabilities before a provider refusal
stopped collection. Its eight-input primary remains incomplete; original records
and independently identified logging errors are preserved. The next question
moves toward actual shared errors on mechanically verified program tasks.
Read the [latest report and figure](results/cycle06-2026-09-10/REPORT.md),
[completed coordinator diagnostic](results/cycle05-replication-2026-09-10/REPORT.md),
[current research state](_sessions/RESEARCH_STATE.md),
[next observation design](_sessions/cycles/2026-09-10-cycle07-observation-design.md),
and [case-study draft](docs/RESEARCH_BRIEF.md). Agent sessions start with [AGENTS.md](AGENTS.md).

## Key Results

**Tier 1 — Unsupervised inference (tested on the configurations below)**

| Variant | NDCG@10 mean | Δ vs v5.0 | Notes |
|---------|---|---|---|
| Vanilla RRF | 0.3910 | +0.0193 | Cross-ensemble baseline (4-7 lexical rankers) |
| IC-RRF v5.0 (per-doc confidence) | 0.3717 | — | Wins only the 4-ranker basin |
| **IC-RRF v6.0 REF (regime-aware)** | **0.3919** | **+0.0202 (+5.4%)** | Strictly dominates v5.0 across all tested ensembles |

TREC DL 2019, 43 queries, cross-ensemble sweep over 4-7 lexical rankers, validated cross-collection on TREC DL 2020. [Full v6.0 results](results/v6.0-regime-aware-fusion-results.md).

**Tier 2 — Label-light per-corpus supervised (exploratory CV on 43/54 queries)**

| Variant | TREC DL 2020 NDCG@10 | vs v5.0 | vs Vanilla | Notes |
|---------|---|---|---|---|
| Vanilla RRF | 0.4483 | — | — | Tier-0 baseline |
| v5.0 | 0.4373 | — | — | Tier-1 IC-RRF crown for v5 era |
| v6.0 REF | 0.4393 | +0.0020 | -0.0090 | Tier-1 cross-ensemble crown |
| **v7.0 PQAS** | **0.4644** | **+0.0271 \*\*** | +0.0161 | **Tier-2 per-corpus supervised, p=0.003** |

Historical within-collection 5-fold CV, 5 seeds averaged. The reported **p=0.003 compares PQAS to v5.0**; its comparison to Vanilla RRF was **p=0.125, not significant**. Hyperparameters were selected on these data and the harness uses a normal approximation for p-values, so treat these as exploratory results. The reported oracle-gap capture was 49.5%; tested cross-collection transfer did not beat the best fixed baseline. A general label-efficiency threshold has not been established. [Full historical v7.0 results](results/v7.0-pqas-results.md), [audit](_sessions/RESEARCH_STATE.md).

## The Lineage's Structural Insight

Earlier in this project, v5.0 was reported as the crown at NDCG@10 = 0.3800 on TREC DL 2019 with a specific 4-ranker setup (+4.3% over Vanilla RRF). That result is reproducible exactly, but **the "+4.3% over RRF" headline is fragile**: it does not hold when even one additional ranker joins the ensemble (Vanilla RRF reaches 0.4031 at n=5, 0.4073 at n=6) and it does not replicate on TREC DL 2020 even with the original 4-ranker setup (Vanilla 0.4483 vs v5.0 0.4373).

The observed lesson: **method performance depends on the tested ranker mix and query collection.** None of the explored methods dominated all tested configurations. The v5.0 result is a configuration-specific win; these experiments do not establish an impossibility theorem or a globally optimal method.

v6.0 (REF — Regime-Aware Fusion) acts on this observation. For each query, it measures mean pairwise top-K Jaccard and modulates Vanilla scores using the difference between Vanilla and v5.0 ranks. It preserves the local v5.0 advantage and reduces v5.0's losses elsewhere, while still trailing Vanilla in several tested configurations.

## The Approach

```
1. Detect regime: rho = mean pairwise top-30 Jaccard across the M ranker lists
2. Map regime to mixing weight: alpha = piecewise_linear(rho; lo=0.35, hi=0.60)
3. Compute Vanilla RRF + v5.0 rankings (existing implementations)
4. Modulate Vanilla scores by an alpha-scaled function of (Vanilla-rank − v5-rank)
5. Sort, return
```

The method uses fixed thresholds and gains at inference and retains the underlying v5.0 implementation. As alpha approaches zero it approaches Vanilla RRF; larger alpha increases the influence of the v5.0 rank adjustment. Its settings were explored on the development data, so unsupervised inference does not imply an untouched evaluation.

## Architecture Evolution

```
RRF (2009)              uniform 1/(k+rank)                              UNSUPERVISED
  → v2.1                per-query adaptive weights via consensus         UNSUPERVISED
    → v3.0 DGAF         per-document gating (lambda per document)        UNSUPERVISED
      → v4.0            soft type routing, per-ranker modulation         UNSUPERVISED
        → v5.0          per-document per-ranker confidence (D × R)       UNSUPERVISED
          → v6.0 REF    regime-aware mixture                             UNSUPERVISED
═════════════════════════════════════════════════════════════════════════════════
            → v7.0 PQAS  per-query supervised selector                    LABEL-LIGHT
                         (label-light supervision; per-corpus training)
```

v2.1 → v6.0 explored different ways to relax uniform weighting. v6.0 introduced regime-aware modulation; v7.0 added a supervised logistic selector. PQAS was evaluated with five-fold CV over collections of 43 and 54 labeled queries, with smaller training folds. The horizontal line distinguishes supervised selection from unsupervised inference.

The lineage's recursive falsification discipline is preserved across both tiers: each version identifies and removes a constraint the previous version did not see, AND each transition leaves a documented falsification record for the candidate refinements that did not work.

## Quick Start

```bash
# Run with synthetic data (no downloads required)
python evaluation/trec_eval_harness.py --demo

# Reproduce the IC-RRF v5.0 baseline (single-basin, TREC DL 2019 n=4)
python evaluation/trec_eval_harness.py \
  --qrels data/trec-dl-2019/2019qrels-pass.txt \
  --runs data/trec-dl-2019/runs/bm25.txt \
         data/trec-dl-2019/runs/bm25_tuned.txt \
         data/trec-dl-2019/runs/tfidf.txt \
         data/trec-dl-2019/runs/ql_dirichlet.txt

# Reproduce the v6.0 cross-ensemble validation
python evaluation/probe_regime_aware_fusion.py
python evaluation/probe_ref_validation.py
```

The evaluation harness has zero external dependencies (Python 3.8+ standard library only). It computes NDCG@10/20, MAP@100, MRR, paired t-tests, and bootstrap confidence intervals — all from scratch.

### Reproducing Run Files

To regenerate the 7 ranking outputs from raw MS MARCO data:

```bash
# Download MS MARCO top-1000 (see data/README.md for links)
python evaluation/generate_diverse_runs.py \
  --top1000 data/trec-dl-2019/msmarco-passagetest2019-top1000.tsv \
  --qrels data/trec-dl-2019/2019qrels-pass.txt
```

This implements 7 ranking functions from scratch: BM25, BM25-tuned, TF-IDF, QL-Dirichlet, TF-IDF with bigrams, proximity scoring, and semantic hashing.

## Repository Structure

```
spec/           Algorithm specifications (v3.0 through v6.0, with falsification records)
evaluation/     Evaluation harness, REF probes, run generation, analysis tools
diagnostics/    Synthetic mechanism validation (no external data needed)
data/           TREC DL 2019/2020 qrels and generated run files
results/        Formatted evaluation results and ablation tables (v5.0 + v6.0)
_sessions/      Workflow, map, backlog, audit, and dated research working notes
docs/           Research case-study draft for the portfolio
```

## What This Demonstrates

**Testing the scope of a result.** The v5.0 → v6.0 experiments showed that relative performance changes across the tested configurations. The initial v5.0 gain did not survive additional rankers or the second annual query collection, prompting a correction to the project's headline.

**Preserving negative results.** The specifications and notebooks record tested refinements that failed to improve the chosen baselines. These counterexamples guide later experiments; they do not prove that an entire method family cannot work.

**Self-contained evaluation.** All metrics computed from first principles — no pytrec_eval dependency. All 7 ranking functions implemented from scratch. The probe scripts (REF v1, REF v2, full validation panel with significance tests) depend only on the harness's primitives. A reviewer can run `--demo` and see results in seconds; the full v6.0 panel in roughly a minute.

**Connecting mechanisms to tests.** Query weighting, document gating, a document-by-ranker confidence matrix, and regime modulation give concrete forms to different hypotheses. Controlled ablations and broader evaluation are needed to determine which mechanisms explain a measured gain.

## Requirements

- **Python 3.8+** — evaluation harness uses standard library only
- **numpy, scipy** — optional, only needed for diverse ranker generation (bigram, proximity, semantic hash)

## References

- Cormack, Clarke, Buettcher (2009). [Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning methods](https://dl.acm.org/doi/10.1145/1571941.1572114). SIGIR 2009.
- TREC 2019 Deep Learning Track. https://trec.nist.gov/data/deep2019.html
- TREC 2020 Deep Learning Track. https://trec.nist.gov/data/deep2020.html
- IC(R/W)-RRF v5.0 spec: [`spec/IC-RW-RRF-v5.0-CONFIDENCE-FUSION.md`](spec/IC-RW-RRF-v5.0-CONFIDENCE-FUSION.md)
- IC(R/W)-RRF v6.0 spec: [`spec/IC-RW-RRF-v6.0-REGIME-AWARE-FUSION.md`](spec/IC-RW-RRF-v6.0-REGIME-AWARE-FUSION.md)
- IC(R/W)-RRF v7.0 spec: [`spec/IC-RW-RRF-v7.0-PER-QUERY-ADAPTIVE-SELECTOR.md`](spec/IC-RW-RRF-v7.0-PER-QUERY-ADAPTIVE-SELECTOR.md)

## License

MIT
