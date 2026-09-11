# Cycle07 — complete collection, no observed error variation

Both solver prompts answered all eight development programs correctly. All16
responses were valid, with no disagreement. The full primary is complete, but
the prespecified observability gate fails: this panel supplies no errors with
which to study correction or shared failure. The configuration is parked and
all16 reserved items remain unsent.

This is a negative feasibility result for a small fixed task/configuration.
It does not establish general solver accuracy, equivalence of the two prompts,
statistical independence, or absence of useful collaboration on other tasks.

## What was fixed before responses

The [design](../../_sessions/cycles/2026-09-10-cycle07-observation-design.md),
[grammar](../../_sessions/cycles/2026-09-10-cycle07-program-grammar.md) and
[execution contract](../../_sessions/cycles/2026-09-10-cycle07-execution-protocol.md)
define a bounded program family, first-acceptance rule, structural deduplication,
seed42 split/order, two solver instructions, metrics and stopping rule.

The first48 candidates produced24 accepted templates and24 full-cell exclusions.
Six templates per truth/stratum cell yielded8 development and16 reserve items.
Normalization removes constants, variable renaming and final predicates; these
are distinct syntactic structures, not24 independent program families. All
selected sources have12 lines. Development cases take10–37 executed statements;
the entire24-item preparation reaches at most38 statements and absolute
intermediate55. The accepted prefix uses addition for its first arithmetic
operator throughout. This limited complexity was recorded before responses;
no model-informed difficulty adjustment or replacement occurred.

Actual Python execution and an independently written AST interpreter agree on
all24 truths, final states, ASTs and step counts. Sources and excluded candidates
are preserved in the [fixture](prepared/fixture.json); its
[manifest](prepared/manifest.json) anchors exact interpreter, code, prompts and
payloads. Preparation took about0.12seconds locally; the exact measured duration
is in that manifest. The independent preflight verified13,983 assertions and
all211 project tests passed before collection.

Each development program went to two separate fresh contexts on the same
`claude-opus-5`/high workflow. G asks for program evaluation; S directs attention
to sequential updates, loop bounds and conditions. S is an audit prompt, not a
proven specialist. The only requested output is a JSON Boolean. Neither role
sees the other's answer or the truth. G-first/S-first order is balanced within
truth/stratum cells; pairs are adjacent. Fresh contexts isolate supplied history,
not statistical errors.

## Observed counts and denominators

| G outcome | S outcome | Item count |
| --- | --- | ---: |
| Correct | Correct | 8 |
| Correct | Wrong | 0 |
| Wrong | Correct | 0 |
| Wrong | Wrong | 0 |

True and false items each contribute four correct pairs. Sequential and bounded
loop strata also each contribute four correct pairs; each truth×stratum cell
contains two. G error, S error, disagreement, available correction to G, potential
harm relative to G and S-minus-G error are all0/8. Conditional correction is
**undefined**, because G made no observed errors; it is stored as `null` with
denominator0. Conditional harm is0/8. Truth-conditioned joint-error excess is
numerically zero with degenerate empirical error marginals, not evidence of
population independence. No confidence interval, p-value or ability threshold
is assigned to this selected development panel.

[Exact scores](scored/scores.json) preserve every count/denominator and all
responses. [Readable development cases](development-cases.md) show the actual
programs, truths and two answers. No missing input or failed output was imputed.

The gate required complete eight-pair coverage, each role to have at least one
correct and one wrong answer, and at least one disagreement. Coverage succeeds;
variation does not. No answer-exposure comparison, automatic harder-task batch,
prompt/model sweep or reserve consumption followed this result.

## Collection, independent audit and next decision

Collection finished in48.34seconds with native list accounting$0.166275,
about$0.0207844 per valid pair. This is not subscription billing. There were16
provider messages, one per invocation, with3,079 output tokens including2,935
reported thinking tokens; the largest message used322 of the500-token per-response
setting. No continuation, fallback, refusal, local error, tool, hook or subagent
activity was observed. The$1/300second batch limits were unchanged. Hidden
transport attempts and provider-weight revisions remain incompletely observable.

The [independent audit](../../_sessions/evidence/2026-09-10-cycle07-independent-check.json)
passed16,402 checks, including all16 private raw streams, exact source/output
custody, truth reconstruction, scores and accounting. No discrepancy was found.
The cycle06 observer correction was used on these normal completions; its refusal
path remains verified by earlier offline replay, not a new refused invocation.
All historical evidence, including incomplete cycle06, remains unchanged.

One tools-disabled Fable review cost$0.21782825, bringing total cycle accounting
to$0.38410325. Its complete public memo was captured from assistant text blocks.
The review and ensuing next design are recorded
in the [integration](../../_sessions/cycles/2026-09-10-cycle07-review-integration.md).
That review cannot supply new empirical answers or turn the failed gate into a
positive dependence finding. Further research needs a separately frozen question;
this batch has reached its promised stop.

## Reproduce without provider calls

```bash
python3 evaluation/cycle07_program_errors.py validate --prepared results/cycle07-2026-09-10/prepared --manifest-sha256 7bad23c670b61b36d2bd17daf27ad83200dddc0f1088edc3035a26a36d933708
python3 _sessions/tools/check_cycle07_evidence.py --public-only
python3 -B -m unittest discover -s evaluation/tests
python3 -B -m unittest discover -s _sessions/tools/tests
```

The public-only audit explicitly cannot inspect ignored raw provider bytes.
Without `--public-only`, local raw streams are checked when present. Preparation
records the Python interpreter because AST serialization and execution are part
of the contract. The standard-library demo remains unchanged. Existing prepared,
observation and scored directories are exclusive; do not overwrite or resume the
closed collector. [Final checks](../../_sessions/evidence/2026-09-10-cycle07-checks.json)
record the current verification and preservation boundaries.
