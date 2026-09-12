# Cycle14 — critique a prospective retrieval transfer

Dave authorizes ongoing Codex/Claude research and explicitly stated on 2026-09-11:
"I approve sharing anything and everything with Claude." This packet contains
unpublished project findings and a proposed next design for the existing signed-in
Claude service through this project's Relay. No public-availability prerequisite.

You are the bounded methodological reviewer. Use only this packet; tools, MCP,
scouts and workflows are disabled. Do not edit files or request another provider
wave. One Fable5.1/high invocation, native list-accounting cap $1.50, wall180s,
4000 configured output tokens per API response, native max-turns1. Codex workers
are separately checking source metadata and local implementation. Higher reasoning
capacity is reserved here for whether the proposed comparison answers the question.

Return a concise public research memo, about500 words. Quote the cycle14 receipt
marker supplied only in Relay context. If unable to ACK with tools disabled, ask
Codex to record consumption of the exact request after reading your complete memo.
Distinguish confirmed facts, assumptions, and recommendations. Do not claim to have
inspected source files or data outside this packet.

## Context

Curiosity-led rank-fusion research; negative results and better questions count.
The original idea concerns useful minority evidence versus repetitive agreement.
We have parked an exhausted arithmetic verifier laboratory and old-panel tuning.
Cycle13 compared A=canonical equal-weight k60 RRF of four retained lexical lists
against B=A plus existing SPLADE++ EnsembleDistil. On97 reused DL2019/2020 queries,
both annual mean B−A bounds are positive under every allowed missing-grade
completion for an unnormalized top10 RBP diagnostic (p4/5, grade/3). Nine queries
favor A. That is not an nDCG or generalization result, nor evidence of fusion
beating the added source alone. More labels cannot change the annual direction.

The next question is whether a fixed source-addition comparison transfers to a
new domain. We selected BEIR SciFact before source inspection because it is a
small scientific-abstract collection, different from MS MARCO passages. No new
collection effectiveness or published comparative performance table has been
read. No dataset sweep or automatic alternative collection this preparation.

## Facts from current independent preparation

- The four lexical lists come from existing local scoring functions: BM25
  (k1=1.2,b=.75), BM25(.9,.4), unigram log-TF/IDF divided by sqrt(document length),
  and QL Dirichlet(mu2000). Shared fixed tokenizer/stopwords; no new tuning.
- They rerank supplied MS MARCO top1000 candidates. Statistics pool unique
  candidate documents across included queries, not the full corpus. Most saved
  outputs have depth200. Exact original first-stage retriever/config is unpinned.
  Stable source-score ties retain candidate order. Canonical fusion uses one-based
  reciprocal contributions and ascending string IDs for computed float ties.
- The same public Castorini cache revision used previously has SciFact BM25 and
  SPLADE++ EnsembleDistil top1000 JSONL files with LFS hashes. Unauthenticated HEAD
  succeeds; combined size995,932,483 bytes, mostly repeated text. No numeric TREC
  alternative was found in that dataset. Top100 files exist but truncate the
  intended lexical candidate and added-source depths. No full run body downloaded.
- Producer code maps independent full-index BM25 and SPLADE SciFact search;
  exact historical generation command/index digests remain unknown, as for the
  old SPLADE cache. BEIR corpus/query/qrel mirrors have immutable revisions;
  actual file-level cohort, text alignment, depth and scores still need validation.
  Raw text remains ignored/private; publish provenance and numeric research facts.
- NIST trec_eval uses linear nDCG gain; our legacy harness uses2**grade−1. These
  coincide for binary grades, conditional on validating the SciFact grade domain.
  The old general driver intersects available query IDs and runs unplanned methods;
  a small strict adapter must preserve the fixed cohort and planned methods instead.

## Proposed next execution (not run this cycle)

Acquire only the pinned two top1000 caches and small collection/qrel metadata,
with fixed byte/hash caps and no model inference. Validate complete official test
cohort, positive-qrel eligibility, string IDs, binary grade domain, text consistency,
actual depths, finite scores and source order before scoring. Missing required
queries/inputs stop the run; never silently take a ranker intersection.

Rerank only the BM25 candidate pool using the four unchanged local functions;
pool statistics over the frozen cohort; retain up to200 per lexical source. B
adds the independent SPLADE top1000. This is a mechanism-level adaptation,
explicitly not an exact-pair replication of an unpinned original candidate generator.

Primary: equal-query mean nDCG@10(B)−nDCG@10(A), binary gains, absent qrels0,
positive-IDCG official test queries. Before data scoring, verify synthetic cases
against pinned NIST trec_eval and serialize strict rank-proxy scores to preserve
the chosen ranking order. No query/document equal-ID removal across namespaces.
Report B versus SPLADE alone and original cached BM25 as fixed secondary baselines;
a win over A alone establishes no fusion benefit beyond a single source. Also
report the fixed top10 RBP binary-gain diagnostic to relate to cycle13, without
equating missing-as-zero benchmark scores to worst-case judgment bounds.

No hyperparameter search, significance claim, label acquisition, per-query router,
extra collection, or model batch. Report the finite-panel delta and query outcomes,
including null/reversed findings. Stop after one complete validated comparison
or an integrity failure; any revision is separately documented before a new run.

Is this worth executing under those boundaries, or does a material confound make
the question uninformative? Identify at most three consequential changes and the
narrow interpretation each comparator can support. Assess the roughly1GB cache
cost versus a distinct inference-heavy alternative, without assuming either wins.
