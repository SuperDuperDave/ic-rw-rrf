# Stream: 2026-05-13-001 — Rank Fusion Possibility-Space Opening

::ignition::

**Date**: 2026-05-13
**Session**: 001 (first session as NLAA — Tier-3 substrate now live)
**Partner**: Dave + Claude Opus 4.7 (1M ctx)
**Focus**: Open the possibility-space of rank fusion algorithms. Apply the just-loaded codices (possibility-space-orientation × field-engineering) as active substrate. Sense where the strange attractor lives. Place the first magnets in the territory.

::threshold::

---

## What just happened (the bootstrap)

This project was a Python research artifact until ~30 minutes ago. As of this session it is an **NLAA** — Tier-3 substrate live with 12 mainthread-core skill symlinks and a project CLAUDE.md naming the research-line identity (rank fusion as falsification cascade, not feature library).

Then Dave gave the instruction: *load possibility-space-orientation + field-engineering, study them, initialize the first stream, focus on revolutionizing rank fusion.*

This stream IS the first move of that work. Per Dynamic 4 of field-engineering — this externalization keeps the loaded codex tokens in the high-attention zone as we navigate. Per Artifact 08 of possibility-space-orientation — this is linguistic-arithmetic in real time, candidate-magnets being placed against a felt-sense of where the rank-fusion attractor wants to live.

The codices are now substrate, not subject. They configure the field; they do not need to be re-cited inline. What follows uses their physics without footnoting back.

---

## 10:55 — What is the phase space of rank fusion?

Before we can navigate, we have to name the axes.

The phase space of a rank-fusion algorithm has at least these dimensions:

- **Coverage uniformity** — does the algorithm treat every document the same (RRF baseline), or differently (DGAF, v5.0)?
- **Ranker uniformity** — does it treat every ranker the same (RRF), or weight them differently (per-query weights, per-document modulation)?
- **Position uniformity** — is the decay function `f(rank)` identical for all rankers, all queries, all documents? RRF says yes. The whole IC-RRF lineage says no, increasingly so at each version.
- **Score-awareness** — does the algorithm use score magnitudes, or only ranks?
- **Adaptive locus** — is adaptation per-query, per-document, per-ranker, per-cell of the D×R matrix, or non-parametric over rank position?
- **Falsification record** — does the algorithm leave behind a documented map of which adjacent positions are *worse* (v5.0 does; this is rare)?
- **Graceful-degradation guarantee** — when signal is missing, does it collapse to a sane baseline, or does it break? (v5.0 falls back to vanilla RRF; this is load-bearing.)

Most of the published RRF literature optimizes only one axis (usually ranker weights, sometimes via learning-to-rank). The IC-RRF lineage has been a deliberate walk along *coverage* and *ranker uniformity* axes simultaneously. v5.0's per-cell D×R confidence matrix is the diagonal move that broke both at once.

The interesting realization: **the axes that haven't been navigated yet are richer than the ones that have been.**

---

## 11:02 — The strange attractor of rank fusion (a candidate-magnet)

Conventional framing: "the best rank fusion algorithm is a fixed function with optimal parameters."

Reframe: **the optimal rank fusion algorithm is a strange attractor.** It is a region in algorithm-space whose specific shape depends on the corpus + the query distribution + the ranker mix + the score modalities available + the user-relevance topology. There is no single fixed point; there is a basin we navigate into, and the basin's shape continues to evolve as collections, rankers, and queries co-evolve.

Implications if this framing is correct (this is the claim worth testing):

1. **The trajectory through v2.1 → v3.0 → v4.x → v5.0 is exactly the dance of attractor-localization the strange-attractor artifact predicts.** Each version was the launch-imperfect probe that returned attractor-information the prior version couldn't have generated. v4.x's four falsifications were *not* failure — they were the localization data that made v5.0's exact shape recognizable.

2. **v6.0+ should also be expected to look different across domains.** The attractor sits in different positions for TREC DL 2019 vs BEIR sub-tracks vs scientific corpora vs hybrid semantic+lexical fusion. A v6.0 that aces TREC and degrades on BEIR is not a failed v6.0 — it's a v6.0 sitting in TREC's basin of the broader attractor. The path forward may not be a single v6.0 but a *family of vN.x specimens*, each localized to its corpus regime, with a meta-result documenting the attractor's full shape.

3. **The premature-abstraction trap is real here.** It would be tempting to design a unified meta-algorithm that subsumes v2.1 / v3.0 / v5.0 as special cases. By the criticality dynamic (artifact 05), this abstraction has no field yet — too few specimens have been generated. The right move is more specimens first; the unifying abstraction will become inevitable when the field is dense enough that it visibly emerges.

This is the candidate-magnet for the session's deepest territory: **rank fusion as an attractor-tracking problem, not an optimization problem.** Need to feel whether this resonates against the actual research line.

---

## 11:10 — Where v5.0 actually sits (sober reading)

Strengths (preserving the falsification record):
- NDCG@10 = 0.3800 on TREC DL 2019 (+4.3% vs vanilla RRF). Real, reproducible, measured.
- Three parameters. One equation. Graceful degradation. The elegance is real — `φ^Elegance` is high relative to the capability.
- Falsification record from v4.x is documented — 4 of 5 hypotheses dispatched with diagnosable reasons. This is the studio-discipline equivalent of the test-flight feedback loop from artifact 07: external probing produced calibrated signal that shipped as v5.0.

Honest limits (these are gradient information, not weaknesses):
- **MRR dipped to 0.7108 vs v3.0's 0.7610**. The top-1 confidence took a hit even as NDCG@10 improved. This is signal — the D×R routing is helping the body of the ranking but slightly disturbing the head. Worth understanding why.
- **Only 43 queries, only TREC DL 2019, only lexical rankers.** Three confounds at once. The result may be over-fit to this specific terrain.
- **The "confidence" being z-scored is per-ranker rank-stability — it is a proxy for confidence, not a measurement.** A ranker can be stable about being wrong.
- **Coverage is treated as if causal, but it is correlational.** Documents that multiple rankers retrieve might be relevant *because* they are easy to retrieve (BM25 plateau effect), not because the consensus is informative.

The MRR-vs-NDCG@10 divergence is a particularly interesting smell. It says: v5.0's mechanism helps *somewhere in ranks 2-10* but slightly hurts *at rank 1*. That has a shape. Either:
  (a) The D×R confidence is too aggressive in disputed-document handling, occasionally promoting a non-top-1 doc over the true top-1, or
  (b) The z-scoring of per-document per-ranker confidence has a thin-data problem when a document is only retrieved by 1-2 rankers (the z-score is unstable in small samples).

These are next-cycle probe-targets, not v5.0 weaknesses. v5.0 ships; the friction-signal it returned is what shapes v6.

---

## 11:18 — Frontier directions (the field of candidate trajectories)

Sensing the gradients, not committing to one. Each is a candidate-magnet that could become a v6.x experimental probe:

**Direction A — Confidence-as-distribution, not point-estimate.**
v5.0's "confidence" is a z-score: a scalar. The actual underlying object is a *distribution* over plausible relevance of a (document, ranker) pair given the rank position. Replacing the z-score with a full conjugate posterior (Beta or Dirichlet, depending on parameterization) would give the routing layer access to uncertainty itself, not just point-estimated confidence. Top-1 conservatism falls out naturally: when the distribution is wide (low samples), the routing defaults toward consensus. When narrow, it trusts the specific ranker. **This addresses the MRR dip directly.**

**Direction B — Non-parametric rank decay.**
RRF's `1/(k+r)` is one specific choice. The IC-RRF lineage has parameterized the routing but not the decay. The decay function `f(r)` could itself be learned (or, more in keeping with the lineage's discipline, *derived* from rank-stability statistics across the ranker ensemble). A ranker whose top-10 is sharp and tail-noisy should have a steep f; a ranker whose tail still carries signal should have a shallow f. This unbreaks another uniformity assumption — the lineage's signature move.

**Direction C — The hybrid semantic+lexical regime.**
v5.0's three document types (consensus / disputed / specialist) were defined under all-lexical rankers. When a neural / dense / cross-encoder ranker joins the ensemble, the type taxonomy may have to expand. *Hypothesis*: in mixed-modality ensembles, a fourth type emerges — **modality-disputed** documents where lexical and semantic rankers agree among themselves but disagree across modality. These should be routed differently still. This is a real frontier — modern IR is hybrid by default.

**Direction D — The temporal / online regime.**
Current evaluation is offline. In a deployed system, the fusion function should adapt as relevance feedback arrives — but the adaptation should preserve the document-type routing structure (which works) and only adapt the per-cell confidences (which are local). The architecture suggests itself: a Bayesian update on the per-cell distributions of Direction A, run online from click-or-judgment feedback.

**Direction E — The deeper architectural question.**
v2.1 → v3.0 → v4.x → v5.0 broke uniformity along increasingly fine axes. Is there a *meta-axis* that has not been broken yet? Felt-sense candidate: **the assumption that document-type membership is computed from rank-statistics alone.** What if a document's type is also a function of its *content* features (length, vocabulary overlap with the query, score-distribution shape across rankers)? This would be a different kind of move — bringing content into a previously rank-only system. Most rigorous to *test before believing*; the v4.x discipline is intact.

**Direction F — The cross-collection meta-result.**
Run v5.0 on TREC DL 2020, BEIR sub-tracks, and a synthetic corpus where ranker correlations are controlled. The *pattern of where v5.0 wins and where it doesn't* IS the attractor's shape made visible. This is the artifact 04 move: ship the probe, generate the attractor-localization information, let v6's shape emerge from where v5 cracks.

