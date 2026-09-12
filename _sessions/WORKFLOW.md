# Session workflow

The standing research practice is curiosity-led and recursive: orient, propose
different explanations, test what distinguishes them, seek independent critique,
update the map, and choose the next question. Use this loop for research; scale
the notes and review to the work. A small maintenance task needs a small check.

## The memory system

| File | Owns |
| --- | --- |
| `AGENTS.md` | Shared standing instructions for Codex and Claude |
| `CLAUDE.md` | Claude entry point into the shared agreement |
| `_sessions/MAP.md` | File roles and navigation; no drifting line numbers |
| `_sessions/RESEARCH_CHARTER.md` | Durable research intent and operating boundaries |
| `_sessions/PHASE_SPACE.md` | Live hypothesis graph: candidate regions, evidence, alternatives, and next discriminating tests |
| `_sessions/PLANNING.md` | Living priorities, decisions, parked work, and acceptance criteria |
| `_sessions/RESEARCH_STATE.md` | Current synthesis, claim boundaries, and evidence links |
| `_sessions/streams/` | Dated working notes: outcomes, decisions, hypotheses, evidence, friction |
| `_sessions/FRICTION.md` | Unresolved process issues and adopted fixes awaiting verification |
| `_sessions/RELAY.md` | Project enrollment, collaboration commands, and operational limits |
| `_sessions/CLAUDE_COMPUTE.md` | Project Claude model/compute contract and invocation checks |

The stream is a journal; the backlog is edited. A long-running item has one
body in PLANNING and short pointers from streams. Do not copy entire backlog
entries forward or put every transient observation into the standing rules.

## Ownership

The **coordinator** owns this task's stream, synthesis, phase-space/backlog
updates, collaborator accounting, and wrap. A **bounded worker** owns its assigned
question or files, reads the necessary context, and returns findings, evidence,
limitations, and live job/claim status. It does not initialize another project
journal or reconcile the shared backlog. A child explicitly assigned an
independent research task and stream coordinates only that scope.

Give independent workers concrete questions and evidence access. Parallelize
useful separate lenses; reserve shared-file edits for named owners. Relay
records coordination facts, while the coordinator checks the underlying result.

Before freezing a worker-owned artifact, wait for its explicit stable-file handoff;
file existence alone does not mean editing is finished. Read and hash the delivered
bytes, then tell the worker they are frozen. Later revisions use a separate path
and an explicit link to the preserved version, including formatting-only edits.

## Start and resume

Read the shared agreement, [charter](RESEARCH_CHARTER.md), [file map](MAP.md),
[phase-space map](PHASE_SPACE.md), [backlog](PLANNING.md), and
[research state](RESEARCH_STATE.md), then the previous relevant stream's Resume,
recent evidence, and Carryforward. Follow older evidence links when needed.
Reconcile this context with the user's current intent and live collaborators
using [RELAY](RELAY.md); use the [Claude compute contract](CLAUDE_COMPUTE.md)
when invoking Claude. Surface unresolved NEEDS DAVE decisions while advancing
independent work.

Run the read-only status helper and preserve existing dirty/untracked work.
Create one coordinating stream only if the current task has none:

```bash
python3 _sessions/tools/session.py status
python3 _sessions/tools/session.py start research-restart
```

The helper resolves the repository from its own location and uses exclusive
creation. Initialization also works without Relay installed; unavailable
coordination state is not evidence that a resource is idle. Use existing
authorization for local research, subagents, and necessary project context sent
to Claude; do not request the same permission at every loop. Surface decisions
that actually change scope, exceed the authorized budget, or need Dave's judgment.

On resume after compaction or interruption, read the **same stream's** Resume
and recent evidence before substantive continuation. Keep the current stream
across date changes within the same task. Announce the immediate question and
checkpoint briefly, then work; initialization is not a report-writing phase.

## Recursive research loop

1. **Orient.** Choose a question from the charter, phase-space map, an unexpected
   observation, or the user's direction. State what is unknown and why resolving
   it would change the next decision. Current backlog order guides attention;
   it does not predetermine every inquiry as k tuning or another RRF variant.
