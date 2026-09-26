#!/usr/bin/env python3
"""One bounded acquisition of the frozen complete submission-group frame."""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import signal
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "_sessions/cycles/2026-09-26-cycle22-input-plan.json"
REQUIRED = {
    "_sessions/cycles/2026-09-26-cycle22-protocol.md",
    "_sessions/cycles/2026-09-26-cycle22-input-plan.json",
    "_sessions/tools/acquire_cycle22_inputs.py",
    "_sessions/tools/check_cycle22_grouped_outputs.py",
    "evaluation/cycle22_grouped_outputs.py",
    "evaluation/tests/test_cycle22_grouped_outputs.py",
    "evaluation/tests/test_cycle22_acquisition.py",
}
SAFE_HEADERS = ("Content-Type", "Content-Length", "ETag", "Last-Modified", "Content-Encoding")


def public_headers(headers):
    return {key: headers[key] for key in SAFE_HEADERS if key in headers}


def identity(path):
    sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
    with Path(path).open("rb") as stream:
        while chunk := stream.read(65536):
            sha.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": sha.hexdigest(), "md5": md5.hexdigest()}


def write_new(path, value):
    with Path(path).open("x") as out:
        json.dump(value, out, indent=2)
        out.write("\n")


def check_frozen(frozen):
    if not REQUIRED <= set(frozen):
        raise ValueError("preflight omits required code or contract")
    for relative, expected in frozen.items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or identity(path)["sha256"] != expected:
            raise ValueError("frozen identity changed: " + relative)


def bounded_copy(stream, destination, limit):
    """Store at most limit bytes; one sentinel byte may detect an overflow."""
    if limit < 1:
        raise ValueError("no byte budget remains")
    size = 0
    with Path(destination).open("xb") as out:
        while True:
            chunk = stream.read(min(65536, limit - size + 1))
            if not chunk:
                break
            if size + len(chunk) > limit:
                out.write(chunk[:limit - size])
                raise ValueError("stream byte ceiling exceeded")
            out.write(chunk)
            size += len(chunk)
    if not size:
        raise ValueError("empty input body")
    return size


def materialize(raw_path, output_path, expected_md5, expansion_limit):
    raw = identity(raw_path)
    with Path(raw_path).open("rb") as stream:
        compressed = stream.read(2) == b"\x1f\x8b"
    with (gzip.open(raw_path, "rb") if compressed else Path(raw_path).open("rb")) as stream:
        bounded_copy(stream, output_path, expansion_limit)
    expanded = identity(output_path)
    matches = [name for name, value in (("raw", raw), ("expanded", expanded))
               if value["md5"] == expected_md5]
    if not matches:
        raise ValueError("publisher MD5 matches neither representation")
    return {**expanded, "raw": raw, "gzip": compressed,
            "publisher_md5": expected_md5, "matched_representation": matches}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise ValueError("redirect outside the declared exact input URL")


def timeout_handler(signum, frame):
    raise TimeoutError("acquisition wall cap reached")


