# Cycle22 — archive bytes and browser MD5 remain different identities

Read-only provenance diagnosis, 2026-09-26. The first frozen acquisition failed
before scoring. The mismatch is verified; its cause is **unresolved**. No new
run body, score table, or label analysis was used for this diagnosis. Earlier
cached run bodies were read only to calculate byte identities. All original
contracts, acquisition artifacts and frozen code remain unchanged.

## Failed input

The [failed acquisition receipt](../evidence/2026-09-26-cycle22-acquisition.json)
records HTTP200 from the exact official archive URL for
[`10x10.prf.unipd.it`](https://ir.nist.gov/trec-covid/archive/round1/10x10.prf.unipd.it).
The receipt itself is 3,055 bytes, SHA256
`54af85d00166df17ce0d45fb7a4ea57501d0ea79daeba36839253e30291bda7f`.

Both ignored files, `_sessions/local/cycle22/inputs/001.run.download` and
`_sessions/local/cycle22/inputs/001.run`, are 1,420,451 bytes with SHA256
`d9c84019fddf6fce17d865a25e91c6b443d3ba9f30d06d3da422ca6a31b8b824`
and MD5 `7e99300e277da620e1e33f046e9a68f6`. The acquired representation is
plain text; materialization did not produce different bytes. Neither matches
the browser metadata MD5 `871dd34389cad9cd9c3b751f30d9b2d0`.
The response declared Content-Length1420451 and Last-Modified
`Fri, 01 May 2020 18:34:11 GMT`; these do not establish a relationship to the
browser digest. The required identity gate correctly stopped the frozen attempt.

## Previously cached comparisons

All four existing archive files also differ from the MD5 shown for their run ID
in the saved official browser metadata. These are provenance comparisons, not
new retrieval measurements or a random sample of archive files.

| Run | Ignored cached path | Bytes | Cached MD5 | Browser MD5 |
|---|---|---:|---|---|
| BITEM_BL | `_sessions/local/cycle17/inputs/A.run` | 1005528 | `ba4d0af42d989b684788d591d2a29fb4` | `e6c33c13f6360539d1296817244d2a09` |
| BioinfoUA-emb | `_sessions/local/cycle17/inputs/S.run` | 1529551 | `1c27114988b3ea2dc98b801b2c43b4b2` | `80b05c54f15981aa74f49aef0bb65127` |
| BITEM_df | `_sessions/local/cycle18/inputs/D.run` | 1020890 | `f6d5fb48f658a75c8b59eb39002d143d` | `92576af90fc88417cb9e6f456d0fba99` |
| BITEM_stem | `_sessions/local/cycle18/inputs/T.run` | 1065685 | `abb8a02205b8de7e65d2ad0402fc360a` | `adb08fd28081f786235798f5757e40f8` |

Their SHA256 identities, in the same order, are:

- A: `2952bb4c58103119dbcb364b3f5f17a40f4208d79f2ea5554beefe8c06899209`
- S: `16a11c75a13c1deba3e41896b6801d7a57285ead28c7ed12e88cb67f848f9821`
- D: `9b0676b75ef0b1467b88ed2ff7275bd18e98154b99dca6832f0502b02ffc2543`
- T: `86cf40346a1b654fa5e19820c2780a87c2389b64fd902ed8cb895b13f02737f6`

## Metadata evidence and source boundaries

The [official run browser](https://pages.nist.gov/trec-browser/trec-covid/round1/runs/)
displays the first run's published MD5 in both independently saved captures.
The [official Round1 archive](https://ir.nist.gov/trec-covid/archive/archive-round1.html)
separately labels its exact URL a submission file. Neither inspected page states
that the browser MD5 hashes the currently downloadable archive representation.
Root and reviewer capture bytes differ; agreement here concerns the relevant
metadata fields, not equality of the complete HTML bodies.

| Ignored capture | Bytes | SHA256 |
|---|---:|---|
| `_sessions/local/cycle21/root/runs.html` | 1616385 | `7718a9fc7a8482f2900a5f3398c99e021b8ad23dfe14b6ef47909e0a86b67431` |
| `_sessions/local/cycle21/root/archive.html` | 24810 | `6aa98bcda1b5fe56fb4ce841c09aec262034ea2bfdcbd551cc50bc0189ba9084` |
| `_sessions/local/cycle21/reviewer/runs.html` | 1616385 | `06230b0c788bc2908cbce20e7e92b08a75431765a6b25b0dfb88f8a8bd8c560f` |
| `_sessions/local/cycle21/reviewer/archive.html` | 24810 | `526d5b349dfe6be8b4d814ed95274ec797cf6bd0eaa604014948aa6059e9f972` |

The [root metadata receipt](../evidence/2026-09-26-cycle21-root-metadata.json)
is 1,018 bytes, SHA256
`b63ca60b11e7ad06b1c25f668c45e689493b890a03084524181f939a0db2df6b`.
The [independent metadata receipt](../evidence/2026-09-26-cycle21-metadata-review.json)
is 103,112 bytes, SHA256
`0cd7beb2bb5d82d03fb4ce447e40f4271c618258cf3557c0b9da883591bae232`.
All six identities above were recomputed from the saved files in this diagnosis.

Supplementary source-text browsing opened three pages:

- [Official Round1 guidelines](https://ir.nist.gov/trec-covid/round1.html),
  Runs section: uploads may be gzip-compressed; tar/zip archives are prohibited.
  Processing sorts by scores and ignores supplied ranks. Neither statement
  documents a byte transformation applied to archived download files or defines
  the browser MD5's representation.
- [Official data documentation](https://ir.nist.gov/trec-covid/data.html): no
  explanation of run-file digest or archive normalization was found.
- [Official browser repository README](https://github.com/usnistgov/trec-browser):
  describes a database-backed metadata browser, but does not define the digest's
  byte representation.

The fourth resource attempt, the
[browser build notebook](https://raw.githubusercontent.com/usnistgov/trec-browser/main/browser/build.ipynb),
failed in the web tool with `Cache miss`; no notebook contents were obtained.
These supplementary web-tool checks have no locally saved raw-body/hash receipt;
they are distinct from the byte-bound Cycle21 captures above. No further fetches
were made.

## Interpretation and next gate

Five mismatches across the failed input and four earlier cached sources make an
isolated typo in the first plan entry an inadequate explanation. They are
consistent with a systematic representation or metadata difference, but do not
identify one. An original compressed upload, formatting/ordering changes, or
stale metadata remain hypotheses. No transformation has been demonstrated to
recover the published digest; do not claim gzip or normalization explains it.

Keep Cycle22 failed under its original contract. Before another acquisition,
either establish what representation the publisher digest identifies, or assess
and separately freeze an archive-byte target whose authority is the official
archive linkage and whose observed bytes receive recorded SHA256 identities.
The latter would retain the browser MD5 as unresolved metadata rather than claim
to satisfy the original digest gate. Preserve the full81-member frame, formulas,
comparators, labels, caps and stops; no source dropping or digest replacement
inside the failed contract. This note supplies evidence for that decision, not
authorization to resume the frozen attempt.
