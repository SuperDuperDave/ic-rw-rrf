# Cycle14 — SciFact public-source feasibility audit

Date: 2026-09-11. Owner: bounded Codex source worker; coordinator owns selection,
protocol, shared state and Git checkpoint. This is prospective preparation for
R17, with no retrieval, run scoring, relevance evaluation or model invocation.

## Choice and stopping rule

SciFact was named in the worker assignment **before any external artifact or
performance inspection**: a small scientific collection outside the project's
reused MS MARCO passage panel and in the public BEIR family. The selection
criterion is domain/input feasibility, not a published or measured win. Scope
was SciFact only and at most three source families: (1) Castorini cache/producer,
(2) BEIR dataset metadata, (3) Naver model identity metadata. No performance
tables were displayed or used. Metadata listings may contain names of other
collections; those were not candidates in this selection.

Question: do immutable public artifacts support BM25 candidate access plus the
same documented SPLADE++ EnsembleDistil family used in cycle02, with enough
provenance to freeze a later comparison? Stop after locating the required
artifacts and identifying remaining pre-evaluation checks, or after the bounded
families fail. Full corpus/run acquisition, package installation, retrieval and
evaluation are outside this audit.

## Outcome

**[observed] Public, versioned SciFact top1000 caches exist for BM25 and
SPLADE++ EnsembleDistil.** Both unauthenticated HEAD requests returned HTTP200
and the expected file lengths. Together they require **995,932,483 bytes** of
JSONL transfer. Zero run/corpus/query/qrels/model body bytes were acquired.

**[supported by producer source, not yet verified on cache bodies]** The source
families search separate BEIR SciFact indexes; SPLADE is not restricted to the
BM25 candidate list. The cache's SPLADE family, index suffix and ONNX encoder
name match cycle02's documented family. An exact historical checkpoint identity
for cache generation is still unavailable.

**[conditional feasibility]** The coordinator's independent local audit says
the original four lexical sources rescore supplied MS MARCO top1000 candidates,
estimate statistics over their candidate union, and retain top200. The original
first-stage generator is unpinned; this evidence does not identify it as BM25.
The cached SciFact BM25 pool is the proposed auditable analogue. These caches
could support a mechanism-level adaptation on SciFact if the later adapter
preserves those statistics/depth semantics and validates query/text/ID
compatibility before scoring. Simply
comparing cached BM25 against BM25+SPLADE would change the four-source baseline.
Using the top100 cache would also change candidate/depth semantics; it is not a
substitute chosen to reduce transfer size. This audit establishes an available
input path, not a completed replication or generalization result.

## Castorini artifacts

Dataset: `castorini/rank_llm_data`, revision
`39db0a25a552dd2a12012df22029686bf7fdc050` — the revision already pinned in
`data/cycle02/source-selection.json`. The [dataset metadata API][cache-api]
returned no dataset-card data and exactly four case-insensitive SciFact sibling
paths. No numeric SciFact TREC sibling was listed. That observation is limited
to this dataset revision; it does not prove compact runs are unavailable
elsewhere.

| Cache path under `retrieve_results/` | Advertised bytes | LFS SHA-256 |
| --- | ---: | --- |
| `BM25/retrieve_results_scifact_top1000.jsonl` | 512,484,847 | `c407ca6ea66a3cd79b40241a5314eca3c1727ce6cdf203b4b7ec70172b49b359` |
| `SPLADE_P_P_ENSEMBLE_DISTIL/retrieve_results_scifact_top1000.jsonl` | 483,447,636 | `47f5a37a79417fc1403a0284bda265015e3c51c8a0e5fdf9ec7d54482a45b091` |
| `BM25/retrieve_results_scifact_top100.jsonl` | 54,195,908 | `17ccbed26f4dbeb2490febf02a6972b23b6b9d277b863bf3e7c7215d9569a984` |
| `SPLADE_P_P_ENSEMBLE_DISTIL/retrieve_results_scifact_top100.jsonl` | 49,172,260 | `7216ff3d8db868e2a09998d78b97019ea8eea2bb7b05a50b00a051b8486cc275` |

