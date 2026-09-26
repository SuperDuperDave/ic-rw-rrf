# Cycle20 — grade-preserving rank-alignment intervention

Status: final contract for one actual execution, to be bound by the separate
preflight before any control heads or outcomes. Independent and Opus prospective
review complete; the grade+membership refinement and interpretation corrections
are adopted. Buddy's substantive critique is assessed and will return to Opus
with the result. Existing cycle18 data and outcomes are known. After the
preflight, preserve this file and all frozen sources without in-place amendment.

## Question and scope

Does the observed arrangement of the two lexical variants contribute to the
family hybrid beyond their marginal rank quality, candidate membership, and
reciprocal-score mass allocated to each membership class?
This controlled diagnostic changes rank alignment while preserving those. It is
not an untouched evaluation, a new deployable policy, proof of independent
errors, or a substitute for the failed exact-pipeline transfer.

Keep all 30 original TREC-COVID Round1 topics, the canonical retained 100 lists
A=BITEM_BL, D=BITEM_df, T=BITEM_stem, S=BioinfoUA-emb, and the same pinned late
judgments. The original D run includes stemming as well as frequency boosting;
source nicknames are shorthand, not causal ablations. Sources and candidate
pools are unchanged. No new ranking/document/qrel body, model call or annotation.

The natural policy is the already measured F=(a+d+t)/3+s, H=a+s, one-based k60
reciprocals, absent=0, score-descending/document-ID-ascending canonical ordering.
The intervention acts on the canonical retained rank vectors; it does not
pretend to regenerate raw retrieval scores or submissions.

## Fixed control generator

Use exactly 256 draws b=0..255. For each draw, numeric-order query, source D then T,
and exact known grade g=0,1,2, split further by the fixed document membership
mask across original A/D/T/S retained sets (bits 1,2,4,8 respectively). Gather
IDs with the same (grade,mask) in original rank order; iterate grades and then
numeric masks ascending. Shuffle IDs only among their original occupied positions. Every
unknown query/document ID stays at its original rank, including when other
sources know/retrieve different IDs. A/S never change. Empty/singleton strata
are unchanged. No draw or query is discarded for a no-op or unfavorable result.

The seed is the big-endian integer value of SHA256 over UTF8 compact JSON:
`["cycle20-alignment-v2",b,qid_string,source_string,grade_integer,mask_integer]`, with no
spaces. Use a fresh standard-library `random.Random(seed).shuffle(ids)` for
each such stratum, starting from original rank order. Record Python version
and frozen source identities. No global mutable random stream, other seed,
strength, fraction, normalization, cutoff or draw-budget search is allowed.

Fuse every resulting control with the fixed F formula. C denotes the arithmetic
mean of their 256 P@10 values, **not** fusion of average score vectors or a new
single ranking. Persist all control top-ten heads and draw identities, plus
head inclusion counts sufficient to independently reconstruct the coefficients.

## Predictions, fixed contrasts and missing labels

Primary: mean binaryP@10 F−C over all 30 queries. The hypothesis predicts a strictly
positive sharp lower bound. Upper<=0 excludes strictly positive benefit against
this finite control panel; other intervals are unresolved. A zero interval is
an exact tie, not statistical equivalence. Every result ends this experiment.

Fixed secondary/contextual contrasts: C−H, C−S, F−H, F−S. H is the existing
simple hybrid and S the standalone reference. These guard against interpreting
natural-versus-control success as practical superiority over stronger simple
references. No best draw, policy or comparator is selected from results.

For the primary, coefficient of query/document pair is
`[256*I(d in F10) − count_b(d in control_b10)]/(256*300)`.
For C−H/S replace the numerator by `count_b − 256*I(reference10)`.
F−H/S retain their existing exact coefficients. Cancel coefficients before
joining labels. Known grades1/2 are positive, grade0 negative, absent unknown.
Sharp bounds add min(c,0)/max(c,0) for each unknown pair; missing-zero point
scores remain separately named conventions. Use exact rational arithmetic.

The displayed coefficients are already scaled for the 30-query MEAN and are
summed across pairs, with no further division. Per-query records instead use
denominator256*10 (and10 for natural fixed pairs), then aggregate those records
by averaging exactly once across30queries. These two routes must agree.
Shared unknowns are the same variables across policies. Check the
coefficient identities F−H=(F−C)+(C−H) and F−S=(F−C)+(C−S).

For these fixed-reference contrasts specifically, each pair's per-draw
coefficient has one sign or zero across draws. Therefore the average of the
per-draw sharp endpoints equals the sharp endpoints of the finite mean.
Aggregation is a clear implementation choice, not a claim to tighten those
particular averaged endpoints. This statement does not extend to arbitrary
contrasts between two varying policy sequences.

