# Public-source research-design review

Review only the two already-published project excerpts below. Their complete
source files were fetched without authentication from the stated immutable
GitHub URLs and matched their local committed SHA256 values. No unpublished
inventory, local cache analysis or private transcript is supplied. Tools, MCP
and scouts are disabled. This is a compact Opus5/high conceptual review, not a
solver experiment. Target 300 words. Return the marker supplied through Relay
and request Codex's consumption ACK for the actual request.

The research question is how to choose a useful applied evidence-acquisition
study after a single verifier solved a small arithmetic panel. Please challenge
the published local gate: must an alternative acquisition policy already be
shown to differ before any empirical feasibility test is worthwhile? Distinguish
case validity, a useful comparison and demonstrated model failure. Consider the
published native-label correction as an illustration of existing evidence
reconciliation, without treating its solved history as unseen model evidence.
Recommend at most one concrete next design action or a meaningful pause. Do not
suggest a search whose stopping rule is finding baseline failures. No new
empirical launch follows from this review. Preserve finite-result and strategy
limits; stronger tiers and scouts are choices, not quotas.


Published source: https://raw.githubusercontent.com/SuperDuperDave/ic-rw-rrf/5b49a464cda025e193c90ea1fb765b1b785a6121/docs/RESEARCH_SYNTHESIS.md

# What this research has clarified

The original question was whether agreement among imperfect sources could help
without suppressing a useful independent minority. It remains a worthwhile
question. The experiments have clarified several different problems hidden
inside that sentence; none has produced a broadly superior successor to RRF.

## Agreement is an observation, not a correctness label

The early adaptive-fusion gain depended on a particular ranker configuration.
Broader comparisons and annual transfer did not establish general superiority.
The canonical rerun retained a narrow six-ranker improvement while exposing
limitations in selection and transfer. More agreement can change an ordering;
it does not by itself explain why the new ordering is better.
[Cycle01 evidence](../results/cycle01-2026-09-10/REPORT.md)

Likewise, “specialist” needs an observable definition. In the later retrieval
panel, isolated neural results were also absent from the retained lexical
candidate union. Sparse pooled judgments and that coupling limited what could
be concluded about useful dissent. The fixed association test remained
inconclusive under its stopping rule.
[Cycle02 observation audit](../results/cycle02-2026-09-10/REPORT.md),
[cycle03 association test](../results/cycle03-2026-09-10/REPORT.md)

## Copying, dependence and reliability are different facts

Repeating a source can amplify its influence without acquiring new information.
Exact-copy invariance is therefore a useful structural diagnostic. It is not
a guarantee of good answers: minority protection can also favor a bad source.
Controlled known-truth calculations showed both a benefit from trusted lineage
and a setting where the protected-minority policy increased error. Distinct
source identities do not establish independent errors; individual calibration
does not specify the full joint error law.
[Cycle04 controlled evidence](../results/cycle04-2026-09-10/REPORT.md)

When the inference law and needed evidence were supplied, one actual coordinator
already reproduced the diagnostic probabilities closely. That established a
bounded ability to use the supplied model, not an ability to discover source
reliability or independence. A subsequent noisy-hint batch stopped incomplete;
its unsent cases remain unsent.
[Cycle05 observations](../results/cycle05-replication-2026-09-10/REPORT.md),
[cycle06 incomplete result](../results/cycle06-2026-09-10/REPORT.md)

## A strong baseline can close a proposed agent experiment

The small program pilot exposed no errors for another stage to correct. Local
difficulty controls then revealed a simple answer-policy confound, so that
provider batch was parked. Certificate experiments gave a more direct way to
ask whether returned evidence judgments were correct, including an invalid
trace with a correct final answer. Later position/endpoint controls separated
the observed output vector from named shortcuts.
[Cycle07](../results/cycle07-2026-09-10/REPORT.md),
[cycle08](../results/cycle08-2026-09-10/REPORT.md),
[cycle09](../results/cycle09-2026-09-11/REPORT.md),
[cycle10](../results/cycle10-2026-09-11/REPORT.md)

The final bridge asked one verifier for both the answer and each submission's
validity under valid-minority and valid-majority copied support. It returned
all four answers and sixteen judgments correctly. We followed the promised
stop and parked multiagent work in that laboratory. Direct solving remains a
sufficient explanation of these outputs; neither strategy nor necessary use
of the certificates was identified. A successful baseline is a research result,
even when it removes the reason to build a more elaborate system.
[Cycle11 result](../results/cycle11-2026-09-11/REPORT.md)

## A possible next question concerns missing evidence

The completed arithmetic packets already contained enough information for one
solver. A different applied question is whether a system chooses a decisive
missing record rather than acquiring another version of what it already knows.
That would expose an acquisition decision and its actual information contribution.
It is a proposal, not a demonstrated improvement or novelty claim.

Before implementing it, identify one auditable applied case where the initial
evidence permits two materially different answers and an accessible record can
settle the distinction. Track source identity, duplicated content and cost.
Give a simple single-system comparator the same access, tools and total budget.
If an aggregation comparison follows, give both systems the same acquired
evidence. Unequal access can explain a gain without better collaboration.

If no such case can be established without another elaborate toy or labels that
reveal the answer, stop here. No new dataset, fixture, provider batch or budget
has been scheduled. The next local gate lives in [PLANNING](../_sessions/PLANNING.md).
The current contribution is a clearer set of questions, reproducible finite
observations, and a record of which attractive explanations survived checking.


Published source: https://raw.githubusercontent.com/SuperDuperDave/ic-rw-rrf/5b49a464cda025e193c90ea1fb765b1b785a6121/results/cycle06-2026-09-10/REPORT.md

## Native failure and independent correction of its interpretation

Four invocations consumed57.71seconds and$0.173296 in native list accounting.
The raw streams contain10 provider message IDs and one locally generated API
error record. Aggregate output is4,386tokens, including4,328thinking tokens;
six provider messages stop at `max_tokens`. The500-token setting is per response,
not a500-token total workflow ceiling. Hidden transport attempts are not fully
observable. There is no evidence that truncation caused the subsequent refusal.

The failed invocation reports `model_refusal_no_fallback` with category
`reasoning_extraction`, exit1, `is_error:true` and terminal stop `refusal`.
The actual request asked for a JSON probability. The category records the
provider's classification; it does not establish a terms violation or explain
why this task was refused. No alternate provider model was observed.

The frozen collector misread “no_fallback” as fallback and treated a known local
`<synthetic>` API-error record as another provider model. That local record also
received cumulative usage/stop metadata belonging to the preceding real provider
message. The [independent audit](../../_sessions/evidence/2026-09-10-cycle06-independent-check.json)
preserves the exact discrepancies. Aggregate accounting, valid probabilities and
direct-loss arithmetic agree. The genuine native failure still requires exclusion;
the batch remains incomplete regardless of those misleading extra labels.

Original observations/scored artifacts remain unchanged. A separately tested
[future observer](../../_sessions/tools/native_stream_observer.py) recognizes
the precise correlated local error shape and records refusal separately from
model switching. Offline replay is distinct from a new native experiment; no
repair batch was launched. This correction does not prevent provider refusals.

