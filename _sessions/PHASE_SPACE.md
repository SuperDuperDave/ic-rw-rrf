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

## Current hypotheses

| ID | Hypothesis / status | Next discriminating observation |
| --- | --- | --- |
| H1 | `[observed, narrow]` n6 gain survives; 2019 aggregate remains uncertain and both n4 annual transfers lose | Park further existing-panel tuning; untouched diverse inputs would test transfer |
| H2 | `[supported in scope]` Depth changes the k effect; smoothing does not provide clone invariance | Separate lost candidates from changed support before attributing the gain to tail corroboration; equal-depth arm had no treatment |
| H3 | `[structural]` Exact-source-copy invariance is a useful diagnostic, not a quality guarantee | Distinguish actual copies from independent sources with similar outputs using provenance/controlled dependence |
| H4 | `[inconclusive under fixed gate]` Cycle03 bounds the SPLADE relevance association; both annual query envelopes remain broad | Stop this panel’s association search. Use the exact known-truth fixture to specify what information could distinguish useful dissent from noise |
| H5 | `[verified in stipulated model]` Trusted lineage improves probability quality; stronger information need not change class decisions | Cycle04 gives a weak-setting Brier-only benefit and a strong-setting error gain; H7 now measures actual use under supplied assumptions |
| H6 | `[derived boundary; run retired]` Correct copy lineage and individual calibration need not justify independent likelihood factors | Common-cause proposal is arithmetically contained in old mixture; retain the distinction, require real joint-error evidence for transfer |
| H7 | `[observed, narrow]` Actual Opus5 uses the fully supplied calibration/lineage model on the fixed diagnostic | Twenty valid fresh responses, all reference decisions, max probability error3.37e-8; source detection and general ability remain open |
| H8 | `[partial, incomplete]` Three returned probabilities track noise-aware inference; full eight-input primary unavailable | One weak hint contrast observed; strong independent-hint cases unsent after refusal; park further supplied tables |
| H9 | `[observed, gate failed]` This small program panel exposed no differing or shared errors | Both roles correct on all8items; park exact configuration, reserve unsent; no general independence/accuracy claim |
| H10 | `[observed locally; provider batch parked]` All four pairs change final state and pass the local gate, but an always-false policy mimics a 4/4→2/4 accuracy decline | Preserve the panel; no model difficulty/error claim. Certificate content offers a more direct evidence question |
| H11 | `[observed, narrow]` Both actual maps reject invalid traces, including one with the correct endpoint; all6 judgments correct | One all-zero program, V-first: first-original-only also perfect. No strategy or causal-copy inference |
| H12 | `[observed, narrow]` All18 returned judgments match exact verification and differ from all named fixed-position/endpoint policies | Close this two-endpoint diagnostic; no unique internal method, general ability or multiagent advantage identified |
| H13 | `[observed, narrow; lab parked]` All4 answers and16 validity judgments are correct under valid-minority/majority copied support | Prespecified stop met; no internal evidence-use, copying-effect or multiagent claim |
| H14 | `[open, gated]` Selecting a missing record may add information that repeated agreement cannot supply | Consolidate first; one auditable applied case and equal-access/budget single-system comparator before any batch |

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

- **Cycle02 observation:** SPLADE top10 is mostly judged, with19/22 queries
  judged in both specialist groups. The source's isolation is exactly absence
  from the retained lexical union; equal depths do not separate access/support.
  More observation reveals a definitional coupling, not just a label shortage.
- **Cycle02 critique:** retain one descriptive association measurement before
  changing laboratories. Correct missing-label bounds and define an explicit
  resource threshold. [Cycle03](cycles/2026-09-10-cycle03-specialist-association-protocol.md)
  uses20/23 candidate-paired queries and can end inconclusively; H5 remains the
  alternate branch. Neither a judged document nor an association is a proven
  useful specialist.

- **Cycle03 outcome:** both primary associations are inconclusive under the fixed
  resource gate. A positive finite2020 interval coexists with a wide conditional
  query envelope; no null or stable material association is established.
- **Cycle03 branch:** follow the promised stop and prepare the exact known-truth
  fixture. Separate truthful lineage from known reliability and from useful
  observations. Strong blind comparators and actual acquisition counts prevent
  a toy from appearing successful merely by giving one policy extra information
  without disclosing it. [Cycle04 design](cycles/2026-09-10-cycle04-known-truth-design.md).

- **Cycle04 measurement:** all six cells independently reconstruct. Probability
  quality improves with trusted lineage even when final answers do not change.
  Strong-setting error falls 15%→14.05% against optimal blind Bayes; weak minority
  protection raises error 27.2%→36.85%. Copy invariance is a structural check,
  not a quality guarantee. [Report](../results/cycle04-2026-09-10/REPORT.md).
