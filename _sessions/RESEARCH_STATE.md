# Research state — 2026-09-10

The live frontier is **distinguishing useful independent evidence from repeated
agreement, with enough observations to test the distinction**. Cycle01 repaired
the k comparison, reproduced its narrow six-ranker gain, and found that its
broader improvement and annual transfer remain unestablished. A depth intervention
and specialist-evidence inventory exposed what the present data can and cannot
resolve. The [cycle01 report](../results/cycle01-2026-09-10/REPORT.md) owns the new
numbers and interpretation; the historical audit below remains relevant to old
probes. No successor algorithm has been promoted.

The initial restart ran the synthetic demo and full `probe_ref_validation.py`
panel successfully, reproducing historical v6 means. [Raw REF output](evidence/2026-09-10-ref-validation.txt)
and [check/input-hash receipt](evidence/2026-09-10-restart-checks.json) record those
checks. The subsequent autonomous cycle added a canonical contract and two new
experiment runners without changing the historical probes or inputs. It used
real phased Fable5.1/Opus5 collaboration, documented in the cycle report and
[compute policy](CLAUDE_COMPUTE.md). No external novelty was established.

## Cycle02: the specialist association is observable, its mechanism is not isolated

The [cycle02 report](../results/cycle02-2026-09-10/REPORT.md) is the latest
checkpoint. A pinned SPLADE++ neural sparse source adds 97,000 numeric rankings
across the same 43/54 queries. Both raw hashes and all converted tuples were
independently verified. Selection followed a three-family access/provenance
inventory before measuring coverage. Historical inputs and cycle01 outputs
remain unchanged.

For SPLADE specialists, 19/43 and 22/54 queries have judged members in both
support groups, versus 1/43 and 2/54 for pooled lexical owners in this new
five-source inventory. Judgedness is not relevance. Isolated SPLADE specialists
are exactly the source top10 outside the retained lexical full union, so support
and that access indicator are perfectly coupled. Equalizing depth changes only
SPLADE and changes every query's candidate set. These are observation results;
no relevance or fusion effects were computed.

A resumed Fable5.1 coordinator and one Opus5 scout prompted a useful distinction:
a descriptive relevance association can still be measured. We corrected its
missing-label bounds, unsupported RRF-derived threshold, and overly strong
uniqueness language; see [review integration](cycles/2026-09-10-cycle02-review-integration.md).

**Next:** PLANNING R6 / [cycle03 protocol](cycles/2026-09-10-cycle03-specialist-association-protocol.md).
Implement synthetic sharp-bound checks before looking at actual outcomes. Use
all 20/23 candidate-paired queries, fixed full-arm cohorts, opposite missing-label
assignments, equal-query estimates, and separate-year bootstrap envelopes.
Delta=.10 is an explicit research resource threshold, not a performance claim.
The protocol chooses between a later fusion-contribution test and the controlled
known-truth branch; it has not run. No new selector or method is promoted.

## Cycle01 evidence and change of direction

- **H1 bounded:** canonical n6 k60=.4072603, training-selected k=.4273351.
  Across the four 2019 ensembles, average the effects within43queries:
  delta+.0039894, conditional query bootstrap95%[−.002963,+.010864]. Both
  cross-annual n4 transfers lose. Same-k selections in all25 n6 training folds
  are valid CV, not leakage. These are development estimates after prior search.
- **H2 refined:** n6 k200−k60 drops from+.0200748 to+.0025729 after a top30 cap.
  Depth matters; changing evidence and candidates together does not isolate a
  causal mechanism. Equal-depth truncation is a no-op because source lengths
  already match within every query. k200 is not the exact asymptotic ordering.
- **H3 structural:** copying a source still changes ordered top10 in roughly90%
  of one-copy interventions at k60 and200. A full-coverage counterexample proves
  no finite k guarantees clone invariance. Exact-list quotienting is invariant
  by construction, with no general source-quality or agent-performance claim.
- **H4 unresolved:** tail-supported versus isolated specialist candidates have
  highly unequal judgment coverage. Only1–5 queries per configuration contain
  judged examples in both groups. Pooled rates cannot establish a reliable
  correctness signal. Observation feasibility must precede the next effect test.
