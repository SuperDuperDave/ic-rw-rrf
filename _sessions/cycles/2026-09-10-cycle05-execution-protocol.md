# Cycle05 execution contract — native coordinator workflow

Frozen before any empirical request. Supplements the [prospective design](2026-09-10-cycle05-coordinator-packet-design.md), SHA256 `ebb5a3298cd3a8aa88a4b759af6a380e598c43d8f94e24da6f7359dfc8cfe6ca`.
Local research date 2026-09-10; execution may be 2026-09-11 UTC.

## Hypothesis and intervention

H7 asks whether a coordinator uses an explicitly supplied calibration and copy
model. The distinguishing prediction is lower posterior approximation error with
the correct root partition, copy invariance for known copied readings, and the
correct reversal between copied and independent strong-specialist conflicts.
The baseline for each view is its own exact Bayes posterior; the paired comparison
uses the same diagnostic worlds, with awareness as the only payload difference.
No truth, target posterior, arm name, acquired count, or evaluation metadata enters
the provider payload. Twenty canonical payloads, prompt, seed42 order, reference
posteriors and exact conditional weights are frozen in a separate prepared
manifest before collection. All 72 selected cycle04 world/arm rows remain the
reference; copied and independent blind inputs share one response.

## Prospective amendment after native-control inspection

The [native control audit](2026-09-10-cycle05-native-controls.md) found that the
installed client can continue a truncated answer or recover transport failures
within one turn despite `--max-turns 1` and its supported retry switches. We
therefore measure a **fixed native coordinator workflow**, not one model forward
pass. The design's twenty-request limit means **at most twenty unique native
invocations**. It does not bound wire requests to twenty. Zero coordinator retries,
replacements, prompt edits, model switches or budget increases are allowed.
Native continuations/recovery are part of the treatment and are recorded when
observable, not selected away. The same native policy applies to both views.
No single-pass, equal-compute, or complete transport-observability claim follows.

Only the unique successful terminal `result.result` is parsed. Earlier assistant
fragments are never selected or stitched. The client exports the last assistant
text block; a resumed JSON tail can therefore be invalid even when an earlier
fragment looked useful. This is a workflow outcome, not evidence of absent
mathematical capability. No preliminary model smoke test is allowed: the first
frozen packet is also the canary and remains an observation.

## Frozen model, context and resource controls

- Native executable `/home/david-wsl/.local/share/claude/versions/2.1.267`, SHA256
  `0399c793ff571d5946ef923d80b4f330d05ac4b6842a6b0775468f5d389403c0`.
- Exact model `claude-opus-5`; high effort in both CLI and process environment.
  No model fallback. No aliases, additional agents, retrieval or proposer calls.
- Fresh empty temporary working directory and random session UUID per invocation;
  stdin is the exact frozen JSON payload and system prompt is the frozen literal.
  Safe mode, empty setting sources, disabled hooks/auto-memory, empty tools/MCP,
  disabled slash commands/browser/prompt suggestions and no session persistence.
  Native authentication is retained; no credentials are read or changed.
  Ordinary project context is suppressed. Native/provider instruction overhead
  and managed policy remain possible; this is not a claim of exact wire prompts.
- `CLAUDE_CODE_MAX_OUTPUT_TOKENS=500` is per API response, including reasoning.
  It is not a 500-token invocation cap. Record native aggregate output and each
  observed message's final cumulative usage. Missing reasoning or message usage
  remains unavailable; do not replace it with zero. The model profile's
  `maxOutputTokens` is not the effective ceiling. Observed per-message output
  above500 is a configuration failure, when that measurement is available.
- Environment overrides: `CLAUDE_CODE_EFFORT_LEVEL=high`,
  `CLAUDE_CODE_MAX_RETRIES=0`, `CLAUDE_CODE_RETRY_WATCHDOG=0`,
  `CLAUDE_CODE_NO_MODEL_FALLBACK=1`,
  `CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1`,
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`,
  `CLAUDE_CODE_DISABLE_FAST_MODE=1`, `CLAUDE_CODE_DISABLE_WORKFLOWS=1`,
  `CLAUDE_CODE_AUTO_CONNECT_IDE=0`, `DISABLE_AUTO_COMPACT=1`.
  Reject inherited provider/Claude behavioral overrides before launch rather
  than silently changing authentication/provider routing. Preserve normal HOME.
- Sequential collection: one invocation in flight, maximum120 seconds each and
  900 seconds total batch wall time. A call gets the lesser remaining deadline.
  On timeout, terminate/reap only the owned process group and stop the batch.
- $4 cumulative native-accounting scheduling allowance. Each invocation gets the
  remaining allowance as native `--max-budget-usd`; stop scheduling at exhaustion.
  The guard is checked after costs accrue: a last-call overshoot is possible.
  This is neither a billing guarantee nor a measure of subscription credits.

The runner records the exact argv template/environment, binary and source
identities in a start manifest. Raw stream JSON and stderr stay ignored under
`_sessions/local/cycle05/`; durable records carry hashes, structured metadata,
valid scalar predictions and failure codes. Never expose private thought text.
Use stream JSON with partial messages and hook events for observation. Count
distinct message IDs, not content blocks; merge cumulative usage by ID, do not
sum repeated cumulative snapshots. Record requesting statuses, stop reasons,
retry/fallback markers, observed canonical models, final native result, cost,
usage, turns and session. These counters do not expose every transport attempt.

## Acceptance, stopping and scoring

Require one runtime init with the requested canonical model and no enabled tools
or MCP servers, no actual hook/tool/subagent activity or alternate model, exit0,
one result with subtype success, `is_error=false`, terminal stop `end_turn`, and
a finite nonnegative native cost. Advertised built-in agent names alone do not
prove agent execution. Native same-model continuations/retries are recorded and
allowed. Configuration failures, unknown cost, native error, missing terminal
result or timeout stop the whole batch and preserve its prefix. No failing call
is retried. Result JSON failure alone continues the frozen order if the native
execution is otherwise acceptable and budgets remain.

Strictly parse exactly one JSON object with exactly `p_positive`, a finite JSON
number in [0,1]. Reject booleans, strings, duplicate/extra keys, fences, prose,
NaN, infinities and partial JSON. Never repair, coerce, select fragments or impute.
Custody failures (changed sources, mismatched payload/hash/order) invalidate the
collection and prevent scoring as the frozen run.

Primary is conditional excess Brier `(p-q)^2` against each view's own exact
posterior, normalized by the exact selected generator mass separately at each
specialist reliability. Full primary requires all20 valid predictions. Also
compute paired expected Brier and its ideal-information/approximation-error
decomposition, posterior errors, decisions, sign symmetry and copy contrasts.
An incomplete run has coverage/failure metadata and, if available, explicitly
descriptive valid-subset scores with changed mass/count denominators. A partial
paired subset can change the blind posterior by selecting hidden lineage; retain
the resulting selection cross-term instead of assuming the full-set decomposition.
No p-values, confidence intervals or independent-sample claim from these packets.

Stop after this one batch, scoring and independent review. Native formatting or
budget failures support workflow findings only. Any later replication, larger
output ceiling or prompt change requires its own prospectively frozen design.
