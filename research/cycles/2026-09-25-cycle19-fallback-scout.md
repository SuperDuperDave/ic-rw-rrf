# Cycle19 fallback scout — hold quality fixed, intervene on rank alignment

Status: proposed experiment, not an executed protocol. Written from the
[Cycle18 report](../../results/cycle18-2026-09-25/REPORT.md), its
[integration](2026-09-25-cycle18-integration.md), and the frozen
[Cycle19 inventory contract](2026-09-25-cycle19-inventory-protocol.md).
No new run, qrel, corpus or network body was inspected for this note. The exact
transfer inventory remains the coordinator's separate ongoing task.

## Recommendation

If the inventory cannot establish the quartet, close that exact-pipeline
transfer route. Do not replace missing roles with whatever accessible runs look
promising. Also stop adding BITEM weights or variants on these 30 queries.

One small mechanism diagnostic is still worth doing before leaving this panel:
**does the observed arrangement of the two variants' ranked documents contribute
beyond their individual rank quality and candidate support?** Randomize that
arrangement while preserving both of those quantities exactly. This addresses a
confound that Cycle18 explicitly leaves open; it is neither another scalar
escape certificate nor another optimized fusion rule.

The output would be evidence about this finite, label-conditioned intervention.
It cannot validate a new method on unseen queries. If the next decision demands
performance transfer rather than understanding this mechanism, skip this scout
instead of presenting its answer as a substitute for transfer.

## One experiment: grade-preserving variant-rank permutations

Keep the already frozen canonical A, D, T and S retained100 lists, the same
30 queries, k60, ID tie rule, full pinned late qrels, and
F=(a+d+t)/3+s and H=a+s. Candidate sets and source coefficients never change.
The natural F is the existing Cycle18 policy, not a newly selected reference.

For each query, separately for D and T:

1. Partition the **judged** documents in that source's retained100 into exact
   grade0, grade1 and grade2 strata using the pinned snapshot.
2. Uniformly permute the document IDs among their own stratum's occupied rank
   positions. A group of size0 or1 is unchanged.
3. Keep every unjudged document at its original rank. Do not shuffle an
   "unknown" class, complete missing labels, move IDs between sources, or
   add/remove candidates.

D and T use independent permutation draws, including when their strata happen
to contain the same IDs. A and S remain fixed. Fuse each resulting pair with the
unchanged formula, using its assigned one-based ranks. These are artificial
post-canonicalization rank vectors, not reconstructed submissions with new raw
retrieval scores.

Use exactly **256** precommitted draws. Freeze the seed construction and shuffle
implementation before generating any control heads; use separate deterministic
random streams indexed by draw, query, source and grade. No draw is accepted,
rejected, rerun or selected because of its resulting ranking or score. Save every
control head and its draw identifiers for independent replay. If the intervention
is a no-op or changes no heads, report that outcome without increasing the budget.

### What is held fixed

- Each source's document SET, depth, rank-contribution multiset and source-level
  candidate access are unchanged. Every document's vector of source-membership
  indicators is also unchanged; the common and source-only support partitions
  cannot move.
- Each source's complete known-grade-at-rank vector is unchanged. More strongly,
  if a missing judgment is represented by its own `(query,document)` symbol,
  the vector of known grades and missing-label symbols at every rank is
  unchanged. Thus each standalone source's binary precision profile is identical
  under **every common allowed completion** of missing labels, not merely under
  the missing-zero convention.
- The U=A100∪D100∪T100∪S100 and U0=A100∪S100 pools remain identical. Cycle18's
  admission bound continues to exclude new-only F head access for this formula.

Exact grade strata are deliberately finer than binary relevance. Permuting
grades1 and2 together would preserve binary P@10 but change the known graded
rank profile. Separate strata preserve that additional information at no new
evaluation cost. No additional graded metric is proposed.

What changes is **cross-source rank alignment**: which already retrieved
documents receive reinforcing high or low reciprocal contributions. D–T and
variant–A/S alignment can both change. The experiment does not isolate those two
relationships from each other. It also does not make the real retrieval
pipelines, evidence origins or errors independent. Membership overlap is fixed,
so this is not an intervention on support duplication or provenance.

## Prediction, comparator and observation contract

**Hypothesis:** the observed rank alignment is useful beyond the individual
rank-quality profiles and candidate support retained by the control.

**Distinct falsifying prediction:** natural F's finite-panel mean binary P@10
exceeds the mean P@10 of the 256 fixed randomized controls under every allowed
missing-label completion. A sharp upper endpoint at most zero excludes that
strict benefit for this intervention panel. An interval containing both gain
and nongain leaves it unresolved; there is no rescue through another random seed,
stratum choice or permutation budget.

The primary comparator is the **arithmetic mean of the 256 control policies'
P@10 values**. Do not average their score vectors and then rank that average:
that would answer a different question. No best or worst draw becomes a policy.

