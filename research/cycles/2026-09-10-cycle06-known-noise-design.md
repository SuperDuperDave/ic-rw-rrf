# Cycle06 design — using uncertainty about provenance

**Prospective design only; no cycle06 model requests.** Selected after the
cycle05 replication and Fable interpretation review. The fixed coordinator
calculated essentially correct posteriors when calibration and lineage were
supplied exactly. Change the quality of supplied evidence before adding agents.

## Question and distinguishing prediction

Does the same coordinator marginalize a precisely specified uncertainty in a
lineage hint, rather than treating the hint as verified provenance or ignoring
it entirely? This tests use of disclosed uncertainty. It does not test discovery
of hidden dependence, estimation of calibration, real cabal detection, or the
reliability of metadata extraction.

Retain the cycle04 binary truth/sensor/construction law. Padded construction is
identified by nulls and remains an analytical check only. On non-null packets,
the true construction A is copied C or independent I, with prior1/2 each before
conditioning on readings. Supply a binary hint H with
`P(H=A | A)=3/4` and `P(H≠A | A)=1/4`, independent of truth and primitive readings
conditional on A. Do not apply an unspecified “flip” to all three constructions:
a binary channel at error1/2 is uninformative; that claim is not automatically
true for a three-class channel.

All model inputs disclose this full channel and the original calibration model.
The actual construction, root partition and truth remain hidden. The hint is
explicitly a noisy observation, never a trusted `parent_partition` field. Keep
the original opaque report IDs and role/value arrangement, with no evaluation
answers or metadata in requests.

Take exactly **eight unique inputs**: both specialist accuracies × both global
sign orientations × both hint values, with all three generalists agreeing and
opposing S. The physical true construction is latent, not another model input.
No padded requests, additional error-rate grid, clean-setting rerun, hidden-flip
arm, second prompt, or proposer-agent wave belongs to this experiment.

## References and predictions

For positive generalists and negative specialist, let
`aC=.7(1-s)`, `bC=.3s`, `aI=.7³(1-s)`, `bI=.3³s`.
For hintC use weights `(wC,wI)=(3/4,1/4)` and for hintI `(1/4,3/4)`.
Then `qH=(wC*aC+wI*aI)/(wC*(aC+bC)+wI*(aI+bI))`.
Reverse signs give complements. The weights are the channel likelihoods with
equal construction priors; do not skip the further likelihood update from
the observed agreement pattern.

Use augmented-generator frequencies, not equal hint-cell weights. For each sign,
normalized diagnostic weights are weak `(1341/4328,823/4328)` for `(hintC,hintI)`
and strong `(481/1448,243/1448)`. Both signs together sum to one at each
reliability. The unconditional non-null disagreement masses are541/2500 and
181/1250 respectively. Independent reconstruction from the original cycle04
world rows verifies these analytical weights.

| Specialist | Correct q, hintC | Correct q, hintI | Naively trust hintI |
| --- | ---: | ---: | ---: |
| 55% | 2443/3576 | 5187/6584 | 343/376 |
| 85% | 2443/7696 | 1729/3888 | 343/496 |

These are **analytical design predictions**, independently checked before
implementation, not model outcomes. At85%, trusting hintI yields probability
about.6915 and follows the positive generalists; the correct noisy posterior is
about.4447 and follows S. Exact blind is about.3602 and also follows S, so class
agreement cannot establish that the coordinator used the hint. Continuous
probabilities must distinguish correct uncertainty use from ignoring the hint.

Check analytically that error0 recovers the trusted-lineage reference and
error1/2 recovers blind. These are boundary checks, not extra empirical cells.
No finite parameter sweep or post-result threshold selection is needed.

## Measurement, resources and stop

Primary: conditional excess Brier `(p-qH)^2`, weighted by the exact augmented
generator mass on non-null disagreement packets and hints, separately by known
specialist accuracy. Freeze all eight payloads, exact references/masses, canonical
serialization, seed42 order, source hashes and scoring before any response.
Strong comparators: the exact noise-aware posterior, exact blind posterior, and
the deliberately naive hint-as-truth posterior. Report their direct expected
Brier on the same worlds, model-to-reference distances, sign decisions and sign
symmetry. Closeness to one reference is descriptive, not a majority-vote success
criterion. No arbitrary tolerance certifies a general ability.

Reuse the verified native workflow and strict terminal-only JSON interpretation,
with the zero-agent-counter regression gate. Pin the exact model ID and the
inspected native executable version/hash, with high effort, fresh empty contexts,
no tools/MCP/agents,500 output tokens per API
response including thinking,120s per invocation,300s total batch wall and$1
native-accounting scheduling allowance. Recheck installed version/context
controls before freezing the launcher; preserve native continuations and cost
limitations. Stop on the existing native/configuration/unknown-cost boundaries,
with no application retries or automatic repair batch. Full primary needs all
eight valid outputs; otherwise retain incomplete coverage and explicit valid
subset denominators without imputation.

Stop after this one fixed batch, scoring and independent review. If probability
estimates again follow the supplied model, the next research investment should
move toward obtaining calibration/dependence evidence or pricing an additional
observation. If they do not, inspect the finite errors and formatting/compute
evidence before proposing a mechanism. Do not inflate the same calculation into
a large agent swarm or infer model-repeat uncertainty from eight chosen inputs.
