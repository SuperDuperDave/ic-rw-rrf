# Cycle15 — critique the measured SciFact transfer

Dave authorizes ongoing Codex/Claude research and explicitly stated on 2026-09-11:
"I approve sharing anything and everything with Claude." This self-contained
packet shares unpublished research findings with the existing signed-in Claude
service through this project's Relay. No public-availability prerequisite.

You are the bounded methodological reviewer. Tools, MCP, scouts and workflows
are disabled. Use only this packet; do not claim file/data inspection or edit
anything. One Fable5.1/high invocation, $1.50 native list-accounting cap, wall180s,
4000 configured output tokens per API response, max-turns1. Separate Codex workers
implemented and reviewed the contract; a numerical reconstruction is now running.
Reserve this stronger model's reasoning for interpretation and next-question value;
no redundant fan-out or additional provider wave is requested.

Return a public research memo around550 words. Quote the cycle15 receipt marker
supplied only in Relay context. With tools disabled, ask Codex to record consumption
of the exact request after reading the complete memo. Distinguish measured facts,
possible mechanisms and proposals. Correct consequential overclaims.

## Context and frozen contract

Curiosity-led research asks when useful minority evidence differs from repetitive
agreement. Negative results and better questions count. Prior arithmetic verifier
laboratory stopped all-correct; it stays parked. Earlier DL2019/2020 query panels
were heavily reused. Cycle13 found positive annual B-A sharp missing-grade bounds
for top10 RBP(p=.8,gain grade/3); nine queries reversed. Those were not nDCG or
source-alone superiority results.

SciFact was selected in cycle14 BEFORE source/performance inspection. Its five
systems were fixed then. P=cached BM25 top1000; S=cached SPLADE++ EnsembleDistil
top1000. Four unchanged local lexical functions rerank P, capped200 each:
BM25(1.2,.75), BM25(.9,.4), unigram logTF/IDF divided sqrt(token length),
QLDirichlet(mu2000). Statistics pool unique P-candidate docs across fixed cohort.
A=canonical one-based equal-weight k60 RRF of four lexical lists. B=A's four lists
plus S. H=canonical k60 RRF of P and S. Lexical ties keep P order, full scores
precede truncation. Fusion uses fsum then string-ID ties. No source weights tuned.

Primary positive-direction prediction: equal-query mean binary nDCG@10 B-A >0.
Fixed contextual B-S/B-P/A-P/B-H contrasts and all five means/signs reported.
Complete qrels IDCG, missing qrels zero at original positions. Secondary RBP
binary p=.8 top10 unnormalized; not sharp bounds. No p-values, confidence intervals, query routers or search.
Mechanism-level adaptation, not exact-pair replication: old first-stage generator
was unpinned. Different collection/document unit/labels/first stage. No established
source error independence, causal correlation correction, novelty, population
inference, or guarantee of benchmark exclusion from upstream training.

## Execution and observed inputs

Single acquisition verified all five pinned raw inputs (1,000,472,770 bytes) in
34.057 seconds, no retry, inference, new labels or global package installation. Pinned isolated
Arrow decoder plus official NIST trec_eval build. All 11 synthetic metric fixtures
passed BEFORE effectiveness, including empty queries/full IDCG/rank-proxy export.
First validation stopped at corpus schema metadata: Arrow large_string instead
of string. Separately frozen width-only adapter accepts both UTF-8 offset widths
with exact original row checks, no casting/normalizing/cohort/scorer/metric change.
Original code, tests, preflight and failure are preserved. Corrected gate passed
all 300 official queries, no zero-IDCG exclusions; all qrels grade 1; both cache bodies
match pinned text/IDs. P depths 66..1000, S all 1000. P union=all 5,183 corpus documents,
which means pooled statistics equal full-corpus statistics here, NOT that each P pool is full-corpus.
One completed run scored in 116.09925839101197 seconds under the 600-second cap.
All rankings saved before metrics. No post-outcome repair or second comparison.

A receipt-edit race after freeze changed only five whitespace bytes in the ancillary
review memo JSON; exact hash-bound bytes restored and both versions/custody note retained.
All 21 code/protocol/failure identities stayed unchanged. No result rerun.

The full raw/numeric independent reconstruction and official per-arm check are
IN PROGRESS; do not call them passed based on this packet. Existing 381 tests plus
10 width-correction tests passed; auditor's 11 synthetic tests passed separately.

