# Data

## Included in this repository

**TREC qrels** (relevance judgments) — small files, standard practice to redistribute:
- `trec-dl-2019/2019qrels-pass.txt` — graded relevance (0-3)
- `trec-dl-2019/2019qrels-pass-binary.txt` — binary relevance
- `trec-dl-2020/2020qrels-pass.txt` — graded relevance
- `trec-dl-2020/2020qrels-pass-binary.txt` — binary relevance

**Generated run files** — TREC-format outputs from 7 ranking functions implemented in `evaluation/generate_diverse_runs.py`:
- `trec-dl-2019/runs/bm25.txt` — BM25 (k1=1.2, b=0.75)
- `trec-dl-2019/runs/bm25_tuned.txt` — BM25 (k1=0.9, b=0.4)
- `trec-dl-2019/runs/tfidf.txt` — TF-IDF cosine similarity
- `trec-dl-2019/runs/ql_dirichlet.txt` — Query Likelihood with Dirichlet smoothing
- `trec-dl-2019/runs/tfidf_bigram.txt` — TF-IDF with (1,2)-grams
- `trec-dl-2019/runs/proximity.txt` — Query term proximity scoring
- `trec-dl-2019/runs/semantic_hash.txt` — Random projection hashing of character n-grams

These run files are sufficient to reproduce all evaluation results without downloading external data.

## Not included (download separately)

**MS MARCO top-1000 passage data** — required only to regenerate run files from scratch:

- **TREC DL 2019**: `msmarco-passagetest2019-top1000.tsv`
  - Source: https://msmarco.z22.web.core.windows.net/msmarcoranking/msmarco-passagetest2019-top1000.tsv.gz
  - Format: `qid \t pid \t query \t passage`

- **TREC DL 2020**: `msmarco-passagetest2020-top1000.tsv`
  - Source: https://msmarco.z22.web.core.windows.net/msmarcoranking/msmarco-passagetest2020-top1000.tsv.gz
  - Format: same as 2019

Place the uncompressed `.tsv` files in the corresponding `trec-dl-YYYY/` directory.
