# Cycle07 preparation — observe errors before modeling dependence

**Prospective feasibility design, not an execution freeze.** No task generator,
item set, provider configuration, or cycle07 response exists under this protocol
yet. This turn prepares the next checkpoint only; it does not launch providers
or repair the incomplete cycle06 batch.

The [cycle06 design](2026-09-10-cycle06-known-noise-design.md) asked a coordinator
to use a fully disclosed probability model. Its [frozen scores](../../results/cycle06-2026-09-10/scored/scores.json)
contain three valid responses, one rejected invocation and four unsent inputs;
the full primary is absent. Close that result with its coverage and observer
qualifications. The [interpretation-review mission](2026-09-10-cycle06-review-mission.md)
opens a different question: can we obtain useful observations of actual errors
on tasks whose answers we can verify?

## Question, prediction and first stopping point

**Question:** On a small fixed set of short program-evaluation tasks, do two
separately invoked solver roles produce truth-anchored joint errors and any
correct dissent? Neither role is assumed more accurate or statistically
independent. The role called S below is an *audit-prompt role*, not an established
specialist.

**Working hypothesis:** this family supplies some correct and incorrect answers
and some disagreements, allowing an initial error table to be observed.
**Distinguishing observation:** a valid G-wrong/S-right pair demonstrates one
available correction to G; a G-right/S-wrong pair demonstrates potential harm.
Both-wrong agreement is directly visible against verified truth. Perfect
accuracy, identical answers, absent required denominators, or collection failure
are informative feasibility outcomes, not evidence of general impossibility.

The first checkpoint is **eight development items, two solver roles each: at
most 16 unique invocations**. It ends after collection, offline scoring and
independent verification, even if its feasibility gate passes. Sixteen additional
items are reserved before calls and remain unsent at this checkpoint. There is
no coordinator, fusion policy, model sweep or answer-exposure arm in this first
batch. One answer per role/item is one observation; provider continuations are
part of that invocation, not extra experimental samples.

## Prepare and seal tasks before observing any response

Implement this preparation separately with the standard library. Use two
prespecified strata of deterministic, terminating integer programs:

- **Sequential state:** 8–14 executable lines, scalar assignments and up to two
  conditionals whose later updates depend on earlier state.
- **Bounded loops:** 8–14 executable lines with one loop over a literal range of
  3–6 iterations, scalar updates and at most one conditional inside the loop.

Use only integer constants, variables, `+`, `-`, `*`, positive-literal `%`,
comparisons, assignment, `if` and the stated bounded loop. No input, imports,
functions with side effects, filesystem, randomness, floats, recursion or
unbounded execution. Each item ends in an explicit Boolean predicate of the
final state. The question supplies the entire program and asks whether that
predicate is true. Bound intermediate integer magnitude and program step count
in the generator's acceptance checks; freeze those numeric bounds and the exact
grammar before enumerating candidates. No claim that these lengths are hard
enough is made in advance.

Before any provider request, make **24 distinct structural templates**, with six
accepted items in each `(program stratum, truth)` cell. Deduplicate normalized
control/data-flow templates, not just rendered strings; parameter changes,
variable renamings and a predicate/complement pair must not cross splits as
apparently new templates. Retain the first accepted candidates under a frozen
generator order; do not hand-select plausible model failures. Set a maximum of
1,000 candidate attempts, record exclusions and stop preparation if the required
cells cannot be filled. Candidate acceptance may depend on truth verification
and the declared syntax limits, never on model responses.

Shuffle template IDs within each cell with seed42, then allocate two per cell
to development and four per cell to the reserved set. Thus development contains
eight items, four per truth, and the reserved set contains 16, eight per truth.
This deliberately balanced construction defines the finite task distribution;
it does not estimate natural program or truth prevalence. Both strata receive
equal item weight. No later replacement of difficult, easy or invalid-response
items is allowed.

Verify every truth **two ways**: execute the generated allowlisted program under
a pinned Python interpreter, and evaluate its syntax/state transitions with an
independently written small evaluator. Preserve exact source, AST, final state,
predicate, outputs and both checker identities. A second person/agent audits the
grammar and independently reconstructs all 24 Boolean answers. The checkers must
not share the state-update implementation. Disagreement blocks launch and is
resolved before sealing; provider answers never decide truth.