- **Cycle04 review transition:** distinguish copy lineage, error dependence
  and calibration, but retire the common-cause numerical run because its law
  repeats the existing non-null mixture. A derived conceptual boundary needs
  no new arithmetic. Select the actual coordinator packet test, whose output
  is unknown. Correct a shared reviewer overreach: below the prior threshold,
  the classification benefit moves to copied packets; it does not vanish.

- **Cycle05 measurement:** native control inspection refined the treatment to a
  fixed workflow with possible continuations. A zero-counter detector fault
  stopped the initial canary; its frozen outcome remains. A separately frozen
  replication produced20valid near-exact posteriors with no observed extra
  messages/agents. Raw and arithmetic reconstruction agree. Supplied-model
  calculation is saturated at observed output precision; add uncertainty about
  evidence quality before scaling the number of agents.
- **Cycle05 critique:** Fable selected known-noise lineage. Specify a binary
  copied/independent hint channel rather than an ambiguous three-class flip;
  reduce its proposed sweep to eight inputs and remove arbitrary thresholds.
  Correct class-only intuition: exact blind already shares the correct noisy
  strong-setting decision, so probabilities must reveal whether the hint is
  used. [Cycle06 design](cycles/2026-09-10-cycle06-known-noise-design.md).

- **Cycle06 partial measurement:** three near-reference probabilities include
  one continuous hint contrast; provider refusal stops the fixed batch before
  the strong distinguishing cells. Full primary remains null. Independent raw
  review corrects fallback/model labels and message attribution without changing
  frozen evidence or accepting the refusal.
- **Cycle06 review transition:** move from supplied error laws toward observing
  actual paired errors. Do not assume fresh contexts imply independent errors,
  confuse an exposed answer with a deterministic copy, or infer dependence causes
  from a tiny truth-conditioned association. [Cycle07 design](cycles/2026-09-10-cycle07-observation-design.md)
  starts with truth and denominator feasibility. H8 stays incomplete, not settled.

- **Cycle07 measurement:** both prompt roles return all correct answers on eight
  independently verified programs. Complete primary, failed variation gate;
  the16reserveitems stay unused. A clean collection can still fail to supply
  the observable needed for the next causal or correction question.
- **Cycle07 review transition:** inspect a loop-bound manipulation locally before
  another provider wave. Distinguish execution length from reasoning difficulty,
  nesting from iteration count, and observed tokens from causal compute benefit.
  Correct the capsule's example count using unchanged source evidence.

- **Cycle08 local measurement:** four candidates produce eight verified programs;
  the committed gate passes. The truth imbalance admits an always-false reference
  policy with a short/long accuracy decline. Distinct end states and two Boolean
  flips are local effects of N; they do not establish harder reasoning.
- **Cycle08 review transition:** park the provider batch despite the passed gate
  and move to certificate-content verification. Preserve independent criticism
  of unsupported chance/novelty claims and a cheaper-than-replay gate. One fresh
  short construction can separate a correct answer from valid support without
  inducing spontaneous solver errors. [Cycle09 design](cycles/2026-09-10-cycle09-certificate-design.md).

- **Cycle09 measurement:** local761checks validate one all-zero program and the
  row3/correct-endpoint negative control. A separately frozen two-call pilot
  returns6/6correct with unchanged base/repeat maps. Always-invalid/endpoint-only
  score2/3, but first-original-only is perfect. Native feasibility is observed;
  checking strategy and repetition causation remain unresolved.
- **Cycle09 transition:** balance position and endpoint alternatives explicitly
  rather than search for a harder-looking random draw. A small prospective local
  policy panel can clarify what a later success would exclude. Preserve the
  exact original result and the distinction between output-policy discrimination
  and a unique internal mechanism. [Cycle10 design](cycles/2026-09-11-cycle10-discriminating-design.md).

- **Cycle10 measurement:** all18 judgments from six fresh contexts match exact
  verification, with eight mismatches against each fixed-position vector and
  six against endpoint agreement. Close this finite diagnostic. Neither outputs
  nor token counts show interior recomputation or a unique checking method.
- **Cycle10 review transition:** take one final bridge from classifying support
  to choosing an answer. Explicitly cross truth and which root has three
  submission instances; copying does not create independent acquisitions.
  The task needs a new answer-plus-validity schema. A perfect single-verifier
  result parks multiagent work in this laboratory; preserve any counterexample
  without an automatic repair wave. [Cycle11 design](cycles/2026-09-11-cycle11-evidence-selection-design.md).

- **Cycle11 measurement:**4/4answers and16/16validities correct in four fixed
  packets. Accepted-support endpoints match answers; copies receive consistent
  judgments. Independent raw/score audit agrees. Direct solving remains an
  alternative mechanism; repeated roots are not independent tasks.
- **Cycle11 transition:** honor the promised park of this arithmetic laboratory.
  Consolidate before another experiment. Missing evidence, rather than another
  presentation of sufficient evidence, is a possible new axis; it requires an
  applied local feasibility gate and an equally informed single-system baseline.
