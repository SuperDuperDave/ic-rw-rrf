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
guarantee independence from repeated evidence. Capping lists at 30 reduced that
configuration's fixed-k contrast from about+0.0201 to+0.0026. A follow-up then
exposed a measurement limit: too few judged examples to tell whether a specialist
corroborated deep in another list is more useful than an isolated one.
[Cycle01 report and reproducible figure](../results/cycle01-2026-09-10/REPORT.md)

**Changing the observations.** A new SPLADE++ source supplied judged examples
of both specialist groups on 19 of 43 and 22 of 54 queries. It also exposed an
ambiguity: its isolated specialists are exactly documents absent from the
retained lexical rankings, coupling support with candidate access.
[Cycle02 inventory](../results/cycle02-2026-09-10/REPORT.md)

**A planned stop.** We then ran one prospective relevance comparison, allowing
unknown judgments to favor either group. The primary 2020 association remains
positive on its observed eligible queries, but uncertainty across queries is
broad in both years. Neither result meets the frozen rule for pursuing another
fusion method, and neither establishes a negligible effect. We followed the
planned stop. [Cycle03 result and figure](../results/cycle03-2026-09-10/REPORT.md)

**A controlled laboratory.** An exact known-truth laboratory separates copied
reports from independent corroboration. It revealed a useful distinction:
knowing evidence origins can improve probability estimates without changing
the final answer. In the strong-specialist setting, an optimal aggregator with
trusted lineage reduced average error from 15% to 14.05% versus an optimal
aggregator that knew the possible constructions but could not see their lineage.
Unconditionally protecting a weak minority instead raised error from 27.2% to
36.85%. Those are controlled model outcomes with known calibration and free,
correct metadata, not real-agent performance. A proposed shared-error test
turned out to repeat arithmetic already in the experiment, so we retired that
run. That set up a test of an actual coordinator on supplied assumptions.
[Cycle04 result and figure](../results/cycle04-2026-09-10/REPORT.md)

**Actual coordinator evidence.** An Opus5 coordinator then returned valid probabilities on
all 20 fixed diagnostic inputs, matching every reference decision with maximum
probability error below 3.4×10⁻⁸. It distinguished copied from independent reports
when their origin was supplied. We also caught and preserved a measurement
mistake: a detector read zero-valued agent counters as activity and stopped the
first run. A separately frozen correction collected entirely fresh responses;
independent checks verified the raw receipts and exact losses. The result
supports supplied-model reasoning, not real-world cabal detection or learned
source reliability. A follow-up gives provenance a known chance of being wrong.
[Empirical result and figure](../results/cycle05-replication-2026-09-10/REPORT.md)

**Uncertain provenance.** That follow-up produced three probabilities close to their
noise-aware references, then a provider refusal stopped the planned eight-input
batch. The full primary remains incomplete. One observed hint contrast is useful
partial evidence; the missing cases remain unknown. An independent audit also
caught misleading fallback labels and message attribution in the failed call.
We preserved those records and tested a future logging correction separately.
The next checkpoint asks whether small, mechanically verified program tasks
produce enough differing and shared solver errors to study actual evidence
quality. Separate sessions alone will not establish independence.
[Cycle06 result and figure](../results/cycle06-2026-09-10/REPORT.md)

**Finding an observable.** The mechanically verified program panel then completed:
two solver prompts each answered all eight development cases correctly. That
sounds successful, but it failed the research gate—there were no errors or
disagreements to compare. The reserved cases remain unused. The next step first
checks whether changing only a loop bound creates an informative contrast;
more execution steps do not necessarily require more reasoning, especially
when a program has a simple recurrence or shortcut.
[Cycle07 result and readable cases](../results/cycle07-2026-09-10/REPORT.md)

**Choosing a more direct test.** The local loop audit passed its construction checks, but
revealed a problem for interpretation: always answering “false” would score
100% on the short programs and 50% on the long ones without doing any arithmetic.
We preserved the panel and skipped the proposed solver batch. Claude's review
helped redirect the next question toward checking evidence itself: can a solver
recognize an invalid explanation that reaches the right answer, then preserve
that judgment when incorrect evidence is repeated? The next local construction
was designed to make that contrast exact before testing a model. This is a research
choice about information value, not a claim of improved model reasoning.
[Cycle08 local result and cases](../results/cycle08-2026-09-10/REPORT.md)

