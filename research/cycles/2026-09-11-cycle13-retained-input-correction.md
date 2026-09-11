# Cycle13 retained-input correction

The [initial protocol](2026-09-11-cycle13-judgment-protocol.md) incorrectly stated
that all lexical run lists have depth30. The coordinator supplied that assumption
to both reviewers. The implementation correctly rejected the actual first query
before any fusion or metric calculation. The [failed attempt](../evidence/2026-09-11-cycle13-stopped-attempt.json)
and original sources/preflight remain unchanged.2019 qrels had been read by the
driver; no comparison was computed, and no output directory was created.

Metadata inspection after the failure establishes the actual retained depths:

| Year | Each lexical source | SPLADE++ |
| --- | --- | --- |
| 2019 | 41 lists of200, one of37, one of5 | 43 lists of1000 |
| 2020 | 52 lists of200, one of188, one of28 | 54 lists of1000 |

The saved [input inventory](../evidence/2026-09-11-cycle13-retained-inputs.json)
pins all12 files and each source's query/depth mapping. These metadata were also
available in cycle02's preserved observation summary. The missed preflight check
is an input-contract error, not evidence that the method or a model failed.

**Corrected execution decision:** preserve every retained source list, as the
original intent required. Validate the exact inventory and identical source query
sets before analysis. No truncation, padding, replacements or cohort exclusion.
The one five-document lexical query stays in the panel; a metric ranking may
contain fewer than10 documents and contributes only its actual positions.

Everything else remains fixed: A/B source identities, canonical floating k60
fusion, grade/3, unnormalized top10 RBP contribution p4/5, per-query budgets0/1/3,
sharp bounds, overlap reporting and stopping after one completed local audit.
Results use the actual retained lengths, not the incorrect30-depth experiment.

A small separate adapter imports the frozen query math and summary functions,
validates these retained inputs, and records actual source depths. Original code,
tests, protocol and failed preflight remain immutable. Test metadata rejection
and full retained-list use before the corrected run. Independent reconstruction
must use the actual depths and all97 queries.

The correction is based on serialized input lengths before any outcome, not a
response-dependent new pair or parameter choice. Stop after the corrected run
and its audit; no further design expansion or provider call is required.
