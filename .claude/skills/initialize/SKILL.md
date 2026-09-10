---
name: initialize
description: Initialize or resume an IC(R/W)-RRF coordinating research session, recover its live notebook and collaboration context, and enter the recursive research loop. Use for session startup or requests to initialize, start a session, or pick up this project. Bounded workers use their assigned context and return findings to the coordinator.
---

# Initialize IC(R/W)-RRF

Read the repository's [shared agreement](../../../AGENTS.md), then follow
[WORKFLOW](../../../_sessions/WORKFLOW.md#start-and-resume). It owns startup,
role selection, the recursive research loop, checkpoints, and friction handling.

Use the [research charter](../../../_sessions/RESEARCH_CHARTER.md) for intent and
[phase-space map](../../../_sessions/PHASE_SPACE.md) for the live hypothesis
graph. Orient with the map, backlog, research state, and relevant stream as the
workflow directs. On compaction, recover the existing stream's Resume and
recent evidence before continuing it. A worker needs only the assigned context;
it reports evidence, limitations, and ownership status without another journal.

Run `python3 _sessions/tools/session.py status` from the repository root;
use `start <slug>` only when this coordinating task has no stream. Reconcile
live ownership through [RELAY](../../../_sessions/RELAY.md) before assigning
overlapping work. Apply the existing project authorization and
[Claude compute contract](../../../_sessions/CLAUDE_COMPUTE.md) when using Claude.

Before completing, handing off, or stopping this coordinating task, use
[session-wrap](../session-wrap/SKILL.md). A wait or compaction continues the task.
