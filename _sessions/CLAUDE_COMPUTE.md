# Claude model and orchestration policy

Verified 2026-09-10 against official documentation and local native Claude Code
2.1.267. The model contract below is supported by official documentation. The
actual research phases are separately evidenced by native runtime receipts.

## Observed use in cycle01

The first phase completed with one `claude-fable-5-1` coordinator and four native
`claude-opus-5` scouts. Native message/model-usage output confirms both IDs;
these are not identities inferred from a model's self-description. The phase
finished successfully in 358.4 seconds, with native list-price accounting
$2.97611925. This is not a subscription invoice or allowance conversion.
[Design receipt](evidence/2026-09-10-cycle01-design-receipt.json)

The second phase resumed that same native coordinator successfully, using one
Opus evidence scout and Fable synthesis of completed measurements. Both model
IDs were again observed. It took 324.9 seconds with $2.318103 native list-price
accounting; the two research phases total $5.29422225 on that basis.
[Results receipt](evidence/2026-09-10-cycle01-review-receipt.json)

Cycle02 resumed the same coordinator with one Opus scout and Fable synthesis.
Native output again confirms both IDs; the phase completed in 151.2 seconds,
with $3.7525075 native list-price accounting. This approached its $4 invocation
cap, largely through coordinator context/cache accounting; no additional review
wave was needed. Scientific recommendations were checked independently, and
missing-label bounds were corrected before adoption.
[Cycle02 receipt](evidence/2026-09-10-cycle02-review-receipt.json),
[integration](cycles/2026-09-10-cycle02-review-integration.md).

Cycle03 observed the same two model IDs and one scout, but the native phase
terminated with `error_max_budget_usd`, exit1, after103.6 seconds. It emitted a
substantive coordinator memo before termination; that text was recovered and
reviewed, while the terminal error remained explicit. Native list-price
accounting was$4.0096155 against a$4 cap, not subscription billing. No further
provider invocation was needed. A growing resumed context can consume much of
a small phase budget; inspect native usage before choosing the next invocation's
scope. Do not raise limits automatically or equate a readable memo with success.
[Cycle03 receipt](evidence/2026-09-10-cycle03-review-receipt.json),
[integration](cycles/2026-09-10-cycle03-review-integration.md).

Cycle04 used a fresh compact coordinator handoff after Dave reported allowance
reset. The $4 native invocation cap stayed unchanged. One Fable5.1 coordinator
and one canonical Opus5 scout completed successfully in370.6 seconds, with
$2.52308675 list-price accounting. The Opus usage key was `claude-opus-5[1m]`;
canonical identity and message output agree. The coordinator supplied an `opus`
override despite the pinned definition, so future missions should omit such
overrides or use the intended exact model when supported. Do not infer identity
from self-description. The final memo exceeded its advisory word target; native
turn/spend limits succeeded. Different scope/context means the cost comparison
with cycle03 is observational, not a measured general efficiency gain.
[Cycle04 receipt](evidence/2026-09-10-cycle04-review-receipt.json),
[integration](cycles/2026-09-10-cycle04-review-integration.md).

Cycle05 measured fixed `claude-opus-5` high on synthetic packets, separately from
research review. An initial native-success canary was rejected by a zero-counter
instrument fault and remained stopped. A separately frozen correction completed
20/20 fresh inputs in83.84s, native list accounting$.182899, with3,730 output tokens
including3,380 reported thinking tokens. No tools/agents/continuations were
observed; the largest per-message output was433. The stopped canary adds$.014545.
All21 raw streams and the probability scores were independently checked.
[Empirical report](../results/cycle05-replication-2026-09-10/REPORT.md).

The [native control audit](cycles/2026-09-10-cycle05-native-controls.md) found that
500 output tokens is a per-API-response ceiling including reasoning, and native
continuations/recovery can bypass turn/retry controls. Safe mode plus fresh empty
working directories kept ordinary project context out of those experimental
invocations. Runtime init, actual message models, activity and terminal results
are separate evidence. An all-zero subagent statistics object is not activity;
the corrected collector recognizes only its precise numeric-count schema.