- **Original question recovered:** February13 consensus + specialist escape +
  anti-cabal uniqueness preceded the repo's February27 scaffold. See [ORIGIN](ORIGIN.md).
  [Checked sources](cycles/2026-09-10-cycle01-sources.md) correct the “unexamined
  k60” narrative and identify dependence-aware ensemble literature to examine.

## Evidence layers

| Layer | Current reading | Primary artifacts |
|---|---|---|
| Historical, specified: v5 | The reported +4.3% over Vanilla is specific to DL2019 with four lexical rankers: 0.3800 versus 0.3645 NDCG@10. Adding rankers or using DL2020 reverses that comparison. | [v5 spec](../spec/IC-RW-RRF-v5.0-CONFIDENCE-FUSION.md), [v6 results](../results/v6.0-regime-aware-fusion-results.md) |
| Historical, specified: v6 REF | Improves mean NDCG over v5 in all five tested configurations. DL2019 cross-ensemble means: REF 0.3919, Vanilla 0.3910, v5 0.3717. This does not establish a general advantage over Vanilla. DL2020: REF 0.4393 versus Vanilla 0.4483. | [v6 spec](../spec/IC-RW-RRF-v6.0-REGIME-AWARE-FUSION.md), [results](../results/v6.0-regime-aware-fusion-results.md) |
| Historical, specified: v7 PQAS | DL2020 repeated CV reports 0.4644 versus Vanilla 0.4483 and v5 0.4373. Reported p=.003 compares against v5; against Vanilla p=.125. DL2019 reports 0.3785 without a demonstrated gain over v5. Transfer failed in the tested directions. These estimates retain tuning/statistics caveats below. | [v7 spec](../spec/IC-RW-RRF-v7.0-PER-QUERY-ADAPTIVE-SELECTOR.md), [results](../results/v7.0-pqas-results.md) |
| Tracked exploration after v7 | Continuous-alpha variants, pooled collection features, three-class selection, cascade routing, and sharpness weighting did not establish a successor on existing data. They are already explored, despite older future-work lists. | [May stream 001](streams/2026-05-13-001-rank-fusion-possibility-space-opening.md), especially the 17:30 onward continuation |
| Untracked exploration at restart | Session 002 tested MC4, score fusion, empirical rank decay, operators, and k calibration. Its k-CV table reports DL2019 n=6 +0.0214 (p=.0024), cross-ensemble +0.0048 (p=.169), n=4 −0.0144, and failed transfer. Baseline conventions differ from the historical harness. No v8 spec/results release exists. | [May stream 002](streams/2026-05-13-002-basin-escape.md), [k probe](../evaluation/probe_v8_k_tuned_rrf.py) |

Preserve the original session-002 stream and its five probes: `probe_basin_escape_mc4.py`, `probe_basin_escape_score.py`, `probe_basin_escape_info_f.py`, `probe_aggregation_operator_landscape.py`, and `probe_v8_k_tuned_rrf.py`. Their untracked status at restart is provenance, not permission to discard them. Earlier exploratory files also use “v8” for unrelated candidates; a filename is not a released version.

## Audit issues to resolve

1. **RRF baseline conventions differ.** `evaluation/trec_eval_harness.py::_rrf_scores` uses `k + idx + 1`; both untracked operator/k probes use `k + idx`. The k probe additionally breaks ties by document ID. A lightweight audit reproduced DL2019 n=6 canonical Vanilla **0.4072603**, local k=60 **0.4059013**, and local k=61 **0.4072603**. Thus, apart from weighting scale and ties, `k_canonical = k_local − 1`: the local k=60 baseline corresponds to canonical k=59. DL2020 document-ID ties alone move 0.4483236 to 0.4483866. Reconcile conventions before comparing historical and provisional gains. Included run files store ranks starting at zero; `probe_basin_escape_info_f.py` directly indexes stored ranks, so future external run imports also need a declared convention.

2. **Nominal p-values are not confirmatory evidence.** `trec_eval_harness.py::paired_t_test` computes a t statistic but uses a normal CDF for its p-value. `probe_pqas_kfold.py` sweeps L2/threshold settings; `probe_pqas_significance.py` then reports the chosen settings on the same collections, without nested tuning. Many hypotheses were explored on these same queries. Inventory the selection/search budget; repeated-query dependence and exploratory selection may matter more than the distribution approximation. Correct the procedure and retain the original values as historical, approximate, unadjusted outputs.

