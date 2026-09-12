# Cycle14 — prospective transfer preparation

Starting checkpoint: `cc421896df9c2c35b88c795bbd307273abfc6481`.
This preparation precedes new collection acquisition, retrieval and evaluation.

**Question.** Can one previously unused collection support an auditable test of
adding a learned sparse source to the project's fixed lexical fusion?

**Candidate chosen before source inspection:** BEIR SciFact. Scientific abstracts
provide a domain/document-unit change from MS MARCO passages; its small collection
is a practical candidate for economical reproducible retrieval. These are selection
reasons, not predictions based on published comparative performance. Verify the
source metadata. No alternate collection search this cycle if this route fails.

**Hypothesis.** The source-addition direction observed under cycle13's diagnostic
may extend to this domain. Alternatives include a reversal, a metric-dependent
direction, or an apparently similar comparison that actually changes candidate
access or source identity. Preparation distinguishes feasibility and comparable
semantics, not these performance alternatives.

**Bounded inspection.** Read local ranker implementation/provenance and primary
SciFact/BEIR/artifact metadata. Inspect at most three public artifact families for
SciFact. Prefer existing score-bearing BM25 and SPLADE++ EnsembleDistil runs or a
small reproducible retrieval path. Do not inspect published performance tables,
compute effectiveness, acquire full inputs, install retrieval packages, train,
or launch a parameter/dataset search during this preparation.

**Observable and gate.** Record collection/split identity, access and usage terms,
document/query ID compatibility, ranker/model identity, candidate access, retained
depths, tie/rank conventions, available scores and exact source revisions where
available. A runnable transfer needs compatible auditable inputs plus an explicit
evaluation contract. Distinguish an exact-pair replication from a mechanism-level
adaptation; an unavailable exact pair is not an impossibility result.

**Metric bridge to resolve before execution.** Original work uses nDCG@10 while
cycle13 used unnormalized top10 RBP contribution with p=4/5. A proposed transfer
must name one primary metric, graded-gain convention, unjudged convention, query
eligibility and authoritative evaluator check. Reuse established readers/fusion
where compatible; expose any required changes without modifying frozen evidence.

**Review and stop.** Independent local/source audits run in parallel. One compact
Claude critique will challenge the proposed comparison and acquisition decision,
with exact-model selection and a bounded invocation recorded before launch. Stop
after a reviewed protocol and concrete input preparation plan, or a documented
feasibility limit. No empirical retrieval/model batch belongs to this cycle.

No new label acquisition, router tuning on the nine old query reversals, reopening
of the parked arithmetic laboratory, or website publication is implied.
