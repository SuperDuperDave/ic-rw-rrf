# SciFact transfer — prospective execution contract

Prepared in cycle14 from checkpoint `cc42189`, before acquiring new run bodies or
inspecting new effectiveness. This protocol fixes the later comparison; execution
still requires the implementation and input/evaluator gates below. The
[preparation design](2026-09-11-cycle14-preparation-design.md) owns the collection
selection and this cycle's stop. No run has yet tested the prediction.

## Question and prediction

Does adding the same documented SPLADE++ EnsembleDistil family improve a fixed
four-source lexical RRF system on BEIR SciFact's test collection?

Primary prediction: the finite-panel mean nDCG@10 difference B−A is positive.
A nonpositive difference fails this prediction. Report any tiny positive value
as such; it is not automatically a practically useful or general improvement.
SPLADE alone or a simple two-source hybrid matching/beating B would challenge
the usefulness of the extra lexical apparatus, even if the primary is positive.

This is a **mechanism-level adaptation**, not an exact-pair replication. The old
first-stage candidate generator was not pinned; SciFact changes the collection,
document unit, judgments and first-stage source. Source quality, candidate access,
depth and relative lexical voting weight are bundled. No causal independence,
specialist-expertise, calibrated-confidence, model-training exclusion or novelty
claim follows. "Unused" means not evaluated by this project before this cycle.

## Inputs and cohort

Use only the immutable sources enumerated by the
[source audit](2026-09-11-cycle14-source-audit.md) and machine-readable
[input plan](../evidence/2026-09-11-cycle14-input-plan.json). Acquire
the BM25 and SPLADE top1000 caches, not their top100 variants. The two raw caches
total 995,932,483 bytes. Full body identities, actual schemas and depths are
execution gates; successful HEAD requests establish access/advertised size only.
No neural model weights, index construction or inference is needed on this route.

The official BEIR SciFact test qrels define the starting query set. Retain every
query with at least one positive qrel, enumerate any excluded zero-IDCG queries
before effectiveness, and freeze the resulting ascending-string query vector.
Validate the complete qrel grade domain as integers in {0,1}; reject other grades
rather than convert them. Use every qrel for each retained query when computing
IDCG, including relevant documents not retrieved by any source. No source-hit,
overlap, ranker-success or minimum-list-length eligibility condition.

Require complete matching test-query coverage in both caches and the pinned query
text source; qrels do not authorize silently intersecting incomplete run files.
Every document ID must belong to the pinned corpus. Preserve string IDs and
separate query/document namespaces: never remove a document merely because its
ID string equals the query ID. Reject duplicate query records, duplicate document
IDs within a ranking, nonfinite scores, malformed rows, text inconsistencies or
unsupported schemas. Do not inject qrel documents into a candidate pool.

For lexical scoring use exactly `candidate.doc.title + "\n" + candidate.doc.text`.
Require those two fields to be strings, candidate.doc._id to match its ranking
document ID, and query/corpus text to match the pinned sources without silent
fallback fields or normalization. The pinned flat-index producer supports this
raw schema and joins indexed title/body with newline; actual caches must still
pass the body-level gate. This fixes text construction before score inspection.

Raw query/passage text and external build/cache files remain in ignored local
storage. Publish source revisions, sizes/hashes, numeric rankings, code and results,
not copied provider transcripts, model weights or repeated source text. The source
audit distinguishes corpus/model licenses from the cache's absent license metadata.

## Five fixed arms

| Arm | Definition | Role |
| --- | --- | --- |
| P | Original cached BM25 ranking, up to1000 documents | Primitive first-stage reference |
| S | Original cached SPLADE++ EnsembleDistil ranking, up to1000 | Added source alone |
| A | Equal-weight canonical k60 RRF of four local lexical rerankings of P, each capped at200 | Fixed primary comparator |
| B | Equal-weight canonical k60 RRF of those same four lists plus S | Primary source-addition system |
| H | Equal-weight canonical k60 RRF of P and S, both capped at1000 | Simple two-source hybrid reference |

The four local scorers and tokenizer are unchanged:
BM25(1.2,.75), BM25(.9,.4), unigram log-TF/IDF divided by sqrt(token length),
QL Dirichlet(mu2000), in that order. Import the functions from the pinned
`generate_diverse_runs.py`; do not execute its CLI, extra rankers or label
diagnostics. No score-normalization, new tokenizer, cosine replacement or tuning.
The [local audit](2026-09-11-cycle14-local-input-audit.md) records exact formulas.

Build statistics once over unique document IDs in P's candidate union across the
entire frozen cohort, using the exact existing function. No full-corpus or
S-candidate statistics substitution. Detect an empty tokenized query before
scoring and stop for an explicit contract revision; do not silently omit it as
the old generator does. Legitimately empty source rankings remain empty and score
zero, but absent records caused by incomplete acquisition fail the input gate.

