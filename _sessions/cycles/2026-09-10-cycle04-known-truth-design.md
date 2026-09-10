# Cycle04 design — evidence origin, agreement, and a protected minority

Prepared after cycle03's frozen gate routed to R5. **Design only: not run.**
Before implementation, review the exact input/output contract below; preserve
any correction as a dated amendment before calculating outcomes. No actual LLM
calls, new retrieval sources, or learned aggregator belong in this first fixture.

## Purpose and scope

Build a small laboratory where truth, repeated evidence, and reliability are
known. Test whether a coordinator treats three copies differently from three
independent agreeing observations, while showing when favoring a minority hurts.
Copy invariance and Bayes optimality under known assumptions are not new results.
The useful output is a verified benchmark, comparator accounting, and an explicit
information boundary for later empirical agent work.

## Primitive world and two factors

One instance contains binary truth `Y` uniformly in `{−1,+1}` and four primitive
readings `G1,G2,G3,S`. Conditional on `Y`, the readings are independent. Each
generalist has symmetric accuracy `7/10`; the specialist has symmetric accuracy
`pS`. Conditional independence is stipulated by the generator, not inferred from
different source names. Errors are symmetric and there are no missing judgments.

Enumerate every one of the 32 assignments of these five binary variables, using
exact rational probability weights. Reuse the same primitive world across report
constructions. Unobserved G2/G3 in padded/copied arms are potential readings,
not charged observations or evidence supplied to a policy.

| Factor | Fixed values |
| --- | --- |
| Report construction | Padded `[G1, null, null, S]`; copied `[G1, G1, G1, S]`; independent `[G1, G2, G3, S]` |
| Specialist reliability | `pS=11/20` (0.55) or `17/20` (0.85) |

The padded/copied comparison holds truth and informative primitive evidence
fixed. The independent arm intentionally supplies two extra readings. All arms
have four report slots and a common four-acquisition ceiling; actual informative
acquisitions are two, two, and four. Do not call independent-versus-copied arms
equal-information or equal-acquisition treatments. Compare policies on identical
packets within each arm and report this resource difference beside cross-arm gaps.

## Information available to a policy

All policies receive the same prior, known reliability parameters, construction
definitions, and equal prior over the three constructions. The realized
construction is hidden; it may be partially inferred from the observed packet.
The specialist role and its known reliability are visible to every policy.
Knowing pS is an idealized calibration resource, not an inferred property of
dissent. The two pS cells are separate known parameter settings, not hidden
truth regimes that only a favored policy can observe.

Each report has a unique opaque report ID independent of truth. These IDs must
not themselves reveal whether generalist payloads came from the same root.
Provenance-aware policies additionally receive the actual parent-source partition
of non-null reports, using opaque root IDs. The root partition supplies trusted
copy lineage only; it never says whether a reading is correct. It is available
equally to all aware policies and inaccessible to all blind policies. Renaming
IDs must not change a policy's prediction.

The optimal blind comparator knows the construction mixture but marginalizes
over its unknown realized arm, conditioning on the observed roles, payloads and
null slots. Do not give it the arm label for per-cell evaluation. The aware
comparator can infer copy structure from the supplied partition. This is a
controlled difference in information, not matched-information superiority.

## Frozen comparator definitions

Every policy returns a probability of `Y=+1`. Use equal prior odds, exact rational
likelihood products where possible, and 0.5 on exact posterior ties.

1. **Naive report independence:** treat every non-null report as an independent
   sensor of its declared reliability, even when it repeats G1.
2. **Payload quotient:** merge identical generalist payloads into one of each
   sign, then use the same independent-sensor likelihood rule. Keep S separate
   by role. This intentionally exposes that identical answers need not share
   an origin; it is a diagnostic comparator, not a proposed solution.
3. **Optimal blind Bayes:** compute the exact posterior by summing weighted
   latent worlds over the known construction mixture consistent with the visible
   packet. Identical visible packets must receive identical probabilities.
