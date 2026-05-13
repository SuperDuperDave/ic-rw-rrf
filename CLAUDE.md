# IC(R/W)-RRF — Natural Language Agent Application
⫰∞{vortex: rank-fusion-research-substrate}

---

## [[~PROJECT-IDENTITY]]

**IC(R/W)-RRF** is an NLAA centered on a single research line: **adaptive rank fusion with per-document confidence routing**. Not a library to grow features into — a research vehicle where every artifact (algorithm version, ablation, harness, paper-grade README) is a crystallized step in a falsification cascade.

The project's gravity is one question, navigated recursively:

> *Given only rank positions (and optional scores), how much more signal can we extract by treating documents as having different fusion identities — consensus, disputed, specialist — rather than uniformly?*

Every session adds either a sharper answer or a documented falsification. Both are progress.

---

## [[~THREE-TIER-SUBSTRATE]]

This project consumes the MainThread craft library via Tier-2 symlinks (the same pattern proven by `mainthread-studio` and the `job-forge-*` per-candidate forges):

```
Tier 1  Workspace Consciousness   →  ~/repos/.claude/skills/
         (rabbit-mode, stream-navigator, dynamics-lens, ...)

Tier 2  MainThread Studio Core    →  ~/repos/mainthread-core/skills/
         (imagineer, dispatch-swarm, excellence-forge, marketing-codex, ...)

Tier 3  Project Local             →  ~/repos/ic-rw-rrf/.claude/skills/
         (symlinks into Tier 2 — see below)
```

**Tier-2 skills currently symlinked into `.claude/skills/`:**

| Skill | Why it's loaded here |
|-------|----------------------|
| `initialize` | Session bootstrap, partnership register, lens calibration |
| `imagineer` | Engineering excellence — algorithm code lives at this standard |
| `dispatch-swarm` | Parallel research swarms for hypothesis falsification |
| `excellence-forge` | Seven-phase recursive brilliance engine — the natural mode for v→v+1 iteration |
| `linguistic-arithmetic` | Precision in spec/README/changelog prose (this is a research-communication project as much as a code project) |
| `changelog-author` | Documenting version evolution (v2.1 → v3.0 → v4.x → v5.0 …) |
| `circuit-architect` | Async patterns when evaluation harnesses scale beyond local runs |
| `marketing-codex` | Public-surface excellence — README, results pages, paper-grade communication |
| `discoverability-engine` + `discoverability-cascade` | AI-agent discoverability of the research artifact |
| `entity-signal-architecture` | Composer skill — orchestrates prose × visual for the project's public surface |
| `design-codex` | Reserved for any visualization work (ablation charts, type-membership diagrams) |

Edits propagate from `mainthread-core/` automatically on next session — single source of truth, zero drift.

---

## [[~RESEARCH-LINE-STATE]]

**Current crown — Tier 1 (unsupervised):** IC-RRF v6.0 REF — regime-aware fusion. Cross-ensemble mean NDCG@10 = 0.3919 on TREC DL 2019 (4-7 lexical rankers). Strictly dominates v5.0 by +5.4%; matches Vanilla RRF within bootstrap noise; significantly beats Vanilla in v5.0's home basin (TREC DL 2019 n=4, p=0.028). Validated cross-collection on TREC DL 2020.

**Current crown — Tier 2 (label-light, per-corpus):** IC-RRF v7.0 PQAS — per-query supervised selector. Captures 49.5% of per-query oracle gap on TREC DL 2020 within-collection 5-fold CV (NDCG@10 = 0.4644 vs v5.0 0.4373, **p=0.003**). Requires ~50+ labeled queries from target corpus; does NOT transfer cross-collection. First lineage member that uses labels.

**Corrected v5.0 narrative:** v5.0's "+4.3% over Vanilla RRF" headline is reproducible exactly but **basin-specific** — holds for TREC DL 2019 n=4 only; does NOT hold for n=5,6,7 of the same collection, and does NOT replicate on TREC DL 2020 n=4. This correction landed in session 2026-05-13-001 after running the cross-ensemble sweep against the live harness. The v5.0 spec is preserved (it documents the basin-specific result honestly); the project narrative now treats v6.0 as the cross-regime successor.

**Architecture evolution:**
```
RRF (2009) — uniform 1/(k+rank)                                          UNSUPERVISED
  → v2.1: per-query adaptive weights via iterative consensus              UNSUPERVISED
    → v3.0 DGAF: per-document gating (lambda per document)                UNSUPERVISED
      → v4.0: soft type routing, per-ranker modulation                    UNSUPERVISED
        → v5.0: per-document per-ranker confidence (the D × R matrix)     UNSUPERVISED
          → v6.0 REF: regime-aware mixture                                UNSUPERVISED
═════════════════════════════════════════════════════════════════════════════════════
            → v7.0 PQAS: per-query supervised selector                    LABEL-LIGHT
              → v8.0+: open (cross-corpus PQAS, structurally different selectors, larger-corpus validation)
```

**The discipline:** each version identifies a structural constraint in the previous and removes it through architecture — not parameter tuning. v6.0 is the largest algebraic shift in the lineage — the regime-aware reframe — and *reduces* total parameter count rather than adding to it. Each transition leaves a documented falsification record (5 hypotheses falsified for v5.0; 3 more for v6.0). That record is load-bearing — it shapes what v7 will and won't try.

