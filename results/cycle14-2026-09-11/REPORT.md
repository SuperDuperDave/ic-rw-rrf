# Cycle14 — preparing a transfer that can answer the question

**Outcome: a concrete SciFact input path and prospective comparison are ready for
implementation. No new retrieval effectiveness has been measured.** We selected
this scientific-abstract collection before source inspection to move beyond the
project's reused MS MARCO passage panels. The preparation stopped at its planned
checkpoint; it did not choose a dataset because a method won there.

The [execution protocol](../../_sessions/cycles/2026-09-11-cycle14-transfer-protocol.md)
and [machine-readable input plan](../../_sessions/evidence/2026-09-11-cycle14-input-plan.json)
fix the comparison, source revisions, byte identities, metrics and stopping rules.

## What became clearer

The old four-source lexical fusion is built from rerankings of supplied candidates,
with statistics pooled across unique candidate documents. It is not four independent
full-corpus searches. Its unigram TF-IDF score is length-normalized log-TF/IDF,
despite a historical documentation label calling it cosine. The current data README
is corrected; old code, inputs and measured results are unchanged.

The original first-stage candidate generator is not pinned. Consequently this
transfer preserves the local formulas and source-addition structure but uses a
documented SciFact BM25 candidate source: a mechanism-level adaptation, not an
exact-pair replication. [Local implementation audit](../../_sessions/cycles/2026-09-11-cycle14-local-input-audit.md).

The same public Castorini revision used in cycle02 has SciFact BM25 and SPLADE++
EnsembleDistil top1000 caches. Metadata gives immutable LFS hashes; two unauthenticated
HEAD requests returned HTTP200 with matching advertised lengths. Their combined
size is 995,932,483 bytes. Corpus/query/qrels mirrors add 4,540,287 bytes. This is a
download-and-local-scoring route, with no neural inference needed. Exact cache
schemas, actual depths/cohort and corpus alignment remain body-validation gates;
the historical cache generation command and model/index digests remain incomplete.
[Source evidence and limits](../../_sessions/cycles/2026-09-11-cycle14-source-audit.md).

We chose the top1000 route because top100 would alter the intended candidate and
depth contract. That decision precedes effectiveness. The raw-input cap is1.05GB;
the small Parquet identity check has a separately pinned 50,102,437-byte PyArrow
wheel. Nothing was downloaded beyond source/metadata responses, and no package
was installed. External raw text remains ignored in any later acquisition.

## The test that follows

| Arm | Fixed system |
| --- | --- |
| P | Cached BM25 top1000 |
| S | Cached SPLADE++ top1000 alone |
| A | Canonical k60 RRF of four unchanged lexical scorers reranking P, each retaining up to200 |
| B | Same four lexical lists plus S under canonical k60 RRF |
| H | Simple canonical k60 RRF of P and S |

The primary is equal-query mean binary nDCG@10(B)−nDCG@10(A). B−S checks whether
fusion adds value over using the added source alone; B−H checks the elaborate
lexical system against a simple hybrid. B−P and A−P remain named contextual
comparisons. All are frozen before scoring, with no best-method selection or
parameter search on this collection.

The metric bridge matters. The local harness uses exponential gains; NIST's
implementation uses relevance values directly. They coincide for binary grades,
which must be checked before reuse. Synthetic comparison against a pinned official
evaluator is a required execution gate. The adapter must also preserve the full
test-query denominator and ranking order rather than use a general driver's
query intersection or tied-score reordering.
[Independent metric audit](../../_sessions/cycles/2026-09-11-cycle14-metric-audit.md),
[pinned evaluator sources](../../_sessions/evidence/2026-09-11-cycle14-metric-sources.json).

A secondary binary top10 RBP contribution links metric directions to cycle13.
It does not transfer cycle13's missing-judgment bounds. Missing-as-zero benchmark
scoring is explicit; it does not establish that every unjudged document is irrelevant.
No confidence interval, p-value, population-generalization or independence claim
is planned from this single fixed panel.

## Claude review and integration

One Fable5.1/high review supported execution of the proposed transfer. Native
execution succeeded in128.89982seconds at$0.7789435 list accounting, under the
fixed$1.50/180second limits. This is not subscription billing. Three native message
IDs were observed; all public text was recovered from two fragments because the
terminal result alone was incomplete. No tools or scouts ran. Request75 was read
and its requested consumption ACK recorded as79; Relay is clear.
[Exact memo](../../_sessions/cycles/2026-09-11-cycle14-claude-review.md),
[receipt](../../_sessions/evidence/2026-09-11-cycle14-review-receipt.json).

We accepted descriptive candidate-pool size, candidate-union/corpus ratio,
B-top10 outside-pool counts, and per-arm missing-qrel counts. They make the
comparison easier to interpret. The simple hybrid H came from the independent
Codex metric audit; it was added before scoring and was not in Claude's packet.

We qualified or declined several reviewer claims:

- Separate indexes do not establish statistically independent errors. The added
  source being stronger on SciFact is an untested assumption, not a design fact.
- Coverage counts do not separate causal contributions. A pool-restricted B would
  change ranks and fusion geometry; it would not automatically fully decompose
  the observed delta. No conditional extra arm or coverage-triggered experiment.
- B above A but below S would show source addition with no advantage over S for
  that metric. It would be compatible with several explanations, including lexical
  weight and source quality; it would not identify repetitive agreement as a cause.
- B−P does not establish A−P. Both contrasts are explicitly reported. A missing
  qrel contributes zero metric gain while its true relevance remains unknown.
- No automatic inference fallback follows a cache failure. Stop, preserve the
  failure, and decide a separately documented revision before new outcomes.

The exact memo is preserved, including its split word and unsupported claims.
Claude reviewed the supplied design summary, not cache bodies, the final protocol,
or a completed transfer result. Independent Codex review covers the final contract.

## Checkpoint and next action

The preparation used independent implementation, public-source and metric audits.
Source identities, input-plan arithmetic, local links, whitespace and preservation
of frozen research artifacts are checked in the
[final receipt](../../_sessions/evidence/2026-09-11-cycle14-checks.json).
Research implementation did not change, so the previous183-test result was not
rerun or counted as new evidence. No actual SciFact data bodies, new relevance
judgments, retrieval/model batch or website publication occurred.

R17 is complete as preparation. R18 owns the small adapter, pinned acquisition,
integrity/evaluator gates and one frozen transfer run. A null, reversal or mixed
result is an acceptable endpoint; any failure is recorded without substituting
another collection or tuning the old query reversals.
