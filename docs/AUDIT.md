# Audit of the historical results

An audit at the September 2026 restart reproduced the historical v5, v6 and v7
numbers and found the caveats below. They apply to the tables in the
[README](../README.md), the [v6](../results/v6.0-regime-aware-fusion-results.md)
and [v7](../results/v7.0-pqas-results.md) result files, and the
[specifications](../spec/). The original values stay as recorded; read them as
historical, approximate and unadjusted until each issue is resolved.

## Issues to resolve

1. **RRF baseline conventions differ.** `evaluation/trec_eval_harness.py::_rrf_scores` uses `k + idx + 1`; the operator and k probes (`probe_aggregation_operator_landscape.py`, `probe_v8_k_tuned_rrf.py`) use `k + idx`. The k probe additionally breaks ties by document ID. A lightweight audit reproduced DL2019 n=6 canonical Vanilla **0.4072603**, local k=60 **0.4059013**, and local k=61 **0.4072603**. Thus, apart from weighting scale and ties, `k_canonical = k_local − 1`: the local k=60 baseline corresponds to canonical k=59. DL2020 document-ID ties alone move 0.4483236 to 0.4483866. Reconcile conventions before comparing historical and provisional gains. Included run files store ranks starting at zero; `probe_basin_escape_info_f.py` directly indexes stored ranks, so future external run imports also need a declared convention.

2. **Nominal p-values are not confirmatory evidence.** `trec_eval_harness.py::paired_t_test` computes a t statistic but uses a normal CDF for its p-value. `probe_pqas_kfold.py` sweeps L2/threshold settings; `probe_pqas_significance.py` then reports the chosen settings on the same collections, without nested tuning. Many hypotheses were explored on these same queries. Inventory the selection/search budget; repeated-query dependence and exploratory selection may matter more than the distribution approximation. Correct the procedure and retain the original values as historical, approximate, unadjusted outputs.

3. **Aggregation units need consistency.** `probe_pqas_kfold.py::kfold_cv` averages unequal-sized fold means, while the significance script averages per-query outputs across seeds. `probe_v8_k_tuned_rrf.py` concatenates measurements of the same 43 queries across four nested ensembles for aggregate significance. Those 172 measurements are not 172 independent queries. Keep query identifiers and use uncertainty estimates that preserve the repeated-query structure.

4. **Benchmark scope is narrower than the prose suggests.** These are generated rerankings of supplied MS MARCO top-1000 candidates, filtered to judged query IDs; collection statistics are built from those candidate documents. Included lists have 5–200 documents for each of 43 DL2019 queries and 28–200 for each of 54 DL2020 queries. DL2020 includes only the four lexical rankers. The “semantic hash” run is character-n-gram random projection, not a trained dense semantic retriever. Describe transfer across annual query collections; independent-domain generalization remains untested. See `data/README.md` and `evaluation/generate_diverse_runs.py`.

5. **Several comparisons confound the proposed mechanisms.** MC4 uses a top-100 candidate union while Vanilla uses full supplied lists, up to 200. The planned score-mixture EM method was not implemented: `probe_basin_escape_score.py::fuse_bayesian_logit` explicitly reduces to CombSUM-Z. Operator variants change coverage treatment as well as aggregation. Empirical rank decay learns binary relevance at grade ≥2, while evaluation rewards graded relevance. These results do not isolate a unique causal reason for failure or exhaust those method families.

6. **Mechanism and sample-size statements are hypotheses.** Higher k reduces relative rank sensitivity and emphasizes coverage; correction of ranker correlation has not been separately demonstrated. A comparison of 43 versus 54 different queries does not establish a ~50-query training threshold. Failed transfer between these collections does not prove structural impossibility. Finite negative probes do not prove a label-free optimum or the unique optimality of SUM.

7. **Run regeneration is not fully deterministic.** `generate_diverse_runs.py::generate_semantic_hash_run` uses Python `hash(g)` despite setting a NumPy RNG seed. Hash randomization can change regenerated rankings. Record or stabilize hashing, input checksums, arguments, and environment before asserting clean regeneration reproduces committed runs. Preserve current run files as historical inputs.

8. **Specific documentation corrections remain.** The v7 spec lists ten features; `probe_pqas_supervised.py::FEATURE_KEYS` fits nine. REF already computes rho/alpha separately for each query. The v7 routing counts 73+89 sum to 162 decisions, not the stated 270. The second May 2026 exploration's displayed oracle-gap fraction is approximately **33%**: `(0.3953−0.3905)/(0.4051−0.3905)`, not ~50%. Its n=4 CV training sets contain **34–35 queries**, not 8–9. Fix current summaries without silently rewriting the historical records.

The harness also needs an explicit metric contract: exponential NDCG gains, treatment of unjudged documents, `rel > 0` for MAP/MRR, cutoff behavior, duplicate handling, and rank/tie conventions. Validate that contract against an authoritative evaluator or independently specified examples while preserving the dependency-free demo.
