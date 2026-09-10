# Cycle04 — what evidence origin changes, and what it does not

The six-cell known-truth fixture is complete. Trusted lineage improves exact
Bayesian probability estimates under the stipulated model. With weak specialist
calibration the improvement changes no classifications; with strong calibration
it reduces mixture error from 15% to 14.05%. Unconditional minority protection
increases Brier loss in both settings and adds classification error when the
specialist is weak. These are expected properties of a deliberately constructed
model, not measured LLM gains or a new aggregation algorithm.

[Figure PNG](known_truth.png) · [Exportable SVG](known_truth.svg) ·
[Exact summary](exact/summary.json) · [All 192 rows](exact/per_world.json) ·
[Manifest](exact/manifest.json) ·
[Independent reconstruction](../../_sessions/evidence/2026-09-10-cycle04-independent-check.json)

## Why this experiment

Cycle03's frozen decision rule stopped an inconclusive specialist association
on retrieval development data. We changed laboratories to separate truth,
copy identity, corroboration and calibration. The original curiosity remains:
when is a minority useful, and when does agreement merely repeat evidence?
[Prior result](../cycle03-2026-09-10/REPORT.md)

The [design](../../_sessions/cycles/2026-09-10-cycle04-known-truth-design.md)
was preserved in the preceding GitHub checkpoint. An independent review caught
an information leak before implementation: acquisition counts would reveal the
hidden construction. The [execution protocol](../../_sessions/cycles/2026-09-10-cycle04-execution-protocol.md)
freezes evaluator-only counts, opaque labels, exact arithmetic and stopping.
No factor, comparator or threshold was selected after the outcomes.

## The controlled model and its information costs

Uniform binary truth generates three conditionally independent generalists of
70% symmetric accuracy and a specialist of either 55% or 85% accuracy. Enumerate
all 32 assignments exactly for each known specialist setting. Each primitive
world feeds three report constructions:

| Construction | Reports | Acquired primitive readings |
| --- | --- | ---: |
| Padded | G1, null, null, S | 2 |
| Copied | G1, G1, G1, S | 2 |
| Independent | G1, G2, G3, S | 4 |

All have four report slots and a four-acquisition ceiling. The independent arm
intentionally supplies more evidence. Comparators receive identical packets
within a cell; the actual arm, truth and costs are hidden from policies. All
know the source accuracies and equal construction prior. The two aware methods
add the true root partition, supplied without a modeled acquisition cost.
Neither total cost nor information is matched across blind and aware methods.
Report/root names themselves carry no truth information.

Optimal blind Bayes marginalizes over the hidden construction. Optimal aware
Bayes uses each observed root once; this product is correct because distinct
primitive errors are conditionally independent **by construction**. Equal-root
weighting ignores reliability differences. Payload quotient merges identical
generalist answers even when they are separate acquisitions. Protected minority
returns the specialist-only posterior when all three generalist reports agree
against it, and otherwise uses optimal blind Bayes.
All three must be non-null: padded packets have one generalist reading and
cannot activate the protected-minority trigger.

## Primary mixture result

Brier loss is the squared error of the probability assigned to positive truth;
lower is better. Each mixture weights the three arms equally, separately for
the two known specialist reliabilities. These are exact expectations, with
canonical rational values saved in JSON; decimals below are display rounding.
There is no sampling uncertainty or confidence interval within this finite model.

| Policy | Weak S: Brier | Weak S: error | Strong S: Brier | Strong S: error |
| --- | ---: | ---: | ---: | ---: |
| Naive report independence | 0.208228 | 27.200% | 0.128371 | 19.050% |
| Payload quotient | 0.205467 | 30.350% | 0.115152 | 15.000% |
| Optimal blind Bayes | 0.195518 | 27.200% | 0.112002 | 15.000% |
| Equal root weighting | 0.226250 | 33.775% | 0.128750 | 20.625% |
| Optimal aware Bayes | 0.190872 | 27.200% | 0.108500 | 14.050% |
| Protected minority | 0.211643 | 36.850% | 0.118397 | 15.000% |

The primary signed difference is **aware minus optimal blind**, not versus naive
report independence. Negative is improvement:

| Known specialist accuracy | Exact Brier difference | Decimal Brier difference | Error difference |
| --- | ---: | ---: | ---: |
| 55% | `-44463497925/9568568217728` | -0.004646829 | 0.000 percentage points |
| 85% | `-104346390575/29794502648832` | -0.003502203 | -0.950 percentage points |

The weak-setting probability improvement changes **no individual class decision**.
The strong-setting classification improvement comes entirely from the independent
arm: aware error is 12.15%, versus blind 15%. Aware and blind already agree on
which class to choose in padded/copied arms. The 2.85-point independent-arm gain
becomes 0.95 points under the equal mixture.