2. **Diverge.** Develop materially different candidate explanations or mechanisms,
   including a plausible null and a surprising alternative when useful. Give
   them distinct predictions. A speculative idea can enter the map before it is
   measurable; label it and identify the missing bridge to a discriminating test.
3. **Discriminate.** Choose the smallest test that could separate the live
   alternatives. Before running, record the prediction, falsifier, relevant
   baseline, data/configuration, metric or observable, selection budget, and
   stopping checkpoint. Use synthetic or mathematical probes where they answer
   the question; use comparable held-out evaluation for performance claims.
4. **Critique independently.** For a material result, ask a separate agent to
   challenge the method or interpretation using raw evidence and a bounded
   question. Do not prime it with a required verdict. Useful lenses include an
   alternative mechanism, a baseline/selection confound, or a counterexample.
   Verify consequential findings against their evidence; agreement is not proof.
   If independent review is unavailable, keep the critique pending and state
   that limitation instead of presenting a self-check as independent validation.
5. **Synthesize and map.** Record the result, critique, unresolved disagreement,
   and the narrow claim justified. Update [PHASE_SPACE](PHASE_SPACE.md) with
   which explanations remain live, which region was bounded, and the test that
   would change that judgment. Update RESEARCH_STATE only when the current
   synthesis changes; put scheduled work in a single PLANNING body.
6. **Continue, pivot, or park.** Continue when a discriminating next test fits
   the objective and budget. Pivot when a new explanation better accounts for
   the evidence. Park when the test is not currently discriminating, a dependency
   is missing, or further work has low expected information value. Record why
   and what observation would reopen it, then feed the next question into Orient.

Use evidence labels where they clarify status:

- **[hypothesis]** — a proposed mechanism, prediction, or interpretation; name
  what could change the judgment.
- **[observed]** — a directly checked result with an artifact, command, or source
  and the conditions under which it occurred.
- **[supported]** — a claim backed by the cited evidence and critique within a
  stated scope; retain alternative explanations and generalization limits.

Confidence is an explanation of evidence strength and remaining uncertainty.
Do not invent calibrated-looking confidence scores. Numerical uncertainty needs
an actual calculation and a described method. Separate measured improvement,
mechanistic explanation, and novelty; evidence for one does not establish the
others.

**Checkpoints keep recursion purposeful.** Agree with the existing task's
constraints on the next observable and cost before each experiment; checkpoint
again after synthesis. Stop expanding a branch when its acceptance/stopping
condition is met, evidence no longer distinguishes alternatives, or the next
step exceeds authorization. Choose another useful branch only while the assigned
objective and budget permit it. An achieved objective, requested handoff, or
explicit stop leads to Wrap. A live job, pause, or compaction leads to a Resume
update. Research may remain open after this particular task is complete.

## Work and resume

Keep a short Resume block with current question, current loop phase, next
discriminating action, live processes/collaborators, and material constraints.
Append concise evidence and decision summaries at material changes, including
failed predictions and surprising directions. Preserve corrections and useful
dead ends. These are outcome/evidence notes, not a verbatim transcript or private
reasoning trace; routine tool traffic does not need a journal entry.

For each experiment record data and run-file identities, code revision/dirty
state, exact command, seeds/splits, baseline semantics, metric, selection budget,
and where raw results live. Prefer project-relative reproducibility commands.
Use one seed for a smoke test; a research claim needs the planned evaluation.

Before an interruption, leave an accurate Resume with artifact paths and any
jobs still running. Recover it on return; a summary alone may omit those facts.

## Friction ratchet

Log `symptom · where it happened · cost · proposed response` when fresh. Fix a
clear local cause during the work when authorized; do not defer every small
improvement until wrap. At each useful checkpoint, and for remaining items at
wrap, choose one disposition:

- **SUBTRACT:** remove a redundant step or fix a tool. Name the change and check
  the actual affected path; a patch alone is not proof of better operation.
