# Cycle10 candidate — position and endpoint controls for certificate judgments

**Draft for review; local audit first, no empirical launch authorized here.**
Design work began while cycle09 calls were pending; this artifact was written
after their reported completion: six correct, unchanged original-ID judgments.
Cycle09's first-original-only rule also scores6/6, leaving that output policy
compatible with the observation. This proposal targets specified response rules,
not induced difficulty, an internal strategy diagnosis or a general ability claim.

## Fixed construction, with no random search

Reuse the six-assignment skeleton and full-row certificate schema from
[cycle09](2026-09-10-cycle09-certificate-design.md), with fixed A=2 and B=3.
Create exactly two programs, R=0 and R=1. No draws, candidate replacements,
difficulty screening or alternative constants are permitted. Nonzero constants
are a declared construction change, not a claim that these programs are harder.

For each program construct the same three private types: V is exact execution;
I increases recorded a at row3 by one and propagates the remaining assignments;
F retains V's integer states and flips only its final recorded Boolean.
Algebra fixes final a=2A+B=7 for V and9 for I. Both have odd parity, so their
final Booleans agree for either R. Changing R complements every certificate's
endpoint Boolean while leaving V valid, I first-invalid at row3 and F at row6.
This creates six root certificates, including two valid roots and four invalid.

For each R render all three cyclic orders, with two trailing null report slots:

| Order label, private to audit | First original | Second | Third |
| --- | --- | --- | --- |
| P1 | V | I | F |
| P2 | F | V | I |
| P3 | I | F | V |

The complete fixture is six packets, not six distinct programs. Each certificate
appears in every original position once. Both endpoint values occur at every
position for every type. All six packets have three reports and two nulls;
copy interventions, including I copying, remain separate future questions.

## IDs, bytes and information boundary

Derive each root/report ID as `r_` plus the first16 lowercase SHA256 hex digits
of UTF-8 `cycle10-certificate\n` followed by canonical JSON containing exactly
`program` and `certificate`. Use cycle09's canonical JSON options and terminal
newline. The hash input contains no V/I/F or order label. An original's root_id
equals its report_id; any collision among the six roots stops construction.
Keep IDs and canonical certificate/report object bytes fixed across that R's
three orders. original_ids follows slot order. Full packet bytes change with
the permutation and must be sealed separately for each packet. Report every
byte-length difference; equal slots need not mean equal native tokens. Only R
changes between the two program sources.

Solver packets contain no construction labels, expected validity, counts of valid
certificates, checker output, filenames or known reliability. Provenance continues
to identify artifacts, not correctness or source independence. Do not supply a
worked example or one packet's answer to another invocation. Private construction
types may be used for offline scoring only. Inspect serialized inputs for leakage.

## Local audit, reference policies and gates

Freeze this construction, generator/checker identities and serialization before
rendering. Reuse the validated AST allowlist, exact scalar types, complete-state
comparisons, six-row bound and integer-magnitude ceiling100 from cycle09.
Independently execute both programs and check every submitted transition.
Require exact agreement on V/I/F validity, first-invalid rows, I's correct
endpoint despite its bad transition, and the R-complement relationships.
Verify both sources, all six certificates and six packet compositions/hashes,
unchanged IDs and certificate/report object bytes across orders, each packet's
separately sealed bytes, exact schemas and position/endpoint balance.
There are two source programs; repeated appearances must not inflate that count.

Audit these fixed policy predictions against all18 planned original-ID judgments:

| Reference policy | Correct / planned |
| --- | --- |
| Exact complete-certificate checker | 18/18 |
| Always valid | 6/18 |
| Always invalid | 12/18 |
| Accept only one fixed original position, any of the three | 10/18 |
| Accept when certificate endpoint agrees with true program answer | 12/18 |
| Use the certificate's final Boolean as its validity judgment | 9/18 |

Require the checker vector to differ from every listed heuristic vector and
the reconstructed reference scores to equal this table. Preserve individual
predictions, not only totals. Stop on any schema, truth, balance, custody, bound,
collision or reference discrepancy. Resolve implementation errors transparently
before proceeding; do not change the construction to fit desired solver behavior.
Seal source, packet and reference bytes with code/interpreter identities and
local wall time. A passing audit ends at a reviewable local fixture.

## Conditional empirical question and stopping

Only a separate execution freeze may consider one single-verifier call per
packet, using the same strict original-ID Boolean-map instruction and fresh
context controls as cycle09. Fixed candidate order: (R0,P1), (R1,P2), (R0,P3),
(R1,P1), (R0,P2), (R1,P3). Recheck native controls/costs and set a batch allowance
before calls. Preserve all18 correct/accepted/planned records, invalid/unsent
separately, plus each root's decisions across positions and each type's decisions
across endpoints. Stop after six calls or the first native/format/custody/resource
failure, with no retries or result-contingent follow-up. Wrong valid maps remain
observations. The complete primary requires all six accepted responses.

Full correctness would distinguish the returned vector from these named fixed
policies on this fixture. It cannot identify the model's internal reasoning,
exclude unlisted shortcuts, establish an isolated causal position/endpoint effect,
or demonstrate general verification, independent samples, novelty or multiagent
benefit. Fixed order and stochastic outputs remain limitations. The programs and
certificates are closely related; report18 judgments on two endpoint variants
of one arithmetic skeleton. This is a response-policy diagnostic, not a claim
that more calls or tokens improve performance. Stop and interpret the fixed
vectors even if every answer is correct; further hardening needs a new question.
