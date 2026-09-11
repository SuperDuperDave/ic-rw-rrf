# Cycle05 initial batch — an instrument failure, preserved

The first native Opus5 invocation succeeded, but the frozen collector rejected
it because a nonempty subagent-statistics object contained zero-valued counters.
The collector mistook the object's presence for activity and followed its
whole-batch stopping rule. The scientific primary is **incomplete: zero accepted,
one rejected, nineteen unscheduled**. This is not a model reasoning failure or
evidence that an agent was dispatched.

[Original observations](observations/responses.json),
[frozen incomplete scores](scored/scores.json),
[independent instrument audit](../../_sessions/evidence/2026-09-10-cycle05-instrument-audit.json).

The raw stream independently confirms one canonical `claude-opus-5` response,
empty tools/MCP, no agent activity, native success and end_turn. It reported 157
output tokens including 138 thinking tokens,4.53 seconds process wall time and
$0.014545 native list-price accounting. The exported answer is valid JSON; it
is used only to diagnose the instrument. It is not retroactively admitted to
the frozen score and is not carried into another batch.

The [separate replication](../cycle05-replication-2026-09-10/REPORT.md) corrects
only zero-count metadata interpretation. It retains the same20 prepared inputs,
prompt, exact reference arithmetic, order and provider/resource controls, with
entirely fresh responses. Its protocol and sources were frozen separately after
the original stopped run was scored and independently reviewed. The original
runner, tests, protocol, observation and score bytes remain unchanged.

This exposes a measurement boundary: native execution, instrumentation acceptance,
valid exported output and mathematical accuracy are separate outcomes. The
regression test now covers the actual zero-counter shape; no improvement in
model ability follows from repairing its detector.
