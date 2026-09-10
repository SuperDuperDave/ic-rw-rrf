# Cycle02 source investigation

Checked primary records on 2026-09-10. This is the bounded three-family
inventory specified by the cycle02 proposal. Source selection preceded run-body
download and observation analysis. No fourth family was explored.

| Family | Access and provenance observation | Decision |
| --- | --- | --- |
| TCT-ColBERT-v2-HN+ | Pyserini documents dense retrieval using a prebuilt index and encoder for both years. The checked reproduction page does not provide a small cached-run download. | Park this route; full index/model generation is unnecessary if a suitable existing artifact is available. No claim that cached runs do not exist elsewhere. |
| IDST/Alibaba BERT | NIST catalogs the 2019 passage run; its official raw URL returned HTTP 401 without credentials. A matching family was not established in the 2020 catalog. | Park this route; access and continuity are unresolved. |
| SPLADE++ EnsembleDistil | Castorini's public cache lists both top1000 files, a fixed dataset revision, LFS SHA256 identities, and combined size 42,988,709 bytes. Producer code identifies the neural sparse retrieval family. | Select based on accessible artifacts, both-year coverage, bounded cost, and representation difference. |

Sources: [Pyserini reproduction matrix](https://castorini.github.io/pyserini/2cr/msmarco-v1-passage.html),
[NIST2019 catalog](https://pages.nist.gov/trec-browser/trec28/deep/runs/#idst_bert_p1),
[NIST2020 catalog](https://pages.nist.gov/trec-browser/trec29/deep/runs/),
[Castorini cache](https://huggingface.co/datasets/castorini/rank_llm_data).

The IDST participant's [official paper](https://trec.nist.gov/pubs/trec28/papers/IDST.DL.pdf)
describes `idst_bert_p1` as full ranking with an expanded-passage BM25 retrieval
stage and BERT reranking. It would be a neural cascade, not a dense-only source.
The absence of an IDST/Alibaba text match in the 2020 catalog is not proof that
no related submission exists under another identity. No raw file was obtained.

For SPLADE++, the dataset revision is
`39db0a25a552dd2a12012df22029686bf7fdc050`. The source selection file records
exact pinned paths, expected byte counts and SHA256s. Metadata reported a public,
ungated dataset and no license card. Raw passage/query text remains local;
numeric ranking facts and aggregate observations are the durable artifacts.

Current RankLLM producer code was inspected at
`443adf3306102f11b85945d2a277fb6aa10ea0aa`. It names the relevant index/encoder
and preserves retrieved hit order in the candidate array. This code is a
provenance cross-check, not proof that the cached files were produced at that
exact revision. Historical index/encoder digests and the original generation
command remain unknown. See [source provenance](../../data/cycle02/README.md).

The learned sparse representation is grounded in
[SPLADE's distillation/hard-negative study](https://arxiv.org/abs/2205.04733).
Different representation does not establish independent errors, a useful
specialist, or superior ranking. Those require observations and a separate
effect protocol. The present phase measures candidate access and whether
judgments exist, including explicit grade 0, without measuring relevance gains.
