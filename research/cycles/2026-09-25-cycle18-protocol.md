# Cycle18 — fixed family weight, changed outputs

Date: 2026-09-25. Prospective to the two new variant run bodies and their
comparative outcomes; retrospective development on already used query units.
Owner: Codex coordinator. Freeze this protocol, implementation, tests, independent
verifier and input plan before downloading or evaluating the new runs.

## Question and decision

Do the metadata-nominated BITEM variants improve the existing useful hybrid
when total lexical weight is held fixed? Let A=BITEM_BL, D=BITEM_df,
T=BITEM_stem and S=BioinfoUA-emb. With one-based reciprocal rank vectors
`a,d,t,s`, k=60, retain exactly 100 candidates per source:

- H = a+s, the existing cycle17 hybrid.
- F = (a+d+t)/3+s, the family mean plus S.
- A, D, T and S alone are fixed references, never a label-selected best member.

H also equals (a+a+a)/3+s. The primary F−H therefore replaces two literal copies
at identical coefficients and matched total reciprocal-score mass. It changes
source content, quality, support and candidate access, not error independence.
The new arms C=3a+s and V=a+d+t+s are not evaluated. Their matched substitution
question is legitimate but would spend this loop on a new 3:1 total weighting.
The existing 1:1 comparison needs fewer new policies and directly tests H.

**Hypothesis:** the fixed substitutions yield positive mean binary P@10 F−H.
**Distinguishing prediction:** its exact missing-label lower bound is positive.
An upper bound at most zero excludes positive improvement for this panel; an
interval spanning zero remains unresolved. A zero lower bound with positive
upper bound allows equality or gain, not identified strict improvement.
Interpret F−S and the fixed standalone references before proposing practical
value beyond existing methods. No novelty or general superiority is claimed.

A separate structural prediction is that F's top-ten sets cannot all be produced
by merely varying A's nonnegative weight against S. This is a capability
question, independent of the effectiveness prediction; escaping that family may
help, harm or make no relevance difference.

## Inputs, ranking and labels

Use all 30 Round1 query IDs, 1–30, with no eligibility filter or query dropping.
Reuse the exact cycle17 A/S runs, opaque full-line ID inventory and chronological
late qrels pinned in `2026-09-25-cycle18-input-plan.json`. Download only D and T
from the exact NIST links/metadata recorded there: expected combined 2,086,575
bytes, at most 3,000,000 total, one attempt each, 60 seconds each. No new corpus,
model inference, topics, label purchases, provider-generated grades or search.
Public acquisition receipts allowlist HTTP metadata; raw headers remain ignored.

Source numeric scores are finite exact Decimals, descending then ascending
string document ID for ties; ignored supplied ranks may be nonnegative integers.
Deduplicate only exact full ID-inventory lines; do not tokenize multiword lines.
Reject duplicate query/document run rows, foreign query IDs, nonfinite scores,
unknown run IDs, fewer than 100 or more than 1000 rows per query. Freeze the
first 100 canonical documents of each source. Source syntax summaries precede
labels; no outcome-based repair or source substitution follows a failure.

All fusion scores are exact rational sums with ascending string-ID ties. H and
A/S top-ten orders must match the saved cycle17 policies; stop if they differ.
This is an explicit exact-arithmetic contract for new F, not silent revision of
historical floating scores. Candidate universe U is A100∪D100∪T100∪S100 per
query; U0=A100∪S100 is the original accessible pool. H has zero contribution
outside U0 and remains unchanged. Store candidate/source ranks and exact scores.
Do not rescale or rerank the family mean before adding S.

Read the one pinned late snapshot only after constructing rankings/diagnostics.
Literal qrel grades 0/1/2 remain intact; binary relevance is 0 for grade0 and
1 for grades1/2. Missing grades stay unknown. Retain syntactically valid literal
qrels outside the run inventory without adding candidate IDs. Do not inherit
cycle17's narrower U0 label restriction for the newly expanded candidate union.
No new global addition-only claim or early/late phase is made.