3. **Aggregation units need consistency.** `probe_pqas_kfold.py::kfold_cv` averages unequal-sized fold means, while the significance script averages per-query outputs across seeds. `probe_v8_k_tuned_rrf.py` concatenates measurements of the same 43 queries across four nested ensembles for aggregate significance. Those 172 measurements are not 172 independent queries. Keep query identifiers and use uncertainty estimates that preserve the repeated-query structure.

4. **Benchmark scope is narrower than the prose suggests.** These are generated rerankings of supplied MS MARCO top-1000 candidates, filtered to judged query IDs; collection statistics are built from those candidate documents. Included lists have 5–200 documents for each of 43 DL2019 queries and 28–200 for each of 54 DL2020 queries. DL2020 includes only the four lexical rankers. The “semantic hash” run is character-n-gram random projection, not a trained dense semantic retriever. Describe transfer across annual query collections; independent-domain generalization remains untested. See `data/README.md` and `evaluation/generate_diverse_runs.py`.

5. **Several comparisons confound the proposed mechanisms.** MC4 uses a top-100 candidate union while Vanilla uses full supplied lists, up to 200. The planned score-mixture EM method was not implemented: `probe_basin_escape_score.py::fuse_bayesian_logit` explicitly reduces to CombSUM-Z. Operator variants change coverage treatment as well as aggregation. Empirical rank decay learns binary relevance at grade ≥2, while evaluation rewards graded relevance. These results do not isolate a unique causal reason for failure or exhaust those method families.

6. **Mechanism and sample-size statements are hypotheses.** Higher k reduces relative rank sensitivity and emphasizes coverage; correction of ranker correlation has not been separately demonstrated. A comparison of 43 versus 54 different queries does not establish a ~50-query training threshold. Failed transfer between these collections does not prove structural impossibility. Finite negative probes do not prove a label-free optimum or the unique optimality of SUM.

7. **Run regeneration is not fully deterministic.** `generate_diverse_runs.py::generate_semantic_hash_run` uses Python `hash(g)` despite setting a NumPy RNG seed. Hash randomization can change regenerated rankings. Record or stabilize hashing, input checksums, arguments, and environment before asserting clean regeneration reproduces committed runs. Preserve current run files as historical inputs.

8. **Specific documentation corrections remain.** The v7 spec lists ten features; `probe_pqas_supervised.py::FEATURE_KEYS` fits nine. REF already computes rho/alpha separately for each query. The v7 routing counts 73+89 sum to 162 decisions, not the stated 270. Session 002's displayed oracle-gap fraction is approximately **33%**: `(0.3953−0.3905)/(0.4051−0.3905)`, not ~50%. Its n=4 CV training sets contain **34–35 queries**, not 8–9. Fix active summaries without silently rewriting the historical stream.

The harness also needs an explicit metric contract: exponential NDCG gains, treatment of unjudged documents, `rel > 0` for MAP/MRR, cutoff behavior, duplicate handling, and rank/tie conventions. Validate that contract against an authoritative evaluator or independently specified examples while preserving the dependency-free demo.

## Next experiment sequence

The cycle01 canonical contract, training-only k grid, query aggregation, and
source/input/output manifests are complete. Do not repeat them on unchanged data
at initialization. The [phase-space map](PHASE_SPACE.md) and editable
[PLANNING](PLANNING.md) own the next discriminating experiment and residual
work. Legacy PQAS nested selection, an authoritative metric cross-check, and
deterministic regeneration remain open; new experiments should use the canonical
contract. An untouched diverse panel is needed for any performance promotion.

## Portfolio boundaries

Defensible framing: **an inspectable rank-fusion research system that discovered its initial gains were configuration-specific, corrected the claim, and evaluated supervised and structural alternatives against a strong simple baseline.** The substantive assets are the self-contained harness, specifications, included runs, ablations, and preserved negative results.

Treat v6/v7 numbers as historical development results with explicit comparison
targets and protocol limitations. Cycle01 validates the narrow k result under
the common contract but supplies no general performance promotion. Do not claim
general superiority, a proven optimum, label-efficiency thresholds,
independent-domain generalization, or a production-ready selector.