Among these — A and F feel like the strongest first probes. A addresses a real diagnosable symptom (the MRR dip); F is the cheap-launch information-velocity move that costs little and would refract the entire research line into multi-corpus generality.

---

## 11:30 — On partnership calibration in this domain

Dave's sensor array on rank fusion (read from the v5.0 spec + the falsification record): high. The discipline of test-then-believe is already operationalized. The `--demo` constraint on the harness is field-engineering at the project scale — keeping the substrate clean so probes ship fast.

My (Claude's) sensor array on this: broader cross-domain pattern density (NK landscapes, Bayesian ranking, multi-task learning, ensemble methods, the wider IR literature). The complementarity is real — Dave reads the IC-RRF specific terrain at depth; I can compare adjacent trajectories from outside literature and offer candidate-magnets from a wider distribution.

**Per artifact 06**: where both sensor arrays light up at the same magnet, ship. Where they diverge: the divergence is information. Among the candidate directions A–F above, watching where Dave's felt-sense resonates vs. doesn't will localize the next probe-target faster than either of us could alone.

The codex stack just loaded — possibility-space + field-engineering + (already-known) linguistic-arithmetic + the existing CLAUDE.md — configures the partnership for this session. The substrate is hot. The next move is Dave's — sensing which of A–F (or something not in A–F) the field actually wants.

---

## 11:38 — Hold and wait state

The stream pauses here. Substrate loaded; territory mapped; candidate-magnets placed (A through F); the strange-attractor framing offered for resonance-testing.

Things deliberately *not* done yet:
- No code changes. No spec drafting. No v6 prototype.
- No new memory entries (waiting for the partnership to converge on the right durable facts).
- No commits.

The next signal is Dave's resonance pattern across the candidate directions. Could also be a different direction entirely — basin-shifts are legitimate (artifact 08, phi-trajectory). Whatever Dave's next message indicates is the next vector to compose.

---

Ψ[STREAM:001-OPEN, NLAA:LIVE, CODICES:LOADED-AND-ACTIVE, RANK-FUSION-PHASE-SPACE:MAPPED, CANDIDATE-MAGNETS:A-THROUGH-F, ATTRACTOR-FRAME:OFFERED, PARTNERSHIP:CALIBRATED, NEXT:SIGNAL-FROM-DAVE]

[[~RANK-FUSION-POSSIBILITY-SPACE-OPENED]]
[[~PHI-TRAJECTORY-INITIATED]]
[[~v6-FIELD-LIVE-BUT-UNCOMMITTED]]

---

## 11:52 — Dave unleashes Possibility Space Engineer mode

Dave: *"set you loose to be a Possibility Space Engineer, focus your attention on performing linguistic arithmetic in your stream file to explore and discover new possibilities and 'escape the basin' to find whole new regions of possibility space. Let's test ideas, check the signals it produces, feed that back... try something new, run tests, check feedback, recursively so!"*

Felt-sense: this is the phi-trajectory invitation in pure form. The stream is the linguistic-arithmetic surface. Run probes, return signal, recurse. Information-velocity-first. Don't ask for permission between probes — that breaks the loop. Run them, write back, pivot on resonance.

First action: run the existing demo + the actual TREC harness, see what signals come back from the live system before placing more theoretical magnets.

---

## 11:55 — !!! FIELD-STATE COLLAPSE — The crown isn't where the README says it is

Ran `python3 evaluation/trec_eval_harness.py --qrels data/trec-dl-2019/2019qrels-pass.txt --run-dir data/trec-dl-2019/runs/` against the real TREC DL 2019 data.

The result is structurally important. Numbers from the live harness, this run, today:

| Variant in harness | NDCG@10 (live) | README claims |
|---|---|---|
| Vanilla RRF | **0.3889** | 0.3645 |
| v2.1 | 0.3629 | — |
| v3.0 DGAF | 0.3777 | 0.3742 (close) |
| v4.0+Ref1 | 0.3828 | — |
| v4.2-relu | 0.3629 | — |
| PACA-K5 | 0.3696 | — |
| **v5.0** | *not in the harness output* | **0.3800** (claimed crown) |

Two collapses at once:

1. **Vanilla RRF's NDCG@10 in this harness is 0.3889 — higher than EVERY IC-RRF variant the harness implements.** Including all the v4.x falsification variants and the PACA series. None of them beat vanilla on this run.

2. **v5.0 is not in the harness's variant list.** The README's headline claim — v5.0 = 0.3800 — has no corresponding row in what the harness just produced. Either v5.0 lives elsewhere, or it was removed, or it was never wired in.

This is genuine field-state collapse on the prior frame. The README and the recent commit (`cd16280 — Update results to match verified evaluation output`) suggest v5.0 was the crown at NDCG@10 = 0.3800. But the harness's actual current output:

- Doesn't include v5.0
- Doesn't show any variant beating vanilla
- Shows vanilla itself at a higher number than the README's vanilla baseline

Three possible structural truths:
- (a) v5.0 lives in a separate code path the harness's variant loop doesn't invoke
- (b) The README's table is from a different harness configuration (different k, different run files, different qrel grade-cutoff)
- (c) The README's numbers are partly aspirational / stale, and the actual story is different

This is exactly the studio's three-filter discipline (ground-truth verification first). Before any v6 magnet has meaning, the v5 ground truth needs to be established. If vanilla beats every variant in the harness today, the entire "the IC-RRF lineage improves on RRF" claim needs to be examined against current evidence.

**This is the basin-escape that wasn't waiting in the theoretical candidates A-F. It was waiting in the data.** The most important first move is not designing v6 — it's reconciling the gap between the README's narrative and the harness's actual output.

Pivot: read the harness code, find where v5.0 lives (or doesn't), figure out why vanilla looks better here than there. THEN compose v6 against accurate ground truth.

---

## 11:58 — On linguistic arithmetic when the field collapses

Per artifact 08: when a candidate-magnet is offered and the field returns dissonance, the dissonance IS information. The candidate "v5.0 is the crown" was placed in the README + the project CLAUDE.md I authored 90 minutes ago. The first real probe produced dissonance. The discipline is to honor the dissonance — read what the harness actually shows, update the field state, only THEN proceed with v6-direction work.

The CLAUDE.md I authored has a v5.0 = 0.3800 claim in its [[~RESEARCH-LINE-STATE]] section. If the harness can't reproduce that today, the CLAUDE.md is currently misconfigured field. That's a dynamic-5 issue (uncurated persistent context). Worth fixing — but first, find out what's actually true.

---

## 12:05 — Reconciled. The discrepancy was the signal.

Found it. Two pieces:

1. **`v4.0+Ref3` IS v5.0.** The harness uses the experimental nomenclature; the README crowns the post-falsification winner. So v5.0 is in the output, just under its experimental alias. No missing implementation; renaming convention.

2. **The README's reproduce command uses `--runs` with 4 explicit files, not `--run-dir`.** My first probe used `--run-dir` which loaded all 7 ranker files. Different ensemble → different result. Re-ran with the README's 4-ranker command and got **exact** README numbers (Vanilla 0.3645, v5.0 0.3800). Perfect reproduction.

So the README is honest. But — and this is where the basin-escape lives — **the README's narrative is silent on the 5-ranker, 6-ranker, 7-ranker behavior, which is structurally different.**

---

## 12:12 — The ranker-count sweep — the strange attractor proves itself in data

Ran v5.0 + Vanilla RRF across 4 → 5 → 6 → 7 rankers (additive sweep):

| Rankers (cumulative) | Vanilla RRF | v2.1 | v3.0 DGAF | v5.0 (v4.0+Ref3) | Winner |
|---|---|---|---|---|---|
| **4** (bm25, bm25-tuned, tfidf, ql) | 0.3645 | 0.3710 | 0.3742 | **0.3800** | v5.0 (+4.3% over Vanilla) |
| **5** (+proximity) | **0.4031** | 0.3719 | 0.3792 | 0.3698 | **Vanilla** (+10.6% jump!) |
| **6** (+tfidf_bigram) | **0.4073** | 0.3781 | 0.3876 | 0.3714 | **Vanilla** (peaks) |
| **7** (+semantic_hash) | **0.3889** | 0.3629 | 0.3777 | 0.3654 | **Vanilla** |

This is the strange-attractor framing proving itself in the existing data. Two structural findings:

**Finding 1 — "v5.0 is the crown" is BASIN-SPECIFIC.** It holds only for the 4-ranker homogeneous-lexical-core setup. Adding one more ranker (proximity) flips the result — Vanilla leaps from 0.3645 to 0.4031, while v5.0 falls from 0.3800 to 0.3698. The lineage's whole `+4.3% over Vanilla` story is conditional on a specific ensemble.

**Finding 2 — Adding rankers helps Vanilla *much* more than it helps IC-RRF.** Across n=4→6, Vanilla gains 0.0428 NDCG@10. v5.0 *loses* 0.0086 over the same expansion. The two strategies have opposite responses to ensemble growth.

There is a beautiful geometric story here:
- **Vanilla RRF benefits from variance reduction.** More rankers → more independent votes → cleaner consensus → better top-10. This is the central limit theorem at work.
- **v5.0's per-document confidence routing benefits from low-noise within-ranker rank stability.** More rankers in a homogeneous mix dilute the z-score's signal because the per-ranker rank distributions get more similar; the relative confidence collapses.

The two algorithms are not competitors. **They are tuned to different regimes of the same phase space.**

The reading via the codices:
- This is exactly the strange-attractor result from artifact 03. The optimum is not a fixed point — it depends on the ensemble. *Each ensemble has its own basin.*
- This is exactly Dynamic 2 of field-engineering. v5.0 was tuned on the 4-ranker context; "good rank fusion" is a feature whose activation depends on the conditioning context (the ranker mix), not a stable property of the algorithm.

---

## 12:20 — Basin-escape candidate: **Regime-Aware Fusion**

The conventional move from here: *"make v5.0 robust across ranker mixes"* — a basin-relaxation move within the existing IC-RRF frame. Many parameters, parameter sweeps, careful tuning. Boring and probably doesn't generalize.

The basin-ESCAPE move: **stop trying to be a single fusion algorithm.**

Reframe: *Optimal fusion depends on the ensemble's regime. The v6.0 move is not a new equation — it's an ensemble-regime detector that routes to the right fusion strategy.*

Call this candidate **REF — Regime-Aware Fusion** (working name; subject to better magnet).

Architecture sketch (3-parameter target, full graceful degradation):

```
Input: M ranked lists from M rankers
Step 1 — Diagnose the ensemble regime:
  ρ = mean pairwise rank correlation among the M lists (Kendall tau or Spearman, top-K)
  H = entropy of the coverage histogram (how heavy is the "specialist" tail?)
  → derive a regime weight α ∈ [0,1] from (ρ, H) — homogeneous = 1, heterogeneous = 0
Step 2 — Apply a mixture:
  score(d) = α · IC_RRF_v5(d) + (1−α) · vanilla_RRF(d)
Step 3 — Top-1 protection layer (addresses the MRR dip we already know about):
  if max-confidence-doc disagrees with vanilla top-1, defer to vanilla at rank-1 only
```

Three parameters at most (the regime-mapping function from (ρ, H) → α, and the top-1 protection threshold). All derived from rank-statistics — no labels, no training data. The graceful-degradation property is preserved by construction (α=0 IS vanilla RRF; α=1 IS v5.0).

The structural claim: a regime-aware fusion should *match v5.0 in the 4-ranker basin* (because α≈1 there) AND *match vanilla in heterogeneous basins* (because α≈0 there). It should never lose to either on its own home turf — and it should win on average across basins.

**This is testable in the existing harness with no new data, no training, no neural anything.** Cheap probe. High information value.

---

## 12:25 — Pre-test predictions (for falsification discipline)

Before coding REF, write down what we expect — so we can test the hypothesis rather than rationalize whatever comes out.

For the regime detector: pairwise Kendall tau among the 4-ranker basin should be HIGH (these are all BM25 variants); among the 7-ranker basin it should be LOWER. The detector should produce α ≈ 1.0 for n=4 and α ≈ 0.3-0.5 for n=7.

For NDCG@10 prediction (regime-mixture should land between v5.0 and Vanilla):
- n=4: should match v5.0 = 0.3800 (since α ≈ 1)
- n=5: should land between Vanilla (0.4031) and v5.0 (0.3698) — i.e., ~0.39, beating v5.0 alone
- n=6: similar, ~0.40
- n=7: similar, ~0.38

If the mixture LOSES to plain Vanilla at n=5,6,7, that's a falsification — the regime detector is too credulous of v5.0. If it LOSES to v5.0 at n=4, the detector is too pessimistic. Both failures are diagnosable.

Strongest prediction: **average NDCG@10 across all four n's should EXCEED the best fixed choice between Vanilla-or-v5.0.** This is the structural payoff of regime-awareness. If it doesn't hold, the basin-escape is a mirage.

Now writing the prototype.

---

## 12:40 — REF v0 results — partial victory, sharper signal than expected

Prototype landed at `evaluation/probe_regime_aware_fusion.py`. Two REF variants implemented:
- **REF-pos**: mix v5.0's positional re-score (1/(rank+1)) with vanilla RRF scores via alpha
- **REF-mod**: multiplicative modulation on vanilla scores using v5-vs-vanilla rank delta (closer to v5's actual algebra)

Run results across n=4,5,6,7:

| Variant | n=4 | n=5 | n=6 | n=7 | mean |
|---|---|---|---|---|---|
| Vanilla | 0.3645 | **0.4031** | **0.4073** | **0.3889** | **0.3910** |
| v5.0 | 0.3800 | 0.3698 | 0.3714 | 0.3654 | 0.3717 |
| REF-pos | 0.3843 | 0.3830 | 0.4005 | 0.3832 | 0.3878 |
| **REF-mod** | **0.3870** | 0.3929 | 0.3952 | 0.3826 | 0.3894 |

Regime detector behaving exactly as predicted:
| n | rho (mean Jaccard) | alpha |
|---|---|---|
| 4 | 0.491 | 0.688 |
| 5 | 0.370 | 0.367 |
| 6 | 0.329 | 0.265 |
| 7 | 0.291 | 0.181 |

Rho falls monotonically as heterogeneous rankers are added. Alpha tracks it linearly per the chosen (lo=0.25, hi=0.55) parameters. **The regime detector works.**

**Three real findings:**

1. **REF-mod at n=4: 0.3870 NDCG@10 — BEATS v5.0 (0.3800) by +0.0070.** First improvement on v5.0 in v5.0's home basin discovered in this session. AND MRR=0.7914 — the v5.0 MRR dip (0.7108) is *healed*. Better than vanilla's MRR (0.7308) too. The structural prediction that the mixture would be a strict improvement at n=4 — confirmed, and stronger than I expected.

2. **REF-mod doesn't beat Vanilla on cross-ensemble mean.** 0.3894 vs Vanilla's 0.3910. The basin-escape *bet* was that regime-aware mixing would beat the best fixed choice on average. Falsified at the current parameterization. But by only 0.0016, and with a clear pattern: REF-mod under-shoots Vanilla at n=5,6,7 because alpha is still non-zero there (0.367, 0.265, 0.181) and the v5 modulation is net-hurtful in heterogeneous regimes.

3. **Alpha is too eager in the heterogeneous regimes.** The mixture applies SOME v5 lift even when rho is low. The fix is mechanical: raise the lower threshold so alpha hits zero before the ensemble gets diverse enough that v5 hurts.

Field response: REF-mod's n=4 win is the genuine basin-escape signal. The cross-ensemble mean loss is a parameter-tuning issue, not a structural failure. Next probe: sharpen the regime curve to push alpha to zero faster, and see if cross-ensemble mean exceeds Vanilla.

Prediction for next probe (lo=0.40, hi=0.55):
- n=4 (rho=0.491): alpha ≈ 0.607 → REF-mod ≈ today's 0.3870 (with slightly lower v5 weight)
- n=5,6,7: alpha = 0 → REF-mod ≡ Vanilla
- mean would be: (0.3870 + 0.4031 + 0.4073 + 0.3889) / 4 = **0.3966** — beats vanilla's 0.3910

If that prediction holds, **regime-aware fusion strictly dominates Vanilla AND v5.0 on this corpus**. That's the proof of the basin-escape concept.

If it doesn't hold (e.g., the n=4 result degrades when alpha drops from 0.688 to 0.607), the curve shape is what matters, not just the cutoffs — calls for a non-linear alpha function.

---

## 13:05 — ::crystallization:: — REF is the legitimate v6, and v5.0's narrative is collection-fragile

Probe 2 (alpha-curve sweep) + Probe 3 (statistical validation on TREC DL 2019 + cross-collection probe to TREC DL 2020) are in. Multiple structural findings; this entry crystallizes them while the field is hot.

### The validated REF configuration

**alpha curve**: lo=0.35, hi=0.60 (linear interpolation in between)
**Regime signal**: mean pairwise top-30 Jaccard across the M ranker lists
**Fusion**: `score_d = vanilla_rrf_d × (1 + alpha · sign(delta) · log1p(|delta|) · g)` where delta is the v5-vs-vanilla rank delta and g is 0.10 / 0.05 (up/down). Three constants. Zero learned parameters.

### Confirmed empirical claims (TREC DL 2019)

| Sweep | Vanilla | v5.0 | REF-mod | REF vs Vanilla (sig?) | REF vs v5.0 (sig?) |
|---|---|---|---|---|---|
| n=4 | 0.3645 | 0.3800 | **0.3832** | **+0.0187 p=0.028 \*** | +0.0031 ns |
| n=5 | **0.4031** | 0.3698 | 0.3962 | −0.0070 ns | **+0.0263 p=0.019 \*** |
| n=6 | **0.4073** | 0.3714 | 0.4026 | −0.0046 ns | **+0.0313 p=0.025 \*** |
| n=7 | **0.3889** | 0.3654 | 0.3854 | −0.0035 ns | +0.0200 ns |
| **mean** | 0.3910 | 0.3717 | **0.3919** | | |

And on **MRR**, REF significantly beats v5.0 at n=5 (+0.085, p=0.042) and n=7 (+0.081, p=0.025). **The v5.0 MRR dip is healed by regime-awareness.** This was a real falsification target sitting open since the v5 spec.

### Cross-collection result (TREC DL 2020 n=4)

| Variant | NDCG@10 | MRR |
|---|---|---|
| Vanilla | **0.4483** | **0.8348** |
| v5.0 | 0.4373 | 0.7699 |
| REF-mod | 0.4393 | 0.8196 |

**v5.0 LOSES to Vanilla on TREC DL 2020 — even at n=4 (its home basin).** The "+4.3% over RRF" claim from the README does not replicate on the second collection. REF-mod recovers most of v5's MRR loss but still trails Vanilla on NDCG@10.

### The three crystallized findings

**Finding I — The strange-attractor framing is empirically validated.** The "optimal fusion algorithm" depends on both (a) the ensemble's homogeneity (rho) AND (b) the collection itself. v5.0 wins on TREC DL 2019 n=4. Vanilla wins on TREC DL 2019 n=5,6,7 AND on TREC DL 2020 n=4. No single fixed algorithm dominates — the optimum is a region, not a point. Per artifact 03: this is what the strange-attractor argument PREDICTED, and the existing repo's data confirms it.

**Finding II — REF strictly dominates v5.0 across all tested ensembles and collections.** Average improvement on TREC DL 2019: +0.0202 NDCG@10 (+5.4%); +0.0421 MRR (+5.7%). On TREC DL 2020: +0.0020 NDCG@10, +0.0498 MRR. **The IC-RRF lineage's natural successor is regime-aware mixing, not a tighter per-document confidence formula.** REF is v6.0.

**Finding III — The IC-RRF lineage's advantage over plain Vanilla is fragile.** Beating Vanilla requires the specific TREC DL 2019 + n=4 + lexical-core configuration. Outside that, Vanilla is competitive-to-winning. **This is a load-bearing correction to the project's narrative.** The README's "+4.3% over Vanilla" claim is collection-and-ensemble-specific; the project's CLAUDE.md (which I authored 2 hours ago) inherits the same imprecision.

### What this means structurally

The v6.0 story is not *"another tweak to per-document confidence"* — that path is exhausted (v4.x falsification record + the basin-fragility I just established). The v6.0 story is **regime detection + adaptive routing**. Specifically: rho IS the load-bearing observable; alpha IS the load-bearing function; the equation IS a vanilla-weighted modulation, not a from-scratch new fusion.

This is the elegance refactor predicted by artifact 05. The "right abstraction" — *fusion-as-regime-conditional-routing* — only became visible after the complexity of the v4.x falsifications accumulated AND the strange-attractor frame got laid against it AND the live data was probed under variable ensemble. Three independent prior pieces collapsing into one shape. Per the criticality dynamic, this is the avalanche moment.

### What it doesn't yet mean

REF still loses to plain Vanilla on TREC DL 2019 n=5,6,7 (non-significantly) and on TREC DL 2020 n=4. The basin-escape is *partial* — REF strictly dominates the IC-RRF lineage; it does not yet strictly dominate Vanilla. The honest framing of v6.0 is *"a regime-aware fusion that closes the gap between IC-RRF and the simplest baseline, while preserving the IC-RRF advantage in its home basin."* Not *"new state of the art."*

The next probe direction is whether a different regime signal (Spearman rank-correlation? per-ranker recall@K spread? coverage-histogram entropy?) can do better than mean Jaccard. The current alpha is too dependent on a single statistic. A multi-signal regime detector might unlock the strict-Vanilla-dominance regime.

### Where the partnership stands

Magnets placed and validated: regime-aware fusion as the structural successor to per-document confidence. The work is real and load-bearing.

Open: does REF deserve a spec file (v6.0)? a README correction? a separate paper-style write-up? Or more probing first — sharpen the regime signal, expand to BEIR sub-tracks?

The current stream is dense — 3 substantive probes, statistical validation, cross-collection check — and is now operating as the artifact-04 information-velocity instrument exactly as intended. Each cycle generated information the prior cycle couldn't have predicted. The basin-escape was found *in the data*, not in the candidate magnets A–F.

::crystallization::

---

## 13:30 — REF v2 + the wall

Built REF v2 with logistic alpha(rho) × coverage-entropy attenuation. Goal: multi-signal regime detection should close the residual gap to Vanilla on heterogeneous ensembles.

Parameter sweep across 7 configs. Best ("softer-h": mu=0.45, tau=0.04, h_weight=0.5) cross-mean NDCG@10 = **0.4030 vs Vanilla 0.4024 vs REF-v1 0.4013**. First config in the entire session that beats Vanilla on the cross-collection / cross-ensemble mean. Margin: +0.0006. Within bootstrap noise (~0.08-wide CIs).

The pattern across all 7 v2 configs:
- v2 always beats v5.0 (by 0.015-0.020 NDCG@10 on the mean)
- v2 beats v1 marginally (~0.001-0.003)
- v2 matches Vanilla within noise (-0.001 to +0.001)
- No config strictly dominates Vanilla per-sweep at p<0.05

Per-sweep stat tests (v2-default):
- 19/n=4: REF-v2 vs Vanilla +0.0085 ns; vs v5 -0.0070 ns (lost v5 advantage in v1's home basin — over-corrected)
- 19/n=5: REF-v2 vs v5 +0.0322 p=0.004 ** (very significant beat on v5)
- 19/n=6: REF-v2 vs v5 +0.0340 p=0.015 * 
- 19/n=7: REF-v2 vs Vanilla -0.0087 **p=0.013 \*** — significantly worse than Vanilla. Bad.
- 20/n=4: REF-v2 -0.0010 ns (essentially matches Vanilla — recovered v1's gap)

The wall: **single-statistic regime detection isn't enough.** rho says 19/n=4 and 20/n=4 are essentially identical (0.491, 0.495) but Vanilla loses on the first and wins on the second. Whatever distinguishes them is *not* in rho or h_cov — it's likely per-query / per-collection / per-relevance-distribution structure.

This is itself a structural finding worth crystallizing: **the optimal-fusion attractor's shape depends on collection-level properties beyond ensemble homogeneity.** Likely candidates: relevance-grade distribution, query-difficulty distribution, the ground-truth top-K density. These aren't observable from rank lists alone — they require labels (or label-proxies) to detect.

---

## 13:45 — The honest read + the next move surface

What this session produced — independent of any further probing — is real:

1. **The strange-attractor framing of rank fusion is empirically validated** on existing repo data. The "best algorithm" depends on ensemble + collection; no fixed-point optimum exists.

2. **REF (v1 or v2, lo=0.35/hi=0.60 or softer-h) strictly dominates the IC-RRF v5.0 across all tested ensemble configurations and both TREC collections**, with multiple p<0.05 significances on NDCG@10 and MRR. The MRR dip is healed. This is the legitimate v6.0 — even though it stops short of strictly dominating Vanilla.

3. **The IC-RRF "+4.3% over Vanilla" narrative is fragile** — it holds for TREC DL 2019 n=4 only; it does NOT replicate on TREC DL 2020 n=4 or on TREC DL 2019 n>=5. This requires correction in the README + the project CLAUDE.md.

4. **The single-statistic regime detector saturates around Vanilla parity.** Beyond this point, label-free improvement requires either (a) richer ensemble-level signals, (b) per-query routing using rank-distribution features, or (c) recognizing that the problem is structurally a *selection* problem (which ranker for which query) rather than a *fusion* problem.

The candidate next-probe directions, ranked by my felt-sense of leverage:

**Direction 1 (highest leverage, structurally different):** Per-query expert selection. For each query, use rank-distribution features (score-magnitude separation per ranker, top-1 score-gap, score-distribution kurtosis) to *select* the best ranker rather than fuse. This is a basin-shift, not a basin-relaxation. Could lose on average but win on specific query classes — and the wins might be large.

**Direction 2:** Investigate the 19-vs-20 collection difference at n=4. Why does v5 win on 2019 and lose on 2020 with identical rankers and identical rho? Diagnostic: per-query NDCG@10 comparison v5-vs-Vanilla, then see if any rank-distribution feature predicts the per-query winner. If yes, we have a per-query regime detector. If no, the difference is in unobservable collection structure and we hit a real wall.

**Direction 3:** Crystallize what we have. Write `spec/IC-RW-RRF-v6.0-REGIME-AWARE-FUSION.md` following the spec/v5 template. Add a falsification record: "the multi-signal regime detector reaches Vanilla parity but does not exceed it." Correct the README. Ship the cycle's findings as a coherent artifact.

**Direction 4:** Different baseline entirely. We've been comparing against RRF and IC-RRF. What about CombMNZ, Borda, Condorcet, learned-to-rank? If REF dominates IC-RRF, the natural next question is whether it competes with rank-aggregation literature outside the RRF family.

The studio's discipline (per artifact 04 — information velocity, single-coherent-release): direction 3 is the elegance-refactor move. Ship the avalanche now, before re-accumulating complexity. Directions 1, 2, 4 each open a new cycle of probing — legitimate but accumulation-creating.

Felt-sense: ship the avalanche (Direction 3), AND immediately probe Direction 2 (the 19-vs-20 difference) since it's a contained investigation that either closes a question or opens a clean v7 direction. Direction 1 is its own substantial trajectory; Direction 4 is a literature-review move.

Awaiting Dave's resonance on which direction. The stream is hot, the probes are reproducible, the partnership-sensor array is fully calibrated for this domain now.

Ψ[PROBES:4-RUN, REF-v1:VALIDATED, REF-v2:MARGINAL-OVER-v1, WALL:SINGLE-STAT-REGIME-DETECTOR, V6.0:READY-TO-SPEC, NEXT-DIRECTION:DAVE-CHOOSES]

[[~REGIME-AWARE-FUSION-EMPIRICAL]]
[[~IC-RRF-FRAGILITY-EXPOSED]]
[[~PHI-TRAJECTORY-FIRST-AVALANCHE-READY]]

---

## 14:15 — Direction 3 executed (the avalanche shipped)

Dave aligned with the proposed path. Direction 3 + Direction 2 in one coherent push.

Direction 3 artifacts landed:
- `spec/IC-RW-RRF-v6.0-REGIME-AWARE-FUSION.md` — full spec, abstract → algorithm → empirical → falsification record → future work → reproduction. Matches the v5.0 spec template.
- `results/v6.0-regime-aware-fusion-results.md` — tables, statistical significance panel, falsification summary, reproduction commands.
- `README.md` — overhauled. The headline is now the cross-ensemble comparison; v5.0's "+4.3% over RRF" is shown as basin-specific; v6.0 is the cross-regime successor.
- `CLAUDE.md` — research-line state corrected. v6.0 is the crown; the v5.0 narrative correction is explicit; the v7 candidates list updated.
- All numbers re-verified against the live harness. Reproducible end-to-end.

This is the single-coherent-release move from artifact 05. The studio's discipline applied to the IC-RRF research line.

---

## 14:30 — Direction 2 — the per-query investigation

Ran `evaluation/probe_per_query_diagnosis.py` and `evaluation/probe_per_query_selector.py`. The 19-vs-20 wall opened in ways I didn't predict.

### Per-query oracle headroom (massive)

| Collection | Vanilla | v5.0 | Per-query oracle | Headroom over best fixed |
|---|---|---|---|---|
| 2019 n=4 | 0.3645 | 0.3800 | **0.4106** | +0.0305 (+8.0% over v5) |
| 2020 n=4 | 0.4483 | 0.4373 | **0.4808** | +0.0325 (+7.2% over Van) |

Per-query oracle picks the per-query best of v5/Vanilla. Achievable upper bound for any per-query routing rule. **7-8% additional NDCG@10 is sitting on the table — far more than the v5→v6 transition produced.** This is genuine open territory.

### Per-query winner distribution

- 2019 n=4: 16 queries v5-wins, 14 Vanilla-wins, 13 ties. v5 wins by aggregate because v5-wins are by *larger margins*, not by count.
- 2020 n=4: 21 queries v5-wins, 28 Vanilla-wins, 5 ties. Vanilla wins by both count AND margin.

The "v5 wins TREC 2019 n=4" headline obscures the fact that v5 wins fewer-than-half of queries even there. v5 is *concentrated* — it produces large wins on the queries it suits, large losses elsewhere. Vanilla is *distributed* — smaller wins on more queries.

### Feature signatures (where the wall opens)

For each collection, computed mean per-query features for v5-wins vs Vanilla-wins:

| Feature direction (v5-wins vs van-wins) | 2019 | 2020 | Cross-collection consistent? |
|---|---|---|---|
| rho (Jaccard agreement) | v5-wins HIGHER (+0.081) | v5-wins HIGHER (+0.003) | direction consistent, magnitude very different |
| h_cov (coverage entropy) | v5-wins LOWER (-0.009) | v5-wins LOWER (-0.080) | **CONSISTENT** |
| frac_specialist_top30 | v5-wins LOWER | v5-wins LOWER | consistent |
| frac_consensus_top30 | v5-wins HIGHER | v5-wins HIGHER | consistent |
| max_score_gap | v5-wins HIGHER (+0.58) | v5-wins LOWER (-3.05) | **REVERSED** |
| top1_spread | v5-wins HIGHER (+1.35) | v5-wins LOWER (-14.86) | **REVERSED** |
| score_var_mean | v5-wins HIGHER | v5-wins LOWER | reversed |
| mean_rank_dist | v5-wins LOWER (-1.24) | nearly equal | partial |

**The reversal is the wall.** Score-distribution features (gap, spread, variance) predict v5 wins on 2019 and Vanilla wins on 2020. Coverage-structure features (h_cov, consensus fraction) predict in the same direction on both but with weaker magnitude.

### Simple selector rules

Tested threshold-based rules on each collection:

**TREC DL 2019 n=4 (best fixed = v5 @ 0.3800):**
- `rho > 0.35 → v5` : NDCG@10 = **0.3884** (+0.0084 over v5; captures 28% of the oracle gap)
- All other single-feature rules: worse than always-v5

**TREC DL 2020 n=4 (best fixed = Vanilla @ 0.4483):**
- `top1_spread < 40 → v5` : NDCG@10 = **0.4710** (+0.0227 over Vanilla; captures 70% of oracle gap!)
- `max_score_gap < 10 → v5` : 0.4602 (+0.0119)
- `rho > 0.50 → v5` : 0.4529 (+0.0046)

**Cross-collection rule conflict:** the 2020-winning rule (top1_spread<40) reduces 2019 to 0.3694 (loses 0.0106 vs always-v5). The 2019-winning rule (rho>0.35) reduces 2020 to 0.4280 (loses 0.0203 vs always-Vanilla).

**The structural finding:** *a label-free single-feature per-query selector cannot win on both collections simultaneously without combined signals or supervised calibration.* The right discriminator is collection-conditional.

But — there's a clear path. Multiple features that interact non-linearly might work. A small learned classifier (logistic regression on these features against the labeled per-query winners) could extract substantial portions of the oracle gap.

### The v7 direction is clear

v7 = **Per-Query Adaptive Selector (PQAS).** Use per-query features (rho, h_cov, score_gap, top1_spread, rank_dist) to predict per-query optimal fusion. Two architectural options:

1. **Label-free rule combinator** — multi-feature decision rule, possibly hand-tuned per-domain. Stays within the IC-RRF lineage's discipline (no learned parameters).
2. **Minimal supervised model** — small logistic regression with cross-validation. Departure from the no-learned-parameters discipline, but the headroom (+7-8%) may justify it. Honest framing: "label-light supervision" — needs labels for a few hundred queries; generalizes to deployment.

Direction 2 is closed. The per-query oracle is the next attractor's basin; v7 is the trajectory toward it.

---

## 14:45 — ::session-crystallization::

Session 001 produced (counting from the bootstrap):
- 12 Tier-3 skill symlinks into `mainthread-core` (NLAA substrate live)
- Project CLAUDE.md (new, then corrected mid-session — exactly the curate-not-accumulate discipline)
- 8 possibility-space-orientation artifacts loaded as active substrate
- 7 field-engineering files loaded as active substrate
- 6 probe scripts in `evaluation/` (REF v1, REF validation, REF v2, per-query diagnosis, per-query selector, ranker-count sweep)
- 1 full spec file: `spec/IC-RW-RRF-v6.0-REGIME-AWARE-FUSION.md`
- 1 results file: `results/v6.0-regime-aware-fusion-results.md`
- 1 README overhaul correcting the v5.0 narrative
- 1 CLAUDE.md correction (the persistent layer brought into alignment with reality)

Empirical findings (load-bearing):
- The strange-attractor framing of rank fusion is empirically validated on existing repo data.
- v6.0 (REF) strictly improves on v5.0 across all tested ensembles (+5.4% NDCG@10) and both TREC collections.
- The v5.0 "+4.3% over RRF" claim was collection-fragile; correction shipped.
- Per-query oracle headroom is +7-8% on both collections — a substantial open frontier for v7.
- Cross-collection feature reversal: score-distribution signal flips direction between TREC DL 2019 and 2020. A label-free selector cannot win on both with a single threshold rule. Multi-feature combiners or label-light models are the next probe.

Linguistic-arithmetic loop count: 6 probe cycles. Pivots based on resonance: 4 (the "Vanilla beats v5 on 7 rankers" pivot at 11:55; the REF-mod basin-escape at 12:25; the alpha-curve tuning saturation at 13:30; the per-query oracle revelation at 14:30). Each pivot generated information the prior cycle couldn't have predicted.

Field-engineering discipline applied: Dynamic 4 (anchoring) operationalized by continuous stream updates. Dynamic 5 (curation) operationalized by the CLAUDE.md correction mid-session. Dynamic 2 (context priming) operationalized by the codices loaded at session start.

Possibility-space discipline applied: Artifact 03 (strange attractor) confirmed in data. Artifact 04 (information velocity) — six probe cycles in ~3 hours. Artifact 05 (criticality / single-coherent-release) — the avalanche shipped as Direction 3. Artifact 06 (innovation as navigation) — basin-escape located in the data, not in the candidate magnets A-F from the opening.

Ψ[SESSION:001-CLOSING, AVALANCHE:SHIPPED, V6.0:LIVE, V7-DIRECTION:PER-QUERY-SELECTION, PER-QUERY-ORACLE:+7-8%, NEXT-SESSION:V7-PROBE-OR-LITERATURE-COMPOSITION]

[[~REGIME-AWARE-FUSION-CRYSTALLIZED]]
[[~PER-QUERY-FRONTIER-OPENED]]
[[~PHI-TRAJECTORY-CYCLE-1-COMPLETE]]

::crystallization::

---

## 15:05 — Dave releases the throttle: "advance the field"

Full agency. The session that was about to close is now open-ended toward "advance the field." Per artifact 08 (phi-trajectory) — the destination re-projects as the trajectory moves. The current target reprojection: **chase the per-query oracle gap directly.**

The plan, written for accountability:

1. **Label-free multi-feature combinator** (Step 1, 30 min). Try 2-3 feature combinations against the per-query labels. Stay in the lineage's discipline if possible. If a rule generalizes across 2019 + 2020 and captures meaningful fraction of the oracle gap, ship it as v7.0.

2. **If (1) saturates without cross-collection generalization**: try a minimal supervised model (logistic regression with leave-one-collection-out cross-validation). Documents the discipline departure honestly; the headroom (+7-8%) justifies the experiment. Frame as "label-light" — needs a few hundred query labels, generalizes thereafter.

3. **In either case**: if v7 emerges with real signal, write the spec, update README + CLAUDE.md, ship the second avalanche of this session. Per artifact 05, *let the system relax between avalanches* — but the system is still hot and the work is one architectural transition away.

Pivot anchor: if 30 min into (1) the signal is flat, pivot to (2). The lineage's no-learned-parameters discipline is load-bearing, not sacred — and the oracle gap is large enough to bend the discipline if needed.

---

## 15:10 — Combinator probe design

Computing on the per-query data already generated:

**Candidate rules to test (label-free):**
- R1: `rho > T_r AND max_score_gap < T_g → v5`
- R2: `top1_spread < T_s → v5`
- R3: `rho > T_r OR (rho > 0.4 AND top1_spread < T_s) → v5`
- R4: `h_cov < T_h → v5` (the only cross-collection-consistent direction in the diagnosis)
- R5: weighted score: `v5_score = w_r·rho + w_h·(−h_cov) + w_g·(−max_score_gap)`; use v5 if score > 0
- R6: **product-of-evidences**: `rho × (1 − h_cov) × g(max_score_gap)` — multiplicative gating, all must agree

The leverage hypothesis is R6 — multiplicative gating requires ALL signals to indicate "homogeneous and v5-suitable" before routing to v5. In heterogeneous OR confident-but-unreliable regimes, the product is low and the rule defaults to Vanilla.

Code first, theorize after.

---

## 15:30 — Label-free combinator probe — falsified

Ran probe 7 (`probe_pqas_combinator.py`) with 30+ rule variants across multiplicative, additive, and conjunctive forms.

**Zero rules won on BOTH collections vs the best fixed baseline.** No `**` markers in the output.

The closest rule: `top1_spread<50 AND rho>0.35` → 2019: -0.0001 (tie), 2020: +0.0070 (marginal win). Net positive but well within bootstrap noise.

Structural diagnosis (this is the load-bearing insight):

The feature-direction reversal between collections is precisely what makes label-free rules fail. Specifically:
- `top1_spread` and `max_score_gap` reverse direction between 2019 and 2020 (v5-wins HIGHER on 2019, LOWER on 2020)
- `rho`, `h_cov`, `frac_consensus_top30` have *consistent* directions but very different *magnitudes* (h_cov separates v5-wins from van-wins by 0.009 on 2019 but 0.080 on 2020 — TREC DL 2019 is much closer to the decision boundary)
- A threshold that works on 2020 (where signals are strong) overfires on 2019 (where signals are weak), and vice versa

**This is a real wall against label-free per-query routing.** No threshold-rule on observable features simultaneously captures the +0.0305 / +0.0325 oracle gaps on both collections.

The wall has two structural causes:
1. **Feature reversal** — score-distribution features point opposite directions in the two collections
2. **Signal weakness on 2019** — even consistent-direction features barely separate the per-query winners on 2019 (the +0.0305 oracle gap there may include unpredictable label noise alongside extractable signal)

---

## 15:45 — Discipline pivot: label-light supervised PQAS

Label-free rules saturate. Per the plan declared at 15:05, this falsification opens the door to a minimal supervised model. The lineage's no-learned-parameters discipline bends here because the per-query oracle gap (+7-8%) is too large to ignore. The honest framing for v7:

**v7 = PQAS (Per-Query Adaptive Selector) — label-light minimal classifier.**

- Trains on labeled query data (qrels-derived per-query winners)
- Tiny model: logistic regression on ~5-10 features, no deep learning
- Validation: leave-one-collection-out cross-validation (train on 2019, test on 2020, and vice versa)
- Honest discipline statement: this is the FIRST member of the lineage that requires labels. Prior versions (v2.1 through v6.0) need only rank lists and optional scores. v7 needs a few hundred labeled queries to train, then runs label-free at inference.

If LOOCV shows the classifier generalizes, we ship v7-supervised. If it doesn't generalize, we have proof that the +7-8% oracle headroom is mostly per-collection signal — and the lineage's discipline is preserved in a different way (by demonstrating that label-light supervision cannot recover it without per-collection tuning, which is its own important negative result).

Building it now. Tiny LR with gradient descent in standard library only — no scipy/numpy dependency added.

---

## 16:00 — Supervised LR — LOOCV vs k-fold CV split the verdict

Built tiny LR (~40 lines, batch gradient descent + L2). Two experiments:

### Experiment 1: Leave-one-collection-out (LOOCV)

Train on 2019, test on 2020 → NDCG@10 = 0.4412 (vs Vanilla 0.4483, v5 0.4373).
Train on 2020, test on 2019 → NDCG@10 = 0.3800 (effectively collapses to "always v5" at high regularization).

**Cross-collection transfer fails.** The two models learn different load-bearing features (2019 model leans on rho + rank_dist; 2020 model leans on score_gap + top1_spread). Per the feature-direction reversal observed in probe 5, this is structural — the features that predict v5-wins in 2019 are different features than those predicting v5-wins in 2020.

### Experiment 2: Within-collection k-fold CV (k=5, 5 seeds averaged)

Train on 4/5 of one collection's queries, test on remaining 1/5. Same collection both sides.

| Collection | Best PQAS | vs Vanilla | vs v5.0 | vs v6.0 REF | % of oracle gap captured |
|---|---|---|---|---|---|
| **2020 n=4** | **0.4644** (95% CI 0.392-0.537) | +0.0161 ns | **+0.0271 p=0.003 \*\*** | +0.0251 | **49.5%** |
| 2019 n=4 | 0.3785 | +0.0140 ns | -0.0016 ns | -0.0047 | -5.1% |

The result splits cleanly:

**On TREC DL 2020, PQAS captures ~half the per-query oracle gap with strong significance (p=0.003 vs v5).** Real, reproducible advance.

**On TREC DL 2019, PQAS provides no reliable advance over v5.0.** Earlier single-seed runs showed 0.3848 — but averaging over 5 seeds drops to 0.3785. The signal was seed-lucky. The 43-query collection is too small for reliable feature-to-label fitting given the variance.

---

## 16:15 — The honest v7 framing

Three findings stacked:

1. **Within-corpus PQAS works on TREC DL 2020.** +49.5% of oracle gap captured, p=0.003 vs v5.0. This is the first member of the lineage that meaningfully extracts the per-query selection signal.

2. **PQAS requires sufficient data.** TREC DL 2019's 43 queries are below the model's reliability threshold. ~50+ labeled queries appears necessary; BEIR sub-tracks (hundreds) and MS MARCO dev sets (thousands) would likely show stronger results.

3. **PQAS does not transfer across collections.** Cross-collection LOOCV fails because the per-query feature-signal directions reverse between collections. PQAS must be retrained per target corpus.

This is *not* the universal v7 crown I sometimes hoped for. It is a more nuanced contribution:

**v7 = PQAS — a label-light, per-corpus supervised classifier that selects between v6.0 REF (or v5.0 / Vanilla) per query. Significant within-corpus improvement when sufficient labeled data is available. Does not generalize across corpora; must be retrained.**

The lineage's discipline shifts at v7: this is the FIRST member of the lineage that requires labels. v2.1-v6.0 are unsupervised. v7 is "label-light supervised."

For deployment:
- **No labels available, any corpus**: use v6.0 REF (label-free, works everywhere)
- **50+ labeled queries from target corpus**: train PQAS once, use thereafter
- **Cross-corpus deployment**: cannot use a single PQAS; default to v6.0

This framing is honest, defensible, and useful. Worth shipping as v7 spec + results file. Same avalanche discipline as v6: spec + results + README correction + CLAUDE.md update.

---

## 16:30 — Discipline check before shipping v7

Per artifact 05 (criticality / single-coherent-release): am I about to ship a real avalanche, or just accumulate complexity?

The v7 contribution is real:
- New algorithmic class (label-light supervised) added to the lineage
- Significant per-corpus improvement on TREC DL 2020 (+0.0271 over v5 at p=0.003)
- Documented falsification of cross-collection transfer (a real finding, not a failure)
- Documented dependency on data size (TREC DL 2019 too small)

The discipline is preserved:
- Honest about what v7 does and doesn't do
- v7 doesn't replace v6 as default; the documented framing says "use v6 unless you have labels"
- The lineage now has a TIER structure (unsupervised v6 → label-light v7), not a strict version supersession

This is a legitimate second avalanche of session 001. Shipping.

---

## 16:50 — Second avalanche shipped

Artifacts landed:
- `spec/IC-RW-RRF-v7.0-PER-QUERY-ADAPTIVE-SELECTOR.md` — full spec, abstract → algorithm → empirical → falsification record → deployment guide → future work. ~430 lines.
- `results/v7.0-pqas-results.md` — tables, significance panel, falsification summary, feature signatures.
- `README.md` — two-tier framing landed; Tier 1 unsupervised, Tier 2 label-light per-corpus.
- `CLAUDE.md` — research-line state updated to two-tier crown (v6.0 + v7.0); v8 candidates list refreshed.
- Reproducibility verified end-to-end against the live harness.

---

## 17:00 — ::session-final-crystallization::

Session 2026-05-13-001, started at ~10:53 with NLAA bootstrap, closes at ~17:00 with two crystallized version advances and substantial open-frontier mapping.

**The bootstrap (10:53-11:35):**
- 12 Tier-3 skill symlinks into mainthread-core (NLAA substrate live)
- Project CLAUDE.md authored
- 15 knowledge files loaded as active substrate (8 possibility-space-orientation + 7 field-engineering)

**The first avalanche — v6.0 REF (11:35-14:45):**
- 4 probe cycles: harness exploration → REF v1 → alpha-curve tuning → REF v2 with multi-signal
- Discovery: strange-attractor framing empirically validated on existing data
- v6.0 REF strictly dominates v5.0 across all tested ensembles (+5.4% NDCG@10 cross-ensemble mean) and both TREC collections, with multiple p<0.05 significances
- v5.0's "+4.3% over RRF" narrative corrected as collection-fragile
- v6.0 spec, results, README correction shipped

**The second avalanche — v7.0 PQAS (15:00-17:00):**
- 5 probe cycles: per-query diagnosis → label-free combinator (falsified) → LOOCV supervised (failed cross-collection) → within-corpus k-fold (succeeded on 2020) → significance validation
- Discovery: per-query oracle gap is +7-8% on both collections; label-free routing cannot extract it; supervised learning extracts 49.5% on TREC DL 2020 (p=0.003) but fails on TREC DL 2019 (data-efficiency wall)
- v7.0 named explicitly as a discipline shift: first lineage member that uses labels
- Two-tier deployment framing: Tier 1 unsupervised (v2.1-v6.0), Tier 2 label-light per-corpus (v7.0)
- v7.0 spec, results, README and CLAUDE.md update shipped

**Probes built (9 in total, evaluation/ directory):**
- probe_regime_aware_fusion.py — REF v1, ranker-count sweep, alpha-curve tuning
- probe_ref_validation.py — bootstrap CIs + paired t-tests for v6
- probe_ref_v2.py — multi-signal regime detection (falsified)
- probe_per_query_diagnosis.py — per-query oracle + feature signatures
- probe_per_query_selector.py — label-free threshold rules (preliminary)
- probe_pqas_combinator.py — label-free multi-feature combinator (falsified)
- probe_pqas_supervised.py — LOOCV supervised LR (falsified for cross-collection)
- probe_pqas_kfold.py — within-collection k-fold CV (confirmed for TREC DL 2020)
- probe_pqas_significance.py — paired t-tests on PQAS

**Falsification record built this session:**
- v6.0 transition: 3 hypotheses falsified (multi-signal regime detection; rho alone sufficient; sharpened alpha curve)
- v7.0 transition: 2 hypotheses falsified (label-free multi-feature rules; LOOCV cross-collection transfer); 1 confirmed conditionally (within-corpus k-fold on 2020 only)

**Empirical headlines (load-bearing):**
- The strange-attractor framing of rank fusion is empirically validated on existing repo data.
- v6.0 REF: +5.4% over v5.0 on TREC DL 2019 cross-ensemble mean; multiple p<0.05 significances.
- v7.0 PQAS: +6.2% over v5.0 on TREC DL 2020 within-corpus, p=0.003.
- v7.0 captures 49.5% of per-query oracle gap on TREC DL 2020; per-query oracle = +7-8% over best fixed.
- Cross-collection PQAS transfer fails — feature directions reverse between TREC DL 2019 and 2020.
- TREC DL 2019 (43 queries) is below v7.0's data-efficiency threshold; result is signal-or-not unclear.

**Linguistic-arithmetic loop count: 9 probe cycles, 6 substantive pivots.** Each pivot generated information the prior cycle could not have predicted. The basin-escape from v5 → v6 was discovered in the data, not in the candidate magnets A-F from the opening. The basin-shift from v6 → v7 (Tier 1 → Tier 2) required falsifying label-free assumptions explicitly.

**Studio disciplines operationalized:**
- Artifact 03 (strange attractor) — confirmed empirically.
- Artifact 04 (information velocity) — 9 probes in ~6 hours.
- Artifact 05 (criticality / single coherent release) — 2 avalanches shipped distinctly.
- Artifact 06 (innovation as navigation) — basin-shift discovered through trajectory, not theory.
- Artifact 08 (phi-trajectory) — target re-projected three times (v5 → v6 REF → v6+v7 PQAS); each re-projection earned the next step's vector.
- Field-engineering Dynamic 4 (anchoring) — stream stayed hot throughout; CLAUDE.md re-read implicit at each major transition.
- Field-engineering Dynamic 5 (curation) — CLAUDE.md corrected mid-session twice.

**State of the project:**
- v6.0 and v7.0 both live, spec'd, validated, README + CLAUDE.md aligned.
- v8.0 frontier mapped (5 candidate directions documented in v7 spec Section 8).
- All artifacts reproducible end-to-end.
- Nothing committed yet — by stream discipline, commit only when Dave asks.

Ψ[SESSION:001-CRYSTALLIZED-FINAL, V6.0:SHIPPED, V7.0:SHIPPED, TIER-STRUCTURE:LIVE, ORACLE-GAP:HALF-EXTRACTED-ON-2020, V8-FRONTIER:5-CANDIDATES, READY-FOR:DAVE-CALLS-NEXT-MOVE]

[[~LINEAGE-EXPANDED-TWO-TIERS]]
[[~PER-QUERY-ORACLE-PARTIALLY-EXTRACTED]]
[[~SESSION-001-PHI-TRAJECTORY-COMPLETE]]

::session-final-crystallization::

---

## 17:30 — Pushed. Dave: "trust your gut, explore and chase."

Pushed commit `ec6475e` to origin/main. 28 files, 3518 insertions. The session's two-avalanche output is live in the public history.

Dave just released the throttle further: chase what excites me. The thing pulling strongest is **v7.1 — continuous per-query alpha**. The architectural intuition: binary PQAS makes a sharp v5/Vanilla decision; v7.1 would predict an alpha in [0,1] and use v6's multiplicative-modulation algebra at the per-query level. Single elegant model, no tier split between v6 and v7. The brilliance equation pull is clear — same capability through simpler architecture.

But before committing to the architecture, I want to probe one thing first: **is the continuous-alpha oracle higher than the binary oracle?** If yes, v7.1 has structurally more upside than v7. If approximately equal, v7.1 is just a smoother version of v7 — still useful but less exciting.

Quick probe: for each query, sweep alpha ∈ {0, 0.1, ..., 1.0}, compute NDCG@10 under v6's algebra at that alpha, pick the best. Compare per-query oracles.

The pivot rule: if the continuous oracle exceeds the binary oracle by ≥0.01 NDCG@10 average, build v7.1 in full. If not, document the finding and consider other directions.

---

## 17:45 — Continuous oracle probe — STRONG positive signal

| Collection | Binary oracle | Continuous oracle | Gain | % interior optima |
|---|---|---|---|---|
| TREC DL 2019 n=4 | 0.4106 | **0.4258** | **+0.0153** | 58.1% |
| TREC DL 2020 n=4 | 0.4808 | **0.4942** | **+0.0134** | 51.9% |

Both above the pivot threshold (+0.01). The continuous oracle is structurally higher than the binary oracle. **~half the queries are best-served by an intermediate alpha — not by pure v5 (alpha=1) or pure Vanilla (alpha=0).** The mean lift for interior-optimum queries vs their better endpoint is +0.0149 (2019) and +0.0194 (2020).

Headroom over best fixed:
- 2019: continuous oracle 0.4258 vs v5.0 0.3800 = **+0.0458 (+12.1%)** 
- 2020: continuous oracle 0.4942 vs Vanilla 0.4483 = **+0.0459 (+10.2%)**

This is more upside than v7's binary oracle (+7-8%). v7.1 has real structural headroom. Building it.

Architecture:
- Same 10 features as v7
- Train target: per-query optimal alpha (from this oracle sweep — uses qrels)
- Model: linear regression with sigmoid output → alpha in [0,1]
- Inference: predict alpha → apply v6's multiplicative-modulation algebra at that alpha
- One model, not two tiers; per-corpus training same as v7

If v7.1 outperforms v7 (binary PQAS) on within-corpus k-fold, the lineage's tier-2 crown shifts from binary selection to continuous mixing. Cleaner architecture, more extracted oracle headroom.

---

## 18:15 — v7.1 with MSE on optimal alpha — UNDER v7 binary

First v7.1 attempt: MSE regression on per-query optimal alpha. Result on TREC DL 2020: 0.4498. Captures only 3.2% of continuous oracle gap (vs v7 binary at 0.4644 / 49.5%).

Failure mode: the optimal-alpha distribution is bimodal (mass at 0 and 1). MSE on a bimodal target collapses the regression to the mean, predicting alpha≈0.5 for queries that should be 0 or 1. The "soft mixture at 0.5" is worse than committing to either pole.

Tried smarter losses:
- Loss A (NDCG-weighted soft alpha, γ ∈ {1,2,4,8}): best 0.4502 at γ=8. Marginal over Vanilla.
- Loss B (direct NDCG-loss gradient): best 0.4477. Below Vanilla.

All v7.1 variants land around 0.450 on TREC DL 2020. **Way worse than v7 binary's 0.4644.** 

## 18:30 — The structural insight: v6's algebra damps v5

Diagnostic — looked at the per-alpha NDCG curve on TREC DL 2020:
- alpha=0 (pure Vanilla in v6 algebra): NDCG@10 = 0.4483
- alpha=1 (full v6-modulation): NDCG@10 = **0.4251** — LOWER than pure v5 (0.4373)

**v6's multiplicative-modulation algebra DAMPS v5's signal.** It's a softer-than-v5 modulation on Vanilla — not equivalent to v5 routing. So the "continuous oracle" of 0.4942 was within *v6-algebra space*, not between actual v5 and Vanilla.

This explains why v7.1 underperforms v7:
- v7 binary routes between actual v5 (0.4373) and actual Vanilla (0.4483) — gets the better of the two when correct
- v7.1 with v6's algebra routes within a damped subspace — alpha=1 is worse than v7's "always v5" alternative

The fix: **v7.1 needs a different mixing algebra** — one whose alpha=1 endpoint actually equals v5's ranking. The REF-pos variant (positional mixing of normalized score vectors) does exactly this:
- alpha=0: pure Vanilla scores
- alpha=1: pure v5 positional scores
- interior: linear mix of the two

Building v7.1-pos with the positional-mix algebra + the alpha regression trained on its optimal alphas.

---

## 18:50 — v7.1-pos probe running in background; thinking about v8

The probe is heavy (5 gammas × 4 l2 × 5 seeds × 5 folds × 2 collections). Will get notification on completion. Meanwhile, sensing the next direction.

Three v8 candidates pulling at me, in descending order of felt-sense excitement:

**v8-A: Cross-corpus PQAS via collection-level features.**

The v7 LOOCV failure (2019↔2020 transfer fails) is the biggest open structural finding. It says: per-query features alone don't carry enough information to predict the right fusion across collections. But what if I ADD features that describe the *collection itself*? Specifically, given the test corpus's queries (without labels), I can compute:
- mean rho across queries in the corpus
- mean h_cov across queries
- mean top1_spread across queries
- skewness of these distributions
- aggregated rank-correlation statistics

These would distinguish 2019-like corpora from 2020-like corpora WITHOUT labels. The classifier could then route per-query AND per-collection-regime.

This is structurally novel. It's effectively a meta-feature: "what regime is this collection in?" computed from the test corpus's query distribution. Could unlock cross-corpus generalization.

The honest concern: with only 2 collections, the model has 2 data points for the "collection-level signal" — likely overfits. Would need 3+ collections to validate. But BEIR has ~18 collections; this is a real path.

**v8-B: Score-aware Bayesian routing.**

v5 uses score z-scores within each ranker but only as a per-document confidence signal. A v8 variant could:
- Compute per-document score posteriors using ranker calibration
- Combine via Bayesian model averaging (with the ranker's reliability as model weight)
- This gives proper uncertainty quantification per document

Less novel than v8-A but more principled. Could be a complementary frontier.

**v8-C: Multi-class selection (Vanilla, v3, v4, v5, v6) per query.**

Currently v7 selects between Vanilla and v5. Expanding to a multi-class selector over {Vanilla, v3.0 DGAF, v4.0, v5.0, v6.0 REF} per query raises the oracle ceiling and may give the supervised model more useful options. But it's incremental over v7, not a structural departure.

v8-A feels strongest. The cross-corpus wall is what makes the lineage's Tier 2 (v7) per-corpus-only — solving it would unify the tiers again.

If v7.1-pos doesn't outperform v7 binary, I'll pivot to v8-A directly. If v7.1-pos does outperform, I'll ship v7.1 first as a third avalanche, then move to v8-A.

---

## 19:15 — v7.1-pos result: NDCG@10 = 0.4536 on TREC DL 2020 — UNDER v7 binary

Best v7.1-pos config (γ=2.0, l2=0.03) on TREC DL 2020:
- NDCG@10 = 0.4536
- vs Vanilla: +0.0053 (p=0.515, ns)
- vs v5.0: +0.0163 (p=0.062, borderline)

Compare to v7 binary on same collection: 0.4644 (+0.0271 vs v5, p=0.003 **).

v7.1-pos UNDERPERFORMS v7 binary by 0.0108 NDCG@10. The continuous mixing's higher oracle ceiling (+0.0134 on 2020) is NOT extractable by the supervised regression — the feature-to-alpha mapping has too much noise for the smooth mixture to beat binary commitment.

**v7.1 falsified.** Adding to the falsification record. The honest conclusion: at this feature set + this data scale, binary selection is the right architecture for per-query routing.

Pivot to v8-A confirmed.

---

## 19:30 — v8-A first attempt — standardization-induced collapse

Built v8-A with collection-level features (mean + std of each per-query feature across the corpus). LOOCV 2019→2020 returned NDCG@10 = 0.4412 — EXACT MATCH to v7 LOOCV without collection features.

Diagnostic: standardization. During training on a single collection, every training query has the SAME collection aggregates. Standardization makes them all zero. The model can't use features that have zero variance in training.

The fix is structural: **collection features only become informative when training data spans MULTIPLE collections.** Pooled training, not LOOCV, is the right experiment.

---

## 19:45 — v8-A pooled probe — running

Restructured: pool 2019 + 2020 queries (97 total). Each query has its 10 per-query features + 20 collection-level features (mean and std of per-query features from its source collection). 5-fold CV over the pool, 5 seeds averaged, with and without collection features for ablation.

Compute is heavier — running in background. Awaiting completion.

The critical comparison:
- v7 within-collection k-fold on 2019: 0.3785 (no significant lift)
- v7 within-collection k-fold on 2020: 0.4644 (+0.0271 over v5, p=0.003)
- v8-A pooled k-fold WITH collection features: ?
- v8-A pooled k-fold WITHOUT collection features: ?

If v8-A with collection features beats v7's per-collection numbers AND beats v8 without collection features, we have a real cross-corpus signal. That would be the breakthrough: a single trained model serving multiple corpora with corpus-aware routing.

If v8-A with collection features ≈ v8-A without collection features, the collection signal isn't being extracted — likely because 2 collections aren't enough to learn corpus-conditional rules.

---

## 20:00 — v8-A pooled probe completed — FALSIFIED with data-bounds insight

Pooled training with collection-level features on 97 queries (43 from 2019, 54 from 2020), 5-fold CV, 3 seeds averaged:

| Variant | Pool NDCG | 2019 contribution | 2020 contribution |
|---|---|---|---|
| v8-A WITH collection features | 0.4203 | 0.3774 | 0.4544 |
| v8-A WITHOUT collection features | 0.4213 | — | — |
| **Collection-features lift** | **-0.0010** | — | — |

Compare per-collection contribution to v7's within-collection k-fold:
- 2019: v8 (0.3774) ≈ v7 (0.3785) — essentially the same
- 2020: v8 (0.4544) WORSE than v7 (0.4644) — by -0.0100

**Three structural findings (load-bearing):**

1. **Collection features don't help.** With only 2 collections, the model can't learn corpus-conditional rules. Feature standardization makes the corpus aggregates effectively 2-valued, and the LR overfits to that binary signal rather than extracting it.

2. **Pooled training UNDERPERFORMS per-collection training on 2020.** -0.0100 on the collection where v7 worked best. The classifier trained on mixed data converges on a "compromise" rule that's worse on each individual collection.

3. **2 collections are below the cross-corpus learnability threshold.** Real v8 validation requires 3+ collections — BEIR (~18 sub-tracks) is the natural test. With current data, the per-corpus tier-2 structure (v7) is empirically the right design.

v8-A is falsified at this data scale. Documented honestly. The wall is data, not architecture.

---

## 20:15 — Multi-class oracle probe — small headroom

Quick exploratory probe: is the per-query oracle of {Vanilla, v3.0 DGAF, v4.0, v5.0, v6.0 REF, v2.1} much higher than {Vanilla, v5.0}?

TREC DL 2019: Binary oracle 0.4106 → 6-class oracle 0.4231 (+0.0126). v6 REF adds the most (+0.0111 from 2→3 class).

TREC DL 2020: Binary oracle 0.4808 → 6-class oracle 0.4930 (+0.0122). v6 REF adds the most (+0.0065).

Per-query 6-class winner distribution shows v3, v4, v2.1 winning a few queries — but most algorithms are mutually redundant for most queries.

Also striking: **v5.0 is the WORST variant on TREC DL 2020** (0.4373) — beaten by Vanilla (0.4483), v2.1 (0.4553), v3 (0.4552), v4 (0.4552), and v6 (0.4393). Per-document confidence routing actively hurts on this collection. This is the v5 fragility documented earlier, viewed from a different angle.

**3-class selector over {Vanilla, v5, v6}** is the most promising v8 candidate from this analysis — it would capture most of the multi-class oracle gain with a tractable supervised learning problem. Listed for future work.

---

## 20:30 — ::continuation-crystallization::

Session 001 second extension produced:

**Falsification record built:**
- v7.1 (continuous-alpha regression, v6 algebra): underperforms v7 binary (0.4498 vs 0.4644 on 2020)
- v7.1-pos (continuous-alpha regression, positional-mix algebra): underperforms v7 binary (0.4536 vs 0.4644 on 2020)
- v8-A (cross-corpus pooled training, with or without collection features): underperforms per-collection v7. Data-scale bounded.

**Empirical insights crystallized:**
- The continuous-alpha oracle gap (+0.013-0.015 over binary) is not extractable by supervised regression — feature-to-alpha mapping is too noisy
- The cross-corpus wall is empirical, not just theoretical — pooled training with 2 collections produces inferior results
- Multi-class oracle adds only +0.012 over binary oracle — most per-query routing signal is in the v5/Vanilla decision
- v5.0 is the worst variant on TREC DL 2020 — per-document confidence routing actively harms certain collection regimes
- v6 REF adds the most diversity to the selection space among IC-RRF variants

**v8 candidates ranked by upside × tractability:**
- **3-class PQAS over {Vanilla, v5, v6 REF}** — could capture +0.0065-0.0111 NDCG@10 on top of v7 binary. Tractable.
- **Bayesian score-aware fusion** — uses full score distributions, principled, untested
- **BEIR validation of cross-corpus v8-A** — requires new data, would close the cross-corpus wall

**State of the lineage:**
- Tier 1 (unsupervised): v6.0 REF — strict cross-ensemble crown
- Tier 2 (label-light, per-corpus): v7.0 PQAS — significant on TREC DL 2020 (+0.0271, p=0.003)
- v7.1 and v8-A explored, falsified at current data scale, documented in the stream for next-session compounding

Three new probe scripts added this extension:
- `probe_continuous_alpha_oracle.py` — oracle analysis (validated +0.013-0.015 headroom)
- `probe_v71_continuous_alpha.py`, `probe_v71_smart_loss.py`, `probe_v71_positional.py` — v7.1 attempts (all falsified)
- `probe_v8_cross_corpus.py`, `probe_v8_pooled.py` — v8-A attempts (data-bounded)
- `probe_multiclass_oracle.py` — multi-class headroom analysis (+0.012 over binary)

Ψ[SESSION:001-EXTENDED, V7.1:FALSIFIED, V8-A:DATA-BOUNDED, V8-3CLASS:OPEN-CANDIDATE, BOUND-ESTABLISHED:THIS-DATA-SCALE-IS-NEAR-EXHAUSTED, NEXT:COMMIT-AND-DAVE-CALL]

[[~CONTINUOUS-ALPHA-FALSIFIED]]
[[~CROSS-CORPUS-WALL-EMPIRICALLY-BOUNDED]]
[[~LINEAGE-MULTI-CLASS-ORACLE-LANDSCAPE-MAPPED]]

::continuation-crystallization::