def _acquire(args):
    started = time.monotonic()
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    preflight = json.loads(args.preflight.read_text())
    if preflight.get("status") != "passed":
        raise ValueError("preflight is not passed")
    frozen = preflight["frozen"]
    check_frozen(frozen)
    plan = json.loads(PLAN.read_text())
    groups = plan["groups"]
    run_ids = sorted(x for members in groups.values() for x in members)
    if len(run_ids) != len(set(run_ids)) or set(run_ids) != set(plan["items"]):
        raise ValueError("plan is not the complete unique member frame")
    if len(run_ids) > plan["max_run_count"]:
        raise ValueError("run-count budget exceeded")
    for key in ("inventory", "S", "prior_verification", "docids", "qrels"):
        item = plan[key]
        if identity(ROOT / item["path"])["sha256"] != item["sha256"]:
            raise ValueError("known input identity changed: " + key)
    args.inputs.mkdir(parents=True, exist_ok=False)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": 1, "status": "started", "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "preflight_sha256": identity(args.preflight)["sha256"], "frozen": frozen,
        "plan_sha256": identity(PLAN)["sha256"], "inputs": {}, "transport": {},
        "max_attempts_per_file": 1, "transfer_bytes_complete_bodies": 0,
        "expanded_bytes_complete_bodies": 0, "byte_limit_sentinel": 1,
    }
    write_new(args.receipt.with_name(args.receipt.stem + "-start.json"), receipt)
    opener = urllib.request.build_opener(NoRedirect())
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(plan["max_acquisition_seconds"])
    active = None
    try:
        for run_id in run_ids:
            active = run_id
            item = plan["items"][run_id]
            if Path(item["filename"]).name != item["filename"]:
                raise ValueError("unsafe destination name")
            if item["url"] != "https://ir.nist.gov/trec-covid/archive/round1/" + run_id:
                raise ValueError("unexpected input URL")
            raw_path = args.inputs / (item["filename"] + ".download")
            output_path = args.inputs / item["filename"]
            limit = min(item["max_bytes"], plan["max_total_bytes"] - receipt["transfer_bytes_complete_bodies"])
            request = urllib.request.Request(item["url"], headers={"Accept-Encoding": "identity", "User-Agent": "IC-RW-RRF frozen research acquisition"})
            with opener.open(request, timeout=plan["timeout_seconds"]) as response:
                transport = {"url": item["url"], "effective_url": response.url, "http_code": response.status,
                             "headers": public_headers(response.headers)}
                receipt["transport"][run_id] = transport
                if response.status != 200 or response.url != item["url"]:
                    raise ValueError("unexpected HTTP response")
                if "html" in response.headers.get("Content-Type", "").lower():
                    raise ValueError("HTML body instead of submitted run")
                if response.headers.get("Content-Encoding", "identity") != "identity":
                    raise ValueError("unexpected transport content encoding")
                length = response.headers.get("Content-Length")
                if length is not None and (not length.isdecimal() or int(length) > limit):
                    raise ValueError("advertised body exceeds remaining budget or invalid length")
                raw_size = bounded_copy(response, raw_path, limit)
                if length is not None and raw_size != int(length):
                    raise ValueError("body length disagrees with declared length")
            receipt["transfer_bytes_complete_bodies"] += raw_size
            expansion_limit = min(plan["max_expanded_per_run"], plan["max_total_expanded_bytes"] - receipt["expanded_bytes_complete_bodies"])
            record = materialize(raw_path, output_path, item["publisher_md5"], expansion_limit)
            receipt["expanded_bytes_complete_bodies"] += record["bytes"]
            record.update(filename=item["filename"], raw_filename=raw_path.name)
            receipt["inputs"][run_id] = record
        check_frozen(frozen)
        receipt["status"] = "passed"
    except Exception as error:
        receipt.update(status="failed", active_run=active, error_type=type(error).__name__, error=str(error))
        receipt["partial_files"] = {p.name: identity(p) for p in args.inputs.iterdir() if p.is_file()}
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        receipt["elapsed_seconds"] = time.monotonic() - started
        write_new(args.receipt, receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "transfer_bytes_complete_bodies", "expanded_bytes_complete_bodies", "elapsed_seconds")}))


def acquire(args):
    """Also preserve failures in initial custody gates, before any HTTP request."""
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    started = time.monotonic()
    attempted_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        return _acquire(args)
    except Exception as error:
        if not args.receipt.exists():
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            write_new(args.receipt, {
                "schema": 1, "status": "failed", "started_at_utc": attempted_at,
                "stage": "initial custody/setup or failure recording",
                "preflight_path": str(args.preflight),
                "elapsed_seconds": time.monotonic() - started,
                "error_type": type(error).__name__, "error": str(error),
                "input_directory_exists": args.inputs.exists(),
            })
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    acquire(parser.parse_args())


if __name__ == "__main__":
    main()
