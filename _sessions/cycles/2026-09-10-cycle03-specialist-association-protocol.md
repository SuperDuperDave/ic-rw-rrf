# Cycle03 — a bounded specialist relevance association

Prospective protocol prepared after cycle02's observation inventory, before
inspecting relevance grades or calculating effects for this source/cohort.
No cycle03 dataset analysis has run. These annual panels were previously used
for development; prospective choices do not make them untouched test data.

## Question and fixed scope

For a SPLADE-owned specialist, does observed lexical tail support mark a
different relevance rate from absence in the recorded lexical union? This is a
descriptive association. It cannot separate corroboration from candidate access,
source language overlap, owner-rank composition, or the judgment process. It
does not establish a useful routing feature beyond existing RRF coverage credit.

Inputs: cycle02's pinned source/derived manifest, the four lexical lists and
original graded qrels, and its full-arm specialist cohort. Use the full-arm
candidate IDs and group labels from the frozen observation artifacts; verify
them against the input hashes. No source search, threshold search, truncation,
new cohort, fusion rule, or learned selection belongs in this phase.

The unit is a query. Analyze years separately, never pool documents as independent
observations. Include every query with at least one candidate in each group:
20 of 43 in 2019 and 23 of 54 in 2020. Eligibility uses candidates, not judgment
presence or relevance. Report the excluded query IDs and retain the all-query
inventory for context. This estimates the eligible-query contrast, not the
average over every benchmark query or every SPLADE result.

## Estimand and missing labels

Primary binary outcome: qrel grade at least2. Secondary descriptive sensitivity:
grade greater than 0. There is one primary contrast and no choice between outcomes
after seeing them. Grades are integers; reject an unexpected value outside 0–3
rather than silently interpreting it. Explicit0 remains known nonrelevant for
both thresholds. Unjudged stays unknown and never enters as an observed0.

For query `q` and group `g` (supported `S` or isolated `I`), define:

- `n_qg`: all fixed candidate members, judged or not.
- `r_qg`: judged members meeting the fixed relevance threshold.
- `u_qg`: unjudged members.
- `L_qg = r_qg / n_qg`; `U_qg = (r_qg + u_qg) / n_qg`.

The finite-panel contrast is the equal-query average of
`mean(Y_qS) − mean(Y_qI)` over eligible queries. Without assumptions about
missing labels, its sharp endpoints are:

`lower = mean_q(L_qS − U_qI)`

`upper = mean_q(U_qS − L_qI)`.

Do not divide pooled counts or assign both groups' missing outcomes the same
value. Each specialist has a unique owner and group; assignments can attain
these endpoints jointly. Preserve per-query counts/endpoints and list the
assumptions. The endpoints quantify missing-label uncertainty on this panel;
they are distinct from sampling uncertainty or evidence about other datasets.
Report this empirical sharp interval alongside the bootstrap envelope below.
Check the invariant `upper−lower = mean_q(u_qS/n_qS + u_qI/n_qI)`; its width
depends only on missing-label membership.

## Precision, decision threshold, and selection budget

Research decision threshold `delta = 0.10` absolute relevance-rate difference.
A ten-percentage-point equal-query gap is the chosen minimum association worth
spending another fusion-design cycle on. This is an explicit project resource
choice, not an RRF-derived probability, a universal useful-effect threshold,
or a predicted NDCG improvement. Freeze it before this contrast is calculated.

Conditional sampling summary: within each year resample eligible queries as
whole paired records with replacement, `B=10,000`, `random.Random(42)` initialized
separately for each year. Sort query IDs lexicographically as strings. With
`n` eligible queries, draw `[rng.randrange(n) for _ in range(n)]` once for each
of the 10,000 replicates, in replicate order. Reuse exactly these indices for
both endpoints and both relevance thresholds. Record Python version and the
index-draw hash. For every resample compute both bound endpoints.
Use linearly interpolated empirical quantiles at 0.025 and 0.975: sorted position
`(B−1)p`. Report the interval from the 2.5th percentile of lower endpoints to
the 97.5th percentile of upper endpoints as an **exploratory bootstrap uncertainty
envelope**. Preserve both endpoint distributions' quantiles. This conditional
bootstrap assumes exchangeable query sampling and does not repair prior search,
nonrandom judgments, or small-panel coverage limitations. Do not claim exact
95% coverage, a calibrated p-value, or confirmatory cross-domain evidence.

Primary interpretation, evaluated separately by year:

- Material positive/negative association: entire envelope above `+delta` or
  below `−delta`, respectively.
- Small under the chosen bound: entire envelope inside `[−delta,+delta]` **and**
  total envelope width at most 0.10. An interval crossing zero is insufficient.
- Otherwise inconclusive for the current decision threshold/precision target.

Advance to a distinct fusion-contribution protocol only if both years show
material association in the same direction. Neither a secondary outcome nor a
favorable subset can override this gate. Any future performance comparison must
include SPLADE alone and ordinary RRF with SPLADE, and distinguish candidate
access from aggregation. An association itself is not a fusion improvement.

If the primary result is inconclusive, inconsistent across years, or small under
the chosen bound, stop this branch without another source/threshold sweep and
draft the controlled known-truth evidence task in R5. This is a resource stop,
not proof that the idea cannot work. It may be revisited with a genuinely new
observation plan. Secondary grade>0 results are descriptive only; no additional
owner-rank strata or alternative inference methods will be searched this cycle.

## Implementation and checkpoint

Before reading actual grades, implement and test the endpoint arithmetic on
synthetic cases: both groups entirely missing gives[−1,+1]; no missing labels
collapses the bounds; opposite missing assignments attain extrema; equal-query
averaging differs from pooled-document weighting; candidate-only eligibility
retains a query with a fully unjudged group; bootstrap paired resampling preserves
group coupling. Tiny exhaustive missing-label assignments can independently
verify sharpness. Validate the relevance threshold and grade contract.

Use a fresh immutable results directory, exact commands/environment, fixed seed,
input/code/protocol hashes before and after, and query-level outputs. No new
provider fan-out is needed before implementation; one independent results audit
and a bounded Claude interpretation are sufficient if they can change a decision.
Stop at the recorded interpretation and next branch choice, update the research
map, commit and push. Do not silently continue into a fusion or agent experiment.
