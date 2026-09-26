# Cycle17 — a relevant admission can still be an unhelpful exchange

On this fixed 30-query TREC-COVID panel, the tested minority-priority exchange
cannot improve mean binary P@10 over the simple hybrid under any allowed
completion of the early missing labels. It trails the generic one-slot policy
by exactly 1/300. This is a local policy result, not a rejection of useful
minority evidence or a new fusion method.

## The question and fixed experiment

Could a single high-ranked result from one source, absent from the other
source's retained list, improve a hybrid that displays none of those results?
The pair was selected using public method/access metadata: A=`BITEM_BL`, an
Elasticsearch baseline, and S=`BioinfoUA-emb`, BM25 plus biomedical neural
reranking. These are archived submitted runs, not new model inference. All 30
Round 1 queries are included. The collection is a retrospective convenience
panel with disclosed prior published-outcome exposure.

Full source lists have 1,000 results/query. Canonical ordering uses exact numeric
scores and document-ID ties; retain 100 per source. H is equal-weight, one-based
k60 RRF. If H10 contains no S-only result but S10 does, M replaces H's tenth
result with the highest S-ranked such candidate. J uses the same trigger and
slot, choosing the highest S-ranked candidate outside H10 regardless of A
support. Otherwise M=J=H. A and S alone are fixed references.

“S-only” means absent from A's retained 100, not necessarily its full submission.
Three M admissions occur at full A ranks 132, 200 and 323; eight are absent from
A's full 1,000. Different ranks and document content prevent M−J from isolating
a causal effect of minority status. The [protocol](../../_sessions/cycles/2026-09-25-cycle17-exchange-protocol.md)
owns the hypothesis, five contrasts, exact bounds and stops; the
[metadata note](../../_sessions/cycles/2026-09-25-cycle17-input-feasibility.md)
records selection, source definitions and access. Its larger family proposal
was narrowed to the two-run experiment before acquisition.

## Loop 1: admission value includes displacement

Eleven queries trigger; M and J are identical on 10 of 11. All 19 other queries
remain unchanged and contribute zero to the primary mean.

| Exchange observation | M: minority priority | J: generic S priority |
| --- | ---: | ---: |
| Known-positive admissions | 7 | 8 |
| Known-negative admissions | 4 | 3 |
| Known-positive displacements | 7 | 7 |
| Rescue: positive replaces known negative | 1 | 1 |
| Harm: known negative replaces positive | 2 | 1 |
| Neutral: both known with same binary relevance | 7 | 8 |
| Unresolved: an exchange label is missing | 1 | 1 |

Thus seven successful positive admissions do not establish improvement. Five
of M's neutral exchanges replace a positive with another positive; its two
remaining neutral exchanges replace negatives with negatives. On query 30, M
chooses a negative at S rank 8, while J chooses a positive at S rank 6 that A
retains at rank 100. They displace the same positive incumbent. This one query
accounts for their exact difference; it is not independent multi-query evidence
for a universal priority rule.

The unresolved query 7 admits a known positive and removes an unjudged incumbent.
It can add at most one relevant result, offsetting M's already observed net loss
of one on the other eligible queries. Therefore positive mean improvement is
already excluded, even though strict loss versus equality remains unresolved.

| Fixed contrast | Early sharp interval in P@10 units | Unknown-zero point |
| --- | --- | ---: |
| **M−H, primary** | **[−1/300, 0]** | 0 |
| M−J | [−1/300, −1/300] | −1/300 |
| M−S | [−7/60, 13/150] | −1/300 |
| H−S | [−7/60, 9/100] | −1/300 |
| H−A | [−23/300, 37/150] | 16/75 |

Multiply by 100 for percentage points: primary [−0.3333,0]. Bounds are exact
finite-panel missing-label bounds, **not confidence intervals**. Shared documents
cancel before unknown labels are assigned opposite extremes according to signed
coefficients. Grade 0 is an explicit negative; grades 1/2 are binary positives;
absent judgments remain unknown. No p-values or population claims are made.

Conventional unjudged-zero means are A=.336667, H=M=.550000, S=J=.553333.
These point scores are a benchmark convention, not estimates that unjudged
documents are truly irrelevant. The source/reference comparisons have broad
missing-label intervals. [Full early result and exchange ledger](final/early/analysis.json).

## Loop 2: the global preservation gate actually failed

After the early artifacts were complete and sealed, we acquired the predeclared
chronological Round1 judgments. All 8,689 in-inventory early records retain their
exact grades. Two outside-inventory records—topic 2/`ccq171wm` and
topic 20/`iu0k7rqc`, both grade 0—are removed. They are outside every frozen
candidate set and have zero coefficient in every comparison.

