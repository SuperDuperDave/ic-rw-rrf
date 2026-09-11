# Agent Relay in this project

## Current sharing authorization — 2026-09-11

After cycle12's inventory-transfer rejection, Dave explicitly stated: "I approve
sharing anything and everything with Claude." Unpublished project research,
inventories, code, findings and working context can be sent to the existing
signed-in Claude service through this Relay. Prior publication is not required.
Include this exact authorization and actual payload/destination when launching;
do not repeat the prior approval question. Cycle12's unsent/sent history remains
unchanged. The expanded consent does not require sending irrelevant context or
publishing private provider/runtime records to GitHub.

## Verified status — 2026-09-10

This repository is enrolled in the existing account-installed Relay development
release `0.1.0-dev-lichtenberg-20260910` (release ID
`751813b97e50176a714235ee77875872fefc2665924d7eb9193c701bc8c4ccff`).
`doctor` reports SQLite integrity `ok`, WAL mode, and schema version 2 for this
project's `.relay/relay.sqlite3`. It uses neither Ascend's ledger nor its receiver.

Enrollment created this project's `.relay/`, its `.git/relay-enrollment.json`,
and the required account enrollment record under the installed Relay data home.
No provider settings, global hooks, installed runtime, or sibling repository was
changed. `.relay/` and `_sessions/local/` are ignored; do not publish them.

The Claude invocation plan was generated and inspected. Following explicit user
approval, a real Claude Code session completed a bounded review of the prepared
audit and case-study draft. It returned the exact marker supplied only through
Relay hook context. Native JSON reported success, exit 0, and `is_error=false`;
the ledger records matching startup, turn-completed, and session-ended events.
The [review receipt](evidence/2026-09-10-claude-review.md) describes the scope.
The request was deliberately acknowledged after review.

The subsequent autonomous cycle verified a stronger collaboration path: one
native Fable5.1 coordinator dispatched four Opus5 scouts for design, then resumed
in the same session with one Opus5 scout for results critique. Both phases
completed successfully with observed native model IDs and distinct context-only
receipt markers. See the [design receipt](evidence/2026-09-10-cycle01-design-receipt.json),
[results receipt](evidence/2026-09-10-cycle01-review-receipt.json), and
[research report](../results/cycle01-2026-09-10/REPORT.md). Requests6 and11 were
consumed and acknowledged by the coordinator for the exact Claude session, as
the read-only provider phases had no shell tool. No pending signals or active
claims remain; no task-owned provider process remains running.

Cycle02 additionally resumed the same native coordinator for one Fable5.1/Opus5
observation review. Request16 returned its exact context marker; lifecycle
seq17–19 records successful startup/completion/end. After reading the complete
request and memo, Codex recorded Claude's requested ACK as seq20 on the exact
native session. The final brief is clear: no pending signals or active claims,
and the bounded provider process exited. [Cycle02 receipt](evidence/2026-09-10-cycle02-review-receipt.json).
This is another verified manual resume, not an automatic listener.

Cycle03 returned its new request21 context marker and a substantive memo, then
ended at the configured native budget limit. Seq22 records startup; seq23 records
session end; there is no `turn.completed` event. Codex recovered and read the
memo, then recorded the requested consumption ACK as seq24. The final Claude
brief has no pending signals or active claims, and the provider process exited.
[Qualified cycle03 receipt](evidence/2026-09-10-cycle03-review-receipt.json).
A consumed request with useful text is distinct from successful native execution.

Cycle04 used a fresh compact Claude session
`3aa95d47-60aa-4387-91a5-7020b8d04744`, with Fable5.1 coordination and one Opus5
scout. Native execution succeeded within its unchanged $4 cap. Request25's
context marker returned; seq26–28 record startup, turn-completed and end.
Codex read the full request/memo and recorded Claude's requested ACK29. The
final Claude brief is clear, with no pending signals or active claims. This is
an explicit bounded handoff, not an automatic listener. The retired common-cause
run and corrected reviewer prior argument are documented in the
[integration](cycles/2026-09-10-cycle04-review-integration.md) and
[receipt](evidence/2026-09-10-cycle04-review-receipt.json).

Cycle09's separate decision review used Fable5.1 session
`358e2b47-96e6-49a7-bc2b-73223e12437b`, tools and scouts disabled. Request50's
marker returned; lifecycle51–53 completed successfully. Codex read the full
request and public-text memo, corrected causal/resource/hash overclaims, and
recorded Claude's requested consumption ACK54. Final brief has no pending
signals or active claims. [Receipt](evidence/2026-09-11-cycle09-review-receipt.json).
Two later empirical contexts used no Relay hooks or review context. No task-owned
provider remains active; the original review is distinct from solver evidence.

