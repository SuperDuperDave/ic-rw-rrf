# Cycle19 — prospective metadata gate for an exact-pipeline transfer

Written before later-round archive metadata is opened. This is a bounded
feasibility experiment, not a ranking-effectiveness run. Cycle18's final Opus
review supplies the opening proposal; Buddy will challenge it while Codex
performs this inventory. All prior cycle18 outcomes are already known.

## Question and distinguishing prediction

Can the frozen cycle18 family hybrid be evaluated on previously unused query
units without silently changing its component pipelines? Prediction: at least
one later TREC-COVID round has a uniquely documented automatic run for every
one of the four required roles and an identifiable newly introduced cohort.
Failure closes this exact-pipeline transfer route, not all transfer research.

Inspect rounds2–5 in chronological order, completing all four metadata checks
even if an earlier round is feasible. Use authoritative NIST archive metadata,
track/round documentation and team papers only. No ranking run, qrels, document
inventory or full-corpus body is downloaded or parsed; no scores, grades, source
effectiveness tables or favorable query outcomes may choose a mapping. Reading
an incidental aggregate in a source must be disclosed and cannot change rules.

## Role mapping fixed before metadata

Each round is eligible only if all these roles map uniquely to documented
automatic runs from the original teams, with enough method detail to establish
the indicated pipeline rather than only a similar name:

- A: BITEM's Elasticsearch lexical baseline, corresponding to Round1 BITEM_BL.
- D: BITEM's same baseline with query-term document-frequency boosting,
  corresponding to Round1 BITEM_df.
- T: BITEM's baseline with stemming, corresponding to Round1 BITEM_stem.
- S: BioinfoUA's BM25 candidate retrieval plus biomedical neural reranking,
  corresponding to Round1 BioinfoUA-emb.

Changed run labels alone are allowed if the published method identifies the
same role. Additional retrieval/model changes or feedback/manual use make an
exact role incompatible unless the documentation explicitly isolates the same
automatic pipeline for new topics. Multiple plausible matches, absent method
detail, absent teams or missing roles fail the round. Record all same-team run
metadata before deciding, including type and pooling/priority status when stated.
No other team, "closest" substitute or result-driven role selection is allowed.
This strict contract deliberately tests exact pipeline feasibility; a future
mechanism-level transfer would be a separate question.

## Cohort and observation contract to verify

Only topics introduced in that round are candidates; topic IDs31–35,36–40,
41–45,46–50 are the reviewer-proposed ranges, not yet verified facts. Verify
those ranges, query counts, document snapshot dates and handling of previously
judged documents from primary documentation. Distinguish new queries from new
corpora and from labels revealed on reused topics. Exclude original topics1–30.
Record judgment/document-identity URLs or release identifiers from metadata,
without fetching their bodies. Document which exact-round qrels would judge
the new topics. No source coverage assertion is possible before a future gate.

## Outcome and stop

Record a four-round table: metadata source identity, original-team run names/
types/methods, unique role decisions, new-topic/evaluation semantics, and outcome
eligible/incompatible/unresolved with reasons. Primary feasibility indicator is
whether any round passes every metadata condition. Stop after this one bounded
inventory and independent source/logic review. Access errors yield unresolved
access, not absence. At most one official-page retry or directly linked official
archive alternate per missing round; no source crawl to rescue the mapping.

If no round is eligible, park this route before data acquisition. If at least
one passes, prepare a separate frozen data contract over ALL eligible rounds'
new topics, with source/query coverage checks before metrics. No automatic
download follows this metadata result alone.

For that possible next contract, preserve F=(a+d+t)/3+s, H=a+s, depth100, k60,
score-descending/id-ascending canonical ties, binaryP@10 exact missing-label
bounds. F−S is the new primary replication of cycle18's identified secondary;
F−H and H−S are fixed secondary, all standalone references retained. An
identified positive lower supports the fixed-panel direction; upper<=0 excludes
positive gain; otherwise unresolved. No weight, source or topic sweep, no claim
of unseen collection transfer from new topics alone. No human/proxy grading.

## Custody

Freeze this protocol's SHA256 before browse. Keep concise source-backed public
observations and exact URLs, retrieval time and identity/hash when captured.
Raw HTTP/runtime material remains ignored. An independent worker may inspect
the same permitted metadata to verify omissions and mappings, without mutating
this protocol or fetching forbidden bodies. Any substantive departure requires
a separate dated design; do not revise this frozen contract after observations.