The original protocol nevertheless required **every** early record to survive.
Its second phase stopped and produced no late scores. Preserve that failed
global contract; it is not a successful addition-only replication.
[Exact mismatch ledger](final/late/label-preservation.json),
[failure artifact](final/late/failure.json).

## Follow-up: more observations settle one comparison, leave another open

After assessing that failure with Opus, we froze a separate **post hoc**
[candidate-scope observation](../../_sessions/cycles/2026-09-25-cycle17-candidate-revelation-protocol.md).
Its scope is each query's already saved A100∪S100. Every policy fits inside it;
the two removed global records are outside it. All early labels **inside this
scope** are preserved exactly, and all early analysis fields match the original
result except the explicitly scoped label count. Every ranking byte is unchanged.

The scope contains 1,848 early and 2,918 later judgments: **1,070 new labels**.
The full source files contain 8,691 and 21,545 records, respectively; those are
separate global counts, including the recorded two removals. No new label was
fabricated or obtained from a model.

| Fixed contrast | Later sharp interval | New labels on its nonzero support | Conclusion |
| --- | --- | ---: | --- |
| M−H | [−1/300, 0] | 0 | Positive improvement remains excluded |
| M−J | [−1/300, −1/300] | 0 | Minority priority remains worse here |
| M−S | [−1/300, 2/75] | 52 | Sign remains unresolved |
| **H−S** | **[−1/300, 3/100]** | **52** | Narrower; sign remains unresolved |
| H−A | [1/25, 19/100] | 52 | Every allowed completion favors H |

The new observation's predicted H−S width reduction occurs: 31/150→1/30,
a reduction of 13/75. The same reduction occurs for M−S and H−A. Their label
supports overlap; **52 per comparison is not 156 independent new judgments**.
The added observations establish at least **4 percentage points** of hybrid
advantage over A on this fixed panel. They do not establish an advantage over S.
Nothing new was learned about the primary slot-exchange outcome: its one
unresolved incumbent remains unjudged.

Later conventional unjudged-zero means are A=.396667, H=M=.580000,
S=J=.583333. H−S's point estimate stays −1/300 while its uncertainty narrows.
This shows why changes in observation and changes in effectiveness are different.
[Full late result](candidate-revelation/late.json),
[label influence and interval changes](candidate-revelation/revelation.json),
[scope and global-removal proof](candidate-revelation/scope.json).

Exactly ten residual H−S unknown query/document pairs, spanning nine topics,
remain, all with positive coefficients. If k of those ten are relevant, the
finite-panel mean difference is exactly `(k−1)/300`: zero relevant gives a small
loss, one equality, two or more a gain. This algebra does not say which labels
are likely, supply independent samples, or justify inventing relevance grades.
It identifies what evidence could settle the remaining comparison.
[The ten residual units and exact decision relation](residual-labels.json)
remain available without assigning them fabricated grades.

## Input compatibility and evidence integrity

Before the completed analysis, three narrow input gates stopped. Separate
amendments and implementations preserved every failure and original source:

1. The official ID inventory contains 51,103 lines but 51,070 distinct full-line
   strings, with 33 exact repeats and 25 multiword entries. The corrected reader
   treats whole printable lines as opaque keys; it never splits words into IDs.
2. A's unused submitted-rank column is 0–999; S's is 1–1000. We permit and preserve
   nonnegative submitted metadata while canonical score/RRF ranks stay one-based.
3. Two early judgments are outside the inventory. Retain those literal records
   without expanding retrieval candidates; all other qrel gates remain intact.

The final policy artifact is byte-identical to the successful preparation before
the qrel correction: SHA256
`888b101919af30f36bc1d12d15c3c7c028bb42a017d71c417cf5bd02360a14cd`.
No query, candidate, source, grade, parameter or policy was selected in response
to an effectiveness result. [Policy-preservation receipt](../../_sessions/evidence/2026-09-25-cycle17-policy-preservation.json).
The [ID](../../_sessions/cycles/2026-09-25-cycle17-docids-correction.md),
[rank-column](../../_sessions/cycles/2026-09-25-cycle17-rank-column-correction.md)
and [qrel-scope](../../_sessions/cycles/2026-09-25-cycle17-qrel-scope-correction.md)
amendments record the exact changes.

