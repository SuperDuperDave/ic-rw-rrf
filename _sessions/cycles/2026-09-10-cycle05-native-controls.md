# Cycle05 native Claude control audit

Read-only preflight on 2026-09-10; **no model request, provider launch, auth
inspection, credential extraction, or global configuration change**. The only
Claude processes run were `claude --version` and `claude --help`. Bounded worker
scope: this note; no journal, backlog, Git mutation, or scientific outcome.

The installed client can request a 500-token output cap with adaptive Opus5 and
retain signed-in authentication while excluding ordinary automatic context.
It **cannot establish one provider request per CLI invocation** with the controls
found in this audit. Native output-limit continuation is a material obstacle,
in addition to transport retries. These findings motivated the prospectively
frozen [execution amendment](2026-09-10-cycle05-execution-protocol.md), which
measures the fixed native workflow, retains its observable same-model
continuations/recovery, parses only its terminal result, and imposes independent
wall and cumulative-accounting bounds. The original strict single-pass contract
was not implementable with the inspected controls; the amendment changes the
measurement target before outcomes rather than claiming those controls exist.

## Audited executable and evidence method

- Launcher: `/home/david-wsl/.local/bin/claude`.
- Resolved executable: `/home/david-wsl/.local/share/claude/versions/2.1.267`.
- Version: `2.1.267 (Claude Code)`; size: 217,013,744 bytes.
- SHA256: `0399c793ff571d5946ef923d80b4f330d05ac4b6842a6b0775468f5d389403c0`.
- Local evidence below uses zero-based byte offsets into that executable's
  embedded JavaScript. Names are minified and are evidence for this build only.
  The executable was read as data, never altered or extracted for execution.
- Official documentation was checked on the audit date; links below identify
  primary sources. No claim below is a measured live-provider result.

## Recommended invocation shape

Construct argv directly, without a shell. The system text and stdin must be the
frozen experiment strings; identifiers below are placeholders, not literal
prompt text. Use a fresh empty temporary directory for each invocation, outside
the repository. Keep the existing HOME/auth configuration location unchanged.

```python
argv = [
    "/home/david-wsl/.local/bin/claude",
    "--print",
    "--safe-mode",
    "--setting-sources", "",
    "--settings", '{"disableAllHooks":true,"autoMemoryEnabled":false}',
    "--tools", "",
    "--strict-mcp-config",
    "--mcp-config", '{"mcpServers":{}}',
    "--disable-slash-commands",
    "--no-chrome",
    "--permission-mode", "dontAsk",
    "--permission-prompts", "none",
    "--no-session-persistence",
    "--model", "claude-opus-5",
    "--effort", "high",
    "--max-turns", "1",
    "--max-budget-usd", str(remaining_native_accounting_allowance),
    "--system-prompt", frozen_system_text,
    "--output-format", "stream-json",
    "--verbose",
    "--include-partial-messages",
    "--include-hook-events",
    "--prompt-suggestions", "false",
]
# subprocess: input=frozen_payload_text, cwd=fresh_empty_directory,
#             env=controlled_child_environment
```

Suggested child-environment overrides (not global shell changes):

```python
overrides = {
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "500",
    "CLAUDE_CODE_EFFORT_LEVEL": "high",
    "CLAUDE_CODE_MAX_RETRIES": "0",
    "CLAUDE_CODE_RETRY_WATCHDOG": "0",
    "CLAUDE_CODE_NO_MODEL_FALLBACK": "1",
    "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "CLAUDE_CODE_DISABLE_FAST_MODE": "1",
    "CLAUDE_CODE_DISABLE_WORKFLOWS": "1",
    "CLAUDE_CODE_AUTO_CONNECT_IDE": "0",
    "DISABLE_AUTO_COMPACT": "1",
}
```

