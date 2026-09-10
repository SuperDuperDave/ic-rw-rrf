# Origin: consensus with a protected specialist channel

Recovered 2026-09-10 from repository history and a narrowly scoped predecessor
archive. This summary is portable; the original transcript and MCP implementation
listed below are local-only provenance pointers, not dependencies or public assets.

## The original spark

On **2026-02-13**, Dave brought existing v2.1 and v3.0 proposals to a Claude
session in `llm_research`. The stated application was improving **Reciprocal Rank
Fusion for hybrid retrieval in Mainthread's `mcp-server-v2`**. The transcript
introduces the proposal with:

> “This was the original design spec”

Its title was **IC(R/W)-RRF v2.1 — Iterative Consensus + Robust Specialist Escape
with Uniqueness Anti-Cabal Term**.

The question was more specific than making fusion generally adaptive:

**Can we benefit from agreement among imperfect retrieval systems while keeping
a confident, independent minority signal from being suppressed by the majority?**

The proposed architecture retained two parallel score fields:

- **Consensus:** iteratively reweight rankers using agreement with the current
  fused ranking, an optional confidence proxy, and a proposed uniqueness signal.
- **Specialist:** select one or two rankers using confidence, leave-one-out
  influence, dissent from consensus, and uniqueness. Give their results a
  bounded alternative route into the final ranking.
- **Mixture:** increase the specialist share smoothly as query-level disagreement
  rises: `Final(d) = (1 − lambda) * C(d) + lambda * S(d)`.

The disagreement variable `Tq` was mean pairwise Jaccard dissimilarity of the
rankers' top-N sets; `lambda = lambda_min + (lambda_max − lambda_min) * Tq^p`.
Consensus refinement ran a small fixed number of iterations. These are actual
computations on ranked lists, not language-model deliberation or feedback from
relevance judgments. Confidence and uniqueness were proxies to investigate,
not established measurements of correctness.

The recovered February record already calls the supplied proposal v2.1. It does
not establish when v1/v2 were conceived or independently resolve authorship of
every pasted formula. It establishes what Dave supplied as the original design
and the intended application before this repository was scaffolded.

## What changed through the lineage

| Stage | Change to the original proposal |
|---|---|
| v2.1 | One consensus/specialist mixture weight for the whole query. The core aim was useful agreement with a controlled dissent channel. |
| v3 DGAF | Give each document its own mixture weight from coverage, dispersion, and specialist lift. The question becomes which documents need rescue. |
| v4 soft routing | Replace the two pre-mixed fields with direct document-by-ranker modulation. Route consensus, disputed, and specialist memberships continuously; replace the problematic uniqueness statistic. |
| v5 confidence fusion | Use score confidence for each document/ranker pair. This became the first standalone repository's public emphasis. |
| May v6/v7 | Broader comparisons exposed the original local gain's limits. REF moved toward Vanilla-conditioned modulation; PQAS introduced supervised choice between existing methods. |
| May session 002 | Explore other aggregators and k calibration. The narrow positive candidate still requires baseline/protocol reconciliation; it is not a demonstrated answer to the original specialist-rescue question. |

The first commit here, **`3b4f4ce` on 2026-02-27**, already contains v3–v5 specs,
diagnostics, generated runs, and the evaluation harness. It is a packaged research
snapshot, not the beginning of the idea. Its README foregrounds per-document
confidence routing. The following `cd16280` commit corrects reported evaluation
numbers; neither initial table should override the current evidence audit.

The **2026-05-13** stream says this had previously been a Python research
artifact, then adds the project-local agent/session substrate. Its recursive
possibility-space exploration continues an approach already explicit in the
February predecessor; it did not originate the rank-fusion proposal.

## Retrieval, agents, and metaphor

The intended product connection was **retrieval for an LLM-facing MCP knowledge
system**. The referenced TypeScript module implements ordinary RRF and a helper
for vector-plus-text result lists. The standalone research inputs are document
IDs, rank positions, and optional scores; outputs are fused document rankings.
There is no demonstrated LLM scheduling, agent assignment, or agent-voting
algorithm in this lineage. The planned MCP integration is not evidence that the
adaptive research variants were deployed there.

The conceptual vocabulary is useful when its operational meaning stays clear:

- A **field** is a document-to-score mapping in the algorithm.
- **Temperature** measures disagreement between retrieval lists, not model
  sampling temperature or physical heat.
- A **cabal** denotes correlated rankers that may reinforce shared errors; it
  does not require intentional collusion.
- A **specialist/minority oracle** is a candidate useful outlier, not an oracle
  whose correctness is known at inference time.