Cycle10 review used Fable5.1 session`b3ae7c13-e503-4929-b029-8c51147aee30`.
Request55's marker returned; lifecycle56–58 completed. The complete public memo
was recovered from both assistant-text fragments; terminal result alone was
incomplete. Codex read the full request/memo, integrated corrections and recorded
Claude's requested consumption ACK59. Final brief is clear, with no task-owned
provider active. [Receipt](evidence/2026-09-11-cycle10-review-receipt.json).
The six empirical contexts had no Relay hooks or review context.

Cycle11 review used Fable5.1 session`7438a7f3-9964-407a-a02c-cb4444ba1245`.
Request60's marker returned; lifecycle61–63 completed. Codex read both public-text
fragments and the exact request, then recorded Claude's requested consumption
ACK64. Final brief is clear; no task-owned provider remains active. The four
empirical calls used isolated contexts without Relay hooks. [Receipt](evidence/2026-09-11-cycle11-review-receipt.json).

## Commands

Cycle05 kept experimental packet contexts separate from Relay hooks. Its
scientific interpretation review used a fresh tools-disabled Fable5.1 session
`7457bb97-1696-492d-84ef-a0aa97121b44` through the project helper. Request30's
context-only marker returned, events31–33 show successful startup/turn/end, and
Codex recorded the requested consumption ACK34 after reading the full event and
memo. Final brief is clear. This is collaboration review, not another empirical
packet observation. [Receipt](evidence/2026-09-10-cycle05-review-receipt.json).

Cycle06's separate Fable5.1 interpretation review used fresh session
`db3fac20-c2ed-4590-a4bf-a8dbda3a8245`. Request35's marker appears in its full
assistant-text memo; terminal result alone held only the final ACK-request
fragment. Lifecycle36–38 records successful startup/turn/end. After consuming
the full request and memo, Codex recorded Claude's requested ACK39; final brief
has no pending signals or active claims. [Receipt](evidence/2026-09-10-cycle06-review-receipt.json).
No empirical packet used Relay review context, and no provider job remains.

Cycle07's interpretation review used fresh session
`9427676d-e459-4536-8c00-bb80dded667b`, separate from16 isolated experimental
contexts. Request40's marker returned; lifecycle41–43 records native success.
The complete assistant-text memo was read, its example-count issue checked
against frozen metadata, and Codex recorded Claude's requested consumptionACK44.
The final brief has no pending signals or active claims, and no provider job
remains. [Receipt](evidence/2026-09-10-cycle07-review-receipt.json).


Cycle08 used one tools-disabled Fable5.1 interpretation session
`9cc0f1aa-02d2-4b47-aacd-89ef97fbacb1`, with no empirical solver invocation.
Request45's artifact-derived capsule marker returned; lifecycle46–48 records
successful startup, turn completion and end. Codex read the exact request and
complete public memo, then recorded Claude's requested ACK49. Final brief:
no pending signals or active claims; the owned provider process exited.
[Receipt](evidence/2026-09-10-cycle08-review-receipt.json).

From the repository root:

```bash
# Project-scoped ledger operations; no provider launch
python3 _sessions/tools/relay.py --json doctor
python3 _sessions/tools/relay.py --json status
python3 _sessions/tools/relay.py --json brief --agent codex
python3 _sessions/tools/relay.py claude-plan

# Read exact handoff events before deliberate consumption acknowledgment
python3 _sessions/tools/relay.py --json events --after 29 --limit 10
# Schema: acknowledge <signal-seq> --agent <recipient> --session <exact-session>
python3 _sessions/tools/relay.py acknowledge --help

# Start a Claude session with invocation-only project Relay hooks
python3 _sessions/tools/relay.py claude
```

The helper resolves its checkout from its own file, so an absolute helper path
also works from another directory. It defaults to `~/.local/bin/relay` and
`~/.local/bin/claude`; `IC_RRF_RELAY_BIN` / `IC_RRF_CLAUDE_BIN` may select other
installed executables. It passes generated JSON arguments directly to the
provider—no shell evaluation—and changes no permanent provider configuration.
It refuses an extra `--repo` or Claude `--settings` override rather than merge
conflicting configuration. Native permissions and hook review still apply.

In this desktop sandbox, the installed Relay refuses `unsafe launcher ancestry`
because `/home` is presented as owned by UID 65534. The same command succeeds in
the normal host context. Use the desktop's supported escalation for an authorized
Relay operation or a normal host terminal. Do not chmod directories, reinstall
Relay, copy the ledger, or bypass its checks to address this mapping.

On a different machine, install a supported Relay release following that
project's instructions, then explicitly enroll this checkout:

```bash
relay --repo /absolute/path/to/ic-rw-rrf --json init
```

