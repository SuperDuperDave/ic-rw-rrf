# Cycle11 local construction checkpoint

Adopt the unchanged [four-case design](2026-09-11-cycle11-evidence-selection-design.md).
The parent is the sealed cycle10 fixture, manifest
`6647f0ae806ada137668252ffe03839caeab3e13ae2ccf8127dcc6b67cf203cd`.
Load and verify its existing source, certificate, root and artifact identities;
do not re-render the actual parent or edit any preceding source or evidence.

Before preparing the four actual packets, finish and review the new producer,
independent checker, synthetic tests and this supplement. Pin their identities
and the reused dependencies in the local manifest. Tests may construct an
explicit synthetic parent with other constants, never a new actual candidate.
There is no RNG, source search, extra arithmetic or changed corruption.

Use the precise canonical JSON and actual LF domain bytes in the original
design. Each report occurrence has an ordinal within its root and packet;
repeated identity tuples reuse IDs across regimes. Distinct tuples must not
collide. Program context is part of identity even when certificate bytes match.
Packets contain only the program, submission IDs and four reports plus null.
Record actual payload byte lengths, root/instance counts and reference vectors.

The independent checker reconstructs full states, V/F validity and first error
through the preserved independent AST interpreter. It checks parent custody,
all four placements, 3:1 counts, complements, IDs, strict types and schemas,
canonical bytes and policy predictions. Unique-root voting abstains four times;
its zero answered cases are not four errors. Exact validity and endpoint
agreement coincide in this V/F-only panel. These are two program variants,
four roots and repeated submissions, not independent samples.

An implementation, truth, schema, identity, custody or reference discrepancy
stops preparation before empirical calls. Preserve any failed preparation and
diagnose it; do not change cases to obtain a desired result. A passed local
gate permits a separate documented execution decision. It does not authorize
automatic extra agents or a harder arithmetic follow-up.
