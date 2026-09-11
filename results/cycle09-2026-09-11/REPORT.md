# Cycle09: correct certificate judgments with an unresolved shortcut

Two fresh Opus5/high invocations returned all six planned judgments correctly:
one valid trace accepted, two invalid traces rejected, before and after adding
two copies of the final-error trace. One invalid trace reaches the correct final
Boolean; its rejection shows that these returned decisions differ from the
endpoint-only reference policy. The first-original-only policy also scores
perfectly on this construction, so the observations do not identify step checking.

This is one program with three traces judged twice. It is a small feasibility
result, not six independent tasks or evidence of general verification ability,
independent errors, causal resistance to repetition, or multiagent advantage.

## Construction and measurements

The previously committed [design](../../_sessions/cycles/2026-09-10-cycle09-certificate-design.md)
specifies one six-assignment program and one parameter draw. Seeds 420009 and
420010 respectively determine parameters and report ordering/IDs. The actual
draw is A=B=R=0; the valid certificate happens to be first. No candidate was
replaced, and no reserve was used. The program is deliberately preserved even
though its all-zero invariant makes the injected nonzero states conspicuous.

```python
a = 0
b = 0
a = a + b
b = a - b
a = a + b
result = (a % 2 == 0)
```

V records the valid execution. I changes a from 0 to 1 at row 3, then continues
consistently from that submitted state: row 4 is (a,b)=(1,1), row 5 is(2,1), and
the final result is still true. Only its row 3 transition is invalid. F keeps
V's integer states and changes only the final result to false; row 6 is invalid.
The independent evaluator checks complete states and exact types after every
assignment, using each preceding submitted state for the next transition.

| Certificate | First invalid row | Recorded final answer | Exact validity | Base judgment | With F copies |
| --- | --- | --- | --- | --- | --- |
| V | none | true | true | true | true |
| I | 3 | true | false | false | false |
| F | 6 | false | false | false | false |

[Readable states](prepared/cases.md) and [canonical fixture](prepared/fixture.json)
preserve the construction; private V/I/F labels are evaluator metadata, absent
from solver inputs. The packets contain opaque instance/root IDs. Base has three
originals plus two null slots; repeat fills those slots with exact F-certificate
copies and new instance IDs. Both requests ask for the same three originals.
Base is 1,079 bytes; repeat is 1,665 bytes, 586 more. Copy identity is not correctness
or evidence of independent errors.

The local gate passes all prescribed checks; a separate independent audit passes
761 checks of truth, local transitions, schema, random draw, copying and custody.
Malformed certificates would have stopped preparation instead of becoming false
scientific examples. [Local receipt](../../_sessions/evidence/2026-09-11-cycle09-independent-check.json).

## Comparators and interpretation

| Policy | Base correct /3 | Repeat correct /3 |
| --- | --- | --- |
| Always valid | 1 | 1 |
| Always invalid | 2 | 2 |
| Final-answer-only | 2 | 2 |
| First-original-only | 3 | 3 |
| Exact machine checker | 3 | 3 |
| Observed Opus5 judgments | 3 | 3 |

These reference counts were recorded before solver responses. Final-answer-only
accepts I incorrectly. The observed map differs from that policy but matches
first-original-only, full replay and other possible procedures. No private
reasoning text is needed or used to infer a strategy. Machine execution is the
practical verifier for this restricted language; the study is about evidence
use by models, not beating program execution at verification cost.

No original's judgment changes across the two packets. This is a descriptive
observation. Two fresh stochastic responses, fixed base-first order, added text
and copying only F cannot establish a pure-copy causal effect or its absence.
No comparison with a multiagent system was run. A collaboration claim would need
the same evidence and total inference resources for a single-verifier baseline.

## Execution, review and reproducibility

The local checkpoint and one Fable5.1/high design review preceded a separate
[execution decision](../../_sessions/evidence/2026-09-11-cycle09-execution-decision.json)
and [protocol](../../_sessions/cycles/2026-09-11-cycle09-execution-protocol.md).
The exact common system prompt and unchanged packet bytes were sealed before
two base-then-repeat calls. The strict parser accepts only a complete original-ID
to Boolean map from the unique terminal result. Wrong judgments and collection
failures have different statuses; no retry, repair or replacement was needed.

Local manifest SHA256:
`0cdb62969bb8a0d365d2b5bd7a225773d938c4a9f66cdc62971d123f62a6d250`.
Execution manifest SHA256:
`43b5fb9e6bf85b7679a192a48f0f1e66b7091070880c565f0841e1235f96cccc`.
The starting commit is d739a949e891d143e93705c285fb8f7bd5aac266; manifests pin
the new source/test/protocol bytes as well as unchanged reusable native code.

Empirical collection completed in 6.01481 seconds at $0.032690 native list
accounting. There were two observed provider messages, one per invocation,
296 output tokens including 194 thinking tokens; no continuation, refusal,
fallback, tool or agent activity. The frozen bounds were $1 scheduling allowance,
120 seconds per invocation and 300 seconds per batch; 500 output tokens is a per
API-response bound, not a guarantee about aggregate tokens or wire attempts.
[Observation manifest](observations/manifest.json), [public response receipts](observations/responses.json),
[all six scored decisions and policies](scored/scores.json).

Fable review cost $0.21040825 and took 35.93 seconds; total observed native cycle
accounting is $0.24309825, excluding Codex work and not subscription billing.
The review endorsed the bounded feasibility question. Integration corrected its
causal wording, presumed resource-failure cause and comparison of hashes for
different artifacts. [Original memo](../../_sessions/cycles/2026-09-11-cycle09-claude-review.md),
[corrections](../../_sessions/cycles/2026-09-11-cycle09-review-integration.md).
Review context was separate from both solver invocations. Request 50 was consumed
and acknowledged as Relay 54; no task-owned provider remains active.

All 270 test cases pass across the final sources. Independent code review caught
an oversized-number JSON exception before execution; its regression verifies
that it remains a format failure. Raw provider streams stay in ignored local
storage. Public receipts contain decisions, hashes and selected native metadata.
The [independent empirical audit](../../_sessions/evidence/2026-09-11-cycle09-empirical-audit.json)
passes 1,298 checks, including both raw streams and independent score reconstruction.

For local rechecks without provider calls:

```bash
python3 _sessions/tools/check_cycle09_evidence.py --prepared results/cycle09-2026-09-11/prepared
python3 _sessions/tools/check_cycle09_observations.py
python3 -B -m unittest discover -s evaluation/tests
python3 -B -m unittest discover -s _sessions/tools/tests
```

The provider/scoring commands are in the frozen execution protocol; their output
directories are exclusive and must not be overwritten. The next question is
whether judgments remain correct across the [prospective balanced panel](../../_sessions/cycles/2026-09-11-cycle10-discriminating-design.md)
where position and endpoint policies no longer match exact verification. That
requires its own local gate and execution decision; no such observations exist.
