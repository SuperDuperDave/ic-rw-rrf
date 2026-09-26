# Cycle17 — valid-ID list format correction before ranking/label parsing

The original initial acquisition passed its unchanged HTTP/identity gates.
Original preparation then stopped at valid-ID line807, before any run or qrel
row was parsed. Preserve its [failure](../../results/cycle17-2026-09-25/prepared/failure.json),
original source/tests/protocol/preflight and acquisition receipt unchanged.

Inspection of only the acquired valid-ID bytes found51103 LF-delimited lines,
51070 distinct full lines,33 repeated strings each occurring twice, and25 full
lines containing spaces (for example `A.; Bennett`). No blank or nonprintable
line is present. The [format audit](../evidence/2026-09-25-cycle17-docids-format-audit.json)
owns exact observations and identity. No cause for the unusual entries is
inferred. We have not inspected selected-pair ranks, grades or effectiveness.

## Narrow interpretation

Treat each nonempty printable-ASCII full line as one **opaque membership key**,
without stripping or tokenizing its contents. Remove the LF delimiter and
deduplicate identical strings. Blank-only, control or non-ASCII lines still fail.
This is an idempotent set representation of the official inventory; it creates
no ID absent as an exact complete line in that inventory.

Run and qrel parsing are unchanged: six/four whitespace-delimited fields,
respectively, with the document field matched exactly against the membership
set. A multiword inventory key cannot match a parsed single document token;
its component words are never accepted as new IDs. Duplicate **run or qrel
pairs** remain errors. All cohort, score, rank, grade and byte-identity gates
remain in force. This does not certify the completeness or source correctness
of NIST's inventory; unmatched run/qrel IDs will still stop the experiment.

The prior protocol's selected sources, retained100, five policies, eligibility,
missing-label bounds, metric, primary comparison and stops are unchanged.
No outcome has motivated a change. Original raw bytes remain untouched and are
not downloaded again. The correction is solely at valid-ID representation.

## Separate corrected execution

Use `evaluation/cycle17_minority_exchange_corrected.py`, importing the immutable
original implementation and temporarily overriding only the ID-list reader and
the frozen-file checker to require this amendment and correction evidence.
Its separate tests exercise exact duplicate collapse, whole-string membership,
rejected control/blank/non-ASCII input, and restoration of the original reader.
The independent checker has its own adapter and independently specified tests;
it does not import or inspect the primary algorithm.

After both workers declare stable files, record a corrected preflight retaining
every original frozen hash and adding this amendment, adapters/tests, the format
audit, original failed preparation and original acquisition receipt. A derived
initial binding receipt links the original receipt/body hashes to that augmented
set; it is explicitly **not another acquisition**. Verify the old receipt and
every source/input hash before writing this binding. The original evidence is
retained under its original names.

Write corrected phases under `results/cycle17-2026-09-25/corrected/`, preserving
the original failed `prepared/`. Save corrected label-free policies before the
early qrel join. Only after corrected early success, acquire the one untouched
late qrel file under the same URL/metadata/one-attempt gate, binding the corrected
early manifest. Run both observation phases and independent reconstruction with
all augmented hashes checked before and after. No further fallback is implied.
