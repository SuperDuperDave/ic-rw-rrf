# Cycle05 separate replication after an instrument failure

Frozen before this replication's provider calls. The original batch is closed:
one native invocation, zero accepted predictions, nineteen unscheduled packets.
Its frozen parser treated any nonempty `subagent_stats` object as activity. The
actual object contained only zero counts. Native status was success, tools/MCP
were empty, and the receipt reports one message, end_turn and no actual agents.
The batch obeyed its stop rule. Original code, tests, receipts and incomplete
scores remain unchanged; no old answer is carried into this replication.

This new batch repairs the measurement instrument. It does not change prompts,
model, effort, packet selection, order, exact references, scoring, provider
controls or interpretation. All twenty original unique payloads are submitted
in fresh contexts, including the first packet whose earlier outcome now exists.
This is a declared replication, not an untouched first exposure, a continuation
of the stopped batch, or a replacement hidden in its results. One response per
unique input still does not measure stochastic variability. Report costs of
both batches separately and together; do not pool their predictions.

## Exact correction and gates

The versioned adapter reuses the preserved collector. It recognizes only the
exact observed subagent-statistics schema with every numeric leaf an integer0,
and `by_type={}`. Booleans, strings, missing/unknown fields, positive/negative
counts, nonempty type counts or alternate schema do not establish zero activity
and stop collection. Actual tool calls, parent tool IDs, hooks, alternate models,
native errors and all existing gates remain failures. The adapter retains the
observed zero-count object in public metadata and the unchanged original stream
hash. No response text is edited, selected, stitched or salvaged.

The original execution protocol plus its preflight clarification remain the
scientific/resource contract: at most20 native invocations, one in flight,
120s per call,900s per batch,500 output tokens per API response including
reasoning,$4 native-accounting scheduling allowance, no coordinator retries or
fallback, unknown-cost/native-error whole-batch stop. Native continuation may
occur and remains observable workflow behavior. This separately authorized
research batch receives the same allowance; it does not increase the terminated
batch's cap or imply a hard billing bound.

Prepared manifest SHA256
`929fa72b040c97f9ce7908244cab9428eae6a9eb3d656f7dec624e929be2a2b0` supplies
the unchanged exact prompt, twenty payloads, seed42 order and references. Original
preparation lives in `results/cycle05-2026-09-10/prepared`; new observation and
score artifacts use `results/cycle05-replication-2026-09-10/` exclusively.
Versioned runner/test/scorer/protocol and original source identities are frozen
in the replication start manifest before its first call. Native authentication
and provider routing stay unchanged. Only synthetic request context is sent.

Full primary still requires twenty valid predictions. Otherwise preserve an
incomplete prefix with descriptive denominators. An independent raw-stream and
arithmetic review follows collection. Stop after this replication, scoring and
review; further schema failures or resource limits do not authorize another
automatic repair run under this contract. A later scientific change needs a
separate design, informed by what these results actually distinguish.
