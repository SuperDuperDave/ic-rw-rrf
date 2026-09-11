# Cycle07 program grammar and candidate order

Written before candidate enumeration. This fixes the local task generator for
the [observation design](2026-09-10-cycle07-observation-design.md); it does not
authorize provider calls or claim that the tasks elicit errors. The preparation
stops at 24 accepted structural templates, six per `(stratum, truth)` cell,
or fails after 1,000 candidate attempts. Acceptance never uses solver answers.

## Syntax and bounds

Each source has 8–14 nonblank executable source lines; an assignment, `if`
header, or `for` header counts as one line. The generator below emits 12 lines.
Allowed scalar names are `a`, `b`, `c`, and loop index `i`; the final assignment
uses `result`. Integer literals, scalar assignment, `+`, `-`, `*`, positive
literal `%`, and one-operator comparisons (`==`, `!=`, `<`, `<=`, `>`, `>=`) are
allowed. A negative integer literal is unary minus on a nonnegative integer
literal. No other expression, statement, operator, call, container, Boolean
literal, annotated/augmented/multiple assignment, or attribute is allowed.
The only call is the loop iterator `range(N)` for a literal integer `3 <= N <= 6`.
The final line is `result = (a % 3 == R)`, with `R` in `{0,1,2}`. Comparisons
occur only as branch conditions or this final predicate, never scalar values.
Every name read must already be assigned on that execution path. Branches have
no `else`; loops have no `else` and are not nested. Sequential programs have no
loops and at most two nonnested conditionals; bounded-loop programs have exactly
one loop and at most one conditional, inside it.

Reject any candidate whose integer literal, scalar state, or intermediate
arithmetic value exceeds absolute magnitude 1,000,000. Reject any candidate
whose worst-case executed-statement bound exceeds 128. Assignments cost one;
each visited `if` condition costs one; a loop with N iterations costs N+1 header
visits plus its executed body statements. Validate the entire AST and this
static bound before any Python execution. Instrumented Python checks every
arithmetic result and actual statement count before a second execution of the
unchanged validated source. Both executions must agree. The independent checker
implements its own AST/state evaluator and verifies all accepted truths and
final states. The Boolean `result` is separate from integer `final_state`.

## Exact candidate enumeration

Use Python's `random.Random(420007)` solely for candidate parameters. For each
zero-based attempt `j` in `0..999`, use `sequential` when j is even, otherwise
`bounded_loop`. Let local index be `j // 2` and structural index be local index
modulo 81. Enumerate the 81 structural tuples in Python `itertools.product`
order, with rightmost argument varying fastest:

```
product(('+', '-', '*'), ('+', '-', '*'), (0, 1, 2), ('<', '>', '=='))
```

These select `(OP1, OP2, tail, CMP)`. On **every** attempt, including exclusions,
draw these seven parameters in this order with inclusive `randint` endpoints:
`A:1..9`, `B:2..7`, `C:1..6`, `M:5..11`, `N:3..6`, `Q:7..13`, `R:0..2`.
Even unused parameters are drawn. Tail expression is respectively
`(a + b) + c`, `(a - b) + c`, or `(a + b) - c`. The two source skeletons are:

```python
a = A
b = B
c = C
a = a OP1 b
b = (a + c) % M
if b CMP c:
    a = a OP2 c
c = c + b
if a % 2 == 0:
    b = b + a
a = TAIL
result = (a % 3 == R)
```

```python
a = A
b = B
c = C
for i in range(N):
    a = a OP1 b
    b = (b + i) % M
    if b CMP c:
        a = a OP2 i
    c = (c + a) % Q
b = b + c
a = TAIL
result = (a % 3 == R)
```

Truth comes from execution of the complete candidate, never choosing R from
the computed state. Retain the first valid candidate in each truth/stratum
cell until that cell has six. Stop immediately once all four cells have six.
Record source and hashes for **every attempted candidate**, selected or excluded,
with syntax/bound failure, duplicate accepted structure, or full cell as the
exclusion reason. Failed or full-cell attempts do not reserve a structure;
deduplication is against all previously accepted items across both splits.

## Structural identity and split

Remove the final `result` assignment before normalization. Replace every integer
literal (including a signed literal) by one common integer marker; replace scalar
names consistently by `v0`, `v1`, ... in first AST traversal order, keeping the
builtin `range` fixed. Keep operator types, target/read identity, statement order,
and control flow. Hash `ast.dump(normalized_tree, include_attributes=False)`
as UTF-8 SHA-256. Thus constants, alpha renaming, and any change or complement
of the final predicate cannot create a new template. This is a syntactic
control/data-flow criterion, not a proof of semantic inequivalence.

Template ID is `t_` plus the first 20 hex digits of that digest. Item ID is `i_`
plus the first 20 hex digits of the exact source SHA-256. Cells are visited in
order `(sequential, false)`, `(sequential, true)`, `(bounded_loop, false)`,
`(bounded_loop, true)`. Within each cell start with template IDs sorted ascending.
One `random.Random(42)` instance shuffles each cell in that cell order. Assign
the first two templates to `development` and the remaining four to `reserved`.
Record each shuffled list. Within each cell, the first development item is G-first
and the second S-first. With a separate `random.Random(42)`, shuffle the globally
sorted eight development item IDs to get item execution order. Emit the two
role calls adjacently per item in its declared first-role order. The resulting
request order has 16 packet IDs and no reserved item.

## Information boundary and custody

Each provider payload is exactly a JSON object with `program` and
`role_instruction`. Common framing asks for the final Boolean `result` and only
`{"answer": true}` or `{"answer": false}`. G and S differ only in the role
instruction stated in the observation design. No truth, split, ID, template,
other answer, or research context appears in the payload. Store its canonical
JSON bytes separately from metadata; only those bytes and the frozen system
prompt may enter a provider request. Strict response parsing rejects duplicate
keys, non-Boolean answers, extra keys, prose, fences, nonfinite constants, and
trailing material. Whitespace permitted by JSON is accepted.

The fixture contains all 24 sources, normalized structures, exact ASTs, truths,
Python final states, candidate audit trail, shuffled cell assignments, and only
the 16 development payloads. Final preparation additionally pins interpreter
identity, source/design/checker hashes, exact preparation argv, independent
truth evidence, and every prepared artifact hash. Local generation/truth-check
wall time is measured separately. Any verification or custody mismatch blocks
launch. Prepared artifacts are written exclusively into a new directory.