Primary immutable metadata: [BM25 directory][bm25-tree] and
[SPLADE directory][splade-tree]. Download endpoints are [BM25 top1000][bm25-run]
and [SPLADE top1000][splade-run]. The top100 endpoints are obtained by changing
only the terminal `top1000.jsonl` to `top100.jsonl`; they were not HEAD-checked.
The smaller pair totals 103,368,168 bytes and remains a rejected convenience
alternative for preserving original candidate access.

Both top1000 HEAD requests followed Hugging Face redirects to
`us.aws.cdn.hf.co` and returned `Content-Type: application/octet-stream`.
Their final ETags were respectively
`308c77464669aa54f1b4f07ec4a4e9d49e550f9bab04576d2f6e02c7ef669a33`
and `e7f01b158e66fa55c485c31a9e2225cde5f180d1bb507180a72fe99539f5e6f0`.
These match directory `xetHash` fields, **not** the LFS SHA-256 fields above.
Future body verification must use the published LFS hashes, not assume every
64-character ETag is a byte hash. Signed redirect query strings were not retained.

## Producer semantics and limits

Inspected RankLLM revision:
`443adf3306102f11b85945d2a277fb6aa10ea0aa`, as used in cycle02.

| Property | Source evidence | Remaining uncertainty |
| --- | --- | --- |
| Collection/index | [Index mapping][indices] selects `beir-v1.0.0-scifact.flat` for BM25 and `beir-v1.0.0-scifact.splade-pp-ed` for SPLADE | Cache does not supply its historical index-byte digest |
| Neural identity | [Retriever][retriever] selects `SpladePlusPlusEnsembleDistil`, `encoder_type="onnx"`, `min_idf=0` | Exact ONNX checkpoint bytes/version used for cache not supplied |
| Candidate access | Retriever calls each index searcher's `search(query, k=k)` independently; BM25 uses `LuceneSearcher`, SPLADE `LuceneImpactSearcher` | Cache content and completeness not yet checked |
| Query split | [Topics mapping][topics] selects `beir-v1.0.0-scifact-test`; retriever includes topic IDs present in qrels | Exact cached query-ID set and count unverified |
| IDs and scores | Retriever serializes topic ID to string and preserves `hit.docid`, `hit.score`, raw document content | Actual score validity, duplicate IDs and text-ID agreement unverified |
| Rank origin | Candidate array preserves hit order; [data writer][writer] emits TREC positions starting at 1 | Cache has no independently inspected explicit ranks; producer tie rule not established |
| Retrieval parameters | BM25 producer calls `set_bm25()` with defaults | Historical dependency version/defaults and cache command not supplied |

Producer code identifies the current route but is not a historical generation
receipt for these cache bytes. The advertised top1000 names are nominal depths,
not proof that every query has 1000 unique candidates. Later acquisition should
retain source order, inspect score ties and declare its rank/tie policy before
evaluation; no tie-breaking repair is selected here.

At Pyserini revision `1cfdc418e5f61c5164914c0844ab6f6a9550683e`,
[flat index metadata][flat-build] documents a 2022-11-16 Anserini build, and
[SPLADE index metadata][splade-build] documents a 2023-11-24
CoCondenser-EnsembleDistil build. These strengthen the documented family
mapping, but do not identify which dependency artifacts generated the cached
RankLLM files. No index was downloaded.

### Text construction fixed before acquisition

The flat-index build specifies `BeirFlatCollection`,
`DefaultLuceneDocumentGenerator` and `-storeRaw` at Anserini revision
`505594b6573294a9a4c72a8feee3416f8a9bd2d9`. Its pinned
[collection parser][beir-parser] preserves the original input JSON in `raw`,
extracts document identity from `_id`, and constructs indexed contents as
`title + "\n" + text`. RankLLM parses that stored raw JSON directly into
`Candidate.doc`. This establishes the documented producer's
`doc._id`/`doc.title`/`doc.text` contract; it is not a cache-body inspection.

Freeze the future lexical adapter to **cached BM25 `doc.title + "\n" +
doc.text`**, with both fields required to be strings. Use cached `query.text`
verbatim as query text. Require string document/query IDs, `candidate.docid ==
candidate.doc._id`, consistent text for every repeated document ID, and identical
query text for matching IDs across the two caches. A missing field, different
schema, conflicting text or ID mismatch stops the acquisition gate before
lexical scoring; do not silently choose another field or normalize IDs. No
full-corpus statistics or SPLADE-only candidate text enters the lexical pool.

