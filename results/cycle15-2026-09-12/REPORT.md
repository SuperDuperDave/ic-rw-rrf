# SciFact transfer — cycle15

Execution of the [prospective cycle14 contract](../../_sessions/cycles/2026-09-11-cycle14-transfer-protocol.md).
The collection and five systems were fixed before this project's first SciFact
effectiveness measurement. This is a mechanism-level adaptation: the earlier
first-stage generator was not pinned, and the collection, document unit,
judgments and first-stage source change.

## Comparison

| Arm | Fixed system |
| --- | --- |
| P | Cached BM25, up to 1,000 documents |
| S | Cached SPLADE++ EnsembleDistil, up to 1,000 documents |
| A | Canonical k60 RRF of four unchanged lexical rerankings of P, each capped at 200 |
| B | The same four lexical lists plus S |
| H | Canonical k60 RRF of P and S |

Primary: equal-query mean binary nDCG@10 difference B−A. The prediction is a
positive difference; the fixed contextual comparisons are B−S, B−P, A−P and
B−H. Full qrels determine IDCG. Missing qrels contribute zero at their retained
rank positions; that convention does not establish that those documents are
irrelevant. Secondary A/B top10 RBP uses p=.8, without renormalizing truncated
weight mass. No p-values, confidence intervals or parameter search are planned.

The lexical scorers, tokenizer and pooled candidate-union statistics come from
the unchanged implementation. Exact lexical ties retain P's input order;
fusion uses one-based reciprocal ranks, accurate summation and string document
IDs on computed-score ties. All numerical rankings are preserved before metrics.

## Acquisition and gates

The one acquisition attempt downloaded and verified all five inputs, totaling
1,000,472,770 bytes, in 34.057 seconds, with no retries or partial files. Pinned
decoder and evaluator support artifacts have separate byte bounds. Raw query
and corpus text stays in ignored local storage. No retrieval-model inference,
index build, new judgments or global package installation was needed.
[Acquisition receipt](../../_sessions/evidence/2026-09-12-cycle15-acquisition.json).

The isolated official NIST evaluator built successfully from its pinned revision.
All 11 synthetic queries passed before collection effectiveness, including empty
results and full-qrel denominators. Local versus independent formula error was
zero; the maximum difference from four-decimal official output was .000035174,
inside the frozen .0000500001 tolerance.
[Metric gate](metric-gate/metric-gate.json),
[build receipt](../../_sessions/evidence/2026-09-12-cycle15-evaluator-build.json).

The first input-validation attempt stopped at corpus schema metadata. Both
Parquet files expose Arrow `large_string` fields; the original adapter required
`string`. No rows, qrels, cache records, lexical scores or collection outcomes
were read or computed in that attempt. A separate pre-outcome correction
accepts both string offset widths with the same value checks and unchanged
research code. Original sources, tests, preflight and failure remain preserved.
[Failure](validation/failure.json),
[correction contract](../../_sessions/cycles/2026-09-12-cycle15-string-correction.md).

Corrected validation passed all 300 official test queries, with no zero-IDCG
exclusions. All recorded qrels have grade 1. Both complete caches match pinned
query and corpus text; every ID and source order passed the strict contract.
The 5,183-document P candidate union is the entire corpus, so the stipulated
pooled statistics coincide with full-corpus statistics on this collection.
This does not mean each query has full-corpus candidate access.
[Corrected validation](corrected-validation/validation.json).

## Measured result

Across all 300 queries, adding S to A increases mean binary nDCG@10 by
**0.019348**, from **0.667303 to 0.686651**. The prespecified positive-direction
prediction holds on this finite panel. The stronger references change the
interpretation: standalone S reaches **0.703635** and simple hybrid H reaches
**0.705391**. The extra lexical apparatus does not establish an advantage here.

| Arm | Mean binary nDCG@10 | Top10 entries without explicit qrels |
| --- | ---: | ---: |
| P: cached BM25 | 0.678909 | 2,735 / 3,000 |
| S: cached SPLADE | 0.703635 | 2,720 / 3,000 |
| A: four lexical lists | 0.667303 | 2,740 / 3,000 |
| B: four lexical lists + S | 0.686651 | 2,728 / 3,000 |
| H: P + S | 0.705391 | 2,722 / 3,000 |

