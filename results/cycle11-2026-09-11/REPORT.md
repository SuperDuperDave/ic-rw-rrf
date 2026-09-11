# Cycle11: correct answers and validity judgments under copied support

One verifier returned **4/4 correct final answers and16/16 correct submission
validity judgments** in the four prespecified cases. All four responses were
accepted. Following the frozen stopping rule, **multiagent work in this
restricted arithmetic laboratory is parked**. No additional solver calls,
repair stages or harder arithmetic follow this result.

## Question and observations

Can one verifier give the correct answer and judge the supplied evidence when
valid support is either the minority or majority by submission count? Reuse
cycle10's exact two programs and valid/endpoint-flipped certificates. Each input
contains three instances of one root and one of its opponent, with distinct
submission IDs and explicit shared root identity. These are copied artifacts,
not independent acquisitions.

| Request | Packet | Private slot types | Correct / accepted answers | Correct / accepted validities | Answer agrees with accepted support |
| --- | --- | --- | --- | --- | --- |
| 1 | R0-A | F,V,F,F | 1/1 | 4/4 | yes |
| 2 | R1-B | V,V,V,F | 1/1 | 4/4 | yes |
| 3 | R0-B | V,F,V,V | 1/1 | 4/4 | yes |
| 4 | R1-A | F,F,F,V | 1/1 | 4/4 | yes |

V denotes a valid trace; F changes only the final Boolean and fails at row6.
These labels were absent from model inputs. Answers in request order were
false,true,false,true. Every returned validity map was exact, with no same-root
copy disagreement. The endpoint set of reports marked valid was a singleton
matching the answer in every case. No missing decisions were imputed.

See the [readable cases](prepared/cases.md), [sealed fixture](prepared/fixture.json),
[responses](observations/responses.json), and [scores](scored/scores.json).

## Comparators and boundaries

Exact replay answers4/4. Majority, minority, either constant and each fixed-slot
answer policy score2/4. Deduplicating the two root votes leaves a1:1 tie in every
case: four abstentions and zero answered, not four wrong answers. Always-valid
and always-invalid each score8/16 judgments; exact checking scores16/16.
Endpoint-agreement validity also scores16/16 on these V/F-only roots, so this
experiment does not independently distinguish it from complete verification.
Cycle10's preserved interior-error diagnostic addresses a different contrast.

The evidence supports these finite returned decisions and their consistency.
It does not show that the model needed the certificates to solve the program,
that it checked before selecting, or that copying had no causal effect. Direct
program solving can produce every correct output. There are two variants of one
arithmetic skeleton, four reused roots, twelve distinct submission IDs across
sixteen appearances, and four calls—not twenty independent tasks. No population
inference, novelty, general superiority or multiagent advantage is established.

## Execution and preservation

The [design](../../_sessions/cycles/2026-09-11-cycle11-evidence-selection-design.md)
predated construction. A passed [local audit](../../_sessions/evidence/2026-09-11-cycle11-independent-check.json)
was followed by a separate [execution decision](../../_sessions/evidence/2026-09-11-cycle11-execution-decision.json)
and [protocol](../../_sessions/cycles/2026-09-11-cycle11-execution-protocol.md).
No RNG, parameter search, replacement, new corruption or prior-artifact edit.
Payload bytes in request order:1394,1394,1396,1396. Local preparation took
0.15684seconds; byte length does not establish equal token exposure.

Four fresh isolated `claude-opus-5`/high calls used the pinned native executable,
no tools, hooks, agents or earlier-response context. Limits remained$1 per batch,
120seconds per call,300seconds total,500 output tokens per API response including
thinking. The batch completed in13.25492seconds with native list accounting
$0.069705. Four observed messages used697 output tokens including384 thinking
tokens; maximum195 per message, with no observed continuation or activity.
Wire attempts remain incompletely observable. This is not subscription billing.

Prepared manifest SHA256:
`c69e0ed91793ff511ebcfb18e40278db5fa0ee0fe3e460eb089ee798e17717cb`.
Execution manifest SHA256:
`bfb2c4859c69177c263903da3b0d7e646da0d924cc7bb87a2e64b1f35154d6ae`.
Their parent remains cycle10 manifest
`6647f0ae806ada137668252ffe03839caeab3e13ae2ccf8127dcc6b67cf203cd`.

```bash
python3 evaluation/cycle11_certificates.py prepare --output results/cycle11-2026-09-11/prepared
python3 _sessions/tools/check_cycle11_evidence.py --prepared results/cycle11-2026-09-11/prepared
python3 _sessions/tools/run_cycle11_verifier.py prepare --prepared-manifest-sha256 c69e0ed91793ff511ebcfb18e40278db5fa0ee0fe3e460eb089ee798e17717cb
python3 _sessions/tools/run_cycle11_verifier.py collect --execution-manifest-sha256 bfb2c4859c69177c263903da3b0d7e646da0d924cc7bb87a2e64b1f35154d6ae
python3 _sessions/tools/score_cycle11_verifier.py --score
```

These are the recorded commands; exclusive directories prevent overwriting this
run. Collection is historical, not an instruction to repeat provider calls.
Raw provider streams stay ignored; selected native metadata and decisions are
public. The standard-library demo and all323 tests passed before collection.

## Research checkpoint

This closes the promised evidence-selection bridge. The practical result is a
working single-verifier baseline with no demonstrated gap for a multiagent stage
to repair here. The [synthesis](../../docs/RESEARCH_SYNTHESIS.md) consolidates the
findings before another laboratory is chosen.
Any future evidence-acquisition question needs an applied case with genuinely
missing information and a single-system comparator with equal access and budget.

The [independent empirical audit](../../_sessions/evidence/2026-09-11-cycle11-empirical-audit.json)
passes7,997 checks and verifies all four raw streams. Its
[public-only run](../../_sessions/evidence/2026-09-11-cycle11-public-only-audit.json)
passes7,893 checks with raw verification explicitly unavailable. Local preparation
passes6,672 checks. Check counts describe audit coverage, not scientific sample size.

Claude agreed to the stop; the [integration](../../_sessions/cycles/2026-09-11-cycle11-review-integration.md)
corrects its claims about internal computation, token evidence and a proposed
relabeling of old retrieval items. The review cost$.48746175 and51.02861seconds;
combined native list accounting$.55716675 excludes Codex and subscription billing.
The full public memo and original overclaims are preserved. No live provider or
pending Relay request remains after consumption ACK64.