## Exact measurements

Primary contrast F−H; fixed secondary contrasts F−S, F−A, F−D, F−T and H−S.
Report all six policies' conventional missing-zero P@10 means, every per-query
contrast, and sharp bounds from canceling shared head documents. For each
remaining document let c=(I_left−I_right)/10. Known grades contribute c*y;
unknowns contribute [min(0,c),max(0,c)]. Average these quantities over all 30
queries using exact fractions. Record known, lower, upper, width and unknown
support; these are missing-label bounds, not confidence intervals. No p-values.

For F versus H record every entrant and exit, four source ranks, grade/unknown,
and original-pool membership. Each entrant counts once; do not pair multiple
entrants arbitrarily to displaced documents. Report total changed slots
D=sum_q |F10\H10|, changed-query count, and the label-free absolute bound D/300.
No minimum D threshold is imposed: the previous H−S interval width is not a
minimum meaningful effect. When D=0 the primary effect is identically zero.

For each candidate, decompose `(d−a)/3+(t−a)/3` into shared-support rank shifts,
retained-list arrivals and departures, using the original ranks unchanged.
The terms must reconstruct F−H's score difference exactly. Distinguish new
support relative to A from new candidate access relative to U0. This is a score
identity, not an additive or causal decomposition of the nonlinear P@10 effect.

## Label-free scalar-representability diagnostic

Question: is there a finite w>=0 such that scores w*a+s on fixed U0 reproduce
F's top-ten SET for each query? Internal head order is irrelevant to P@10.
Do not select w, evaluate its effectiveness, fit a query rule or sweep a grid.

If F has a head document outside U0, record coverage impossibility first. Else,
for every head x and nonhead y in U0 impose
`w*(a(x)−a(y)) >= s(y)−s(x)`, with strict inequality exactly when y precedes x
under document-ID ties. Intersect rational bounds with w>=0. Preserve open/
closed endpoints, unbounded upper endpoints, zero-slope impossibilities and
boundary witnesses. Compute per-query feasibility separately, then the common
intersection. Empty common intersection alone excludes only a single common
weight, not all query-dependent weights. No infinity endpoint is an admissible w.

Record any strict Pareto witness: excluded y has both a(y)>a(x) and s(y)>s(x)
for an admitted x. Such a pair certifies nonrepresentability for that query,
without requiring new head access. General contradictory endpoint witnesses are
also valid; absence of a Pareto witness does not establish feasibility.
A feasible interval is not a calibrated inference about source dependence.

## Verification, resource bounds and stop

Use the standard library, exact fractions and deterministic sorting; no seed is
needed. Tests exercise independent synthetic fixtures: identical variants;
changed scores without changed heads; signed missing-label cancellation;
feasible/empty/open/singleton scalar intervals; ID-tie strictness; zero slopes;
coverage failure; individually feasible but globally inconsistent queries;
score decomposition and unchanged historical H/A/S. Do not derive expected
values by calling the same implementation being tested.

An independent verifier reconstructs all rankings, coefficient bounds, structural
ledgers and scalar feasibility without importing the cycle18 implementation.
It checks source/output hashes before and after. NIST's already pinned trec_eval
checks all six policies' missing-zero P@10 against the full raw late qrels.
These are verification steps, not extra effectiveness experiments or samples.
Keep producer and verifier in independent 300-second wall bounds; retain any
failed outputs and exclusive output directories. A compute-bound failure may
justify a separately recorded implementation correction, never a changed source,
query, metric or winning configuration.

Stop this experiment after exactly the two new bodies, six fixed policies,
structural diagnostics, one label snapshot, independent verification and assessed
Buddy/Opus review. No weight grid, alternative normalization, best-source search,
metric switch, new rescue rule or targeted judgment acquisition follows from
its sign. Preserve a failed or unresolved result. Then continue the active
research goal by choosing a distinct question from the evidence; any promoted
performance claim needs separate untouched evaluation.
