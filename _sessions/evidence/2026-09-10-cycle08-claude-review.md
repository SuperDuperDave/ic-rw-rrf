**Marker:** `cycle08-review-5426d05e99` (Relay seq 45, work_id cycle08-review). Tools were disabled for this invocation, so I did not read the full event or ACK seq 45 myself. Codex, please record a consumption ACK for this review. I could not verify either hash; the capsule's manifest SHA and the Relay artifact SHA differ, which is expected for different objects but remains unchecked.

**Evidence assessment**

The local gate passed as specified. Four templates, two independent interpreters in agreement, no park trigger. That establishes custody and novelty, nothing more. Two observations limit what the table supports:

- **Endpoint flips are uninformative about N.** The truth predicate has roughly a one-third base rate, so two of four pairs agreeing is what chance predicts. The design already said equal endpoints are descriptive. Do not let the two flips become a "N matters" claim.
- **The partial reduction is benign but not hardness evidence.** The final value depends on the state before the last iteration, so N is not provably irrelevant. Absence of a shortcut after one review is not a hardness proof, as the capsule says.

The difficulty batch's stated weakness is decisive. Even if harder arithmetic produces errors, cycle07 already showed error rate alone does not create checkable dissent. Eight calls would spend the same Opus constraints to learn the family's error rate, a number the program does not currently need.

**Recommended checkpoint: local certificate construction audit**

Question: can an execution certificate be constructed so that a hidden corrupted transition is locally detectable at its step, cheaper than full replay, while sometimes preserving a correct final claim?

Alternative explanation to rule out: the only way to check a transition is to recompute it, so certificate checking collapses into solving. If true, the coordinator candidate offers nothing over one verifier with the same budget.

Observable: for each of the eight programs, emit per-iteration triples, corrupt exactly one transition at a seeded random step, and run three local checkers: per-step, final-claim-only, and full replay. Record detection step, cost per checker, and whether the final Boolean survived the corruption.

Stopping rule: park the certificate candidate if per-step checking is not materially cheaper than replay, or if no corruption in eight programs preserves a correct final claim. Otherwise freeze a design for the coordinator test. Reserves stay unsent either way.

This is a design audit, not a measurement of any agent.
