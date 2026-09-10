# Cycle 01 — checked sources and integration decisions

Primary pages/PDFs fetched by Codex on 2026-09-10. This is a bounded prior-work
check, not a systematic literature review or novelty clearance.

## Original RRF

Cormack, Clarke, and Büttcher, SIGIR 2009,
[Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods](https://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf).
Section1 and Table1 explicitly describe pilot testing of k, selecting60, and
keeping it fixed for later validation. The authors explain k as moderating
high ranks from outlier systems. Thus neither choosing a different k nor
reducing outlier rank influence is novel here. The old “unexamined constant”
narrative is unsupported. This source does not establish clone invariance or
optimality of60 for our truncated generated runs.

## Dependence-aware ensemble learning

Jaffe, Fetaya, Nadler, Jiang, and Kluger, AISTATS 2016,
[Unsupervised Ensemble Learning with Dependent Classifiers](https://proceedings.mlr.press/v51/jaffe16.html)
([paper](https://proceedings.mlr.press/v51/jaffe16.pdf)).
The paper models groups of dependent classifiers and estimates their structure
and reliability from multiple unlabeled instances under statistical assumptions.
It establishes an adjacent research tradition worth evaluating before inventing
another agreement-based weighting scheme. It is not a ready-made guarantee for
truncated document rankings, query-varying expertise, or LLM agents. Any mapping
to our setting must state those assumptions and test their failure modes.

## Claude design review: accepted and corrected

Native Fable5.1 coordinated four Opus5 scouts. Their useful proposals led to
query-level aggregation, exact asymptotic ordering, source-copy interventions,
and the separately frozen depth/tail extension. The literature scout lacked
web tools because the root invocation excluded them. Its references were a
verification queue; the primary-source checks above were performed separately.

Review is fallible. Do not inherit these errors from the original memo:

- Choosing the same k in every training fold is compatible with valid CV;
  it does not prove full-data leakage. Test membership boundaries directly.
- A derived sufficient condition for coverage dominance is not a necessary
  condition. k500 need not equal the exact asymptotic ordering, but absence of
  the bound does not prove that any particular pair is outside that regime.
- Canonical k=0 is mathematically a valid reciprocal-rank parameter with
  one-based positive ranks, although it is outside this cycle's frozen grid.
- REF validation calls `fuse_ref_score_mix` with thresholds .35/.60. Defaults
  .25/.55 and other exploratory `fuse_ref` functions are not the evaluated call.
- An imprecise interval does not prove a zero effect or absence of information.
  No post hoc |delta|<.020 stopping threshold was adopted.
- Repeated samples from a stochastic model are not necessarily exact copied
  evidence. The retrieval clone invariant alone does not establish how many
  votes model samples should receive or how an agent ensemble should perform.
- Dave's standing authorization already covers ordinary research model calls;
  no new recurring permission gate was adopted from the memo.

The geometry and tail protocols retain their pre-run contents. Corrections and
interpretation belong here and in the final report, not inside frozen receipts.

## Results review: accepted and corrected

The same native coordinator resumed successfully, using one Opus5 tail-evidence
scout and Fable5.1 synthesis. It found no material implementation bug and
explicitly retracted the earlier CV-leakage claim. Its proposal to obtain a
different evidence source is accepted as a feasibility-first next direction.
The following stronger interpretations are not adopted:

- Shortening the rank range reduces the kernel contrast; this is a plausible
  alternative explanation for the cap interaction. “Mostly kernel flattening”
  was not isolated by the experiment. Retain it as a hypothesis.
- The n6 OOF result is held out from each fold's parameter training but remains
  development evidence after historical search. Neither fact cancels the other.
- Sparse judgments cannot show that lexical rankers lack useful specialists.
  A neural/dense source can have different evidence without guaranteeing
  independence, expertise, or better judgment coverage.
- The exact-copy counterexample proves failure of clone invariance. It does not
  characterize all forms or degrees of source correlation.
- An interval crossing zero does not justify closing a branch as negligible.
  A future equivalence/stopping claim needs an explicit meaningful-effect bound
  and an observation plan capable of resolving it.
- The next neural-source proposal requires concrete run access, document/query
  conventions, provenance, and observed judgment coverage before its effect
  analysis is frozen. Do not treat “one public run” as an acquired artifact.

The final report describes a mixed result with a useful pivot, rather than
accepting the review's blanket “clean negative” characterization.
