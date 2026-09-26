# Cycle 21: value and arithmetic review of submission-group aggregation

Date: 2026-09-26. Bounded design scout; no new run bodies, qrel bodies, or
performance tables read. No effectiveness computation or acquisition authorized
by this note. The coordinator owns the prospective experiment contract and its
execution gate.

## Recommendation and scope

One complete, frozen census is informative. Its distinct question is whether
combining all automatic submissions of each eligible team at total weight one,
then adding the fixed S source at weight one, improves P@10 over the expected
P@10 of selecting a member uniformly and combining that member with S. This
adds new rank outputs to the previous quartet evidence. It remains an evaluation
on the same 30 queries and shared late labels, not independent labeled transfer.

The current metadata frame contains 29 eligible teams and 81 automatic runs:
six pairs and 23 triples, after the exact BITEM and BioinformaticsUA exclusions.
All members must enter. Equal team weighting gives a two-member team the same
primary weight as a three-member team. Do not select the best member, winning
team, closest method, or a favorable subset after acquisition. Those changes
would turn the census into source selection.

Call these **submission groups**, not identified dependent families. The
comparison measures the return from aggregating their submitted outputs. It
does not hold a single member's available candidate set fixed, and does not
separate candidate access, score alignment, or latent error dependence. The
mean-member baseline is a concrete simple randomized policy's expected metric;
it is not the best member and is not a trained selector. That limitation is
acceptable for this bounded question and should remain visible in the report.

The primary alone does not establish improvement over S. A predeclared G−S
contextual contrast can answer that separate question. A positive primary
does not imply every team benefits. A nonpositive primary does not establish
that the earlier BITEM F−S finding was idiosyncratic: the comparator changed.
Do not add a correlation-versus-gain analysis or further parameter grid.

## Metadata cautions that change the interpretation

The official type and owner fields define eligibility; method prose does not
reclassify an automatic run as manual. Examples in the metadata show why:

- unipd.it and ielab include automatic pseudo-relevance feedback. Automatic
  does not mean no feedback, no learned components, or no development labels.
- Covidex and Elhuyar combine lexical retrieval with neural reranking within
  one team. Team identity is not a homogeneous architecture definition.
- Technion-RRF explicitly fuses other approaches from its own submission
  group; unique_ptr also has an internally fused output. The external average
  therefore need not average independent primitive signals.
- DMIS descriptions reuse Covidex scores. Distinct teams do not ensure
  independent provenance. Query fields and document facets also differ across
  several groups.

These are reasons to limit the claim, not new exclusion criteria. Literal
duplicate rank outputs under distinct eligible run IDs remain distinct members
of the stated submission census; descriptive duplicate reporting is permissible,
but post hoc deduplication changes the estimand. Duplicate *run identifiers* or
ambiguous owner/type records are inventory validity failures instead.

Only metadata was inspected. One method description incidentally quotes a
pretrained model's external STS benchmark score; it was not a TREC-COVID outcome
and played no role in eligibility or this recommendation.

## Exact estimand and pair coefficients

Let T=29, Q=30, and m_t be team t's member count. For retained rank r≤100,
define a_tiq(d)=1/(60+r), zero when absent; define s_q analogously. Construct
each ordered top ten with exact score arithmetic and ascending document ID at
ties:

    G_tq = top10[(1/m_t) Σ_i a_tiq + s_q]
    H_tiq = top10[a_tiq + s_q]

The team/query effect is P10(G_tq) − (1/m_t)Σ_i P10(H_tiq). Averaging the
*scores* before taking a head is not interchangeable with averaging the member
metrics. For binary relevance y_qd, the primary is Σ_q,d c_qd y_qd, where

    c_qd = Σ_t [1{d∈G_tq} − (1/m_t)Σ_i 1{d∈H_tiq}] / (10 T Q).

Pool these coefficients by **(query ID, document ID)** before joining labels.
The same unknown pair has one binary value across all teams. The same document
under different queries is a different label pair.

For the current pairs/triples frame, use exact integer numerator

    K_qd = Σ_t [6·1{d∈G_tq} − (6/m_t)Σ_i 1{d∈H_tiq}],
    c_qd = K_qd / 52200.

Here 52200=6·10·29·30. The equivalent per-query route uses K/1740 and averages
once across 30 queries. Assert that the routes agree; do not divide the already
mean-scaled coefficient by 30 again. Each query's coefficients sum to zero.
Cancel zero coefficients before counting unknown support or bounding the metric.

