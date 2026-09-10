# Cycle03 review integration and branch decision

The same Claude session resumed with one Fable5.1 coordinator and one Opus5
statistics scout. Native events confirm both model identities. The coordinator
emitted a substantive review memo, then the invocation ended with
`error_max_budget_usd`, `is_error=true`, exit1, after103.6 seconds. Native
list-price accounting was$4.0096155 against a$4 cap; this is not subscription
billing. There is no successful result or `turn.completed` event for this phase.

The memo was recovered from an assistant text block, with its hash and terminal
status preserved in the [receipt](../evidence/2026-09-10-cycle03-review-receipt.json).
Request21 carried `cycle03-review-149dae43df`, returned from Relay context.
After reading the complete request and recovered memo, Codex recorded Claude's
requested ACK on the exact native session. That ACK means consumption, not
successful native completion. No additional provider run was launched.

The scout read the implementation and test names, taking the contract from its
coordinator rather than reading the protocol itself. Fable reported reading
the protocol, summary, and independent reconstruction. The scout's model-ID
visibility caveat in the prose does not override observed native model metadata.

## Accepted findings

- No consequential implementation discrepancy was found. The independent
  reconstruction agrees on groups, eligibility, exact endpoints, draw hashes,
  bootstrap quantiles, classifications, and branch decision. The scout's static
  reading likewise found no unjudged-as-observed-zero error or secondary-outcome
  path into the primary decision. Synthetic behavioral checks already pass.
- Both primary annual results fail the material-association gate and the narrow
  small-effect gate. Follow the frozen resource stop and draft R5. Neither a
  negligible effect nor a fusion improvement is established.
- State that the secondary threshold is descriptive. Its missing interpretation
  field is intentional; the report and figure say so explicitly.
- Separate generation provenance from specialist reliability in the next
  laboratory. Preserve cells where protecting a minority hurts, and expose the
  information unavailable to an aggregator.

## Corrections and limits

- The memo calls both primary point ranges nonnegative. The2019 sharp lower
  endpoint is actually−0.0013889; only2020's primary sharp interval is entirely
  positive. Preserve that narrow local observation without generalizing it.
- The change between grade≥2 and grade>0 does not identify composition as the
  explanation. They are different outcomes, and no composition intervention or
  model comparison was performed. It is a sensitivity observation, not evidence
  favoring a particular causal mechanism.
- The bootstrap envelopes are wider than the empirical missing-label intervals,
  but this is not a formal variance decomposition. Describe the two uncertainty
  summaries separately rather than attributing a precise share to sampling.
- The proposed equality between a provenance-aware quotient and an output-copy
  quotient is not universal: distinct independent sources can produce identical
  rankings. Collapsing by output may then discard independent corroboration.
- An inverse-lineage heuristic losing while an oracle wins would not prove that
  dependence must be estimated from outputs. The heuristic may simply use the
  available provenance poorly, or the oracle may have additional reliability
  information. Comparator information must be explicit.

## Next design selected

Claude proposed a ranking simulation with shared noise and a two-level specialist
accuracy manipulation, preceded by a small exact toy. A separate Codex design
worker proposed a smaller binary-evidence fixture with exact enumeration and an
optimal provenance-blind Bayes baseline. We select the smaller fixture first:
it makes information access, dependence, reliability, and comparator strength
fully inspectable without another Monte Carlo grid or NDCG threshold.

The [cycle04 design](2026-09-10-cycle04-known-truth-design.md) incorporates the
useful ingredients from both critiques: copied versus fresh corroboration,
strong versus weak specialists, fixed primitive evidence for copy interventions,
losses as well as rescues, and known limitations. It includes an optimal blind
baseline so a favorable result cannot rest solely on defeating naive voting.
Trusted lineage and known reliability are explicit idealized resources supplied
fairly to comparators; provenance labels do not encode truth.

No cycle04 experiment or real-LLM benchmark was run in this cycle. Its purpose
is to validate a laboratory and clarify what information a future method would
need, not to claim novelty or turn a constructed Bayes advantage into a discovery.

The independent design worker read the integrated cycle04 draft and found no
consequential contract defect. It added two useful clarifications: define the
correction-minus-harm sign relative to the named baseline, and note that optimal
blind Bayes already follows the strong specialist in the specified disagreement
pattern. A protected-minority policy there changes confidence, not classification
relative to that baseline. Both points are incorporated without running the toy.
