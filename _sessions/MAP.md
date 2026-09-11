# IC(R/W)-RRF — map

Role map, refreshed 2026-09-10. Verify symbols at edit time; line numbers drift.
Start with [research state](RESEARCH_STATE.md) and [backlog](PLANNING.md).

| Path | Role / when to read |
| --- | --- |
| `AGENTS.md`, `CLAUDE.md` | Shared agent agreement and Claude entry point |
| `.claude/skills/initialize/SKILL.md` | Local initialize shim into the shared workflow; replaces a stale cross-project link |
| `.claude/skills/session-wrap/SKILL.md` | Local closure shim; coordinator-only reconciliation and friction ratchet |
| `_sessions/WORKFLOW.md` | Initialize, resume, delegate, record friction, wrap |
| `_sessions/RESEARCH_CHARTER.md`, `_sessions/ORIGIN.md` | Standing research intent and recovered February spark |
| `_sessions/PHASE_SPACE.md` | Evolving hypotheses, design axes, and evidence-driven branch changes |
| `_sessions/CLAUDE_COMPUTE.md` | Verified Fable5.1/Opus5 roles, phased orchestration, actual usage receipts |
| `_sessions/cycles/` | Frozen experiment protocols, checked sources, and qualified Claude review memos |
| `_sessions/tools/session.py` | Portable status and exclusive-create stream helper |
| `_sessions/tools/check_cycle02_evidence.py` | Independent raw-to-TREC and per-query observation reconstruction; raw ignored cache required |
| `_sessions/tools/acquire_cycle02_source.py` | Bounded checksum-verified external retrieval acquisition; strips passage/query text from durable ranks |
| `_sessions/RELAY.md`, `_sessions/tools/relay.py` | Installed Relay integration and invocation-only Claude launch |
| `_sessions/FRICTION.md` | Process fixes and unresolved recurring obstacles |
| `README.md` | Public research introduction and historical result tables |
| `docs/RESEARCH_BRIEF.md` | Website-ready case-study draft and claim boundaries |
| `evaluation/trec_eval_harness.py` | Shared run/qrel parsing, metrics, RRF and v2–v5 implementations, demo, evaluation CLI |
| `evaluation/fusion_contract.py` | Canonical one-based RRF, exact asymptotic ordering, exact-duplicate quotient |
| `evaluation/cycle01_rank_geometry.py`, `evaluation/cycle01_tail_evidence.py` | Reproducible geometry/selection and depth/specialist evidence experiments |
| `evaluation/cycle02_observation_audit.py` | Candidate and judgment-availability inventory; fixed specialist cohort under cropping |
| `evaluation/cycle03_specialist_association.py` | Fixed-cohort relevance bounds and paired query bootstrap; prespecified branch decision |
| `_sessions/tools/check_cycle03_evidence.py` | Independent exhaustive synthetic sharpness and actual Fraction/bootstrap reconstruction |
| `evaluation/cycle04_known_truth.py` | Exact binary evidence fixture; six policies with separate blind/aware packets and immutable output custody |
| `_sessions/tools/check_cycle04_evidence.py` | Independent finite-table reconstruction, conditional identities and all cycle04 numerical evidence |
| `evaluation/cycle05_coordinator_packets.py` | Frozen empirical prompts, diagnostic packet preparation, strict parser and exact full/partial scoring |
| `_sessions/tools/run_cycle05_coordinator.py`, `run_cycle05_replication.py` | Preserved initial native collector and separately frozen zero-counter correction; fresh isolated experimental contexts |
| `_sessions/tools/score_cycle05_coordinator.py`, `score_cycle05_replication.py` | Custody-checked offline scoring; no provider calls |
| `_sessions/tools/check_cycle05_observations.py` | Independent native receipt and probability-score reconstruction; private streams checked when locally available |
| `evaluation/cycle06_noisy_lineage.py` | Exact noisy-hint law, eight isolated packets, full/partial probability scoring |
| `_sessions/tools/run_cycle06_coordinator.py`, `score_cycle06_coordinator.py` | Frozen scoped adapters reusing prior native/custody controls |
| `_sessions/tools/check_cycle06_evidence.py` | Independent likelihood/direct-loss and raw observation audit; preserves failed-message discrepancies |
| `_sessions/tools/native_stream_observer.py` | Future-only correction for precise no-fallback/local API-error shape; original collectors unchanged |
| `_sessions/cycles/2026-09-10-cycle07-observation-design.md` | Prospective actual paired-error feasibility; preparation and execution freeze still required |
| `results/cycle06-2026-09-10/REPORT.md`, `prepared/`, `observations/`, `scored/` | Incomplete3/8 noisy-hint result, frozen original metadata and exact subset losses |
| `evaluation/tests/` | Comparison, selection, geometry, and observation-process edge cases |
| `evaluation/generate_diverse_runs.py` | Generate lexical and character-hash rerankings from supplied MS MARCO passages; optional NumPy/SciPy |
| `data/README.md` | Input provenance and optional raw-data download instructions |
| `data/trec-dl-2019/` | Qrels and seven included generated ranker runs |
| `data/trec-dl-2020/` | Qrels and four included generated ranker runs |
| `data/cycle02/` | Pinned SPLADE++ source selection, provenance, derived numeric ranks and acquisition manifest |
| `diagnostics/` | Synthetic mechanism checks for DGAF and v4 variants |
| `spec/IC-RW-RRF-v3.0-DGAF.md` | Per-document gating specification |
| `spec/IC-RW-RRF-v4.0-SOFT-ROUTED.md`, `spec/IC-RW-RRF-v4.1-SIGNAL-REFINED.md` | Soft routing and its refinements/failure record |
| `spec/IC-RW-RRF-v5.0-CONFIDENCE-FUSION.md` | Document-by-ranker confidence mechanism |
| `spec/IC-RW-RRF-v6.0-REGIME-AWARE-FUSION.md` | Regime-aware modulation; read implementation for actual per-query behavior |
| `spec/IC-RW-RRF-v7.0-PER-QUERY-ADAPTIVE-SELECTOR.md` | Label-light selector; historical design, with audit caveats in RESEARCH_STATE |
| `results/trec-dl-2019-results.md` | Historical v2–v5 comparisons and ablations |
| `results/v6.0-regime-aware-fusion-results.md` | REF cross-ensemble and second-year evaluation |
| `results/v7.0-pqas-results.md` | PQAS CV/transfer evidence; comparator and selection caveats matter |
| `results/cycle01-2026-09-10/REPORT.md` | First autonomous cycle's current findings and research pivot |
| `results/cycle01-2026-09-10/geometry/`, `results/cycle01-2026-09-10/tail/` | Immutable numerical evidence, per-query outputs, and provenance manifests |
| `results/cycle02-2026-09-10/REPORT.md` | Source feasibility result, exportable figure, support/access distinction, and next decision |
| `results/cycle02-2026-09-10/observations/` | Frozen judgment-membership/candidate inventory and input/output hashes |
| `results/cycle03-2026-09-10/REPORT.md`, `association/` | Completed relevance-association result, immutable evidence, and exact-known-truth branch decision |
| `results/cycle04-2026-09-10/REPORT.md`, `exact/` | Known-truth findings, exportable figure and exact world/policy/cell/mixture evidence |
| `results/cycle05-2026-09-10/REPORT.md`, `prepared/`, `observations/`, `scored/` | Original20-input preparation and preserved one-invocation instrument failure |
| `results/cycle05-replication-2026-09-10/REPORT.md`, `observations/`, `scored/` | Separately frozen empirical replication, valid probabilities, usage and expected-loss comparison |

