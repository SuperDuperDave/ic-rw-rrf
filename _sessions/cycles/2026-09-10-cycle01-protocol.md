# Cycle 01 — rank geometry and independent evidence

Written before this cycle's numerical results. Existing TREC data have already
been extensively explored; this is a development protocol, not retrospective
preregistration or a confirmatory trial. Claude's pre-run critique may revise
this protocol before execution; later adaptations will be marked as such.

## Question and competing explanations

The original proposal sought useful consensus plus a protected minority channel
and resistance to correlated votes. The later k result may reflect (a) a changed
baseline convention, (b) coverage versus rank sensitivity, (c) selection on a
small repeatedly explored query set, or combinations of these. A copied ranker
adds no new observation, but plain RRF counts it as another vote.

## Frozen numerical comparison

- Inputs: included seven 2019 / four 2020 rankers, qrels, and exact input hashes.
- Configurations: 2019 n=4,5,6,7; 2020 n=4. Lexical core ordered BM25,
  BM25-tuned, TF-IDF, QL-Dirichlet; extensions proximity, bigram, character hash.
- Candidates: full supplied lists, same eligible queries for every compared
  method within a configuration. No new pool truncation or silent missing ranker.
- RRF: one-based position, equal source weights, `math.fsum`, deterministic
  document-ID ties. Historical baseline also scored separately to expose drift.
  Formula is ordinary RRF, not a claimed new method.
- Primary outcome: mean NDCG@10 using the existing exponential graded-gain
  metric; unjudged documents have zero gain. Preserve query IDs and raw scores.
- Grid: `[1,5,10,30,60,100,200,500]`; baseline k=60. Select k using only training
  queries. Equal training means choose the first/smallest k in the grid.
- Five folds, seeds `[42,123,7,99,2026]`. Store all train/test memberships and
  selected k. Average each query's held-out score over seeds, then average queries.
- Descriptive uncertainty: paired query bootstrap, 4,000 resamples, seed1847.
  For the 2019 aggregate, first average the four ensemble deltas within each
  query; bootstrap the 43 query clusters, not 172 pseudo-independent rows.
  These intervals condition on fixed OOF predictions and do not include full
  training-set/selection uncertainty. Report seed sensitivity, not a p-value.
- Additional descriptive comparisons: fixed k200, exact-duplicate quotient k60,
  coverage-first/rank-sum proxy, and full asymptotic rank-moment ordering.
- Cross-annual transfer: choose k on every n=4 query from one year, evaluate on
  all eligible n=4 queries of the other. Both years remain development evidence.

## Mechanism interventions

**H2: large-k geometry.** The expansion is
`1/(k+r) = 1/k − r/k² + r²/k³ − …` for k larger than the finite ranks.
Coverage dominates, followed by rank sums, then alternating higher moments.
A coverage/rank-sum proxy is not the exact limiting ordering when those two
terms tie. Compare both the proxy and full asymptotic ordering with grid outputs;
record NDCG and exact ordered top10 equality. A matching outcome is descriptive
of these inputs, not proof that k200 has reached its asymptotic regime.

**H3: repeated evidence.** On each year's n=4 configuration, duplicate each
source with 1 and 3 additional exact copies. Evaluate k60 and k200, keeping qrels
and other source lists fixed. Report ordered-top10 change and signed/absolute
NDCG change. Average source interventions within each query before bootstrap.
Repeat after quotienting identical ordered lists; exact-copy invariance is
expected by construction and is not evidence of improved relevance.

**Pre-run critique refinement:** supplement the retrieval interventions with a
full-coverage five-document counterexample. Let x have ranks `(1,5,5)` and y
`(5,1,1)` in three complete lists; copying the first list twice reverses their
ordering for every finite k>=0. Their score difference is exactly the sign of
`1/(k+1)−1/(k+5)`. All documents are present in every source, so this particular
failure of duplication invariance does not rely on differential coverage or
candidate truncation. Do not infer a universal monotonic relationship between
k and empirical duplication sensitivity from it.

**H4: specialist identifiability.** Use identical three-source rank observations
(two identical majority sources, one specialist) and identical confidence values
in two worlds: relevant documents match either majority or specialist. Score
ordinary RRF, the exact-duplicate quotient, and historical v2.1. The point is the
information boundary: no deterministic method receiving the same observations
can infer which unobserved truth changed. This is a constructive counterexample,
not a novel theorem or a broad impossibility result for informative score/label
or source-provenance features. Name additional evidence needed for a future test.

## Decision and stopping rules

### Claude design review before execution

A Fable5.1 coordinator completed four Opus5 scout branches. Adopted query-level
aggregation, explicit full moment ordering, displacement as well as relevance,
and the full-coverage duplication counterexample. The two-world fixture remains
a short explanatory boundary check, not the main empirical discovery. Next,
test tail support and equalized-depth effects in a separately recorded extension.

The coordinator did not establish all of its suggestions. In particular,
selecting the same k in every training fold does **not** turn valid CV into
full-data selection; its leakage claim is rejected. The coverage-dominance bound
is a sufficient worst-case bound, not a necessary condition for a given input.
No post-hoc 0.020 significance/stopping threshold is adopted. Claude's source
review lacked web tools, so its remembered literature stays unverified until
Codex retrieves primary sources. These disagreements are part of the review,
not grounds for treating model consensus as truth.

Do not promote v8 from a positive development comparison. If convention repair
removes the signal, explain it. If the signal persists, identify whether it is
configuration-specific and what untouched test would be worth running next.
If changing k leaves duplicate sensitivity substantial, retire “k independently
corrects source dependence” as an explanation; test actual source dependence
with a distinct mechanism. A quotient's algebraic invariance is useful but
insufficient for learned/near-duplicate dependence handling.

After results, obtain independent criticism and revise PHASE_SPACE. Continue
with a second small discriminating test if the first reveals a concrete ambiguity
that can be resolved with available inputs. Stop this autonomous run when there
is a coherent reviewed findings artifact and a better specified next frontier,
not merely because scripts ran or a model agreed.
