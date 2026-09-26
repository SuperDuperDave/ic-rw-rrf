# Cycle18 — independent contrast-triangle and Pareto interpretation check

Date: 2026-09-25. Read-only derivation from the completed, independently verified
Cycle18 policy and analysis artifacts. This adds no rankings, metrics, judgments,
configuration search, or independent sample. Owner: bounded verifier worker.

## Evidence and check

Checked these fixed files:

- `results/cycle18-2026-09-25/interpretation-ledger.json`, SHA256
  `9e96a5df73e443a5c02a2194426b41aff76dc2ddc29c67b5912189becdff81d2`.
- `results/cycle18-2026-09-25/run/policies.json`, SHA256
  `5d065f82672b6ee7744e12857ff3aedddc9bcde9206c6dba46e184ded1c90305`.
- `results/cycle18-2026-09-25/run/analysis.json`, SHA256
  `4676a4bd95706a160ab9dc2dc8ea063cd591c7353073b59898ebcc5518e94875`.

A separate inline standard-library check, without importing the producer or
verifier, reconstructed signed supports from the saved top-ten sets, matched
every triangle-support document and coefficient to `analysis.json`, and summed
the known binary grades with `Fraction`. It checked the ledger's source hashes,
unknown-support lists, all stored Pareto cases and their copied candidate fields,
membership flags, support grades, and per-query F−H/F−S entries. All matched.
It also enumerated all 1,024 completions of the ten triangle-support unknown
query-document labels to verify the identities below. This is exhaustive
algebraic validation of existing bounds, not a new relevance experiment.

## Exact triangle

Let `k` count relevant labels among these nine unknown query-document pairs:

| Query | Document |
| --- | --- |
| 3 | `92smham8` |
| 4 | `yjay3t38` |
| 5 | `2g5uxglk` |
| 5 | `ezmiwwzi` |
| 7 | `u5tvbej3` |
| 13 | `1xxrnpg3` |
| 16 | `o44k9zll` |
| 25 | `betpeary` |
| 26 | `kv3363qh` |

Each belongs to H's head and neither F's nor S's head. Its coefficient is
−1/300 in the mean F−H contrast and +1/300 in H−S. Let `y` be the binary relevance
of query 17 / `201jppkd`, which belongs to both F and H but not S. It contributes
+1/300 to H−S and F−S and cancels from F−H. Thus `k` is an integer from 0 to 9
and `y` is 0 or 1; no probability distribution is assumed.

The known-label constants are respectively 6/300, −1/300, and 5/300. Therefore,
for every common completion of the missing labels:

```
F−H = (6−k)/300
H−S = (k+y−1)/300
F−S = (5+y)/300 = (F−H) + (H−S)
```

These identities give exactly the recorded marginal bounds:

| Contrast | Sharp bound |
| --- | --- |
| F−H | [−1/100, 1/50] |
| H−S | [−1/300, 3/100] |
| F−S | [1/60, 1/50] |

F exceeds H when `k <= 5`, ties it when `k = 6`, and falls below it when
`k >= 7`. The extra label `y` cannot settle F−H. H exceeds S when `k+y >= 2`,
ties it when `k+y = 1`, and falls below it only when `k+y = 0`.

F−S is positive for every completion because the nine shared uncertain labels
cancel, not because they have been resolved. The two wider contrasts are
coupled through the same labels; their bounds cannot be treated as independent
rectangles or as independent statistical evidence. For example, F−H at its
lower endpoint requires `k=9`, whereas H−S at its lower endpoint requires
`k=y=0`; those endpoints cannot hold together. If F−H is nonpositive, H−S must
be positive. If H−S is nonpositive, F−H must be positive.

This identifies F's positive difference from S on the fixed panel, conditional
on supplied grades, while leaving the primary incremental value over H
unresolved. It does not establish general superiority, source independence,
statistical confidence, or the probability of any missing-label completion.
The score-decomposition and scalar-capability findings do not decide `k`.

## Pareto ledger interpretation

The ledger contains every stored strict Pareto witness: queries 7 and 17. In
each, the excluded document has strictly larger A and S reciprocal contributions
than the admitted F-head document, while F ranks the admitted document above
it. This certifies that no finite nonnegative scalar weight on A against S can
reproduce that F-head set. The excluded document need only belong to U0 outside
F's head; it need not belong to H's head.

| Query | Admitted F head | Excluded witness | Excluded in H head? | Grades available on contrast support |
| --- | --- | --- | --- | --- |
| 7 | `6hep2lin` | `llqpfhwg` | Yes | Both grade 2 |
| 17 | `wmfcwqfw` | `h3mdrikn` | No | Admitted grade 2; excluded absent from all six contrast supports |

For query 7, the positive-positive witness pair itself contributes zero to
binary F−H. The other entrant is known positive and the other exit is unknown,
giving the recorded query F−H interval [0, 1/10]. The witness does not identify
that remaining label or a positive incremental effect.

For query 17, the actual F−H exchange is admitted `wmfcwqfw` for `jc9ugexn`,
both grade 2, so the query's F−H effect is exactly zero. The Pareto witness
`h3mdrikn` is not that exit. Its
`grade_if_on_contrast_support: null` arises because it is absent from all
recorded contrast supports; the check did not consult its raw qrel. The field
therefore does **not** establish that the document is unjudged. More generally,
this nullable convenience field can also be null for an unknown label on
support, so support membership must be checked before interpreting it.

Both examples demonstrate a representational distinction without establishing
that escaping scalar weighting caused a relevance gain. No document grades
were inferred from witness status, source scores, or null convenience fields.

## Disposition

All claimed triangle identities and ledger entries passed. No artifact or
frozen-code correction is needed. Preserve the distinctions between shared
missing-label uncertainty, scalar nonrepresentability, and measured relevance;
the note makes no acquisition or further-experiment recommendation.
