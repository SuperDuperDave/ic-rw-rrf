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

Model roles
follow expected information value; four scouts are not a quota for every loop.
The [research report](../results/cycle01-2026-09-10/REPORT.md) records the outcome
and the next checkpoint.

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