Do not precreate `.relay/` or copy enrollment metadata from another machine.
The research/demo and session helper work without Relay. The installed Relay
profile currently requires Linux/WSL x86-64, Python 3.12, Git, Landlock ABI3+,
procfs, and filesystem birth-time support; this does not change the research
harness's Python 3.8+ standard-library requirement.

## Collaborating

1. Read the bounded brief before taking scope; inspect full events/artifacts
   when an inbox item matters. A failed brief is unavailable state, not empty state.
2. Give the other agent a bounded task, owned paths (or read-only scope), evidence,
   stopping condition, and expected result. An ordinary reviewer reports back
   to the coordinator instead of starting another journal/backlog.
3. Signal `review.requested` / `work.handoff` only for actual work. Artifacts must
   use `git:<oid>`, `sha256:<digest>`, or `receipt:<stable-id>`; a raw file path is
   not an immutable reference. Read `signal --help` for the installed schema.
4. Read the returned review and verify its artifact. ACK means deliberate
   consumption/routing of the exact signal; it is not a notification cleanup step.
5. Keep claims specific to shared resources and release only exact claims owned
   by this task. Ordinary disjoint read-only work needs no ceremonial claim.

The current desktop task uses explicit CLI briefs; starting a new Claude through
the helper adds its invocation hooks. For a new Codex CLI session, the installed
`provider-config --client codex` can generate native arguments, with Codex's
separate hook-review step. This does not retrofit hooks into an already running
desktop task.

Manual native resume worked for cycle01 using `--resume` with the saved native
session UUID and the same project helper. This reuses the coordinator's context;
it is not an automatic Relay wakeup. Reuse requires the native session record
to remain available on this host. Raw transcripts stay ignored.

Hooks supply startup/prompt context and record lifecycle events. They do not
wake peers, deliver arbitrary user prompts, ACK work, release claims, or prove
task completion. There is no permanently listening Claude session here. Full
automatic wake/resume and two-agent recovery behavior remain part of Agent
Relay's active development; do not claim those from ledger health alone.

## Completed bounded review

The ignored `_sessions/local/` contains the exact review packet, its SHA-256,
signal receipt, and provider output. The packet contained only the new research
audit and case-study draft. The invocation used the existing Claude sign-in,
disabled tools, MCP, and optional setting sources for that process, supplied
excerpts in the prompt, and enforced a three minute process limit. No permanent
settings were altered. Authentication and the native model response succeeded.

Automatic approval review initially blocked external-provider egress; Dave then
explicitly approved the bounded review, and the identical scope proceeded. This
is historical context, not a new confirmation requirement for future already
authorized work.

Claude asked the coordinator to record the ACK because the review had tools
disabled. Codex read the complete request event, verified the context marker and
completed review, and recorded the receipt for that exact Claude session. The
ACK was coordinator-recorded, not a Claude tool call. The final Claude brief has
no pending request and no resource claims. Substantive review findings were
incorporated, with a reviewer arithmetic mistake explicitly corrected.

This verifies authenticated context delivery plus an excerpt review. It does
not verify autonomous code edits, Claude-operated acknowledgement, native Codex
hook trust, automatic peer wake/resume, or a full implement/review/restart loop.
Cycle01 additionally verifies native phased subagents, code/evidence reading,
model-tier observation, and manual coordinator resume. Its `--tools` allowed
only read operations plus bounded native agents; permanent provider settings
and neighboring project sessions were not changed.

Cycle12's initial new-inventory transfer was denied by automatic approval review
before execution. No Relay event or provider process was created for that action.
An approved narrower review used only previously published, immutable GitHub
excerpts after unauthenticated retrieval and byte-hash verification. No content
was newly published to enable the transfer. Claude's review therefore covers
those public excerpts, not the unsent inventory or later case card. Preserve that
scope distinction when incorporating its findings; the standing collaboration
authorization does not become a recurring permission question.

That review completed through request65 and lifecycle66–68. Codex read the exact
request and full public memo, then recorded the requested ACK69 for native session
`0396bb41-f763-4040-bc46-f989527bebfa`. Final brief69 is clear, without pending
signals or active claims. See the [boundary receipt](evidence/2026-09-11-cycle12-review-boundary.json)
and [review receipt](evidence/2026-09-11-cycle12-review-receipt.json).

Cycle13 used the expanded authorization for an unpublished direction handoff.
Fable session`363eb9b6-9a58-46ed-a108-f426e23b1f77` returned request70's marker;
lifecycle71–73 completed. Codex read the request and full two-fragment public memo
and recorded Claude's requested ACK74. The final brief is clear; no provider
remains active. This was a design review, not review of the later input correction
or measured results. [Receipt](evidence/2026-09-11-cycle13-design-receipt.json).
