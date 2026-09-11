# Cycle12: an applied provenance case, with no justified agent comparison

The bounded existing-material inspection did **not justify a new solver or
multiagent experiment**. A later approval interruption produced a concrete
provenance case: verifying public access to exact committed file bytes. Its
strongest simple route is already direct retrieval and hash checking. The paper
comparison is complete and parked. No new dataset was acquired, no passages were
semantically screened, and no solver batch was run. The arithmetic laboratory
remains parked.

This is a retrospective feasibility inspection. The investigators knew the
project history. It is neither a preregistered experiment nor a held-out policy
comparison. The [inventory receipt](../../_sessions/evidence/2026-09-11-cycle12-feasibility.json)
records source hashes, scope, the actual lookup, and limitations.

## What the existing retrieval material supplies

The committed run files contain ranked document IDs and scores; qrels contain
relevance grades. The original query/passage TSVs are absent. Existing ignored
SPLADE caches do contain text: **97 query records and 97,000 candidate appearances**
across the two years. Their hashes and byte counts still match the original
[acquisition manifest](../../data/cycle02/acquired/source-manifest.json).

Every candidate has `docid`, `score`, and `doc`, whose fields are `id` and
`contents`. That schema does not supply factual answer keys, structured source
URLs/timestamps, initial-evidence boundaries, decisive-record annotations or
per-record acquisition costs. The presence of passage text does not supply
those relationships automatically. Relevance grades cannot simply be renamed
as factual answers. This inventory does not claim that the passages contain
no useful cases; identifying one would require semantic adjudication.

## One historical operational case

**Question:** did cycle06's fourth invocation show an actual fallback-model switch?
Its [frozen receipt](../cycle06-2026-09-10/observations/04-p_d52a21de38a2a5a8c21d.json)
contains `model_fallback` and an apparent `<synthetic>` model, alongside the
`model_refusal_no_fallback` marker. Checking the underlying evidence matters:
repeating the collector's labels in several summaries adds no independent support.

The existing [independent audit](../../_sessions/evidence/2026-09-10-cycle06-independent-check.json)
separates two provider message IDs, both `claude-opus-5`, from the local synthetic
error record. Its preserved native evidence shows refusal without an observed
fallback model. The old label arose from a substring match and message attribution
errors. This does not establish complete visibility into transport behavior.
The failure remains rejected; the historical correction was already landed.

A literal lookup at the starting commit returns that audit as its **only match**
in the evidence directory:

```bash
git grep -l -F p_d52a21de38a2a5a8c21d 5b49a464cda025e193c90ea1fb765b1b785a6121 -- _sessions/evidence
```

Thus a simple equal-access route is one search followed by reading the audit.
File byte counts are recorded; search scan cost, reasoning cost and model policy
performance were not measured. The initial receipt already contains a relevant
no-fallback marker, so the supposedly missing distinction is not cleanly absent.
No alternative policy with a consequentially different acquisition was established.

The root also inspected cycle03's review receipt/integration as a provenance
example; both already state its terminal budget error. It was not packaged or
tested as a second case. We did not keep looking for cases until a simple
baseline failed.

## Decision and next boundary

The retrieval reuse route lacks a defined factual case; the operational route
does not establish an acquisition-policy gap. Preserve the latter as a useful
evidence-reconciliation example. Do not promote it into an agent benchmark or
infer general baseline success from this lookup.

R14 closes this inspection. A future applied branch needs a naturally occurring,
well-specified information need and traceable supporting records before choosing
policies. It must disclose what a single system can already access and do with
the same budget. The next choice is a research-design decision, not permission
to repeat arithmetic, search for model failures or turn every caveat into code.

The [cycle11 synthesis](../../docs/RESEARCH_SYNTHESIS.md) remains unchanged.

## A case that arose from actual workflow friction

Automatic approval review blocked the initial Claude inventory transfer as
unapproved external sharing. We preserved that denial, verified three previously
published GitHub files by unauthenticated HTTP200 responses and matching hashes,
and obtained approval for a materially narrower review containing only old public
excerpts. No new content was published to enable that review. Claude did not
review the unpublished inventory; the independent Codex audit did.

The interruption supplied a naturally occurring information need: whether the
exact committed document bytes were publicly retrievable. A stale public repository
listing did not establish it; the versioned GET and hash match did. The
[case card and paper comparison](../../_sessions/cycles/2026-09-11-cycle12-public-artifact-case.md)
separate this valid provenance task from a meaningful policy comparison. Direct
fetch must be the single-system baseline; repeated summaries and a repository
badge are insufficient substitutes. No new method with a distinct benefit over
that baseline was established. This is a retrospective case, not a model test.

Claude's public-source review clarified case validity, comparison value and
observed model failure as separate gates. The [integration](../../_sessions/cycles/2026-09-11-cycle12-review-integration.md)
qualifies its reading of the old gate and documents the changed review scope.
One Opus5/high call succeeded under$0.50/120seconds, with no tools or scouts;
actual native accounting was$0.2276195 and50.67498seconds. Output3354 tokens
includes2716 thinking tokens across two observed message IDs; final per-message
telemetry is unavailable. The2000-token setting is per API response. Its327-word
memo exceeds the300-word advisory target. Native accounting is not subscription
billing and excludes Codex work.

R14's inventory and R15's paper comparison are complete. The latter is parked
for empirical work. Future work needs a distinct applied information or resource
question; case selection must be independent of observed model failure. No new
benchmark or automatic acquisition batch is scheduled. Relay request65 was read
and acknowledged as69; all collaborators finished.

## Verification

An independent Codex audit matched the source hashes, cache schema/counts and
operational metadata. A separate case review checked the recorded public-source
proof and paper comparison without repeating the network requests. It found the
case valid and no established benefit beyond direct fetch; its wording correction
separates nonavailability from a failed check that leaves availability unknown.

The small replay helper was written after the inspection. It performs no network
or provider calls and does not evaluate passage semantics or model policies:

```bash
python3 _sessions/tools/check_cycle12_feasibility.py
python3 _sessions/tools/check_cycle12_feasibility.py --public-only
```

Both pass. The full local check verifies both caches and the original native
message identities; public-only explicitly marks those ignored inputs unavailable.
Both reproduce the single audit match at the fixed starting commit. The research
harness and native collectors are unchanged; their323-test cycle11 checkpoint
was not rerun for this documentation/inventory cycle. Current custody, link and
whitespace checks are recorded in the [final receipt](../../_sessions/evidence/2026-09-11-cycle12-checks.json).