A separate fresh Fable5.1 interpretation review used normal project Relay hooks,
no tools/subagents, and a$1 native cap. It succeeded in39.68s at$.313930 with
2,885 output tokens including1,612 thinking tokens; its557-word memo exceeded the
advisory500-word target. Model choice reserved Fable for interpretation, with
Opus as the empirical workhorse; no scout quota was needed. Total this cycle's
native accounting across the two empirical batches and review is$.511374,
not subscription billing. [Review receipt](evidence/2026-09-10-cycle05-review-receipt.json).
Cycle06 subsequently closed incomplete: four invocations, three valid, one
provider refusal, four unsent. Raw streams verify10 provider message IDs plus
one local API-error record;4,386 output tokens include4,328 thinking tokens.
Six message stops hit `max_tokens`; invocation outputs can exceed500 through
continuation. Empirical cost$.173296,57.71seconds. Do not infer that continuation
caused the refusal, or that the category establishes a task terms violation.

The preserved collector mislabels `model_refusal_no_fallback` and a correlated
local `<synthetic>` message, and misattributes two message fields. No actual
alternate model was observed. The future-only `native_stream_observer.py`
separates the exact verified local error shape and preserves refusal rejection;
unknown shapes retain conservative gates. It must be pinned in any future
execution contract, not substituted retroactively into frozen observations.
See [audit](evidence/2026-09-10-cycle06-independent-check.json).

One separate Fable5.1/high review succeeded in46.30seconds at$.30278075,
3,098output tokens including2,057thinking tokens; no tools/scouts. Its492-word
public memo exceeds the400-word advisory target. The terminal result contains
only its final ACK paragraph; the full public review is assembled from assistant
text blocks, excluding thinking. Total cycle06 native list accounting$.47607675;
no cap was raised after an error. [Receipt](evidence/2026-09-10-cycle06-review-receipt.json).
Cycle07 subsequently used the same verified Opus5/high controls for16 fresh
program/role requests. All16 were valid, with one provider message each and no
observed continuation/activity.3,079 output tokens include2,935 thinking tokens;
max322total permessage. Empirical native$.166275,48.34seconds. Both roles answered
all8items correctly, so the error-variation gate failed; no reserve calls followed.

One Fable5.1/high interpretation review completed in42.61seconds at$.21782825,
2,509output tokens including1,517thinking;450 public words versus400 advisory.
No tools or scouts were needed. The source-derived public memo extractor worked
on the actual invocation; no thought text is published. Total cycle07 native
accounting$.38410325. [Receipt](evidence/2026-09-10-cycle07-review-receipt.json).
Next work audits task observability locally. Short-task costs do not predict a
longer program's usage, and token counts do not identify reasoning strategy or
causal compute benefit. Any later provider batch needs its own effective-control
freeze; extra agents or stronger tiers remain choices, not quotas.


Cycle08 used no empirical solver calls. One compact Fable5.1/high interpretation
review completed in 31.35 seconds at $0.19646825 native list accounting, with
2,033 output tokens including 1,212 thinking tokens; no tools or scouts.
The 392-word public memo exceeded its 350-word advisory target. The review used
an artifact-derived numeric table and example, independently checked against
the sealed local panel. [Receipt](evidence/2026-09-10-cycle08-review-receipt.json).
The local gate passed, but a simple constant-answer reference exposes an
interpretation limit. We parked the arithmetic batch and selected a local
certificate-content audit. Any subsequent solver/comparison budget remains
unfrozen; computational resources are not needed to induce errors before that
construction can be checked.

Cycle09 used one Fable5.1/high decision review,35.93seconds,$.21040825,
2063output tokens including1250thinking, with no tools/scouts. Its392-word memo
exceeds350 advisory. Request50 was consumed/ACK54; final brief clear.
A separately sealed Opus5/high pilot used exactly2 isolated calls,6.01481seconds,
$.032690,296output tokens including194thinking,2messages with no continuation
or activity. All6 judgments are correct; a first-position reference also scores
perfectly. Total native accounting$.24309825 excludes Codex and subscription
billing. [Review receipt](evidence/2026-09-11-cycle09-review-receipt.json),
[empirical manifest](../results/cycle09-2026-09-11/observations/manifest.json).
The prospective cycle10 local panel has no provider budget yet; do not infer
its cost or value from these short calls.

Cycle10 reused Opus5/high for six fixed native calls:19.69405seconds,$.088035,
879output including561thinking tokens, six messages with no observed continuation
or activity; maximum152output/message. All18 returned judgments match exact
verification. The finite named heuristic vectors differ; no internal algorithm
or multiagent benefit follows.

