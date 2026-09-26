#!/usr/bin/env python3
"""Independent nonnegative supplied-rank compatibility adapter for Cycle17.

The official score order still controls canonical ranks. The frozen independent
run parser is changed only to admit zero in the preserved, unused rank field.
The earlier opaque-ID correction and all its custody requirements are reused.
"""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORRECTED = ROOT / "_sessions/tools/check_cycle17_exchange_corrected.py"
CORRECTED_SHA256 = "39dc333fcacea94dd226f217b1fda4653461336ca6388cd988fff45d8c218789"
EXTRA_FROZEN = {
    "_sessions/cycles/2026-09-25-cycle17-rank-column-correction.md",
    "evaluation/cycle17_minority_exchange_compatible.py",
    "evaluation/tests/test_cycle17_minority_exchange_compatible.py",
    "_sessions/tools/check_cycle17_exchange_compatible.py",
    "_sessions/evidence/2026-09-25-cycle17-run-format-audit.json",
    "_sessions/evidence/2026-09-25-cycle17-corrected-preflight.json",
    "_sessions/evidence/2026-09-25-cycle17-corrected-initial-acquisition.json",
    "results/cycle17-2026-09-25/corrected/prepared/failure.json",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_corrected():
    require(hashlib.sha256(CORRECTED.read_bytes()).hexdigest() == CORRECTED_SHA256,
            "frozen corrected independent verifier changed")
    spec = importlib.util.spec_from_file_location("cycle17_corrected_independent", CORRECTED)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adapt_own_run_parser(module):
    source = inspect.getsource(module.read_run)
    old = "rank_text.isdigit() and int(rank_text) > 0"
    require(source.count(old) == 1, "expected own rank predicate not uniquely located")
    source = source.replace(old, "rank_text.isdigit() and int(rank_text) >= 0", 1)
    source = source.replace('"invalid positive rank"', '"invalid nonnegative rank"', 1)
    exec(compile(source, str(Path(__file__).resolve()) + ":own-read-run", "exec"), module.__dict__)


def self_test(module, corrected):
    prior = corrected.self_test(module)
    with tempfile.TemporaryDirectory(prefix="cycle17-compatible-verifier-test-") as temporary:
        path = Path(temporary) / "synthetic.run"
        valid = {f"d{i}" for i in range(10)}
        rows = [f"{q} Q0 d{i} {i} {10-i} synthetic"
                for q in module.QUERY_IDS for i in range(10)]
        path.write_text("\n".join(rows) + "\n")
        parsed = module.read_run(path, valid)
        require(parsed["1"]["details"]["d0"]["supplied_rank"] == 0,
                "raw zero-based rank not preserved")
        require(parsed["1"]["details"]["d0"]["canonical_rank"] == 1,
                "canonical rank did not remain one-based")
        require(parsed["1"]["full_order"] == [f"d{i}" for i in range(10)],
                "score ordering changed")
        require(parsed["1"]["diagnostics"]["supplied_rank_disagreements"] == 10,
                "raw vs canonical disagreement diagnostics changed")
        for token in ("-1", "1.5", "nan"):
            bad = rows.copy()
            fields = bad[0].split()
            fields[3] = token
            bad[0] = " ".join(fields)
            path.write_text("\n".join(bad) + "\n")
            try:
                module.read_run(path, valid)
            except ValueError:
                pass
            else:
                raise ValueError("invalid supplied rank accepted")
    return {"prior_synthetic_checks": prior, "zero_rank_accepted_and_preserved": True,
            "one_based_score_ranks_preserved": True, "raw_disagreement_count": True,
            "invalid_rank_tokens_rejected": 3}


def main():
    corrected = load_corrected()
    previous_loader = corrected.load_original

    def load_compatible():
        module = previous_loader()
        adapt_own_run_parser(module)
        prior_custody = module.check_custody

        def check_compatible_custody(args):
            current = module.read_json(args.initial_acquisition)
            require(EXTRA_FROZEN <= current["frozen"].keys(), "rank correction custody incomplete")
            corrected_receipt = module.read_json(
                ROOT / "_sessions/evidence/2026-09-25-cycle17-corrected-initial-acquisition.json")
            module.equal(current["inputs"], corrected_receipt["inputs"],
                         "rank correction preserves acquired bytes")
            return prior_custody(args)

        module.check_custody = check_compatible_custody
        return module

    corrected.load_original = load_compatible
    if sys.argv[1:] == ["--self-test"]:
        module = load_compatible()
        module.read_docids = corrected.read_docids
        print(json.dumps(self_test(module, corrected), sort_keys=True))
    else:
        corrected.main()


if __name__ == "__main__":
    main()
