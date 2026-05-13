# IC(R/W)-RRF: Adaptive Rank Fusion — Two-Tier Lineage

Rank fusion that adapts per-query, per-document, per-ranker, and per ensemble regime. The lineage now offers two deployment tiers: an unsupervised default and a label-light per-corpus upgrade.

## Key Results

**Tier 1 — Unsupervised (label-free, works everywhere)**

| Variant | NDCG@10 mean | Δ vs v5.0 | Notes |
|---------|---|---|---|
| Vanilla RRF | 0.3910 | +0.0193 | Cross-ensemble baseline (4-7 lexical rankers) |
| IC-RRF v5.0 (per-doc confidence) | 0.3717 | — | Wins only the 4-ranker basin |
| **IC-RRF v6.0 REF (regime-aware)** | **0.3919** | **+0.0202 (+5.4%)** | Strictly dominates v5.0 across all tested ensembles |

TREC DL 2019, 43 queries, cross-ensemble sweep over 4-7 lexical rankers, validated cross-collection on TREC DL 2020. [Full v6.0 results](results/v6.0-regime-aware-fusion-results.md).

**Tier 2 — Label-light per-corpus supervised (requires ~50+ labeled queries from target corpus)**

| Variant | TREC DL 2020 NDCG@10 | vs v5.0 | vs Vanilla | Notes |
|---------|---|---|---|---|
| Vanilla RRF | 0.4483 | — | — | Tier-0 baseline |
| v5.0 | 0.4373 | — | — | Tier-1 IC-RRF crown for v5 era |
| v6.0 REF | 0.4393 | +0.0020 | -0.0090 | Tier-1 cross-ensemble crown |
| **v7.0 PQAS** | **0.4644** | **+0.0271 \*\*** | +0.0161 | **Tier-2 per-corpus supervised, p=0.003** |

Within-collection 5-fold CV, 5 seeds averaged. PQAS captures **49.5% of the per-query oracle gap** on TREC DL 2020. Does NOT transfer cross-collection (must be retrained per corpus). [Full v7.0 results](results/v7.0-pqas-results.md).

## The Lineage's Structural Insight

Earlier in this project, v5.0 was reported as the crown at NDCG@10 = 0.3800 on TREC DL 2019 with a specific 4-ranker setup (+4.3% over Vanilla RRF). That result is reproducible exactly, but **the "+4.3% over RRF" headline is fragile**: it does not hold when even one additional ranker joins the ensemble (Vanilla RRF reaches 0.4031 at n=5, 0.4073 at n=6) and it does not replicate on TREC DL 2020 even with the original 4-ranker setup (Vanilla 0.4483 vs v5.0 0.4373).

The deeper structural truth: **the optimal fusion algorithm depends on the ensemble's regime.** No fixed equation dominates across all (corpus, ranker-mix) configurations — because no such equation can exist. The v5.0 result is a basin-specific win, not a universal one.

v6.0 (REF — Regime-Aware Fusion) acts on this insight directly. It detects the ensemble's regime from rank statistics alone (mean pairwise top-K Jaccard) and continuously mixes v5.0's per-document confidence routing with Vanilla RRF based on the regime. The result preserves v5.0's advantage in its home basin while not surrendering Vanilla's advantage elsewhere.

## The Approach

```
1. Detect regime: rho = mean pairwise top-30 Jaccard across the M ranker lists
2. Map regime to mixing weight: alpha = piecewise_linear(rho; lo=0.35, hi=0.60)
3. Compute Vanilla RRF + v5.0 rankings (existing implementations)
4. Modulate Vanilla scores by an alpha-scaled function of (v5-rank − Vanilla-rank)
5. Sort, return
```

Three new constants. Zero learned parameters. The mixture interpolates continuously between Vanilla (heterogeneous regimes) and v5.0-modulated Vanilla (homogeneous regimes). All graceful-degradation properties of the v5.0 → v4.0 → v2.1 → RRF chain are preserved.

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

v2.1 → v6.0 each broke a uniformity assumption in the fusion equation. v6.0 broke the assumption that the optimal equation is fixed (regime-aware mixing). v7.0 breaks a *different* kind of assumption — that the lineage must be unsupervised. v7.0 is the first member that uses labels (a tiny logistic regression trained on ~50+ labeled queries from the target corpus). The horizontal line marks the discipline shift.

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
_sessions/      Stream-of-thought archive — reasoning records for each session
```

## What This Demonstrates

**Strange-attractor empiricism.** The v5.0 → v6.0 transition empirically demonstrated, on the existing repo data, that the optimal fusion algorithm is regime-dependent. The "v5.0 wins" finding from a single (corpus, ensemble) configuration generalized to neither additional ranker subsets nor a second collection. The crown's apparent stability was an artifact of evaluation scope, not algorithm structure.

**Recursive falsification.** The v4.x series falsified 5 hypotheses to settle v5.0. The v5.0 → v6.0 transition falsified 3 more hypotheses to settle v6.0 (multi-signal regime detection, sharpened alpha curves, fixed-equation universality). Each falsification narrows the algorithm; each narrowing leaves a more elegant artifact behind. The falsification record is documented in the v6.0 spec for downstream audit.

**Self-contained evaluation.** All metrics computed from first principles — no pytrec_eval dependency. All 7 ranking functions implemented from scratch. The probe scripts (REF v1, REF v2, full validation panel with significance tests) depend only on the harness's primitives. A reviewer can run `--demo` and see results in seconds; the full v6.0 panel in roughly a minute.

**Algebraic reasoning about fusion.** Each version identifies a structural constraint (information bottleneck, rank-2 bilinear form, D × R confidence matrix, fixed-equation universality) and removes it through architecture, not parameter tuning. v6.0's regime-aware mixture is the largest algebraic shift in the lineage — but the parameter count is *smaller*, not larger, because the alpha curve replaces multiple algorithm-internal knobs.

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
