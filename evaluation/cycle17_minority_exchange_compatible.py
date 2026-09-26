#!/usr/bin/env python3
"""Recorded Cycle17 compatibility for ignored zero-based supplied rank columns.

The frozen original parser still validates and orders the runs. A temporary +1
encoding permits a canonical nonnegative supplied integer; its exact original
value is restored in metadata. This never changes a score, candidate or policy.
The preceding whole-line document-universe correction remains in effect.
"""

from contextlib import contextmanager
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import cycle17_minority_exchange as original
from evaluation import cycle17_minority_exchange_corrected as corrected


CORRECTION = "_sessions/cycles/2026-09-25-cycle17-rank-column-correction.md"
SOURCE = "evaluation/cycle17_minority_exchange_compatible.py"
TESTS = "evaluation/tests/test_cycle17_minority_exchange_compatible.py"
VERIFIER = "_sessions/tools/check_cycle17_exchange_compatible.py"
AUDIT = "_sessions/evidence/2026-09-25-cycle17-run-format-audit.json"
PRIOR_PREFLIGHT = "_sessions/evidence/2026-09-25-cycle17-corrected-preflight.json"
PRIOR_ACQUISITION = "_sessions/evidence/2026-09-25-cycle17-corrected-initial-acquisition.json"
FAILURE = "results/cycle17-2026-09-25/corrected/prepared/failure.json"
REQUIRED_FROZEN = frozenset((CORRECTION, SOURCE, TESTS, VERIFIER, AUDIT,
                            PRIOR_PREFLIGHT, PRIOR_ACQUISITION, FAILURE))
_BASE_PARSE_RUN = original.parse_run


def parse_run(text, docids, query_ids=original.QUERY_IDS):
    """Accept nonnegative supplied ranks; canonical order remains score then ID."""
    encoded = []
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        original.require(len(fields) == 6, f"run line {number}: expected six fields")
        original.require(re.fullmatch(r"0|[1-9][0-9]*", fields[3]) is not None,
                         f"run line {number}: supplied rank must be canonical nonnegative integer")
        fields[3] = str(int(fields[3]) + 1)
        encoded.append(" ".join(fields))
    result = _BASE_PARSE_RUN("\n".join(encoded), docids, query_ids)
    for query in result.values():
        for row in query["details"].values():
            row["supplied_rank"] -= 1
        query["supplied_rank_disagreements"] = sum(
            row["supplied_rank"] != row["canonical_rank"] for row in query["details"].values())
    return result


@contextmanager
def compatible_runtime():
    with corrected.corrected_runtime():
        old_parser, old_check = original.parse_run, original.check_frozen

        def check_frozen(frozen):
            original.require(REQUIRED_FROZEN <= set(frozen), "rank correction omitted required frozen identities")
            return old_check(frozen)

        original.parse_run, original.check_frozen = parse_run, check_frozen
        try:
            yield
        finally:
            original.parse_run, original.check_frozen = old_parser, old_check


def main(argv=None):
    with compatible_runtime():
        return original.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
