# Cycle15 — execute the frozen SciFact transfer

Starting checkpoint `9dd01eaad023b7223863271a775df76c7ef71804`.
Continue the [cycle14 protocol](2026-09-11-cycle14-transfer-protocol.md) and
[input plan](../evidence/2026-09-11-cycle14-input-plan.json) without changing
collection, sources, scoring functions, five arms, primary/secondary outcomes,
diagnostics or stopping rules. R18 owns this execution; the preparation's stop
does not prohibit the separately authorized execution turn.

## Before actual inputs

Synthetic contract tests and independent source review precede acquisition. Pin
new source/test hashes and exact commands in a preflight receipt. The acquisition
adapter requests the five original files once each, verifies size and SHA256 or
Git-blob SHA1 as specified, and preserves partial/failure records on any error.
The aggregate raw cap is1.05GB; decoder and evaluator archive have separate60MB
and10MB caps. Overall download wall cap1200seconds, no automatic retry/fallback.

Download the specified PyArrow wheel only to ignored local storage and unpack
it there after its exact byte identity is verified; no global package change.
Download official evaluator source from
`https://codeload.github.com/usnistgov/trec_eval/tar.gz/ba38899cbd4de0fb699b47f39b64ef1c107e4a5c`.
Verify safe archive paths and the pinned `m_ndcg_cut.c` SHA256 before running
`make -C <ignored extracted directory>`. Record source archive, executable,
command and revision in a build receipt. No system installation.

The metric fixture contract uses `<trec_eval> -q -c -m ndcg_cut.10` so absent
result queries remain in the official denominator. Freeze fixtures and tolerances
before that invocation:5.00001e-5 for four-decimal official output and1e-12 for
local versus independent formula. Preserve exact per-query and aggregate output.
No SciFact effectiveness may precede that gate.

## Validation and one run

The strict adapter verifies all five file identities before parsing, then checks
the complete binary qrels, corpus/query text, both full cache query sets, IDs,
source scores/order/depth and text consistency. It records positive-IDCG cohort
and exclusions without ranker-success screening. Build pooled lexical statistics
only for the frozen cohort. No outcome is used to select the inputs or methods.

After the input and metric gates pass, execute the frozen five-arm comparison
once with a600second scoring cap and immutable output directory. Independent
reconstruction and a bounded Claude interpretation review follow the evidence.
No extra source, weight/depth search, diagnostic-triggered arm or router is added.

A failed gate stops the attempted run. Record exactly which data and metrics
were read/computed. An explicit pre-outcome correction may be separately proposed
and verified if it preserves the intended comparison; a post-outcome correction
must be labeled accordingly. Never erase or overwrite the original attempt.
