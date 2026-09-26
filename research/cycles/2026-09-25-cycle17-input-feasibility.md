# Cycle17 applied input feasibility — TREC-COVID Round 1

Date: 2026-09-25 America/New_York (HTTP checks crossed into September 26 UTC).
Owner: bounded Codex input-feasibility worker. Scope: primary-source metadata,
public accessibility and an observation proposal. No run body, qrels body,
selected-run effectiveness report, leaderboard, or collection score was read.
No dataset files were downloaded or experiments run by this worker.

## Decision and selection exposure

**One viable route; stop the source search here.** Use the three BITEM Round 1
submissions as the naturally arising family and `BioinfoUA-emb` as the external
source. These are four existing submitted lists, not constructed copies.
An application decision is whether a pandemic literature search should reserve
one of ten displayed results for a high-ranked neural-source document absent
from the retained union of three related lexical variants.

Selection was based on primary method and access metadata, before viewing these
runs or their outcomes. It is a nominated convenience panel, not a random sample
or a pristine collection holdout. The coordinator/literature workers already
knew RRF102's high-level TREC-COVID findings. This worker's initial broad source
search also returned incidental outcome snippets about RRF102, RMITB and a
continuous-active-learning paper, plus unrelated TREC-IS numerical results.
None describes the selected four runs' effectiveness, and none was used to
choose them. Do not advertise this collection as wholly unexposed.

The metadata-only selection path was: inspect the official Round 1 archive;
take BITEM, the first listed team with three automatic runs whose descriptions
explicitly name a shared baseline and its variants; select BioinformaticsUA
because the inspected submission description specifies biomedical neural
reranking, different input fields and a different document subset; choose its
lexicographically first run tag, `BioinfoUA-emb`. This last choice is within the
named team, not a claim that it is the first eligible neural run in the entire
archive. Freeze this exact tuple; do not swap members after seeing labels.

## Provenance and common units

