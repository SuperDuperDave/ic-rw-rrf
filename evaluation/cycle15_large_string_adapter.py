#!/usr/bin/env python3
"""Pre-effectiveness correction accepting both Arrow UTF-8 offset widths.

The original cycle15 driver and first failed validation remain frozen. This
adapter changes only the physical Parquet string-width gate. It performs no
casts or text normalization and reuses the original identity, body, cohort,
lexical, fusion, metric, resource-cap and output-custody implementations.
"""

import argparse
import json
from pathlib import Path
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import cycle15_scifact_transfer as original

ADAPTER = "evaluation/cycle15_large_string_adapter.py"
TESTS = "evaluation/tests/test_cycle15_large_string_adapter.py"
CORRECTION = "_sessions/cycles/2026-09-12-cycle15-string-correction.md"
CORRECTION_SOURCES = (ADAPTER, TESTS, CORRECTION)
CUSTODY_SOURCES = (
    "results/cycle15-2026-09-12/validation/failure.json",
    "_sessions/evidence/2026-09-12-cycle15-schema-failure.json",
)


def parquet_texts(path, arrow, parquet, role, schemas=None):
    """Accept UTF-8 string/large_string fields; preserve the original row gate."""
    reader = parquet.ParquetFile(path)
    schema = reader.schema_arrow
    allowed = (arrow.string(), arrow.large_string())
    if set(schema.names) != {"_id", "title", "text"} or len(schema.names) != 3 or any(field.type not in allowed for field in schema):
        raise original.ContractError(role + ": unsupported Parquet schema (expected three string or large_string fields)")
    if schemas is not None:
        schemas[role] = {field.name: str(field.type) for field in schema}
    result = {}
    for batch in reader.iter_batches(batch_size=256):
        for row in batch.to_pylist():
            identifier = original._id(row["_id"], role)
            if identifier in result or not isinstance(row["title"], str) or not isinstance(row["text"], str):
                raise original.ContractError(role + ": duplicate ID or non-string text")
            result[identifier] = (row["title"], row["text"])
    if not result:
        raise original.ContractError(role + ": empty text source")
    return result


def require_corrected_preflight(path):
    """Check new sources and unchanged ancestry before any input body parsing."""
    checked = original.require_preflight(path)
    if not set(CORRECTION_SOURCES + CUSTODY_SOURCES) <= set(checked["source_sha256"]):
        raise original.ContractError("corrected preflight missing correction sources or original failure custody")
    receipt = original.read_json(path)
    ancestor = receipt.get("original_preflight")
    if not isinstance(ancestor, dict) or set(ancestor) != {"path", "sha256"} or not isinstance(ancestor["path"], str):
        raise original.ContractError("corrected preflight requires original preflight identity")
    ancestor_path = (original.ROOT / ancestor["path"]).resolve()
    if not ancestor_path.is_relative_to(original.ROOT) or original.file_identity(ancestor_path)["sha256"] != ancestor["sha256"]:
        raise original.ContractError("original preflight identity mismatch")
    ancestor_checked = original.require_preflight(ancestor_path)
    for relative, expected in ancestor_checked["source_sha256"].items():
        if checked["source_sha256"].get(relative) != expected:
            raise original.ContractError("corrected preflight changed or omitted original source: " + relative)
    return dict(checked, original_preflight=ancestor)


def load_validate(inputs, decoder_path=None, acquisition_manifest=None,
                  decoder_wheel=None, preflight=None):
    """Compose the original input gate with only the physical-width correction."""
    started = time.monotonic()
    correction_gate = require_corrected_preflight(preflight)
    code_hashes = original.verify_frozen_code()
    for relative in CORRECTION_SOURCES:
        code_hashes[relative] = correction_gate["source_sha256"][relative]
    plan = original.read_json(original.ROOT / original.PLAN)
    if "inputs" in inputs:
        if inputs.get("status") != "passed" or inputs.get("input_plan_sha256") != original.FROZEN_SHA256[original.PLAN]:
            raise original.ContractError("acquisition receipt incomplete or input-plan identity differs")
        inputs = inputs["inputs"]
    identities = original.verify_inputs(inputs, plan)
    schemas = {}
    with original.pinned_decoder(decoder_path, plan, decoder_wheel) as (arrow, parquet, decoder_identity):
        corpus = parquet_texts(inputs["corpus"], arrow, parquet, "corpus", schemas)
        queries = parquet_texts(inputs["query_texts"], arrow, parquet, "query_texts", schemas)
    qrels = original.read_binary_qrels(inputs["test_qrels"])
    validated = original.validate_components(corpus, queries, qrels, inputs["candidate_pool"], inputs["added_source"])
    validated.manifest["schema"]["parquet"] = "_id,title,text: Arrow string or large_string UTF-8; no casts or normalization"
    validated.manifest.update(input_identities=identities, code_sha256=code_hashes,
                              decoder=decoder_identity, validation_elapsed_seconds=time.monotonic() - started,
                              parquet_physical_types=schemas, correction_preflight=correction_gate)
    if acquisition_manifest is not None:
        validated.manifest["acquisition_receipt_sha256"] = original.file_identity(acquisition_manifest)["sha256"]
    return validated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("validate", "run"))
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--decoder-path", required=True, type=Path)
    parser.add_argument("--decoder-wheel", required=True, type=Path)
    parser.add_argument("--acquisition-manifest", type=Path)
    parser.add_argument("--metric-gate", type=Path)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a fresh directory")
    if args.mode == "run" and args.metric_gate is None:
        parser.error("run requires --metric-gate")
    try:
        require_corrected_preflight(args.preflight)
        if args.mode == "run":
            original.require_metric_gate(args.metric_gate)
        config = original.read_json(args.inputs)
        acquisition_manifest = args.acquisition_manifest or (args.inputs if "inputs" in config else None)
        validated = load_validate(config, args.decoder_path, acquisition_manifest,
                                  args.decoder_wheel, args.preflight)
        if args.mode == "validate":
            args.output.mkdir(parents=True, exist_ok=False)
            original.write_json(args.output / "validation.json", dict(validated.manifest, command=sys.argv))
            print(json.dumps({"status": "validated_before_effectiveness", "n_queries": len(validated.qids)}))
        else:
            # Recheck the complete correction ancestry immediately before the
            # unchanged driver establishes its own scoring/output gates.
            require_corrected_preflight(args.preflight)
            summary = original.execute(validated, args.output, args.metric_gate, args.preflight)
            print(json.dumps({"status": "completed", "n_queries": len(validated.qids),
                              "primary_B-A": summary["contrasts_ndcg10"]["B-A"]}))
    except (ValueError, OSError, ImportError) as error:
        # execute() owns all post-scoring failures and partial output custody.
        if not args.output.exists():
            args.output.mkdir(parents=True, exist_ok=False)
            original.write_json(args.output / "failure.json", {
                "status": "gate_failed_before_scoring", "type": type(error).__name__,
                "failure": str(error), "command": sys.argv, "correction": CORRECTION,
                "effectiveness_started": False, "effectiveness_completed": False})
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
