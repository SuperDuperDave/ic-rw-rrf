# Cycle17 — allow zero in the ignored submitted-rank column

The first ID-list correction passed its gate. The next preparation stopped at
A's first run row because its supplied rank is0. Preserve the
[second failure](../../results/cycle17-2026-09-25/corrected/prepared/failure.json)
and every prior source, test, protocol and receipt unchanged. No policy or
relevance-label analysis had run.

A subsequent full **label-free syntax inventory** of the two acquired runs
found30000 rows per source,1000 for each of the30 topics; A supplies ranks0–999,
S1–1000. All60000 rows have six fields, finite numeric scores, unique query/doc
pairs and exact membership in the full-line official ID set. The supplied rank
tokens are canonical nonnegative integers. No effectiveness or label content
was examined. The [inventory](../evidence/2026-09-25-cycle17-run-format-audit.json)
records these observations without candidate or score selection.

[NIST's submitted-run rules](https://ir.nist.gov/trec-covid/round1.html) explicitly
ignore the supplied-rank column and order by decreasing numeric score. The
original protocol's positive-only syntactic requirement was unnecessarily
strict for this unused column. Allow canonical **nonnegative** supplied ranks;
continue rejecting negative or noninteger tokens. Preserve the raw supplied
rank in output metadata and compare it honestly with canonical ranks. Do not
silently relabel A's recorded ranks as one-based.

Canonical rankings and RRF ranks remain **one-based**, computed exclusively
from the same Decimal score and document-ID tie rules. No supplied-rank value
enters fusion. Everything scientific is unchanged: sources, retained depth,
query cohort, five policies, primary/other contrasts, qrels, bounds and stops.
The full-line ID correction remains in effect. There is no new acquisition,
input editing, query exclusion, candidate substitution or label-driven repair.

## Separately versioned implementation

`evaluation/cycle17_minority_exchange_compatible.py` layers the new compatibility
reader over the immutable original and first corrected adapter. To reuse the
original validations, it temporarily increments only the submitted-rank field
for parsing, then restores the exact submitted metadata and recomputes its
disagreement count. Scores, IDs, canonical order and all policy/analysis code
are untouched. Tests compare positive-rank behavior to the unchanged reader,
exercise zero-based metadata, and reject malformed/negative ranks.

The independently owned verifier has a separate nonnegative-rank reader; it
does not import or inspect the primary algorithm. Its tests verify that supplied
rank origins do not alter canonical order. Pin both new implementations/tests,
this amendment, the syntax inventory, the prior corrected preflight/binding
and the second failed preparation in an augmented compatible preflight. Retain
all prior frozen identities. The compatible initial binding must preserve the
original acquired byte identities and explicitly report zero additional GETs.

Use exclusive `results/cycle17-2026-09-25/compatible/{prepared,early,late}`
directories. Freeze the policy bytes before the first qrel join, then perform
the planned additional-label acquisition only after successful early results.
Every other provenance and stopping gate from the original protocol applies.
