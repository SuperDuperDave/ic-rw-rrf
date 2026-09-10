# Agent Relay in this project

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

## Commands

From the repository root:

```bash
# Project-scoped ledger operations; no provider launch
python3 _sessions/tools/relay.py --json doctor
python3 _sessions/tools/relay.py --json status
python3 _sessions/tools/relay.py --json brief --agent codex
python3 _sessions/tools/relay.py claude-plan

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
