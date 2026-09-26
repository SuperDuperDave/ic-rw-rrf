# Cycle16 — endpoint quality does not determine a weight intervention

## Pre-test hypothesis and bounded design

2026-09-25. Test the assertion that better mean standalone S effectiveness than
lexical aggregate A predicts improvement when moving from `B=4L+s` to `C=L+s`.
Here L is the mean of four lexical reciprocal-rank contribution vectors, A
sorts L, and s is S's reciprocal-rank contribution. A counterexample to the
universal inference has `nDCG(S)>nDCG(A)` but `nDCG(C)<nDCG(B)`.

Use synthetic full-coverage permutations only, four identical lexical lists,
one S list, one query, and one relevant document. Rankings use one-based k60
RRF, exact `Fraction` scores, and ascending string-ID ties. Primary metric is
binary nDCG@10 with full synthetic qrels; with one relevant document this is
`1/log2(rank+1)` through rank10 and zero thereafter. Exact rank inequalities
establish the metric inequalities without relying on floating-point agreement.
No random seed, benchmark inputs, labels from an existing collection, or model
calls. Baselines are standalone A and S and the specified B weight vector;
C is the sole intervention.

First check a constructed eight-document fixture. If it fails, enumerate
small permutations with a bounded search of at most three minutes. Stop after
one strict counterexample, exact-score verification, and an explanation of its
interpretation. Do not search for favorable benchmark outcomes or build a
general parameter grid. Also determine whether C has any oracle-upper-bound
status under these definitions.

## Result

**The first fixture is a strict counterexample.** No enumeration or further
search was needed. One query is sufficient; its effectiveness is also the
collection mean. This is a compact example, not a proof of minimum size.

All four lexical lists are `a b r d e f g h`; S is `d r a e f g h b`.
Only r is relevant. Every list covers the same eight documents, all source
and fused scores are strictly ordered, and all documents fit inside cutoff10.
The canonical source weights are B=`[1,1,1,1,1]` and
C=`[1/4,1/4,1/4,1/4,1]`.

| System | Exact fused order | Relevant rank | Binary nDCG@10 |
| --- | --- | ---: | ---: |
| A | a b r d e f g h | 3 | 0.5000000000 |
| S | d r a e f g h b | 2 | 0.6309297536 |
| B | a r b d e f g h | 2 | 0.6309297536 |
| C | a d r e b f g h | 3 | 0.5000000000 |

Thus `S−A=+0.1309297536` but `C−B=−0.1309297536`. These signs are exact:
`1/log2(3)>1/log2(4)=1/2`. Decimal formatting is not the evidence for the
inequality.

The decisive score comparisons are also exact:

- B: `score(r)−score(b)=53/132804>0` and
  `score(r)−score(d)=1387/1906128>0`.
- C: `score(r)=125/3906`, `score(d)=125/3904`, hence
  `score(r)−score(d)=−125/7624512<0`.

B has already used S's preference to move r above b. Increasing S's relative
weight lets S's nonrelevant leader d overtake r, while lexical leader a stays
above r. Standalone S places a below r again. The relevant rank therefore
worsens between B and C despite the superior S endpoint. Every pair reversal
still follows S's preference, as the prior geometry note predicts; nDCG is not
monotone in that preference shift. The endpoint means alone do not identify
which nonrelevant documents cross the relevant document at intermediate weights.

This refutes a universal implication from `mean(S)>mean(A)` to `mean(C)>mean(B)`.
It does not estimate how frequently the pattern occurs on actual collections,
or rule out a separately supported empirical tendency. Such a tendency needs
evidence beyond the endpoint inequality. Actual SciFact outcomes remain untouched.

## C is not an oracle upper bound

C is a prespecified feasible weight vector; it neither receives relevance labels
nor maximizes the evaluation metric. Here B and S both strictly outperform it,
so it is not an effectiveness upper bound over even these named alternatives.
Because all four lexical lists are identical, C also exactly equals RRF of one
unique lexical list and S. Even genuine clone removal supplies no effectiveness
upper-bound guarantee.

An oracle choosing the best system per query using known labels, or maximizing
the metric over a declared weight set containing C, would upper-bound C on that
finite evaluation panel by definition. Its privileged selection procedure and
candidate set must be named. Those properties do not transfer to C merely
because its family weights are motivated by redundancy.

## Reproduction and stopping

The following repository-root command uses only Python 3's standard library.
It independently constructs the four systems, verifies every exact score is
distinct, checks the relevant ranks, and checks the decisive rational margins.
No seeds or external inputs are used. Stop condition met after this fixture.

```bash
python3 - <<'PY'
from fractions import Fraction as F
from math import log2
L = ('a', 'b', 'r', 'd', 'e', 'f', 'g', 'h')
S = ('d', 'r', 'a', 'e', 'f', 'g', 'h', 'b')
assert set(L) == set(S) and len(set(L)) == len(L) == 8
lexical = [L] * 4
scores = {}
for name, weights, lists in [('A', [1]*4, lexical), ('S', [1], [S]),
                             ('B', [1]*5, lexical+[S]),
                             ('C', [F(1,4)]*4+[1], lexical+[S])]:
    scores[name] = {d: sum(F(w, 61+ranking.index(d))
        for w, ranking in zip(weights, lists)) for d in L}
orders = {name: tuple(sorted(L, key=lambda d: (-ss[d], d)))
          for name, ss in scores.items()}
ranks = {name: order.index('r')+1 for name, order in orders.items()}
assert ranks == {'A': 3, 'S': 2, 'B': 2, 'C': 3}
assert all(len(set(ss.values())) == len(L) for ss in scores.values())
assert scores['B']['r']-scores['B']['b'] == F(53, 132804)
assert scores['B']['r']-scores['B']['d'] == F(1387, 1906128)
assert scores['C']['r']-scores['C']['d'] == -F(125, 7624512)
for name, order in orders.items():
    print(name, ''.join(order), ranks[name], 1/log2(ranks[name]+1))
print('All exact assertions passed.')
PY
```
