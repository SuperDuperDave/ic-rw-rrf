# Cycle22 — fixed submission-group fusion versus a uniform member hybrid

Status: final experiment contract, effective when the passed preflight records
its hash. No new empirical run body has been acquired at contract finalization.
The preflight freezes this protocol, plan, producer, tests, acquisition tool and
independent checker before actual acquisition. Cycle21's assessed Buddy → Opus loop selects
one experiment; no further provider approval is required. Preserve all frozen
earlier cycles and the closed BITEM quartet stop.

## Hypothesis and information value

On the complete metadata-defined frame of29other teams and81automatic Round1
submissions, equally averaging a team's reciprocal-rank contributions at total
coefficient weight one, plus the fixed S source at weight one, has higher mean
binary P@10 than uniformly choosing one of that team's members and combining
it with S. The prediction is a strictly positive sharp lower bound for the
equally team/query-weighted primary contrast. This is a finite developmental
comparison using new outputs on the same30reused queries, not population
inference, dependence identification, exact-family replication or novel fusion.

Positive primary evidence justifies considering a separately frozen fresh-topic
test of this exact grouping/comparator rule using the documented Round2 S route;
it does not authorize changing to a S-free comparison or guarantee transfer
feasibility. Nonpositive upper excludes positive benefit on this panel (zero is
not a loss); unresolved means the sign is not identified. Either closes further
investment in this specified route absent a genuinely new question. Report G−S
as a separate contextual practical reference: a simpler source dominating would
weaken practical investment despite a positive primary. No contextual result
rescues a failed primary. No parameter/source/family/member sweep or new judging.

## Frozen population and input identities

Use every automatic member of all29eligible teams from the cycle21 inventory,
including all23triples and6pairs. BITEM and BioinformaticsUA are excluded by the
metadata rule; single-automatic-run teams are excluded. Preserve heterogeneous
methods, internal fusions, borrowed outputs and even identical rank vectors under
different valid run IDs. The experiment evaluates submitted outputs, not
independent primitive rankers. No quality, coverage or pool-contributor filtering.

The input plan binds the exact team/member map,81archiveURLs,publisherMD5s,
safe destination names and prior verified S/docids/qrel identities. Acquire each
required new body once. Compute SHA256 and bytes; validate publisher MD5 against
the retrieved submission representation. If a gzip representation is encountered,
record raw/expanded hashes and which representation matches the published MD5;
only a matching representation is accepted. No archive containers or redirects
outside the declared exact HTTPS origin/path. No overwrite of existing outputs.

Resource limits: max180runs (actual81),16MiB transferred per run,256MiB total;
gzip expansion max256MiB per run and1GiB total. Fetch timeout60seconds/run,
one attempt/run, overall acquisition900seconds. Enforce total remaining bytes
while streaming. A single sentinel byte may detect an oversized stream; never
read an additional full chunk past the remaining budget or store excess bytes.
Only safe Content-Type/Content-Length/ETag/Last-Modified/Content-Encoding metadata
is published. Raw bodies/HTTP/provider runtime remain ignored.

No metrics before every source identity/format check passes. A missing,
ambiguous, corrupt, oversized or invalid required source stops the attempt and
preserves its receipt; do not drop it, substitute another source or change the
contract on observed outcomes. Any subsequent corrective contract must preserve
the failed attempt and its reason explicitly.

## Canonical rankings and policies, before labels

All30query IDs1..30 must occur in each run. Official guidelines permit1..1000
documents per topic: require at least1unique valid document per query and at
most1000. Retain min(100,actual_count). This100is a cap, not a claim that every
source supplies100documents. Valid short submissions remain in the full frame;
record full and retained depths. Missing source/query pairs, duplicate query/doc
rows or out-of-inventory docIDs fail. The fixed S source already has100/query,
so every hybrid can yield ten documents regardless of shorter member lists.

Require the six-field submission syntax, expected run tag, valid query ID and
finite Decimal score. Supplied rank may be zero-based and does not determine
canonical order; accept ASCII `\+?[0-9]+` (including leading zeros), interpret
it as a nonnegative integer, and reject negative/noninteger tokens. Record
discrepancies descriptively. This syntax choice precedes any new body access.
Order by exact score
descending and document ID ascending, then assign one-based ranks. A rank r≤100
contributes1/(60+r); absent documents contribute zero. Retain the established
literal opaque document-inventory and qrel semantics. Fixed S's canonical orders
and top-ten reference must match the pinned prior verified artifact.

For team t of m_t members and query q:

    G_tq = top10[(sum_i a_tiq)/m_t + s_q]
    H_tiq = top10[a_tiq + s_q]

