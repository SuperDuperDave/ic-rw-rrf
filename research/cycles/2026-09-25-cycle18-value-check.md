# Cycle18 value check — real variants versus repeated baseline votes

Date: 2026-09-25. Bounded Codex design review for R21. Existing evidence and
metadata only; neither the `BITEM_df` nor `BITEM_stem` run body, their scores,
or their effectiveness reports were opened. No new experiment, download,
provider call, or shared-state edit accompanies this note.

## Decision

**The fixed substitution comparison has a small, distinct information value.**
It is worth one inexpensive development measurement if the coordinator wants to
decide whether these two real submitted variants add value to this particular
fusion. It is redundant as a demonstration that copying votes changes RRF, and
it cannot identify source dependence or establish a minority-protection method.
Those purposes would not justify another run.

The new observable is the finite-panel retrieval effect of replacing two exact
copies of a named baseline with two separately submitted variants derived
from that baseline, while preserving the number and coefficients of the source
slots. Separate archived submissions do not imply independent errors or
independently acquired information.

## What the previous cycles already established

| Prior evidence | Established | Still unmeasured by that evidence |
| --- | --- | --- |
| [Cycle01](../../results/cycle01-2026-09-10/REPORT.md), [protocol](2026-09-10-cycle01-protocol.md) | Exact source copies change ordinary RRF, including with common coverage; relevance effects are mixed; exact deduplication gives invariance without guaranteeing quality. Interventions included one and three additional copies on the existing four-source configurations. | A matched comparison between replacing repeated baseline slots with these real BITEM variants on this applied panel. Another copy count alone would add little. |
| [Cycle15](../../results/cycle15-2026-09-12/REPORT.md) | Adding S to four lexical rerankings improves the family aggregate under the benchmark convention, while simple H and standalone S outperform the resulting five-list fusion. Candidate access, ordering and weighting remain bundled. | A same-slot-count literal-copy control for the lexical variants. The four local rerankings were also a different family, collection and depth contract. |
| [Cycle16 geometry](2026-09-25-cycle16-weight-geometry.md), [report](../../results/cycle16-2026-09-25/REPORT.md) | Family reweighting is a coefficient intervention; copy invariance and effectiveness differ; a better standalone source need not benefit a fusion when upweighted. Support certificates locate a fixed admission barrier without inferring correlated errors. | Whether the actual output differences of this externally submitted family help relative to repeated A votes. The proposed family-weight effectiveness test was parked. |
| [Cycle17](../../results/cycle17-2026-09-25/REPORT.md) | On this pair, the one-slot minority policy cannot improve mean P@10 over H under allowed labels. Later observations establish H over A but leave H versus S unresolved. | The effect of the still-unopened df/stem outputs. Existing findings motivate keeping H and S as references; they do not predict the new variants' quality. |

Thus the discriminating question is about the value of particular different
rankings, not the already-settled lack of copy invariance. This is a local
development comparison on reused topics with known A/S outcomes.

## Smallest informative contract

Use these three configurations, with S alone retained as a reference:

- **H:** A + S, exactly the existing cycle17 hybrid.
- **W:** three literal A copies + S; equivalently `3a+s`.
- **V:** A + `BITEM_df` + `BITEM_stem` + S; score `a+b+c+s`.

Here each lower-case vector contributes `1/(60+r)` at its canonical one-based
rank and zero when absent. Before ranking,

`V(d) - W(d) = b(d) + c(d) - 2a(d)`.

S cancels from this score difference but still affects each arm's final ranking
and cutoff. The **primary effectiveness contrast is V−W**, equal-query mean
binary P@10 under sharp missing-label bounds. A positive lower bound establishes
that these substitutions improve this fixed output policy over repeated A votes
for every allowed label completion. It does not establish that a latent
"information" quantity increased, nor that the reason was reduced dependence.

The two new inputs are documented, nested preprocessing/query-weight variants:
stemming, and stemming plus PMC document-frequency boosting, of BITEM's body-text
Elasticsearch baseline. Their [existing metadata](2026-09-25-cycle17-input-feasibility.md)
justifies the family designation without measuring error correlation.