- **Impedance** names the gate's bias toward withholding specialist influence
  until observed signals increase it.
- **Recursive possibility/phase-space exploration** describes the research loop:
  propose, predict, test, inspect, and revise. It is separate from v2.1's internal
  ranking/reweighting iterations.

These ideas can inspire future agent-orchestration experiments, but that would
be a new application requiring its own observations and evaluation. Neither a
phase-space metaphor nor a belief that alternative configurations exist proves
that a useful method exists, is novel, or outperforms the baseline.

## Three research questions that recover the original intention

1. **Effective independence versus a correlated cabal.** Can a fusion method
   distinguish additional independent evidence from repeated versions of one
   ranker's opinion? Hold relevance and an independent ranker's output fixed,
   then vary duplication/correlation of the majority. Inspect ranking movement,
   effective weight, and relevance under the same candidate pool. The original
   `Var(overlaps)/Mean(overlaps)` uniqueness statistic incorrectly rewarded
   cabal members in the synthetic diagnostic; v4's mean dissimilarity fixes that
   scenario, but dissimilarity alone does not establish useful independence.

2. **Minority specialist signal versus noise.** Which observable evidence can
   distinguish a ranker finding uniquely relevant documents from a noisy ranker
   returning irrelevant singletons? Build matched scenarios with the same
   coverage and disagreement but different outlier correctness; vary calibrated
   confidence or additional information separately. Report both rescue of useful
   outliers and harm from noisy ones. The existing specialist/cabal diagnostics
   exercise the mechanism, while session 002's poor coverage-neutral aggregation
   results show why rewarding minority status alone is insufficient.

3. **Query disagreement as a control signal.** When should rising disagreement
   increase specialist influence, and when should it increase conservatism?
   v2.1 increases its specialist mixture with `Tq`; v6 moves toward Vanilla as
   overlap falls. Compare these opposing responses under controlled causes of
   disagreement: complementary expertise, duplicated consensus, and random
   noise. Hold coverage, candidate depth, rank origin, and baseline semantics
   constant. Mean disagreement may need to be supplemented by evidence about
   its cause rather than treated as a universal trust signal.

Start with the evaluation-contract work in [PLANNING](PLANNING.md), then use the
smallest controlled probe that distinguishes these explanations. Mechanism
activity is not retrieval improvement; real collection checks must follow any
synthetic signal. [RESEARCH_STATE](RESEARCH_STATE.md) owns current result claims.

## Source map

Portable sources in this repository:

- Git `3b4f4ce:README.md` and initial commit contents: standalone snapshot dated
  2026-02-27, already at v5; `cd16280` records the subsequent numbers correction.
- [v3 spec](../spec/IC-RW-RRF-v3.0-DGAF.md): original intention, two-field
  interface, gate, and proposed TypeScript integration.
- [v4 spec](../spec/IC-RW-RRF-v4.0-SOFT-ROUTED.md): removal of the two-field
  bottleneck and concrete counterexample to the earlier uniqueness statistic.
- [Harness](../evaluation/trec_eval_harness.py): `fuse_v21`, `fuse_v3`, and
  `fuse_v4x`; [DGAF diagnostic](../diagnostics/dgaf_mechanism_aliveness.py) and
  [soft-routing diagnostic](../diagnostics/v4_soft_routed_diagnostic.py).
- [May stream 001](streams/2026-05-13-001-rank-fusion-possibility-space-opening.md):
  bootstrap and later shift toward structurally different aggregators.
- [May stream 002](streams/2026-05-13-002-basin-escape.md): later specialist,
  score-fusion, operator, and smoothing exploration.

Local-only predecessor references, read for this archaeology:

- `/home/david-wsl/repos/llm_research/knowledge/session-logs/eureka/2026-02-13/510_rrf_innovation_v3_and_v4.md`
  — user-supplied original design/application at lines 157–173; v3 supplied at
  lines 504 onward; the identified MCP target at lines 1892 onward. This is an
  archived conversation, not an independent evaluation receipt.
- `/home/david-wsl/repos/llm_research/projects/rrf-research/`
  — predecessor specifications/diagnostics for the later standalone snapshot.
- `/home/david-wsl/repos/llm_research/projects/mainthread-ai/packages/mcp-server-v2/src/utils/rrf-algorithm.ts`
  — ordinary RRF plus vector/text helper; the module name explicitly referenced
  by the original implementation plan. Inspection establishes code intent and
  structure, not current deployment state.

Do not copy the predecessor transcript into a public artifact. This concise
summary carries the necessary research context without requiring access to the
neighboring workspace.