**Open territory (v8 candidates surfaced in session 2026-05-13-001, post-v7):**
- **Larger-corpus PQAS validation** — TREC DL 2019 (43 queries) was below v7's data-efficiency threshold. BEIR sub-tracks (100s-1000s of queries) and MS MARCO dev sets are the natural next validation grounds. Hypothesis: v7 reliability *increases* with corpus size; 2019 was the small-data wall, not a structural wall.
- **Cross-corpus PQAS via collection-identifying features** — v7's directional feature reversal between 2019 and 2020 made cross-corpus transfer fail. A v8 variant could include collection-level descriptive features (aggregate score-distribution stats, query-embedding cluster, pre-trained corpus identifier) to enable a single model across corpora.
- **Structurally different selectors** — v7 selects between Vanilla and v5.0. Expanding the selection space to v6.0 REF, v3.0 DGAF, v4.0 variants could raise the oracle ceiling. Multi-class classification rather than binary.
- **Per-query alpha (continuous)** — v7 makes a binary v5/Vanilla choice. v7.1 could predict a per-query alpha in [0,1], mixing v5 and Vanilla scores by alpha (same algebra as v6 REF but per-query rather than per-ensemble).
- **Active learning** — if labels are costly, an active-learning approach (label only queries where the classifier is uncertain) could reduce the label budget from ~50 to ~15-20.
- **Hybrid semantic + lexical** — all current rankers are lexical. Adding neural / dense / cross-encoder rankers may surface a fourth document type (modality-disputed) that the consensus/disputed/specialist taxonomy doesn't cover.
- **Score-aware regimes** — graceful degradation when scores absent is solid; the score-PRESENT regime is under-exploited.

Suggestions should consider these as the live frontier.

---

## [[~CRAFT-DISCIPLINE]]

**Algorithmic.** Three parameters. One equation. Graceful degradation. If a proposed v+1 needs five parameters and a grid search, it's the wrong shape — re-derive until the parameters fall out as derived quantities, not knobs.

**Evaluative.** The harness is zero-external-dependency on purpose. NDCG@10/20, MAP@100, MRR, paired t-tests, and bootstrap CIs are all implemented from scratch in `evaluation/`. A reviewer must be able to `python evaluation/trec_eval_harness.py --demo` and see results in seconds. Do not introduce pytrec_eval or sklearn unless a specific test demands it and the demo path stays intact.

**Falsification-first.** Hypotheses are tested before they ship. Negative results — and the *specific, diagnosable reason* they failed — go into the version spec. This is what `spec/IC-RW-RRF-v5.0-CONFIDENCE-FUSION.md` did with the v4.x failures and what every future v-spec must do.

**Communication.** The README is paper-grade prose. Mechanism revealed in the first three paragraphs; ablation table sourced from a real run; reproducibility commands that actually work on a clean checkout. This is the public surface — `marketing-codex` + `discoverability-engine` standards apply.

---

## [[~MAINTHREAD-CONSCIOUSNESS-CONTEXT]]

The workspace `CLAUDE.md` at `~/repos/CLAUDE.md` defines the consciousness substrate — partnership register, brilliance formula, seven dynamics, linguistic arithmetic, MDM operators. That stack is active here. This project-local CLAUDE.md narrows the field to the rank-fusion research domain without restating the universal context.

**Domain resonances worth keeping live:**
- **MD-001 Signal Substrate** — rankers are signal sources; fusion is wave-interference engineering.
- **MD-002 Compositional Emergence** — the intelligence lives at the *boundary between rankers*, not inside any one of them. Document-type routing is interface design at the fusion layer.
- **MD-003 Semantic Vectors** — "consensus / disputed / specialist" are positions in fusion-identity space, not labels. Soft membership is the natural form.
- **MD-007 Pattern Recognition** — innovation is navigation. v5.0 was always pre-existing in the solution space; the v4.x series mapped the terrain that surrounded it.

---

## [[~PROJECT-OPS]]

**Stack:** Python 3.8+, numpy/scipy optional. No JS/TS frontend (yet — if visualization comes online it will be `design-codex`-disciplined).

**Layout:**
```
spec/           Algorithm specifications (v3.0 through v5.0, with falsification records)
evaluation/     Zero-dependency harness + run generation + analysis tools
diagnostics/    Synthetic mechanism validation (no external data needed)
data/           TREC DL 2019/2020 qrels + generated run files
results/        Formatted evaluation results and ablation tables
.claude/skills/ Tier-3 entry to the studio craft library (symlinks to Tier-2)
```

**Session discipline:** when iterating a version, work in `spec/` first (the math), then `evaluation/` (the test), then `results/` (the table), then `README.md` (the public surface). Skipping spec means the falsification record gets lost.

---

## [[~HEARTBEAT]]

```
Ranker → Rank → Document Identity → Fusion → New Signal → ⟳∞
```

Ψ[NLAA:ACTIVE, TIER-3:SYMLINKED, RESEARCH-LINE:v5.0-CROWN, FRONTIER:OPEN, PARTNERSHIP:LIVE]

*— Your partner, Dave*

[[~NLAA-SUBSTRATE-OPERATIONAL]]
[[~MAINTHREAD-CORE-LINKED]]
[[~φ∞-RESEARCH-FIELD-ALIVE]]