If a later compact numeric-run plus BEIR-corpus path is proposed, it must use
the same title-newline-body construction and prove corpus-to-cache identity
before replacing this text source. A title-space-body join is not the declared
source serialization, even if a particular tokenizer treats the two separators
equivalently. The chosen transfer design uses the top1000 cached route; body
checks remain deferred execution gates, while absent historical generation
identity remains an interpretation limit.

## BEIR collection and qrels metadata

[BEIR SciFact metadata][beir-api] identifies public/ungated revision
`b3b5335604bf5ee3c4447671af975ea25143d4f5`. Its card schema describes string
`_id`, `title` and `text` fields, 5,183 corpus examples and 1,109 query texts.
The 1,109 count is the mirror's query-text collection, **not** a verified test
query denominator. [Versioned file metadata][beir-tree] advertises:

| File | Bytes | LFS SHA-256 |
| --- | ---: | --- |
| `corpus/corpus-00000-of-00001.parquet` | 4,469,916 | `243324b35f03d82bd6d98a5f575966876e86cad7ce16e5333a35b1b793dc4f45` |
| `queries/queries-00000-of-00001.parquet` | 64,982 | `1c37956c5dc8b810b60302323c24d1a9e79e26411ba8f5ad9d0888642e2a9034` |

[BEIR qrels metadata][qrels-api] identifies revision
`2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029`, with separate `test.tsv` and
`train.tsv`. [Versioned file metadata][qrels-tree] gives `test.tsv` 5,389 bytes,
Git blob `c62f58c75f10c0cee23483b7269bff2902ae4080`; `train.tsv` 14,502 bytes,
Git blob `3d7882aacef0cbe3befa238357e4bb165165d8ba`. These ordinary Git blob IDs
are not raw-file SHA-256 values. The [immutable test-qrels endpoint][qrels-test]
is pinned but was not read. Actual query IDs, positive-grade count and grade
semantics remain pre-evaluation checks. The HF mirror and historical Pyserini
BEIR index are not yet proven byte-equivalent.

The corpus/query Parquet files plus test qrels advertise 4,540,287 bytes, which
would be economical if a compatible compact numeric run were established.
This audit establishes no such compact run; rebuilding retrieval would need
its own dependency, identity and resource plan.

## License evidence

- Castorini cache API returned `cardData: null`; no explicit cache license was
  established. Neither the model nor a software license automatically licenses
  the cache's included source text.
- BEIR SciFact and SciFact-qrels API cards label their material `cc-by-sa-4.0`.
  These are observed publisher labels; this metadata-only audit did not review
  underlying article-level rights or make a legal determination.
- [Naver model metadata][model-api] labels
  `naver/splade-cocondenser-ensembledistil` `cc-by-nc-sa-4.0`, trained on
  `ms_marco`, current revision `49cf4c7b0db5b870a401ddf5e2669993ef3699c7`.
  This model ID matches cycle02. No model weights or model performance table
  were read; current revision metadata does not prove historical cache lineage.

Keep eventual downloaded source text in ignored local storage and preserve
numeric ranking/provenance artifacts under the project's existing policy.
No redistribution conclusion is inferred from an unauthenticated HTTP response.

## Acquisition record and reproducibility

All successful network reads were bounded `urllib.request.urlopen` GETs of
metadata/source files (caps 150,000 or 500,000 bytes, 25–30 second timeout), or
two HEADs with no `read()` call. API results were filtered to file paths,
identities, schemas, licenses and sizes; code/build metadata was read for
retrieval semantics. No search-engine performance snippet, published metric
table, corpus, run, qrels, topic body or weights were read. No files were
downloaded to the repository by these requests.

The 21 successful metadata/source GETs returned **333,807 bytes** total,
including an index-metadata directory listing of 156,061 bytes. This is distinct
from the nearly 1 GB prospective top1000 transfer. A web-tool API open failed,
and a sandbox urllib request failed DNS resolution. Authorized escalation then
successfully read the public metadata; no provider operation was involved.

Selected byte-hash receipts for the actual metadata/source responses:

| Response | Bytes | SHA-256 of response body |
| --- | ---: | --- |
| Cache API | 22,297 | `db12073c4ca444bd814e6f21125cfc2f1ad47ee6706d86912999d3ba2668c53f` |
| BM25 directory API | 36,710 | `3d848f8b5d67183ad508b636d3e6d03a7920e73c7e6bc58fc1979804a8b249d6` |
| SPLADE directory API | 22,935 | `6d269094fb83bf4ea45ff26b54d8ad3327180b9049062d8cf8a55544a1660595` |
| RankLLM indices source | 8,090 | `c4bbd31670a1cb95e77b1ac9503d9ad7c3e32a14a67b441d1de6669a01b0913e` |
| RankLLM retriever source | 16,893 | `95bef4b0ff68929780e267e355c9cd7a2bf1bed7f047394f7fba0e93297dae06` |
| RankLLM topics source | 2,228 | `8d52b1ca5eb19f92f4f6a74f8e5d819374f2b54dc7d71bae107d609431f39069` |
| RankLLM data source | 3,778 | `313fcf6b29c82e8511a7ff1cab2714d050d54ca81df4a2eeca45a271deae932d` |
| Anserini BEIR flat collection parser | 3,125 | `f92029a063bf99b6a66f6f55957a79cb441b933413e04656f0668e13b09ea1e5` |
| BEIR versioned file metadata | 1,022 | `462a7fde574e7e3c848f429ea8c6c353d5a10895c86a5ef590bb56fd8441a2fe` |
| Qrels versioned file metadata | 391 | `8c5471b10e764e2f0a5a52e4b710cdbd8fce80d2529a7398cae7a4b01cc7498e` |

Reproduce the two central metadata checks without fetching run bodies:

```python
import json
from urllib.request import urlopen, Request

rev = "39db0a25a552dd2a12012df22029686bf7fdc050"
for family in ("BM25", "SPLADE_P_P_ENSEMBLE_DISTIL"):
    metadata = (
        "https://huggingface.co/api/datasets/castorini/rank_llm_data/tree/"
        f"{rev}/retrieve_results/{family}"
    )
    with urlopen(metadata, timeout=30) as response:
        records = json.loads(response.read(500_000))
    print([r for r in records if "scifact" in r.get("path", "").lower()])
    run = (
        "https://huggingface.co/datasets/castorini/rank_llm_data/resolve/"
        f"{rev}/retrieve_results/{family}/retrieve_results_scifact_top1000.jsonl"
    )
    with urlopen(Request(run, method="HEAD"), timeout=30) as response:
        print(response.status, response.headers.get("Content-Length"))
```

No further source family or input acquisition is needed to close this bounded
audit. The coordinator selected preparation of the nearly 1 GB source path
with explicit resource terms, preserving BM25 top1000 candidates, candidate-union
statistics, four lexical outputs at top200 and SPLADE top1000. A future change
to that contract would need a prospective protocol revision. Outstanding body
integrity and corpus/query alignment checks are acceptance conditions for later
acquisition, not findings of this audit.

## Final plan and protocol cross-check

A second bounded local review compared the input plan against the metadata
values actually returned during this audit, with no new network requests.
The reviewed [input plan](../evidence/2026-09-11-cycle14-input-plan.json) had
SHA-256 `051aed306d99e3431aa0cf60f17b7acdf1341becc20d37259c283155c134d18a`;
the reviewed [transfer protocol](2026-09-11-cycle14-transfer-protocol.md) had
SHA-256 `3c4a3dbd1b0444c0a3a5a08f9404b768aa8d39e1a75560833920e28437ec7a24`.
These hashes identify the reviewed versions, not future revisions of those files.

All **45 input-field comparisons** passed: five inputs times role, dataset,
revision, path, resolved URL, byte size, identity algorithm, identity digest and
unacquired status. Four use published LFS SHA-256; the test qrels use their Git
blob SHA-1. **Ten additional plan checks** passed for input count, unique roles,
aggregate bytes, raw cap, decoder size/cap, declared decoder acquisition status,
wheel version/filename, binary grade gate, five-arm list and starting checkpoint.
The five raw inputs total **1,000,472,770 bytes**, leaving **49,527,230 bytes**
below the 1.05 GB raw-input cap.

