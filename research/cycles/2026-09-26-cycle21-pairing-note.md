# Cycle21 — exact pairing witnesses under the frozen source invariants

Status: completed synthetic proof task only; no real-query data or performance
inference. No Cycle20 controls or source implementations were imported or rerun.

## Prospective search contract

Recorded before the bounded synthetic search. Hypothesis: grade/membership-mask
preservation does not force the sign of natural F minus a control mean. Seek a
single legal permutation orbit with two distinct P@10 values; choosing its high
and low members as separate natural fixtures then supplies opposite signs.

Use four depth-100 rankings with the same 100 document IDs, one-based k60 and
F=(a+d+t)/3+s. All membership masks are 15. Nine common fixed prefix documents
occupy ranks 1–9. Only two grade-1 documents p,q and a grade-0 document n occupy
ranks 10–12; all remaining documents and the prefix are unknown and fixed.
For D/T, only p and q may swap. A/S remain fixed. Enumerate tail orders
deterministically, using exact rational scores and ascending-ID ties. Retain
only an orbit whose contested winners are strict, with both a positive and n
winning in different states. Primary observable: exact P@10 differences across
the four equally weighted D/T swap states. Stop at the first witness or after
30 seconds; no real data, seeds, source selection or benchmark tuning.

The search only selects a mathematical counterexample to a universal sign
claim. It cannot support an empirical frequency or effectiveness claim.

## The base score and the unsupported mechanism claim

For the actual formula, the fixed base while D/T vary is

```
base(x) = a(x)/3 + s(x)
extra(x) = [d(x)+t(x)]/3
F(x) = base(x) + extra(x).
```

Using a+s as the base and then adding the D/T contributions overcounts A by
2a/3. An alternative correct decomposition is
F=H+(d+t−2a)/3, where H=a+s; that perturbation includes a negative A term and
cannot be described as just D/T contributions.

Grade/mask permutations fix the total extra score mass within each class, but
change its distribution over documents with different fixed base scores. This
describes a real degree of freedom. It does not prove that concentrating score
on high-base documents decreases P@10. Top-ten membership is a discontinuous
function of competing scores, and the cutoff generally moves with the control.
There is no demonstrated universal convexity, concavity or covariance rule that
determines its sign. The actual negative Cycle20 contrast alone does not measure
the proposed natural "correlation concentration" or establish it as a cause.

## One full-depth orbit supplies both signs

The deterministic search stopped at its first witness after 20 orbits, taking
0.003115 seconds, below the 30-second cap. It enumerated the six permutations
of (n,p,q) for A/S/D/T and kept only the lexicographically first p/q orientation
for D and T before evaluating each four-state orbit. No additional search
followed this witness.

Each source contains exactly these 100 distinct documents:

```
g01,...,g09, n,p,q, f013,...,f100.
```

All four sources place g01,...,g09 at ranks 1,...,9 in that order and
f013,...,f100 at ranks 13,...,100. Those 97 documents are unknown, with their
identities and ranks fixed in every source. Let grade(p)=grade(q)=1 and
grade(n)=0. All documents have the same full membership mask, 15.

The only changing positions are:

| Source/state | Rank 10 | Rank 11 | Rank 12 |
| --- | --- | --- | --- |
| A, always | n | p | q |
| S, always | p | n | q |
| D0 | n | p | q |
| D1 | n | q | p |
| T0 | p | n | q |
| T1 | q | n | p |

D0/D1 and T0/T1 differ only by swapping the two grade-1, mask-15 documents.
The grade-0 stratum is a singleton. Thus every source candidate set, membership
pattern, exact grade/missing-ID-at-rank vector, and grade/mask reciprocal mass
is identical throughout the orbit. A/S are unchanged. This satisfies the
stronger membership-mask constraint, not merely the earlier grade-only version.

Every prefix document has F score at least 2/69. Every tail candidate has
score at most 2/70, so the nine prefix documents always fill the first nine
slots. Each of n,p,q has score at least 2/72, while each filler has score at
most 2/73. Therefore the tenth result is exactly the highest-scoring member
of n,p,q. No filler can affect the head.

The following are exact F score numerators over a common denominator 536760:

| Orbit state | n | p | q | Tenth document |
| --- | ---: | ---: | ---: | --- |
| D0,T0 | 15192 | 15264 | 14910 | p |
| D0,T1 | 15192 | 15193 | 14981 | p |
| D1,T0 | 15192 | 15229 | 14945 | p |
| D1,T1 | 15192 | 15158 | 15016 | n |

All winners are strict; the smallest winning gap is 1/536760 in state D0,T1.
The rival n has a fixed score in this example. The actual tenth score still
changes with the winning document; this example does not assume a universally
fixed fusion threshold.

