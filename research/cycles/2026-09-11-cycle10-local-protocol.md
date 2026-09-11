# Cycle10 local construction checkpoint

This supplement adopts the unchanged, previously reviewed
[design](2026-09-11-cycle10-discriminating-design.md) for local implementation.
The independent cycle09 prose/design audit already checked its algebra and
reference counts. Do not edit that committed design or preceding evidence.

The fixed construction is A=2, B=3, R in {0,1}; three specified cyclic orders
per program. There is no RNG, candidate search, difficulty screen, replacement
or reserve use. Hash IDs use the real newline byte in the domain prefix
`cycle10-certificate\n`, followed by canonical JSON for exactly program and
certificate, including its terminal newline. Each packet is sealed separately;
the certificate/report objects and their IDs stay fixed across permutations.

Before materializing this actual panel, review new and untracked source files,
run synthetic tests on other explicit constants, and freeze the generator,
independent checker, reused dependencies, tests and both design documents.
The producer may reuse cycle09's bounded Python/schema primitives; the checker
may reuse the independent cycle09 AST implementation. They must retain separate
truth and reference reconstruction. No new interpreter framework is needed.

Local acceptance requires all prescribed full-state/type/first-error checks,
six unique content-derived IDs, exact order/schema/byte custody, complementary
endpoints and the named policy vectors/counts. Correctness is not balanced:
there are two valid and four invalid certificates; endpoint Booleans and
positions are balanced by construction. This distinction remains in summaries.
Malformed data stops preparation rather than becoming an incorrect judgment.

The first actual rendering is the only candidate. A construction discrepancy
stops before solver calls; diagnose implementation versus design transparently.
No changed constants, alternative orders or hidden selection. Save a readable
table derived from the sealed fixture alongside exact source and packet bytes.

A passed local gate ends at a separate execution decision. It would permit
considering six fixed single-verifier calls, not a multiagent comparison or an
internal-strategy claim. The smallest useful interpretation is whether the
returned vector differs from the named finite policies. Unlisted shortcuts,
generalization and causal effects remain separate questions.
