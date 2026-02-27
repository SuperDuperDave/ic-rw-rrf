# IC(R/W)-RRF: Adaptive Rank Fusion with Per-Document Confidence Routing

Unsupervised rank fusion that adapts per-query, per-document, and per-ranker — using only rank positions and optional scores. No training data. No learned parameters.

## Key Result

| Variant | NDCG@10 | MRR | vs Vanilla RRF |
|---------|---------|-----|----------------|
| Vanilla RRF | 0.3645 | 0.7308 | -- |
| IC-RRF v2.1 | 0.3710 | 0.7553 | +1.8% |
| IC-RRF v3.0 DGAF | 0.3742 | 0.7610 | +2.7% |
| **IC-RRF v5.0** | **0.3800** | 0.7108 | **+4.3%** |

TREC Deep Learning 2019 | 43 queries | 4 lexical rankers | [Full results](results/trec-dl-2019-results.md)

## The Problem

Standard RRF treats every document identically: `1/(k + rank)`. This is a structural mismatch — the same query produces documents where rankers agree (consensus), disagree (disputed), or where only one ranker retrieves them (specialist). Each category demands different treatment.

## The Approach

IC(R/W)-RRF classifies documents into soft type membership using two observable signals — coverage and rank dispersion — then applies type-specific ranker modulation:

- **Consensus documents**: Trust the base weights (modulation near 1.0)
- **Disputed documents**: Boost the ranker most confident about *this specific document* (v5.0: per-document per-ranker z-scored confidence)
- **Specialist documents**: Boost structurally independent rankers

Three parameters. One equation. Graceful degradation to vanilla RRF when scores are unavailable.

## Architecture Evolution

```
RRF (2009) — uniform 1/(k+rank)
  -> v2.1: per-query adaptive weights via iterative consensus
    -> v3.0 DGAF: per-document gating (lambda per document)
      -> v4.0: soft type routing, per-ranker modulation
        -> v5.0: per-document per-ranker confidence (the D x R matrix)
```

Each version identifies and removes a structural constraint from the previous. v5.0 was distilled from a v4.x experimental series where 5 hypotheses were tested and 4 were falsified. The falsification results — and the specific, diagnosable reasons each hypothesis failed — are documented in the [v5.0 specification](spec/IC-RW-RRF-v5.0-CONFIDENCE-FUSION.md).

## Quick Start

```bash
# Run with synthetic data (no downloads required)
python evaluation/trec_eval_harness.py --demo

# Run on TREC DL 2019 (run files included in this repo)
python evaluation/trec_eval_harness.py \
  --qrels data/trec-dl-2019/2019qrels-pass.txt \
  --run-dir data/trec-dl-2019/runs/
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
spec/           Algorithm specifications (v3.0 through v5.0)
evaluation/     Evaluation harness, run generation, analysis tools
diagnostics/    Synthetic mechanism validation (no external data needed)
data/           TREC DL 2019/2020 qrels and generated run files
results/        Formatted evaluation results and ablation tables
```

## What This Demonstrates

**Systematic hypothesis testing.** The v4.x experimental series tested 5 refinements. 4 were falsified with specific, diagnosable reasons documented in the v5.0 spec. The research advanced through falsification, not intuition.

**Self-contained evaluation.** All metrics computed from first principles — no pytrec_eval dependency. All 7 ranking functions implemented from scratch. A reviewer can run `--demo` and see results in seconds.

**Algebraic reasoning about fusion.** Each version identifies a structural constraint (information bottleneck, rank-2 bilinear form, D x R confidence matrix) and removes it through architecture, not parameter tuning.

## Requirements

- **Python 3.8+** — evaluation harness uses standard library only
- **numpy, scipy** — optional, only needed for diverse ranker generation (bigram, proximity, semantic hash)

## References

- Cormack, Clarke, Buettcher (2009). [Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning methods](https://dl.acm.org/doi/10.1145/1571941.1572114). SIGIR 2009.
- TREC 2019 Deep Learning Track. https://trec.nist.gov/data/deep2019.html
- TREC 2020 Deep Learning Track. https://trec.nist.gov/data/deep2020.html

## License

MIT