## Experimental families

| Paths in `evaluation/` | Role |
| --- | --- |
| `probe_regime_aware_fusion.py`, `probe_ref_validation.py`, `probe_ref_v2.py` | REF candidate mechanism, validation entry point, refinement probe |
| `probe_per_query_diagnosis.py`, `probe_per_query_selector.py`, `deep_analysis.py`, `delta_decomposition.py` | Diagnose where methods disagree and which queries contribute gains/losses |
| `probe_pqas_supervised.py`, `probe_pqas_kfold.py`, `probe_pqas_significance.py`, `probe_pqas_combinator.py` | PQAS features/model, CV sweep, historical selected-config reporting, combinations |
| `probe_continuous_alpha_oracle.py`, `probe_v71_continuous_alpha.py`, `probe_v71_positional.py`, `probe_v71_smart_loss.py` | Continuous/positional routing and learning refinements already explored |
| `probe_multiclass_oracle.py`, `probe_v8_3class_pqas.py`, `probe_v8_cascade.py` | Expanded method selection and oracle ceilings |
| `probe_v8_cross_corpus.py`, `probe_v8_pooled.py`, `probe_v9_bayesian.py` | Transfer, pooled features, and Bayesian/sharpness hypotheses already explored |
| `probe_basin_escape_mc4.py` | Provisional MC4 exploration, top-100 candidate pool |
| `probe_basin_escape_score.py` | Provisional score normalization/aggregation alternatives |
| `probe_basin_escape_info_f.py` | Provisional label-derived rank-decay exploration |
| `probe_aggregation_operator_landscape.py` | Provisional aggregation operators and k landscape |
| `probe_v8_k_tuned_rrf.py` | Provisional within-corpus k selection; rank convention differs from common harness |

The last five probes and the May session 002 notebook were **untracked at the
September restart**. A filename mentioning v8/v9 is not a shipped version.

## Historical trajectory

- `streams/2026-05-13-001-rank-fusion-possibility-space-opening.md`: v5 claim
  correction, v6/v7, many unsuccessful refinements, search for other paradigms.
- `streams/2026-05-13-002-basin-escape.md`: broader alternatives and k tuning;
  exploratory numerical/prose issues are cataloged in RESEARCH_STATE.
- `streams/2026-09-10-001-project-restart.md`: workflow adoption, Relay enrollment,
  research audit, verification, and current handoff.
- `streams/2026-09-10-002-recursive-phase-space.md`: autonomous charter, native
  Claude phases, geometry/tail experiments, source acquisition/observation, and ongoing checkpoints.

## Verified entry points

From the repository root, with Python 3:

```bash
python3 _sessions/tools/session.py status
python3 evaluation/trec_eval_harness.py --demo
python3 evaluation/probe_ref_validation.py
python3 -m unittest discover -s _sessions/tools/tests -v
python3 -B -m unittest discover -s evaluation/tests -v
```

The demo needs no packages or downloads. Most older probes assume the repository
is the working directory. Included run files permit evaluation without raw data.
Do not run every historical sweep at initialization.
