# Cycle14 — independent metric and baseline audit

Preparation only, 2026-09-11. Reviewed the cycle14 preparation design,
cycle13 report, `evaluation/trec_eval_harness.py`, and
`evaluation/fusion_contract.py`. No collection acquisition, model invocation,
effectiveness calculation, implementation change, or test execution occurred.

**Conclusion:** the proposed binary SciFact nDCG@10 comparison is coherent after
the gates below. It tests a fixed source-addition system on a new project panel;
it is not an exact replication of cycle13's metric, a causal independence test,
or evidence that fusion beats using the learned source alone.

## Metric and evaluation contract

- Primary: equal-query mean nDCG@10, gain equal to binary relevance, discount
  `1/log2(rank+1)`, one-based ranks, unjudged gain zero without removing their
  positions. IDCG uses all positive official qrels for that query, not only
  positives in retrieved candidates. Short rankings receive no invented hits.
- Validate every retained grade is 0 or 1 before reusing the local
  `ndcg_at_k`: its exponential gain then equals linear gain exactly. Negative
  grades and grades above 1 fail this gate; they must not be silently coerced.
  This does not repair or retrospectively validate historical graded nDCG.
  The pinned [official trec_eval implementation](https://github.com/usnistgov/trec_eval/blob/ba38899cbd4de0fb699b47f39b64ef1c107e4a5c/m_ndcg_cut.c)
  uses relevance values as gains and treats nonpositive values as zero.
- Freeze an explicit ordered vector of official test qids with at least one
  positive qrel. Enumerate any exclusions before effectiveness is inspected.
  No source-hit, relevant-hit, source-overlap or minimum-list-length screening.
  A genuine empty retrieval is a zero-scoring ranking. An absent query caused
  by incomplete acquisition is a preflight failure, not permission to reduce
  the denominator. Reindex every arm's per-query outputs to the frozen vector.
- Do not call `run_evaluation` unchanged: it intersects all run query sets,
  skips queries with fewer than two sources, and runs unplanned variants.
  Reuse the individual metric and canonical fusion functions with a small
  explicit adapter in the later execution cycle.
- Preserve unique string document IDs and validate source ranks, finite scores,
  declared ordering and retained depths. Reject malformed or duplicate rows;
  the legacy readers silently skip malformed short rows and cannot themselves
  establish the input contract. Pin source ties separately from fused ties.
- Use `canonical_rrf(k=60)` with unit weight per retained source, one-based
  positions, absent contribution zero, `math.fsum`, and ascending string-ID
  fused-score ties. For authoritative evaluation, export the already-decided
  ranking with distinct decreasing proxy scores, e.g. `score=-rank`; preserve
  original retrieval scores in separate source artifacts. The pinned
  [trec_eval result reader](https://github.com/usnistgov/trec_eval/blob/ba38899cbd4de0fb699b47f39b64ef1c107e4a5c/form_res_rels.c)
  orders by score and breaks score ties by descending document ID, so raw
  tied fusion scores could otherwise change the project ranking.
- Do not remove `qid == docid`: these are separate namespaces. The pinned
  [BEIR wrapper](https://github.com/beir-cellar/beir/blob/ef83d29307061c65d04b035b4f4e7c18bd8374af/beir/retrieval/evaluation.py)
  defaults to that removal and averages only its returned score keys. Prefer
  direct per-query evaluator output and the explicit denominator; if using the
  wrapper, disable identical-ID removal and check keys before aggregation.

## Baselines and permitted interpretations

Freeze these four arms before scoring:

| Arm | Ranking | Purpose |
| --- | --- | --- |
| P | Primitive BM25 top1000, before local reranking | Tests whether the lexical system itself improves the supplied retrieval |
| S | Pinned SPLADE source top1000 alone | Tests whether adding fusion helps over direct use of the new source |
| A | Canonical k60 RRF over the four fixed lexical top200 rerankings of P | Preserves the fixed lexical comparison target |
| B | The same A inputs plus S at top1000, canonical k60 RRF | Primary source-addition system |

Primary delta is B minus A. Report B minus S, B minus P and A minus P as
prespecified context with named comparators. A positive B−A with nonpositive
B−S supports source addition to A, not added value over simply deploying S.
Even B beating both standalone arms does not establish an independence or
specialist-support mechanism. Candidate access, retained depth, source quality
and four correlated lexical votes versus one learned vote remain bundled.

The strongest cheap additional baseline is fixed two-source
`canonical_rrf([P_top1000, S_top1000], k=60)`: it asks whether the four-source
lexical apparatus is needed beyond a simple hybrid. It requires no new retrieval
or tuning, but is optional for the narrow B−A question and must be frozen before
scores if included. Its candidate access differs from B; interpret it as a
system comparator, not an isolated causal ablation. Standalone constituent
rankings can also be reported descriptively without selecting a deployable
winner from test labels.

Cycle13's bounded unnormalized RBP contribution is not an nDCG estimate.
Binary-gain agreement between evaluators bridges metric implementations, not
the old RBP conclusion to new nDCG performance. A secondary fixed top10 RBP
diagnostic could compare metric directions, but cannot rescue a failed primary
and is unnecessary for this preparation. “Unused by this project” does not
establish that the collection was absent from upstream model training.

## Minimal later execution gate and stop

1. Freeze acquisition/model revisions, text preprocessing, query vector,
   candidate access, source order/ties, depths, four arms, primary metric and
   reporting rule. Preserve full inputs and hashes; fix resource limits before
   retrieval. Inspect integrity metadata before effectiveness.
2. Cross-check binary synthetic fixtures against the pinned official evaluator
   before new collection scores: relevant documents at ranks 1, 2, 10 and 11;
   multiple positives including unretrieved positives; unjudged documents;
   short/empty rankings; a source tie; and equal query/document strings in
   separate namespaces. Validate per-query values and the frozen aggregate
   denominator. The coordinator reports no evaluator currently installed;
   building the pinned evaluator belongs to execution, not this preparation.
3. On any identity, query-completeness, grade-domain or evaluator mismatch,
   stop before comparison. Record and correct the contract without choosing
   another source, collection or parameter from observed effectiveness.
4. Run the frozen panel once, retain query-level paired deltas, report positive,
   negative and tied query counts, and use one prespecified paired query
   bootstrap if uncertainty is reported. Do not use the harness's normal-CDF
   approximation as an exact paired t-test. Multiple arm observations of one
   query remain one resampling unit.
5. Stop after the fixed result and review, whether favorable, reversed or
   inconclusive. An observed positive mean describes this finite test panel;
   an interval spanning zero does not establish positive transfer to future
   queries. No within-panel weight/depth/k sweep or query router follows.

Friction disposition: **PROMOTE** the explicit evaluator/denominator/export
gate into the prospective protocol. No code fix is claimed as landed, and no
execution improvement has yet been observed. Coordinator owns integration,
shared state and the Git checkpoint; this worker has no live jobs.