With known term B=Σ_known c_qd·1{grade>0}, the sharp bounds are

    lower = B + Σ_unknown min(c_qd, 0)
    upper = B + Σ_unknown max(c_qd, 0).

Known grades 1 and 2 are positive, grade 0 is negative, and missing pairs are
unknown. Binary completions can attain both endpoints. The unknown-support
count is the number of distinct nonzero-coefficient unknown pairs, not a sum
of team counts. Benchmark unknown-as-zero results remain separately labeled.

### Which endpoint averages are sharp?

Within a team, averaging bounds for G_t minus each H_ti is sharp: for a fixed
pair, the fixed G_t indicator makes all nonzero member-comparison coefficients
have the same sign. Across teams, both G_t and its mean-member comparator vary;
coefficients can oppose. Averaging team lower bounds can be too low, and
averaging team upper bounds can be too high. Pooling first gives the sharp
primary interval. Equality holds when each unknown pair has no opposing
nonzero team coefficients.

For the separate G_t−S contrast, S is fixed across teams. Its pair coefficients
cannot oppose across teams, so averaging those team endpoints *is* sharp.
Avoid a blanket claim that averaging all group bounds is non-sharp. A single
coefficient aggregation implementation is nevertheless a clean way to evaluate
both contrasts correctly.

## Small, exact synthetic counterexamples

These fixtures use complete 100-document lists, k=60, and the same fixed S.
They were checked with a temporary standard-library Fraction calculation only.
Let P=[p01,…,p09], F=[f00,…,f87], and document IDs satisfy x<y<z. Concatenation
below gives complete orders; the nine P documents occupy every resulting head.

    S  = P + [z,x,y] + F
    R0 = P + [x,z] + F + [y]
    R1 = P + [z,x] + F + [y]
    R2 = P + [x] + F + [y,z]
    R3 = P + [y,f00,z] + [f01,…,f87] + [x]

1. **No predetermined effect sign.** Member hybrids R0+S and R3+S have boundary
   documents x and y, respectively. The average of R0 and R3, plus S, has
   boundary z. Thus the effect is [y_z−(y_x+y_y)/2]/10. Setting z positive and
   x,y negative gives +1/10; reversing these labels gives −1/10. Equal labels
   give zero. Averaging rank scores has no general Jensen-style performance
   guarantee or predetermined concentration effect.
2. **Cross-team bound cancellation.** Team 1=(R0,R1) has G boundary z and member
   boundaries x,z, so its effect is (y_z−y_x)/20. Team 2=(R1,R2) has G boundary x
   and member boundaries z,x, so its effect is (y_x−y_z)/20. With x known
   negative and z unknown, team intervals are [0,1/20] and [−1/20,0]. Their
   averaged interval is [−1/40,1/40], but the pooled primary is exactly zero
   under both possible labels of z. The shared R1 vector is intentional; two
   synthetic submissions may have identical ranks.
3. **Identity negative control.** Identical member rank vectors make G and
   every H identical, hence every coefficient zero for every label completion.
   This catches family-weight and tie-order mistakes.
4. **Equal-team normalization.** Synthetic team effects +1/10 for a pair and
   −1/10 for a triple must average to zero. Pooling members instead produces
   −1/50 and silently changes the estimand.

The first two fixtures can be repeated across all 30 query IDs without changing
their mean effects. Exhaustive binary completion of their tiny unknown support
checks sharpness directly. No research labels are needed for these tests.

## Required prospective validity checks and bounded execution

Freeze the metadata team/member map, exclusions, run URLs and publisher MD5s
before bodies. Record SHA256 and byte counts at acquisition too. A missing,
oversized, corrupt, malformed, or incomplete required run stops this attempt;
it does not justify silently dropping a member, team, or query. Streaming
transfer/decompression caps address the inventory's absent published sizes.

Validate all 30 query IDs and at least 100 distinct documents for every source
and query, with the protocol's fixed maximum depth. Reject duplicate query/doc
pairs, nonfinite scores, malformed fields, and out-of-inventory run IDs. Ignore
the supplied rank column for ordering; canonicalize by exact finite Decimal
score descending and document ID ascending, then retain 100. Preserve the
previously corrected opaque inventory-line semantics. Retain supplied-rank
metadata only as an audit field. No new policy may depend on qrels.

Build every G and H head before label joining. Replay fixed S from its pinned
canonical ranks and require identity with the existing reference. Every head
has ten unique IDs in its allowed source union. If L=lcm(61,…,160), exact group
ranking can use integer score Σ_i L/(60+r_i) + m_t·L/(60+r_S), with absent terms
zero; dividing by m_t·L is unnecessary for ordering. This is the declared
normalized score, not RRF applied again to reranked family means or member
hybrids. Use the same document-ID tie rule everywhere.

