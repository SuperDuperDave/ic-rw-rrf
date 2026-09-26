# Cycle18 — different outputs versus repeated weighting

2026-09-25. Bounded independent mathematical design scout for R21. This note
uses the completed [Cycle17 report](../../results/cycle17-2026-09-25/REPORT.md),
its [protocol](2026-09-25-cycle17-exchange-protocol.md), the
[Cycle16 weight geometry](2026-09-25-cycle16-weight-geometry.md), and existing
[source metadata](2026-09-25-cycle17-input-feasibility.md). No new run bodies,
comparative outcomes, labels, provider calls, or experiments were acquired or
executed. The proposed diagnostics below are not measured findings or a frozen
execution protocol.

## What the three configurations identify

For one query, let a, b, t and s be the retained-100 reciprocal-rank contribution
vectors of BITEM_BL, BITEM_df, BITEM_stem and BioinfoUA-emb. A present document at
canonical one-based rank r contributes 1/(60+r); an absent document contributes
zero. Use one document-ID namespace and extend all vectors by zero over
U = A100 union B100 union T100 union S100. Then

```
H = a + s
C = 3a + s
V = a + b + t + s
C - H = 2a
V - C = (b - a) + (t - a).
```

These are score-vector identities, not identities between P@10 values. A
positive score change can still lower a document's rank relative to competitors.

**C versus H** is a fixed coefficient intervention, holding the two underlying
lists, their ranks and their effective candidate union U0 = A100 union S100
fixed. It asks what happens when A receives weight three instead of one. A
strict pair reversal along w*a+s, from w=1 to w=3, must favor A's pair
preference: the A and S preferences oppose, with crossing
w* = -(s(x)-s(y))/(a(x)-a(y)) between the endpoints. C−H cannot diagnose why
A deserves that weight, establish dependence, or add independent information.
Its empirical value here is a matched control, not a new mathematical question.

**V versus C** replaces two literal A contribution vectors with the two named
variants. It holds the count and coefficients of lexical contributions fixed.
When every retained list has exactly 100 documents, it also holds their total
score mass fixed: each list contributes sum(r=1..100) 1/(60+r). Validate depths
before claiming that stronger match; permitting shorter lists changes mass.

The replacement can change candidate availability, repeated support for existing
documents, ranks on shared support, and the resulting displacement costs. It
measures the finite-panel value of these particular different outputs relative
to literal copies. It does not isolate statistical independence, diversity as
a latent quality, stemming as a causal treatment, or additional retrieval work
at equal compute cost. The archived pipelines can differ in several ways and
the available runs do not randomize those ways.

The comparison is not redundant with the clone theorem: the theorem determines
what copies do to coefficients; it cannot determine the relevance or rank
contributions of the unopened variants. The distinct empirical question is
whether these fixed replacements change useful output beyond the copy control.
The same 30 previously evaluated queries remain a development panel.

## An exact contribution ledger, without another evaluated arm

For each variant j in {b,t}, partition its change from A at every document:

```
rank_j(d)    = (j(d)-a(d)) if d is in A100 intersect J100, else 0
arrival_j(d) = j(d)        if d is in J100 minus A100, else 0
exit_j(d)    = -a(d)       if d is in A100 minus J100, else 0
j(d)-a(d)   = rank_j(d) + arrival_j(d) + exit_j(d).
```

Sum both variants to reconstruct V−C exactly. Record all terms and their support
counts before labels. An arrival here is new support relative to A's retained
100, not necessarily a new candidate: it may already occur in S100. Distinguish
that case from a document outside U0, which truly expands the original candidate
union. Retained-list departure also does not mean absence from a full submission
or from the corpus. Keep those notions separate in the ledger.

This decomposition identifies which observed rank/support changes produce a
score difference. It does not uniquely allocate a P@10 difference to rank versus
coverage: the top-10 operation is nonlinear, and both terms can be necessary
for one crossing. Adding separate performance effects of rank and coverage
would require specified counterfactual rankings and an intervention order.

For effectiveness, cancel shared head documents first, then record V admissions
and C displacements with their exact binary grades or unknown status. Cycle17
already supplies the reason: a relevant admission can replace another relevant
document and create no benefit. Use the same signed-coefficient bounds; do not
credit arrivals without accounting for displaced documents.

## A useful falsifier: distinct outputs can escape every fixed A weight

The strongest simple null is not merely V=C. It is:

> There exists one finite nonnegative scalar w, common to all 30 queries, for which
> w*a+s reproduces every query's V top-10 document set.

This tests representability of the displayed document sets. It does not fit a
weight for use, select an effective system, or score a weight grid. Test the null
analytically once, using rank contributions and V's fixed heads only, before
reading their labels. P@10 depends on membership, so matching the internal order
of a head is unnecessary and would test a different, stronger null.

For this diagnostic the fixed candidate set is U0 = A100 union S100; it does not
expand with the variants or change with w. If V admits any document outside U0,
record a coverage failure before constructing inequalities: that document has
zero contribution under every w*a+s, while the 100 S documents have positive
contribution. Otherwise, for every admitted x and excluded y in U0 require