| Fixed contrast | Mean nDCG difference | Positive / zero / negative query differences |
| --- | ---: | ---: |
| B−A (primary) | +0.019348 | 47 / 241 / 12 |
| B−S | −0.016984 | 52 / 198 / 50 |
| B−P | +0.007741 | 54 / 216 / 30 |
| A−P | −0.011607 | 37 / 220 / 43 |
| B−H | −0.018741 | 35 / 218 / 47 |

Query signs alone do not determine mean benefit: B beats S on slightly more
queries than it loses, yet its mean is lower. Equal metric values do not imply
identical rankings. B−A ranges from −0.710935 to +0.569323 across queries.
[Full precision summary](transfer/summary.json),
[per-query evidence](transfer/per-query.json).

Secondary top10 RBP rises from 0.145396 to 0.149722, B−A=+0.004326, with the
same 47/241/12 sign counts. This is binary absent-as-zero scoring, not cycle13's
sharp bounds over missing grades. It supplies no guarantee under alternative
judgments.

No B top10 document lies outside that query's original P pool: **0 / 3,000**.
The result therefore did not require surfacing a document absent from P into
B's measured top10. This does not isolate why rankings improved or establish
source independence: S can still supply different ordering and documents absent
from the four retained lexical top200 lists. Depth, local scorer quality and
relative lexical voting weight remain bundled.

P lists range from 66 to 1,000 documents; all S lists have 1,000. All lists remain
eligible. The completed run took 116.099 seconds within its frozen 600-second scoring limit.
The execution manifest preserves exact source identities, commands, depths,
rankings and phase boundaries. [Manifest](transfer/manifest.json).

## Interpretation and verification

This is one previously unused-by-this-project collection under conventional
binary benchmark treatment. No generalization, novelty, causal correlation
correction, significance, or upstream training-data exclusion follows. The
source-addition result does not establish a new fusion algorithm. Keep the
prespecified stop: no weight/depth/k search or query router on these outcomes.

The independent audit reconstructed all **1,669,294 ranking rows** across four
lexical sources and five arms, with exact document order, depths and score values.
All summary values match exactly; the largest per-query metric difference is
2.22e-16 from floating-point summation. Five official evaluator exports preserve
rank order with strict rank-proxy scores; all 300 query values and each aggregate
pass the frozen four-decimal tolerance. The audit took 17.965 seconds, including
all five official calls. [Independent receipt](../../_sessions/evidence/2026-09-12-cycle15-result-audit.json),
[reconstruction protocol and outputs](independent-audit/audit-protocol.json).

All 211 research tests and 191 helper tests pass, including real synthetic Parquet
fixtures for both string widths and independent audit tests. The standard-library
demo passed before acquisition; its source stayed unchanged. Independent static
reviews found no remaining consequential implementation issue.

One ancillary review receipt was reformatted while the coordinator froze its
reference. The exact hash-bound bytes were recovered; the later five-space edit
is preserved separately. All 21 code/protocol/failure hashes remained intact,
and no outcomes were rerun. [Receipt custody note](../../_sessions/evidence/2026-09-12-cycle15-review-custody.json).

One bounded Claude Fable5.1 review completed successfully. Its packet preceded
the audit's completion; the review does not supply numerical verification.
The integration corrects its reversed judgment-coverage comparison, unsupported
tie explanation and overstrong causal reading of proposed future patterns.
[Review and next-question integration](../../_sessions/cycles/2026-09-12-cycle15-review-integration.md),
[native/Relay receipt](../../_sessions/evidence/2026-09-12-cycle15-review-receipt.json).

## Decision

Complete R18 and stop this fixed comparison. R19 will first assess the value and
prior art of one matched weighting question: keep B's lists fixed, scale each
lexical contribution by1/4, and leave S unchanged. This defines a family-balanced
C system whose comparison with B changes relative weights alone. It is a proposed
future intervention, not a tested method, an inferred dependence correction, or
proof that vote count caused B's deficit. Preserve S and H as strong references;
choose any new collection before comparative score inspection. No tuning or
additional experiment was performed after these results.
