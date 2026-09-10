# Cycle04 execution contract — frozen before implementation

2026-09-10. Executes the six-cell [design](2026-09-10-cycle04-known-truth-design.md)
preserved at Git commit `44869862be44178ebeedc132bc662ee436e84a6b`.
Design SHA256: `319827f9bae8d902318f34d79f7d8cfdb67a0a917f9e57c0894f2517ce7b3d7b`.
This supplement resolves representation and evidence-access details; it changes
no factors, comparator, metric, or stopping rule. A bounded independent design
review found no conceptual contradiction and identified the leakage channels
closed below. No outcome metrics were calculated before this contract.

## Packet and evaluator separation

The blind policy input contains exactly the four ordered report slots, their
roles (three generalist slots, then specialist), payloads in `{−1,+1,null}`,
and unique opaque report IDs. Shared model parameters include the prior,
reliabilities and equal construction mixture described in the design.
Neither actual arm, truth, primitive-variable names, unobserved readings,
acquisition count nor result-row metadata may reach a blind policy. Acquisition
counts are evaluator-only: revealing two versus four acquisitions would reveal
the copy/independent distinction. Aware policies add only the observed root
partition. All aware policies share that same additional information.
The recorded cost counts primitive readings only. Trusted provenance is supplied
without a modeled acquisition cost; this is not an equal-total-cost comparison.

Use constant positional report IDs within the experiment, independent of arm,
payload and truth. They communicate only already-visible slot identity; they
are placeholders for opaque labels, not a measured random feature. Do not
perform a stochastic ID experiment. Renaming report IDs is an invariant test.
Root IDs are opaque equality labels. Canonicalize them by first occurrence in
the packet; the actual spelling is immaterial. Null slots have no root. Thus
padded, copied and independent partitions are respectively `(0,null,null,1)`,
`(0,0,0,1)` and `(0,1,2,3)`. Revealing equality is the intended information
treatment; arbitrary root labels reveal no extra truth information.

Return only the probability of positive truth from each policy. The evaluator
retains latent worlds and resource counts separately. An exhaustive blind
conditioning table may internally represent the specified latent model, but
its lookup key contains only visible payload/role information. It may never
select a table using the realized arm. Aware lookup additionally uses the
canonical partition. Identical admissible observations yield identical outputs.

## Exact arithmetic and evidence

Enumerate `(Y,G1,G2,G3,S)` in lexicographic order over `(-1,+1)^5`, for
`pS=11/20,17/20`, then padded/copied/independent arms in that order. Each
cell has 32 rows whose exact probability mass sums to one; the six cells have
192 rows. Unobserved potential readings are marginalized, not supplied to
policies or charged as acquisitions. The known arm mixture weights are `1/3`.

All model probabilities, policy probabilities, Brier loss, expected error,
correction and harm use `fractions.Fraction` or equivalent exact arithmetic.
Serialize rational values as canonical strings such as `"0"`, `"1/2"`, `"1"`;
decimal formatting belongs only in presentation. No seed, bootstrap, estimated
interval, Monte Carlo, fit, parameter selection or additional cells are used.

For each world and comparator, record probability, Brier loss, expected error,
and correction/harm relative to optimal blind Bayes. Correction means blind
wrong and comparator right; harm means blind right and comparator wrong.
Enumerate one common fair tie coin for both decisions. Retain all rows, each
cell's exact weighted aggregates, and equal-arm mixture aggregates separately
for each known specialist reliability. Preserve signed aware-minus-blind Brier
and error gaps; improvement is negative. For each comparator the identity
`correction - harm = error(blind) - error(comparator)` must hold exactly.

Record probability-change count and weighted mass for padded-to-copied pairs,
with the identical primitive world on both sides. Aware Bayes and equal-root
weighting must remain invariant. Other changes are diagnostic, not automatically
faults: optimal blind Bayes rationally conditions on a changed observation.

## Verification and run custody

Before the durable experiment, run meaningful synthetic/structural tests of
mass normalization, closed-form versus enumerated conditioning, information
access, ID renaming, sign symmetry, copy invariance and shared tie handling.
After the run, an independent implementation must rebuild all world weights,
observations, policy outputs, aggregates and correction/harm from the contract
without importing production experiment code. Check the two Bayes policies by
direct finite-table conditioning; check blind comparator optimality on the
equal mixture and aware conditional optimality. A discrepancy blocks claims
until resolved and documented.
Also verify the conditional-expectation identity between the two Bayes policies
and the exact mixture Brier identity
`loss(blind) - loss(aware) = E[(p_aware - p_blind)^2]`.
Blind and aware posteriors coincide on padded and mixed-sign generalist packets;
only unanimous non-null generalist packets leave lineage ambiguous. These are
structural arithmetic checks on the stated model, not new selected endpoints.

Use a fresh immutable output directory. Save exact argv, UTC times, Python/Git
state, protocol/design/code/test SHA256s before and after execution, numerical
output hashes and an explicit complete or invalid manifest. Never overwrite a
prior result. Preserve cycle01–03 protocols, inputs, code and numerical evidence.
The independent reconstruction and review receipts are separate artifacts.

## Interpretive checkpoint

The existing analytic predictions are calibration checks, not discoveries.
Read every comparator and unfavorable cell. A blind Bayes policy can lose
within a hidden arm while remaining optimal for the specified mixture.
Report separately the information benefit of trusted lineage, the effect of
additional independent acquisitions, and poor use of already available inputs.
Known source reliability is an idealized truth anchor; dissent does not supply it.

Stop after six cells, independent arithmetic review, one bounded Claude review
and a recorded next empirical observable. The Claude phase uses a compact fresh
coordinator with necessary project context, the existing pinned models, one
read-only scout and the same $4 native invocation cap; no full prior transcript
is needed for this fixture. Dave reported the provider allowance reset, but
this does not remove the invocation cap or authorize automatic retries.
No real-agent benchmark, retrieval sweep or novelty claim is part of this run.
