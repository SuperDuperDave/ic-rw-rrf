# Cycle02 external source

SPLADE++ EnsembleDistil cached passage rankings were selected by artifact access,
provenance, both-year availability, and bounded resources before measuring
candidate or judgment coverage. They add a neural sparse representation to the
existing lexical core. This is a different source family, not an independence
or performance claim.

[source-selection.json](source-selection.json) pins the two raw files to
Castorini's Hugging Face dataset revision and published LFS SHA256/size metadata.
The [observation protocol](../../_sessions/cycles/2026-09-10-cycle02-observation-protocol.md)
was frozen before acquisition and distinguishes observations from effects.

## Provenance

- [Castorini retrieval cache](https://huggingface.co/datasets/castorini/rank_llm_data)
  supplies top1000 DL2019/DL2020 JSONL retrieval inputs, about 43 MB combined.
- [Producer implementation](https://github.com/castorini/rank_llm/blob/443adf3306102f11b85945d2a277fb6aa10ea0aa/src/rank_llm/retrieve/pyserini_retriever.py)
  maps the SPLADE++ family to a Lucene impact searcher with an ONNX query encoder.
  Its index map names `msmarco-v1-passage.splade-pp-ed-text`. This identifies the
  documented retrieval path; the cache does not supply the exact historical
  production command or index/encoder digests. Do not claim a regenerated run
  is identical merely because the family name agrees.
- [SPLADE model card](https://huggingface.co/naver/splade-cocondenser-ensembledistil)
  and [paper](https://arxiv.org/abs/2205.04733) describe sparse neural retrieval,
  distillation, and hard-negative training. The model card labels its license
  CC-BY-NC-SA-4.0. That model label is not treated as a license for passages in
  the cache; the inspected dataset metadata supplied no license card.

Raw JSONL, including query and passage text, stays in ignored local storage.
Only numeric ranking facts, source identities, conversion code, and audit
results are committed. This acquisition does not download model weights,
indexes, or a full passage corpus. External ranking covers corpus-wide candidate
access according to the producer path; our historical lexical runs rerank a
supplied candidate pool. That distinction remains part of the experiment.

## Reproduce acquisition

From the repository root, these commands reproduce acquisition and observation
into fresh ignored local directories. The committed evidence is under
`data/cycle02/acquired` and `results/cycle02-2026-09-10/observations`.

```bash
python3 _sessions/tools/acquire_cycle02_source.py --selection data/cycle02/source-selection.json --cache-dir _sessions/local/cycle02/source-cache --output _sessions/local/cycle02/reproduced-source
python3 -B evaluation/cycle02_observation_audit.py --source-manifest _sessions/local/cycle02/reproduced-source/source-manifest.json --protocol _sessions/cycles/2026-09-10-cycle02-observation-protocol.md --output _sessions/local/cycle02/reproduced-observations
```

The acquisition checks byte counts/hashes and preserves candidate-array order
when assigning one-based TREC ranks. Equal scores retain their supplied order.
It neither reads qrels nor computes a ranking metric. Existing output must not
be overwritten; a verified raw cache may be reused for a new conversion directory.
The acquired manifest records exact inputs, derived hashes, observed schema,
query coverage, and rank/tie information.
