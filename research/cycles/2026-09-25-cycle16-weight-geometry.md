# Cycle16 — what the family weight intervention identifies

2026-09-25. Bounded mathematical/design note for R19; no collection outcomes
computed. Context: [cycle15 integration](2026-09-12-cycle15-review-integration.md)
and [frozen report](../../results/cycle15-2026-09-12/REPORT.md).

## Hypothesis and toy contract, recorded before checking

**Prediction:** family averaging preserves uniform replication of a family but
not arbitrary member replication. It is also different from reranking that
average and applying another RRF stage. Baselines are the original family mean
and C, respectively. Use the two explicit fixtures below, one-based k60 ranks,
zero contribution for absence, a fixed candidate union, exact rational arithmetic,
and ascending document-ID ties. Primary observable: the sign of the x-minus-y
score difference. No labels, random seeds, effectiveness metrics or parameter
search. Stop after checking the two reversals and algebra; they establish
structural distinctions, not retrieval quality or novelty.

## C is a fixed weighting choice

Write `x_i(d)=1/(60+r_i(d))` when present and zero otherwise;
`L(d)=sum_{i=1}^4 x_i(d)/4`, and `s(d)` for S's contribution. Then
`B=4L+s` and `C=L+s`. C has the same mathematical ranking as `sum x_i+4s`.
Calling this family balancing does not introduce inferred dependence: it
downweights the lexical aggregate relative to S by exactly four.

For a pair of documents let `ΔL=L(x)−L(y)` and `Δs=s(x)−s(y)`.
Along `F_t=tL+s`, C has t=1 and B has t=4. A strict pair reversal requires
opposed signs and a crossing `t*=−Δs/ΔL` strictly between 1 and 4; endpoint
ties require the declared tie rule. Pairs on which L and S agree cannot reverse.
Every strict reversal from B to C therefore moves toward S's pair preference.
This theorem concerns exact scores; implementations must check computed-score
ties and rounding under the existing canonical contract.

C−B isolates the effect of these coefficients, with lists/candidates/ranks fixed.
It cannot identify whether the previous weights were poor because of dependence,
weaker lexical ordering, retained depth, or another collection-specific property.
A positive C−B does not show that lexical evidence helps relative to S or H;
a nonpositive value does not establish a content/depth explanation.

## What replication invariance actually holds

For a declared family of m contribution vectors, let `M=sum x_i/m`.
Replicating **every** member the same positive integer number of times preserves
M exactly. Appending one copy of member j instead gives
`M'=M+(x_j−M)/(m+1)`. Exact score invariance holds iff `x_j=M`; ordering can
remain unchanged by accident. If all members are identical, arbitrary copies
are harmless. Splitting a member's existing weight among its copies also preserves
scores, but that requires identity/lineage bookkeeping outside family averaging.

**Counterexample, full common coverage:** four lexical rankings are
`xabcdy`, `xbadcy`, `yabcdx`, `ybadcx`; S is `abcdyx`.
All rankings contain the same six documents. Initially `L(x)=L(y)`, so
`C(x)−C(y)=−1/(65*66)`. Append one copy of the first lexical ranking and
re-average all five. The difference becomes
`(1/61−1/66)/5−1/(65*66)=4/(61*65*66)>0`.
The reversal survives normalization; this extends cycle01's unnormalized-copy
example by locating precisely which stronger invariance the mean still lacks.

Appending a genuinely distinct member v obeys the same update formula. It can
dilute an existing document's lexical score when v omits that document. There
is no algebraic distinction between redundant and useful new content here.
Splitting/merging declared families can also change their effective weights.
Thus “one family, one vote” names a partition and coefficient convention.

Depth further limits that phrase: the total score mass of one list is
`sum_{r=1}^D 1/(60+r)`, which grows with retained depth D. Equal sums of source
coefficients do not equalize that mass, per-document support, or information.
Truncating a member changes its vector even if S preserves the candidate union;
it removes lexical support from retained candidates. No replication theorem
justifies treating the truncated list as an unchanged copy.

## Hierarchical aggregation is a separate intervention

A hierarchy that passes the unaltered mean scores upward and adds s is exactly
C. A hierarchy that sorts L, replaces its scores by reciprocal ranks, and adds
s generally is not: it discards score gaps and support magnitudes.

**Strict counterexample:** lexical lists are `xzy`, `yxz`, `xzy`, `yxz`; S is
`zyx`. L strictly orders `xyz`. C's x-minus-y difference is `−1/(2*62*63)`.
RRF of the single family ranking `xyz` with `zyx` instead gives
`1/61−2/62+1/63=2/(61*62*63)>0`. There is no family tie or candidate change.

## One next design and its weakest link

Retain one prospective B/C comparison on a collection chosen before comparative
outcomes, with S and H as the already motivated usefulness references. Ask:
**does the fixed weight change improve B while the resulting mixture also adds
value over those simple references?** Preserve C−B as primary, binary nDCG@10,
the canonical contract, fixed cohort, and a single-run stop; no weight sweep.
A label-free implementation check should verify the score identity above and
that any strict B/C pair reversal agrees with S. No extra system arm is needed.
If C only improves B, the conclusion is a better coefficient choice for this
configuration. Positive C−S and C−H would additionally support local incremental
value of this particular mixture, still without establishing a dependence
mechanism or general superiority.

The weakest link is the source-family convention: four related scorers are not
four proven copies, and their 200-deep lists need not have the same information
content as S's deeper list. The proposal is a transfer test of a motivated fixed
weight choice, not a new redundancy estimator. Cycle04's stipulated lineage and
calibration model supplies no missing empirical identification here.

## Exact verification

Both predeclared strict reversals passed with Python 3's standard-library
`Fraction`; no seed or benchmark execution. Uniform replication and the
member-update identity also passed on all six documents. Replay:

```bash
python3 - <<'PY'
from fractions import Fraction as F
def mean(lists, d):
    return sum(F(1, 61 + s.index(d)) for s in lists) / len(lists)
def gap(lists, s):
    return mean(lists, 'x') - mean(lists, 'y') + mean([s], 'x') - mean([s], 'y')
ls = ['xabcdy', 'xbadcy', 'yabcdx', 'ybadcx']
assert gap(ls, 'abcdyx') == -F(1, 4290)
assert gap(ls + [ls[0]], 'abcdyx') == F(2, 130845)
assert all(mean(ls, d) == mean(ls * 3, d) for d in 'abcdxy')
assert all(mean(ls + [ls[0]], d) - mean(ls, d) ==
           (mean([ls[0]], d) - mean(ls, d)) / 5 for d in 'abcdxy')
ls = ['xzy', 'yxz', 'xzy', 'yxz']
family = ''.join(sorted('xyz', key=lambda d: (-mean(ls, d), d)))
assert family == 'xyz'
assert gap(ls, 'zyx') == -F(1, 7812)
assert gap([family], 'zyx') == F(1, 119133)
print('All exact assertions passed.')
PY
```

No workflow friction requiring a durable change was identified (DROP).
