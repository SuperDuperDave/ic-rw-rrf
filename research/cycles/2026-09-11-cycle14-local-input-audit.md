# Cycle14 — local ranker and transfer-input audit

Read-only implementation/provenance audit on 2026-09-11 for R17 preparation.
Starting project checkpoint: `cc421896df9c2c35b88c795bbd307273abfc6481`.
No retrieval, effectiveness evaluation, new collection acquisition, model call,
package installation, or new collection outcome inspection was performed.
The worker owns only this note; the coordinator owns the transfer decision.

## Finding

The safest available route preserves the four **implemented lexical rerankers**
over one separately supplied lexical candidate pool, then adds an independently
supplied learned sparse ranking under canonical k60 RRF. The existing code can
score another collection with a small input adapter. It does not supply that
collection, its initial candidate retrieval, or its learned sparse source.
Matching family names alone is insufficient to establish the same comparison.

The historical inputs establish an applied comparison with different candidate
access and retained depths. They do not isolate the quality of added expertise.
See the [cycle13 report](../../results/cycle13-2026-09-11/REPORT.md) and
[retained-input correction](2026-09-11-cycle13-retained-input-correction.md).

## What the four lexical sources compute

Authoritative implementation: [`generate_diverse_runs.py`](../../evaluation/generate_diverse_runs.py),
lines 76–97, 118–211, 480–495 and 632–660. SHA256 at audit:
`0702155886c270c507b5c4a3f21e1145782ba25d8b4fd430fc10dac7ef0233f8`.

Shared preprocessing lowercases text, splits at every non-alphanumeric character
using Python `str.isalnum`, removes the explicit English stopword set, and removes
tokens of length one. Unicode alphanumeric characters survive. There is no
stemming, lemmatization, subword tokenizer, or query-term deduplication. Repeated
query terms repeat their score contribution. Query and document preprocessing
are identical.

Let N be the number of unique candidate document IDs in the statistics pool,
df(t) its document frequency, cf(t) its term frequency, T its total token count,
dl the document's token count, and avdl the mean count. The sum below iterates
the tokenized query with multiplicity. Natural logarithms are used.

| Saved source | Exact implemented score / parameters |
| --- | --- |
| `bm25` | Sum over matched t of `log(1 + (N-df(t)+0.5)/(df(t)+0.5)) * tf(t)*(k1+1)/(tf(t)+k1*(1-b+b*dl/avdl))`; k1=1.2, b=0.75 |
| `bm25_tuned` | Same formula; k1=0.9, b=0.4. The name is a fixed configuration here, not a proposal to tune on SciFact. |
| `tfidf` | `sum((1+log(tf(t))) * log(N/(df(t)+1))) / sqrt(dl)` over matched t; empty document returns 0. This is not cosine similarity. |
| `ql_dirichlet` | Sum of `log((tf(t)+mu*cf(t)/max(T,1))/(dl+mu))` where that probability is positive; mu=2000. Empty document returns -1e10. |

Two less conventional details must be preserved if the aim is mechanism transfer:
TF-IDF IDF can be negative when df=N; QL skips query terms with zero collection
frequency rather than adding negative infinity. A tokenized-empty query is
omitted entirely by `generate_lexical_run`. A future strict adapter should detect
that case before scoring and follow its frozen eligibility rule, rather than
silently lose a query.

`data/README.md:14` labels the unigram TF-IDF source “cosine similarity.” The code
contradicts that label; the separate bigram ranker uses cosine. Neither an
off-the-shelf cosine TF-IDF implementation nor a new BM25 library is an exact
replacement for these four functions.

## Original candidate and statistics contract

`load_top1000` (lines 50–69) consumes four tab-separated fields:
`qid, docid, query_text, passage_text`. Candidate order is the source file order;
the first observed query text is retained. The loader silently skips short rows
and reads only the first four fields. It does not check repeated IDs or
inconsistent repeated text.

