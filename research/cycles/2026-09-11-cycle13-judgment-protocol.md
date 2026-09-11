# Cycle13: where another judgment can change a fusion comparison

## Question and prediction

Disagreement can identify a useful question without telling us which source is
right. For one fixed retrieval comparison, how much uncertainty remains under
all completions of missing relevance grades, and which judgments most reduce it?

Prediction: for a linear metric and equal exact-label costs, the absolute
difference between a document's two rank weights gives its guaranteed reduction
in interval width. Ranking those values is optimal for this width objective.
The unknown empirical quantity is how much useful remaining uncertainty this
fixed pair actually has, and how its acquisition priorities compare with pooled
head and uniform judging. Neither the theorem nor its implementation is a novelty
claim. No new relevance labels, model answers or dataset are acquired in this audit.

## Fixed inputs and comparison

Use both2019 and2020, the43/54 common queries in the existing run files. Require
all five source query sets to agree and match these counts; fail rather than
silently drop queries. Include every query, including zero-width/tied cases.
Qrel absence means unknown, explicit grade0 means known. No positive-grade
eligibility filter, subgroup search, bootstrap or seed sweep.

- A: canonical RRF k60, equal weights, the existing bm25, bm25_tuned, tfidf and
  ql_dirichlet files in that order under `data/trec-dl-<year>/runs/`.
- B: the same four plus `data/cycle02/acquired/dl<year>.trec` (SPLADE++).
- Preserve each complete retained source list, verify lexical depth30 and
  SPLADE depth1000, and use cycle02's strict serialized readers (origins0/1).
  `fusion_contract.canonical_rrf` uses one-based contributions and computed
  float score ties by ascending string document ID. Do not replace this with
  a rational-fusion ordering. Exact rational arithmetic below concerns metric
  weights and bounds, not the upstream floating fusion score.
- Qrels: original `data/trec-dl-<year>/<year>qrels-pass.txt`, strict grades0..3
  via the existing cycle03 reader. Gain is grade/3, fixed before the audit.

The systems have different candidate support and retained depth by design.
This is the applied pair being evaluated, not an isolated causal test of adding
expertise or a repetition of cycle03's specialist association.

## Metric and exact bounds

Metric: top10 RBP contribution, persistence p=4/5,
`S(R)=sum((1-p)*p**(r-1)*gain(doc), r=1..10)`. Weight is zero below10;
there is no tail inference or normalization. It is neither full RBP nor the
historical nDCG measure. Equal-query annual mean is the finite-panel aggregate.

Let U be the union of the two top10 lists. Combine identity before computing
`a[d]=w_B[d]-w_A[d]`. One query-document pair has one gain in both rankings.
Let C=sum(a[d]*grade[d]/3) for known grades. For unknown grades, endpoints0/3
remain possible independently of other documents. Therefore the sharp interval
for B−A is `[C+sum(min(a,0)), C+sum(max(a,0))]` over unknowns. Its width W is
sum(abs(a)). Endpoint assignments attain both bounds. Same-position shared
documents have zero coefficient, even if their relevance is unknown.

An exact new label for d removes abs(a[d]) from width, independent of its value.
An exchange argument gives the optimal equal-cost b-label set: b largest
absolute coefficients. This does not optimize expected sign resolution,
annotation error, unequal costs, multiple comparison objectives or generalization.
A current strict sign certificate requires lower>0 or upper<0; [0,0] is a tie,
and a bound touching zero without being [0,0] is unresolved.

## Acquisition comparison and reporting

Eligible pool: every unjudged document in U, including zero coefficients.
Each policy receives the same pool, grades already known, ranks and unit costs.
Budgets per query are exactly0,1,3; realized b=min(budget,pool size).
This is a per-query allocation constraint. It does not claim an optimal use of
a global annual labeling budget; that would compare coefficients across queries.

1. Absolute influence: sort by descending abs(a), then ascending string docid.
2. Pooled head: ascending minimum rank in A/B (absent rank infinity), then docid.
3. Uniform without replacement: expected residual width `W*(m-b)/m` for pool
   size m>0, zero for m=0. Analytic expectation, no sampled runs.

Report source hashes; all query IDs/top10s; known/unknown counts and coefficients;
current lower/upper/width; current sign/tie/unresolved status; selected docids
and projected widths at0/1/3; annual means and counts.
Also report influence/head selected-set equality and intersection counts, with
nonempty-pool counts so trivial equality of empty selections is visible.
A projected width after
new labels is not a projected center/sign: those values remain unknown.
No policy consumes new labels, so these are acquisition plans, not measured
labeling outcomes or new relevance scores. Include ties and zero-width cases.

## Validation and stopping

Before the actual run, test small permutations and all completions of missing
grades to establish sharpness; enumerate budget subsets to check optimal width;
check shared-document cancellation, explicit zero versus absent, swapping A/B,
and input rejection. Freeze this protocol, implementation and source identities
after independent/Claude design review. Run the fixed audit once; independent
reconstruction then verifies outputs and arithmetic without importing its scorer.

Stop after that evidence map, regardless of result. Do not change metric,
cutoff, pair, budgets or cohort to create headroom. A useful map may motivate a
separately justified label-acquisition decision; it does not schedule one.
Old arithmetic and association stops remain in force.

## Position relative to prior work

Selective judging for system comparison is established in
[Carterette, Allan and Sitaraman (SIGIR2006)](https://ciir.cs.umass.edu/pubfiles/ir-475.pdf).
Bounds using partial judgments and metric-dependent rank differences are central
to [Tan and Clarke's MED work](https://arxiv.org/abs/1408.3587), including linear
measures. Our signed interval and width objective must not be conflated with the
absolute MED value `max(abs(lower),abs(upper))`. This local application adds a
project-specific evidence map, not a claimed new acquisition algorithm.