Here the blind Bayes class rule is simple: it always chooses S in the strong
setting, and the observed generalist majority in the weak setting. Its full
probability estimates still use the supplied model. Accuracy therefore misses
some meaningful probability changes. The aware-versus-blind class difference
occurs only when independent unanimous generalists oppose strong S; these fixed
accuracies were chosen to produce that ordering, not discovered to improve an
actual coordinator. Other diagnostic policies can differ on other patterns.

This is an information-value comparison under known assumptions. The exact
identity `Brier(blind) - Brier(aware) = E[(p_aware - p_blind)^2]` holds in both
settings. It follows by expanding the squared loss and conditioning on the
richer observation: the cross term is zero because its posterior equals the
conditional mean of truth. Thus the optimal richer-information policy has a
nonnegative expected benefit; observing that fact here is a calibration check,
not a new theorem or learned policy improvement.

## All six cells

A mixture-optimal blind rule may lose within an arm whose identity it cannot
observe. Such a per-arm loss is not evidence of a faulty Bayes calculation.
Every policy, including unfavorable comparisons, appears below.

### Expected Brier loss

| S / construction | Naive report independence | Payload quotient | Optimal blind Bayes | Equal root weighting | Optimal aware Bayes | Protected minority |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 55% / padded | 0.208233 | 0.208233 | 0.208233 | 0.255000 | 0.208233 | 0.208233 |
| 55% / copied | 0.260301 | 0.208233 | 0.211970 | 0.255000 | 0.208233 | 0.230252 |
| 55% / independent | 0.156148 | 0.199934 | 0.166353 | 0.168750 | 0.156148 | 0.196443 |
| 85% / padded | 0.116211 | 0.116211 | 0.116211 | 0.135000 | 0.116211 | 0.116211 |
| 85% / copied | 0.175823 | 0.116211 | 0.118104 | 0.135000 | 0.116211 | 0.123641 |
| 85% / independent | 0.093078 | 0.113034 | 0.101691 | 0.116250 | 0.093078 | 0.115340 |

### Expected classification error

| S / construction | Naive report independence | Payload quotient | Optimal blind Bayes | Equal root weighting | Optimal aware Bayes | Protected minority |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 55% / padded | 30.000% | 30.000% | 30.000% | 37.500% | 30.000% | 30.000% |
| 55% / copied | 30.000% | 30.000% | 30.000% | 37.500% | 30.000% | 45.000% |
| 55% / independent | 21.600% | 31.050% | 21.600% | 26.325% | 21.600% | 35.550% |
| 85% / padded | 15.000% | 15.000% | 15.000% | 22.500% | 15.000% | 15.000% |
| 85% / copied | 30.000% | 15.000% | 15.000% | 22.500% | 15.000% | 15.000% |
| 85% / independent | 12.150% | 15.000% | 15.000% | 16.875% | 12.150% | 15.000% |

## Correction, harm and unchanged answers

Every entry below compares with **optimal blind Bayes** on the same underlying
worlds and uses one shared fair tie coin. Correction is probability mass where
the comparator fixes a blind error; harm is mass where it introduces one.
`correction - harm = error(blind) - error(comparator)` holds exactly for every
world, cell and mixture. Marginal error alone would hide these two directions.

| Policy | Weak S: correction | Weak S: harm | Strong S: correction | Strong S: harm |
| --- | ---: | ---: | ---: | ---: |
| Naive report independence | 0.000% | 0.000% | 5.215% | 9.265% |
| Payload quotient | 3.465% | 6.615% | 0.000% | 0.000% |
| Optimal blind Bayes | 0.000% | 0.000% | 0.000% | 0.000% |
| Equal root weighting | 7.233% | 13.808% | 6.318% | 11.943% |
| Optimal aware Bayes | 0.000% | 0.000% | 1.715% | 0.765% |
| Protected minority | 5.995% | 15.645% | 0.000% | 0.000% |

Protected minority raises weak-setting error by **9.65 percentage points**:
5.995% correction mass is outweighed by 15.645% harm. With strong S it changes
no classifications relative to optimal blind Bayes, which already follows S in
the ambiguous disagreement pattern. It still worsens mixture Brier loss by
0.006394923 through its changed probability estimates. The result illustrates
why protecting dissent and accurately using calibrated evidence are different
operations.

## One identical vote pattern, different evidence

For three positive generalist reports opposing a negative specialist, exact
posteriors for positive truth are:

