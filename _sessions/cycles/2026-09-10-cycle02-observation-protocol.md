# Cycle02 — source and observation feasibility

Frozen on 2026-09-10 before downloading the selected run bodies or measuring
their candidate/judgment coverage. This extends the earlier source-feasibility
proposal; it is not a ranking-performance experiment. Preserve after launch.

## Selection and hypothesis

Select the cached SPLADE++ EnsembleDistil source family from Castorini's public
RankLLM retrieval cache. It supplies both DL2019 and DL2020 top1000 files, about
43MB combined, with a pinned dataset revision, declared file sizes, and LFS
SHA256 identities. It uses a neural sparse representation, meaningfully different
from the existing hand-built lexical functions. It is not dense retrieval, and
different representation is not proof of independent errors or useful expertise.

Exactly three families were considered by provenance/access: TCT-ColBERT-v2
(documented generation, no small precomputed artifact established in checked
route), official IDST BERT (raw run returned401; cross-year continuity unresolved),
and this SPLADE++ cache. Selection used accessible existing artifacts, both-year
coverage, resource size, and producer documentation. No new comparative relevance
outcome was computed to choose among sources. Performance tables on navigation
pages may be visible; they are not the selection rule.

**Question:** does this source make specialist observations feasible, or do
candidate access, truncation, and missing judgments still dominate the problem?
Possible outcomes include adequate observed groups, sparse paired groups despite
many pooled documents, substantial access to candidates absent from the old
lexical lists, or a malformed/incompatible source requiring a documented stop.

## Fixed inputs and acquisition

The selection file `data/cycle02/source-selection.json` owns the pinned URLs,
expected sizes/hashes, provenance, and access/usage notes. Validate downloaded
bytes and retain raw JSONL in ignored local cache. Convert only query IDs,
document IDs, scores, and array-order ranks into one-based TREC files, preserving
ties. Do not commit passage or query text. Record observed schema, query counts,
depths, and input/output hashes without relevance evaluation. Reject duplicates,
nonfinite scores, unsafe IDs, unexpected score order, or hash mismatch.

Use the four existing lexical runs (bm25, bm25_tuned, tfidf, ql_dirichlet) and
original graded qrels for each year. Validate lexical rank origin0 and external
rank origin1, then report source positions from1. Keep all current qrel queries
with every required nonempty source; explicitly record omissions. No query is
selected by a gain, loss, or judged fraction.

## Observation inventory

Primary arm: complete supplied lexical lists plus the new source's supplied
top1000. Secondary arm: cap all five sources to
`Dq = min(200, minimum supplied source length for that query)`.
This controls list length; it does not equate candidate sets or convert
corpus-wide retrieval into reranking of the old candidate pool.

For each query/arm record source depths, candidate union/intersection, source
overlap, and top10 documents newly available relative to the original lexical
union. Report judgment counts/fractions for source top10/top30/top100/full lists
and newly available candidates. Count how often the secondary arm actually
changes an input or candidate set. Qrel membership means judged, including
explicit grade0. Unknown judgments stay unknown. Do not compute relevance rates,
NDCG, oracle gains, trained features, or effect p-values in this phase.

Define specialist candidates ONCE from the original full lists: owner top10,
absent from every other source's top30. Tail-supported means another source
contains it below30; isolated means absent from all other supplied lists.
Both labels describe the observed truncated input, not the entire corpus.
Keep this cohort and group labels fixed when capping. Record active and original
source ranks and whether each member remains visible in its owner's capped list;
cropping must not invent specialists or turn unobserved support into true absence.

Summarize candidates/judgments by new-source owner, pooled lexical owner, and
individual lexical owner, crossed with support group. Report per-query
denominators and query counts with both groups present and with judgments in
both groups. Keep fixed-cohort and visible-only summaries distinct. Repeated
documents, owners, arms, or years do not create independent queries.

## Decision and stop

This inventory can show that a proposed contrast is impossible or poorly
observed; it cannot establish a fusion improvement. Do not infer adequate power
from a raw query-count threshold. A later effect protocol must predeclare a
scientifically useful difference, precision target, selection budget, and
operation-specific null/stopping rule, using an observation plan that can resolve
them. A zero-crossing interval alone cannot show negligible headroom.

Stop this phase after the manifest, inventory, independent critique, and a
decision: proceed to a specified effect experiment, revise the candidate/label
observation plan, or change the laboratory. Do not search source families or
specialist thresholds until the desired answer appears. Preserve a useful
alternative, including a controlled known-truth agent/evidence task, if this
panel still cannot discriminate the original question.

## Reproducibility and review

Standard-library code, synthetic tests for eligibility/censoring/judgment
denominators, new immutable output directory, and start/end hashes of protocol,
selection/derived manifest, actual inputs, and code. Save query-level observations
sufficient to challenge every count. One Opus5 evidence scout and the existing
Fable5.1 coordinator can critique a completed result; more agents require a new
independent question. Codex integrates corrections, updates the map, and commits
and pushes the checkpoint under Dave's standing authorization.