Let G be the number of relevant prefix documents under any common completion
of the unknown labels. The four P@10 values are

```
(G+1)/10, (G+1)/10, (G+1)/10, G/10.
```

Uniform independent within-stratum permutations of D and T give these four
states equal probability. Their exact mean is G/10+3/40. Consequently:

- **Positive-natural fixture:** use D0,T0 as natural. Natural F minus the orbit
  mean is exactly **+1/40**.
- **Negative-natural fixture:** use D1,T1 as natural, keeping the same A/S,
  labels, candidate sets and source grade-at-rank profiles. Natural F minus
  the same orbit mean is exactly **−3/40**.

These identities hold for every completion of all 97 unknown labels. They are
not missing-zero-only examples. Reversing the natural orientation does not
change the legal uniform permutation orbit. More generally, any finite orbit
with nonconstant performance has a member above and a member below its uniform
mean; no preservation invariant can give every member the same advantage.

This comparator is the exhaustive four-state orbit mean. Repeating each state
64 times would give the same mean for a legal 256-member control panel, but
that is not asserted to be the particular Cycle20 v2 seeded panel. The witnesses
refute a sign implication from the stated invariants or from uniform legal
shuffling; they make no new claim about Cycle20's already measured finite draws.

A complementary thought experiment makes the role of relevance explicit:
change only the fixture's fixed grades to grade(p)=grade(q)=0 and grade(n)=1.
The same within-grade swaps remain legal, the score table is unchanged, and
the four tail gains become 0,0,0,1. With D0,T0 natural, the difference from the
uniform mean is now −1/40. Each fixture preserves its own source relevance
profiles exactly. This is a constructed second labeling, not a proposed grade
change or an inference about any real document.

## Standalone exact witness replay

This replay checks the complete depth-100 construction and both signs without
searching, importing project code, or opening a data file:

```sh
python3 -B - <<'PY'
from fractions import Fraction as Q
from itertools import product

prefix = [f'g{i:02}' for i in range(1, 10)]
fillers = [f'f{i:03}' for i in range(13, 101)]
def ranking(tail):
    return prefix + list(tail) + fillers
A, S = ranking('npq'), ranking('pnq')
D, T = [ranking(x) for x in ('npq', 'nqp')], [ranking(x) for x in ('pnq', 'qnp')]
grades = {'p': 1, 'q': 1, 'n': 0}
def profile(run):
    return [grades.get(doc, ('unknown', doc)) for doc in run]
def mass(run):
    return {g: sum((Q(1, 60+r) for r, doc in enumerate(run, 1)
                    if grades.get(doc) == g), Q()) for g in (0, 1, 2)}
for variants in (D, T):
    assert profile(variants[0]) == profile(variants[1])
    assert mass(variants[0]) == mass(variants[1])
rows = [(15192,15264,14910), (15192,15193,14981),
        (15192,15229,14945), (15192,15158,15016)]
heads = []
for i, (d, t) in enumerate(product(D, T)):
    runs = [A, d, t, S]
    assert all(len(run) == len(set(run)) == 100 and set(run) == set(A) for run in runs)
    ranks = [{doc: r for r, doc in enumerate(run, 1)} for run in runs]
    scores = {doc: sum((Q(1, 60+r[doc]) for r in ranks[:3]), Q())/3
                   + Q(1, 60+ranks[3][doc]) for doc in A}
    assert tuple(scores[doc]*536760 for doc in 'npq') == rows[i]
    head = sorted(A, key=lambda doc: (-scores[doc], doc))[:10]
    assert head[:9] == prefix and head[9] == ('p' if i < 3 else 'n')
    heads.append(head)
# Shared unknown prefix entries cancel identically; no assignment is needed.
tail_gains = [Q(grades[head[9]], 10) for head in heads]
mean = sum(tail_gains, Q()) / 4
assert mean == Q(3, 40)
assert tail_gains[0] - mean == Q(1, 40)
assert tail_gains[3] - mean == -Q(3, 40)
complement = [Q(1-grades[head[9]], 10) for head in heads]
assert complement[0] - sum(complement, Q())/4 == -Q(1, 40)
print('Both signs and all full-depth witness identities passed.')
PY
```

## Limits and disposition

The witnesses establish mathematical possibility, not typicality, a generative
retrieval model, a cause of the actual negative result, or novelty. They do not
make label-conditioned controls deployable. Actual attribution would require
an explicit pairing/concentration statistic and a separate identifying design;
retrofitting that explanation after seeing the sign is not proof.

No further search or real-panel optimization follows this construction. Retain
the exact counterexample as a limit on the proposed mechanism, while preserving
Cycle20's measured conclusion about its own fixed control mean.
