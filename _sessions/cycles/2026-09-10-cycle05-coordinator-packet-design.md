# Cycle05 design — can a coordinator use the supplied evidence model?

Selected after cycle04 review. **Design only; no model requests or scores yet.**
The alternative common-cause run was retired because its numerical distribution
is already contained in cycle04. This first empirical step has an outcome the
exact fixture cannot determine: the probabilities an actual coordinator returns.

## Question and bounded claim

Given the fully specified cycle04 sensor model, does one coordinator correctly
use calibration and copy lineage, marginalize when lineage is hidden, and avoid
automatically favoring a minority? This tests behavior under supplied assumptions.
It does not estimate real source reliability, independence, general reasoning
ability, retrieval quality, or a multi-agent collaboration advantage.

Use the existing [exact cycle04 evidence](../../results/cycle04-2026-09-10/exact/summary.json)
as the reference. The experiment supplies reports directly; no proposer agents
generate them. Truth and desired probabilities never appear in request payloads.

## Fixed diagnostic inputs

Include every padded/copied/independent packet in which all observed generalist
values agree and oppose the specialist, at both known pS values 11/20 and 17/20,
and both global sign orientations. There are 12 distinct aware observations.
The copied and independent blind observations coincide, leaving eight distinct
blind observations. **Twenty unique requests maximum.** Reuse the same blind
response for identical observations; do not count copies as independent trials.

Each request receives uniform truth prior, generalist accuracy 7/10, its known
specialist accuracy, the full conditional-independence/error model, the three
construction definitions and equal construction prior. Show four ordered roles,
payloads/nulls and fixed opaque report IDs. Aware requests add the canonical root
partition. Hide arm, acquired-reading count, latent truth and unobserved readings
in blind requests; aware requests gain only the partition. The prompt must
explain that nulls reflect padding and that reports sharing a root repeat one
reading. Ask only for a JSON probability of positive truth.

Before execution, freeze the exact request templates, all 20 serialized payloads,
request order, reference conditional probabilities and weighting table with
SHA256 identities. The execution protocol must verify that no reference answer
or evaluation-only field enters a provider request. Prepare a fixed shuffle with
seed42 before any response; preserve the resulting order as an artifact.

## Model, context and capacity

Use one pinned `claude-opus-5` configuration at explicit high effort. This is the
workhorse measurement; do not switch to Fable after seeing misses. All requests
have the same output ceiling and no tools, subagents, MCP, retrieval or access
to this repository's answers. Use isolated fresh contexts, with a shared fixed
prompt, rather than a sequential conversation that can learn from prior cases.
Check effective native context controls locally before freezing the launcher.
An isolated temporary working directory can keep project instructions/results
out of automatic context; do not change global provider settings.

Set a 500-output-token target and a $4 native-accounting scheduling ceiling for
the whole batch. Verify what the installed native client counts as output,
including reasoning, and freeze enforceable controls before the first request.
Track input, cached input, output, reasoning where supplied, wall time, observed
canonical model, stop reason and native cost for each call. Do not describe a
provider's post-call budget guard as a hard billing guarantee. Stop scheduling
when the batch allowance is exhausted, account for any single-call overshoot,
and preserve an incomplete batch. No retries, replacement responses, model
fallback, prompt search, extra billing settings or automatic budget increase.

Twenty independent native invocations are not twenty collaborating agents. The
12-aware/8-blind unique request counts and additional metadata tokens differ;
report their actual costs. Identical per-request ceilings do not imply equal
total compute. A one-packet canary, if useful, must be the first frozen request
and remain in the dataset, not an extra tuning call.

## Outcomes and interpretation

Primary: each view's conditional excess Brier loss against its **own** exact
Bayes posterior on the fixed diagnostic set, reported separately for each known
specialist reliability. For a returned probability p and reference q, conditional
regret is `(p-q)^2`. Weight observations by their exact cycle04 generator mass,
conditioned on inclusion in this diagnostic set; normalize separately by pS.
The same underlying diagnostic worlds define both blind and aware comparisons.
Reuse blind outputs across compatible worlds when evaluating the paired change.
This is conditional diagnostic performance, not the full six-cell benchmark.

Also report the actual aware-minus-blind expected Brier difference on those
same cases, separating ideal information value from the model's approximation
error. Report every probability, absolute posterior error, sign decision,
sign symmetry and padded-to-copied probability change. Known-lineage copied
and independent disagreement packets have different reference posteriors;
equal outputs on them reveal insensitivity for those observed requests, not
an impossibility of lineage use in other contexts.

Parse a strict JSON object with one finite numeric `p_positive` in [0,1]; reject
duplicate/extra keys, explanations or malformed output. Preserve raw native
responses privately and durable extracted predictions/usage/failure metadata.
Do not repair, retry, coerce or impute invalid probabilities. Report coverage and
failure types. The full primary result is defined only if all 20 requests yield
valid probabilities; otherwise mark it incomplete and label any valid-subset
summaries as descriptive, with their changed denominator explicit.

No arbitrary 9-of-12 success threshold or ±.05 tolerance is adopted as a test of
general reasoning. Continuous errors, probability contrasts, malformed outputs
and resource use are the measurements. Expected relationships from cycle04 are
explicit predictions: calibrated aware probabilities are copy invariant; strong
S defeats copies but loses to independent unanimous generalists; weak S loses
both conflicts; the blind strong-setting rule already follows S. Departures
identify behavior on these exact requests, not a general model capability.

## Stop and next decision

Stop after this one model/prompt/order, up to20 requests, scoring and independent
review. No confidence interval can be justified by treating deterministic
packets or reused blind responses as repeated model samples. One response per
unique packet does not characterize model stochastic variability, prompt
sensitivity or provider/model drift. Later replication must be a separately
frozen design, not retries hidden inside this run.

If outputs follow the supplied model, next ask what happens when calibration or
metadata must be learned or are wrong. If they fail, distinguish parsing/context
failures, posterior approximation, and unsupported minority rescue before
proposing more agents. In either case the existing report and exact outputs
remain valid. The coordinator freezes the execution contract before any call;
the current cycle ends with this design, not an empirical performance claim.
