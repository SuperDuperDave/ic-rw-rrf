# Cycle19 — review of a label-conditioned rank-alignment intervention

2026-09-25. Independent bounded reasoning from the frozen Cycle18 formula and
completed evidence. No controls, new rankings, labels or downloads were created.
This is a proposed next design, not an executed experiment or an amendment to
Cycle18's frozen protocol.

## Recommendation

This has more information value than another minimax-regret calculation on the
existing F/H/S triangle. It changes a concrete property of the input rankings
while preserving strong measured margins. A single frozen batch can distinguish
whether the natural document-to-rank assignments help F relative to the specified
synthetic assignments. The question is narrower than whether independence,
diversity or agreement generally helps retrieval.

Use it only as a label-conditioned development diagnostic. The controls consult
the already known qrels to construct ranks and are not deployable unsupervised
policies. The prospective elements are the control rule, seed, finite batch,
contrast and stop, not fresh labels or an untouched evaluation panel.

## What is actually preserved

For each query and each of D and T, partition the retained 100 positions by
the occupant's observed exact grade 0, 1 or 2. Permute document IDs only among
positions in the same grade stratum of that same source and query. Keep each
unjudged document at its original source rank. Keep A and S entirely fixed.

Then, for every common completion of the missing labels:

- Every source's candidate set and every document's source-membership pattern
  are unchanged. All source-pair support intersections and candidate unions
  therefore remain unchanged.
- Each source's entire relevance sequence by rank is unchanged: known positions
  receive the same exact grade, and unknown positions retain the same document.
  Standalone P@10 is identical, as are ordinary relevance-sequence metrics
  under the same qrels and cutoff. This does not preserve content-sensitive
  diversity or redundancy measures.
- Reciprocal-score mass is unchanged. Every unjudged document's fused F score
  is also unchanged because its A/S ranks and its D/T ranks or absences are
  fixed. Its head membership can nevertheless change when known documents'
  scores cross its fixed score.
- The Cycle18 admission proof continues to apply: every control F head lies
  inside the original A100 union S100. New candidate access cannot explain a
  difference between the natural F and these controls.

The changed object is the assignment of reciprocal contributions to individual
known documents. Independent D/T permutations change D-versus-A/S,
T-versus-A/S and D-versus-T rank relationships together. They do not change
which sources cover each document. There is no clean attribution to one source
pair or one notion of alignment without another separately specified design.

## Causal and measurement limits

These controls do not remove all dependence. Grade-at-rank structure, membership
overlap, A/S alignment and every unknown document's rank alignment remain
fixed. The intervention acts on the judged slice, which was not randomly
selected for judging. Do not describe it as making the sources independent or
as uniformly shuffling all rank alignment.

The shuffled lists need not be outputs of any feasible retrieval pipeline.
Differences identify the consequence of this explicit intervention on ranking
inputs, conditional on the fixed grades and support sets. They do not identify
the causal effect of stemming, retrieval-model dependence, or semantic diversity
in a population. Nor does preserving each standalone metric mean that every
form of source quality or document difficulty has been controlled.

Do not present a permutation p-value: no exchangeability claim has been
established. The average of 256 seeded controls is exactly that finite batch's
average, not the exact expectation over all legal permutations. Missing-label
bounds for the batch are exact; they do not quantify Monte Carlo uncertainty
about a larger permutation distribution.

## Sharp bounds and the fixed-reference exception

Let N(q,d) be the number of the 256 control heads containing document d for
query q, and I_F(q,d) the natural head indicator. With all 30 queries retained,
the coefficient in natural F minus the mean control is

```
c(q,d) = [I_F(q,d) - N(q,d)/256] / 300.
```

Use one relevance variable per query/document across all controls. Known labels
contribute c times binary relevance; unknowns give min(0,c) to the lower bound
and max(0,c) to the upper bound. Cancel zero coefficients before reporting support.

There is an important simplification here. For each document, every individual
natural-minus-control coefficient has the same sign: it is nonnegative when
the fixed natural head contains that document and nonpositive otherwise.
Consequently the average of the individual sharp lower endpoints equals the
sharp aggregate lower endpoint; the same holds for upper endpoints. One shared
completion attains all individual lower endpoints simultaneously, and likewise
all upper endpoints. Thus averaging their sharp endpoints is valid here.

The same sign argument applies to mean control minus fixed H or S. It does not
automatically apply when both sides of a contrast vary across draws and a
document's coefficient can switch signs. Treating labels as independent across
draws remains conceptually incorrect even when the fixed-reference structure
happens to give the same numerical endpoints.

## A bounded contract worth considering

Freeze exactly 256 controls, one specified PRNG/seed and deterministic iteration
order, with independent uniform within-stratum permutations for D and T. Keep
identity permutations and duplicate controls; do not resample to force head
changes. Fix all 30 queries, depth 100, k60, exact rational fusion and ID ties.
The original raw labels and natural policies remain pinned and unchanged.

Primary question: does natural F have a strictly positive sharp lower bound
against the arithmetic mean of this fixed control batch? A nonpositive upper
bound excludes positive advantage for that batch; an interval containing zero
remains unresolved. This is a proposed falsifiable prediction, not an expected
outcome inferred from the completed F−S result.

Verify source-set, per-document support, full grade-at-rank and unknown-rank
invariance before accepting any metric. Report nontrivial stratum sizes,
changed ranks and changed heads as manipulation descriptions, without a
minimum-change gate or favorable-query subset. If all heads remain unchanged,
that is a null for the specified intervention and cutoff.

Keep the control mean's direct contrasts with fixed H and S visible, without
selecting a control or adding weights. Because H/S are fixed,
(natural F−S)−(mean control−S) equals the primary contrast; this is an accounting
identity, not an extra independent result. Stop after this single batch and
independent reconstruction. No seed, stratum, grade-grouping or budget sweep
follows a disappointing outcome.

## Why the existing minimax triangle does not need another experiment

The [triangle](2026-09-25-cycle18-triangle-check.md) makes S strictly dominated
by F in every allowed completion. Pure F/H/S have worst regrets 3/300, 6/300
and 9/300. A lottery over whole F versus H heads, independent of the fixed
labels, with probabilities 2/3 and 1/3 has worst expected regret 2/300. This is
not reciprocal-score fusion or a guarantee for each random realization.

After truthful labels reveal r positives and z negatives among the nine unknown
H-only pairs, let a=max(3−z,0) and b=max(6−r,0). Pure-action minimax regret is
min(a,b)/300. Allowing the lottery gives ab/[300(a+b)] when a+b>0, and zero
otherwise. The tenth triangle label contributes zero to this action decision.
The nine relevant labels are exchangeable under equal cost: adaptive selection
among their identities adds no information advantage. Zero-regret action choice
is certified once z>=3 or r>=6, hence after at most eight such labels, although
strict superiority or an exact tie can require more information.

Unlike Cycle13's width objective, this is explicitly decision-conditioned.
But the current case reduces to standard count arithmetic, with no acquisition
policy competition left to test. Retain the derivation if useful; park a new
decision experiment until an actual action, utility/cost model, admissible
randomization and trustworthy judgment process give it a purpose.
