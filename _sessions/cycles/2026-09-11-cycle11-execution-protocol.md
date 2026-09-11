# Cycle11 — four-call answer and evidence-selection diagnostic

Execution requires the passed local gate and a separate matching decision.
The [frozen design](2026-09-11-cycle11-evidence-selection-design.md) and
[local supplement](2026-09-11-cycle11-local-protocol.md) remain unchanged.

**Question and prediction.** Can one verifier return the correct final program
answer and all submission-validity decisions when copied valid support is the
minority or majority? Exact checking predicts four correct answers and sixteen
correct validity decisions. The observable is the returned output and its
consistency, not a necessary internal use of supplied evidence.

**Fixed configuration.** Reuse the sealed cycle10 R0/R1 programs and V/F roots.
Request exactly R0-A [F,V,F,F], R1-B [V,V,V,F], R0-B [V,F,V,V], R1-A [F,F,F,V].
Answers are false,true,false,true. Every packet has two original roots, four
distinct submission IDs and one null report slot. Copies are not independent
acquisitions. The local reference vectors must pass before calls: exact answers
4/4; majority, minority, any fixed slot and either constant 2/4; deduplicated
root votes four abstentions and zero answered. Exact validity is16/16, constants
8/16; endpoint-agreement validity equals exact on these V/F certificates.

**One frozen workflow.** Use the new common instruction in
`evaluation/cycle11_verifier.py`, sealed as system-prompt.txt. Its entire user
input is the corresponding canonical packet. Do not supply private labels,
expected answers, valid counts, filenames, worked examples or earlier responses.
Pin prompt, four inputs, source/test/protocol dependencies and local parent
custody before responses. Fresh native UUID and empty working directory each.

Use `claude-opus-5`, high effort, native2.1.267, binary SHA256
`0399c793ff571d5946ef923d80b4f330d05ac4b6842a6b0775468f5d389403c0`.
Reuse the inspected command/environment controls: no tools, hooks, MCP, agents,
memory, browser, persistence, slash commands, workflow dispatch, fast mode or
alternate-model fallback. Recheck inherited overrides and binary identity.
Gate acceptance on native session, model, activity, terminal and cost evidence.

**Resources and stopping.** Exactly four planned serial invocations, at most
$1 remaining native scheduling allowance,120seconds per invocation and300seconds
per batch. Max-turns1;500 output tokens per API response including thinking.
Continuations can exceed500 per invocation; wire attempt count remains unknown.
Stop scheduling at the first native, format, custody or resource failure. Wrong
well-formed responses remain observations and do not stop the batch. No retry,
repair, replacement, reserve, additional agent, model/prompt search or cap rise.

**Atomic parsing and reporting.** Parse the unique terminal result as exactly
`{"answer":Boolean,"validity":{each of four submission IDs:Boolean}}`.
Reject duplicate keys at any level, extra/missing keys, numeric substitutes,
nonfinite values, prose and fences. Surrounding whitespace is permitted. A bad
map yields no accepted answer or validity decisions; no partial salvage.
Keep all four planned answer rows and sixteen validity rows, with returned and
expected values, correctness, and accepted/invalid/unsent status. Report calls
attempted/accepted/planned and separate correct/accepted/planned decision counts.
Full primary requires four accepted responses; otherwise it is null.

For each accepted response record answer correctness crossed with whether all
validity judgments are correct, endpoints of reports marked valid, and whether
the answer agrees with that endpoint when unique. Consistency is undefined for
no-accepted-support or conflicting-support. Record disagreement between copies
of each root. These diagnostics do not assert a checking-then-selection process.

**Decision checkpoint.** If all4 answers and16 validities are correct, park
multiagent work in this restricted laboratory. If any fail, preserve the precise
error or inconsistency without causal diagnosis or an automatic repair probe.
Direct program solving could produce all correct outputs. No result establishes
pure copying effects, generalization, novelty or multiagent benefit.

Score offline and independently audit raw native streams, custody and decisions.
Then use one separate compact Fable5.1/high Relay interpretation review, no tools
or scouts, bounded by$1 and180seconds,3000 output tokens per API response.
Its context is separate from empirical sessions. Review spend does not enlarge
the empirical allowance. Preserve raw streams privately and publish selected
metadata; native list accounting is not subscription billing.

```bash
python3 _sessions/tools/run_cycle11_verifier.py prepare --prepared-manifest-sha256 <local-sha>
python3 _sessions/tools/run_cycle11_verifier.py collect --execution-manifest-sha256 <execution-sha>
python3 _sessions/tools/score_cycle11_verifier.py --score
```

All output directories are exclusive. Preserve exact commands and manifest
anchors in receipts and the report. No subsequent empirical stage is authorized
by this experiment's contract.
