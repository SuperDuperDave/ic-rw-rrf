# Adaptive rank fusion: testing an attractive idea against a strong baseline

**Draft for the Independent AI & Product Builder website — 2026-09-10.**
Research in progress. This is a case-study handoff, not a claim of a new
state-of-the-art retrieval method. See the [current audit](../_sessions/RESEARCH_STATE.md)
before reusing numerical claims.

## Short project description

I explored whether search results could be combined more intelligently by
treating agreement, disagreement, and specialist matches differently. I built
an evaluation harness and a sequence of adaptive fusion methods, then tested
the ideas across different combinations of rankers. Broader tests showed that
an early improvement was specific to one configuration. That changed both the
research direction and the claims I was willing to make.

The project records the useful failures as well as the promising results:
what I expected, what the experiments showed, and which question became worth
asking next.

## The research story

**Question.** When several search systems rank the same documents differently,
can their pattern of agreement tell us how to combine them? Reciprocal Rank
Fusion provides a simple starting point: add contributions that decrease with
each document's rank. The project explored query weighting, document routing,
document-by-ranker confidence, regime-aware modulation, and supervised selection.

**Early signal.** One confidence-based method, v5, improved NDCG@10 from about
0.3645 to 0.3800 in a four-ranker configuration on TREC DL 2019. That was
encouraging enough to investigate, but it was not evidence of broad superiority.

**The correction.** Adding rankers reversed the comparison, and the original
gain did not replicate on the 2020 query set. A subsequent regime-aware method
recovered much of the lost ground. Its mean across four 2019 configurations was
0.3919, alongside 0.3910 for ordinary RRF—too close to establish a general win.
On the 2020 queries, REF scored 0.4393 versus Vanilla's 0.4483. These historical
means reproduced in the September restart's
[validation run](../_sessions/evidence/2026-09-10-ref-validation.txt).
[Historical result tables](../results/v6.0-regime-aware-fusion-results.md)

**Other directions.** I explored supervised selection and alternatives involving
pairwise preferences, score information, learned rank decay, and different
aggregation operators. Several failed in the tested setup. These outcomes help
define the next experiments; they do not rule out whole classes of methods.

**The next loop.** A canonical rerun confirmed a six-ranker gain from 0.4073 to
0.4273 NDCG@10, while the aggregate result remained uncertain and both tested
annual transfers lost. A source-copy counterexample showed that smoothing cannot
guarantee independence from repeated evidence. Capping lists at30 reduced that
configuration's fixed-k contrast from about+0.0201 to+0.0026. A follow-up then
exposed a measurement limit: too few judged examples to tell whether a specialist
corroborated deep in another list is more useful than an isolated one.
[Cycle01 report and reproducible figure](../results/cycle01-2026-09-10/REPORT.md)

**Current frontier.** The question became sharper: when a source disagrees,
what tells us it has different useful evidence? The next step is to obtain a
meaningfully different retrieval source and audit whether its specialist results
are observable before designing another method. A new source may help; it does
not guarantee independence, correctness, or adequate judgments.

**How collaboration shaped the research.** A Fable5.1 Claude coordinator used
four Opus5 scouts to examine the design, then resumed with one evidence scout
to critique the results. Codex implemented the experiments and integrated
independent checks. Critique changed the experiment, and numerical evidence
changed the question. Reviewer mistakes were preserved and corrected too.

## What the project demonstrates

- Turning an intuition into equations, code, baselines, and falsifiable tests.
- Following unexpected results and correcting an attractive initial claim.
- Preserving failed hypotheses so future work starts with better information.
- Using AI collaborators for implementation, independent audits, and review
  while keeping evidence and research judgment inspectable.
- Building a portable session memory and friction-improvement loop so a paused
  research project can resume without losing its context.

## Evidence and publication notes

The standard-library [harness](../evaluation/trec_eval_harness.py) runs a
synthetic demo without downloads. [Included runs](../data/README.md) support
evaluation of the historical experiments; regenerating raw inputs has additional
dependencies and a hashing reproducibility issue identified in the audit.

Keep these limits beside the story: small query sets, related MS MARCO data,
generated lexical/character-based rankers, extensive exploratory selection, and
no established improvement across independent domains. The v7 headline p-value
compares against v5, not ordinary RRF. There is no supported “minimum 50 labels”
threshold, proof of optimality, or novelty claim about tuning k.

The existing specifications and May notebooks are historical artifacts. Current
qualifications live in RESEARCH_STATE. The brief can showcase an inspectable
research process now; a new technical contribution still needs its own related
work and independent evaluation. [PLANNING](../_sessions/PLANNING.md) separates
the next source-feasibility step from parked algorithm promotion. The separate
website task owns integration and publication.
