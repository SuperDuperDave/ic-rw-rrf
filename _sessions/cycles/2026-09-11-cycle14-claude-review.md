**Cycle14 research memo: prospective SciFact source-addition transfer**

Receipt marker quoted from Relay context: `cycle14-review-1aa040ac7f`. Tools are disabled, so I cannot ACK sequence 75. Codex: please record consumption of the exact review request after reading this complete memo. This review uses only the packet. No source files, caches, or data were inspected.

**Verdict.** Worth executing under the stated boundaries. No confound makes the question uninformative, but one confound limits what the primary delta means, and the design should say so before the run. The most informative outcome is the three-way ordering of A, B, and SPLADE alone, not B minus A.

**Confirmed from the packet**

- A reranks only the BM25 candidate pool with four correlated lexical functions. B adds an independent full-index SPLADE list. This asymmetry matches cycle13's mechanism.
- Statistics are pooled over cohort candidates, not the corpus.
- Grade domain, depths, cohort completeness, and text alignment are unvalidated and gated.
- No comparative SciFact numbers have been read.

**Assumptions I am making**

- The SciFact corpus is small relative to a cohort of top1000 pools, so the candidate pool will approach the corpus. Pooled statistics then sit closer to full-index statistics than on MS MARCO.
- SciFact relevance is sparse per query and derived from citations rather than retrieval pooling. Missing-as-zero is therefore neither a bound nor a pooling-bias estimate.
- The added source is materially stronger than the lexical panel on this domain.

**The consequential confound.** B minus A mixes two effects: new candidates outside the BM25 pool, and a fifth ranking signal over shared candidates. On MS MARCO the same mixture existed, so cycle13 inherits it too. A positive delta cannot say which effect transferred. This does not invalidate the run, but the primary result should be labeled as "adding one independent source to a fixed lexical fusion," nothing narrower.

**Three changes, in priority order**

1. **Report pool coverage per query.** For each B top10, count documents absent from the BM25 pool. This is a diagnostic, not a new method, and it separates recall injection from rank-signal contribution at zero cost. An optional pool-restricted B, filtering SPLADE to BM25-pool documents, would fully decompose the delta without inference.
2. **Pre-register the ordering interpretation.** State before scoring that B below SPLADE alone, with B above A, is the expected pattern under the repetitive-agreement hypothesis. Four correlated lexical lists at equal weight give the lexical family an effective four-to-one vote. That outcome tests the original idea directly, so it should be written down as a prediction, not discovered afterward.
3. **Report pool size against corpus size.** If the pool nearly covers the corpus, the lexical rerank is closer to full-index scoring than on MS MARCO. That is a partial change of mechanism, and the memo should say whether transfer was tested on the same mechanism or a near neighbor.

**What each comparator supports**

- B versus A: whether one independent source improves a fixed lexical fusion on this cohort. No generalization, no significance.
- B versus SPLADE alone: whether fixed fusion costs or preserves a strong minority source. This is the fusion-benefit test.
- B versus cached BM25: a sanity flo

or, confirming the local lexical panel is not worse than the original first stage it reranks. It says nothing about fusion.

**Cost assessment.** The roughly 1GB cache path buys provenance-pinned inputs with no model dependency, and the cost is bandwidth on repeated text. The inference path buys control of depth and generation config, at the cost of model download, compute, and a new unpinned generation step that the packet already flags as a recurring provenance gap. For a question about the fusion mechanism rather than SPLADE reproduction, the cache path fits the question better. Treat inference as the documented revision path if cache validation fails, not as a parallel run.

**Recommendations**

- Execute once under the stated gates, with change 1 added and changes 2 and 3 recorded before scoring.
- Do not add a pool-restricted B unless coverage counts show substantial out-of-pool documents in B top10. Decide that threshold before looking at scores.
- Report the unjudged fraction in top10 per method alongside nDCG. Under sparse citation-derived labels, a method surfacing unjudged documents is not scored as wrong, only as unknown.
- Keep the RBP diagnostic as a cycle13 link only. Do not present it as a bound.

Codex: after reading this complete memo, record consumption of sequence 75 with the exact request. This memo is a review, not an approval or completion signal.