The driver first filters candidate/query maps to query IDs present anywhere in
the qrels (lines 636–642). It does not select queries by positive relevance.
`build_collection_stats` then deduplicates document IDs across **all remaining
query candidate pools** and computes statistics on that union. The first text
seen for a repeated ID supplies its statistics. Empty documents count in N.
Statistics are neither full MS MARCO corpus statistics nor per-query statistics.
Thus changing the included query set can change scores through the pooled
statistics, even without using relevance grades. Generate the frozen cohort
together, not as independent query batches with separate statistics.

`data/README.md` identifies the original MS MARCO top1000 TSV URLs. The local
generator itself performs no first-stage retrieval. This audit found no original
candidate-generator command, configuration, corpus-statistics snapshot, or TSV
checksum. Both expected raw TSV paths are absent locally. Therefore the local
evidence supports “reranking supplied MS MARCO candidates”; it does not establish
the exact original first-stage retriever, its tie behavior, or clean regeneration
of the committed lexical runs. The implementation and data README entered in
commit `3b4f4ce`; their Git history supplies no later regeneration receipt.

The saved lexical lists are mostly depth200, from `top_k=200` after scoring the
supplied candidates. Exact metadata already pinned in cycle13 is:

| Panel | Each lexical source | Added SPLADE++ source |
| --- | --- | --- |
| DL2019 | 43 queries: 41 lists of200, one of37, one of5 | 43 lists of1000 |
| DL2020 | 54 queries: 52 lists of200, one of188, one of28 | 54 lists of1000 |

These are retained-output depths, not proof of the original raw pool lengths.
All retained lists stay in cycle13, including the short query.

The [SPLADE provenance note](../../data/cycle02/README.md) documents a separate
full-index retrieval path using `msmarco-v1-passage.splade-pp-ed-text` and the
SPLADE++ EnsembleDistil family. Exact historical cache production command and
index/encoder digests are not supplied. The raw cache contains the added source's
candidate texts; using those as the four lexical sources' pool would give A the
added source's candidate access and change the experiment.

## Ranking, scores, and fusion

The lexical generator uses a stable descending sort on the unrounded float score.
Exact ties retain candidate input order. It then emits zero-based contiguous
ranks and six decimal score digits. Distinct internal scores can become equal
after serialization; those apparent ties still retain the already computed
order. Neither source ties nor rounded ties are re-sorted by document ID.

[`read_ranked_run`](../../evaluation/cycle02_observation_audit.py), lines 83–118,
validates six fields, contiguous rank origin, finite/nonincreasing scores, and
unique document IDs per query. It preserves serialized order without score
sorting or repair. Historical lexical origin is0 and the converted SPLADE source
origin is1. The latter preserves its raw candidate-array order, including ties.
Scores are available in both types of saved file; canonical RRF ignores their
magnitudes after the input validation.

[`canonical_rrf`](../../evaluation/fusion_contract.py), lines 57–89, assigns
one-based contributions `1/(60+rank)`, zero contribution for absence, equal
source weights, `math.fsum` for accumulated float scores, and ascending **string**
document ID for ties in those computed fusion scores. This differs from source
tie handling. Preserve the four-source order `bm25, bm25_tuned, tfidf,
ql_dirichlet`, followed by the added source in B. Cycle13 uses this floating
contract, not a rational ordering of the fusion scores.

## Minimum future adapter and safest comparison

The following is an implementation boundary for a future frozen protocol, not
an executed or acquisition-authorized command in this preparation:

1. Pin a collection/split, complete query-ID cohort, corpus/query/qrel bytes, a
   separate lexical candidate run, and one learned sparse run. Require ID
   compatibility and one declared candidate order. Fix title/body joining and
   whitespace handling before scoring; do not substitute cache text silently
   for the pinned collection text. Reject duplicate query/document IDs and
   inconsistent text instead of relying on the old loader's first-seen behavior.
