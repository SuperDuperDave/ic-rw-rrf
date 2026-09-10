# Retired cycle05 candidate — independent origins, correlated errors

Prepared during cycle04, then **retired as a new numerical experiment** after
Claude review and independent algebra. Not run. Retain the conceptual boundary
and original candidate below; the selected next step is the
[coordinator packet test](2026-09-10-cycle05-coordinator-packet-design.md).

The marginalized generalist likelihood is
`(1-lambda)*product_i P(Gi|Y) + lambda*1[all G agree]*P(G1|Y)`.
At lambda=1/2 this is exactly cycle04's copied/independent mixture after
conditioning on non-null packets and discarding arm/partition metadata. Its
joint Bayes equals old blind Bayes; root-product equals old naive independence.
At lambda=0 both equal the old independent-arm posterior. The acquisition/root
metadata differ, but the proposed losses can be recovered from existing tables.
A new run would repeat arithmetic. The useful derived lesson remains: distinct
acquisitions and correct individual calibration need not imply independent
errors. This is an analytical boundary, not newly measured behavior.

## Question

Does correct copy lineage plus correct individual source calibration suffice
for the root-product rule when distinct acquisitions share an environmental
error? Cycle04 stipulates conditional independence across primitive roots.
Copy identity, statistical dependence and accuracy are different observables.

## Two fixed cells

Retain uniform binary truth Y, three generalists of symmetric accuracy 7/10,
and one specialist of symmetric accuracy 17/20. Observe all four distinct
roots, four report slots and four acquisitions in both cells. No copies,
missing values, hidden arm mixture, or additional source-quality setting.

Let an environmental mode Z be Bernoulli(lambda), independent of truth. At
Z=0, the generalist errors are independent Bernoulli(3/10). At Z=1, draw one
Bernoulli(3/10) environmental error and let it affect all three distinct
acquisitions. The specialist error remains independent Bernoulli(3/20).
Every source retains its stated marginal calibration. Root IDs truthfully
identify distinct acquisitions; the environment is not a copied report.

Fix lambda at 0 and 1/2. Marginalize Z and the error draws analytically to give
32 assignments of (Y,G1,G2,G3,S), with exact rational weights in each cell.
Do not sweep lambda or select a specialist reliability after outcomes.

Compare the root-product rule carried from cycle04 with exact joint Bayes.
Both policies are told the same correct joint model and known lambda. The
root-product comparator deliberately uses only its marginal reliability
factors; joint Bayes uses the provided dependence. This comparison tests a
factorization assumption, not a hidden information gift to one policy.
Use these two comparators only.
No policy receives realized truth, environmental mode or latent error flags.

## Prediction and measurement

Primary: exact expected Brier regret of root-product against joint Bayes,
separately for each lambda. Secondary: expected classification error and paired
correction/harm of joint Bayes relative to root-product, using a shared fair
coin on ties. Report actual acquisition counts and no modeled provenance cost.

Before outcomes, the constructed disagreement check is explicit. At lambda=0,
unanimous generalist likelihood odds are 343/27, exceeding specialist odds
17/3. At lambda=1/2 they become 1043/327, below 17/3. The root-product rule
still uses 343/27, so it and joint Bayes choose different signs when unanimous
generalists oppose S in the correlated cell. Reproducing this is a calibration
check. Failure means the proposed construction or implementation needs repair.

Also record the truth-conditional pairwise error covariance
`P(Ei=1,Ej=1 | Y) - P(Ei=1 | Y)P(Ej=1 | Y)`.
In this specified construction it is `lambda*(3/10)*(7/10)`. Direct measurement
requires correctness labels over repeated tasks. Agreement-based inference
would need additional identifying assumptions; source names alone do not
supply them. A later empirical estimate would need held-out calibration,
sampling uncertainty and an account of other shared causes.

## Stop and alternative

Freeze the final packet/comparator/serialization contract before implementation.
Stop after two exact distributions, an independent arithmetic reconstruction,
and one worked counterexample. No providers, data acquisition, fitted dependency
model, parameter search, confidence intervals or real-world performance claim.
The supported boundary would concern sufficiency of lineage and calibration;
it would not make provenance useless or establish actual LLM dependence.

The alternative empirical step is one coordinator interpreting the cycle04
disagreement packets: two known specialist reliabilities, both sign orientations,
and padded/copied/independent constructions. There are 12 distinct aware inputs
and eight blind inputs (copy/independent blind packets coincide), at most 20
requests with one frozen model/prompt and a declared cap. Reuse each blind
response for identical observations. Compare probabilities with the appropriate
exact Bayes posterior, retain parsing failures and actual usage, and stop without
prompt tuning or retries. This measures use of supplied assumptions, not actual
source calibration or independence. It remains unexecuted and separately scoped.