Keep H=a+s as the strongest existing simple hybrid baseline and retain the
preexisting standalone S reference. Report natural F−H and F−S unchanged, and
the fixed control mean minus H and minus S. These situate the diagnostic: a
natural-versus-control difference alone does not establish practical superiority
over H/S, and controls may preserve a gain over S without requiring the natural
alignment. No new weight, source or comparator is chosen from these outcomes.

All policies receive only their prescribed ranked lists and the same fixed
fusion rule. Qrels are used explicitly to construct the **experimental
intervention**, then to evaluate every policy with the same snapshot. Neither
fusion receives grades, reliability estimates, extra content or a learned rule.
This is fair for the conditional mechanism question, but it is not a label-free
deployable algorithm or a prospective performance estimate. State this before
the results, not in a footnote.

For the primary, form one coefficient per query/document **after aggregating the
control indicators**:

`c(q,d) = [I(d in natural F10) - (1/256) Σ_b I(d in control_b10)] / 300`.

Cancel equal coefficients before joining labels. Known grades contribute
`c * I(grade>0)`; each absent grade contributes `[min(c,0), max(c,0)]`. Summing
with exact rational arithmetic gives sharp bounds for the comparison with this
finite control mean. Aggregate coefficients provide an efficient, inspectable
implementation. Here averaging the individual sharp endpoints is equivalent:
for a fixed natural head, any particular pair has only zero/positive
coefficients across controls, or only zero/negative coefficients. Its extremizing
unknown value therefore cannot conflict between draws. The same argument holds
for control mean minus fixed H/S. The missing-zero point remains a separately
named benchmark convention.

This is an assessed design correction from the coordinator: the scout's initial
warning that endpoint averaging would be loose was false for these fixed-reference
comparisons. Opposite coefficient signs across draws are possible with two
varying policies, but not in this proposed primary. The experiment is unchanged;
no unnecessary generic varying-policy test or extra arm follows the correction.

Retain per-query coefficients, bounds, control head frequencies and changed-slot
counts. Control-draw variation can be described, but the 256 draws are Monte
Carlo interventions on the same30 queries, **not 256 new labeled panels**. Their
finite average does not identify the full permutation-distribution expectation
without Monte Carlo uncertainty. Do not attach a permutation p-value without a
substantive exchangeability/null model for why the natural alignment would have
been drawn by this randomizer; none is supplied here. No population p-value or
query generalization claim is proposed.

## Minimal inputs, checks and budget

Required inputs already exist locally: the successful Cycle18 policy artifact
(containing all four retained orders), its custody manifest, the exact pinned
late qrels, and the recorded natural policies. Pin their hashes in a new
preflight; no run/corpus download, model call, proxy judgment or new label is
needed. No earlier raw provider receipt is a scientific dependency.

One standard-library producer run and one independent reconstruction, each
limited to300seconds. Exactly256 draws, 30queries, two permuted sources and
three fixed exact-grade strata per source; the number does not depend on
outcomes. There is no sweep over strengths, fractions,
normalizations, grades, cutoffs or seed counts. Keep artifacts compact: natural
and control heads, permutations or reproducible seeds, invariant checks,
coefficients and summaries; not a duplicate full research framework.

Two checks provide adequate protection without adding experimental arms:

1. The identity permutation must reproduce every saved natural F head and score
   exactly before any random control is admitted. This is a coding check, not an
   additional observed policy.
2. For every control, assert source candidate-set equality and exact equality of
   the known-grade/missing-ID-symbol vector at each source rank. Independently
   recompute the resulting F heads and aggregate signed bounds. Synthetic tests
   check shared missing-label accounting and equivalence with averaged sharp
   endpoints for the fixed-reference comparisons, together with their exact
   contrast-triangle identities.

Any custody, invariance, arithmetic or runtime failure preserves the failure and
stops. Any successful sign—including no effect or unresolved bounds—ends this
diagnostic. Do not follow it with another permutation arm on these labels.

## Why this is a different branch, and when to stop

Cycle04 already demonstrated the value and limits of trusted lineage inside a
stipulated probability model; repeating that calculation with another copy rate
would not address the present evidence. Cycle18 already establishes scalar
nonrepresentability for many actual queries. Here the informative quantity is
whether **actual identity/rank arrangement contributes when marginal source
quality and support cannot change**. The independent permutation intervention
does not stipulate the answer: matched quality can coexist with helpful,
harmful or irrelevant alignment.

A positive lower bound would justify saying that this natural arrangement beats
these quality-and-support-matched randomized arrangements on the reused panel.
It would not establish source independence, an anti-cabal learning rule or
transfer. An upper bound≤0 would challenge the idea that the natural arrangement
is especially useful under this intervention. Unresolved bounds still show the
limit of what the current labels can identify.

Whichever result occurs, close optimization on this30-query quartet afterward.
Keep the broader consensus/specialist question open, but require a genuinely new
information or evaluation contract for the next experiment. That stopping rule
prevents a useful diagnostic from becoming an endless local search.