`CLAUDE_CODE_NO_MODEL_FALLBACK` and
`CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK` are supported by the inspected local
implementation but were not located in the published environment reference.
They are build-specific controls, not a portable API promise. The former has a
tripwire and collapses the availability chain to the primary at byte181315455;
the refusal path also checks it at byte185555661. It is stronger than merely
omitting `--fallback-model`.

Avoid inherited behavioral overrides: in particular `MAX_THINKING_TOKENS`,
`CLAUDE_CODE_SIMPLE`, thinking-disabling variables, extra request bodies/betas,
provider switches, fallback settings, background/team settings, and remote/SDK
session identifiers. Preserve necessary native-auth infrastructure; do not read
or log secret values. An API-key or custom-provider override must not silently
replace the intended signed-in account. The runner should fail a preflight that
cannot establish its intended configuration, rather than improvise authentication.

Do not pass `--bare`: installed help explicitly makes it API-key/helper-only
for Anthropic access and excludes OAuth. Do not pass resume/continue, agents,
plugin directories, extra directories, context files, or `--json-schema`.
Structured-output validation has a separate retry mechanism; strict local
parsing of the model's text follows the experimental design.

## Isolation: supported guarantees and boundaries

Installed help documents safe mode, and the published
[CLI reference](https://code.claude.com/docs/en/cli-reference) confirms that it
retains authentication while suppressing ordinary customizations. `--tools ""`
removes the built-in tool surface. A custom system prompt replaces the default
prompt. No persistence and no resume keep these as fresh conversational contexts.

Safe mode includes automatic CLAUDE.md, skills, plugins, MCP, custom agents,
workflows and auto-memory suppression. Startup sets
`CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` at byte193108539. Keep a fresh temporary cwd
anyway: it makes the filesystem configuration explicit and keeps research
answers out of ordinary discovery. Use the Claude executable directly, not this
repository's Relay launcher, whose task is to add hooks and project context.

Managed policy remains active. The local hook resolver at byte182150819 returns
policy hooks in safe mode; an invocation-level `disableAllHooks:true` does not
override them. Thus zero hooks is conditional on absence of policy hooks.
Existence checks found none of `/etc/claude-code/managed-settings.json`,
`/etc/claude-code/managed-settings.d`, or `/etc/claude-code/managed-mcp.json`.
That does not establish absence of server/host-delivered policy. No account
configuration or cached policy was read. The
[settings documentation](https://code.claude.com/docs/en/settings) explains
managed sources and precedence; do not bypass an organization policy.

Custom prompt replacement does not imply that the provider sees exactly the
stdin and system strings with zero native/provider overhead. Native metadata,
authentication-related system identity and provider thinking instructions can
remain. This audit establishes controls over project/context discovery, not a
captured complete wire payload. Session non-persistence also does not promise
zero incidental native cache/auth/log filesystem activity.

## Output and cost semantics

Local evidence establishes that 500 is accepted by the request builder:

| Byte offset | Observed implementation consequence |
| --- | --- |
| 184467077 | `hre` rejects nonpositive/invalid values and clamps an excessive value to the upper limit; it has no positive lower clamp. |
| 188803579 | `jUe` resolves `CLAUDE_CODE_MAX_OUTPUT_TOKENS` through that validator. |
| 188732587 | The request output maximum is the minimum of that limit and any request override. Adaptive thinking sends `type:adaptive`. |
| 188733011 | The 1,024-token lower floor applies to legacy manual `budget_tokens`, not the adaptive total output cap. |
| 188736745 | The computed value is assigned to request `max_tokens`. |

Therefore do not turn on legacy fixed thinking or claim that Opus5 requires a
1,025-token total cap based on the legacy floor. API acceptance of this exact
live request has not been tested. A native canary, if used, must be the first
frozen observation and remain in the dataset, including any failure.

The provider's [thinking cost controls](https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost#cost-control)
define `max_tokens` as the combined thinking/text ceiling for **one request**.
Effort is behavioral guidance. The same page describes output reasoning details
and warns that visible summarized thinking differs from billed thinking.
Consequently 500 is not a per-invocation cap when native continuation occurs.

Native budget checking compares accumulated cost with the supplied dollar limit
(`EV`, byte185448837) while consuming yielded events (byte192902879). A request
can already have incurred cost before the stop condition is reached. Pass the
remaining batch allowance, subtract observed native cost after each invocation,
stop scheduling at exhaustion, and preserve overshoot. A $4 native-accounting
ceiling is neither a preauthorized billing reservation nor a subscription invoice.

## Native repetition: confirmed limitations

**No supported no-streaming execution option was found.** The CLI's output
format controls serialization, not provider streaming. The internal nonstreaming
request function `Fkr` has call sites in streaming-fallback paths at bytes
188787296 and188790762. Neither the full CLI flag table, official CLI reference,
nor the inspected environment names exposed an initial nonstreaming switch.
No auth change, proxy, patched client or alternate API route was attempted.

`CLAUDE_CODE_MAX_RETRIES=0` is accepted by `fdt` at byte186387735, but this controls
only the retry paths that consult it. The following are independent:

| Mechanism | Local evidence | Consequence |
| --- | --- | --- |
| Output-limit continuation | `hgr=3` at188194986; branch at188244567 onward | Up to three continuation attempts after `max_tokens`; a continuation prompt or incomplete thinking is reused. |
| Truncated-response recovery |188245500 onward | Shares the output recovery counter, behind a feature condition. |
| Thinking-only final response |188247772 | One nudge can request a visible answer. |
| Thinking-only connection recovery | `sm=2` at188738316; branch188779620 | May retry streaming twice without consulting configured retry count. |
| Stream idle recovery | `DA=1` at188738337; branch188784050 | May retry once even with configured retries zero. |
| Dispatch-header transport recovery |188782708 onward | Can retry after removing a native dispatch header. |

The output-limit and thinking-only branches preserve `turnCount:Cr`; the
`--max-turns` checks occur elsewhere. **`--max-turns 1` does not disable these
same-turn continuations.** No native flag/environment control disabling those
branches was found. Nonstreaming-fallback suppression is checked after some
streaming-recovery branches, so it does not remove them.

For a prospective amendment, distinguish **at most20 fresh CLI invocations,
zero application retries/replacements**, from a hard20-wire-request limit.
The unamended strict no-retries design is not fully enforceable by these native
controls. Automatic continuation can also change the per-packet prompt/context,
so it is not merely a transport accounting footnote. The
[prospective amendment](2026-09-10-cycle05-execution-protocol.md) now retains
valid terminal native-workflow responses while recording their continuations
and changed resource use; continuation alone is not grounds for selecting an
observation away. Its explicit configuration, error, cost and wall-time stopping
rules govern collection.
Killing on a marker can reduce further activity but is race-prone and cannot
retroactively guarantee that no next request was dispatched.

## What to observe without credential-bearing debug logs

Use standard stream-json output, keeping its raw content private:

- `system/init`: requested/resolved model information, tool and MCP lists,
  advertised skills/agents/plugins when present. Reject unexpected active tools,
  MCP or integrations. Distinguish advertised built-in agent names from an actual
  subagent invocation; the tool surface is the critical execution control.
- `system/status` with `status:"requesting"`: emitted for each high-level query
  iteration by the mapping at byte192898443. A second occurrence is evidence of
  additional work. It is not an exact wire-attempt count because transport
  retries happen inside an iteration.
- `stream_event/message_start`: track distinct native message IDs and model IDs.
  Multiple `assistant` records can describe different blocks of one message;
  do not equate their raw count with separate model requests.
- `stream_event/message_delta`: preserve stop reason and final usage, including
  `output_tokens_details.thinking_tokens` when present. `max_tokens` is a direct
  continuation-risk signal. Preserve all message usage and deduplicate by ID;
  usage deltas are cumulative values, not token increments to blindly sum.
- `system/api_retry`: positive evidence of a retry; the native schema at
  byte181463857 includes attempt, maximum, delay and error status. Some recovery
  paths do not emit this frame, so its absence is not proof of no retries.
- Model-fallback events, hook lifecycle frames, tool-use blocks,
  `parent_tool_use_id`, and subagent statistics: reject unexpected activity.
  `--include-hook-events` improves coverage, but not every hook lifecycle emits
  every kind of event.
- Final `result`: subtype, error state, exit status, stop reason, session ID,
  cost, total usage, per-model usage and `num_turns`. Do not use `num_turns` as a
  wire-attempt count. Missing/invalid accounting or an interrupted invocation
  requires an explicit incomplete-cost outcome and no next scheduling decision
  based on an invented zero cost.

The final `result.result` is not a concatenation of every response. At
byte192896497 the engine assigns the latest assistant record's last content
block text to its result accumulator (`kL` is the array-last helper at
byte179751006), applying native marker stripping; it resets that accumulator
on user/tombstone events. The final success result uses the accumulator at
byte192903499. Freeze strict parsing of `result.result` alone if measuring the
exported native workflow, and preserve prior response fragments only as
evidence. A continuation returning merely the tail of JSON may therefore fail
strict parsing. Manually joining fragments would introduce an extra response
repair rule absent from the design.

Apply finite per-invocation and total-batch wall deadlines independently of
native turn/recovery counters. Those bounds stop a stalled process or scheduling
loop but do not prove a provider request has ceased billing at the instant of
local termination.

The usage aggregator at byte185454887 accumulates per-model `thinkingTokens`
from reasoning detail, substituting zero when detail is absent; retain the
availability distinction. It also assigns `modelUsage[model].maxOutputTokens`
from `z9(model).default`, **not the effective environment cap**. That metadata
field cannot verify or falsify the configured500 cap by itself.

### Selected model and canonical identity

`system/init.model` is the current or resolved initial session-model string,
not an independently canonicalized provider response. The init builder at
byte192873692 emits `model:w.model` directly. The engine supplies its current or
initial model at byte192891442; the initial-model resolver at byte192933335
uses the session's main-loop model. Therefore init is evidence of runtime
selection; actual message models and terminal usage remain necessary.

The narrow native spelling set supported for this first-party Opus5 run is
`claude-opus-5` and `claude-opus-5[1m]`. The embedded catalog at byte180744313
defines the first-party identifier as `claude-opus-5` and declares native1M and
1M-suffix support; local code also explicitly recognizes the suffixed spelling
at byte185553977. Existing project cycle04 receipts observed the suffixed usage
key. Do not accept arbitrary aliases, provider-prefixed names, dates or strings
merely because they contain `claude-opus-5`.

The terminal usage entry's `canonicalModel` means the normalized identity used
for pricing (schema at byte181357922), populated from `Be(rawModelString)` at
byte185454597. Its `provider` records the provider category. Check the exact
canonical ID `claude-opus-5` and `firstParty` provider when supplied; retain both
raw and canonical fields. Canonical pricing metadata is useful corroboration,
not a substitute for native message identity. The native canonicalizer itself
has a broad substring fallback at byte181316152; reproducing that fallback
would make an experiment's acceptance rule unnecessarily permissive.

## Friction disposition

**PROMOTE:** native output continuation and partial retry observability belong
in the frozen execution contract and result limitations, with this note as the
durable implementation evidence. A runner that stops on detected recovery is
a control, not evidence that all recovery is detectable or prevented.

**SUBTRACT:** use direct isolated safe-mode invocations for these observations;
avoid Relay/research-agent context and legacy thinking-budget arguments. These
are control recommendations; this audit did not execute or measure their impact.

**DROP:** treating `--max-turns 1`, `--max-budget-usd`, or native
`modelUsage.maxOutputTokens` as proof of a strict one-request/500-token/invoice
bound. No changes outside this evidence note were made.
