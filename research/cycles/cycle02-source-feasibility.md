# Cycle02 proposal — make useful dissent observable

Next-session starting point, selected after cycle01 on 2026-09-10. This is a
bounded acquisition/feasibility protocol, not a frozen performance experiment.
No new source has been downloaded or evaluated yet.

## Question

Can we obtain a meaningfully different retrieval source and enough judgments
to distinguish useful specialist evidence from isolated noise? A new source
family provides a candidate explanation, not proof of independent information.

The phase follows Claude's source-injection proposal with two corrections:
neural/dense outputs are not guaranteed to be better judged, and an imprecise
null result cannot establish negligible rescue potential. Measure both first.

## Bounded first phase

1. Inspect primary records for at most three candidate source families. Prefer
   a precomputed passage-ranking run covering the existing judged query IDs;
   use documented reproducible generation only if a small resource estimate
   justifies it. Initial verified navigation points are the
   [NIST DL2019 run catalog](https://pages.nist.gov/trec-browser/trec28/deep/runs/)
   and [Pyserini MS MARCO passage reproduction matrix](https://castorini.github.io/pyserini/2cr/msmarco-v1-passage.html).
   These pages establish discovery/reproduction routes, not that a selected
   run is freely downloadable, licensed for redistribution, or acquired here.
2. Choose at most one source family before computing comparative relevance
   outcomes. Record provenance, training/evidence type, source identity,
   availability, usage terms, expected storage/compute, candidate generation,
   query/document IDs, ranks/ties, depths, and exact artifact hashes. Do not
   select the source by its score on our already-used query sets.
3. Audit the observation geometry: overlap with the lexical core's candidates,
   actual variation in any proposed intervention, specialist group counts,
   judged fractions by source/group/query, and queries containing both groups.
   Missing judgments remain missing, including for the new source. Distinguish
   corpus-wide retrieval from reranking the supplied candidate pool.
4. Decide whether this panel could support the intended contrast. Before any
   effect analysis, specify the smallest scientifically useful difference,
   required precision, selection budget, comparison family, and stopping rule.
   Use simulation/known-truth fixtures to check the analysis when counts are
   sparse. Do not infer an adequate sample from an arbitrary query-count rule.

Stop after a source/feasibility manifest and decision. If suitable access or
judgments are unavailable, park this panel and choose either a known-truth
controlled evidence task or another openly available collection. The question
remains open; there is no reason to force another adaptive RRF variant.

## Conditional effect phase to specify afterward

Use the canonical contract and fixed k60, with a prespecified candidate-depth
policy, the new source alone, lexical-only RRF, and RRF with that source.
Separate extra candidate access from improved aggregation. Measure source-owned
specialist outcomes only where the observation plan supports them.

If oracle rescue is informative, define the permitted operation exactly before
running: for example, the best single insertion from an eligible specialist
set into the baseline top10, preserving all other relative positions and
allowing no insertion. Its nonnegative gap is only an upper bound for that
operation, not a realizable method, and incomplete judgments bias the bound.
Do not equate a nonzero oracle gap with a usable label-free routing feature.

Competing predictions: new evidence contains useful dissent suppressed by the
fixed aggregator; ordinary RRF already captures the useful extra source;
apparent gains arise from candidate access/judgment coverage; or observations
remain insufficient. Any routing feature needs a separate training/evaluation
plan. These are prospective hypotheses, not results of cycle01.

## Compute and broader bridge

Codex owns the manifest and implementation; one Opus5 scout audits provenance
and observation eligibility; Fable5.1 interprets a substantive ambiguity or
completed result. Add more agents only for independently useful questions.
The user's standing research authorization persists.

For an eventual agent branch, separately test whether a coordinator can use
information about which agent had distinct evidence. Compare equal resource
budgets, controlled evidence sharing, correlated errors, and final correctness.
Retrieval metrics and exact copied lists do not establish behavior of repeated
stochastic LLM samples. Dependence-aware ensemble literature is a starting
point, with assumptions to verify, not a ready-made solution.