One Fable5.1/high interpretation review completed in59.67seconds at$.43333375,
3,857output including2,565thinking tokens. Two message IDs appear; per-message
final usage and stop metadata are unavailable. The terminal field held only the
second public-text fragment; the existing extractor recovered the full596-word
memo without another call. The400-word advisory target was exceeded; the$1/180s
native bounds were respected. Total native cycle accounting$.52136875 excludes
Codex and subscription billing. [Receipt](evidence/2026-09-11-cycle10-review-receipt.json).
Cycle11 is only a prospective four-packet decision design; it needs a new task
instruction/parser and separate execution freeze. Do not assume its cost from
cycle10 or scale agents before observing a single-verifier gap.

Model roles
follow expected information value; four scouts are not a quota for every loop.
The [research report](../results/cycle01-2026-09-10/REPORT.md) records the outcome
and the next checkpoint.

Cycle11 completed four isolated Opus5/high calls:4/4 answers and16/16 validities
correct,697 output tokens including384 thinking, four messages with maximum195
per message and no observed continuation/activity. Empirical native accounting
$.069705 over13.25492seconds. The full-correct stopping rule parks multiagent work
in this arithmetic laboratory; no extra stage was launched.

One separate Fable5.1/high tools-disabled review succeeded in51.02861seconds at
$.48746175,3351 output tokens including2177 thinking, two observed message IDs.
Final per-message usage and stop telemetry remain unavailable; the3000 ceiling
is per API response. Its555 public words exceed450 advisory. Full public memo
extraction recovered both fragments without another call. Native total$.55716675
excludes Codex and subscription billing. Its token/strategy and recomputability
claims were corrected in [integration](cycles/2026-09-11-cycle11-review-integration.md);
strong-model interpretation remains evidence to check, not an authority to adopt.

## Select the requested models exactly

| Role / property | Fable 5.1 | Opus 5 |
| --- | --- | --- |
| Pinned Claude model ID | `claude-fable-5-1` | `claude-opus-5` |
| Standard API input / million tokens | $10 | $5 |
| Standard API output / million tokens | $50 | $25 |
| Cache read / million tokens | $0.25 | $0.50 |
| Context / maximum output | 1M / 128K | 1M / 128K |
| Documented relative latency | Slower | Moderate |