The [NIST run metadata](https://pages.nist.gov/trec-browser/trec-covid/round1/runs/)
describes BITEM's automatic April 22 submissions as an Elasticsearch baseline
over documents with body text, using query, question and selected narrative
terms; `BITEM_stem` adds stemming; `BITEM_df` adds stemming and query-term
boosting using PMC document frequencies. The browser hides some angle-bracketed
field names; the raw official HTML preserves them.

Its automatic April 23 `BioinfoUA-emb` submission uses BM25 plus a DeepRank-based
neural model developed for BioASQ, question text, documents with title and
abstract, and word2vec embeddings from CORD plus PubMed. This is a documented
method/input contrast. Team identity alone does not establish error dependence,
and the neural source is not independent of lexical retrieval.

[Official Round 1 guidelines](https://ir.nist.gov/trec-covid/round1.html) define
30 topic IDs, 1–30, using the April 10, 2020 CORD-19 release. Runs contain one to
1000 rows per topic and use `cord_uid` document identifiers. Submitted rank
columns are ignored during official processing; decreasing numeric score
determines order. Fix an explicit document-ID tie rule for our replay and report
it, rather than silently relying on file order. All four lists share evaluation
topics and document identifiers, while their retrieval subsets differ. The
same guidelines announce public archiving to support research, require no login
for archive retrieval, and say the underlying CORD-19 corpus has a separate data
license. This proposal needs only IDs, ranks/scores, topics and qrels, not article
text. No explicit standalone license for contributed run files was found on
the inspected archive/data pages; do not infer unrestricted redistribution.

## Exact public access route

Links are copied from the [official archive HTML](https://ir.nist.gov/trec-covid/archive/archive-round1.html)
and [official data page](https://ir.nist.gov/trec-covid/data.html), not guessed
filenames. The following HEAD requests returned HTTP 200 without authentication.
No response advertised `Content-Encoding` for these four run objects; their
compression/content magic has not been inspected. They are extensionless files,
not `.gz` URLs.

| Input | Exact URL | Content-Length bytes | ETag |
| --- | --- | ---: | --- |
| Family baseline | https://ir.nist.gov/trec-covid/archive/round1/BITEM_BL | 1,005,528 | `"f57d8-5a49a6d58ac80"` |
| Family DF variant | https://ir.nist.gov/trec-covid/archive/round1/BITEM_df | 1,020,890 | `"f93da-5a49a6d58ac80"` |
| Family stemming variant | https://ir.nist.gov/trec-covid/archive/round1/BITEM_stem | 1,065,685 | `"1042d5-5a49a6d58ac80"` |
| External source | https://ir.nist.gov/trec-covid/archive/round1/BioinfoUA-emb | 1,529,551 | `"1756cf-5a49a6d67eec0"` |

The four advertised lengths total **4,621,654 bytes**. All run Last-Modified
headers date to May 1, 2020 (18:34:10 UTC for BITEM; 18:34:11 for the external
run). This is accessibility evidence, not a cryptographic content pin. Acquisition
must save SHA-256 hashes before parsing and preserve the original bytes.

| Companion | Exact URL | HEAD metadata |
| --- | --- | --- |
| Topics | https://ir.nist.gov/trec-covid/data/topics-rnd1.xml | 200; application/xml; ETag `W/"286c-5a333759d2e5b-gzip"` |
| Valid Round 1 IDs | https://ir.nist.gov/trec-covid/data/docids-rnd1.txt | 200; text/plain; ETag `W/"704c4-5a31f721ed920-gzip"` |
| Original Round 1 qrels link | https://ir.nist.gov/trec-covid/data/qrels-rnd1.txt | 200; text/plain; ETag `W/"24a5e-5a4b3dc4f47be-gzip"` |
| Cumulative Round 1 judgments | https://ir.nist.gov/trec-covid/data/qrels-covid_d1_j0.5-1.txt | 200; text/plain; ETag `W/"2286b-5b78ca1c1591b-gzip"` |
| Chronological Round 1 judgments | https://ir.nist.gov/trec-covid/data/qrels-covid_d1_j0.5-5.txt | 200; text/plain; ETag `W/"5817f-5b85591f9a181-gzip"` |

Companion HEAD responses did not provide Content-Length; do not convert their
ETags into asserted sizes. Original and cumulative Round 1 qrels links have
different ETags: do not assume byte identity. Freeze the cumulative Round 1 and
chronological Round 1 files as the early/later label pair before parsing either.
Their Last-Modified values are December 28, 2020 21:05:20 UTC and January 7,
2021 20:49:04 UTC, respectively. These timestamps describe hosted files, not
when assessors supplied their judgments.

The [NIST judgment documentation](https://ir.nist.gov/trec-covid/data.html)
defines grades 0 = nonrelevant, 1 = partially relevant, 2 = fully relevant.
Unjudged is distinct. `d1_j0.5-1` contains judgments through Round 1 for Round 1
IDs. `d1_j0.5-5` is chronological/total, **not a later-round cumulative file**:
it covers Round 1 topics and valid IDs judged in any round, retaining the Round
1 cumulative grade where present and otherwise the earliest later grade. NIST
forces agreement with cumulative grades despite historical rejudgment issues;
renamed documents are not necessarily mapped backward. Thus verify early-label
inclusion and grade agreement before interpreting a second pass. Round 1 needs
no residual removal. These files support partial-label bounds; actual coverage
and point identification remain unmeasured.

## Minimum proposed experiment for the coordinator to freeze

Hypothesis: one metadata-defined external source supplies high-ranked candidates
absent from all three retained family lists; a fixed one-slot intervention can
recover judged relevant items, but its net value must include the displaced
item and missing labels. This adds real submitted variants, an explicit
application cutoff, and known negative grades to the old synthetic-family panel.
It does not identify correlated errors or establish a new fusion method.

Following the coordinator's subsequent design steer, cap every input at 100,
a fixed practical fusion window rather than a cutoff selected for query counts.
Validate IDs, scores, duplicates, query completeness and tie rules before
labels. Define H as fixed k60 RRF of `BITEM_BL` and the external source. The
other two BITEM lists preserve the naturally arising family support information.
For each query find the highest
ranked external item absent from the entire retained BITEM union, only if its
external rank is at most 10. If absent from H's top10, replace H's rank10 with
that item; otherwise leave H unchanged. Call the result P. Freeze this rule and
cohort before acquisition; do not tune the source-rank cutoff from outcomes.
This remains an input worker's proposal; the coordinator's frozen protocol
controls the actual minority definition and intervention.

Matched references should include the external source alone, `BITEM_BL` alone,
and H itself. `BITEM_BL` is nominated as
the documented baseline, not selected as the best family member. The same
retained input lists are available to each relevant fusion; no comparator gets
an oracle-selected member or additional retrieval depth. A family-only RRF may
describe the starting support, but is insufficient as the sole comparator.

Use a simple primary quantity with explicit missing-label bounds: mean change
in binary relevant count among the first ten, or equivalently P@10. Set binary
relevance to one for grades 1–2 and zero for grade 0; missing labels range over
{0,1}. For the one-slot swap the per-query delta is `(y_admit-y_displace)/10`.
For arbitrary reference comparisons, cancel shared documents before bounding:
if `c_d=(1[d in P10]-1[d in Ref10])/10`, the tight label-only interval is
`sum_known(c_d*y_d) + [sum_unknown min(0,c_d), sum_unknown max(0,c_d)]`.
Average over all 30 topics, with unchanged queries contributing zero for P−H.
Do not report only triggered queries or pretend unknowns are negatives.
Report triggered-query counts, known-positive admissions, known-zero admissions,
known-positive displacement and missing-label status of each changed pair.

The same frozen P and reference rankings can then be assessed under the later
chronological file. This is an additional-label observation on the same topics,
not independent replication. Once early-grade preservation is verified, any
contraction of the exact bounds reflects new labels; widening is a bug or a
violated input assumption. Preserve both intervals and changed-item statuses.
Do not retune the intervention after the early pass.

Weakest identification assumption: the official grade is applicable to the
Round 1 query/document unit; bounds otherwise make no missing-at-random
assumption. The action comparison is deterministic on the saved panel. To turn
it into a claim about dependency mitigation, new collections, actual clinician
utility or future traffic requires assumptions this experiment does not supply.
The retrospective chronology particularly does not estimate what was knowable
to assessors at the original submission deadline. A document first judged later
may have changed since Round 1; the chronology construction cannot guarantee
the unobserved old version would receive that later grade.

Stop after this fixed four-run panel and one intervention. If there are no
eligible changes, that falsifies this panel's immediate rescue opportunity. If
the upper P−H bound is nonpositive, a positive mean admission claim is excluded
for this label contract. If intervals straddle zero, report partial
identification rather than launch a weight grid. P−H improvement alone does not
justify added complexity when the fixed simple source/family references do as
well. No significance claim is required; there are only 30 topic units.

Acquisition/compute ceiling: four runs plus the two frozen qrels files, topics and
valid IDs; 20 MiB total downloaded bytes and 120,000 run rows maximum; standard
library replay under five minutes CPU; no corpus, model inference or provider
experiment. Unexpected size, invalid units or missing full-topic runs stops the
execution for diagnosis, not a silent candidate substitution.

## Checks, friction and handoff

Read `AGENTS.md`, planning R20 and cycle16's report. Checked official archive,
method metadata, task definition and label semantics. Metadata HTTP retrieval
used curl; accessibility used `curl -sS -I -L --max-time 20 URL` (30 seconds on
the single external-run retry). No run or label body was fetched.

Friction: sandbox DNS initially prevented urllib access; permitted network
escalation then gave urllib HTTP 403, while curl read the same metadata page.
One external-run HEAD timed out and succeeded on one retry. A guessed `.gz`
HEAD returned 404 before actual links were extracted. **SUBTRACT:** use exact
archive links and curl for this acquisition, with a single bounded retry. This
is a documented workaround, not a claimed persistent network fix. **PROMOTE:**
preserve the run-sort and judgment-version distinctions in the execution
protocol. **DROP:** no broader source catalog, outcome-based source search, or
new dependence claim.

Stable handoff: this file is complete. Only this artifact is owned/edited by
the bounded worker. The coordinator owns protocol approval, acquisition,
implementation, experiment, interpretation, shared state and git checkpoint.
