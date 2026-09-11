# Cycle09 empirical candidate — one verifier, two sealed packets

**Candidate only; no provider launch or case generation under this document.**
Depends on every gate in [the local design](2026-09-10-cycle09-certificate-design.md)
passing, independent verification, and a separate execution freeze/source seal.
No local failure may be repaired by inspecting model answers or replacing cases.

## Recommendation before outcomes

Recommend the bounded two-call measurement after those prerequisites: whether an
actual solver accepts V and rejects I/F is unknown, and I's correct final answer
makes this a content-validity question beyond the earlier supplied probability
tables. This is one single-verifier feasibility observation, not an aggregation
comparison or a cost-benefit result. Stop after the fixed measurement regardless
of success; neither perfection nor errors authorize another task/prompt sweep.
Root may instead stop at the local fixture without leaving an empirical claim.

## Inputs, order and one prompt

Use only the two accepted canonical packet files, base first and repeat second.
Do not regenerate parameters, IDs, payloads or order. Seal exact input bytes,
their hashes, reference validity mapping, checker/code identities and the final
rendered prompts before either call. Private V/I/F labels and expected decisions
stay in evaluation artifacts; providers receive only the following fixed
instruction plus one canonical packet. No known-valid count or reliability table
is supplied. The packet already contains the exact original_ids to judge.

```text
For each report ID in original_ids, decide whether its certificate is a valid
execution of program. Each numbered row must record the complete state after
that assignment, including unchanged variables and their exact types. Check
from the initial assignments through the final Boolean assignment. Agreement
with the final answer alone is insufficient. root_id identifies copies of an
artifact; it does not certify correctness or independent errors. Return exactly
one JSON object with only the IDs in original_ids as keys and Boolean values:
true means the certificate is valid, false means it is invalid. Return no other
text. Evaluate this packet:
```

Append one newline and the unchanged canonical packet, retaining its terminal
newline. The separate execution freeze must seal these complete prompt bytes.
Use separate fresh contexts with no previous answer, project/Relay instructions,
tools, MCP, subagents, examples or hidden reference output in experimental inputs.

## Candidate controls and strict acceptance

Candidate settings are exact model `claude-opus-5`, high effort, 500 output tokens
per API response including reported thinking, $1 native-accounting scheduling
allowance, 120 seconds per invocation and 300 seconds for the two-call batch.
Recheck identity, availability, native controls, costs and observer behavior
before freezing execution. The response cap is not an aggregate invocation cap;
continuations are part of an invocation. A scheduling allowance is not an invoice
cap. Record realized calls/messages/tokens/costs and unobservable fields; meeting
these limits is not a scientific success criterion or evidence of efficiency.

Accept a response only if native/custody checks pass and its complete terminal
text parses as one JSON object, allowing surrounding whitespace only. Require
exactly the sealed original-ID key set, no duplicate keys, and actual JSON Boolean
values. Reject extra/missing keys, numeric substitutes, fences and other text.
An invalid map yields no accepted decisions; preserve raw output without partial
salvage. Wrong but well-formed validity judgments remain scientific observations.
Stop scheduling at the first native, format, custody or resource failure,
unexpected identity/activity, or unavailable cost observation. No retries,
fallbacks, replacement calls, prompt changes or parameter searches are allowed.

## Frozen measurements and limits

Preserve all six planned `(packet, original_id)` records, expected validity,
returned Boolean when accepted, correctness, and accepted/invalid/unsent status.
Report correct/accepted/planned decisions for each packet and overall, alongside
attempted/accepted/planned invocation counts. The complete primary needs both
accepted maps; otherwise keep it absent and label any partial counts explicitly.
Never impute invalid or unsent decisions as wrong certificate judgments.

With two accepted maps, report each original's exact base-to-repeat decision and
correctness transition, including unchanged-correct and unchanged-wrong cases.
These are three repeated certificate judgments on one program, not six independent
task samples. Always-valid gets 1/3 and always-invalid 2/3 per packet; checking
only agreement with the true final answer also gets 2/3 by wrongly accepting I.
Report those descriptive reference scores, with no chance model or significance.

Full correctness would establish six correct decisions, including rejection of
I despite its correct final answer, and observed invariance on these originals.
It would not identify internal checking strategy, general accuracy, independence,
novelty, or collaboration benefit. Only invalid F is copied: rejecting repeated
roots can identify it without content checking. Repeats also add text; fixed call
order, stochastic responses and text length prevent an isolated copying-effect
claim. Any later multiagent comparison needs its own matched single-verifier
baseline and evidence/compute contract; this candidate contains none.
