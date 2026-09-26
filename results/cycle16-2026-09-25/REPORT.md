# Weight geometry and the protected minority question — cycle16

This cycle combines primary-literature review, exact synthetic counterexamples,
Buddy's repository-based critique, and three turns with Claude Opus 5.5 at high effort. It
parks the proposed fresh-collection family-weight trial and returns to a smaller
question: does the existing panel contain known-relevant documents supported
only by the retained minority source? No new fusion method or collection has
been evaluated. The numerical cycle15 results remain unchanged.

## A useful counterexample

Giving a better source more weight need not improve a fused ranking. Consider
one query with eight documents; only r is relevant. Four identical lexical
lists rank `abrdefgh`; S ranks `draefghb`. With one-based k60 RRF:

| System | Relevant rank | Binary nDCG@10 |
| --- | ---: | ---: |
| Four-list aggregate A | 3 | .500000 |
| S alone | 2 | .630930 |
| B: weight 1 for every list | 2 | .630930 |
| C: weight 1/4 for each lexical list, weight 1 for S | 3 | .500000 |

S is better than A, yet C is worse than B. All scores are strictly ordered,
and exact rational score margins establish the ranks. Every pair reversal
toward C follows S's preference; the relevant document still falls because
another source-preferred nonrelevant document overtakes it. This refutes an
initial review inference, not an empirical estimate of how often it happens.
[Complete construction and replay](../../_sessions/cycles/2026-09-25-cycle16-weight-counterexample.md).

The same example shows that removing genuine duplicate votes does not guarantee
effectiveness: C exactly fuses one unique lexical list with S, yet B beats it.
Copy invariance and retrieval quality are distinct requirements. Separate exact
examples show that averaging family scores protects uniform replication of
every member but not copying one member, and that reranking a group before
outer RRF differs from averaging its original reciprocal scores.
[Geometry and proofs](../../_sessions/cycles/2026-09-25-cycle16-weight-geometry.md).

## Why the proposed transfer is parked

C is mathematically equivalent to multiplying S's original weight by four.
Its comparison with B can measure that coefficient intervention, but cannot
identify dependence as the explanation. Prior work already includes weighted
and hierarchical group-balanced RRF; its group reranking differs from C.
[Primary-source review](../../_sessions/cycles/2026-09-25-cycle16-prior-work.md).

Buddy favored retaining a prospective fixed C/B test with S and H references.
Claude initially proposed a pooled shared-miss analysis, then withdrew it after
the confounding and endpoint counterexample were checked. Its resumed review
favored parking C/B and checking whether minority-only support exists. Codex
adopted that smaller question, with corrected depth and missing-label boundaries.
This is a research-priority decision, not proof that weighted RRF or a future
replication has no value. [Assessed disagreement and receipts](../../_sessions/cycles/2026-09-25-cycle16-integration.md).

## Retained-support census

The [protocol](../../_sessions/cycles/2026-09-25-cycle16-support-protocol.md)
was fixed before computing the census. Existing SciFact was already used for
cycle15, so this is post hoc descriptive development. The primary observable is
the count of known-positive query/document pairs in S's retained 1000 but outside
the union of the four retained lexical lists, each capped at 200. It includes
all S depths, with a fixed top 10/deeper partition. Unjudged documents receive
no relevance label. An exact label-free sufficient condition checks whether
ten lexical score contributions already exceed the best S-only contribution.

Across 300 queries and 339 known-positive query/document pairs:

| Retained support | Known-positive pairs | Queries containing such a pair |
| --- | ---: | ---: |
| Both lexical union and S | 314 | 277 |
| S only | 21 | 21 |
| Lexical union only | 2 | 2 |
| Neither | 2 | 2 |

Query counts overlap and must not be added. Of the 21 S-only positives, **6**
are in S's top 10 and **15** are at ranks 11–1000. **16** were already available
in P's per-query candidate pool, while **5** were outside it. Absence from the
retained lexical union therefore differs from absence from original access.

Every query has S-only candidates. On **300/300** queries, the tenth-largest
pure lexical contribution T is strictly greater than the strongest actual
S-only contribution V. Ten lexically supported documents therefore already
outrank every S-only document before their additional S contributions. The
saved B rankings confirm **0/3000 S-only top 10 entries**. This establishes a
specific admission barrier in the fixed lists and weights; it does not require
assuming correlated errors. [Counts](support-census/summary.json),
[per-query exact certificates](support-census/perquery.json),
[all positive support records](support-census/positive-support.json).

The directional presence hypothesis passes. These 21 examples form an observed
development set for the narrowly defined support question. They do not establish
that protected slots, reweighting or a learned gate would improve performance:
extra candidates may displace useful results, and unjudged candidates are not
known negatives. S and H already beat B on cycle15, so simply restoring some
S results is not sufficient evidence for another elaborate method.

## Reproduction and stopping

The census checks committed input identities, cohort/depth constraints and
numeric ranks before analysis; it does not regenerate retrieval or fusion.
All source, protocol, input and output hashes are in the
[execution manifest](support-census/manifest.json). Historical evidence is
unchanged. Standard-library command used from the repository root:

```bash
timeout 300 python3 -B evaluation/cycle16_support_census.py --output results/cycle16-2026-09-25/support-census
```

Outputs use exclusive creation; a later reproduction must supply a new path.
The 12 synthetic tests cover depth partitions, missing support, strict/equal
certificate boundaries, label handling, malformed inputs and custody-before-row
parsing. The census stops here under its declared rule; no rescue method, C/B
effectiveness run or second intervention follows from the positive count.

An [independent verifier](../../_sessions/tools/check_cycle16_census.py) rebuilt
the support partition and certificates from all seven original run files using
integer common denominators, without importing the census implementation. Every
per-query, known-positive and aggregate field matched, with unchanged input and
output hashes. [Verification receipt](independent-census.json).

## Next decision

Park further tuning of this four-list apparatus while preserving its results,
cases and certificate. The next task is an applied feasibility contract where
rescue and harmful admissions can be assessed against equally informed simple
references, using adequate judgments or explicit missing-label bounds. S's six
head cases are already available from S itself; any more elaborate method must
justify what it adds. No replacement method or new collection is selected.

The final Claude critique supports the branch stop but overstates several
limits of positive-only labels and possible comparisons. Those qualifications,
including the unverified claim about H returning the same cases, remain visible
in the [integration](../../_sessions/cycles/2026-09-25-cycle16-integration.md).
Buddy's different recommendation is preserved. This is a checked collaborative
research result, not consensus used as evidence of truth.