| Specialist accuracy | Known copies | Known independent roots | Lineage hidden, known mixture |
| --- | ---: | ---: | ---: |
| 55% | 21/32 = 65.625% | 343/376 ≈ 91.223% | 3129/4328 ≈ 72.297% |
| 85% | 7/24 ≈ 29.167% | 343/496 ≈ 69.153% | 1043/2896 ≈ 36.015% |

Copies of G1 add no evidence to the aware posterior. Three independent agreeing
roots can outweigh strong S. Blind Bayes uses one posterior for identical
visible copied/independent packets; giving it the true arm would invalidate
the intended comparison.

Replacing the padded nulls with copies preserves truth and the informative
primitive readings. Aware Bayes, equal-root weighting and payload quotient have
zero probability changes over all 32 pairs in each specialist setting. Naive,
optimal blind and protected minority probabilities change in all 32 pairs.
The blind Bayes change is rational updating about possible hidden lineage.
Payload quotient's copy invariance does not guarantee good aggregation: it
throws away independent repeated answers. With weak S in the independent arm,
its error is 31.05%, versus 21.6% for optimal aware Bayes/naive independence.

## Claim boundary and next decision

The fixture assumes known reliability, a known construction mixture, correct
lineage, symmetric errors and conditional independence across primitive roots.
No real language model made these sensor predictions. The Claude review is
research collaboration, not an experimental arm. No retrieval gain, general
agent advantage, real metadata quality or literature novelty follows.

Without an accuracy/truth anchor, a separate transformation can flip latent
truth and source accuracies while preserving observed-answer distributions.
That construction lies outside these two known-calibration settings. Lineage
alone cannot orient truth under that broader uncertainty.

Claude review exposed that the candidate [shared-error run](../../_sessions/cycles/2026-09-10-cycle05-common-cause-design.md)
would reproduce the existing copied/independent mixture's truth/payload law.
We retired that numerical run and retained the conceptual boundary: correct
origin labels and marginal accuracies do not guarantee independent errors.
The selected [next design](../../_sessions/cycles/2026-09-10-cycle05-coordinator-packet-design.md)
measures one actual coordinator on12 distinct aware and8 blind diagnostic inputs.
It has not run. This measures use of supplied assumptions, not real source quality.

## Verification and reproduction

Twelve synthetic/structural tests passed before the durable run. An independent
implementation, without importing or reading the production algorithm, rebuilt
all 192 world-arm rows, six policies, six cells and two mixtures. Its 31,587
checks include exact conditioning, observation equivalence, normalization,
posterior identities, sign symmetry, all correction/harm values and copy
statistics. Code inspection and tests separately verify the runtime packet
boundary. Source/output hashes match throughout.
[Preflight](../../_sessions/evidence/2026-09-10-cycle04-preflight.json) ·
[Independent receipt](../../_sessions/evidence/2026-09-10-cycle04-independent-check.json)

Use a fresh result directory; never overwrite the checkpoint:

```bash
python3 -B -m unittest discover -s evaluation/tests -p test_cycle04_known_truth.py -v
python3 -B evaluation/cycle04_known_truth.py --output results/cycle04-reproduction/exact
python3 -B _sessions/tools/check_cycle04_evidence.py --results results/cycle04-reproduction/exact --output /tmp/cycle04-reproduction-check.json
```

The experiment/checker require Python 3.8+ and only the standard library.
`python3 -B results/cycle04-2026-09-10/plot_known_truth.py` renders the saved
summary with optional Matplotlib; both exported figures embed exact plotted
values and source/script hashes. The experimental numerical artifacts remain
immutable when presentation or narrative changes.

## Claude review and a corrected prior argument

The fresh Fable5.1 coordinator and one Opus5 scout completed successfully under
the unchanged $4 cap ($2.52308675 native list accounting, not subscription
billing). No consequential implementation defect was found. The review improved
the interpretation and prevented a redundant next run.
[Execution receipt](../../_sessions/evidence/2026-09-10-cycle04-review-receipt.json) ·
[Full integration and corrections](../../_sessions/cycles/2026-09-10-cycle04-review-integration.md)

One shared reviewer conclusion required correction. Changing the copied prior
share changes which arm benefits from lineage; it does not remove that benefit
at an interior prior. Post-result algebra, independently checked, gives
`error(blind)-error(aware) = min(3w/20,57(1-w)/2000)` conditional on non-null
packets, where w is the copied construction's prior share before observing signs.
At w=19/119 the blind disagreement decision switches. Below it the benefit
comes from copies, above it from independent evidence. It remains positive for
0<w<1. No prior sweep or changed primary experiment was performed.

The exact known-truth laboratory is complete. A stronger empirical claim now
needs observed coordinator outputs. All 95 research/helper tests pass; the next
design remains prospective.
