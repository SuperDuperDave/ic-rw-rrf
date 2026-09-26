# Cycle22 — acquisition stopped before evaluation

The frozen 29-team, 81-submission comparison **did not reach evaluation**.
Its first acquisition stopped on a publisher-checksum mismatch. This is a data
identity failure under the declared contract, not evidence for or against
averaging submitted outputs.

| Item | Observed |
| --- | --- |
| First run | `10x10.prf.unipd.it` |
| HTTP status | 200 at the exact declared NIST URL; no redirect |
| Bytes | 1,420,451; plain text, not gzip |
| Browser metadata MD5 | `871dd34389cad9cd9c3b751f30d9b2d0` |
| Retrieved raw and decoded MD5 | `7e99300e277da620e1e33f046e9a68f6` |
| Retrieved SHA256 | `d9c84019fddf6fce17d865a25e91c6b443d3ba9f30d06d3da422ca6a31b8b824` |
| Accepted inputs / remaining unfetched | 0 / 80 |
| Numerical producer / independent empirical replay | Not invoked |

The listed hash is independently present in both previously captured copies of
[NIST's run metadata](https://pages.nist.gov/trec-browser/trec-covid/round1/runs/#10x10prfunipdit).
The [official archive](https://ir.nist.gov/trec-covid/archive/archive-round1.html)
links the exact acquired [submission URL](https://ir.nist.gov/trec-covid/archive/round1/10x10.prf.unipd.it).
The response Content-Length and ETag length component agree with the received
size. Those facts do not establish why the metadata checksum differs.

The [freeze](../../_sessions/evidence/2026-09-26-cycle22-preflight.json) precedes
the [failed acquisition](../../_sessions/evidence/2026-09-26-cycle22-acquisition.json).
The failed receipt, original bytes and partial decoded copy are preserved.
No run is dropped, no hash overwritten and no numerical result is available.
Any corrected attempt needs a separate source-identity contract and must retain
this failure; the existing frozen files remain immutable.

Before acquisition, 28 targeted tests passed. Separate parsers and exact scoring
implementations agreed on all 3,300 heads and every synthetic numerical/provenance
field, including short and gzip inputs. The maximum 2.43-million-row fixture took
10.40 seconds for the producer and 10.10 seconds for the checker. These checks
validate implementation behavior, not publisher data identity or the hypothesis.
[Synthetic check receipt](../../_sessions/evidence/2026-09-26-cycle22-synthetic-checks.json).

A [bounded representation diagnostic](../../_sessions/evidence/2026-09-26-cycle22-checksum-diagnostic.json)
found no match among six predeclared byte variants. A separate provenance check
also found metadata/byte MD5 mismatches in all four previously cached BITEM/S
files; the cause remains unverified. No metrics or labels were inspected.

The [assessed Opus review](../../_sessions/cycles/2026-09-26-cycle22-integration.md)
selects a separate cycle23 contract identifying current archive bytes explicitly,
while preserving the original metadata hashes and this stopped attempt. Source
selection, numerical policies and stopping rules remain fixed. The retry will
not claim identity to original submitted bytes where the hashes differ.