Retain supplied source-array order and validate its declared rank/score contract.
Local lexical ranking uses the existing stable descending sort on unrounded
scores, retaining P's order on exact ties; cap only after scoring. Serialize ranks
and scores without reconstructing order from six-decimal rounded scores. Canonical
fusion uses one-based contributions, missing contribution0, `math.fsum`, and
ascending string document IDs on computed fusion-score ties. Keep actual
per-query depth maps; a cap is not evidence that every list reaches that cap.

## Outcomes and metric gate

Primary: equal-query mean `nDCG@10(B) - nDCG@10(A)`, binary gain, logarithmic
rank discount, absent qrels treated as zero without deleting their rank positions.
This is conventional benchmark treatment, not proof that absent judgments are
true negatives. Preserve unrounded per-query scores and named paired deltas.

Fixed contextual nDCG contrasts: B−S, B−P, A−P and B−H. Publish all five arm
means and query-level signs for every listed contrast. No selecting the comparator
after results. B−A alone does not show fusion value beyond S; B−H compares complete
systems with differing candidate/depth access, not a causal ablation.

Secondary only: top10 RBP contribution, p=4/5, binary gain, absent-as-zero, for
A and B and their paired difference. This relates metric directions to cycle13
but is neither its grade/3 metric nor its sharp missing-judgment bounds. It cannot
rescue a failed primary. Do not rerun acquisition priorities or claim that the old
worst-case-label result has transferred from this secondary.
Explicitly, sum `(1-p) * p**(r-1) * rel(d_r)` over one-based ranks1 through
`min(10, returned_length)`; no renormalization of the truncated weight mass.

Descriptive diagnostics fixed before scoring: candidate count per query, the
unique P-candidate union divided by corpus size, B-top10 count outside that
query's P pool, and each arm's top10 count lacking an explicit qrel (report the
actual returned top10 denominator, including zero). These measure access and
judgment availability, not relevance of the unknown documents or a causal split
of the improvement. No diagnostic threshold activates a new method or run.

No p-value, confidence interval or population-significance claim in this small
fixed transfer. Report the full finite-panel result and its per-query variation.
Repeated arm scores reuse queries; shared candidate-union statistics couple the
rankings further. Upstream model training and benchmark selection remain outside
this project's holdout guarantee.

Before any SciFact effectiveness, cross-check binary synthetic fixtures against
the pinned NIST evaluator in the [metric source receipt](../evidence/2026-09-11-cycle14-metric-sources.json).
Fixtures cover relevant documents at ranks1/2/10/11, multiple/unretrieved positives,
unjudged documents, short/empty lists, tied original scores, identical query/doc
strings and explicit aggregate denominators. Use strict decreasing rank-proxy
scores (e.g. `-rank`) for authoritative evaluator export, preserving the already
chosen order. Reuse `ndcg_at_k` only under the validated binary domain. Do not
call the old general evaluator driver, which intersects query IDs and expands
methods, or rely on BEIR's default identical-ID removal. Record evaluator revision,
build command and numeric tolerance before the fixture run.

## Execution sequence and resource stop

1. Implement a small acquisition/input adapter and the five-arm driver. Scoring,
   fusion and metrics keep the standard-library path. The two pinned corpus/query
   files are Parquet; isolate the pinned PyArrow25.0.1 CPython3.12 Linux wheel
   (50,102,437 bytes, hash in the input plan) solely for decoding those identity
   checks. It is not currently installed. A failed wheel/platform/decoder check
   stops rather than changing input formats. Reuse existing scorers, strict readers,
   metric and canonical fusion;
   preserve all historical files. Synthetic edge-case tests precede real inputs.
2. Freeze source/code hashes and exact commands. Download each pinned input once,
   verify advertised byte count/hash before parsing, and retain failure evidence.
   Aggregate raw-input cap1.05GB (decimal), excluding a separately capped10MB
   official evaluator source archive and60MB pinned decoder wheel; download wall
   cap20minutes and later local
   scoring wall cap10minutes. No automatic retry, mirror change or raised cap.
3. Validate both complete input sets, cohort, labels, text/IDs, finite scores,
   actual ranks/depths and corpus statistics before any effectiveness. Record all
   metadata in a manifest; stop on mismatch rather than repairing silently.
4. Pass the authoritative synthetic metric gate, then run the single frozen
   five-arm comparison once. Use all planned queries and metrics; retain output
   identities and exact elapsed time. No retrieval model calls or label acquisition.
5. Independently reconstruct consequential results, record criticism and update
   the research map. Stop at that result whether positive, reversed or mixed.
   No k/weight/depth sweep, query router, substitute collection or automatic
   repair batch. A gate failure before effectiveness can motivate a separately
   recorded pre-outcome correction. A defect found after scores must preserve
   the first run and be identified as a post-outcome correction.

This cycle stops after preparation and review. Implementation, acquisition,
official evaluator execution and the actual transfer comparison remain future
work under this contract.
