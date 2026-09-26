# Cycle17 — post-failure observation on unchanged candidate support

This is a new, explicitly post hoc protocol after the original global-label
preservation experiment stopped. It does not turn that failure into a successful
original execution. The early outcome and the two globally removed grade0
records are known. No late effectiveness/contrast measurements have been
computed. The same30 topics are reused; no independent sample is created.

The [original protocol](2026-09-25-cycle17-exchange-protocol.md), all three
compatibility amendments, every failed attempt and the complete early result
remain unchanged. Opus5.5 reviewed the early result and assessed Buddy feedback
in the [synthesis memo](2026-09-25-cycle17-opus-synthesis-memo.md). Codex accepts
one cheap observation because the hybrid/source comparisons remain unresolved,
while primary M−H already excludes positive improvement.

## Hypothesis, scope and fixed measurements

**Hypothesis:** later compatible labels strictly narrow the finite-panel H−S
P@10 interval. H is the same simple hybrid and S the same source alone.
**Competing outcome:** later labels do not touch the unresolved support, so the
interval does not narrow. A narrowing need not determine its sign or justify a
new fusion policy. No minimum improvement or significance threshold is invented.

For each topic define the observation scope as the saved `hybrid_order`, exactly
its already frozen A100∪S100 candidate set. This set contains every displayed
document in A,S,H,M,J and is independent of early/late label values. Its policy
artifact must retain SHA256
`888b101919af30f36bc1d12d15c3c7c028bb42a017d71c417cf5bd02360a14cd`.
Load its bytes; never rebuild rankings or eligibility. No additional download,
model inference, judging, parameter choice or candidate selection.

Validate both full qrel files with the already recorded literal-ID parser.
Record global counts and removals, then restrict labels to that query's fixed
candidate scope. Require **every scoped early pair** to survive with exactly the
same grade. Any scoped removal/revision stops the new observation with a failure
artifact. The known two global removals have zero coefficients for all five
comparisons; preserve that fact explicitly instead of dropping the old failure.

Compute early and late analyses with the immutable original exact-Fraction
functions. The scoped early analysis must equal the prior complete full-label
analysis in **every field except `qrels_pair_count`**, which now counts only
labels inside the fixed candidate scope. This checks that the restriction has
not changed any metric, contrast, ledger, trigger or sign decision.

**Primary observation:** early-width minus late-width for H−S. Report its exact
endpoints, sign status and count of newly known labels on nonzero coefficients.
**Fixed descriptive observations:** the same quantities for M−H, M−J, M−S and
H−A; unknown-zero means for all five policies; exchange-category changes; total
and newly added labels inside the candidate scope. Global source-file counts
remain separate. M−H remains the original effectiveness primary, whose early
positive-improvement exclusion is not reset by this new observation priority.

Every per-query and aggregate late interval must nest in its early interval.
No missing-at-random assumption is made. Nonrandom later pooling can change the
unjudged-zero point; conditional bounds remain valid for every permitted binary
completion of the supplied grades. They are not confidence intervals or proof
that old document versions would receive the later grades.

## Execution, audit and stop

Freeze this protocol, new runner/tests and independent checker before the new
measurement. Bind all prior source identities, successful prepared/early
artifacts, final scoped input binding, late acquisition receipt, original global
failure/mismatch ledger and policy-preservation receipt. Verify raw input,
source, artifact and frozen policy identities before and after. The earlier
cookie-bearing receipts remain local; public custody checks can use their
sanitized counterparts with explicit limits on original-byte rehashing.

One execution, standard library,300seconds maximum; exclusive
`results/cycle17-2026-09-25/candidate-revelation/`. Save `early.json`, `late.json`,
`revelation.json`, `scope.json`, manifest and success/failure. Meaningful synthetic
checks cover inert outside-scope removal, failure on scoped grade changes,
nesting after added labels, invariant early outcomes and no policy rebuilding.
The independent implementation reconstructs every field from raw inputs and
the fixed policy contract. A different implementation is an arithmetic check,
not another effectiveness sample.

Stop after this one observation and assessed Opus review. If no interval narrows,
preserve that negative observation; if signs remain unresolved, do not declare
a tie or obtain labels merely to force a conclusion. No same-panel weight,
depth, eligibility, source-pair, boundary-feature or priority search follows.
A future experiment needs a distinct prediction and its own selection/evaluation
contract. The exact outcome of this late observation is currently unknown.
