# Cycle05 preflight clarification

Written after preparation and before any model invocation. The prepared fixture,
its reference arithmetic and the original execution-contract bytes are preserved.
This addendum is frozen with the collection runner's source manifest.

The execution contract's phrase “lower posterior approximation error with the
correct root partition” is not implied by successful supplied-model reasoning.
The distinguishing prediction is **correct posteriors in each view**, copy
invariance when lineage is known, and the correct copied/independent conflict
reversal. Perfect reasoning has zero approximation regret in both views.
Information can lower ideal expected Brier; empirical approximation error is
a separate outcome. The prepared scorer already implements that separation.

The leakage exclusion's “arm name” means **realized arm identity**. Construction
names intentionally occur in the known generative model and equal prior given
to every request. Neither actual lineage arm nor any reference answer is sent
as evaluation metadata; aware inputs receive only the root partition.

Independent preflight review checked all packet posteriors and normalized
weights in closed form. These are scientific wording corrections before data,
not changed outcomes, prompts, packet selection, weights or scoring rules.