2. Construct `data[qid] = [(docid, text), ...]` in the supplied lexical candidate
   order, and `queries[qid] = text`. Preserve up to1000 available candidates per
   query, with no qrel-document injection or grade-based candidate filter.
   Build statistics once over the union for the complete frozen cohort using
   `build_collection_stats`, then call the four existing scoring functions via
   `generate_lexical_run(..., top_k=200)`.
3. Import those functions through a small driver. Do not invoke the current
   generator CLI: it also attempts three extra rankers and ends by computing
   relevance diagnostics. There is no lexical-only/no-analysis CLI switch.
4. Convert the new learned sparse source to one declared rank origin, preserve
   its supplied order and scores, retain its fixed top1000 where available,
   and validate all five sources before evaluation. Record actual query/depth
   maps and hashes, rather than assuming every list reaches its cap.
5. Reuse the strict ranked reader and canonical fusion for A=four lexical
   sources and B=A+the learned sparse source. Freeze the metric/cohort decision
   separately. `trec_eval_harness.ndcg_at_k` (lines139–149) already accepts
   integer binary grades, uses exponential gain, treats absent qrels as zero,
   and returns zero for zero IDCG; the caller still controls query eligibility.

This keeps the lexical formulas, candidate-pool statistics policy, retained
depth policy, and applied source-addition structure. It is a **mechanism-level
adaptation**, not an exact-pair replication: a new collection necessarily changes
document/query content, and the old initial candidate generator is not pinned.
An auditable independently produced lexical candidate pool is the closest local
analogue. Reranking the entire new corpus changes candidate access and statistics;
using the new SPLADE pool changes access in A; replacing A with one published
BM25 run changes the baseline ensemble. Each may answer a useful question, but
none is a silent substitute for the proposed four-source transfer.

If the candidate audit finds only one source family or lacks compatible text,
stop at that feasibility limit. The existing ranker code does not justify
selecting a different collection or changing the baseline after score inspection.

If SciFact qrels are confirmed binary, cycle13's unchanged grade/3 diagnostic
must not be copied blindly: it would assign a positive label gain1/3 while still
allowing unjudged grades through3. A separately frozen gain/unknown-label contract
is needed for any secondary partial-judgment bounds. Ordinary benchmark nDCG
with absent-as-zero and missing-judgment bounds are distinct estimands.

## Local availability and limits

Metadata-only inventory used `/usr/bin/python3`, version3.12.3. Installed selected
distributions: NumPy1.26.4, SciPy1.11.4, huggingface-hub1.6.0, ONNX Runtime1.27.0.
Not registered in that interpreter: torch, transformers, sentence-transformers,
pyserini, beir, ir-datasets, datasets, rank-bm25, nltk, pytrec-eval, ir-measures.
No `java` executable is on PATH. `uv` is available; no repo `.venv` exists.
This is a scoped active-interpreter inventory, not a claim about every possible
environment on the host. The four lexical scorer functions themselves need only
the standard library; optional NumPy/SciPy imports occur at module load.

Repository data contains the two historical DL panels and cycle02 source files.
The two ignored raw cycle02 JSONL cache files are present. Both original MS MARCO
top1000 TSV files remain absent. No SciFact/SPLADE-named top-level entry appeared
in the inspected Hugging Face hub/datasets caches or ir_datasets directory; this
limited filename inspection does not establish host-wide absence. No cached
collection content or unseen source scores were read.

Checks were source/code reads, `session.py status`, source hashes, relevant Git
history, path existence, and installed-distribution metadata. No tests or
effectiveness measurements were needed for this documentation-only audit.
No worker-created process, claim, or provider session remains live.

**Friction routing:** SUBTRACT the incorrect TF-IDF cosine label in the current
data README through the coordinator's documentation ownership. This note reports
the mismatch; no label correction has landed in this worker's scope. PROMOTE
candidate provenance/statistics and source-versus-fusion tie distinctions into
the single prospective transfer protocol. Do not create a separate tuning task.