Raw runs/qrels and HTTP logs stay local. Original header receipts containing
transient response cookies are ignored and preserved unchanged; public copies
omit those headers while retaining input identities and original receipt hashes.
Full historical runtime-custody replay requires the local original receipts.
The public result contains numeric rankings, labels and exact derived quantities,
not article text, credentials or provider transcripts.

## Verification and reproduction

All 48 targeted synthetic tests pass, including exhaustive 81 partial-label tables
and 256 completions, Decimal score ties, eligibility/control cases, no policy
rebuilding, label-scope invariance and preserved failure conditions. The
standard-library demo also completes. These tests do not validate medical facts
or a general ranking advantage.

The [early independent audit](checkpoint-audit.json) reconstructs every policy,
query, exchange and aggregate, and the failed global preservation check. The
[follow-up audit](candidate-revelation/independent-check.json) independently
reconstructs every scoped early/late/revelation field. Integer-denominator RRF
ordering agrees with protocol floating ordering on all 30 queries. Every
per-query and aggregate late interval nests inside its early counterpart.

The pinned NIST evaluator independently matches **all 300 query scores and 10
means** across the two measured phases; the
[early](early-official-metric-check.json) and
[later](candidate-official-metric-check.json) receipts use full raw qrels and
rank-preserving exports. These checks validate the unjudged-zero precision
convention, not the truth of missing relevance labels.

Exact successful commands (run from repository root; output directories are
exclusive, so preserve existing artifacts before a deliberately separate replay):

```sh
python3 -B evaluation/cycle17_scoped_labels.py prepare --inputs _sessions/local/cycle17/inputs --acquisition _sessions/evidence/2026-09-25-cycle17-scoped-initial-acquisition.json --output results/cycle17-2026-09-25/final/prepared
python3 -B evaluation/cycle17_scoped_labels.py early --prepared results/cycle17-2026-09-25/final/prepared --output results/cycle17-2026-09-25/final/early
python3 -B evaluation/cycle17_candidate_revelation.py --preflight _sessions/evidence/2026-09-25-cycle17-candidate-preflight.json --output results/cycle17-2026-09-25/candidate-revelation
python3 -B _sessions/tools/check_cycle17_checkpoint.py --public-custody --output /tmp/cycle17-public-checkpoint-replay.json
python3 -B _sessions/tools/check_cycle17_candidate_revelation.py --public-custody --output /tmp/cycle17-public-candidate-replay.json
```

The [input plan](../../_sessions/cycles/2026-09-25-cycle17-input-plan.json),
[public initial receipt](../../_sessions/evidence/2026-09-25-cycle17-initial-acquisition-public.json)
and [late receipt](../../_sessions/evidence/2026-09-25-cycle17-late-acquisition.json)
pin all five downloaded files (3,497,301 bytes total). Both public numerical
replay modes were exercised successfully using these cached bytes; fresh
checkouts must first acquire the exact hash-matching public inputs. Public mode
checks sanitized identity statements instead of requiring private cookie-bearing
receipt bytes. Complete original producer-custody replay additionally needs
those local originals, as stated above.

Buddy's assessed critique was returned to the same Opus 5.5/high coordinator
alongside actual measurements. The [integration](../../_sessions/cycles/2026-09-25-cycle17-integration.md)
distinguishes useful proposals from corrected mathematical and causal claims.
Collaborator reviews are not additional numerical replications or proof that a
multiagent workflow beats a single researcher.

The measured cycle ends here. The next proposed value check distinguishes
repeating A's vote from adding the documented related BITEM variants at the same
vote count, with standalone S and the original hybrid retained as references.
No additional source body, priority rule, depth sweep or label purchase has
followed this result. [R21](../../_sessions/PLANNING.md) owns that bounded proposal.

## Sources and limits

[NIST Round 1 rules](https://ir.nist.gov/trec-covid/round1.html),
[run method metadata](https://pages.nist.gov/trec-browser/trec-covid/round1/runs/),
[archive](https://ir.nist.gov/trec-covid/archive/archive-round1.html) and
[judgment definitions](https://ir.nist.gov/trec-covid/data.html) supply the
public inputs and their intended semantics. No unrestricted run-redistribution
license or new algorithmic novelty is inferred. NIST already studied extended
judgment pools. Later grades may concern changed document content despite
official Round 1 mapping; all label conclusions are conditional on that mapping.

The same 30 queries reused across policies or observation phases are not new
independent samples. Known neural/lexical provenance does not identify error
dependence. This experiment measures a fixed output policy and its displacement
cost; it does not establish clinical utility, source independence, general
superiority or multiagent performance benefits.
