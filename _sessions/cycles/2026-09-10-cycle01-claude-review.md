# Claude results memo — historical reviewer output

Read with [integration corrections](2026-09-10-cycle01-sources.md). This memo contains hypotheses and overstatements rejected in synthesis; the final report owns accepted conclusions.

**Cycle 01 review memo — Fable 5.1 coordinator, phase 2**
Receipt: `cycle01-review-5f005e00ca` (Relay seq=11, work_id cycle01-review). Not acknowledged here; no shell tool. Codex records consumption.

**Orchestration actually used.** One `ic-statistics` scout on the tail probe only (13 tool calls, ~40k subagent tokens; model ID not surfaced in the tool result). I did the geometry and cross-result work myself from `summary.json` of both cycles, `cycle01_rank_geometry.py`, `fusion_contract.py`, and one targeted read of the n6 tail block. No web tools used or assumed.

## 1. Bugs versus declared limits

No material implementation bug found. Checks that hold [observed]:

- Canonical RRF is one-based, fsum, docID ties, rejects in-list duplicates (`fusion_contract.py:37-38, 81-89`). Legacy k60 equals canonical k60 on 2019 and differs on 2020 only by the declared tie effect.
- CV selects on training folds only (`cycle01_rank_geometry.py:49-65`). The scout and I both confirm the tail specialist classification matches the protocol (owner rank ≤10 in full lists, absent from others' top30, tail-supported iff any other rank >30). The top30 cap applies to the owner too. Judged includes grade 0; unjudged gets zero gain consistently.
- Bootstrap resamples query-level deltas, interaction computed within query first. Same seed 1847 in every call, so intervals across comparisons are correlated; a hazard for reading one interval against another, not an error.
- Zero-width intervals are all-zero delta vectors (full vs equalized no-op; quotient on all-distinct lists), as you stated.

My earlier "leakage" claim was wrong and the correction stands. The residual concern is narrower: with all 25 folds selecting 200, the n6 selected-k OOF mean equals the full-data k200 mean exactly (0.4273350732 both), so the interval carries zero selection uncertainty, and k200 was already known to win on these 43 queries in May. It is a development replication, not held-out evidence.

Counterinterpretations to block:

- **The top30-cap collapse is mostly kernel flattening.** With ranks ≤30, the k=60 kernel spans 1/61..1/90 and k=200 spans 1/201..1/230; both are near-uniform votes. The cap arm shows 36/43 ties, 14 ordered top10 changes, 3 membership changes (tail summary lines 8572-8612). The interaction says the k contrast needs deep ranks to exist. It does not say deep support is informative.
- **Tail-supported equals coverage ≥2.** The group label is the very feature RRF rewards and the feature that drives pooling. Judged fractions are 25.5% vs 6.6% on n6 (lines 8677, 8688), and the ordering of judged fractions itself flips on 2020, where the "reversal" rests on 2 of 7. The scout's cheap offline check is still worth running: within tail-supported, does relevance-among-judged rise with coverage count 2 vs 3+? That uses `per_query.json` keys already present.
- **Interior k beats the limit.** On n6, k200 delta +0.0201 versus asymptotic +0.0116; on 2020 the asymptotic ordering loses to k60 with an interval excluding zero (−0.0095). Whatever k does, it is not coverage counting.
- **Duplication.** k200 displacement equals k60 displacement (top10 changed 0.901 vs 0.913 with one copy; absolute NDCG change 0.025 vs 0.026). Combined with the full-coverage counterexample, "k corrects source dependence" is retired on both proof and data.

## 2. Revised hypotheses and the missing observation

- **H1 → retired as a method, kept as a finding.** [observed] Trained k is configuration-specific: n6/n7 positive, n4 2019 negative with an interval excluding zero, 2020 tiny, both cross-annual transfers negative. Selected-k counts scatter across the grid on n4 (1/5/100/200/500). Nothing here transfers.
- **H2 → "k is a rank bandwidth."** [observed] The effect lives in deep ranks and is not the asymptotic order. [hypothesis] Best bandwidth grows with source count on 2019 (100, 100, 200, 200) and is 10 on 2020. Falsifier: leave-one-source-out landscapes that do not move monotonically with source count. Low value; do not chase.
- **H3 → dependence needs a non-k mechanism.** [observed] Plain RRF is vote-stuffable at every k; the quotient is invariant by construction. [hypothesis] The existing ensembles already contain near-copies (bm25/bm25_tuned, tfidf/tfidf_bigram), so part of the configuration-specific k behavior is k interacting with unmeasured dependence. Cheap descriptive: per-query rank correlation between those pairs, no protocol needed.
- **H4 → untestable on this data as posed.** [observed] The two-world fixture shows rank-only non-identifiability. The tail probe cannot supply a correctness feature because judgment coverage is confounded with every candidate feature. [hypothesis] More fundamentally, an all-lexical ensemble has no genuine specialist: isolated lexical singletons are rarely relevant under either the judged-only rate (1/6) or the unjudged-as-zero rate (0.011), and the character-hash run is not a different evidence type.

The most needed observation is **source provenance with a genuinely different evidence type**, and it fixes the judgment problem at the same time. TREC DL 2019/2020 pools were built from participant runs, including neural ones. A public neural or dense run for these queries is therefore far better judged than our generated lexical lists, so its singletons are observable. A fuller judging pass on the 313 unjudged n6 specialists would need passage text the repo does not hold, and would still leave us with lexical-only dissent.

## 3. One bounded next experiment: genuine specialist injection

Add one publicly archived neural/dense DL2019 and DL2020 run (official participant run or a reproducible Pyserini dense run) to the n4 lexical core. Same canonical contract, k=60 fixed, no k search, no new fusion method. Codex verifies provenance, licensing, and that the run's queries match; hash it like existing inputs.

Measure, all at query level with the existing bootstrap:

1. Judged fraction and relevance of dense-owned specialists (isolated and tail-supported) versus lexical-owned, same definitions.
2. Oracle rescue headroom: plain RRF with the dense source versus an oracle that places dense-owned relevant specialists at their best position. This is the upper bound any specialist channel could earn.
3. Whether owner identity plus tail support separates correct from noisy dense-owned specialists among judged, versus chance.

Competing predictions. **Spark alive:** dense-owned isolated specialists have a relevance rate well above lexical-owned ones, rescue headroom exceeds the resolution seen this cycle, and provenance-plus-tail-support beats chance. **Spark absorbed:** plain RRF already captures the dense value through singleton mass and headroom is near zero. **Null:** judged-fraction differences again dominate, reported as such.

Stopping rule: if rescue headroom is inside the paired bootstrap noise, close the specialist branch on this data and say so. Only if headroom is large does a routing feature design become justified, with source provenance an allowed input. Resource split: Codex does data acquisition and the run; one Opus scout audits judged fractions and the oracle computation; Fable interprets once. Information gain: it decides whether the original question is testable at all on obtainable data, and it converts "specialist" from a rank pattern into a labeled source, which is the cross-query dimension rank-only probes cannot see. The agent-system bridge is the same question, stated separately: does the aggregator know which agent holds different evidence, not merely that it disagrees. Retrieval results will not establish that.

## 4. For Dave, and whether to stop

Worth conveying now: cycle 01 is a clean, reproducible negative. Tuning k is configuration-specific and does not transfer across years. Large k is not a defense against copied or correlated sources, by proof and by measurement. The k effect depends on deep-rank evidence and is not coverage counting. The specialist question cannot be answered on an all-lexical, partially judged ensemble, and the tail-support association is confounded with judgment pooling.

Refuse to claim: any v8, any tail-support mechanism, any specialist rescue, any novelty, and any agent-system implication.

This is a meaningful checkpoint, not a point for another sweep. Three hypotheses retired or reframed, one sharpened question, and one concrete data requirement before further compute. The next wave is justified only by the injection experiment above, which needs one new input file, not more k grids.
