# Cycle09 — local certificate-content construction audit

**Prospective local design, frozen before parameter draws. No provider execution.**
Selected after the cycle08 local audit and Claude review; see
[review integration](2026-09-10-cycle08-review-integration.md). No cases have
been generated and no provider observations exist. Freeze implementation and
independent-checker identities before the one permitted parameter draw.
Existing cycle08 evidence and its passed local gate remain intact.

## Question and smallest fixture

Can a solver judge whether an execution certificate is valid from its actual
steps, including an invalid certificate whose final answer happens to be right?
The empirical unknown is content verification, rather than use of supplied
reliability numbers. A separate repeat intervention asks whether that judgment
changes when an invalid artifact is copied. Neither establishes multiagent value.

Use one fresh scalar program and three root certificates in two diagnostic packets:

```python
a = A
b = B
a = a + b
b = a - b
a = a + b
result = (a % 2 == R)
```

A certificate lists the complete defined-variable state after each numbered
assignment, including the final Boolean. The sole requested judgment is, for
each of the three designated original report IDs: **does every recorded state
follow from the supplied program, starting from its initial assignments?**
Return three Boolean validity decisions. Final-answer accuracy is a local
negative-control property, not a second requested solver outcome.

## Prospective order and corruption rule

Freeze code, grammar, schema and this rule before enumeration.
One `random.Random(420009)` draws A and B with `randint(-9,9)`, then R with
`randrange(2)`. Accept this first candidate only; do not search for difficulty,
truth balance or persuasive-looking corruption. A failed audit stops the panel.

Construct V from exact execution. Construct I by increasing the recorded a after
assignment3 by one, then executing the remaining assignments from that altered
state. I has one invalid local transition but the same final Boolean as V:
the alteration increases final a by two, preserving parity. Construct F by
retaining V's integer states and flipping only its final recorded Boolean.
F has an incorrect final predicate transition and an incorrect final answer.
V/I/F are private construction labels and must never appear in solver packets.

The base packet contains the three originals and two explicitly empty slots.
The repeat packet replaces those slots with byte-identical copies of F's
certificate payload. Preserve the program, original reports, order and truth.
Report IDs identify artifact instances; root IDs identify the copied artifact.
Distinct roots here do not imply independent authors or independent errors:
all three certificates derive from one construction. Provenance supplies no
validity bit, reliability rate, corruption location or correctness endorsement.

Use a separate random.Random(420010): shuffle the private list [V,I,F] once,
then draw five getrandbits(64) values in order, formatting each as `r_` plus16
lowercase hexadecimal digits. The first three identify originals in shuffled
order; the last two identify copies in slots4/5. Any ID collision stops the
construction without a replacement draw. Keep IDs/order fixed across packets.
Audit prompts/serialization for label words, source filenames, incidental validity-dependent
fields, unequal trace completeness, annotations and exposed checker output.
All certificate types use the same row/schema structure; wrong values are the
intended evidence, not a hidden formatting cue. Do not announce how many are valid.

## Exact serialization and information boundary

A certificate payload is `{"rows":[{"step":1,"state":{"a":...}},...]}`.
There are exactly six ordered rows with integer steps1..6. Row1 state contains
only `a`; rows2..5 contain exactly `a,b`; row6 contains exactly `a,b,result`.
All scalar states are JSON integers, excluding Booleans, except `result`, which
is a Boolean. Reject missing/extra/duplicate keys, rows or nonfinite values.

Both packet objects have exactly `program`, `original_ids`, and `reports`.
Program is identical source text; original_ids lists the three originals in
shuffled slot order. Reports is a five-element array. Each nonempty report has
exactly `report_id`, `root_id`, `certificate`. An original's root_id equals its
own report_id. The base's last two slots are JSON null; repeat slots contain F
copies with new report_ids and F's root_id. The copied boundary is the entire
certificate object, excluding the instance IDs; its canonical bytes must match.
Serialize all objects with sort_keys=True, separators=(',',':'), ensure_ascii=True,
allow_nan=False, followed by one newline. No construction labels, validity bits,
corruption locations, source paths or checker verdicts enter either packet.
The later prompt must explain that root_id records copying, not independence or
correctness, and request validity only for original_ids; freeze that prompt
and its strict response schema in a separate empirical execution contract.

## Exact local verification and stop

Allowlist the complete AST before execution: only the six stated assignments,
integer constants, names, +, -, positive-literal %, and the final comparison.
Negative initial literals allow only UnaryOp(USub, Constant(integer)); do not
allow arbitrary unary expressions, calls, imports or additional statements.
Bound every integer's absolute magnitude by100 and every trace to six rows.
Verify V using instrumented execution of the validated program and an independent
state-transition checker. The checker separately verifies each submitted row
against the preceding submitted state, comparing the entire expected next state,
including unchanged variables and exact scalar types; compare whole-certificate validity and
first divergence, not later mismatch counts against V. Require V valid, I invalid
first at row3 with V's Boolean, and F invalid first at row6 with the opposite Boolean.

Preserve candidate parameters, all source/payload bytes, reference states,
checker revisions, interpreter identity, hashes, exclusions and local wall time.
Verify identity of original payloads across packets and exact F-copy payloads.
Stop on any truth, schema, bound, custody or negative-control failure; no repairs
chosen to improve future solver outcomes, replacement seed or extra candidates.
If all checks pass, stop with an auditable fixture and a separate launch decision.

## Comparator and claim boundaries for any later empirical proposal

The minimum operational comparator is one verifier given the identical complete
packet, provenance, requested judgments and total inference allowance. Any
multiagent candidate must count every acquisition, verifier and coordinator call
and token, and receive no extra truth, calibration, checker verdict or tooling.
Freeze equal total input/output allowances and actual native compute controls
before calls; report realized tokens/costs, since equal ceilings are not equal work.
Both packets have five slots, but repeats add text: report that cost rather than
claiming equal token exposure or an isolated causal effect of copying. Compare methods within packet; paired original-ID
decision changes across packets describe robustness to redundant presentation.
Exact machine checking is a separate correctness ceiling and practical baseline.

The local primary is exact agreement on V/I/F validity and first-invalid rows,
plus the parity-preserving negative control, payload identity and leakage checks.
A future empirical primary would retain each original-ID decision and exact
correct/valid/planned denominators in each packet; no imputation or population
uncertainty follows from six judgments. Its resource/format stops remain to be
frozen. No solver errors or adaptive corruption search are needed to prepare.

Verification means correctly judging V, I and F; recognizing I requires more than
matching final answers. Copy robustness means preserving original judgments under
the repeat intervention, and can coexist with uniformly wrong judgments.
Only F is replicated, so a heuristic rejecting repeated roots can identify F in
the repeat packet without inspecting its content. This fixture does not separate
those mechanisms on F. Keep claims restricted to this invalid-artifact repeat
intervention, retain base-packet decisions, and compare simple always-valid and
always-invalid reference policies. Correct validity bits alone do not identify
the model's internal verification strategy.
Outperforming the matched single verifier would require a separately designed
collaboration comparison. This six-judgment pilot supplies no independence,
population accuracy, calibrated reliability or general reasoning claim.
