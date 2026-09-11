# Cycle08 — a valid loop contrast, then a change of question

The eight matched programs pass their local construction gate. Independent
execution checks agree on every state and answer, and none of the planned
cycle, endpoint or source-review stopping conditions occurs. We nevertheless
park the proposed arithmetic solver batch: the panel has a label imbalance
that makes an accuracy decline ambiguous, and inducing arithmetic errors is
an indirect route to the original evidence-aggregation question.

There were **zero empirical solver calls**. One separate Claude interpretation
review supported moving to a local certificate-content construction audit.
No replacement candidates, seed search or old reserve consumption followed.

## Frozen construction and local result

The [committed design](../../_sessions/cycles/2026-09-10-cycle08-loopbound-design.md)
and [local contract](../../_sessions/cycles/2026-09-10-cycle08-local-protocol.md)
fixed the grammar, seed 420008, candidate order, limits and decision before
enumeration. Four operator templates each appear at N=4 and N=64. Only the loop
bound changes within a pair; the family also changes other features relative
to cycle07. The two bounds are matched cases, not independent templates.

The first four candidates supplied four new syntactic templates and eight
programs, with no exclusions. All programs have 12 source lines. Python executes
only the completely allowlisted AST; instrumentation bounds intermediate
integers and counts statements. A separate AST interpreter reconstructs the
same calculations without executing Python program code. The old fixture
contributes only 24 stored structural hashes for exclusion, not reserved sources
or truths for refining this design.

| Operators | N=4 truth | N=4 statements | N=64 truth | N=64 statements |
| --- | --- | ---: | --- | ---: |
| + / + | false | 29 | true | 361 |
| + / − | false | 28 | false | 355 |
| − / + | false | 29 | false | 364 |
| − / − | false | 28 | true | 361 |

The largest absolute intermediate is 965,150, below 1,000,000. The static worst
case is 6N+7 statements: 31 and 391, below 512. Actual counts include assignments,
if visits and N+1 loop-header visits; expression nodes are not statements.
Preparation and truth checking took 0.09357735799858347 seconds locally.

Each template’s 65 states, from before iteration 1 through iteration 64, are
distinct. All four pairs end with different(a,b,c) triples. No constant Boolean
path appears when the fixed tail/predicate is applied at prefixes 0..64. Two
pairs change their Boolean; two retain it. The bounded source review finds a
last-step algebraic reduction for OP2=−, but it still depends on the prior
loop state. No shortcut making N irrelevant was demonstrated. None of these
observations proves minimum solution work or harder model reasoning.

The [panel](prepared/panel.json), [readable cases](prepared/cases.md) and
[manifest](prepared/manifest.json) preserve all programs, traces, branch counts,
predicates, source identities, exact command and interpreter. The preparation
manifest SHA256 is
`315b0282dc765569f9d4acc6f47a6a56ca3b65eaea12d7ae037b0886c5873a0d`.
The [independent audit](../../_sessions/evidence/2026-09-10-cycle08-independent-check.json)
passed 24,968 deterministic checks. Check counts are not additional observations.

## Why passing the gate did not trigger a solver batch

All four short-program answers are false; only two long-program answers are
false. Therefore an **always-false reference policy** scores 4/4 at N=4 and 2/4
at N=64, without computing either program. Its two correct→wrong paired
transitions can mimic a difficulty-related accuracy decline. These are locally
calculated reference-policy outcomes, not model responses. A future measured
decline would need its actual predictions and this alternative explanation.

The original gate excluded an all-eight-identical Boolean panel; it did not
require balance at each bound. We preserve its **passed** result and make a
separate information-value decision to park the provider batch. No outcomes
were relabeled, no balance criterion was added retrospectively, and no new
seed or predicate was sought. The distinct end states and two Boolean flips
remain valid observations about these fixed programs.

The broader limit is that shared arithmetic burden may produce more errors
without producing useful dissent. Error feasibility, available correction and
successful use of correction are separate milestones. A research branch about
checkable evidence need not first induce naturally occurring role errors.

## Review and next direction

One fresh Fable5.1/high review recommended a certificate-content audit. It
completed in 31.35 seconds at $0.19646825 native list accounting, with 2,033 output
tokens including 1,212 thinking tokens. Tools, MCP and subagents were disabled;
Relay supplied the review context. The 392-word memo exceeded its 350-word
advisory target. This accounting is not subscription billing or total all-agent
compute. The [receipt](../../_sessions/evidence/2026-09-10-cycle08-review-receipt.json)
records native success and the consumed Relay handoff.

The [integration](../../_sessions/cycles/2026-09-10-cycle08-review-integration.md)
records disagreements too. Claude's chance interpretation of endpoint flips
was unsupported, and syntactic freshness does not establish research novelty.
We also removed a proposed requirement that checking an entire certificate be
cheaper than replaying it: that is a separate efficiency question.

The [next design](../../_sessions/cycles/2026-09-10-cycle09-certificate-design.md)
uses one fresh short program and three certificate types: a valid trace, a trace
with an invalid intermediate transition but correct final answer, and a trace
with an incorrect final predicate. A repeat packet adds copies of erroneous
evidence. Exact local checks will establish the intended contrast before any
solver sees it. No next-cycle parameters or inputs have been generated.

The empirical question would be whether a solver checks evidence content and
preserves that judgment under redundant presentation. Copying also adds text,
so that contrast cannot isolate a pure copying mechanism. Machine verification
is the practical baseline for executable certificates. Any later claim of
multiagent benefit needs a single-verifier comparator with the same evidence
and total inference budget; this local result establishes no such benefit.

## Reproduce locally

```bash
python3 evaluation/cycle08_loopbound.py validate --prepared results/cycle08-2026-09-10/prepared --manifest-sha256 315b0282dc765569f9d4acc6f47a6a56ca3b65eaea12d7ae037b0886c5873a0d
python3 _sessions/tools/check_cycle08_evidence.py
python3 -B -m unittest discover -s evaluation/tests
python3 -B -m unittest discover -s _sessions/tools/tests
```

All 236 tests passed before enumeration. Preparation uses exclusive output
directories and does not overwrite this panel. The standard-library demo and
all prior frozen evidence remain unchanged. The review capsule's numeric table
and displayed source were generated directly from the sealed panel and checked
independently, exercising the correction to last cycle's handwritten label.
[Final checks](../../_sessions/evidence/2026-09-10-cycle08-checks.json) record the
completed verification. Raw provider thoughts and Relay state remain ignored.