Parse the pinned late qrels once using the existing literal-label contract.
Out-of-inventory labels remain inert labels and never expand any source's
candidate universe. Use shared pair identities across all groups. Assert the
normalization identity above, zero coefficient sums, head sizes, identity
negative control, and exhaustive small-fixture bound attainment. Global sharp
width must not exceed the average team width. An independent reconstruction
should verify all heads and pair coefficients, not just the final mean.

This frame entails 81 member hybrids plus 29 group hybrids across 30 queries:
3300 heads, or 33,000 displayed head entries. Parsing up to roughly 2.43 million
input rows is likely the dominant work if each query has 1000 supplied rows.
A sequential parser can discard full-depth rows after validation and retaining
100. Integer reciprocal units avoid repeated Fraction work while preserving
exact ties. A synthetic maximum-shape timing check before freezing code is
appropriate; the intended 300-second phase limit remains a stopping rule, not
a reason to sample members or queries. Reuse the established binary P@10
convention and independent arithmetic; a new official export of every head is
not necessary for this design question.

After this one complete panel, report the primary sign/bounds and limitations.
Per-team results are descriptive, not invitations to choose a new winning
family. Continuing requires a distinct question and prospective contract.

## Evidence consulted

- `_sessions/cycles/2026-09-26-cycle21-metadata-protocol.md`
- `results/cycle21-2026-09-26/inventory.json` (metadata only)
- `_sessions/cycles/2026-09-25-cycle20-integration.md`
- `_sessions/cycles/2026-09-25-cycle20-opus-results-memo.md`

The Cycle 20 assessment's corrections carry forward: its fixed base was a/3+s,
the proposed concentration mechanism was not measured, and the old quartet
optimization is closed. This census offers a new finite comparison; it is not
an attempt to repair that mechanism story or reopen the quartet search.

## 2026-09-26 addendum: assessment of Buddy's concrete challenge

Read the task-bound reply in `_sessions/local/cycle21/buddy-replies.json`.
This assessment paraphrases the argument rather than reproducing provider raw
text. No run/qrel bodies, performance tables, or old control outputs were read
or recomputed for the assessment.

### Value criticism: retain the limitation, reject the exclusive framing

Buddy correctly distinguishes the proposed group-versus-mean-member primary
from the earlier F−S result. He also correctly objects to treating a census as
a concentration-mechanism test, a deployment recommendation, or independent
transfer evidence. Those claims are outside the proposed estimand. The
opportunity-cost challenge is legitimate: a new finite-panel fact is not
automatically worth collecting simply because acquisition is possible.

His assertion that mechanism is the only remaining useful question is a
research-priority judgment, not a consequence of Cycle 20. The census asks a
different operational question: on the complete eligible submission panel,
does retaining and combining all outputs at fixed total group weight outperform
uniformly selecting a member before adding S? Its possible consumer is the
research decision whether this aggregation policy merits a later, separately
designed evaluation on untouched queries/corpora. This is a limited reason to
run one bounded census, not a claim that a positive local mean establishes
general value. A nonpositive bound rejects the frozen strict-positive panel
prediction; an unresolved bound leaves it unresolved and closes this attempt.

Before bodies, make that decision use and stopping interpretation explicit.
If the coordinator does not value this finite comparison, closing the branch
is reasonable. That choice should be recorded as an opportunity-cost decision,
not as a proof that missing labels force an uninformative result.

### Pool participation does not determine sharp contrast width

Let B be the known-label contribution of the pooled pair coefficients, and let

    N = −Σ_unknown min(c_qd,0),  P = Σ_unknown max(c_qd,0).

The exact interval is [B−N, B+P], with width W=N+P=Σ_unknown |c_qd|. A positive
lower endpoint requires B>N; a nonpositive upper endpoint requires B≤−P.
Named pool-contributor fractions determine neither B nor N nor P. Judged-set
membership alone also does not determine them: the rankings determine which
pairs occur in the contrasting heads, with which signed coefficients, and
which contributions cancel across teams. Pooling prioritization can inform
a coverage expectation, but it is not a deterministic relation between
run-level contributor share and this contrast's width.

Three counterexamples use the preceding exact fixtures or their identity case:

