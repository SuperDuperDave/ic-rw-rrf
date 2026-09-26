# Cycle17 — one-slot minority exchange, then additional-label revelation

Frozen before any selected run or qrel body is acquired or parsed. This is a
retrospective applied study of a convenience pair, with a prospectively recorded
analysis for this project. Published TREC-COVID high-level outcomes were seen
during prior literature and metadata searches; selected-pair scores were not.
No untouched-domain, random-sample, clinical-utility or novelty claim follows.

The user explicitly requested recursive loops that include experiments. The
opening Opus review proposed an exchange ledger. Codex corrects its missing-label
bounds and unmatched shared-source comparison here. Buddy receives that assessed
design while implementation proceeds; later advice cannot silently change a
frozen analysis. This cycle contains two linked measurements under one contract.

## Fixed sources and units

Use TREC-COVID Round 1, all 30 topic IDs `1` through `30`, April 10 document IDs.
The [input-feasibility note](2026-09-25-cycle17-input-feasibility.md) owns checked
primary metadata, exact public URLs and exposure disclosure. Choose:

- A = `BITEM_BL`, the named automatic Elasticsearch baseline.
- S = `BioinfoUA-emb`, the lexicographically first submission of the inspected
  BioinformaticsUA team, using BM25 plus biomedical DeepRank neural reranking.

These are selected by method/access metadata, not effectiveness. BITEM's other
variants establish provenance context but are not acquired or used here. A and
S use different source fields/document subsets; the contrast does not isolate
neural computation or source independence. We test a simple two-list hybrid,
not a continuation of the parked four-local-lexical weighting apparatus.

Parse all submitted rows (1–1000 per query), validating six fields, finite
numeric score, positive integer supplied rank, nonduplicate query/document IDs,
full topic cohort and membership in NIST's `docids-rnd1.txt`. Submitted rank
columns do not control order: NIST specifies decreasing numeric score. Use exact
Decimal score comparison and ascending string document ID on tied scores, then
retain **100 per source** (or all if shorter, with at least10 required). Record
full depths/ties and supplied-rank disagreements. These choices are not a
byte-for-byte replay of the official evaluation's unspecified tie order.

The common top100 window is a fixed bounded retrieval-output setting, selected
before trigger counts. No alternative depth/pair or minimum-trigger fallback.
"S-only" always means absent from **A's retained100**, not absent from its full
submission or the corpus. Membership in A's full submission is a descriptive
ledger field, so truncation and full-list absence remain distinguishable.

## Loop 1: fixed one-slot policy

**Hypothesis:** admitting one high-ranked S-only result that a simple hybrid
excluded produces a positive finite-panel mean binary P@10 difference over H.
**Competing explanations:** it displaces better candidates; any benefit comes
from generic S-priority rather than minority priority; or there is no eligible
opportunity on the fixed pair. No error-dependence mechanism is identified.

H = canonical one-based, k60, equal-weight RRF of retained A and S. Sum with
`math.fsum`, zero for absence, descending computed score and string-ID ties.
Use the same candidate union; no new retrieval. Save A,S,H top10 before labels.

A query is eligible iff H top10 contains no S-only document and S top10 contains
at least one S-only document. The minority candidate m is the highest-S-ranked
such document. It is necessarily outside H top10. On precisely those queries:
- M = H first9 followed by m, replacing only H rank10.
- J = H first9 followed by j, where j is the highest-S-ranked document in S
  top10 outside H top10, regardless of A support. m witnesses J's feasibility.
On every other query M=J=H. Also report A and S alone. These five fixed policies
are all references; no best member is selected from test labels.

J matches M's trigger and one-slot budget. M−J compares minority-priority to
generic S-priority as policies; admitted document ranks/content can differ, so
it is not an isolated causal effect of minority status. Save whether M=J.

**Primary:** equal-query mean binary P@10 difference M−H across all30 queries,
including zeros. Fixed usefulness contrasts: M−J, M−S, H−S, H−A. Eligibility
counts and triggered-only summaries are descriptive, not replacement primaries.
No p-values, query router, weight grid or secondary nDCG computation.

Read `qrels-covid_d1_j0.5-1.txt` only after canonical inputs, policies, eligibility
and all source/protocol identities are saved. Grades1/2 mean binary positive;
grade0 is an explicit negative; absent is unknown. Validate four fields, unique
query/document pairs, grade domain0/1/2, finite positive judgment-round field
(half-rounds allowed), exact30-topic cohort, and valid Round1 IDs.