## Preserved information and interpretive boundaries

Each source retains its document set, source-membership indicators, reciprocal
score mass within each exact-grade/membership class, and every
known grade or missing-ID symbol at each rank. Thus its standalone metric
profile is identical under every common missing-label completion, including
graded rank profiles. Both U and original U0=A100∪S100 stay unchanged; the
cycle18 bound still forbids outside-U0 F admissions. Every unknown candidate's
own F contribution score stays unchanged because its positions are fixed.

What changes is rank alignment among D/T and between them and fixed A/S,
within known-grade/membership classes. The earlier unfrozen grade-only proposal
preserved membership but could move score mass between membership classes.
Opus identified that broader intervention; before outcomes, Codex chose the
narrower control as the sole arm. The earlier proposal was a valid broader
rank-assignment question, not a violation of its stated membership invariants.
Neither relationship is isolated from the other. Candidate membership overlap
and retrieval provenance remain fixed. Statistical error dependence is not
identified; document-level top-k error overlap can change. The preserved source
quality concerns relevance-sequence metrics under fixed labels/completions,
not every content-sensitive measure of redundancy or diversity. The artificial
permutations need not correspond to a realizable
retrieval model. This is evidence about that intervention, conditional on the
fixed observed labels and lists.

Qrels explicitly construct the controls and evaluate them. They are not hidden
training data, nor does labeling this operation a control make it label-free.
The unknown-symbol and membership constraints leave unjudged alignment and
between-class mass allocation untouched, so a null
result cannot exclude value in alignment the intervention did not vary.

The 256 draws are repeated interventions on the same 30 queries, not independent
labeled samples. The finite control mean is the exact target of this run;
it does not identify the entire permutation-distribution expectation. No
permutation p-value, query-population inference or exchangeability null is
assumed. Per-draw point summaries are descriptive, not an optimization search.

Freeze the interpretation with the comparison. An identified positive F−C means
natural F beats this finite mean under the declared intervention. If C−S is
also identified positive, a gain over S persists in the controls; if C−S is
unresolved, its sign is unknown and no dependence/necessity claim follows. If
C−S has upper<=0 while F−S is positive, the contrast with these particular
controls removes that finite-panel gain, not all possible alternatives. If
F−C has upper<=0, a natural advantage over this control mean is excluded; this
does not attribute the gain exclusively to marginal quality or membership.
An unresolved primary remains unresolved. No row means that all alignment was
destroyed, that one mechanism uniquely caused the gain, or that F beats H.

## Custody, checks and stopping

Before controls, pin this final protocol, producer, verifier, tests, and the
successful cycle18 policy/analysis/manifest/success, independent receipt and
`results/cycle18-2026-09-25/official-metric-check.json` NIST receipt.
The manifest identifies the exact cached late qrels by path, byte count and
SHA256. Verify that chain and raw qrel bytes directly; original private HTTP or
provider receipts are not scientific prerequisites. Rehash sources and inputs
after computation. Preserve every failure with no silent repair of frozen code.

Require exact query IDs 1..30, unique retained 100 per source, valid ranks/types,
unambiguous qrels and complete policy references. Identity permutation must
reproduce natural F/H/S heads, exact scores and historical contrasts before
controls. For every draw, check candidate sets, known-grade/missing-ID-symbol
rank profiles and exact reciprocal mass by (grade,mask). Check head uniqueness/
size and zero outside-U0 entries. Report stratum sizes and head changes as
descriptive manipulation facts. No singleton or changed-head threshold changes
the arm or authorizes another run. Assert original
files stay unchanged. Save exclusive output artifacts and a success marker only
after all checks and hashes; failures remain inspectable.

Synthetic tests cover seed determinism, exact ties, missing grades fixed in
place, membership-class mass preservation, preservation for all binary completions
of a small fixture, nontrivial
fusion changes despite preserved marginal profiles, aggregate coefficients and
the special fixed-reference endpoint equivalence. An independent implementation
must reconstruct every control head, inclusion count and numerical analysis
field, with its own scoring and signed-bound implementation.

One standard-library execution and one independent reconstruction, each capped
at 300 seconds. Any gate/runtime failure stops this frozen attempt. No new NIST
invocation is required for the unchanged simple P@10 formula if existing
authoritative metric checks and independent fixture arithmetic still apply;
document that reuse explicitly rather than claiming all control heads were
individually exported to NIST.

After one verified result, close optimization on this 30-query quartet. Further
research needs a distinct information/evaluation contract; there is no automatic
permutation variant, finer subgroup, seed sweep, label purchase or proxy grade.
