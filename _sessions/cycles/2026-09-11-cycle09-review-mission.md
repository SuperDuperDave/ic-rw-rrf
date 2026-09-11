# Cycle09 local-evidence and execution-decision review

You are Fable5.1, Dave's scientific collaborator on curiosity-led rank-fusion
and agent evidence research. Tools/MCP/agents are disabled. Review only this
capsule. Target350 words: recommend RUN or PARK for the specifically bounded
two-call pilot below, identify what could falsify the narrow hypothesis, and
name the most informative next question after that checkpoint. Return the
marker delivered through Relay and request Codex's consumption ACK; do not
invent a missing marker. This is a design review, not a solver observation.

Origin: distinguish useful minority evidence from noise and repeated agreement.
Earlier actual models reproduced supplied Bayesian probabilities; that did not
measure extracting reliability from content. A program-error pilot had no errors.
A later local loop audit passed its gate but its label imbalance let always-false
answers mimic a short/long accuracy decline. We parked that provider batch and
chose evidence-content verification with your preceding review.

Cycle09's local design was committed before drawing parameters. One exact
six-assignment program, one seeded A/B/R draw, one seeded shuffle and five ID
draws; no replacement. V is valid; I injects +1 after assignment3 then propagates
the altered state; its final a changes by2 so parity survives. F flips only the
final Boolean. Python and an independently written AST checker verify complete
submitted states, all local transitions, first-invalid rows, schema and custody.
Malformed/ill-typed traces are construction failures, not mathematical errors.

The solver-candidate base packet has three originals plus two null slots; the
repeat packet adds two exact F-certificate copies with new instance IDs and F's
root ID. Copy identity never supplies validity or independence. Private labels
and checker verdicts shown here do not appear in candidate solver payloads.
The actual facts below are generated directly from sealed artifacts.

Manifest SHA256: `0cdb62969bb8a0d365d2b5bd7a225773d938c4a9f66cdc62971d123f62a6d250`.
Parameters: `{"A": 0, "B": 0, "R": 0}`.
Private shuffled order: `V,I,F`.
Packet bytes: `{"base": 1079, "repeat": 1665}`.

# Cycle09 certificate cases

Local construction labels and checker verdicts below are evaluator metadata.
Only the separately serialized packet files are candidate solver inputs.

## Program

~~~python
a = 0
b = 0
a = a + b
b = a - b
a = a + b
result = (a % 2 == 0)
~~~

## Certificate V

| Step | Recorded complete state | Locally valid transition |
| --- | --- | --- |
| 1 | {"a":0} | true |
| 2 | {"a":0,"b":0} | true |
| 3 | {"a":0,"b":0} | true |
| 4 | {"a":0,"b":0} | true |
| 5 | {"a":0,"b":0} | true |
| 6 | {"a":0,"b":0,"result":true} | true |

Whole-certificate validity: true. First invalid step: None.

## Certificate I

| Step | Recorded complete state | Locally valid transition |
| --- | --- | --- |
| 1 | {"a":0} | true |
| 2 | {"a":0,"b":0} | true |
| 3 | {"a":1,"b":0} | false |
| 4 | {"a":1,"b":1} | true |
| 5 | {"a":2,"b":1} | true |
| 6 | {"a":2,"b":1,"result":true} | true |

Whole-certificate validity: false. First invalid step: 3.

## Certificate F

| Step | Recorded complete state | Locally valid transition |
| --- | --- | --- |
| 1 | {"a":0} | true |
| 2 | {"a":0,"b":0} | true |
| 3 | {"a":0,"b":0} | true |
| 4 | {"a":0,"b":0} | true |
| 5 | {"a":0,"b":0} | true |
| 6 | {"a":0,"b":0,"result":false} | false |

Whole-certificate validity: false. First invalid step: 6.

## Fixed reference policies

| Packet | Policy | Correct / valid / planned original judgments |
| --- | --- | --- |
| base | always_valid | 1 / 3 / 3 |
| base | always_invalid | 2 / 3 / 3 |
| base | exact_checker | 3 / 3 / 3 |
| repeat | always_valid | 1 / 3 / 3 |
| repeat | always_invalid | 2 / 3 / 3 |
| repeat | exact_checker | 3 / 3 / 3 |

These are six diagnostic judgments from one program construction.
No empirical solver outcome or provider launch is implied.


This actual draw is the all-zero program; I invents conspicuous nonzero states.
The valid original happens to be first. Always-valid scores1/3; always-invalid
and final-answer-only score2/3; first-original-only scores3/3 in each packet.
These pre-response reference-policy facts limit any perfect result. The exact
local gate passed; do not seek a new seed, order or corruption to harden the case.

Candidate empirical pilot: exactly two native Opus5/high calls, base then repeat,
fresh isolated contexts. Common fixed system instruction requests a validity
Boolean for each original ID, explicitly checking complete steps and noting
that a correct endpoint is insufficient. Only the corresponding canonical packet
is the user input. Accept exactly the original-ID-to-Boolean JSON map; no extra
keys, numbers, duplicate keys or partial salvage. First native/format/custody/
resource failure stops scheduling. No retries, alternate model, repair, reserve
or prompt search. Current binary remains2.1.267 with the prior hash; official
Opus/Fable IDs and prices rechecked. Tools/hooks/MCP/agents disabled for empirical
calls. Use$1 native scheduling allowance,120s/call,300s/batch,500 output tokens
per API response including thinking; continuations can exceed500 perinvocation.
The execution protocol/source/payload seal remains pending this local checkpoint.

Primary requires both maps: preserve all6 original-ID decisions, exact correct/
accepted/planned counts and each original's base→repeat transition. Partial
counts are separate with full primary null. No imputed mathematical errors.
Wrong V or accepted I/F would falsify successful instruction following on this
minimal case; six correct decisions would be consistent with checking, while
also matching the position heuristic. This is a semantic/format feasibility
pilot, not difficult reasoning, internal strategy, independence or generalization.

F-only duplication, added text, fixed call order and stochastic responses prevent
a pure-copy causal claim. No multiagent comparison exists. Machine execution is
the practical verifier for these programs. A later collaboration claim would
need a single verifier with identical evidence and total inference resources.
The local fixture is already complete. Is one bounded actual observation worth
its cost, or is a more discriminating prospective local design the better next
step? Do not treat either decision as requiring new permission from Dave.
