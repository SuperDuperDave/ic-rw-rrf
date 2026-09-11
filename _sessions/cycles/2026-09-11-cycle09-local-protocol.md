# Cycle09 local preparation contract

Written before the actual parameter and identifier draws. The
[committed design](2026-09-10-cycle09-certificate-design.md) at `d739a94`
fixes the single program, two RNG sequences, three certificates, two packets,
schema, bounds and stopping rule. This supplement changes no candidate choice.

## Hypothesis, comparator and observation

An invalid transition can preserve a correct final Boolean, so endpoint
agreement need not establish valid support. V is the fully valid reference;
I increments the row3 value of a and then propagates the altered state;
F changes only the final Boolean. The local prediction is first-invalid rows
null,3,6 respectively, with I sharing V's answer and F opposing it.

The primary checks are exact full-state validity, first-invalid row, final-answer
agreement, copy identity, deterministic construction and the declared information
boundary. Always-valid and always-invalid policies give explicit reference
validity decisions; repeated judgments on the same three originals are not
six independent cases. No model response or calibrated reliability is inferred.

Malformed certificates, including Boolean values in integer fields or missing
unchanged variables, are construction/schema failures. Do not label them as
well-formed mathematically invalid certificates. For a well-formed certificate,
compute each expected next full state from the preceding submitted state and
the actual program assignment. Record every local invalid row and its first
member; do not compare later rows only against the uncorrupted reference trace.

## Freeze and execution

Implement the exact allowlisted Python execution and a separate AST transition
checker. Use synthetic cases before the actual draw. Review all new files,
including untracked ones, for whitespace and unintended changes before freezing
their hashes. Do not edit cycle08's frozen test to remove its historical EOF blank.

Prepare once into a new exclusive output directory after sources/tests are stable.
Pin generator/checker/test/design/protocol hashes, Python executable/version,
exact command, measured local wall time and output identities. The independent
checker reconstructs both RNG sequences, all source/packet bytes and truths.
Stop on any construction/checker/custody disagreement, preserving an explicit
failure; no new seed, replacement candidate or outcome-guided repair search.

Produce readable trace tables and any review capsule directly from the verified
artifacts. Neither V/I/F labels, reference validity, corruption locations nor
checker output may enter a future solver payload. root_id records copying;
F-only replication remains an intended but non-diagnostic cue for a heuristic
that rejects repeated roots. Repeat versus empty slots also changes text volume.

## Interpretation checkpoint

Stop the local preparation at its verified fixture and decision. A compact Claude
review may assess whether a separately frozen two-call single-verifier pilot
would add information. One fresh Fable5.1/high review, tools/MCP/agents disabled,
has a $1 native allowance,180-second process bound and3,000 output tokens per
API response. Review content and accounting are separate from solver observations;
raw provider thoughts and Relay runtime remain ignored.

Any empirical phase needs its own explicit protocol, effective native controls,
prompt/response contract, sealed payloads and stopping rule after the local
checkpoint. Passing this construction does not itself launch that phase.
The standing research authorization persists; this is a scientific decision,
not a recurring request for user permission.