Require all four real inputs to supply at least 100 valid distinct candidates
on all 30 topics, then retain exactly 100 per source. This makes W and V match
both four nominal source slots and total reciprocal-score mass. If a new run
fails that precommitted input condition, stop instead of dropping queries or
changing depth. Equal slots and score mass do **not** match the information or
retrieval-compute cost: W obtains no new ranking, whereas V uses two additional
outputs. Original generation costs are not measured here.

Necessary fixed comparisons are **V−H**, **V−S**, and **W−H**. The first two ask
whether the extra outputs improve on the existing useful references. W−H is
explicitly the weighting effect of tripling A; it is a control description, not
a new finding about dependence. Retain original A/S/H rankings and identities;
do not choose the best family member using labels. No other copy count, weight,
depth, family normalizer or protected-slot policy is needed.

Use the already acquired late chronological Round1 labels as the single primary
label source, with the same binary grade contract and absent-as-unknown bounds.
Fix that choice before viewing the new bodies. Repeating the early/late label
experiment would enlarge this study without being necessary for its new question.
The existing labels and topic outcomes have been used; no untouched-evaluation
claim follows merely because two source files remain unopened.

## Observation units and interpretation

Freeze each query's observation universe as
`U_q = A100 ∪ df100 ∪ stem100 ∪ S100` before applying labels. Scores for absent
sources are zero; extra zero-score candidates cannot change H or W's top10.
Preserve the original H/S ranking bytes and use the same string-ID tie rule,
finite-score canonicalization and retained-depth contract throughout.

For every contrast, cancel common top10 members first and bound the relevance
of each remaining unknown query/document unit. Average over all 30 topics;
changed or eligible subsets are descriptive only. Source variants and repeated
votes create no additional independent query units. No p-values are needed.

The minimal diagnostic ledger records V/W top10 entrants and exits, source
ranks, known grades or unknown status, and whether each entrant was absent from
the original A100∪S100. This separates newly available candidates from changes
among previously available candidates without adding a fourth fusion arm.
These are descriptive categories, not a causal decomposition: new inputs change
support and scores jointly, and there is no unique matching of multiple entrants
to displaced documents.

Do not redefine S-only against the larger family and interpret the resulting
count as the original manipulation check. Expanding the lexical union changes
the predicate itself. The primary V−W contrast needs no S-only eligibility gate.

## Falsifier, stop and value of the possible outcomes

Stop after the two new inputs, this one fixed comparison, independent arithmetic
reconstruction and assessed review. Metadata lists the two bodies at a combined
2,086,575 bytes; acquisition should pin those prior identities and freeze a
small explicit byte/time ceiling. No corpus or model inference is needed.

If V and W have identical top10 **sets** on every query, V−W is exactly zero for
this metric without reading labels; different order within the first ten cannot
change P@10. Preserve that result without changing the metric to find a gain.

Otherwise classify the V−W interval using the existing exact rule:

- Lower endpoint > 0: the actual variant substitutions help relative to the
  copy control on this panel. Inspect the already-fixed V−H/V−S bounds before
  describing the extra apparatus as useful beyond simple references.
- Upper endpoint ≤ 0: positive improvement over the copy control is excluded
  under this contract. This is local to these two replacements and coefficients.
- An interval crossing zero: the available labels do not settle its sign.
  Preserve partial identification; do not search another configuration, choose
  only favorable queries, or buy labels automatically to force a verdict.

A V−W gain with no supported gain over H/S can mean that real variants repair
some damage caused by overweighting A. It does not justify replacing the simpler
references. Conversely, an unresolved V−H or V−S interval is not evidence of a
tie or proof of no value. Even positive bounds against every fixed reference
remain development evidence requiring a separately selected evaluation setting
before broader promotion.

This supports a **conditional proceed** decision for the concrete variant-value
question. Its value depends on measuring the substitution and keeping the
simple references visible; the known vote-count effect supplies only a control.

## Handoff and friction

Only this note is changed by the worker. Source bodies, outcome files, shared
planning, session streams and git state were not modified. A read attempted the
wrong date for the cycle15 report, then used its actual September12 path;
**DROP** as a transient lookup error, with no workflow change warranted.

Stable handoff to the coordinator and Opus: this is a value assessment and
suggested minimal contract, not authority to change R21's scope or a report of
new empirical results.