Tie order is ascending document ID for all fused heads. Use exact integer units
L=lcm(61,...,160): group ranking is equivalent to sum_i a_units+m_t*s_units.
No second RRF over group ranks, mean hybrid-score vectors, best member or S-free
arm. Each head has10unique documents in its actual allowed candidate union.
Source coefficient weight is fixed; available candidate sets and total score
mass can vary with submitted depth. These differences are part of the outputs
being compared, not an identified rank-alignment intervention.

Serialize all retained source orders and all29group/81member hybrid heads before
parsing/joining label values. Custody hashing may read label-file bytes earlier.
Label knowledge from earlier cycles
is disclosed; no source selection or policy depends on a new label lookup.

## Estimand, uncertainty and saved evidence

Primary: mean over teams and queries of
P10(G_tq)−mean_i P10(H_tiq). The comparator is the expected metric of uniform
member selection, not the best member, a trained selector, or the metric of
averaged member score vectors. All means weight teams equally, regardless of
having two or three members. Within each team, members are equally weighted.

For each shared (query,document) pair, calculate

    K_qd = sum_t [6 I(d in G_tq) − (6/m_t) sum_i I(d in H_tiq)]
    c_qd = K_qd / 52200, where52200=6*10*29*30.

Pool K across teams before canceling zeros and taking bounds. Given known binary
relevance grade>0, let B=sum_known c*y. Sharp bounds are

    [B + sum_unknown min(c,0), B + sum_unknown max(c,0)].

The same unknown pair has one label across all policies/teams. The same docID on
different queries has different label identities. Verify aggregate and per-query
normalization, exact zero coefficient sums, bound attainment on small fixtures,
and that global sharp width does not exceed averaged team widths. Averaging
team endpoints can be loose; within-team G−H_i endpoint averaging is sharp.
Fixed-reference G−S endpoints also average sharply. No p-values, bootstrap,
independence or population intervals are needed for this finite estimand.

Save primary global/per-query/per-team bounds, exact pair coefficients and
support grades, contextual G−S with its explicitly different comparator, and
unknown-as-zero benchmark means clearly separated from completion bounds.
Report counts of team signs descriptively, without thresholds selecting teams.
No new individual best-member or source-quality ranking is a research outcome.

## Verification and stop

Before freeze: synthetic positive/negative effects; literal-copy zero control;
cross-team missing-label cancellation; equal-team versus unequal-member
normalization; exact ties; valid short members; malformed/duplicate/nonfinite
input rejection; cookie-header filtering; byte ceilings; no label-dependent
policy construction. Use the supplied exact common-S witnesses. Time one bounded
synthetic maximum-shape run to check the declared compute cap.

After freeze: one acquisition, one producer run and one independent reconstruction.
Producer and independent checker each have300second wall caps. The checker uses
its own parser/score/bound implementation, independently verifies every retained
order and ordered head from pinned bodies, and checks every coefficient/metric
field. Reuse the established binary P@10 convention; do not claim that the new
heads were all exported to NIST unless that additional check actually occurs.

Every verified primary result ends the experiment. Preserve failures and every
bound; no chosen seed, new group definition, label purchase, dropping wide-bound
teams or follow-up same-panel optimization. Assess the measured result, return
it to Opus with the completed Buddy critique, commit/push, and continue the
standing research goal through a justified new information contract.

## Exact execution commands

From the repository root, after the preflight records a passed freeze:

```sh
python3 -B _sessions/tools/acquire_cycle22_inputs.py --inputs _sessions/local/cycle22/inputs --preflight _sessions/evidence/2026-09-26-cycle22-preflight.json --receipt _sessions/evidence/2026-09-26-cycle22-acquisition.json
python3 -B evaluation/cycle22_grouped_outputs.py --preflight _sessions/evidence/2026-09-26-cycle22-preflight.json --inputs _sessions/local/cycle22/inputs --acquisition _sessions/evidence/2026-09-26-cycle22-acquisition.json --output results/cycle22-2026-09-26/run
python3 -B _sessions/tools/check_cycle22_grouped_outputs.py --result results/cycle22-2026-09-26/run --preflight _sessions/evidence/2026-09-26-cycle22-preflight.json --inputs _sessions/local/cycle22/inputs --acquisition _sessions/evidence/2026-09-26-cycle22-acquisition.json --output results/cycle22-2026-09-26/independent-check.json
```

Outputs use exclusive creation. The acquirer enforces its 900-second wall cap;
both numerical entry points enforce their 300-second caps. No empirical retry
or changed output path is authorized merely by a failed result.
