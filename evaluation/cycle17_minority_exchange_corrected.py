#!/usr/bin/env python3
"""Cycle17's recorded docid-list correction; original runner stays immutable.

Only document-universe parsing and the additional provenance requirements are
adapted. Canonical runs, policies, labels, bounds and phase gates use the original
implementation. Importing this module does not mutate that implementation.
"""

from contextlib import contextmanager
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import cycle17_minority_exchange as original


CORRECTION = "_sessions/cycles/2026-09-25-cycle17-docids-correction.md"
SOURCE = "evaluation/cycle17_minority_exchange_corrected.py"
TESTS = "evaluation/tests/test_cycle17_minority_exchange_corrected.py"
VERIFIER = "_sessions/tools/check_cycle17_exchange_corrected.py"
ACQUISITION = "_sessions/evidence/2026-09-25-cycle17-initial-acquisition.json"
FAILURE = "results/cycle17-2026-09-25/prepared/failure.json"
REQUIRED_FROZEN = frozenset((CORRECTION, SOURCE, TESTS, VERIFIER, ACQUISITION, FAILURE))


def parse_docids(text):
    """Deduplicate exact, printable ASCII whole lines; never create token IDs."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    ids = set()
    for number, line in enumerate(lines, 1):
        original.require(bool(line) and bool(line.strip(" ")) and
                         all(32 <= ord(char) <= 126 for char in line),
                         f"docids line {number}: expected nonblank printable ASCII full line")
        ids.add(line)
    original.require(ids, "empty document universe")
    return ids


@contextmanager
def corrected_runtime():
    """Install the two bounded overrides only for the duration of a CLI call."""
    old_parser, old_check = original.parse_docids, original.check_frozen

    def check_frozen(frozen):
        original.require(REQUIRED_FROZEN <= set(frozen), "correction omitted required frozen identities")
        return old_check(frozen)

    original.parse_docids, original.check_frozen = parse_docids, check_frozen
    try:
        yield
    finally:
        original.parse_docids, original.check_frozen = old_parser, old_check


def main(argv=None):
    with corrected_runtime():
        return original.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
