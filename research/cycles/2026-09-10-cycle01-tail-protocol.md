# Cycle 01 extension — tail evidence and depth intervention

Frozen before the first numerical tail-probe run, 2026-09-10. This extension
was selected after Claude's four-scout design critique and inspection of the
completed geometry summary. It is exploratory, not an untouched confirmation.
Do not edit this protocol after its manifest is created; append corrections
in a separate artifact.

## Question and competing explanations

Does increasing RRF k help by promoting broadly covered documents with weak
support deeper in source lists? Is apparent specialist isolation partly an
artifact of observing only the top of each list?

- **H2a:** The k60→200 effect depends on available source depth. Truncation
  should change its magnitude and which documents move.
- **H2b:** The effect reflects ordering even when each source has equal depth;
  equalizing lengths will not necessarily erase it. Equal lengths do not imply
  equal candidate sets, so this arm cannot isolate coverage alone.
- **H4a:** A top10 document absent from every other source's top30 is more often
  relevant when another source supports it below rank30 than when all other
  sources omit it. This is an association, not a causal mechanism or a new
  ranker's measured performance.
- **Null/alternatives:** No stable relation; relevance-judgment coverage,
  source identity, owner rank, query difficulty, or candidate-generation depth
  explain the observed difference. Missing judgments are not known irrelevance.

## Fixed comparison contract

Use the same five configurations, source files, qrels, query eligibility,
one-based canonical RRF and document-ID ties as the geometry cycle. Main
comparison: k200 minus k60 in nDCG@10. No k selection or method search here.

Evaluate three arms: original full supplied lists; truncate every source to
the shortest supplied list for that query; cap each source at top30. Keep qrels
and queries fixed across arms. Record absolute means and paired query deltas,
top10 entrants/exits, and documents whose positions change. Include both the
active arm's source ranks/coverage and the original full-list ranks/coverage.
Do not present source interventions or ensemble repetitions as new queries.

Define specialists using original full lists only: owner rank≤10, absent from
every other source's top30. Such a document has a unique owner. Partition into
tail-supported (any other source rank>30) and isolated (absent from every other
source). Report document counts, judged counts/fractions, relevant grade≥2
among judged, and all-candidate gain/relevance with unjudged assigned zero for
that explicitly named metric. Separately report owner-rank1–3 and4–10 strata.
For paired comparisons, average within each query/group, then compare only
queries containing both groups; state the actual eligible query count. Pooled
document rates remain descriptive. A difference does not remove confounding.

## Provenance and checkpoint

Use standard-library Python, synthetic tests for classification and denominator
edge cases, a new output directory, and start/end hashes of input data, source
code, and this protocol. Never overwrite the geometry artifacts. Save per-query
observations sufficient to challenge the summary. Review results independently
with the existing Claude coordinator before deciding whether to build a new
method, seek new data, or pivot. Stop this extension after these fixed arms and
strata; do not search thresholds to improve the result.

Planned command:

```bash
python3 -B evaluation/cycle01_tail_evidence.py --protocol _sessions/cycles/2026-09-10-cycle01-tail-protocol.md --output results/cycle01-2026-09-10/tail
```
