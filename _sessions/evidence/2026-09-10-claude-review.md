# Bounded Claude review — 2026-09-10

## Scope and outcome

One real Claude Code session, launched through the project Relay helper after
Dave explicitly approved sending the prepared research audit/case-study packet.
Tools, MCP, optional setting sources, and session persistence were disabled for
this invocation. The process had a three minute limit and completed normally.
The helper/runtime generated invocation-only hooks; no global settings changed.

- Native process exit: **0**; result subtype: **success**; `is_error`: **false**.
- Claude identified the pending review request and returned an exact marker
  available only in the injected Relay context, not the supplied user prompt.
- Project ledger: request seq 1, matching native session startup/turn/end at
  seq 2–4; complete event contents inspected by the coordinator.
- Claude explicitly requested coordinator acknowledgement because tools were
  disabled. Codex recorded the exact delivery ACK at seq 5 after review; this
  was not a native Claude tool call. Final Claude brief: no pending signals,
  no active claims. Provider process ended.
- Exact packet and provider output remain under ignored `_sessions/local/`.
  Request artifact SHA-256:
  `41424a34b7c94cc734e0aad954666c0563c1d0fd050046159e89f5e6ca56c599`.

## Findings and disposition

1. **Show the adverse REF comparison.** Added DL2020 REF 0.4393 versus Vanilla
   0.4483 to the case-study draft beside the 2019 near-tie.
2. **Name the repeated pattern.** Added that the narrow k win resembles the
   earlier configuration-specific v5 signal; it needs untouched evaluation.
3. **Make fresh reproduction evidence explicit.** The initial audit worker had
   only checked baselines; the coordinator separately ran the full REF panel.
   Linked that raw output and clarified audit versus coordinator checks.
4. **Prioritize the larger statistical issues.** The plan now explicitly calls
   for a search-budget inventory and resampling whole queries while preserving
   their repeated ensemble measurements; normal-versus-t is not the only issue.
5. **Correct the reviewer too.** Claude correctly identified the baseline offset
   but suggested the wrong sign when translating tuned k. Algebra gives
   `k_canonical = k_local − 1`, since `k_local + idx = k_canonical + idx + 1`.
   We did not adopt its proposed `k+1` relabeling or use it to skip reconciliation.

The review considered supplied excerpts; it did not independently inspect or
execute the underlying code. This verifies model-visible Relay context and a
useful review response, not autonomous coding, wake/resume, or full recovery.
