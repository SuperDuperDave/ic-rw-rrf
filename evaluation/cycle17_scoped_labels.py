#!/usr/bin/env python3
"""Preserve syntactically valid out-of-inventory judgments as inert labels.

This recorded correction changes qrel membership validation only. Run membership,
canonical candidates and every frozen policy remain controlled by the original
document universe. All original qrel shape, cohort, grade and uniqueness gates
still apply, including to labels that no fixed policy can retrieve.
"""

from contextlib import contextmanager
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import cycle17_minority_exchange as original
from evaluation import cycle17_minority_exchange_compatible as compatible


CORRECTION = "_sessions/cycles/2026-09-25-cycle17-qrel-scope-correction.md"
SOURCE = "evaluation/cycle17_scoped_labels.py"
TESTS = "evaluation/tests/test_cycle17_scoped_labels.py"
VERIFIER = "_sessions/tools/check_cycle17_scoped_labels.py"
AUDIT = "_sessions/evidence/2026-09-25-cycle17-qrel-universe-audit.json"
PRIOR_PREFLIGHT = "_sessions/evidence/2026-09-25-cycle17-compatible-preflight.json"
PRIOR_ACQUISITION = "_sessions/evidence/2026-09-25-cycle17-compatible-initial-acquisition.json"
PRIOR_PREPARED = "results/cycle17-2026-09-25/compatible/prepared/"
FAILURE = "results/cycle17-2026-09-25/compatible/early/failure.json"
REQUIRED_FROZEN = frozenset((CORRECTION, SOURCE, TESTS, VERIFIER, AUDIT, PRIOR_PREFLIGHT,
                            PRIOR_ACQUISITION, FAILURE, PRIOR_PREPARED + "policies.json",
                            PRIOR_PREPARED + "manifest.json", PRIOR_PREPARED + "success.json"))
_BASE_PARSE_QRELS = original.parse_qrels


def parse_qrels(text, docids, query_ids=original.QUERY_IDS):
    """Validate and retain all judgment rows without changing the run universe."""
    literal_ids = set()
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        original.require(len(fields) == 4, f"qrels line {number}: expected four fields")
        doc = fields[2]
        original.require(original.valid_id(doc), f"qrels line {number}: invalid document ID")
        literal_ids.add(doc)
    return _BASE_PARSE_QRELS(text, set(docids) | literal_ids, query_ids)


@contextmanager
def scoped_runtime():
    with compatible.compatible_runtime():
        old_parser, old_check = original.parse_qrels, original.check_frozen

        def check_frozen(frozen):
            original.require(REQUIRED_FROZEN <= set(frozen), "qrel correction omitted required frozen identities")
            return old_check(frozen)

        original.parse_qrels, original.check_frozen = parse_qrels, check_frozen
        try:
            yield
        finally:
            original.parse_qrels, original.check_frozen = old_parser, old_check


def main(argv=None):
    with scoped_runtime():
        return original.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
