# Cycle21 — independent automatic-team census review

Date: 2026-09-26. This review read the frozen protocol and its freeze receipt
before independently capturing the two allowed official metadata pages. Protocol
SHA256: `0582e59291dbc5146b8f7c3643b8a448a63db5747ad0d38cdb250131a07dc1f1`.

**Metadata feasible: 29 eligible teams, containing all 81 of their automatic
submissions.** The coordinator and independent parser agree on the full census,
archive links and team associations. This authorizes no run-body acquisition or
empirical claim: scientific-value assessment and a separate bounded data contract
remain necessary.

## Complete census and agreement

The complete [official run metadata](https://pages.nist.gov/trec-browser/trec-covid/round1/runs/)
and [archive index](https://ir.nist.gov/trec-covid/archive/archive-round1.html)
contain 143 unique run IDs from 56 teams: 100 explicitly automatic and 43 manual,
with no feedback or unspecified types. All 143 have method descriptions and
publisher MD5 values; those values are unique. The archive has exactly the same
143 IDs and 56 teams, with every run assigned to the same team. Publisher MD5s
are metadata, not locally verified identities of unopened run bodies.

`BITEM_BL` uniquely belongs to BITEM; `BioinfoUA-emb` uniquely belongs to
BioinformaticsUA. Excluding both teams removes six automatic submissions.
Thirteen remaining teams have only one automatic output, and twelve have none.
The remaining 29 groups consist of 23 triples and six pairs, totaling 81 runs.
No architecture, method similarity, published quality, or favorable outcome
selected a group or a member.

The independent JSON receipt
`_sessions/evidence/2026-09-26-cycle21-metadata-review.json` contains the full
56-team census, all 143 factual submission records and exact archive URLs,
all exclusions, normalized method hashes, constraints, and source identities.
The source pages and normalized descriptive text stay ignored locally.

## Every eligible group and its documented methods

All listed members have official type `automatic`. Descriptions below are
metadata summaries, not assertions of architectural identity or independent
errors. The source metadata is authoritative where a detail is unspecified.

| Team | All automatic members | Method summary |
| --- | --- | --- |
| BRPHJ_NLP | `BRPHJ_NLP1`, `BRPHJ_NLP2`, `BRPHJ_NLP3` | NLP1 uses sentence embeddings/FAISS followed by BM25; NLP2 omits that reranking; NLP3 uses a retriever plus BERT reader. |
| CSIROmed | `CSIROmedNIR`, `CSIROmed_PE` | PE reranks DFR results with sentence embeddings and a date filter. NIR combines neural similarities with BM25 over multiple fields and applies another date rule. |
| CincyMedIR | `CincyMedIR-run1`, `CincyMedIR-run2`, `CincyMedIR-run3` | Run1 searches query text against title/abstract with BM25. Runs2/3 search extracted concepts; run3 additionally uses question and narrative. |
| DA_IICT | `DA_IICT_all`, `DA_IICT_narr`, `DA_IICT_narr_qe` | All uses three topic fields; narr uses narrative; narr_qe adds Bo1 expansion from ten documents. All use In_expC2. |
| Elhuyar_NLP_team | `elhuyar_indri`, `elhuyar_rRnk_cbert`, `elhuyar_rRnk_sbert` | Indri passage retrieval alone, ClinicalBERT passage reranking, and SBERT/Indri combination. Document scores come from passages; training sources differ. |
| IRC | `irc_entrez`, `irc_pmc`, `irc_pubmed` | BM25 then topic-specific DRMM/GloVe reranking. Training material comes respectively from Entrez title/abstract results, PMC full text, and PubMed title/abstract results. |
| IRIT_markers | `IRIT_marked_base`, `IRIT_marked_mu_pair`, `IRIT_marked_un_pair` | All rerank title/abstract BM25+RM3 candidates with MS MARCO-trained BERT. Base omits exact-match marking; the two marked descriptions do not distinguish their variants. |
| IRLabKU | `KU_run1`, `KU_run3` | Run1 reranks BM25 by publication year. Run3 additionally uses title/abstract/paragraph indexing and BioBERT paragraph/query similarities. |
| IR_COVID19_CLE | `ir_covid19_cle_dfr`, `ir_covid19_cle_ib`, `ir_covid19_cle_lmd` | Three Lucene abstract-search runs differ by DFR, information-based similarity, or Dirichlet language modeling; metadata says each returns the first100 documents. |
| KAROTENE_SYNAPTIQ_UMBC | `ERST_NARRATIVE`, `ERST_PROSE`, `ERST_QUESTION` | All index automatically extracted document tags in Elasticsearch; NARRATIVE, PROSE, and QUESTION vary the topic fields. |
| KoreaUniversity_DMIS | `dmis-rnd1-run1`, `dmis-rnd1-run2` | Both combine DenSPI/covidAsk with Covidex document scores on a COVID-focused subset. Run1 uses question/SQuAD; run2 uses query/SQuAD+NaturalQuestions. |
| SFDC | `SFDC-23April-run1`, `SFDC-23April-run2` | Both describe semantic retrieval using generated query-paragraph training pairs and Sentence-BERT; the descriptions do not identify their difference. |
| SavantX | `savantx_nist_run_1`, `savantx_nist_run_2`, `savantx_nist_run_3` | Three entries describe the same automatic SavantX PRO workflow and unsupervised relationship model; their specific differences are not documented. |
| THUMSR | `BERT`, `Conv_KNRM`, `Meta-Conv-KNRM` | BERT and Conv_KNRM combine BM25 with neural scores using Reinfoselect training; Meta-Conv-KNRM uses meta-learning. |
| TM_IR_HITZ | `lda400s2000`, `lda400s5000`, `tm_lda400` | Two runs use400-topic LDA to form candidate subsets before BM25F; tm_lda400 ranks abstract-topic distributions by Jensen-Shannon divergence. |
| TU_Vienna | `TU_Vienna_TKL_1`, `TU_Vienna_TKL_2` | Both rerank the first100 BM25 results using TKL trained on MS MARCO document data. Bases differ: GloVe versus BERT embeddings without attention layers. |
| Technion | `Technion-JPD`, `Technion-MEDMM`, `Technion-RRF` | JPD reranks language-model candidates using passage features and INEX-trained RankSVM; MEDMM expands queries; RRF combines submitted component rankings at k60. |
| UB_BW | `CBOWexp.0`, `PL2c1.0`, `PL2c1.0_Bo1` | All use Terrier PL2 with title/abstract indexing; variants use word2vec expansion, term-dependence modeling, or Bo1 pseudo-feedback expansion. |
| UIowaS | `UIowaS_Run1`, `UIowaS_Run2`, `UIowaS_Run3` | Filtered corpus and query+narrative inputs; runs use DPH, BM25, and BM25 with query expansion respectively. |
| abccaba | `bm25_baseline`, `bm25_basline` | Both describe lowercase concatenated-text BM25. bm25_baseline additionally specifies shorter queries and correction of a previous bug; both remain separate submissions. |
| covidex | `BM25R2`, `T5R1`, `T5R3` | BM25R2 uses Anserini BM25. T5R1/T5R3 add MS MARCO-trained T5-11B; their indexed paragraph representations differ in abstract inclusion. |
| ielab | `ielab-prf`, `ielab-prf.2query.v3`, `ielab-prf.recency` | All use BM25 then pseudo-feedback; variants further change query-field composition or combine recency with relevance. |
| ixa | `ixa-ir-filter-narr`, `ixa-ir-filter-query`, `ixa-ir-filter-quest` | Whoosh/BM25F over a COVID-focused passage index; the three entries vary narrative, query, or question input. |
| sabir | `sab20.1.blind`, `sab20.1.merged`, `sab20.1.meta.docs` | SMART vector methods: JSON-only pseudo-feedback, merged metadata/JSON representation, or separately scored metadata/JSON combination. |
| smith | `smith.bm25`, `smith.ql`, `smith.rm3` | BM25, query likelihood, and RM3 over available document text; RM3 settings are explicitly described. |
| udel_fang | `udel_fang_run1`, `udel_fang_run2`, `udel_fang_run3` | F2EXP variants change indexing and topic fields; run2 adds publication-year reranking, while run3 uses axiomatic expansion and combines two indexes. |
| unipd.it | `10x10.prf.unipd.it`, `10x20.prf.unipd.it`, `base.unipd.it` | Elasticsearch title/abstract baseline and two pseudo-feedback variants using10 documents and10 versus20 expansion terms; the filter is not explained. |
| unique_ptr | `UP-cqqrnd1`, `UP-rrf5rnd1`, `UP-sdqrnd1` | Query sequential dependence, embedding-derived n-gram weighting, and an RRF combination of five component runs. |
| uogTr | `uogTrDPH_QE`, `uogTrDPH_QE_QQ`, `uogTrDPH_prox_QQ` | pyTerrier DPH variants add term proximity or Bo1 expansion and use query+question versus query+question+narrative fields. |

## Full exclusion accounting

The following entries complete the 56-team census. A manual sibling of an
eligible team's automatic runs remains excluded without removing its team:
CSIROmed, IRLabKU and KoreaUniversity_DMIS each have one such manual sibling.

| Excluded team | Automatic count | Manual count | Reason |
| --- | ---: | ---: | --- |
| BBGhelani | 0 | 2 | fewer than two explicitly automatic runs |
| BITEM | 3 | 0 | previously inspected anchor team |
| BioinformaticsUA | 3 | 0 | fixed external-source owner team |
| Factum | 1 | 0 | fewer than two explicitly automatic runs |
| GUIR_S2 | 1 | 2 | fewer than two explicitly automatic runs |
| IRIT_LSIS_FR | 0 | 2 | fewer than two explicitly automatic runs |
| NI_CCHMC | 0 | 3 | fewer than two explicitly automatic runs |
| NTU_NMLab | 1 | 2 | fewer than two explicitly automatic runs |
| OHSU | 1 | 2 | fewer than two explicitly automatic runs |
| PITTSCI | 0 | 3 | fewer than two explicitly automatic runs |
| POZNAN | 0 | 3 | fewer than two explicitly automatic runs |
| RMITB | 0 | 2 | fewer than two explicitly automatic runs |
| RUIR | 1 | 2 | fewer than two explicitly automatic runs |
| Sinequa | 1 | 1 | fewer than two explicitly automatic runs |
| Sinequa2 | 0 | 1 | fewer than two explicitly automatic runs |
| TMACC_SeTA | 1 | 0 | fewer than two explicitly automatic runs |
| UB_NLP | 1 | 0 | fewer than two explicitly automatic runs |
| UIUC_DMG | 0 | 3 | fewer than two explicitly automatic runs |
| UMASS_CIIR | 1 | 1 | fewer than two explicitly automatic runs |
| VirginiaTechHAT | 1 | 2 | fewer than two explicitly automatic runs |
| azimiv | 1 | 0 | fewer than two explicitly automatic runs |
| columbia_university_dbmi | 0 | 2 | fewer than two explicitly automatic runs |
| cord19.vespa.ai | 1 | 0 | fewer than two explicitly automatic runs |
| julielab | 1 | 2 | fewer than two explicitly automatic runs |
| tcs_ilabs_gg | 0 | 1 | fewer than two explicitly automatic runs |
| wistud | 0 | 3 | fewer than two explicitly automatic runs |
| xj4wang | 0 | 1 | fewer than two explicitly automatic runs |

## Genuine input and interpretation constraints

Eligibility based on official team/type metadata does not imply interchangeable
inputs. The descriptions identify several material constraints:

- IR_COVID19_CLE describes returning 100 documents, exactly the proposed retained
  depth. TU_Vienna describes reranking only 100 BM25 candidates. Neither fact
  establishes that all 30 actual topic lists contain 100 unique valid documents.
- CSIROmed uses publication-date filtering or score-zeroing; KoreaUniversity_DMIS,
  UIowaS and ixa restrict document sets by COVID/coronavirus string matches;
  ielab removes title-only documents. TM_IR_HITZ creates topic-dependent subsets.
- Title/abstract, concept, full-text and passage indexes coexist. sabir even varies
  metadata versus JSON access within its team. These differences must remain
  documented instead of being interpreted as pure algorithm ablations.
- KoreaUniversity_DMIS combines Covidex scores with its own system. Submitted
  outputs can themselves be fusions, including unique_ptr and Technion. Separate
  team names therefore do not certify independent origins; members are outputs,
  not necessarily primitive rankers.
- Automatic methods include pseudo-feedback, externally supervised models and
  validation-based choices. The official classification is the eligibility fact;
  it does not establish label-free development or untouched evaluation.
- SFDC and SavantX have repeated high-level descriptions, and the two marked
  IRIT descriptions do not resolve their precise implementation difference.
  Distinct documented IDs and MD5 values remain included under the frozen rule.
- `bm25_baseline` and `bm25_basline` are distinct abccaba entries. The former
  describes a bug correction and shorter query input. Both have unique IDs,
  distinct publisher MD5s and separate archive entries: no near-name deduplication
  or retrospective removal is justified by this census.

No individual run byte lengths are published in these two pages. All 81 are
below the prospective **run-count** cap of 180, but transferred/expanded-size
feasibility is unknown. Any later acquisition must impose the frozen streaming
limits, and must check source/topic coverage before metrics. Missing sizes are
not a reason to sample convenient teams or silently drop a member.

## Independent capture identity and parser fidelity

Two complete pages were independently fetched once each, with 60-second timeouts
and an 8 MiB page cap. Their combined 1,641,195 bytes are below the 24 MiB total
cap. Retrievals occurred at 04:27:37 UTC on September 26, 2026. Both returned
HTTP 200. Safe header subsets, byte counts, timestamps and complete SHA256s are
in the receipt; no cookies or raw runtime header collections are published.

| Page | Bytes | Reviewer capture SHA256 |
| --- | ---: | --- |
| Run metadata | 1,616,385 | `06230b0c788bc2908cbce20e7e92b08a75431765a6b25b0dfb88f8a8bd8c560f` |
| Archive index | 24,810 | `526d5b349dfe6be8b4d814ed95274ec797cf6bd0eaa604014948aa6059e9f972` |

The coordinator's raw hashes differ. Removing script blocks makes both pairs
of complete captures byte-identical. The resulting hashes are
`532b8745183e969c9c0c9dc8f520dc592b90c4a89d4606fce0649f227b893c10`
for run metadata and
`79739ad8af73a8f2e770fbe65c2437b79b559fd71513289d5947e4be01a8c46d`
for the archive. Thus the differences are in runtime script content, not the
team/method/archive records. Script values were neither printed nor published.

The independent parser used HTML event handling for the run sections and nested
archive team lists, retaining literal angle-bracketed field names. Review caught
that generic tag removal in the coordinator's unfrozen parser dropped some
literal query/question/narrative/text field names. The coordinator corrected
that descriptive-text normalization before finalizing this census. Three IRC
method strings also differ in whitespace before a colon. These presentation
issues did not affect any ID, type, ownership, MD5, archive URL or eligible set;
the complete raw source hashes remain the authoritative record.

## Exposure, limits and disposition

No new run, qrel, topic, document-inventory, corpus or performance-report body
was opened. While reviewing method descriptions, one SBERT entry incidentally
stated an external STSbenchmark result; generic effectiveness claims and
optimization criteria also occur in method prose/references. No TREC-COVID
run effectiveness or document judgment was seen or used for selection.

The existing quartet's outcomes and the reused 30-query setting were already
known. Census breadth does not create new labeled query units, population
representativeness, or a performance replication. This review establishes an
explicit complete input frame, not that the proposed grouped-output comparison
will be informative or favorable. Buddy's substantive assessment and a separate
execution freeze remain distinct from metadata feasibility.

No material census discrepancy remains. Stop this review at the 29-team,
81-run metadata result; no body acquisition follows automatically.