Freeze a manifest containing all candidate/item bytes and hashes, truth records,
template families, split membership, seed and actual order, exclusion reasons,
generator/checker revisions and exact preparation commands. Keep reserved items
out of provider prompts and outcome-based prompt/task development. Their truth
verification is not a solver outcome; any later inspection used to revise the
task design retires the affected reserve as development. Do not describe this
document itself as that completed freeze.

## Solver configurations and matched observations

G and S receive identical code and answer schema in separate fresh contexts.
Their instruction templates differ only by the declared role instruction:

- **G:** evaluate the supplied program and answer the final Boolean question.
- **S:** check sequential updates, loop bounds and branch conditions when
  evaluating the supplied program, then answer the final Boolean question.

Both return only `{"answer": true}` or `{"answer": false}`. Request no internal
reasoning, confidence score, supplied calibration or lineage inference. Freeze
the complete actual prompt bytes before calls, including the common framing and
format requirement. Use the same verified exact model ID, effort, output limits
and native context controls for both roles. This first comparison concerns a
prompt intervention under one workflow; a second model would introduce another
factor. No designated cheap model or price ratio is assumed here.

Use empty fresh working contexts, no history, tools, MCP or subagents, and no
project/Relay research material in experimental prompts. Never feed G's answer
to S in this batch. Fresh context establishes the absence of supplied shared
conversation history; shared training, task difficulty, deterministic behavior
or other common causes may still align errors.

Prepare the eight-item order before launch with seed42. Within each truth/stratum
cell, assign one item's G invocation first and the other item's S invocation
first, with the assignment frozen before responses. Keep the two calls for an
item adjacent and execute serially. This bounds order confounding and keeps
partial coverage interpretable; it does not create independent statistical
samples. Do not obtain additional draws to replace an inconvenient answer.

## Exact observables and denominator gate

On each valid pair let `Y` be verified truth and `E_G`, `E_S` indicate a wrong
Boolean answer. The **primary observable** is the joint count table
`n_y(a,b) = count(Y=y, E_G=a, E_S=b)`, with all eight cells and denominators
`N_y = sum_ab n_y(a,b)` printed, including zeros. Also print these tables by
program stratum; do not pool away a visibly concentrated failure type.

On the same valid paired set, report the following descriptive quantities:

| Quantity | Definition and named comparison |
| --- | --- |
| G error / S error | `(n10+n11)/N` / `(n01+n11)/N`, summing over truth |
| Disagreement | `(n10+n01)/N`; binary disagreement means exactly one role is correct |
| Available corrections to G | `n10/N`; conditional correction `n10/(n10+n11)` |
| Potential harm relative to G | `n01/N`; conditional harm `n01/(n00+n01)` |
| S-minus-G error | `(n01-n10)/N`; substitution of S for G, not a fusion result |
| Joint-error excess by truth | `C_y=n_y(1,1)/N_y - e_G,y*e_S,y`, where both marginal errors use that same `N_y` |

An undefined ratio is `null` with its zero denominator. `C_y` is a descriptive
departure from the product of panel marginal errors; it is **not** a test of
independence conditional on the full task. Conditioning on truth does not remove
heterogeneous item difficulty. One draw per role/item cannot distinguish a
shared task effect from other sources of dependence. The stratum tables describe
that limitation but do not solve it. No p-value, correlation significance,
calibration estimate or population performance claim belongs to eight items.

The full primary needs all eight valid pairs. Preserve all attempted responses,
including a valid unpaired answer, and distinguish invalid from unsent. If the
batch stops, the full primary remains `null`; any partial table explicitly names
its selected valid-pair denominator and cannot stand in for the planned panel.
Invalid format, truncation and refusal are collection outcomes, not imputed
mathematical errors.

The **observability gate** for considering a later intervention is: complete
eight-pair collection; at least one G error and one G correct answer; at least
one S error and one S correct answer; and at least one disagreement. These are
minimum nonzero denominators/variation for the proposed correction, harm and
error-dependence questions. They are not a target error band, evidence of a
material effect, a precision guarantee, or a power calculation. Print the actual
counts; a denominator of one is fragile. All-zero-error or all-agreement panels
are still valid descriptive outcomes, but do not justify spending on that
panel's exposure comparison. Correct dissent may be absent even when this gate
passes; report that fact rather than adding it as a post hoc pass requirement.

