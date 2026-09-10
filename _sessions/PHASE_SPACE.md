# Phase-space map

Living hypothesis/design map, opened 2026-09-10. These are coordinates for
exploration, not claims that all useful methods fit the current taxonomy.

## Initial coordinates

| Axis | Current/nearby choices | What could distinguish them? |
| --- | --- | --- |
| Evidence source | Rank, score, relevance labels, source provenance, semantic representation | Does new information help under matched candidate/query conditions? |
| Observation | Fully known truth, pooled partial judgments, unjudged items, source-conditioned eligibility | Is the proposed contrast observable, and is the intervention nontrivial? |
| Independence | Equal ranker votes, exact-duplicate quotient, dependence-aware weighting | Does repeating one source change the result without new evidence? |
| Minority evidence | Suppress outliers, preserve specialists, route by confidence | Can the method distinguish a correct specialist from isolated noise? |
| Aggregation | Reciprocal kernel, exact alternating-moment limit, pairwise preference, learned selection | What ordering changes, and what information is lost? |
| Adaptation | Fixed, query-dependent, document-dependent, source-dependent, iterative feedback | Does adaptation improve held-out performance and remain stable? |
| Interaction | Parallel independent proposals, shared discussion, staged synthesis, adversarial review | On a defined task, does communication add information or synchronize errors? |
| Resource | Labels, computation, latency, model tier, number/depth of agents | Does additional cost buy a measurable reduction in uncertainty/error? |

Objectives include relevance, robustness to redundant/noisy inputs, transfer,
interpretability, and cost. An improvement on one axis may trade off another.

## Hypotheses after cycle01

| ID | Hypothesis / status | Next discriminating observation |
| --- | --- | --- |
| H1 | `[observed, narrow]` n6 gain survives; 2019 aggregate remains uncertain and both n4 annual transfers lose | Park further existing-panel tuning; untouched diverse inputs would test transfer |
| H2 | `[supported in scope]` Depth changes the k effect; smoothing does not provide clone invariance | Separate lost candidates from changed support before attributing the gain to tail corroboration; equal-depth arm had no treatment |
| H3 | `[structural]` Exact-source-copy invariance is a useful diagnostic, not a quality guarantee | Distinguish actual copies from independent sources with similar outputs using provenance/controlled dependence |
| H4 | `[open]` Agreement alone cannot identify correctness in rank-isomorphic worlds; real tail evidence is too sparsely judged | A feasible observation plan with known truth or sufficient group judgments must precede another specialist gate |
| H5 | `[open, broader branch]` Agent agreement may have a related dependence problem | Define an agent task, independent unit, matched resource budget, and correlated-error metric; retrieval results do not establish the analogy |

Evidence lives in the [cycle01 report](../results/cycle01-2026-09-10/REPORT.md).
Existing DL2019/2020 queries are heavily used development data. Cycle01 cannot
confer untouched generalization evidence on them. The bounded source check
found relevant prior work; it does not constitute novelty clearance.

## Transition log

- **Entry:** recovered original consensus + robust-specialist + anti-cabal intent;
  expand the immediate view beyond k tuning while retaining comparable metrics.
- **Design critique:** replace a two-term large-k proxy with the full moment
  order; add real depth and tail-support tests. Retain synthetic matched-input
  truth swaps only as an information-boundary illustration.
- **Measurements:** n6 signal persists, broad selection benefit does not settle;
  exact copying remains influential; top30 caps weaken the n6 effect.
- **Observation constraint:** list lengths already match within query; sparse,
  uneven judgments prevent a convincing specialist correctness comparison.
  Add an observation/eligibility axis before inventing another aggregation rule.
- **Results critique and checkpoint:** new source provenance may make dissent
  more informative, but neither neural evidence nor pooled judgments guarantee
  independence or correctness. [Cycle02](cycles/cycle02-source-feasibility.md)
  begins with access and observation feasibility. Existing-panel k sweeps are
  parked. A controlled agent-evidence branch remains separate and untested.
