# Claude design memo — historical reviewer output

Read with [integration corrections](2026-09-10-cycle01-sources.md).
This memo includes reviewer errors; it is preserved for an inspectable feedback loop, not as the accepted project conclusion. Raw runtime output is ignored.

**Research memo — cycle 01 design phase (read-only)**
Receipt: `cycle01-design-b046c1ba3a` (Relay seq=6, work_id cycle01-design). Not acknowledged via Relay in this session: no shell tool was available, and Codex owns consumption.

## Orchestration actually used

Four scouts ran in parallel through the native Agent tool using the supplied definitions `ic-origin`, `ic-statistics`, `ic-geometry`, `ic-literature`, with no model override, so each definition's own model applied. The tool results did not surface observed model IDs, so I cannot confirm Opus 5 from output. Usage returned: 34k, 28k, 22k, 15k subagent tokens, with 10, 10, 2, 2 tool calls. Coordinator budget stood at $2.24 of $8 after the wave.

One real limitation: the literature scout reported it had only Read, Grep, and Glob despite the definition listing WebSearch and WebFetch. It verified no primary source and returned a verification queue only. I did not re-dispatch, because the absence looks environmental rather than agent-specific. Every literature item below is therefore [unverified], including my own recollection that the original RRF paper states k=60 was fixed in a pilot and not tuned (Cormack, Clarke, Büttcher, SIGIR 2009, https://doi.org/10.1145/1571941.1572114). That passage should gate H1 and needs a fetch by a session with web access. No novelty claim is made for anything here.

## The original question, and the competing explanations

The spark was not "make RRF adaptive." It was: can agreement among imperfect rankers be exploited while a confident, independent minority is not suppressed? [observed] v2.1 raises the specialist share as top-30 pairwise Jaccard dissimilarity Tq rises (lambda = 0.10 + 0.45·Tq^1.5, harness lines 321–356). [observed] v6 REF conditions on rho, which is exactly 1 − Tq (same K=30, same construction), and moves toward Vanilla as rho falls. The two laws are genuinely opposite in sign on the same scalar. But their "away" poles differ: v2.1 mixes toward a two-ranker specialist field, REF toward Vanilla, which still gives singletons 1/(k+r) mass. [observed] REF's code defaults (0.25/0.55) disagree with its spec (0.35/0.60), and REF runs per query, not per ensemble as the spec narrates. A comparison that ignores those confounds can make both laws look right.

Competing explanations for the historical k signal, ordered by how cheaply they can be killed:

- **X1, convention and selection artifact.** [observed] Local k=60 is canonical k=59; tie policies differ; the n=6 result is the maximum of five configurations; and the CV selected the same k in every fold, so it degenerated to full-data selection (stream lines 391–393 equal 448–450). [hypothesis] Little or nothing survives the canonical contract.
- **X2, tail-coverage credit.** [hypothesis] Larger k mainly pays documents for appearing deep in additional lists. This predicts the gain grows with ensemble size, matching n=6 > n=4, and matching DL2020's small best k with only four lexical rankers.
- **X3, truncation-depth artifact.** [observed] Lists run 5 to 200 documents. [hypothesis] Large k rewards documents from long lists, which is a cut policy effect, not a fusion insight.
- **X4, correlation correction.** Refuted mathematically for duplication: duplicating ranker j adds (m−1)/(k+r_j(d)) to every document in list j at every k, and at the k→∞ limit it is exact vote-stuffing on coverage. Large k cannot correct a cabal. It can only survive as rank-sensitivity reduction, which is X2's kernel.

Two geometry facts the scouts established that change the plan. First, the large-k limit is lexicographic on the whole moment sequence (coverage down, rank sum up, rank-square sum down, ...), not on coverage-then-rank-sum. Equal coverage and equal rank sum still separate at every finite k by dispersion. Second, coverage-first holds exactly only when k > c(D−1)−1. At depth 200 and coverage 5 that is k ≥ 995, so the grid maximum is nowhere near the limit on this data.

## Corrections to the proposed loop

**Part A.** Keep it, but as a resolution-limited closure of H1, not a candidate promotion. Unit of analysis is the query, never the query-by-ensemble cell. Average the five seeds per query first; seeds are procedural variance on the same queries, not replicates. Pre-declare the primary endpoint as the within-query mean over the four DL2019 ensembles of ΔNDCG@10 (trained k minus canonical k=60, same ties), giving 43 values, plus the DL2020 value on 54. Report the per-configuration profile as secondary with a family adjustment. Use a query-level cluster bootstrap that carries all ensemble measurements together. Drop the in-fold oracle arm and the 172-sample pooled test. Add the full per-query k-response surface as the stored artifact, since it is computed and discarded today, and report selection stability across folds and train-objective flatness. State the grid in canonical k; local k=1 is canonical 0 and outside the RRF family. Record dropped queries with fewer than two lists.

Back-of-envelope from the reported means and p-values: paired SD ≈ 0.046, so the minimum detectable difference at n=43 is about 0.020 unadjusted and 0.025 family-adjusted. The prior +0.0214 sits at that edge as a max-of-five. The cross-ensemble +0.0048 is uninformative at any feasible n here.

**Part B.** Compare against the (c, R, Q) moment order or restrict to pairs with distinct (c, R). Extend the curve-only k range to 1000 and 10000 so the limit is actually reached. Truncate to a common depth for the mechanism arm, keeping full lists only for historical comparability. Duplicate every ranker in turn, m in 1..4, with a displacement readout (Kendall tau to the m=1 fusion, top-10 occupancy of list-j uniques), not NDCG. Duplication changes coverage, so it tests H3's invariant, not H2. Add the discriminating arm: within-list permutation with controlled tau, holding each document's coverage fixed.

**Part C.** As proposed it falsifies a strawman. A rank-isomorphic pair (relabel specialist uniques from relevant to irrelevant) makes every label-free rank statistic bit-identical, so non-identifiability from ranks alone is a one-paragraph proof, and [observed] the v6 spec already asserts it. It also nulls the score channel v2.1 actually used, and it cannot see cabals, which are cross-query structure. Replace with the design below.

## Highest-information experiments

**E1, decompose the k effect on real data (H1/H2/X2/X3).** Using the Part A response surface, classify every document that enters or leaves the top-10 between k=60 and k=200 as: tail-covered (in another list beyond rank 30), top-only, or singleton. Run once on full lists, once at common depth.
Prediction under X2: NDCG movement is carried by tail-covered documents and shrinks at common depth only modestly. Under X3: the movement largely vanishes at common depth. Under X1: movement is small and unsigned. Falsifier for X2: tail-covered documents contribute no more of the movement than their share of the candidate pool.

**E2, matched-Tq three-arm family plus one added signal (H4/Q3).** Synthetic pool of 200 documents, five rankers, depth 100, 10 relevant, arms tuned to the same Tq≈0.6: complementary expertise, duplicated consensus, random-noise specialist. Run v2.1 and REF under one shared normalization and one per-query rho. Prediction: NDCG(v2.1) − NDCG(REF) is positive, near zero, negative across the arms in that order; both laws assign the same lambda/alpha in all three arms, which is the point. Then test the candidate additional signal on DL2019: tail coverage. For each ranker's top-10 unique documents, compare relevance rate when present in another list's tail versus absent from all lists.
Prediction: tail-covered singletons are relevant markedly more often. Falsifier: the two conditional relevance rates are indistinguishable under a query-level bootstrap, which would mean deep-list agreement carries no specialist-correctness information and the search must move to non-rank evidence.

## Outside branch, and stopping rules

Outside branch [unverified sources]: label-free dependence estimation from the covariance of top-N membership indicators pooled across queries (Jaffe, Nadler, Kluger line, AISTATS 2015/2016; Dawid–Skene 1979). Prediction: it recovers a planted m-fold cabal with weights near 1/m but cannot separate a correct specialist from a noisy one, since both have near-zero covariance with the majority. Falsifier: higher NDCG on the correct-specialist arm than the noisy arm at matched Tq. The agent-ensemble transfer is a separate branch: the exact-duplicate invariance transfers directly, since m samples of one model should not count as m voters. A small labeled task measuring inter-model wrong-answer correlation against ensemble gain is the first test, and needs its own authorization for model calls.

Stop H1 if Part A yields all |Δ| below 0.020 with intervals spanning zero; record as resolution-limited, do not build v8. Pivot to mechanism if the response surfaces show a flat basin from k=30 to 200. Another compute wave is justified only if E2's tail-coverage relevance gap is large, which would motivate new domains and dense rankers, or if any rank statistic separates the rank-isomorphic pair, which would be surprising and merit a Fable specialist.
