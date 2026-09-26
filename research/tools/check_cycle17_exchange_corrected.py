#!/usr/bin/env python3
"""Narrow docid-list compatibility adapter for the frozen independent verifier.

Only valid-ID membership parsing changes: exact printable ASCII lines form a
set, including opaque multiword entries. Ranking and judgment parsers, policies,
bounds, evidence reconstruction and the original verifier source stay frozen.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "_sessions/tools/check_cycle17_exchange.py"
ORIGINAL_SHA256 = "53b810518a649c1b388d9d55f5c2f677bd473aebf32e47198268cd01e5315e10"
EXTRA_FROZEN = {
    "_sessions/cycles/2026-09-25-cycle17-docids-correction.md",
    "evaluation/cycle17_minority_exchange_corrected.py",
    "evaluation/tests/test_cycle17_minority_exchange_corrected.py",
    "_sessions/tools/check_cycle17_exchange_corrected.py",
    "_sessions/evidence/2026-09-25-cycle17-initial-acquisition.json",
    "results/cycle17-2026-09-25/prepared/failure.json",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_docids(path):
    """Decode only LF separators; preserve every byte within each ASCII key."""
    data = Path(path).read_bytes()
    lines = data.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    require(bool(lines), "empty valid-ID list")
    for number, line in enumerate(lines, 1):
        require(bool(line) and any(c != 32 for c in line),
                f"blank valid-ID line {number}")
        require(all(32 <= c <= 126 for c in line),
                f"non-printable-ASCII valid-ID line {number}")
    return {line.decode("ascii") for line in lines}


def load_original():
    require(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == ORIGINAL_SHA256,
            "frozen independent verifier changed")
    spec = importlib.util.spec_from_file_location("cycle17_frozen_independent", ORIGINAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def self_test(module):
    with tempfile.TemporaryDirectory(prefix="cycle17-corrected-verifier-test-") as temporary:
        path = Path(temporary) / "docids.txt"
        path.write_bytes(b"doc1\nA.; Bennett\ndoc1\nA.; Bennett\n padded id \n")
        require(read_docids(path) == {"doc1", "A.; Bennett", " padded id "},
                "exact opaque membership or duplicate handling")
        path.write_bytes(b"single")
        require(read_docids(path) == {"single"}, "optional terminal LF")
        failures = (b"", b"\n", b"doc\n\n", b" \n", b"doc\tother\n",
                    b"doc\x0bother\n", b"doc\x0cother\n", b"doc\r\n",
                    b"doc\x7f\n", b"doc\xff\n")
        for invalid in failures:
            path.write_bytes(invalid)
            try:
                read_docids(path)
            except ValueError:
                pass
            else:
                raise ValueError("invalid ID-list byte pattern accepted")
    return {"original_synthetic_checks": module.self_test(),
            "opaque_multiword_preservation": True, "exact_duplicate_deduplication": True,
            "edge_spaces_preserved": True, "optional_terminal_lf": True,
            "rejected_invalid_patterns": len(failures)}


def main():
    module = load_original()
    module.read_docids = read_docids
    original_custody = module.check_custody

    def check_corrected_custody(args):
        current = module.read_json(args.initial_acquisition)
        require(EXTRA_FROZEN <= current["frozen"].keys(), "correction custody incomplete")
        original_receipt = module.read_json(
            ROOT / "_sessions/evidence/2026-09-25-cycle17-initial-acquisition.json")
        module.equal(current["inputs"], original_receipt["inputs"],
                     "correction preserves acquired initial bytes")
        require(original_receipt["status"] == "passed", "original acquisition not passed")
        return original_custody(args)

    module.check_custody = check_corrected_custody
    if sys.argv[1:] == ["--self-test"]:
        print(json.dumps(self_test(module), sort_keys=True))
    else:
        module.main()


if __name__ == "__main__":
    main()
