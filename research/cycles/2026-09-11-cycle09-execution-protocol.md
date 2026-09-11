# Cycle09 — two-call verifier feasibility protocol

Frozen before empirical responses, after the separate local checkpoint and
[execution decision](../evidence/2026-09-11-cycle09-execution-decision.json).
The original [construction design](2026-09-10-cycle09-certificate-design.md),
[local supplement](2026-09-11-cycle09-local-protocol.md) and prepared bytes stay
unchanged. This protocol finalizes the [candidate](2026-09-11-cycle09-empirical-candidate.md).

**Question and prediction.** Can this native Opus5 workflow return a complete
validity map agreeing with exact verification for the three original certificates
in each of two packets? The expected map is V=true, I=false, F=false. A returned
wrong judgment falsifies success on that case. A collection/format failure leaves
the full primary unavailable, with a separately recorded stop cause.

**Inputs and comparator.** The single seeded draw gives A=B=R=0 and order V,I,F.
The I trace breaks row3 while retaining the correct final answer; F breaks row6.
The repeat packet adds two exact F-certificate copies, with stable root identity.
Only original IDs are judged. Always-valid scores1/3, always-invalid and
final-answer-only score2/3, first-original-only and exact checking score3/3 on
each packet. These facts precede responses and constrain even a perfect result.

**Invocation.** Exactly base then repeat in two fresh, isolated native contexts.
The exact common SYSTEM_PROMPT in `evaluation/cycle09_verifier.py` is the custom
system prompt; the unchanged canonical packet is the entire user input. This
finalizes prompt placement before outcomes; the candidate had described a common
instruction prefix. The execution manifest seals all three byte artifacts,
source/test hashes, this protocol and the decision before collection.

Use pinned Claude2.1.267, SHA256
`0399c793ff571d5946ef923d80b4f330d05ac4b6842a6b0775468f5d389403c0`,
model `claude-opus-5`, high effort. Reuse the verified native command/environment
contract: no tools, hooks, MCP, agents, project memory, browser, persistence,
slash commands, workflow dispatch, fast mode or alternate-model fallback.
Fresh UUID and empty working directory per invocation; check inherited overrides.
No reviewer context or labels enter solver inputs.

**Bounds and stops.** At most2 native invocations, $1 remaining native scheduling
allowance, 120seconds per invocation, 300seconds per batch, 500 output tokens per
API response including thinking, max-turns1. Native continuations may exceed500
tokens per invocation; wire attempts are incompletely observable. Check native
cost/model/activity/session/terminal evidence, preserve all receipts, and stop
after the first native, format, custody or resource failure. No retry, repair,
fallback, reserve, new candidate, model change or prompt search. A wrong but
well-formed map is measured and does not stop the second planned invocation.

**Parsing and primary.** Only the unique terminal result is parsed. Require one
JSON object with exactly the three original IDs and strict Boolean values;
reject duplicate/extra/missing keys, prose, numeric substitutes and partial maps.
Full primary requires both accepted maps: all6 decisions, correct/accepted/planned
counts and each original's base→repeat transition. On failure retain all6 planned
rows with invalid/unsent status, separate observed counts and null full primary.
Never impute an invalid or unsent response as a mathematical error. Metadata's
valid_predictions counts accepted maps (maximum2), not individual decisions.

**Interpretation and stop checkpoint.** This is one program with three traces
judged twice, not six independent tasks. No confidence interval, population,
internal-strategy, pure-copy causation or multiagent-benefit claim. All-zero
states make I conspicuous and a first-position policy is perfect. Success only
shows correct returned judgments on these particular inputs; failure can expose
a workflow limitation. F-only copying,586 extra bytes, fixed order and stochastic
responses prevent causal attribution. Stop after scoring and independent raw
audit; a future design must be prospective and separately justified.

**Reproduction.** Run preparation with the local manifest SHA256
`0cdb62969bb8a0d365d2b5bd7a225773d938c4a9f66cdc62971d123f62a6d250`:

```bash
python3 _sessions/tools/run_cycle09_verifier.py prepare --prepared-manifest-sha256 0cdb62969bb8a0d365d2b5bd7a225773d938c4a9f66cdc62971d123f62a6d250
python3 _sessions/tools/run_cycle09_verifier.py collect --execution-manifest-sha256 <returned-sha256>
python3 _sessions/tools/score_cycle09_verifier.py --score
```

Preparation/collection/scoring refuse existing output directories. Reproduction
must use a separate checkout/output root; never overwrite frozen observations.
Raw provider streams remain ignored; only decisions and selected usage/control
metadata are public. Native cost is list accounting, not subscription billing.
The official [Opus5 overview](https://platform.claude.com/docs/en/models/opus-5/overview)
and [Fable5.1 overview](https://platform.claude.com/docs/en/models/fable-5-1/overview)
were checked2026-09-11; review uses the stronger tier, these fixed judgments Opus.
