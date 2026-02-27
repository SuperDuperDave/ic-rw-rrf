# TREC DL 2019 Evaluation Results

43 queries | 4 lexical rankers (BM25, BM25-tuned, TF-IDF, QL-Dirichlet)

## Main Results

| Variant | NDCG@10 | MRR | vs v2.1 | Notes |
|---------|---------|-----|---------|-------|
| Vanilla RRF | 0.3645 | 0.7308 | -0.0065 | Baseline — uniform 1/(k+rank) |
| v2.1 IC(R/W)-RRF | 0.3710 | 0.7553 | -- | Per-query adaptive consensus |
| v3.0 DGAF | 0.3742 | 0.7610 | +0.0032 | Per-document gating |
| v4.0 Soft-Routed | 0.3750 | 0.7642 | +0.0040 | Per-ranker modulation |
| **v5.0 (v4.0+Ref3)** | **0.3800** | 0.7108 | **+0.0090** | Per-document confidence — **Best NDCG@10** |
| v4.1 (all 3 refs) | 0.3747 | 0.6957 | +0.0037 | Ref1 interferes with Ref3 |

v5.0: +4.3% NDCG@10 over vanilla RRF, +2.4% over v2.1.

## Ablation Results (v4.x experimental series)

| Ablation | NDCG@10 | MRR | Finding |
|----------|---------|-----|---------|
| v4.0 + Ref1 only | 0.3734 | 0.7673 | Contribution-space dispersion: marginal NDCG effect |
| v4.0 + Ref2 only | 0.3750 | 0.7642 | Reliability gate = no-op (p_S = 0 with homogeneous rankers) |
| v4.0 + Ref3 only | **0.3800** | 0.7108 | Per-document confidence = sole source of NDCG gain (**= v5.0**) |
| v4.0 + all three | 0.3747 | 0.6957 | Ref1 interferes with Ref3 |
| v4.2-sig | 0.3731 | 0.6957 | Type S inert with homogeneous rankers |
| PACA-K3 | 0.3692 | 0.6420 | Position protection protects wrong documents |

## Falsified Hypotheses

1. **Contribution-space dispersion improves type routing.** Falsified: compresses p_D at top positions, weakening the confidence signal where it matters most.
2. **Reliability gate prevents noisy-independent boosting.** Falsified: creates w-squared suppression; completely inert with homogeneous rankers (coverage = 1.0).
3. **One-sided confidence preserves gains.** Falsified: identical to two-sided (Ref3+1side = v5.0 exactly).
4. **Confidence-gated independence leverages per-doc signal.** Falsified: Type S pathway inert without diverse rankers.
5. **Position-aware attenuation protects MRR.** Falsified: protects the base ranking's top-1 mistakes, not its correct placements.

## Cross-Version Comparison

| Dimension | v2.1 | v3.0 DGAF | v4.0 | v5.0 |
|-----------|------|-----------|------|------|
| Per-query adaptive | Yes | Yes | Yes | Yes |
| Per-document adaptive | No | Yes (lambda) | Yes (type routing) | Yes (type + confidence) |
| Per-ranker adaptive | No | No | Yes (modulation) | Yes (per-doc modulation) |
| Confidence resolution | Per-ranker | Per-ranker | Per-ranker | **Per-document per-ranker** |
| Parameters | 3+ | 5+ | 3 | **3** |
| Score requirement | No | No | No | Optional (graceful fallback) |
| Best metric | -- | -- | -- | NDCG@10 |
| Degradation path | -> RRF | -> v2.1 | -> v2.1 | -> v4.0 -> v2.1 -> RRF |

## Known Trade-offs

v5.0 improves NDCG@10 but shows MRR regression (-0.0534 vs v4.0). Per-document confidence promotes relevant documents into top-10 on most queries, but on some queries it promotes the wrong document into top-1. This is a genuine NDCG-vs-MRR trade-off.

No result reaches statistical significance at p<0.05 with 43 queries. Evaluation on TREC DL 2020 with expanded ranker diversity is planned.

## Reproduction

```bash
# Exact command to reproduce these results:
python evaluation/trec_eval_harness.py \
  --qrels data/trec-dl-2019/2019qrels-pass.txt \
  --runs data/trec-dl-2019/runs/bm25.txt \
        data/trec-dl-2019/runs/bm25_tuned.txt \
        data/trec-dl-2019/runs/tfidf.txt \
        data/trec-dl-2019/runs/ql_dirichlet.txt
```