4. **Equal root weighting:** among distinct observed roots, report the fraction
   of positive readings. This transparent provenance heuristic ignores known
   reliability differences; it is not a calibrated Bayes claim.
5. **Optimal aware Bayes:** count each distinct observed primitive root once,
   using its known reliability in the likelihood product. Verify independently
   by conditioning the exhaustive world table on payloads plus root partition.
6. **Protected minority diagnostic:** when all three non-null generalist reports
   agree against S, return the S-only posterior (`pS` if S is positive, `1−pS`
   otherwise). In other cases use the optimal blind posterior. It receives the
   same blind information as comparator3. It operationalizes unconditional
   rescue under this disagreement pattern; it is not an endorsed algorithm.

For classification error, choose the more probable sign; count exact probability
0.5 as expected half an error. For paired correction/harm decomposition, use the
same fair tie coin in both policies and enumerate its two values if needed.
Do not quietly reward one tie rule over another.

## Measurements, predictions, and falsifiers

Primary result: exact expected Brier loss `(p − 1[Y=+1])²`, including aware versus
**optimal blind** difference under the fixed equal construction mixture, reported
separately by pS. Also report every policy's per-cell Brier loss/classification
error, and probability mass of corrected versus newly introduced errors against
the same optimal-blind comparator. The sign convention is
`correction − harm = error(optimal blind) − error(policy)`.
Per-cell comparisons are diagnostics; a
mixture-optimal policy need not be optimal conditional on a hidden arm.

Secondary structural check: for each primitive world, does replacing null slots
with copies change the probability while keeping informative evidence fixed?
Aware Bayes and equal-root predictions must be invariant. Blind Bayes need not
be invariant because its observation changes its posterior over hidden lineage.
Do not label that rational uncertainty a generic reasoning failure.

Analytical calibration prediction: one generalist supplies likelihood odds
`7/3`; three independent agreeing generalists supply `(7/3)^3`. Strong-specialist
odds `17/3` lie between them. Thus, when all generalists oppose S, aware Bayes
follows strong S against copied consensus but follows three independent agreeing
generalists. Weak-specialist odds `11/9` are below even one generalist's odds;
blindly rescuing that minority is harmful in the copied-disagreement cell.
These are constructed expectations to check, not empirical discoveries.

Against the **optimal blind** comparator, strong-specialist rescue is not an
automatic improvement: in the disagreement pattern, its generalist likelihood
ratio is `(0.7 + 0.7³)/(0.3 + 0.3³) = 1043/327`, below specialist odds `17/3`.
It already follows strong S. The protected-minority diagnostic then changes
confidence/Brier loss, not its class prediction. Any rescue claim against naive
report independence must name that different comparator. With weak S,
`1043/327 > 11/9`, so the diagnostic does flip the optimal-blind choice toward
the weaker specialist. Do not silently switch baselines to find a rescue.

Falsifiers/checks: probabilities sum to one; independently conditioned Bayes
tables agree; root renaming and global sign swaps behave correctly; repeated
reports do not become independent likelihood factors in aware Bayes; and
correction-minus-harm mass matches the paired classification-error difference.
Report losses and counterexamples, not only favorable cells. A discrepancy with
the exact conditioning reference is a model/implementation problem to resolve
before interpreting the fixture.

## Information boundary and stop

Trusted lineage plus known calibration is a strong idealization. Without a
truth/calibration anchor, globally reversing truth and source accuracies can
preserve visible-answer distributions while reversing correctness. Source origin
alone cannot identify which hidden world is true. This construction lies outside
the two known-reliability cells and should be presented as a separate analytical
boundary, not silently added as another experiment arm.

Stop after the six cells, exact tables, independent arithmetic review, and a
decision about what observable an empirical extension would need. No Monte Carlo
confidence intervals, free parameter grid, or real LLM fan-out is needed for
32-state enumeration. A later agent test must separately specify trustworthy
evidence access, equal token/call budgets, model calibration and metadata errors.
Any accuracy advantage here belongs to the stipulated information model; it
does not establish new retrieval performance or real-agent reasoning ability.
