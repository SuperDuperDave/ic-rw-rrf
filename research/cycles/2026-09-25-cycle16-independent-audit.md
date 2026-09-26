# Cycle16 — independent argument audit

2026-09-25 local / 2026-09-26 UTC. Bounded reviewer of the delivered
[prior-work](2026-09-25-cycle16-prior-work.md),
[geometry](2026-09-25-cycle16-weight-geometry.md),
[counterexample](2026-09-25-cycle16-weight-counterexample.md), and
[Buddy assessment](2026-09-25-cycle16-buddy-assessment.md) notes against the
[committed cycle15 report](../../results/cycle15-2026-09-12/REPORT.md).
No benchmark outcomes were computed, no provider was invoked, and no new
collection was selected.

**Verdict:** the mathematical distinctions and counterexample pass. The public
Buddy assessment fairly preserves useful advice while correcting actual claims
in the complete private reply. These results support local mathematical facts
and narrower interpretation, not methodological novelty or retrieval benefit.

## Exact checks

Both embedded Python replay blocks executed successfully. Independently, I
enumerated rank positions into integer score maps with
`Q=lcm(61,...,68)=6209288205120`, adding `weight*Q//(60+rank)`.
Multiplying all C weights by four removes fractional weights without changing
order. This avoids the replays' `Fraction` arithmetic and document-index lookup.

- Family-copy x−y margins: `−1/4290` before and `2/130845` after copying one
  member. Uniform triple replication preserves the mean; the single-member
  update identity passes for all six documents.
- Hierarchy fixture: family order `xyz`; direct C margin `−1/7812`, versus
  reranked-family margin `1/119133`. No tie explains the reversal.
- Eight-document fixture: A=`abrdefgh`, S=`draefghb`, B=`arbdefgh`,
  C=`adrebfgh`, with all within-system scores distinct. Relevant ranks are
  3, 2, 2, 3. B's r−b and r−d margins are `53/132804` and
  `1387/1906128`; C's r−d margin is `−125/7624512`.
- All three strict B/C pair reversals agree with S. Algebra independently
  gives crossing `t*=−Δs/ΔL`: a strict reversal between t=4 and t=1 requires
  opposed component preferences. This supplies no monotonicity of nDCG.

The strict inequality `log2(3)<2` establishes S>A and B>C in the fixture.
Thus endpoint superiority does not imply improvement at C, and C is no oracle
upper bound, even when the four lexical sources really are copies.

`git show 19139bdd061fd2e51e529d7411264014e0b093a3:results/cycle15-2026-09-12/REPORT.md`
matches the working file byte-for-byte; Python `hashlib.sha256` returns
`5cab12bfe23827c5a423b7943b6152ef2eb17043ff9abf8edbc78332c57db2fc`.
This verifies the cited identity, not Buddy's remote execution or the underlying
benchmark rows.

## Interpretation and source checks

A and P share upstream candidates, but A retains a union of capped rerankings;
scoring, retention, aggregation and multiplicity differ. Say **capped at 200**,
not always 200: P can contain only 66 documents. Reported missing-qrel counts
imply A260/B272/P265/S280/H278 explicit entries out of3000; the missing range
is2720–2740. These are report consistency checks, not fresh metric validation.

RRF(S,S)=2s preserves S's order exactly. Comparing it with RRF(P,S) replaces
P; RRF(P,S,S) versus RRF(P,S) is the matched copy addition. B's deficits do not
prove every lexical contribution worthless. No outside-P B top10 entries rules
out only that particular observed membership event. These corrections respond
to Buddy's actual overstatements; the assessment also credits its fixed-arm,
prospective-selection, reference-system and stopping recommendations.

Direct primary-source checks confirm [Cormack's pilot-fixed k and related
configurations](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf),
[RRF102's reranked group hierarchy and weighting](https://arxiv.org/pdf/2010.00200),
[Bruch's normalization conditions and union rescoring](https://arxiv.org/html/2210.11934v2),
and [Hermosillo-Valadez's concordance-based copula/NFC distinction](https://arxiv.org/html/2208.05574v1).
The note's distinctions are supported; this is not exhaustive novelty clearance.
Browser responses exposed neighboring published outcomes, so this reviewer
should not own an unexposed future collection choice.

## Boundary on the later census suggestion

Claude's subsequent synthesis correctly withdraws the endpoint implication,
oracle language and pooled miss-odds proposal. Its new exclusion argument needs
qualification: populated lists alone do not ensure ten candidates above the
S-only score ceiling `1/61`. Long disjoint lexical lists are a counterexample.
Ten actual competitors strictly above that ceiling suffice; equality requires
the tie contract. Zero known S-only positives at S rank≤10 leaves deeper
known positives and unjudged relevance open, and cannot establish that all gains
are reordering only. A post hoc support census can describe retained membership;
it cannot establish mechanism or authorize an escape-rule search by itself.

No durable workflow fix follows from this bounded review (DROP). No live job or
unresolved reviewer-owned edit remains after handoff.