For each contrast form coefficients
`c(q,d)=(I[d in left10]−I[d in right10])/10`. Cancel shared documents first.
For known labels sum `c*y`; for unknown labels the sharp lower endpoint adds
`min(c,0)` and upper adds `max(c,0)`. Average over30 queries using exact Fraction
arithmetic; unknown relevance is independent as a logical completion variable
per (query,document), not a statistical independence assumption. Uniformly
setting all unknowns0 or all1 is generally NOT the contrast's bounds.
Report conventional unknown-zero P@10 separately, explicitly a benchmark convention.

The exchange ledger records admitted/displaced IDs, S and full-A rank/membership,
exact known grades or unknown, rescue (positive replaces explicit zero), harm
(explicit zero replaces positive), neutral (same known binary value), unresolved
(unknown on either side), unchanged queries, and known-positive admissions,
explicit-negative admissions and known-positive displacements. Unresolved cases
remain unresolved; pooled judging does not guarantee complete head labels.

**Stop/decision:** no eligible changes → no opportunity for this exact policy
on this pair. Lower M−H>0 → every allowed completion favors this finite contrast;
upper M−H<=0 → positive mean improvement is excluded under the label contract;
otherwise its sign is unresolved. Apply the same descriptive sign classification
to other contrasts. M−J=0 for identical policies supplies no special-priority
evidence. M−H alone does not justify complexity over S/J. No population claim,
threshold search or automatic new algorithm follows any branch.

## Loop 2: change observations, keep every policy fixed

After Loop1 artifacts are complete and hashed, acquire
`qrels-covid_d1_j0.5-5.txt`: NIST's **chronological/total Round1** judgments,
not a later-round residual or cumulative collection. It maps all judging rounds
to Round1 topics and valid document IDs, preserving the early cumulative grade
where present, otherwise using the earliest later judgment. This is the explicit
reason for using Round1 chronological data rather than TREC-COVID Complete.
[NIST definitions](https://ir.nist.gov/trec-covid/data.html).

Freeze every Loop1 policy/rank/candidate/eligibility byte. Check late qrels with
the same parser. Verify that every early pair exists with the exact same grade
in the late file. If any removal or revision appears, stop this second phase
with its mismatch ledger; do not silently choose replacement labels or proceed
as an addition-only experiment. The raw source failure remains preserved.

**Hypothesis:** added labels reduce at least one of the five predeclared contrast
interval widths; the primary reduction is the M−H width. Measure early/late
widths, sign status changes, added labels on nonzero coefficient support,
resolved exchange categories and source/reference P@10 under the convention.
Late intervals must nest within early ones. No narrowing is an informative
negative for the fixed contrast; no eligibility does not authorize a new pair.
If all primary contrasts were already point identified, later unchanged values
are a robustness check, not another performance replication.

This is new evidence about the same queries, not independent samples or held-out
generalization. Later judgments may concern changed document content despite
official Round1 mapping. Bounds are conditional on treating the supplied official
grades as labels for that query/document unit. They do not correct grader errors
or estimate what was known at the 2020 submission deadline. Related NIST pool
extension studies already exist; no novelty claim about additional judging.

## Execution and verification bounds

Inputs are only the two named runs, valid-ID list and two named qrels. The
acquisition plan pins URLs, metadata and byte ceilings before GET; initial
acquisition excludes the late qrels. One attempt per file, curl/HTTPS, no retry
or alternate mirror. Caps:4MiB per run,1MiB IDs,1MiB early qrels,2MiB late qrels;
12MiB total maximum,60seconds/file,300seconds each analysis. A host header is
not a cryptographic pin: preserve acquired SHA256 before any row parsing.
Reject unexpected run byte lengths, HTML responses or changed declared metadata.
Raw files and HTTP logs stay ignored. Durable outputs contain numeric IDs/ranks,
label-derived observations, identities, exact commands and source attribution.

Implementation uses Python standard library plus existing curl; no package,
corpus download, inference, new judgment service or private-project access.
Record code/protocol/plan hashes before acquisition and verify them before and
after each phase. Exclusive output directories; no overwrite or outcome-tuned
repair. Save a failure artifact if a gate fails. Primary code and meaningful
synthetic tests must stabilize before body acquisition. Tests include duplicate/
invalid IDs, canonical score ties, no-eligibility, M=J/M!=J, K-like shared control
absence, exact bound sharpness by exhaustive binary completions, shared-doc
cancellation, unknown-zero inside bounds and monotonic addition of labels.

An independent reader reconstructs canonical ranks, fusion, eligibility, all
policy outputs and exact bounds from raw inputs without importing primary code.
Official P@10 can additionally check the binary unjudged-zero convention using
the already installed pinned NIST evaluator; it is not a validation of unknown
truth labels. Stop after the two frozen phases, independent audit, and assessed
Buddy/Opus interpretation. A subsequent experimental loop needs its own newly
recorded prediction; no automatic sweep follows.
