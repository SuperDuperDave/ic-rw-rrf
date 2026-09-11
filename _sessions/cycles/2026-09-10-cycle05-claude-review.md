# Cycle05 Claude review — qualified source memo

Fable5.1 review of the supplied capsule. Recommendations are not automatically
adopted; the [integration](2026-09-10-cycle05-review-integration.md) corrects the
channel ambiguity and narrows the next experiment. Independent raw verification
was pending when this memo was written and subsequently passed.

---

I'll critique the cycle05 capsule as supplied, propose one next design, and return the relay marker.

**Verdict on the interpretation:** I agree, with one sharpening. The replication shows the pinned Opus 5 coordinator reproduces an exact Bayes calculation when every ingredient is handed to it. That is a ceiling result. Another prompt or agent sweep on the same cases can only re-measure that ceiling. The zero copied-minus-padded contrasts are the strongest single check, since they confirm the coordinator treats three copies as one root rather than as three votes.

**Caveats the capsule already states and I endorse:**
- The aware-over-blind Brier gain is a property of the generator, not evidence of coordinator skill. Any correct calculator shows it.
- Nothing here touches the original spark. The coordinator never detects a cabal. It consumes a declared partition. Equal payloads still prove nothing about copying.
- Errors at the 1e-8 scale are decimal rounding and should not be reported as a discrimination result.
- The disclosed prior exposure means this is a fixed-workflow measurement, not a clean benchmark.
- The independent raw and arithmetic audit is still open. The frozen scores are provisional until it closes.

**Recommended next design: known-noise lineage.** Keep the exact model and the same diagnostic event. Give the aware observer a lineage label that is correct with a disclosed flip rate ε, swept over four cells such as 0, 0.1, 0.3, 0.5. The true construction stays drawn with prior 1/3.

- **Distinguishing prediction.** Two closed-form references exist per cell. The exact posterior marginalizes over the label flip. The naive posterior trusts the label. At ε=0 they coincide. At ε=0.5 the exact posterior equals blind. The coordinator's returned probability lands nearer one or the other.
- **Strong baseline.** The exact noise-aware posterior, plus the naive-trust posterior as the failure reference. Both are analytic, so no sampling noise enters.
- **Observable.** Squared error to the exact posterior, and a per-packet classification of which reference is closer.
- **Stopping rule.** Twenty valid packets per cell under the same controls. Stop the axis if error to exact stays below 1e-4 in every cell, which means declared uncertainty is also saturated. Stop and document if any cell tracks naive-trust closer than exact on a majority of packets.
- **Misspecification guard.** Run the ε=0.3 cell a second time with the flip undisclosed in the prompt. Score that cell only against the naive posterior, because that is the exact answer under the supplied assumptions. Scoring it against the noise-aware posterior would confound missing information with failure to use available information, which the capsule rightly forbids.

**Why this beats adding agents.** Adding agents leaves the generator law unchanged, so the correct answer is unchanged and any agreement among agents is redundant with a result already at ceiling. Known-noise lineage changes the correct answer per cell and makes the coordinator's treatment of declared uncertainty observable. That treatment is the mechanism the anti-cabal spark actually needs, since real cabal detection is never certain.

**Relay marker, from hook context:** receipt marker `cycle05-review-e28679ade2`, seq=30, work_id cycle05-review, scope research-cycle05, artifact sha256 89d4c2b6d3b307e6494a6b54b4e38e2349dd381245f55694a633d18978a5e802. Tools are disabled in this invocation, so I did not inspect the artifact or read the seq=30 event, and I have not written an ACK. Codex, please record the consumption ACK for seq=30 on the claude agent's behalf, noting that ACK records consumption only, not approval.
