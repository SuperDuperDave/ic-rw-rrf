---
name: session-wrap
description: Close an IC(R/W)-RRF coordinating research session with evidence, updated hypothesis and backlog state, verified friction triage, and a clear resume point. Use when completing, handing off, or stopping owned research work. Ordinary bounded workers, waits, and compaction do not trigger a project wrap.
---

# Wrap IC(R/W)-RRF

Follow the shared [WORKFLOW wrap](../../../_sessions/WORKFLOW.md#wrap).
The coordinator owns the current stream, synthesis, backlog reconciliation,
collaborator accounting, and one completion report. A bounded worker returns
its result and ownership status to that coordinator. An independently assigned
research task wraps only its own scope and notebook.

Reconcile evidence and rejected assumptions with the
[phase-space map](../../../_sessions/PHASE_SPACE.md) and edit canonical
[backlog bodies](../../../_sessions/PLANNING.md). Keep carryforward as pointers.
Run the workflow's [friction ratchet](../../../_sessions/WORKFLOW.md#friction-ratchet)
before choosing what survives into the next session; a landed fix still needs
outcome evidence. Update Resume with the real stopping point and live work.

If already wrapped, check what changed and reuse the existing receipt when
still accurate. Follow existing authorization for any external handoff; this
skill adds no automatic commit, publication, or branch-cleanup step.
