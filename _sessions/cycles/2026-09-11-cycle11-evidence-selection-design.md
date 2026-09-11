# Cycle11 — four-packet evidence-selection construction

**Prospective local design; no rendering or provider execution has occurred.**
Follow [cycle10 review integration](2026-09-11-cycle10-review-integration.md).
Freeze this contract and implementation/checker identities before construction.
A passing local gate permits a separate execution decision, not automatic calls.

## Question and sealed inputs

Does one verifier return the correct final program answer alongside correct
submission-validity judgments when valid evidence is either the apparent minority
or majority? Correct validity judgments with a wrong answer are informative in
either regime. This measures the returned decisions and their consistency, not
internal checking, indispensable use of certificates or multiagent benefit.

Reuse cycle10's exact R0/R1 program source, V/F certificate bytes and existing
root IDs from `results/cycle10-2026-09-11/prepared/`. Verify its manifest SHA256:
`6647f0ae806ada137668252ffe03839caeab3e13ae2ccf8127dcc6b67cf203cd`.
Verify referenced artifact hashes and root mappings before use. Preserve I and
every prior artifact unchanged; I does not appear in this fixture. No new
arithmetic, parameter draws, corruption, certificate repair or source selection.
The existing final state has a=7: R0's answer is false and R1's is true.

V records the correct endpoint and is valid; F records its complement and is
invalid at the final transition. V/F are private construction labels. Validity
depends on the supplied program: identical certificate bytes across R0/R1 can
have opposite validity. Preserve the program-conditioned root IDs; never merge
roots across programs merely because certificate payload bytes are identical.

## Fixed crossing and request order

Regime A has one V instance and three F instances; B has three V and one F.
Apparent support is submission count, with three instances of one artifact and
one of its opponent. These are two original roots, not independent acquisitions.
Use exactly this order and placement; the fifth report slot is null throughout:

| Request | Program | Private regime | Slots1,2,3,4 | Exact answer |
| --- | --- | --- | --- | --- |
| 1 | R0 | A | F,V,F,F | false |
| 2 | R1 | B | V,V,V,F | true |
| 3 | R0 | B | V,F,V,V | false |
| 4 | R1 | A | F,F,F,V | true |

Within each program, A/B are labelwise complements at every slot. Thus each
fixed slot contains V once and F once per truth, giving2/4 correct final answers.
Majority-by-instance count is correct in both B cases and wrong in both A cases;
minority choice does the reverse. Both score2/4. Always-false and always-true
also score2/4. Exact replay scores4/4. Deduplicated root votes tie1:1 everywhere:
record four abstentions and zero answered, not0/4 incorrect. Deduplication alone
supplies no final selection rule. No chance null is claimed.

## Instances, bytes and packet schema

Assign each root's occurrences ordinal1,2,3 in left-to-right order within a
packet. Derive report_id as `s_` plus the first16 lowercase SHA256 hex digits of
the UTF-8 prefix `cycle11-submission` followed by one actual LF byte, then
canonical JSON containing exactly `program`, `root_id`, `instance_ordinal`.
Program is its unchanged source string; ordinal is an integer. Canonical JSON
uses sort_keys=True, separators=(',',':'), ensure_ascii=True, allow_nan=False,
and one terminal LF. Neither private V/F nor A/B labels enter the hash input.
The same identity tuple reuses its ID across regimes; distinct tuples must not
collide. Any collision stops construction without another prefix or draw.

Each packet has exactly `program`, `submission_ids`, `reports`. submission_ids
lists the four report_ids in slot order. reports is a five-element array with
four objects and a final null. Each object has exactly `report_id`, `root_id`,
`certificate`. Root IDs and canonical certificate object bytes come unchanged
from cycle10. New instance IDs are distinct even for copied certificates.
Seal each whole packet separately; different slot order/multiplicity changes
packet bytes, while each reused certificate's canonical bytes stay fixed.

Use the same canonical serialization for packets. No type/regime labels, expected
answers, valid-count annotations, checker verdicts or source paths enter inputs.
Root metadata records artifact identity/copying, not correctness or independence.
Record actual input byte lengths and later token costs; do not infer equal tokens
from equal slots, forecast costs from cycle10, or require a tempting majority.

## New response contract and measurements

A later execution contract must freeze a new common instruction: determine the
program's final Boolean, judge complete execution validity for every submission,
explain root metadata's limited meaning, and request only the following shape:
`{"answer": <Boolean>, "validity": {<each exact submission_id>: <Boolean>}}`.
It must not announce how many submissions are valid. No examples, prior responses,
reference labels, reliability tables or additional agent stage are supplied.

The complete terminal output must parse as one JSON object with exactly answer
and validity. Require an actual JSON Boolean answer, exactly the four sealed
submission-ID keys, actual Boolean values, and no duplicate keys at any level.
Reject missing/extra fields, numeric substitutes, other text and fences; permit
surrounding whitespace. An invalid map contributes no accepted decisions and is
preserved without partial salvage. The cycle10 three-ID parser is not this schema.

Preserve all four planned answer records and all16 planned validity records with
expected/returned values, correctness and accepted/invalid/unsent status. Report
correct/accepted/planned counts separately for answers and validities, plus
attempted/accepted/planned calls. The complete primary requires all four accepted
maps; otherwise mark it absent and label partial counts. No missing-value imputation.

For every accepted map in either regime, record answer correctness crossed with
whether all four validity judgments are correct. Also record the set of endpoint
Booleans among submissions marked valid. If that set has one member, record
whether answer equals it; otherwise report consistency as undefined with reason
no-accepted-support or conflicting-support. Record disagreement among validity
judgments for instances of the same root. These diagnostics use the returned map
and do not presume a sequence of internal verification followed by selection.

## Local gates, references and stop

Independently reconstruct both program truths, each reused certificate's complete
state transitions and first-invalid row, and all packet/instance/root relations.
Require four packets, four nonnull instances each, two roots per packet, the
frozen3:1 crossing/slot order, exact source/certificate custody, strict schemas,
unique tuple IDs, and preserved within-program truth and underlying two-root
evidence across regimes.
Preserve manifest/code/interpreter identities, canonical bytes and local wall time.

Verify exact reference vectors before model observations: replay4/4 answers and
16/16 validities; majority, minority, each fixed slot, always-true and always-false
each2/4 answers. Always-valid and always-invalid each score8/16 validities.
Endpoint-agreement validity is identical to exact checking for these V/F roots:
this selection task does not repeat cycle10's endpoint-only discrimination.
Require every stated count and all type/position/truth balances; retain vectors.
Stop on any schema, truth, identity, custody or reference failure. Report the
discrepancy; no outcome-driven construction change or replacement case is allowed.

A passing audit stops at a sealed local fixture and explicit launch decision.
Any separate empirical freeze may schedule exactly four fresh single-verifier
calls in the stated order, after rechecking native controls and setting resources.
Stop scheduling at the first native/format/custody/resource failure. Wrong but
accepted maps remain observations in the fixed batch; no retries, repairs,
extra agent, parameter search or automatic follow-up probe follows any failure.

If all four answers and16 validity judgments are correct, park multiagent work
in this restricted laboratory: no observed single-verifier deficit remains here.
Otherwise preserve the precise error/inconsistency without a causal diagnosis.
Counts, positions, context and stochastic responses do not establish pure copying
effects. These are reused roots on two variants of one skeleton, not independent
samples, a generalization result or a novelty claim. No result identifies internal
strategy; a direct program solver can also produce every correct output.
