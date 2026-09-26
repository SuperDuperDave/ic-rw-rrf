# Cycle18 — different outputs at a fixed family weight

Status: frozen experiment completed and independently verified. The primary
comparison is unresolved; all four predeclared comparisons with standalone
sources are positive under every allowed completion of missing labels.

## The question

Cycle17 showed that a relevant admission may still be an unhelpful exchange.
This cycle changes the question: do two documented retrieval variants improve
an established hybrid when the family's total weight remains fixed?

A is BITEM_BL, D is BITEM_df, T is BITEM_stem and S is BioinfoUA-emb. For each
canonical retained source, lowercase letters denote its one-based k60 reciprocal
rank contributions. The existing hybrid is H=a+s; the new family hybrid is
F=(a+d+t)/3+s. Since H=(a+a+a)/3+s, the comparison replaces two repeated outputs
at the same coefficients. Four standalone references remain visible. No source
is chosen as best using the labels.

The primary quantity is mean binary P@10 F−H across the same 30 TREC-COVID
Round1 topics. Missing labels produce exact signed-completion bounds; they are
not assumed negative except in the separately labeled benchmark point scores.
This is development on reused topics, not untouched generalization evidence.

## A separate question about attainable rankings

Can any finite nonnegative A weight, against fixed S, reproduce F's top-ten
sets using the original candidate pool? The diagnostic solves exact head versus
nonhead inequalities. It separately reports new candidate access, impossible
per-query sets, and whether one common weight works across queries. It chooses
and evaluates no new weight.

A new attainable set need not be a better set. A synthetic common-coverage
fixture demonstrates that F can admit a document strictly below an excluded
competitor in both A and S; opposite relevance labels then make that admission
helpful or harmful. The actual experiment must measure both properties.

## Results

All quantities below are mean binary P@10 differences on the same 30 reused
development queries. Bounds allow each missing query/document judgment to be
either relevant or nonrelevant, consistently across policies. The missing-zero
point uses the conventional benchmark treatment and is not an identified effect.

| Contrast | Sharp lower | Sharp upper | Missing-zero point | Missing pairs with nonzero coefficient |
|---|---:|---:|---:|---:|
| **F−H (primary)** | **−1/100** | **1/50** | **1/50** | **9** |
| F−S | 1/60 | 1/50 | 1/60 | 1 |
| F−A | 1/30 | 31/150 | 61/300 | 52 |
| F−D | 23/150 | 47/300 | 23/150 | 1 |
| F−T | 8/75 | 29/150 | 19/100 | 26 |
| H−S | −1/300 | 3/100 | −1/300 | 10 |

The fixed family hybrid beats S by between **1⅔ and 2 percentage points** on
this panel, regardless of its one remaining missing-label value. The primary
F−H interval is **−1 to +2 percentage points**. A positive secondary comparison
does not resolve that primary question or the unchanged H−S contrast.

The conventional means are A=119/300, D=67/150, T=41/100, S=7/12,
H=29/50 and F=3/5. These are not untouched evaluation results. No significance
test, weight search, source selection or new relevance annotation was run.

F changes 46 slots across 25 queries relative to H: 29 positive and 17 negative
admissions replace 23 positive, 14 negative and 9 unjudged exits. These counts
explain the primary interval; calling every relevant admission an improvement
would ignore what it displaced.

The unknowns are coupled across contrasts. Let k be the number of positive
labels among the nine unknown H-only exits, and y the one unknown shared by
F/H but absent from S. Then F−H=(6−k)/300, H−S=(k+y−1)/300 and
F−S=(5+y)/300. The same unknown labels cancel in F−S; they have not been
resolved. An [independent check](../../_sessions/cycles/2026-09-25-cycle18-triangle-check.md)
verified these identities over all 1,024 label completions. Marginal interval
endpoints cannot be combined as if the contrasts were independent.

For **23 of 30 queries**, no finite nonnegative A weight against fixed S can
reproduce F's top-ten set. Seven queries admit a weight interval; there is no
common weight across all queries because 23 are individually infeasible. This
is a top-ten membership capability result for these fixed rank vectors and
candidate pools. It does not show that the capability caused the metric gain,
that no other fusion method could match it, or that matched sets have matched
internal order. Two queries have the stronger certificate of an included
document strictly dominated in both original A and S contributions by an
excluded document.

**Zero admissions come from outside A100∪S100.** This was established before
the new data by an [admission bound](../../_sessions/cycles/2026-09-25-cycle18-admission-bound.md):
a new-only candidate scores at most 2/183, while ten S-head candidates score
at least 1/70. The observed scalar escapes therefore occur inside the original
candidate pool. This bound is conditional on this formula and cutoff.

## Verification and reproduction

The [preflight](../../_sessions/evidence/2026-09-25-cycle18-preflight.json)
froze 24 files before fetching D/T and observing their outcomes. The two new
run files required 2,086,575 bytes in one attempt each; A/S and the exact pinned
late judgments were reused. Public acquisition receipts exclude HTTP cookies.

An [independent implementation](independent-check.json), using its own parser
and integer-scaled scores, matched every policy and analysis field, including
exact interval endpoints and the unchanged historical A/S/H heads. The pinned
NIST trec_eval [check](official-metric-check.json) matched all 180 per-query
point scores and six means to its four-decimal reporting precision. Sixty-five
targeted tests passed, including strict ties, singleton and incompatible
weight intervals, missing labels, candidate scope, and a same-pool fixture
whose capability change can help or harm under different relevance assignments.

The core commands, from the repository root, are:

```sh
python3 -B _sessions/tools/acquire_cycle18_inputs.py --phase initial --inputs _sessions/local/cycle18/inputs --preflight _sessions/evidence/2026-09-25-cycle18-preflight.json --receipt _sessions/evidence/2026-09-25-cycle18-acquisition.json
python3 -B evaluation/cycle18_family_outputs.py --preflight _sessions/evidence/2026-09-25-cycle18-preflight.json --acquisition _sessions/evidence/2026-09-25-cycle18-acquisition.json --inputs _sessions/local/cycle18/inputs --output results/cycle18-2026-09-25/run
python3 -B _sessions/tools/check_cycle18_family_outputs.py --result results/cycle18-2026-09-25/run --preflight _sessions/evidence/2026-09-25-cycle18-preflight.json --acquisition _sessions/evidence/2026-09-25-cycle18-acquisition.json --inputs _sessions/local/cycle18/inputs --output results/cycle18-2026-09-25/independent-check.json
python3 -B _sessions/tools/check_cycle18_official_metric.py --execute --expected-source-sha256 33027f0689715359586f467347450a28435da0b5aed61b589265afe327ae4739 --policies results/cycle18-2026-09-25/run/policies.json --analysis results/cycle18-2026-09-25/run/analysis.json
```

Outputs are exclusive: preserve the completed directory and use fresh output
locations for a replay. Raw inputs and the pinned external evaluation binary
are local prerequisites; the tracked manifests record identities. The public
results are inspectable without downloading raw provider or retrieval files.

## Protocol and scope

The [protocol](../../_sessions/cycles/2026-09-25-cycle18-protocol.md) fixes the
inputs, six policies, six contrasts, exact arithmetic, diagnostics and stopping
rule. The [integration](../../_sessions/cycles/2026-09-25-cycle18-integration.md)
records assessed Opus, Buddy and independent reviews. A
[primary-source positioning note](../../_sessions/cycles/2026-09-25-cycle18-prior-positioning.md)
connects the diagnostic to existing weighted-fusion and ranking-region work.
No geometric-method novelty, causal source independence or agent performance
benefit is asserted.
