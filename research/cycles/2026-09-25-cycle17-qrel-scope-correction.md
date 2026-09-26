# Cycle17 — tolerate inert off-inventory judgment records

The compatible preparation succeeded, freezing all policies before labels:
`policies.json` SHA256
`888b101919af30f36bc1d12d15c3c7c028bb42a017d71c417cf5bd02360a14cd`.
The subsequent early phase stopped at qrel line434 because its document ID was
absent from the official inventory. Preserve the
[failure](../../results/cycle17-2026-09-25/compatible/early/failure.json)
and all earlier sources/evidence unchanged. No comparison score was computed.

The [qrel syntax/universe audit](../evidence/2026-09-25-cycle17-qrel-universe-audit.json)
finds8691 early records, exactly30 topics, valid positive judgment rounds,
grades0/1/2 and no duplicate query/doc pairs. Exactly two IDs are outside the
inventory: `ccq171wm` on topic2 and `iu0k7rqc` on topic20. Neither is in any
frozen candidate union. Their cause is unknown; we do not remap them or infer
missing relevance for another document. This audit inspected qrel fields after
policies were frozen, without computing or choosing a policy outcome.

## Scope and mathematical effect

Allow a qrel's syntactically valid printable single-token document ID even if
that ID is not in the retrieval inventory. Preserve **every** qrel record,
grade and query pairing. All other qrel validation is unchanged. This solely
removes an unnecessary requirement on records that no evaluated policy can use.

The run parser still requires inventory membership; neither candidate sets nor
policies may expand. Thus every off-inventory qrel has zero coefficient in
every frozen metric/contrast. Its inclusion, exclusion or grade cannot alter
those values. Missing labels for actual retrieved candidates remain unknown;
this correction supplies none. It does not validate the official inventory's
completeness or repair the unusual source IDs.

The late phase still checks **all** early qrel records for exact grade retention,
including the two inert records. No removal/revision exception is added. Later
outside-inventory IDs likewise cannot enter any policy. Report input integrity
limits and off-inventory counts separately from performance.

## Frozen implementation and replay

Use the separately versioned `evaluation/cycle17_scoped_labels.py` atop the
immutable compatible adapter. It validates literal qrel ID syntax, temporarily
extends **only the qrel parser's validation set** with those literal tokens,
and reuses all original field/cohort/grade/duplicate checks. It does not change
the run parser's universe, policy builder, contrast calculation or late-phase
preservation logic. Synthetic tests verify these boundaries and that inert
judgments cannot change any policy metric or signed interval.

The independent scoped-label checker uses its own parser and the same explicit
scope, without importing the primary algorithm. Pin both new sources/tests,
this amendment and audit, the prior compatible preflight/binding, the successful
compatible prepared policies/manifest/success, and the failed early artifact.
The scoped initial binding preserves all original input hashes and makes no
new network request.

Write final phases to exclusive
`results/cycle17-2026-09-25/final/{prepared,early,late}`. Before joining labels,
require final policy bytes to equal the already frozen successful compatible
policy hash above. This verifies that the correction after qrel exposure did
not change a candidate, rank, trigger or policy. Only after early success fetch
the still-unseen late qrels under the original plan. All other protocol gates,
five comparisons and the two-phase stop remain in force.

Original HTTP receipts captured transient response cookies. Preserve their
frozen bytes locally under exact Git-ignore entries; publish separate sanitized
counterparts with original SHA256 and the same input identities. They are not
rewritten to satisfy prior hashes. The next acquisition reuses the frozen HTTP
gates through `acquire_cycle17_public_inputs.py`, which retains only explicitly
allowed public response headers. Pin that wrapper and its sanitizer here as
well. No credential, cookie or raw provider transcript belongs in the checkpoint.
Full historical runtime-custody replay needs those local original receipts;
public copies retain all input identities and consequential transport checks.