## Artifact-derived numerical result

Summary SHA256: 595ac582afb1a8ad1e8f5e5205bc4cce539e2535e6f7c7694b85710b834e0459
Manifest SHA256: 0d2ac1cd0c64e88c5cace0b7f5a5dd3782b2cf2b6f3ae52ce895554e87d9c3cd

```json
{
  "B_top10_outside_P_totals": {
    "count": 0,
    "returned_top10": 3000
  },
  "P_candidate_union_over_corpus": 1.0,
  "contrast_rbp10_B-A": {
    "maximum": 0.10757119999999996,
    "mean_delta": 0.004325984597333333,
    "minimum": -0.17315645439999994,
    "n_queries": 300,
    "negative": 12,
    "positive": 47,
    "zero": 241
  },
  "contrasts_ndcg10": {
    "A-P": {
      "maximum": 1.0,
      "mean_delta": -0.011606622073662039,
      "minimum": -1.0,
      "n_queries": 300,
      "negative": 43,
      "positive": 37,
      "zero": 220
    },
    "B-A": {
      "maximum": 0.5693234419266069,
      "mean_delta": 0.01934785827329663,
      "minimum": -0.7109351736821121,
      "n_queries": 300,
      "negative": 12,
      "positive": 47,
      "zero": 241
    },
    "B-H": {
      "maximum": 0.5,
      "mean_delta": -0.018740808004350185,
      "minimum": -1.0,
      "n_queries": 300,
      "negative": 47,
      "positive": 35,
      "zero": 218
    },
    "B-P": {
      "maximum": 1.0,
      "mean_delta": 0.007741236199634591,
      "minimum": -1.0,
      "n_queries": 300,
      "negative": 30,
      "positive": 54,
      "zero": 216
    },
    "B-S": {
      "maximum": 0.6666666666666667,
      "mean_delta": -0.016983978807087526,
      "minimum": -1.0,
      "n_queries": 300,
      "negative": 50,
      "positive": 52,
      "zero": 198
    }
  },
  "inference": "fixed finite panel; no p-values, confidence intervals, or population-significance claim",
  "judgedness_totals": {
    "A": {
      "count": 2740,
      "returned_top10": 3000
    },
    "B": {
      "count": 2728,
      "returned_top10": 3000
    },
    "H": {
      "count": 2722,
      "returned_top10": 3000
    },
    "P": {
      "count": 2735,
      "returned_top10": 3000
    },
    "S": {
      "count": 2720,
      "returned_top10": 3000
    }
  },
  "means_ndcg10": {
    "A": 0.6673028053771691,
    "B": 0.6866506636504658,
    "H": 0.7053914716548159,
    "P": 0.6789094274508312,
    "S": 0.7036346424575532
  },
  "means_rbp10_p_4_5": {
    "A": 0.14539629943466664,
    "B": 0.14972228403199997
  },
  "metric": "binary nDCG@10; absent qrels zero; complete qrels IDCG",
  "n_queries": 300,
  "primary": "B-A"
}
```

## Provisional interpretation to challenge

The source-addition prediction holds on this finite panel, but B trails S and H.
A also trails P. Thus extra lexical apparatus has no demonstrated mean benefit
against these strong fixed references here. Slightly more positive B-S query
signs still coexist with negative B-S mean; metric ties are not ranking identity.
All 3,000 B top10 documents were already in that query's P pool. This narrows the access
observation but doesn't isolate a cause: S may supply documents absent from the
four retained lexical top200 lists, or different ranks over available documents.
Neither high missing-qrel fraction nor benchmarkzero establishes true irrelevance.

What is the strongest warranted conclusion, and which tempting mechanism claims
should we reject? What ONE next research question would best reconfigure the
project toward new information rather than retuning an already observed panel?
Consider family vote balance versus local reranker quality/depth as competing
explanations, with a matched structural intervention and strong simple references.
Do not treat four different lexical functions as exact copies, assume family labels
prove dependence, or claim rank agreement identifies reliability. Any current-panel
mechanism probe would be explicitly post hoc, not another untouched transfer.
Recommend a bounded prospective design or argue to park this branch; no additional
experiment happens in this cycle. Prior art must be checked before novelty claims.
