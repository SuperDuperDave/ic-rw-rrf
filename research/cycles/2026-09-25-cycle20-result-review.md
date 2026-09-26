# Cycle20 — independent result and interpretation review

Reviewed 2026-09-26 against the experiment dated 2026-09-25. This bounded
read-only review used completed artifacts; it generated no controls, rankings,
labels or new experimental outcomes. No frozen file was modified.

## Evidence and review scope

Checked these exact files, then confirmed their hashes were unchanged afterward:

| Artifact | SHA256 |
| --- | --- |
| `results/cycle20-2026-09-25/run/analysis.json` | `a86cec279956ebf34e6c1f846b7441a50b319baca205bd6c69ad9ae531589c1a` |
| `results/cycle20-2026-09-25/run/controls.json` | `92f43001b26c1b4f8c1d0335196ed4e1feb762f37510861c1e7119d6d39c5646` |
| `results/cycle20-2026-09-25/independent-check.json` | `e4d6e56b2c262f038f065ab47ba74304679e0fc66bc766daa03b4f6d7594991a` |

A separate inline standard-library reader, importing no project implementation,
recounted memberships and changed slots from all 256 by 30 stored control
heads. It checked the complete query/draw inventories, head uniqueness and size,
every stored head inclusion count, and every saved changed-slot count. For all
five contrasts it reconstructed per-query coefficients from the heads, joined
the already saved support grades, recalculated the exact known contribution
and sharp endpoints, and averaged once across 30 queries. All matched.

The existing independent receipt reports `passed`, matches the reviewed output
hashes, and separately establishes regeneration of every ordered head and
analysis field from pinned inputs. Its checks include the identity replay,
grade/membership-class mass, unknown-score preservation, normalization, and
fixed-reference endpoint equivalence. This review did not rerun that producer
or verifier and did not independently reassess the supplied relevance grades.

## Primary result and its sole remaining unknown

The exact finite-panel primary interval is

```
F - C in [-1223/76800, -121/7680].
```

Both endpoints are strictly negative. Thus the arithmetic mean C of these
256 fixed controls exceeds natural F for every allowed completion of the
missing labels. Its advantage is between 121/7680 and 1223/76800 P@10 units,
approximately 1.575521 to 1.592448 percentage points. This is stronger than
merely failing to establish a natural advantage, but remains a statement about
the particular finite control mean.

Only query 26 / `kv3363qh` is unknown on nonzero primary support. It is absent
from natural F and appears in 13 of the 256 control heads. Its coefficient is
−13/2560 in that query's contrast and −13/76800 in the 30-query mean. If z is
its binary relevance, the complete primary identity is

```
F - C = -(1210 + 13*z)/76800,  z in {0,1}.
```

Neither value can reverse the result. Its presence in some control heads is
consistent with its own fused score being fixed: known documents can cross
that score after their ranks are reassigned.

The reconstructed contextual intervals are:

| Contrast | Sharp lower | Sharp upper |
| --- | ---: | ---: |
| C−H | 91/15360 | 1373/38400 |
| C−S | 83/2560 | 2759/76800 |
| F−H | −1/100 | 1/50 |
| F−S | 1/60 | 1/50 |

The control mean also exceeds H and S under every allowed completion. Natural
F−H remains unresolved and natural F−S remains positive, exactly as before.
The missing-zero means are C=4729/7680, F=3/5, H=29/50 and S=7/12. Those
point conventions do not replace the bounds.

## Manipulation counts, with units made explicit

| Quantity recounted from saved artifacts | Confirmed value |
| --- | ---: |
| Control query-head observations | 7,680 = 256 draws times 30 queries |
| Heads whose top-ten membership set differs from natural F | 6,677 |
| Heads whose ordered top-ten sequence differs from natural F | 7,677 |
| Total changed slots, counting admitted documents once | 13,141 |
| Minimum total changed slots in one 30-query draw | 43 |
| Maximum total changed slots in one 30-query draw | 61 |
| Nonempty known-grade/membership-mask strata | 688 |
| Singleton strata | 270 |
| Strata with size greater than one | 418 |
| Maximum stratum size | 38 |

The 688 strata are source/query/grade/mask cells across D and T, counted once
before their repeated permutations. They exclude unknown positions, which
remain fixed. They are not 688 independent queries or labels. Each changed
slot is one admission relative to natural F; an equal number of exits exists
and is not added again. Membership change, rather than order-only change, is
the relevant manipulation for P@10. These are descriptive checks, not a
post-result eligibility threshold or an authorization for another control arm.

## Interpretation for the collaborator return

The primary prediction of positive natural F−C is refuted for the specified
finite batch and label contract. The natural assignment of known documents to
ranks within the fixed grade/membership strata is not needed to preserve the
observed average advantage over H or S in this intervention: the control mean
retains those advantages and exceeds F. This does not mean every individual
draw beats F, nor that all possible legal permutations do so.

The experiment does not identify marginal quality or membership as the exclusive
cause of the gain. Between-class score mass, candidate support, A/S alignment,
and all unjudged-document rank assignments remain intact. Dependence and other
relationships not varied by the intervention can still matter. The result
also does not attribute the effect to a particular D/T or variant-versus-A/S
relationship, since those within-class rank relationships changed together.

The controls use known qrels in their construction and need not correspond to
realizable retrieval pipelines. C is an average of outcomes, not a single new
ranking or a deployable unlabeled policy. Neither the finite mean nor these
missing-label intervals estimates a population or full-permutation expectation.
There is no permutation p-value, new labeled sample, source-independence result,
or transfer result here. Earlier scalar nonrepresentability does not imply that
the natural arrangement must be effective or uniquely valuable.

P@10's unchanged convention reuses the pinned Cycle18 NIST evidence; these
7,680 control heads were not individually exported to NIST. The independent
reconstruction checks their arithmetic directly. Preserve that distinction.

No correction to the frozen artifacts is indicated. The result completes this
intervention; it does not justify another seed, stratum definition, query subset
or optimization pass on the same quartet.
