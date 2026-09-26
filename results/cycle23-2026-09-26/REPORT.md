# Cycle23 — a positive finite comparison for grouped archived outputs

Across the complete frozen frame of 29 submission groups and 30 development
queries, averaging a group's reciprocal-rank contributions and adding fixed S
has higher mean binary P@10 than uniformly choosing one group member and adding
the same S. The sharp difference remains positive under every completion of
missing labels. This is a result about the identified archived files, not a new
method, a causal dependence effect, or evidence on untouched queries.

| Contrast, equal team/query weights | Exact sharp interval | P@10 percentage points |
| --- | --- | --- |
| **Primary: G minus expected member hybrid H** | `[127/52200, 221/3480]` | **+0.2433 to +6.3506** |
| Context: G minus fixed S alone | `[113/4350, 379/8700]` | +2.5977 to +4.3563 |

G averages each team's two or three reciprocal-rank score vectors at total
coefficient one, then adds S at coefficient one. Each H combines one member with
S. The primary baseline is the expected P@10 of uniform member selection; it is
not the best member, a learned selector, or ordinary RRF across the whole census.
Teams and queries each receive equal weight. The fixed S is the previously
verified BioinfoUA-emb artifact. Scores are canonicalized before one-based k60
RRF, with at most 100 retained documents per source/query and ten output documents.

## What the uncertainty establishes

There are 1,377 unknown query/document pairs with nonzero pooled primary
coefficients. Their labels are shared consistently across every policy and team.
The lower and upper endpoints come from coefficient signs, not statistical
confidence intervals or an assumption that unjudged documents are irrelevant.
No p-value, independent-query claim, or new labeled sample is supplied.

Missing-as-zero benchmark means are G=1767/2900=0.609310, expected H=3592/6525
=0.550498, and S=7/12=0.583333. These are separate conventions; the benchmark
primary gain of 5.8812 points is not the guaranteed lower bound.

The mean of separate team primary endpoints is also positive:
`[53/52200, 3389/52200]`. Pooling shared coefficients narrows this to the reported
sharp interval; **cancellation was not necessary to identify the positive sign**.
Across teams, primary intervals are 13 positive, 2 negative, 1 nonnegative,
1 nonpositive and 12 unresolved. Thus the mean benefit is not universal benefit.
Context G−S is 21 positive, 3 negative, 1 nonnegative and 4 unresolved.

## Inputs and the preserved checksum failure

[Cycle22](../cycle22-2026-09-26/REPORT.md) permanently remains a stopped attempt:
its first archived body did not match the browser metadata MD5. Bounded diagnosis
could not establish the digest's representation. A separate
[cycle23 contract](../../_sessions/cycles/2026-09-26-cycle23-protocol.md) therefore
identifies current bytes at all 81 declared [official NIST archive URLs](https://ir.nist.gov/trec-covid/archive/archive-round1.html),
retains every original browser digest and preserves the full scientific plan.
It does not claim original submitted-byte identity where the digest differs.

All 81 fresh requests passed. Acquisition occurred 2026-09-26T05:33:56.708700Z through
05:34:20.311273Z, transferring 93,596,624 bytes in 23.60 seconds. All received files
were plain text; raw and decoded totals agree. Three browser MD5s match and 78 do
not; every discrepancy remains explicit. The first newly fetched body matches
the SHA256 recorded in the failed attempt. That is same-origin stability evidence,
not an independent origin or proof of historical submission identity. S stays
cached, so this is not an atomic contemporary snapshot of the whole ensemble.

The files contain 1,979,714 rows. All 2,430 member/query cases are present, with full
depths from 1 to 1,000; 244 cases have fewer than 100 documents. The prospective depth
cap kept those valid short lists in the frame. No team or member was dropped,
no parameter was chosen from scores, and no label was parsed before policies
were serialized. Team provenance and automatic submission status do not establish
independent rankers or absence of prior supervised training.

## Verification and reproduction

The [passed preflight](../../_sessions/evidence/2026-09-26-cycle23-preflight.json)
freezes 23 identities, including the stopped attempt and unchanged numerical code.
Forty-six combined tests passed. Independent synthetic reconstruction covered
short/gzip lists and 2.43 million rows, including both matching and mismatching
metadata digests, malformed receipts, changed hashes and missing members.

The actual producer completed in 10.64 seconds. A separate checker with its own
parsers and exact Fraction scoring rebuilt **all 3,300 ordered heads and every
source, policy, analysis and provenance field** in 11.33 seconds. A further read-only
interpretation audit independently summed the saved coefficient ledger and
confirmed both endpoint fractions and the already-positive mean team interval.
The new heads were not additionally exported through NIST's evaluator; binary
P@10 semantics reuse the earlier independently checked convention.

- [Acquisition and per-file identities](../../_sessions/evidence/2026-09-26-cycle23-acquisition.json)
- [Retained source diagnostics](run/sources.json), [policies](run/policies.json), [exact analysis and coefficient ledger](run/analysis.json)
- [Execution manifest](run/manifest.json), [independent check](independent-check.json)
- [Synthetic checks](../../_sessions/evidence/2026-09-26-cycle23-synthetic-checks.json)

The protocol contains the exact execution commands. Raw public run bodies are
ignored locally; durable artifacts preserve identities, canonical retained inputs,
heads and all evaluation evidence.

## Decision

This fixed comparison is complete and meets its positive-primary prediction.
The separate G−S context is positive too. Further optimization on these 30 queries
is not the next step. The result justifies considering a separately specified
fresh-topic test of the same grouping/comparator rule. Feasibility must distinguish
policy transfer to a new complete submission frame from exact pipeline replication;
five fresh Round2topics would still constitute a small finite panel. Dave requested a pause at this completed checkpoint. The next Buddy and Opus
review is queued for resume, with no remote task outstanding. No transfer result
is claimed here, and the closed BITEM quartet optimization remains closed.
