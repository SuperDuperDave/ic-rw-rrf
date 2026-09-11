# Cycle13: the annual comparison is settled before buying another judgment

Adding the existing SPLADE++ source to four-source k60 RRF improves the annual
mean **under this fixed top10 diagnostic metric**, even under the worst allowed
completion of missing relevance grades. Both panels have strictly positive
lower bounds. Further judgments are unnecessary to determine that annual direction.

The result is not uniform across queries:65 favor adding SPLADE,9 favor the
four-source fusion,5 are exact ties and18 remain unresolved. This is a conditional
finite-panel finding, not a general superiority or safe-per-query routing claim.
The underlying query records and inputs are heavily reused development material.

## What was compared

A uses the retained bm25, bm25_tuned, tfidf and ql_dirichlet lists; B adds the
previously acquired SPLADE++ list. Both use the canonical floating k60 RRF contract
with one-based contributions and document-ID score ties. All43/54 queries are
retained. Lexical lists are mostly200 documents with four shorter query lists
per source across the years; SPLADE lists have1000. Candidate access and depth
are part of this applied comparison, not isolated causes.

The metric is the **unnormalized top10 RBP contribution**, persistence4/5 and
gain=grade/3. Weight is zero below10; short rankings use only their actual
positions. It is neither full RBP nor the previous nDCG metric. Known grades are
held fixed; missing grades range independently over0..3, with each query-document
sharing one grade across A and B. These are sharp logical bounds, not confidence
intervals over future queries or uncertain assessors.

| Panel | Queries | Exact-bound lower, B−A | Exact-bound upper, B−A | B / A / tie / unresolved queries |
| --- | ---: | ---: | ---: | --- |
| 2019 | 43 | +0.041061 | +0.096263 | 27 / 3 / 2 / 11 |
| 2020 | 54 | +0.037144 | +0.067333 | 38 / 6 / 3 / 7 |

Displayed endpoints are rounded; [full results](corrected/summary.json) retain
exact rational values. In particular, positive annual means do not eliminate
the nine per-query reversals. No selection rule was fitted to those cases.

## Where another judgment would reduce uncertainty

For a shared document, subtract its two metric weights first. If the resulting
coefficient is a, revealing its exact grade removes |a| from interval width,
regardless of that grade. Equal-cost, per-query width is therefore minimized by
selecting the largest |a| values. This is a strong simple baseline, not a new
algorithm or a guarantee of sign resolution.

The top10 unions contain65 unjudged query-document pairs in2019 and39 in2020.
Of these,3 and2 have zero coefficients: their unknown grades cancel in the
comparison. There are25 and17 queries with nonempty judgment pools.

| Panel | Budget per query | Projected total labels | Width: largest influence | Width: pooled head | Expected width: uniform |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2019 | 0 | 0 | 0.055202 | 0.055202 | 0.055202 |
| 2019 | 1 | 25 | 0.026663 | 0.028868 | 0.032470 |
| 2019 | 3 | 49 | 0.008420 | 0.009636 | 0.012639 |
| 2020 | 0 | 0 | 0.030190 | 0.030190 | 0.030190 |
| 2020 | 1 | 17 | 0.012713 | 0.014761 | 0.016831 |
| 2020 | 3 | 33 | 0.002928 | 0.003231 | 0.004997 |

Widths are annual equal-query means. Each policy has the same unjudged pool and
unit costs; budgets are capped by pool size. Uniform is an analytic expectation
without replacement. These are **projected widths after exact labels**, not
observed labeling outcomes, future interval centers or measured annotation costs.
No labels were acquired. Per-query allocation is not globally optimal allocation
of one annual budget.

At budget1, influence and pooled-head select the same document in20/25 nonempty
pools in2019 and10/17 in2020. At budget3, selected sets coincide in20/25 and16/17.
The additional18/37 empty-pool agreements are excluded from these denominators.
Influence improves the projected width here, but cannot improve the already
settled answer to the annual-sign question. A narrower interval needs its own
decision purpose before spending on labels.

## Failure, correction and independent checks

The first actual attempt stopped before any fusion or bound calculation. The
coordinator had incorrectly described retained lexical depth as30; the code
enforced that mistaken contract. The failed attempt, original protocol/code/tests
and preflight are preserved. A [separate correction](../../_sessions/cycles/2026-09-11-cycle13-retained-input-correction.md)
uses exact retained-input metadata, already present in cycle02, and validates
all12 files and both years' lengths before scoring. No outcome informed the
correction, and no list or query was removed.

All183 research tests pass, including4,500 exhaustive synthetic bound cases and
five new adapter tests. The standard-library demo exits0. The
[independent audit](../../_sessions/evidence/2026-09-11-cycle13-independent-check.json)
reconstructs485 source/query lists,194 fused rankings, all97 query records and291
budget plans from raw files without importing the new producer/scorer. Both
annual summaries, exact artifact bytes and input/source identities match.
The corrected local analysis took0.382749seconds by its recorded timer.

Reproduce into a fresh directory:

```bash
python3 -B evaluation/cycle13_retained_inputs.py --output /tmp/ic-rrf-cycle13-replay
python3 -B -m unittest discover -s evaluation/tests
```

One Fable5.1/high design review completed at$0.4884975 native list accounting;
it reviewed the proposed direction, not these later results. Its assumptions
about directional missing-label bias were qualified before execution. See
[integration](../../_sessions/cycles/2026-09-11-cycle13-design-integration.md).
Dave's expanded sharing authorization was accepted for that unpublished handoff.
Request70 was consumed/ACK74; no collaborator remains active.

## What changes in the research direction

Disagreement can tell us where a judgment matters without telling us which
source is right. Selective judging is established in
[Carterette, Allan and Sitaraman](https://ciir.cs.umass.edu/pubfiles/ir-475.pdf);
metric-dependent bounds with partial judgments are established in
[Tan and Clarke's MED work](https://arxiv.org/abs/1408.3587). The new contribution
here is the concrete, verified evidence map for this project's fixed pair.

Close this audit without acquiring grades merely to narrow an interval. The
current annual direction is already determined, while per-query reversals rule
out a uniform-benefit reading. A useful next step is a prospective transfer
design on one collection not previously analyzed in this project, with fixed
ranker/candidate semantics and explicit original-metric evaluation. Establish
input feasibility and freeze choices before inspecting its scores; do not tune
a router on these nine reversals or advertise this diagnostic as an nDCG gain.