```
w * (a(x)-a(y)) >= s(y)-s(x).
```

Equality is allowed precisely when x precedes y under the fixed ascending
document-ID tie rule; otherwise the inequality is strict. Each nonzero slope
gives a rational lower or upper bound on w. A zero slope either imposes no bound
or makes the constraint impossible. Intersect these bounds with w>=0, first per
query and then across all 30 queries, preserving open/closed endpoints. An
unbounded interval can contain finite weights; positive infinity is never an
admissible weight. Report each query's full feasible interval separately from
the global intersection, with the inequalities defining its boundaries. The
computation is finite and label-free; it requires no search over candidate
weights. Save intervals, feasibility and defining boundary witnesses, not a
chosen w or its effectiveness. This is a diagnostic of a predeclared family, not a new
fourth retrieval configuration.

**Surprising falsifier:** V may have no new candidate in its head and still have
an empty feasible interval. A particularly legible witness is an admitted x and
excluded y for which a(y)>a(x) and s(y)>s(x). Every nonnegative weighting of A
and S strictly prefers y, yet the additional output vectors make V admit x.
This disproves a scalar A-weight explanation of that boundary even without any
new candidate coverage. Whether x is better than y remains a label question.

If each query is individually feasible but the global intersection is empty,
the conclusion is only that no *single common weight* reproduces the panel.
It does not exclude a query-dependent weight rule, and no such rule should be
fitted here. If the global intersection is nonempty, all V P@10 outcomes are
reproducible by that scalar family for every relevance completion. That weakens
a claim of necessary new output capacity at this cutoff, but it does not prove
the actual pipelines used that mechanism or that their full rankings coincide.
Different score vectors can induce the same head sets.

Use exact rational rank contributions for this diagnostic. Preserve the
declared computed-score policy and ties rather than silently replacing its
rankings: independently audit any computed-versus-rational ordering discrepancy
before asserting an exact geometric witness. The diagnostic's null and its
arithmetic must be stated explicitly.

## What a fixed coverage counterfactual could add

If a later protocol needs to isolate candidate availability more directly,
define V0 by ranking only U0 with the **unchanged V scores**. Preserve every
original source rank and contribution; do not remove documents from source
lists and renumber them. V0 holds all within-U0 variant support and rank effects
fixed while removing candidates outside U0. Then, for every label completion,

```
P@10(V) - P@10(C)
  = [P@10(V) - P@10(V0)] + [P@10(V0) - P@10(C)].
```

The first term is the effect of admitting the new candidate pool under those
fixed scores. The second is the effect of changed contributions on the old
candidate pool. If V's head contains no new candidate, the first term is exactly
zero for every completion. This can rule out new candidate admission as the
source of a gain, while leaving changed support and ordering as explanations.

This is a specified algebraic intervention, not a causal estimate of independent
information. New candidates may already have pushed old documents down in the
variants' original source ranks; that consequence remains in V0. Reversing the
intervention order can allocate interactions differently. Moreover, the two
performance terms share unknown labels: their marginal sharp interval endpoints
cannot generally be added to recover the sharp V−C interval. Compute V−C from
its own cancelled coefficient vector.

R21 currently promises exactly three configurations. Prefer the contribution
ledger and scalar-feasibility falsifier for this cycle. Do not quietly introduce
V0 as a fourth scored arm; adopt it only through an explicit prospective scope
decision before opening the new bodies. It is not needed to interpret the
three-arm primary contrast responsibly.

## Bounded recommendation for the coordinator

Freeze one experiment with the metadata-selected tuple, all 30 queries, depth
100, one-based k60 and declared ties. The primary hypothesis is positive mean
binary P@10 V−C; the comparator is literal-copy C. Under missing labels, lower
bound >0 supports that finite contrast, upper bound <=0 excludes positive gain,
and all other cases remain unresolved. Preserve V−H and V−S as fixed usefulness
references and C−H as the explicit weighting control. No best member is selected.

The proposed distinguishing structural prediction is that V's heads are not
jointly representable by a single nonnegative A weight; its failure is a useful
negative about output capacity at cutoff 10, not a reason to change sources or
weights. That prediction is separate from the performance prediction: escaping
the scalar family can help, harm, or make no relevance difference.

Freeze the candidate observation scope as U for every query before consulting
qrels. Use the declared raw Round1 judgment file and missing-label convention;
do not inherit Cycle17's narrower A100 union S100 label filter for new variant
candidates. The two previously observed outside-inventory record removals do
not justify another unqualified global addition-only claim. A single declared
judgment snapshot avoids reopening that already failed contract.

Stop after the three fixed configurations, exact direct contrast bounds,
contribution ledger, optional predeclared feasibility diagnostic, independent
reconstruction, and assessment. Empty head changes, a weight-representable V,
or inconclusive bounds do not authorize a replacement pair, depth sweep,
query subset, weight grid, or new rescue rule. A gain over C alone supports the
replacement relative to repetition; practical value beyond the already useful
simple alternatives still requires their direct comparisons. Any promotion
beyond this reused panel needs separate untouched evaluation.

No operational friction or local workflow change was identified (DROP).
