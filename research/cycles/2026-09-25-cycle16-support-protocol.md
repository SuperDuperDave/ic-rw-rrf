# Cycle16 — retained-support census (post hoc development)

Written before implementing or computing this census on the existing SciFact
rankings. Cycle15 outcomes motivated the question; this is **post hoc descriptive
development**, not an untouched test, effect estimate, learned rule or new fusion.
It follows Buddy's emphasis on fixed inputs and Claude's return to the original
minority-rescue question, with the coordinator's corrections below.

## Question, predictions and decision

Does the existing panel contain known-relevant documents supplied by S but absent
from all four retained local lexical lists? These are concrete examples of the
original escape-channel target under this pipeline's200/1000 retention choices.
**Primary observable:** number of distinct (query, known-positive document) pairs
present in S and absent from the union U of the four retained lexical lists.
Report the number of queries contributing those pairs. Directional hypothesis:
this count is nonzero. It is a presence hypothesis, not an effect-size claim.
Report its fixed S-rank1–10 and11–1000 partition; neither replaces the full count.

The reference is membership in U versus S, not a rival effectiveness score.
For every qrel pair, report the exhaustive four-way partition: U-and-S, U-only,
S-only, neither. Also partition S-only known positives by presence in the
original per-query P pool, separating access from retained support. No relevance
is inferred for unjudged documents. Repeated query/document pairs count once;
multiple positives within one query are not independent query observations.

**Decision fixed before the census:** if the full S-only known-positive count
is zero, park this panel for developing that specific S-only rescue rule: it
has no *observed positive examples* under the present labels and depths. This
does not prove there are no truly relevant unjudged examples or no other
specialist mechanism. If the count is positive, preserve the cases as a finite
development feasibility set; no algorithm is promoted or automatically run.
If only ranks11–1000 contribute, a head-only rule has no observed examples here,
but deeper rescue remains a separate possibility. Either outcome stops after
the census and independent verification. C/B transfer and pooled miss odds stay
parked. No threshold, router, weight sweep, new labels or collection selection.

## Fixed supplementary observables

Read the already frozen B ranking: count S-only entries in its top10, and report
explicit-qrel membership among them. Denominator is all3000 B top10 entries;
the number of queries with any such entry is also reported. This checks whether
that channel actually enters B at the specified cutoff; it does not decompose
B−A or establish that absence elsewhere explains its nDCG difference.

For each query with at least one S-only candidate, optionally sharpen the
algebraic exclusion statement with a **predeclared exact certificate**, computed
for every such query: let T be the tenth-largest sum of its four lexical
`1/(60+rank)` contributions (zeros for absence) among U; let V be the largest
S reciprocal contribution among S-only candidates. If `T>V`, at least ten
lexically supported candidates beat every S-only candidate even before adding
their nonnegative S contributions. Therefore no S-only candidate can enter B's
top10. Count certificates and list each T,V as exact fractions. Ties (`T=V`)
do not certify exclusion. If fewer than ten U candidates exist, no certificate.
This sufficient condition is label-free; failure is not admission or relevance.
Well-populated lists alone do not imply the condition. Compute no new ranking.

## Input custody and implementation

Use only these committed cycle15 numeric outputs:
- `transfer/{bm25,bm25_tuned,tfidf,ql_dirichlet,S,P,B}.trec`;
- `independent-audit/official.qrels`, the already verified positive-only export.

Pin SHA256 identities of the protocol, census source and all eight inputs in an
execution receipt **before** opening input rows. Validate input digests against
the cycle15 manifest/official evaluator command where recorded, and against
checkpoint19139bd. Historical files are read-only. Fail on duplicate rows, query
cohort mismatch, noncontiguous one-based ranks, nonfinite scores, invalid IDs,
nonpositive/nonbinary qrels, missing lexical candidates in P, or unexpected
depths (lexical<=200, S=1000, P<=1000, B>=10). Exactly300 qrel queries must appear
in every run. Use string IDs and rank columns, not reconstructed score sorts.

Implementation uses Python standard library, set membership and exact Fraction
arithmetic for the certificate. No packages, network, provider or raw-text reads.
One execution with a five-minute ceiling and no fallback/input substitution.
Write a new result directory with exclusive creation, source/input/protocol
identities, per-query rows, known-positive support rows and aggregate counts.
Test the meaningful edge cases before data: a deeper S-only positive despite
zero head positives; absent-from-both; U-only; inside-P versus outside-P S-only;
strict certificate, equality failure and fewer-than-ten failure. An independent
reader must reconstruct the counts and certificates from frozen numeric inputs
without importing the census implementation. No changes to cycle15 evidence.

## Interpretation boundary

S-only means absent from retained lists, not independent, correct, uncorrelated
or unreachable by another depth/scorer. A positive inventory just supplies
observations. Even if B excludes every known-positive S-only case, an escape
rule could introduce many unjudged or nonrelevant candidates and displace useful
ones. Any later rule needs an equally informed simple S/H baseline, matched
candidate budget and an untouched evaluation; it cannot be justified by this
count alone. C remains a fixed weight heuristic, not an oracle bound.