1. A group with no contributing member may reproduce the same retained ranks
   across all members. Then G=H_i and every coefficient is zero, for any qrels
   and any unknown-label fraction. Its sharp width is zero. Non-contributors
   may also retrieve documents judged through other contributing sources or
   another label-collection round; contributor status does not make their
   retrieved documents unjudged.
2. In the R0/R3 fixture, suppose x and y are known negative and z is known
   positive through other pool sources. The group effect is the point +1/10,
   although neither group member needs to have contributed to judging. Swap
   those known labels and the point is −1/10. Both nonzero signs are compatible
   with zero group pool-contributor share.
3. In the two-team cancellation fixture, both x and z may be unknown. The
   individual intervals are then [−1/20,1/20], but their equally weighted
   pooled contrast is identically zero: opposite coefficients cancel for each
   unknown pair. Looking at source participation or averaging group coverage
   misses that cancellation completely.

These are logical counterexamples, not forecasts about the unseen 81 runs.
They refute “low contributor share means wide bounds by construction.” The
converse expectation is also insufficient: contributor status does not by
itself say that every document entering a retained-depth fusion head was
judged. Neither a wide nor a narrow realized interval should be predicted here
as a mathematical necessity.

The proposed requirement that an interval be capable of *excluding zero* also
differs from the existing nonpositive falsification cell, upper≤0. An exactly
zero effect excludes the strict-positive prediction without excluding zero.
Do not silently strengthen the stopping criterion to demand a strictly
negative result on that side.

Therefore do not add the suggested contributor-share gate, projected-width
threshold, or performance-sensitive subset selection. A data-dependent bound
gate would require at least the frozen heads and pair coefficients; it cannot
be manufactured from this metadata census. Computing the full predeclared
contrast after acquisition is already the proposed bounded observation. Keep
the existing metadata validity, resource, and complete-panel gates distinct
from an unsupported assurance of statistical resolution.

### The proposed old-control correlation is not a causal mechanism test

Buddy suggests correlating control gain with a grade-split fraction of changed
head slots whose stratum score ranges bracket the realized head threshold.
That statistic needs a precise definition before even an association is
testable. More fundamentally, it can reuse the same relevant entrants that
define the response, and the realized threshold depends on the same scores
and selected head. This makes a sign-consistent association compatible with
pure metric accounting, without establishing harmful natural concentration.

A minimal algebraic counterexample: every control shares nine natural head
documents and replaces the same known-negative tenth document. Let the sole
entrant's relevance be y_b, and suppose every entrant's stratum score range
brackets that control's threshold. The relevant bracketed share of changed
slots is then X_b=y_b, while its P@10 gain is Y_b=y_b/10. Whenever both relevance
values occur, their correlation is exactly +1 by definition. This identity
holds regardless of the source of the score variation or whether natural
alignment created a harmful concentration mechanism. It demonstrates the
identification problem; it does not claim that the actual controls have this
form. More generally, gain equals (relevant entrants minus relevant exits)/10,
so a grade-split changed-slot predictor requires care even when the identity
is not exact.

Freezing a new scalar after the old gain distribution and primary sign were
seen would make this a post-outcome exploratory association. The 256 controls
remain interventions on the same fixed query panel, not 256 new labeled
samples. A wrong-sign result could challenge a precisely stated association
prediction, but neither sign alone establishes or refutes the broad causal
concentration account. Identifying that mechanism would require a distinct
intervention that isolates its proposed contribution and accounts for other
paths to head changes, not merely correlating an outcome-derived statistic.

Do not substitute this analysis for the census or reopen the closed quartet
under a mechanism label. No such computation was performed. The valid update
from Buddy is to sharpen the census's decision purpose and modest interpretation;
his pool-width claim and suggested correlation do not warrant changes to its
membership, primary metric, coefficient bounds, or stopping rule.

## 2026-09-26 prospective submission-depth correction

Before any new run body was acquired, the coordinator checked the official
Round 1 format and corrected the proposed minimum-depth gate: valid submissions
may provide 1..1000 documents per query. Consequently 100 is a retention cap,
not a required member depth. Retain min(100, submitted depth), require every
source/query pair to be present and nonempty, and report both full and retained
depths. The pinned S source still supplies 100 documents per query and guarantees
ten-document hybrid heads. Preserve every eligible short submission and its
fixed member coefficient; do not rescale for its available reciprocal mass.

This supersedes the earlier minimum-100 member validity sentence above. It
changes no grouping, metric, head tie rule, bound formula, or stopping rule.
The complete-100 synthetic witnesses and their checked conclusions remain
unchanged. Add a short-member synthetic case to verify the corrected format
contract before freezing the Cycle 22 implementation.
