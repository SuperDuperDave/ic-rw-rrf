#!/usr/bin/env python3
"""One-attempt acquisition for the frozen Cycle17 early/later observation loop."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "_sessions/cycles/2026-09-25-cycle17-input-plan.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")


def verify_frozen(frozen):
    for relative, expected in frozen.items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or digest(path) != expected:
            raise ValueError("frozen source mismatch: " + relative)


def acquire(args):
    started = time.monotonic()
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    preflight = json.loads(args.preflight.read_text())
    frozen = preflight["frozen"]
    verify_frozen(frozen)
    for needed in (str(PLAN.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT))):
        if needed not in frozen:
            raise ValueError("preflight lacks acquisition source/plan")
    plan = json.loads(PLAN.read_text())
    keys = plan["initial_keys" if args.phase == "initial" else "late_keys"]
    args.inputs.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    paths = {key: args.inputs / plan["items"][key]["filename"] for key in keys}
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("an input destination already exists; no overwrite/retry")
    receipt = {"schema": 1, "phase": args.phase, "status": "started",
               "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "preflight_sha256": digest(args.preflight), "frozen": frozen,
               "inputs": {}, "transport": {}, "max_attempts_per_file": 1}
    if args.phase == "late":
        if args.early_results is None:
            raise ValueError("late acquisition requires completed early results")
        early_manifest = args.early_results / "manifest.json"
        if not early_manifest.is_file() or not (args.early_results / "success.json").is_file():
            raise ValueError("early phase is not complete")
        receipt["early_manifest_sha256"] = digest(early_manifest)
    write(args.receipt.with_name(args.receipt.stem + "-start.json"), receipt)
    try:
        total = 0
        for key in keys:
            item, path = plan["items"][key], paths[key]
            headers = args.inputs / (item["filename"] + ".headers")
            if headers.exists():
                raise FileExistsError(headers)
            command = ["curl", "--fail", "--silent", "--show-error", "--location",
                       "--max-redirs", "2", "--proto", "=https", "--proto-redir", "=https",
                       "--max-time", str(plan["timeout_seconds"]), "--max-filesize", str(item["max_bytes"]),
                       "--retry", "0", "--header", "Accept-Encoding: identity",
                       "--dump-header", str(headers), "--output", str(path),
                       "--write-out", "%{json}", item["url"]]
            response = subprocess.run(command, capture_output=True, text=True,
                                      timeout=plan["timeout_seconds"] + 5)
            transport = json.loads(response.stdout) if response.stdout.strip() else {}
            receipt["transport"][key] = {"url": item["url"], "command": command,
                                         "curl_exit": response.returncode,
                                         "effective_url": transport.get("url_effective"),
                                         "http_code": transport.get("http_code"),
                                         "stderr": response.stderr[-1000:]}
            if response.returncode or transport.get("http_code") != 200:
                raise ValueError("acquisition failed: " + key)
            if transport.get("url_effective") != item["url"]:
                raise ValueError("unexpected redirect: " + key)
            final_headers = {}
            for line in headers.read_text().splitlines():
                if line.startswith("HTTP/"):
                    final_headers = {}
                elif ":" in line:
                    name, value = line.split(":", 1)
                    final_headers[name.lower()] = value.strip()
            size = path.stat().st_size
            if size < 1 or size > item["max_bytes"]:
                raise ValueError("input byte ceiling/empty input: " + key)
            if "expected_bytes" in item and size != item["expected_bytes"]:
                raise ValueError("advertised run length changed: " + key)
            for field in ("etag", "last_modified"):
                if field in item and final_headers.get(field.replace("_", "-")) != item[field]:
                    raise ValueError("declared HTTP metadata changed: " + key + "/" + field)
            if "html" in final_headers.get("content-type", "").lower():
                raise ValueError("unexpected HTML input: " + key)
            if final_headers.get("content-encoding", "identity") != "identity":
                raise ValueError("unexpected compressed input: " + key)
            total += size
            if total > plan["max_total_bytes"]:
                raise ValueError("total byte ceiling")
            receipt["inputs"][item["filename"]] = {"bytes": size, "sha256": digest(path)}
            receipt["transport"][key]["headers"] = final_headers
        verify_frozen(frozen)
        receipt.update(status="passed", bytes_downloaded=total,
                       elapsed_seconds=time.monotonic() - started)
    except Exception as error:
        receipt.update(status="failed", error_type=type(error).__name__, error=str(error),
                       elapsed_seconds=time.monotonic() - started)
        write(args.receipt, receipt)
        raise
    write(args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "phase": args.phase,
                      "bytes_downloaded": receipt["bytes_downloaded"],
                      "receipt": str(args.receipt)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("initial", "late"), required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--early-results", type=Path)
    acquire(parser.parse_args())


if __name__ == "__main__":
    main()
