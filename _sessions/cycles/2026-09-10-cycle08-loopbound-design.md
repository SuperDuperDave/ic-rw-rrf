# Cycle08 proposal — audit a loop-bound manipulation locally

**Prospective local preparation only.** Freeze this grammar/order before any
candidate enumeration. Cycle07's eight development pairs were all correct;
that result concerns that finite panel. Its 16 reserved items remain unsent and
are not inputs to this new design. No provider invocation is authorized by this
document. A favorable local audit permits consideration of a separate execution
freeze, not automatic launch.

## Question and smallest contrast

Can a fixed source manipulation change the amount of sequential state evolution
without changing nesting, operations, parameters, role instruction or effort?
Use four fresh structural templates, each at literal loop bounds N=4 and N=64:
eight programs in four matched pairs. Execution length is an operational
manipulation, not a guarantee of reasoning difficulty or minimum solution work.
An algebraic shortcut can make a long execution easy.
This is a new family relative to cycle07; the one-variable claim applies within
each new matched pair, not to differences between the two cycles.

## Frozen grammar, candidate order and resource bounds

Use the following 12-line skeleton; OP1 and OP2 are independently + or -.
Every occurrence of 997 is fixed. The loop index is never read in its body.

~~~python
a = A
b = B
c = C
for i in range(N):
    a = (a * b OP1 c) % 997
    b = (b * c OP2 a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == R)
~~~

Zero-based candidate j uses the j modulo 4 member of the ordered operator list
[(+, +), (+, -), (-, +), (-, -)]. One Python random.Random(420008) draws A, B,
C with randint(1,996), then R with randint(0,2), on every candidate attempt.
Both N variants use those identical parameters and identical final predicate.
Generate at most 32 candidates; retain the first four syntactically valid,
bounded, structurally distinct candidates. Normalize as in cycle07: erase
constants, alpha-rename variables, and remove the final predicate assignment.
Require novelty against cycle07's stored template hashes and all accepted new
templates. The two N variants intentionally share one structural identity;
they are matched observations, never independent templates or different splits.
Do not access old reserved sources or answers to refine this grammar.

Only the skeleton's integer assignments, positive literal modulus, arithmetic,
single comparison, bounded loop and final Boolean predicate are allowed.
Validate the complete AST before Python execution. Bound absolute intermediate
integers by 1,000,000 and executed statements by 512. Counting assignments and
if visits once and loop headers N+1 times gives worst-case 6N+7 statements:
31 at N=4 and 391 at N=64. All modular states are in 0..996; even multiplication
followed by addition stays below the magnitude ceiling. Reject bound/syntax
failures with a reason; an independent-checker disagreement stops preparation.
Stop once four templates are accepted or the 32-attempt ceiling is reached.
Neither model outcomes nor local cycle/truth findings select replacements.

## Local evidence and decision

Independently reconstruct all eight truths using validated Python execution
and a separately written AST/state evaluator. Match source, AST, final scalar
state, predicate, exact Boolean answer and actual/static statement counts.
Preserve every candidate/parameter/hash/exclusion, both evaluator revisions,
interpreter identity, exact commands and measured local wall time.
For each accepted template, record the initial (a,b,c) and every loop state
through iteration 64. Because the transition never reads i, a repeated full
state proves an eventual cycle; record its entry and period. Compare the two
endpoint states, final (a,b,c) and predicate answers. Compute the predicate after
the fixed tail at every prefix length 0..64 to identify observed constant-output
paths. Record branch counts and verify by source comparison that only N changes.
One bounded independent source review checks whether a reset, disconnected
predicate, fixed point or explicit algebraic identity defeats this contrast.
Absence of a found shortcut is not proof that no short solution exists.
Park this fixed panel if four fresh templates cannot be obtained, any custody/
truth check fails, all eight answers have one Boolean value, or any template has
identical final (a,b,c) at both bounds, a repeated full state within the
64-step trace, or a demonstrated shortcut making the bound change irrelevant.
Report the reason without replacing that template or searching another seed.
Otherwise the local audit justifies considering eight empirical observations:
it establishes a nondegenerate manipulation, not expected solver errors.
All audit-based decisions are finite development choices and must be reported.
## Conditional empirical checkpoint, requiring another freeze

A later protocol may fix exactly eight G-only calls, one per frozen program,
with fresh contexts and matched native controls. Counterbalance which bound
comes first in two template pairs each and freeze template order before calls.
Primary: actual correct/valid/planned counts and accuracy by bound, plus the four
paired correctness transitions; report invalid and unsent separately. Stop after
the fixed eight calls or the first native/format/custody/resource failure.
There is no first-mixed-level stopping rule, S arm, exposure arm, reserve,
effort change, confidence interval or generalization claim. A mixed result is
development evidence only. Increased thinking tokens describe observed cost;
they do not identify a causal mechanism. Recheck prices and native controls
before that separate freeze; previous realized costs are not a forecast.
