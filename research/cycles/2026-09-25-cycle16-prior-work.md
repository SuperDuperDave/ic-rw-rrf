# Cycle16 — prior work and the information value of R19

Prepared 2026-09-25 against checkpoint `19139bd`; literature review only.
No retrieval experiment, acquisition, collection selection, or tuning was done.
The question comes from the [cycle15 report](../../results/cycle15-2026-09-12/REPORT.md)
and [review integration](2026-09-12-cycle15-review-integration.md).

**Recommendation:** retain C−B as a small prospective weighting diagnostic if its
answer will determine whether to retain the four-list lexical apparatus. Do not
present C as a new fusion method or an identified correction for dependence.
There is close prior art for both source weighting and balancing unequal numbers
of runs. Preparation can stop with that narrower contract; novelty does not
justify a larger experiment.

Four primary sources were checked directly, including the cited method sections:

1. **Cormack, Clarke and Büttcher (2009), “Reciprocal Rank Fusion outperforms
   Condorcet and individual Rank Learning Methods,” SIGIR, pp. 758–759.**
   Section 1 defines the sum of `1/(k + rank)` and says k=60 was chosen in pilot
   work before subsequent validation. Section 2 emphasizes ignoring arbitrary
   source-score scales. The paper reports empirical effectiveness, not a theorem
   of superiority or independence. Its pilot ensemble already combines multiple
   configurations of one search engine, so using related systems is not itself a
   new research setting. [Author-hosted full paper](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf).

2. **Bendersky, Zhuang, Ma, Han, Hall and McDonald (2020), “RRF102: Meeting
   the TREC-COVID Challenge with a 100+ Runs Ensemble,” arXiv:2010.00200v1.**
   Sections 3.1–3.4 partition runs by originating system to limit domination by
   unequal run counts. They fuse within groups, then apply weighted RRF to the
   resulting *group rankings*, giving greater weight to systems using prior
   judgments. This directly anticipates group balancing and provenance-based
   weighting. C instead averages the original reciprocal contributions without
   re-ranking the aggregate; the paper does not establish C’s benefit here.
   [Full paper, equations 1–3, printed p. 4](https://arxiv.org/pdf/2010.00200).

3. **Bruch, Gai and Ingber, “An Analysis of Fusion Functions for Hybrid
   Retrieval,” arXiv:2210.11934v2 (2023; journal DOI 10.1145/3596512).**
   Sections 4–5 compare normalized-score convex combination with RRF, examining
   both parameter sensitivity and information lost by replacing scores with
   ranks. Lemma 4.2 establishes per-query equivalence between appropriate
   weights under min-max and z-score normalization; collection-wide equivalence
   needs additional conditions in Theorem 4.5. This does not mean one fixed
   weight makes all normalizations interchangeable. Crucially, Section 3.1
   computes missing scores over the candidate union, and Section 5.1 derives
   ranks there. Our absent-list contribution of zero has different semantics.
   The methods support normalized-score fusion as an established alternative,
   but their comparative outcomes are not directly transferable to our cached,
   truncated lists. [Full text](https://arxiv.org/html/2210.11934v2).

4. **Hermosillo-Valadez et al. (2022), “Exploiting Hierarchical Dependence
   Structures for Unsupervised Rank Fusion in Information Retrieval,”
   arXiv:2208.05574v1; DOI 10.1007/s10844-022-00751-3.** Sections 3–4 build
   nested nonlinear fusion functions inspired by copulas. Kendall’s tau measures
   output concordance, while query-document matching and rank consistency affect
   document-specific parameters. The authors distinguish formal copulas from
   relaxed function compositions. This is prior work on explicitly modeled
   dependence; declaring four lists “lexical” supplies none of those estimates.
   Rank concordance also should not be silently substituted for shared relevance
   errors or verified copying. [Full text, equations 8 and 12–17](https://arxiv.org/html/2208.05574v1).

The exact information supplied by C is easy to state. Let `u_i(d)` be
`1/(60 + rank_i(d))`, or zero when absent. With `L=sum_i u_i` for the four
lexical lists and `s=u_S`, B scores `L+s`, while C scores `L/4+s`. Consequently
`4C=L+4s`: C’s ranking is equally describable as quadrupling S’s weight.
Equivalently, normalizing overall weights changes the mixture of the lexical
mean and S from 80:20 to 50:50. This is algebra, not an empirical mechanism.
“Lexical family” is a declared grouping; SPLADE itself has a sparse lexical
representation, so the grouping should name the four local scorers explicitly.

A positive C−B identifies the benefit of this fixed relative-weight change on
the chosen finite panel. It does not discriminate “too many correlated lexical
votes” from “S deserves more weight.” C−S and C−H answer the separate practical
question of whether the apparatus improves on simpler references. A null or
negative C−B ends this weight configuration without diagnosing content or depth.
Freeze source lists, candidate access, k, ties, cohort and binary nDCG@10 before
the new evaluation; current SciFact is development evidence.

The earlier [cycle01 result](../../results/cycle01-2026-09-10/REPORT.md) proved
that k tuning cannot guarantee exact-copy invariance and verified a duplicate
quotient. Family averaging is different: duplicating every family member leaves
its mean unchanged, but duplicating one unequal member generally changes it.
Neither that structural fact nor exact-copy invariance establishes relevance
quality or models dependence among these four distinct scorers.

**One discriminating alternative:** compare C with D=`RRF_k60(rank(L), S)`,
retaining the entire lexical union and the same ties. This applies RRF102’s
hierarchy to two groups. Both preserve lexical aggregate order but transform
its score gaps differently before outer fusion. D−C tests that transformation’s
effect beyond fixed family weighting; it cannot identify copying or correlated
errors. Choose it only as a separate explicit question, not an automatic extra
arm or a search after C fails.

Scope limitation: this bounded search is not exhaustive novelty clearance.
Methods-focused browser requests inadvertently included neighboring benchmark
tables, exposing this worker to published collection outcomes. No such scores
are reproduced or used to recommend a collection; prospective collection choice
must remain with an unexposed owner under outcome-independent criteria.