## Resource contract and failure boundary

Before launch, verify available model identities, native executable/version,
context isolation, activity/fallback/refusal observation, continuation semantics
and current cost accounting. Resolve the one role-to-model mapping then and
record requested and observed IDs; do not infer availability or price from a
model's self-description. [CLAUDE_COMPUTE](../CLAUDE_COMPUTE.md) provides the
existing project contract, whose launch-relevant facts must be checked then.
The cycle06 observer correction must have independent regression evidence;
do not reinterpret its frozen scores as if a future parser produced them.

Prospective ceiling for this new development batch: **16 unique invocations,
$1 native-accounting scheduling allowance, 300 seconds total wall time,
120 seconds per invocation and 500 output tokens per API response including
reported thinking**. Confirm those controls' actual meaning at launch. Multiple
native messages can occur within one invocation; the 500-token response ceiling
is not an aggregate invocation token guarantee. State whether the current
runtime can enforce a spend bound or only report it after a response. Do not
launch when reliable cost observation is unavailable; do not label a scheduling
allowance a hard invoice cap.

Record attempts, provider-message counts, usage/cache categories, native costs,
elapsed times and any unobserved fields. Sum realized acquisition cost across
both roles, including failures; report cost per valid pair only with its
denominator and total attempted cost alongside it. Native list accounting is
not subscription billing. The local truth-checking work has its own measured
wall time. No price-efficiency conclusion follows without the actual cost
mapping and observed outcomes.

Stop scheduling immediately at the first native error/refusal, unexpected model
or activity, unknown cost, invalid terminal output, truth/custody discrepancy,
or resource boundary. Preserve the reason and already collected observations;
no retries, prompt changes, fallback providers or automatically raised limits.
Do not spend reserved-item calls to compensate for incomplete development.

## Conditional next step, requiring its own freeze

At the development checkpoint, stop and decide using the recorded counts.
Failure of the observability gate parks this task/role configuration; a revised
family or prompt requires a new development design and a fresh untouched reserve.
Passing permits consideration of one answer-exposure experiment, not automatic
launch or a claim that the task family is adequate for effect estimation.

The candidate follow-up uses each untouched item to acquire G once and two
fresh S contexts: **S-blind** receives the task alone; **S-exposed** receives that
same task plus the actual G answer, labeled as an unverified other solver answer.
The audit instruction/model/resources remain matched; counterbalance the order
of the two S calls before outcomes. G's answer must exist before either S call,
and no truth or correctness label is supplied. Each item supplies one paired
exposure contrast; it does not contribute three independent task samples.

Prespecify exposure-minus-blind S error, harmful/correcting answer transitions,
and their denominators conditional on G correctness. A larger `C_y` alone cannot
identify harmful answer copying: exposure can also change marginal accuracy,
and item difficulty still matters. Simply setting `S_copy=G` offline establishes
a deterministic duplication identity with zero new acquisition; it is **not** an
empirical exposed-agent arm. Defer random/wrong-answer exposure, repeated draws,
extra models, learned routing and fusion to a separately justified question.

Before any reserved-item calls, freeze that follow-up's exact metrics, prompt
templates, item/role order and total budget. If development prompts or task
definitions change, do not reuse the reserve as untouched evidence. Even an
unchanged reserve tests new items under this chosen family and configuration;
it does not establish cross-domain transfer or novelty.

## Rationale and handoff

This design replaces supplied probabilities with externally checked answers,
shrinks the first empirical decision to 16 invocations, and preserves a reserve
without committing to a large treatment sweep. It separates fresh contexts,
copied outputs, actual answer exposure, and statistical dependence. Minimum
observable counts replace an arbitrary `.15–.5` error target; neither counts nor
a gate are evidence of a useful effect.

Next authorized local work is generator/checker preparation, an independent
truth and leakage review, and an execution freeze. No provider calls or code
implementation are part of this document's preparation. The coordinator owns
the shared research map, backlog, stream and any eventual launch decision.