- **PROMOTE:** retain necessary work but capture the recurring judgment in one
  helper, map entry, research rule, or backlog item. A necessary scientific
  check can be made easier to invoke without removing the check.
- **DROP:** discard a demonstrated non-pattern or observation with no useful
  action. Record the reason; do not accumulate ceremonial rules.

Route surviving work to one durable home: move open recurring issues to
FRICTION and link substantive work to PLANNING. Prefer capability gained and
recurring effort removed per unit of lasting complexity. Do not build a new
framework for a one-off annoyance or repeat a triage already recorded.

Mark an implemented fix `landed, awaiting outcome verification`. Verification
requires either an exact before/after reproduction at the original friction
point or a later independent use that exercises the fix. A passing tool test or
new document proves implementation health, not reduced friction. A DROP records
its reason without claiming verified improvement; recurrence reopens the item.
Keep necessary scientific checks even when they cost time.

## Wrap

The coordinator wraps when completing, handing off, or stopping its owned task.
An ordinary worker returns to its owner. A process stopping, waiting, or crossing
a context boundary does not by itself mean the task is complete.

1. Stop opening new experiments. Collect worker results and resolve or explicitly
   checkpoint live jobs and pending decisions. Check the diff and run verification
   appropriate to changed behavior; preserve unrelated changes.
2. Write outcomes, evidence, falsified predictions, critique, and limitations into
   the stream. Reconcile the phase-space map and current synthesis where changed.
3. Edit each unfinished or parked PLANNING item's existing body with status,
   evidence, why parked, next acceptance condition, and owner/decision needed.
   Keep stream Carryforward as short pointers, not duplicated item bodies.
4. Run the friction wrap-pass; make clear authorized fixes now, and retain the
   verification state honestly. Update the file map only if navigation changed.
5. Account for Relay assignments and exact claims owned by this task. Release
   those claims after their final protected action; carry unresolved coordination
   forward explicitly. Delivery and acknowledgement alone do not prove review or
   completion. Follow RELAY for any authorized external handoff.
6. Set Resume to the real stopping point, the next owner's first action, and
   explicit in-flight state. Report the outcome, checks, unproven claims, parked
   work, and any live collaborator in a short self-contained completion message.
7. Follow the shared agreement's **Preserve work each turn** policy: review and
   commit this turn's project changes, push to the branch's configured upstream,
   and verify the remote result before the completion message. The coordinator
   owns this checkpoint. No empty commit is needed for a turn without changes.
   Private Relay/runtime files stay ignored. Report a failed push honestly while
   retaining the local commit; preserve concurrent work without force-pushing.

If the stream already contains a wrap, check current status, evidence, ownership,
and live jobs. Reuse the existing receipt if accurate; update only changed facts
or reopened work. Dave's 2026-09-10 standing authorization covers project GitHub
commits and pushes each turn. Website publication, branch retirement, new
provider operations outside existing authority, and other projects' edits are
separate actions; wrapping does not expand their scope.

## Portability and provenance

Adapted on 2026-09-10 from the active Ascend initialize and session-wrap skills
at the `69be/ascend` worktree, read without changes. Mirrored patterns are bounded
context/coordination bridging, a live Resume through compaction, independent
exploratory and skeptical lenses followed by coordinator synthesis, editable
backlog bodies, coordinator-only semantic closure, repeat-wrap auditing, and
SUBTRACT/PROMOTE/DROP with outcome evidence. The research loop above adapts
those patterns to this project's question rather than its app/release machinery.

Here `.agents` and `.codex` are managed and read-only in the desktop sandbox.
The ordinary repository workflow and Python helper are portable; thin project
Claude skills route initialization and closure here. No sibling repository,
private skill, or global configuration is required.

Codex's documented repository instruction entry point is `AGENTS.md`:
[official OpenAI documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
The Claude shim explicitly imports that file. The local
`.claude/skills/initialize/SKILL.md` and
`.claude/skills/session-wrap/SKILL.md` route to this workflow. The initialize
skill's previous shared symlink had drifted into TWE Staffing instructions, so
only that local link was
replaced; the shared source and other historical craft links remain untouched.
