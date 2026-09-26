#!/usr/bin/env python3
"""Independent Cycle17 adapter retaining inert, off-universe judgment records.

Only the qrel document-ID membership gate changes. Run validation, canonical
inputs, candidate universe, all policies and all bound calculations stay frozen.
The final policy bytes must equal the previous successful preparation exactly.
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
COMPATIBLE = ROOT / "_sessions/tools/check_cycle17_exchange_compatible.py"
COMPATIBLE_SHA256 = "4585d988f1520c4552cb6d6be8370f600201af5e4614b818e3afde80cf0cb18c"
PRIOR_POLICIES = ROOT / "results/cycle17-2026-09-25/compatible/prepared/policies.json"
EXTRA_FROZEN = {
    "_sessions/cycles/2026-09-25-cycle17-qrel-scope-correction.md",
    "evaluation/cycle17_scoped_labels.py",
    "evaluation/tests/test_cycle17_scoped_labels.py",
    "_sessions/tools/check_cycle17_scoped_labels.py",
    "_sessions/evidence/2026-09-25-cycle17-qrel-universe-audit.json",
    "_sessions/evidence/2026-09-25-cycle17-compatible-preflight.json",
    "_sessions/evidence/2026-09-25-cycle17-compatible-initial-acquisition.json",
    "results/cycle17-2026-09-25/compatible/prepared/policies.json",
    "results/cycle17-2026-09-25/compatible/prepared/manifest.json",
    "results/cycle17-2026-09-25/compatible/prepared/success.json",
    "results/cycle17-2026-09-25/compatible/early/failure.json",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_compatible():
    require(hashlib.sha256(COMPATIBLE.read_bytes()).hexdigest() == COMPATIBLE_SHA256,
            "frozen compatible independent verifier changed")
    spec = importlib.util.spec_from_file_location("cycle17_compatible_independent", COMPATIBLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adapt_own_qrel_parser(module):
    source = inspect.getsource(module.read_qrels)
    old = 'require(doc in valid, f"invalid qrel doc {doc}")'
    new = ('require(bool(doc) and all(33 <= ord(c) <= 126 for c in doc), '
           'f"invalid qrel doc token {doc}")')
    require(source.count(old) == 1, "expected own qrel membership gate not unique")
    source = source.replace(old, new, 1)
    exec(compile(source, str(Path(__file__).resolve()) + ":own-read-qrels", "exec"), module.__dict__)


def self_test(module, corrected, compatible):
    inherited = compatible.self_test(module, corrected)
    with tempfile.TemporaryDirectory(prefix="cycle17-scoped-verifier-test-") as temporary:
        path = Path(temporary) / "synthetic.qrels"
        rows = [f"{q} 0.5 known 1" for q in module.QUERY_IDS]
        path.write_text("\n".join(rows) + "\n")
        before = module.read_qrels(path, {"known", "other"})
        augmented = rows + ["1 1 outside_inventory 2"]
        path.write_text("\n".join(augmented) + "\n")
        after = module.read_qrels(path, {"known", "other"})
        require(after["1"]["outside_inventory"] == 2, "inert label discarded")
        require(sum(map(len, after.values())) == 31, "all qrel rows not retained")
        module.equal(module.bound(["known"], ["other"], before["1"]),
                     module.bound(["known"], ["other"], after["1"]),
                     "off-candidate label has no bound effect")
        bad_rows = (augmented + ["1 1 outside_inventory 0"],
                    rows + ["1 1 outside_inventory 3"],
                    rows + ["1 0 outside_inventory 0"],
                    rows + ["1 1 nonascii_\u00e9 0"])
        for bad in bad_rows:
            path.write_text("\n".join(bad) + "\n")
            try:
                module.read_qrels(path, {"known", "other"})
            except ValueError:
                pass
            else:
                raise ValueError("other qrel validation weakened")
    return {"prior_synthetic_checks": inherited, "inert_label_retained": True,
            "off_candidate_bound_invariant": True, "other_qrel_rejections": 4}


def main():
    compatible = load_compatible()
    previous_loader = compatible.load_corrected

    def load_scoped_corrected():
        corrected = previous_loader()
        previous_original_loader = corrected.load_original

        def load_scoped_original():
            module = previous_original_loader()
            adapt_own_qrel_parser(module)
            prior_custody = module.check_custody

            def check_scoped_custody(args):
                current = module.read_json(args.initial_acquisition)
                require(EXTRA_FROZEN <= current["frozen"].keys(), "qrel-scope custody incomplete")
                prior_receipt = module.read_json(
                    ROOT / "_sessions/evidence/2026-09-25-cycle17-compatible-initial-acquisition.json")
                module.equal(current["inputs"], prior_receipt["inputs"],
                             "qrel-scope correction preserves acquired initial bytes")
                require(module.sha256(Path(args.prepared) / "policies.json") == module.sha256(PRIOR_POLICIES),
                        "scoped-label correction changed frozen policies")
                return prior_custody(args)

            module.check_custody = check_scoped_custody
            return module

        corrected.load_original = load_scoped_original
        return corrected

    compatible.load_corrected = load_scoped_corrected
    if sys.argv[1:] == ["--self-test"]:
        corrected = load_scoped_corrected()
        module = corrected.load_original()
        compatible.adapt_own_run_parser(module)
        module.read_docids = corrected.read_docids
        print(json.dumps(self_test(module, corrected, compatible), sort_keys=True))
    else:
        compatible.main()


if __name__ == "__main__":
    main()