These are standard API prices, not a conversion of subscription allowances.
Cached input, cache writes, output, and thinking change actual spend.
[Fable specifications](https://platform.claude.com/docs/en/models/fable-5-1/overview),
[Opus specifications](https://platform.claude.com/docs/en/models/opus-5/overview).

Anthropic positions Fable 5.1 as its strongest widely released model and Opus 5
as the starting point for most workloads. Its guidance recommends increasing
Opus effort or moving to Fable when measured quality requires it. Fable should
not be treated as a cheaper exploration tier.
[Model-selection guidance](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model).

Use full IDs in `--model` and custom agent definitions. Aliases vary by provider,
environment overrides, and release: `fable` usually means 5.1 now, but the Claude
apps gateway can still resolve it to 5. Fable 5.1 needs client 2.1.257+; Opus 5
needs 2.1.219+. The inspected native binary meets both thresholds and contains
both exact IDs. Both models also responded successfully in this account's
cycle01 design phase; availability should be rechecked if later requests fail.
[Model configuration](https://code.claude.com/docs/en/model-config).

## First wave: one coordinator, bounded specialist work

Project recommendation: one Fable 5.1 coordinator at `high` effort, dispatching
up to four Opus 5 evidence scouts at `high`. Use separate scientific questions:
baseline/evaluation semantics, selection leakage, mechanism counterexamples,
and prior-work positioning. Every scout returns source references, a falsifier,
and a bounded proposed experiment. The coordinator compares disagreements and
selects the smallest discriminating experiment. A later Fable specialist is
justified by a specific unresolved hard question, not by a quota.

Keep first-wave scouts read-only, with explicit project paths and no overlapping
artifact ownership. The coordinating session owns synthesis and experimental
implementation. Do not launch neighboring projects or their agents. Native
permission rules and the existing task's authorization remain authoritative.

`--agents` accepts invocation-only JSON definitions. For example, construct this
object programmatically and pass `json.dumps(agents)` as one argv element:

```json
{
  "ic-evidence": {
    "description": "Check one assigned research claim against project evidence.",
    "prompt": "Stay within the assigned project question. Return evidence, uncertainties, and one falsifier. Do not edit files or delegate further.",
    "model": "claude-opus-5",
    "effort": "high",
    "tools": ["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
    "maxTurns": 12
  }
}
```

Use distinct scoped names if different scouts need different instructions. The
root invocation's tool set must also contain any tool a child is expected to
use. A child definition alone did not supply web access in the design phase.
The results-review phase instead advertises the actual read-only tools and
supplies primary-source checks performed by Codex.

The launcher shape is `python3 _sessions/tools/relay.py claude --model
claude-fable-5-1 --effort high --agents <JSON> --print <mission> --output-format
stream-json --verbose --max-turns <phase-bound>`. Assemble argv through a process
API; angle-bracket items above are placeholders. The project helper contributes
the Relay hook settings. No second `--settings` argument is needed.
`--max-budget-usd` additionally caps tracked API spend in print mode, including
subagents; use the task's authorized amount. Record partial/limit outcomes rather
than treating them as completion.
[CLI reference](https://code.claude.com/docs/en/cli-reference).

## Nesting, model precedence, and concurrency

Current subagents can nest: the default depth is three layers, not zero.
For a flat first wave set `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` in this
invocation's environment. Set `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=4` to bound
new Agent-tool starts. The default concurrency is 20; resumes, workflows, teams,
and ultracode have exceptions or separate limits, so also keep the planned wave
small. Scouts without the Agent tool cannot delegate.

Model precedence in 2.1.267 is per-call model, definition model, subagent default
environment variable, then parent model. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`
overrides this order. Neither override was found in inspected local settings or
the audit process environment. Managed model restrictions can substitute a
different model. Record actual model IDs from native output; prompts claiming
the requested name are insufficient. `maxTurns` limits each subagent, and a
limited result is partial. Forks inherit the parent's model, so use named,
non-fork specialists when mixed models matter.
[Subagent documentation](https://code.claude.com/docs/en/sub-agents).

## Workflows and teams are separate options

Dynamic workflows are available on paid plans and API providers; Pro requires
enabling the feature. `--effort ultracode` requests automated workflow planning
with `xhigh` reasoning. A literal ultracode keyword in a `-p` prompt does not
activate that shortcut. Workflow agents can select models per stage. Runtime
limits are up to 16 concurrent agents, CPU-dependent, and 1,000 total per run.
`workflowSizeGuideline=small` suggests fewer than five agents but is not a cap.
Workflow permission evaluation still applies. To keep the first wave on ordinary
subagents, `CLAUDE_CODE_DISABLE_WORKFLOWS=1` is an invocation-only option.
If later scale warrants workflows, first inspect the generated phase script and
its agent count, then run a small slice. Do not assume a four-subagent setting
caps workflow agents.
[Dynamic workflows](https://code.claude.com/docs/en/workflows).

Agent teams are experimental and add independent peer sessions. Teams cannot
nest; only their lead can create teammates. In-process teammates have resume
limitations and cannot run their own background subagents. Teams are unnecessary
for the proposed first wave. An ancestor repository settings file contains a
team-enable value; whether that file loads here must be determined from effective
native configuration, not its mere existence.
[Agent teams](https://code.claude.com/docs/en/agent-teams).

## Evidence and spending boundary

Use an explicit `--effort` so the inspected user's `xhigh` default does not
silently define this run. A launch flag does not persist the selection. Depending
on plan, Fable can draw usage credits; print mode does not show the interactive
credit-consent prompt. Preserve the user's existing spending authorization and
do not enable extra billing or bypass provider controls.
[Model and usage-credit behavior](https://code.claude.com/docs/en/model-config).

For every phase, keep the native session/agent IDs, requested and observed models,
tool results, token/cost fields when supplied, outcome, and artifact identities.
Keep raw provider transcripts private and ignored. Before a later wave, inspect
new information gained and remaining uncertainty; do not continue generating
agents after independent checks cease to change the decision. Existing signed-in
native access, Relay observation, successful model output, consumed handoff,
verified experiment, and research improvement are distinct evidence claims.
