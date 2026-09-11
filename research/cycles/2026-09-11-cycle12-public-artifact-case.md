# An applied case that arose during the work

This case arose from an actual approval interruption after the bounded
existing-material inventory. It was not obtained by searching for model failures.
It is recorded retrospectively: the answer is already known, and no model-policy
comparison has been run.

## Information need

Before sending a narrower public-source review, establish whether the **exact
bytes of a particular committed research document are publicly retrievable
without authentication**. A local file, authenticated Git push, or old repository
homepage does not by itself demonstrate that fact for the specified file/version.
This factual question is separate from permission to send a particular payload.

Use the first document in the actual public-source check, preserving its order:

- Document: `docs/RESEARCH_SYNTHESIS.md`.
- Commit: `5b49a464cda025e193c90ea1fb765b1b785a6121`.
- Expected SHA256: `5112929a096900d3a5035fb4e77270c6fec05cd395bec44d01f8bf74b9a69398`.
- Exact URL: <https://raw.githubusercontent.com/SuperDuperDave/ic-rw-rrf/5b49a464cda025e193c90ea1fb765b1b785a6121/docs/RESEARCH_SYNTHESIS.md>.

The initial local identity is compatible with two possibilities: those exact
bytes are served without authentication at that URL, or they are not. A public
repository badge and stale listing do not settle the exact
artifact question. A transport failure would also leave it unverified, not prove
that the file is private or absent.

## Acquired evidence and result

An unauthenticated HTTPS GET returned HTTP200 and5,042 bytes whose SHA256 matched
the expected local committed bytes. The [public-source receipt](../evidence/2026-09-11-cycle12-public-source-check.json)
records this and two other requested files, all matching. No source file was
published or changed to obtain this outcome; the commit had already been pushed
in the previous turn.

The web tool had returned an old repository listing and cache misses for exact
raw URLs. Those failures were not treated as evidence of private or nonexistent
files. The later GET establishes observed public retrieval of the exact bytes
during this check; it does not establish future availability or origin-cache
freshness. Exact request timestamps, response headers and network latency were
not retained. Byte counts are not total acquisition or reasoning costs.

## Case validity versus comparison value

This is a concrete record acquisition with an objective byte-level reference.
The acquired response supplied a fact that the initial local identity and old
listing did not establish. It is an applied provenance case, outside the parked
arithmetic laboratory, not a scientific breakthrough or evidence of agent benefit.

Two possible routes request different records: inspect a repository-level listing,
or fetch the versioned artifact and compare its hash. They answer different levels
of the provenance question. Deliberately making the listing-only route the sole
baseline would create an underpowered comparison. A competent single-system
baseline can fetch the exact URL immediately with the same access and budget.
That baseline must be included before considering a new policy or extra agents.

Therefore **case validity is concrete; comparative research value remains open**.
No new solver call follows. This case may serve as a small operational regression
example, but the public-source check alone is not a model evaluation. Keep its
already-known outcome separate from any future untouched evaluation set.

## Paper comparison and stopping decision

All routes may access the same URL and local expected hash. The target remains
exact public bytes, not merely whether the repository has a public badge.

| Route | Record acquired | What it can establish here |
| --- | --- | --- |
| Repository listing | Repository-level page | Repository-level information; insufficient by itself for the exact artifact claim |
| Direct versioned GET plus hash | Response body/status at the exact URL | Observed public availability of matching bytes; the strongest simple route |
| More summaries of the same claim | Derived prose or copied metadata | No demonstrated additional observation of the exact public bytes |

The routes can select different records, but that alone is not a useful
algorithmic result. For this already-specified URL/hash, no additional acquisition
policy or agent stage with a distinct benefit over direct fetch has been proposed.
No latency, cost or model accuracy comparison was run, and no global optimality
claim is made. The paper decision is to **park an empirical comparison on this
case**, retaining it as a concrete provenance example. This completes R15's
comparison check without another provider wave.
