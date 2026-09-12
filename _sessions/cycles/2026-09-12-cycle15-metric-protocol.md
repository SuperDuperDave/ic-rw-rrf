# Cycle15 — binary synthetic metric gate

Frozen before invoking the authoritative evaluator. This is an implementation
cross-check, with no SciFact scores, retrieval calls or labels acquired here.
The [cycle14 transfer contract](2026-09-11-cycle14-transfer-protocol.md) remains
the owner of the five-arm comparison and retained real-query cohort.

Hypothesis: the existing `ndcg_at_k` agrees with independently written binary
hand expectations and pinned NIST `trec_eval` on every fixture and on the equal
query mean. Distinguishing prediction: all values meet the tolerances below,
with all eleven qrel queries in the aggregate. The baseline is
`d(r)=1/log2(r+1)` and hand-specified relevant positions/positive counts.
Stop on any build identity, process, output-key, or numeric mismatch; one
authoritative invocation, with no automatic repair or repeat. No RNG is used.

Evaluator revision: `ba38899cbd4de0fb699b47f39b64ef1c107e4a5c`. Root acquires the
pinned source archive and builds once using `make -C <source_directory>` in
ignored local storage. The gate requires the build receipt, checks the pinned
`m_ndcg_cut.c` and local harness hashes from the cycle14 source receipt, and
checks the recorded binary hash against the executable. Receipt linkage records
the build provenance; a matching metric-source file alone does not establish
the origin of an arbitrary executable.

Exact command template:

```text
python3 _sessions/tools/check_cycle15_metric.py --trec-eval <source_directory>/trec_eval --build-receipt _sessions/evidence/2026-09-12-cycle15-evaluator-build.json --output <fresh_output_directory>
<absolute_trec_eval> -q -c -m ndcg_cut.10 <absolute_output>/fixtures.qrels <absolute_output>/fixtures.run
```

The concrete argument vector, input hashes, code/binary identities, hand
expectations, timeout (30 seconds), and `LC_ALL=C` are written to
`metric-protocol.json` before subprocess invocation. Tolerances are absolute
`0.0000500001` against the default four-decimal official output and `1e-12`
for unrounded local versus hand values; relative tolerance is zero. The mean
uses the unrounded hand/local values divided by eleven, not rounded official
per-query values. Empty-query output and the aggregate must both be present.

Fixtures cover positives at ranks1/2/10/11; multiple positives including an
unretrieved positive; twelve positive qrels with IDCG capped at10; unjudged
versus explicit-zero rank positions; short missed and empty rankings; tied
original scores whose chosen a-before-z order is preserved by score=`-rank`;
and identical query/document string `00101` without removing its leading zeros
or document. Every fixture query has a positive qrel. The empty ranking emits
no run rows; `-c` must return its zero and retain it in the denominator.

The pinned [official README](https://github.com/usnistgov/trec_eval/blob/ba38899cbd4de0fb699b47f39b64ef1c107e4a5c/README)
specifies `make` and complete-query evaluation. Its
[main procedure](https://github.com/usnistgov/trec_eval/blob/ba38899cbd4de0fb699b47f39b64ef1c107e4a5c/trec_eval.c)
implements `-c` missing-query evaluation and per-query printing. Strict parsing
requires exactly `ndcg_cut_10`, every fixed query key once, one `all` key and
finite values in [0,1]. Exit failure or stderr also fails the gate. Failure
evidence is retained, and an existing output directory is never overwritten.

Friction disposition: **PROMOTE** exact output-key and complete-denominator
checks into this metric gate. Tests with simulated subprocess output verify
failure handling; they do not constitute the authoritative fixture result.