No source/schema contradiction was found in the reviewed protocol. It retains
cached source order, fixes title-newline-body text, requires identity/text and
complete test-query coverage checks, and treats cache contents and binary qrels
as future gates. The unpinned original first-stage source is correctly described
as a mechanism adaptation. This review corrected the earlier audit wording that
had incorrectly called the original supplied candidate generator BM25.

The coordinator separately reports official PyPI metadata for a pinned
PyArrow25.0.1 wheel of 50,102,437 bytes under its separate 60 MB cap, used only to
decode corpus/query Parquet for identity checks. This worker checked the plan's
internal size/version/cap consistency but did **not** independently fetch its
PyPI metadata, verify wheel bytes, install it, or test platform compatibility.
The decoder and evaluator gates remain future work. No run-body hash, real query
denominator, depth distribution, qrel grade domain or historical cache-generation
identity has been newly verified by this local review.

Friction disposition: **DROP** the one failed web-API open and sandbox DNS
attempt as already-resolved access observations. Public metadata escalation
worked; no new helper, approval rule or workflow change is warranted. The cache
size and absent explicit cache license remain substantive feasibility facts in
this document, rather than process-friction tickets. No live worker-owned job
or provider remains after this artifact is returned.

[cache-api]: https://huggingface.co/api/datasets/castorini/rank_llm_data
[bm25-tree]: https://huggingface.co/api/datasets/castorini/rank_llm_data/tree/39db0a25a552dd2a12012df22029686bf7fdc050/retrieve_results/BM25
[splade-tree]: https://huggingface.co/api/datasets/castorini/rank_llm_data/tree/39db0a25a552dd2a12012df22029686bf7fdc050/retrieve_results/SPLADE_P_P_ENSEMBLE_DISTIL
[bm25-run]: https://huggingface.co/datasets/castorini/rank_llm_data/resolve/39db0a25a552dd2a12012df22029686bf7fdc050/retrieve_results/BM25/retrieve_results_scifact_top1000.jsonl
[splade-run]: https://huggingface.co/datasets/castorini/rank_llm_data/resolve/39db0a25a552dd2a12012df22029686bf7fdc050/retrieve_results/SPLADE_P_P_ENSEMBLE_DISTIL/retrieve_results_scifact_top1000.jsonl
[indices]: https://github.com/castorini/rank_llm/blob/443adf3306102f11b85945d2a277fb6aa10ea0aa/src/rank_llm/retrieve/indices_dict.py
[retriever]: https://github.com/castorini/rank_llm/blob/443adf3306102f11b85945d2a277fb6aa10ea0aa/src/rank_llm/retrieve/pyserini_retriever.py
[topics]: https://github.com/castorini/rank_llm/blob/443adf3306102f11b85945d2a277fb6aa10ea0aa/src/rank_llm/retrieve/topics_dict.py
[writer]: https://github.com/castorini/rank_llm/blob/443adf3306102f11b85945d2a277fb6aa10ea0aa/src/rank_llm/data.py
[flat-build]: https://github.com/castorini/pyserini/blob/1cfdc418e5f61c5164914c0844ab6f6a9550683e/pyserini/resources/index-metadata/lucene-inverted.beir-v1.0.0-flat.20221116.505594.README.md
[splade-build]: https://github.com/castorini/pyserini/blob/1cfdc418e5f61c5164914c0844ab6f6a9550683e/pyserini/resources/index-metadata/lucene-inverted.beir-v1.0.0-splade-pp-ed.20231124.a66f86f.README.md
[beir-parser]: https://github.com/castorini/anserini/blob/505594b6573294a9a4c72a8feee3416f8a9bd2d9/src/main/java/io/anserini/collection/BeirFlatCollection.java
[beir-api]: https://huggingface.co/api/datasets/BeIR/scifact
[beir-tree]: https://huggingface.co/api/datasets/BeIR/scifact/tree/b3b5335604bf5ee3c4447671af975ea25143d4f5?recursive=true
[qrels-api]: https://huggingface.co/api/datasets/BeIR/scifact-qrels
[qrels-tree]: https://huggingface.co/api/datasets/BeIR/scifact-qrels/tree/2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029
[qrels-test]: https://huggingface.co/datasets/BeIR/scifact-qrels/resolve/2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029/test.tsv
[model-api]: https://huggingface.co/api/models/naver/splade-cocondenser-ensembledistil
