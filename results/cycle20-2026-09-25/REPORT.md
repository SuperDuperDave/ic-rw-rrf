# Cycle20 — natural alignment loses to the matched finite control mean

The natural family fusion F performs **1.576–1.592 P@10 percentage points worse**
than the mean C of 256 predeclared controls, under every permitted completion of
the missing judgments. The proposed advantage of the natural arrangement over
this finite control mean is excluded. C remains above both H and S. This is a
label-conditioned mechanism diagnostic on 30 reused development topics, not a
deployable improvement, a population test, or an estimate of error independence.

## Frozen question and intervention

The [protocol](../../_sessions/cycles/2026-09-25-cycle20-protocol.md) and
[34-file preflight](../../_sessions/evidence/2026-09-25-cycle20-preflight.json)
were frozen before the single actual execution. A/S stay fixed; known document
IDs in D/T are independently permuted within exact relevance grade and original
full A/D/T/S membership mask. Unknown IDs remain at their original ranks.
This preserves candidate sets, membership patterns, grade/missing-ID symbols at
every source rank, and reciprocal mass per grade/membership class. It preserves
source relevance-sequence metrics under every common label completion. It does
not preserve all document-level error overlap or content redundancy.

F=(a+d+t)/3+s and H=a+s retain the established depth 100, one-based k60 and
canonical score/ID tie handling. The control intervention changes known-document
rank assignment in D/T, including their alignment with each other and with A/S.
It does not isolate a single pairwise relationship. C is the arithmetic mean of
256 control P@10 values, not the ranking of mean score vectors or a selected draw.
Seeds, strata, comparison directions and one-run stop were fixed prospectively.

Across 7,680 query/control observations, 6,677 head membership sets change
(7,677 ordered heads). The intervention changes 43–61 slots per 30-query draw.
Of 688 nonempty known-grade/mask strata, 270 are singletons and 418 permit a swap.
These are manipulation descriptions, not new query counts or eligibility gates.
The [separate result review](../../_sessions/cycles/2026-09-25-cycle20-result-review.md)
recounts them directly from saved heads.

## Exact results

Binary relevance means grade>0. Bounds use shared query-document unknown labels;
they are sharp conditional completion bounds, not confidence intervals.

| Contrast | Lower | Upper | All completions |
|---|---:|---:|---|
| **F−C, primary** | **−1223/76800** | **−121/7680** | **Negative** |
| C−H | 91/15360 | 1373/38400 | Positive |
| C−S | 83/2560 | 2759/76800 | Positive |
| F−H, historical reference | −1/100 | 1/50 | Unresolved |
| F−S, historical reference | 1/60 | 1/50 | Positive |

Assigning missing judgments zero gives C=4729/7680 (0.615755), F=0.60,
H=0.58 and S=7/12. Individual control means range from 89/150 to 16/25;
some controls are below F. The claim concerns the specified finite mean, not
every shuffled arrangement or the full permutation expectation. The 256 controls
do not create additional independent labeled queries, and no permutation p-value
or best-seed method is reported.

Only one unknown pair affects the primary: query 26/document kv3363qh, absent
from natural F and present in 13 controls. For its binary relevance z,
F−C=−(1210+13z)/76800. Neither permitted value changes the conclusion.

The old F−H uncertainty survives unchanged. C−S being positive shows that a gain
persists under this intervention; it does not attribute all gains exclusively to
marginal quality and support or imply that all alignment was destroyed. The
strict negative primary challenges the proposed helpful natural alignment on
this panel. Because qrels define the control strata, the higher control mean
cannot be promoted as an unsupervised retrieval policy.

## Verification and reproduction

All 82 targeted tests passed before freezing. The producer succeeded on its
first actual run; an independent Fraction-based implementation reconstructed
every field of controls.json and analysis.json in 18.36 seconds. This includes
all 7,680 ordered control heads, label coefficients, exact bounds, natural
references, seed behavior and invariants. No producer/parser implementation was
imported by the checker. All outside-original-pool admissions remain zero, as
the prior formula-specific admission bound requires.

The independent checker also verifies shared-label triangle identities and both
aggregate normalization routes. Its synthetic tests cover 81 partial-label
tables, 1,280 contrast completions and 48 rank-profile completions. A separate
nontrivial fixture changes fused P@10 despite preserving grade/membership
profiles. NIST evidence for the unchanged natural references comes from cycle18;
the new control heads were checked by independent arithmetic, not separately
exported to NIST.

```sh
python3 -B evaluation/cycle20_alignment_control.py --preflight _sessions/evidence/2026-09-25-cycle20-preflight.json --output results/cycle20-2026-09-25/run
python3 -B _sessions/tools/check_cycle20_alignment_control.py --result results/cycle20-2026-09-25/run --preflight _sessions/evidence/2026-09-25-cycle20-preflight.json --output results/cycle20-2026-09-25/independent-check.json
```

These are the exact executed commands. Replay uses an unused output directory
and the pinned cycle18 derived inputs plus the identified late-qrels snapshot;
existing evidence must not be overwritten. Saved-result verification pins
CPython3.12.3; it rejects a different interpreter version. Restore the ignored
late.qrels using the [cycle17 input plan](../../_sessions/cycles/2026-09-25-cycle17-input-plan.json)
and verify SHA25684f608d302d07df206243b051e52ea0592a09ef0413cf56a12b77c9a30d022f5.
The standard-library implementation
requires no new research dependencies.

Artifacts: [controls](run/controls.json), [analysis](run/analysis.json),
[manifest](run/manifest.json), [success](run/success.json),
[independent reconstruction](independent-check.json).

## Decision

The frozen stop is met: close optimization of this 30-topic quartet. No new
seed, source, stratum, depth or weight search follows this result. A subsequent
research branch needs a different question and information/evaluation contract.
The [integration](../../_sessions/cycles/2026-09-25-cycle20-integration.md)
owns the assessed Buddy → Opus return and the next branch decision.
