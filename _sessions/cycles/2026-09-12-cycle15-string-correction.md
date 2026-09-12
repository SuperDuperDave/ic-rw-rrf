# Cycle15 — pre-outcome Arrow string correction

The original input validation stopped at the corpus Parquet schema check:
`corpus: unsupported Parquet schema (expected three string fields)`.
Preserve the original driver, tests, source preflight and
[failure receipt](../../results/cycle15-2026-09-12/validation/failure.json).
All five input identities and the isolated decoder had passed verification.
No corpus rows, query rows, qrels or cache records were read by that attempt;
no lexical scoring, fusion or collection effectiveness was computed.

A subsequent metadata-only inspection found the expected three columns
`_id`, `title`, `text` in both files, with Arrow `large_string` types. Footer
row counts were 5,183 corpus rows and 1,109 query rows. The pinned publisher API
had described these columns as strings. Arrow's Utf8 and Large Utf8 layouts use
32-bit and 64-bit offsets, respectively; both carry string values. This is a
decoder type restriction, not evidence of changed text or a different dataset.
[Arrow format specification](https://arrow.apache.org/docs/format/Columnar.html),
[PyArrow large_string reference](https://arrow.apache.org/docs/python/generated/pyarrow.large_string.html).

Before any collection outcomes, add a separate adapter accepting `string` or
`large_string` for these three columns. It must decode values directly without
casting, normalizing text, repairing IDs, dropping rows or relaxing null,
duplicate, field-name or value checks. All original input identity checks,
cohort construction, rankers, tie rules, metrics, five arms, diagnostics and
600-second scoring limit remain in the original implementation.

Use synthetic Unicode fixtures of both offset widths and malformed type/value
fixtures to verify the correction. An independent reviewer checks that the
adapter delegates all research operations unchanged. Freeze this document,
the adapter and its tests in a new correction preflight referencing every
original source identity and the original failed attempt. Require that new
preflight for corrected validation and execution, with exact commands and fresh
output directories recorded before either starts.

Reuse the passed 11-query authoritative synthetic metric gate; its implementation
and formula did not change. This correction authorizes one new validation
attempt and, only if it passes, one fixed comparison. Any further failure is
preserved and stops that attempt. No automatic type fallback, data substitution
or outcome-driven revision is authorized by this correction.