**A correct answer can have invalid support.** The certificate test then returned all six planned
judgments correctly: three traces, judged before and after copying one invalid
trace twice. The model rejected an invalid intermediate step even though its
trace ended with the right answer. However, the valid trace happened to be first,
so “accept only the first” would also score perfectly. We preserved that limit
instead of treating success as proof of a checking strategy. The next design
uses a small balanced panel to separate position and endpoint policies from
exact verification. No multiagent advantage or general ability is established.
[Cycle09 result and certificate cases](../results/cycle09-2026-09-11/REPORT.md)

**Separating simple alternatives.** The follow-up fixed the program values and varied report
position and final-answer values. All 18 judgments were correct. A fixed-position
rule would score 10/18 and endpoint-only checking 12/18; the observed vector differs
from both. That closes a specific ambiguity, while leaving the internal checking
method unknown. The next four-case design returns to the original minority
question: does valid minority evidence guide a decision against repeated bad
support, and can the same verifier resist an invalid minority? If that simple
verifier succeeds completely, we will park multiagent work in this small
laboratory. More agents need a demonstrated problem to solve.
[Cycle10 result and verified cases](../results/cycle10-2026-09-11/REPORT.md)

**Knowing when to stop.** The four-case bridge then returned all four correct
answers and all sixteen correct evidence-validity judgments, whether valid support
was outnumbered or in the majority among copied reports. We followed the stopping
rule and parked multiagent work in this arithmetic laboratory. A single verifier
already solved every case; adding agents would lack a demonstrated problem to
repair. These outputs do not prove how it reasoned or whether it needed the
certificates. The [synthesis](RESEARCH_SYNTHESIS.md) consolidates the findings before considering
an applied task where a decisive piece of evidence is actually missing.
[Cycle11 result and stopping decision](../results/cycle11-2026-09-11/REPORT.md)

**An applied case from the workflow.** A later approval interruption raised a
concrete question: were the exact research files already publicly accessible?
A repository label did not settle the versioned-byte question. Unauthenticated
retrieval and hash matching did. We recorded the case while retaining direct
fetch as the strong single-system baseline; there is no measured agent advantage.
That clarified another useful distinction: validating a case is different from
justifying a comparison, and finding a baseline failure must not be a condition
for selecting research cases. [Cycle12](../results/cycle12-2026-09-11/REPORT.md)

**When no more labels are needed.** We returned to retrieval by asking which
missing judgments could change a fixed fusion comparison. Under an explicit
top10 RBP diagnostic, adding SPLADE++ to four-source RRF has positive annual
mean bounds on both existing panels even under worst-case missing grades.
The direction needs no new judgments, although9 of97 queries favor the original
fusion and18 remain unresolved. The audit separates a narrower interval from
a decision worth spending on. It is a finite-panel result under that metric,
with no nDCG or generalization claim. An incorrect list-depth assumption was
caught before scoring, preserved and corrected using existing input metadata.
[Cycle13 evidence map](../results/cycle13-2026-09-11/REPORT.md)

**How collaboration shaped the research.** A Fable5.1 Claude coordinator used
four Opus5 scouts to examine the design, then resumed with one evidence scout
to critique the results. Codex implemented the experiments and integrated
independent checks. Critique changed the experiment, and numerical evidence
changed the question. A further review of the new source preserved a useful
association test while an independent check corrected its missing-label bounds.
Reviewer mistakes were recorded and corrected too. A later native review hit
its configured budget after emitting a useful memo; its limit is preserved
alongside the critique, rather than reported as successful execution.
A fresh compact review subsequently completed under the same cap. It caught
the redundant next experiment; independent algebra also corrected a conclusion
both reviewers had accepted. Collaboration improved the research through
checked disagreements, not agreement alone.
A further tools-disabled Fable review helped choose noisy provenance as the next
axis. Independent algebra made the proposed error channel precise and reduced
the experiment to eight inputs. Large agent counts were unnecessary when one
coordinator already reproduced the fully supplied calculation. The later review
also caught an incorrect statement-count label in our capsule; the verified
experiment records were already correct. We retained the original handoff and
documented the correction, then refined its proposed difficulty experiment to
avoid changing nesting and loop bounds together.

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
historical generated lexical/character-based rankers plus one cached neural
sparse source, extensive exploratory selection, and
no established improvement across independent domains. The v7 headline p-value
compares against v5, not ordinary RRF. There is no supported “minimum 50 labels”
threshold, proof of optimality, or novelty claim about tuning k.

The existing specifications and May notebooks are historical artifacts. Current
qualifications live in RESEARCH_STATE. The brief can showcase an inspectable
research process now; a new technical contribution still needs its own related
work and independent evaluation. [PLANNING](../_sessions/PLANNING.md) separates
the next local loop-bound audit from parked algorithm promotion. The separate
website task owns integration and publication.
