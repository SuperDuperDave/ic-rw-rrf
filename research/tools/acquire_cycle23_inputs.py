#!/usr/bin/env python3
"""Acquire declared current archive bytes; retain unresolved publisher digests."""
import argparse
import datetime
import gzip
import importlib.util
import json
from pathlib import Path
import signal
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "_sessions/cycles/2026-09-26-cycle23-input-plan.json"
CONTRACT = "current-nist-archive-bytes-v1"
SPEC = importlib.util.spec_from_file_location("cycle23_transport_primitives", ROOT / "_sessions/tools/acquire_cycle22_inputs.py")
transport = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transport)
REQUIRED = {
    "_sessions/cycles/2026-09-26-cycle23-protocol.md",
    "_sessions/cycles/2026-09-26-cycle23-input-plan.json",
    "_sessions/tools/acquire_cycle23_inputs.py",
    "_sessions/tools/check_cycle23_archived_groups.py",
    "evaluation/cycle23_archived_groups.py",
    "evaluation/tests/test_cycle23_archived_groups.py",
    "evaluation/tests/test_cycle23_acquisition.py",
    "_sessions/tools/acquire_cycle22_inputs.py",
}


def check_frozen(frozen):
    if not REQUIRED <= set(frozen):
        raise ValueError("required frozen dependency absent")
    for name, expected in frozen.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or transport.identity(path)["sha256"] != expected:
            raise ValueError("frozen identity changed: " + name)


def materialize(raw_path, output_path, expected_md5, expansion_limit, expected_raw_sha256=None):
    raw = transport.identity(raw_path)
    if expected_raw_sha256 is not None and raw["sha256"] != expected_raw_sha256:
        raise ValueError("previously observed raw SHA256 changed")
    with Path(raw_path).open("rb") as source:
        compressed = source.read(2) == b"\x1f\x8b"
    with (gzip.open(raw_path, "rb") if compressed else Path(raw_path).open("rb")) as source:
        transport.bounded_copy(source, output_path, expansion_limit)
    decoded = transport.identity(output_path)
    matched = [key for key, value in (("raw", raw), ("expanded", decoded)) if value["md5"] == expected_md5]
    return {**decoded, "raw": raw, "gzip": compressed, "publisher_md5": expected_md5,
            "matched_representation": matched, "publisher_checksum_status": "match" if matched else "mismatch"}


def timed_out(signum, frame):
    raise TimeoutError("acquisition wall cap reached")


def acquire(args):
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    started = time.monotonic()
    receipt = {"schema": 2, "status": "started", "identity_contract": CONTRACT,
               "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "inputs": {}, "transport": {}, "max_attempts_per_file": 1,
               "transfer_bytes_complete_bodies": 0, "expanded_bytes_complete_bodies": 0,
               "byte_limit_sentinel": 1, "publisher_checksums": {"match": 0, "mismatch": 0}}
    old_handler = None
    active = None
    try:
        preflight = json.loads(args.preflight.read_text())
        if preflight.get("status") != "passed":
            raise ValueError("preflight is not passed")
        frozen = preflight["frozen"]
        check_frozen(frozen)
        plan = json.loads(PLAN.read_text())
        if plan.get("identity_contract") != CONTRACT or plan.get("schema") != 2:
            raise ValueError("wrong source identity contract")
        earlier = plan["supersedes_failed_attempt"]
        if earlier.get("preserve_failure") is not True:
            raise ValueError("prior failure is not preserved")
        if not {earlier["preflight"], earlier["acquisition"]} <= set(frozen):
            raise ValueError("prior attempt is not frozen")
        old_freeze = json.loads((ROOT / earlier["preflight"]).read_text())
        if any(frozen.get(name) != sha for name, sha in old_freeze["frozen"].items()):
            raise ValueError("prior frozen dependency not preserved")
        failure = json.loads((ROOT / earlier["acquisition"]).read_text())
        if failure.get("status") != "failed":
            raise ValueError("prior acquisition failure changed")
        names = sorted(r for members in plan["groups"].values() for r in members)
        if len(plan["groups"]) != 29 or len(names) != len(set(names)) or len(names) != 81 or set(names) != set(plan["items"]):
            raise ValueError("complete unique member frame differs")
        if len(names) > plan["max_run_count"]:
            raise ValueError("run-count budget exceeded")
        first = names[0]
        first_item = plan["items"][first]
        if failure["active_run"] != first or first_item.get("expected_raw_sha256") != failure["partial_files"][first_item["filename"] + ".download"]["sha256"]:
            raise ValueError("first-body stability pin differs from preserved failure")
        for key in ("inventory", "S", "prior_verification", "docids", "qrels"):
            item = plan[key]
            if transport.identity(ROOT / item["path"])["sha256"] != item["sha256"]:
                raise ValueError("known input identity changed: " + key)
        args.inputs.mkdir(parents=True, exist_ok=False)
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.update(preflight_sha256=transport.identity(args.preflight)["sha256"], frozen=frozen,
                       plan_sha256=transport.identity(PLAN)["sha256"], supersedes_failed_attempt=earlier)
        transport.write_new(args.receipt.with_name(args.receipt.stem + "-start.json"), receipt)
        opener = urllib.request.build_opener(transport.NoRedirect())
        old_handler = signal.signal(signal.SIGALRM, timed_out)
        remaining = plan["max_acquisition_seconds"] - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("acquisition wall cap reached during initial custody")
        signal.setitimer(signal.ITIMER_REAL, remaining)
        for name in names:
            active = name
            item = plan["items"][name]
            if Path(item["filename"]).name != item["filename"]:
                raise ValueError("unsafe destination name")
            if item["url"] != "https://ir.nist.gov/trec-covid/archive/round1/" + name:
                raise ValueError("unexpected input URL")
            raw_path = args.inputs / (item["filename"] + ".download")
            decoded_path = args.inputs / item["filename"]
            limit = min(item["max_bytes"], plan["max_total_bytes"] - receipt["transfer_bytes_complete_bodies"])
            request = urllib.request.Request(item["url"], headers={"Accept-Encoding": "identity", "User-Agent": "IC-RW-RRF frozen archive research"})
            with opener.open(request, timeout=plan["timeout_seconds"]) as response:
                receipt["transport"][name] = {"url": item["url"], "effective_url": response.url,
                    "http_code": response.status, "headers": transport.public_headers(response.headers)}
                if response.status != 200 or response.url != item["url"]:
                    raise ValueError("unexpected HTTP response")
                if "html" in response.headers.get("Content-Type", "").lower() or response.headers.get("Content-Encoding", "identity") != "identity":
                    raise ValueError("unexpected HTTP content type or encoding")
                length = response.headers.get("Content-Length")
                if length is not None and (not length.isdecimal() or int(length) > limit):
                    raise ValueError("advertised body exceeds remaining budget or invalid length")
                size = transport.bounded_copy(response, raw_path, limit)
                if length is not None and size != int(length):
                    raise ValueError("body length disagrees with declared length")
            receipt["transfer_bytes_complete_bodies"] += size
            expanded_limit = min(plan["max_expanded_per_run"], plan["max_total_expanded_bytes"] - receipt["expanded_bytes_complete_bodies"])
            record = materialize(raw_path, decoded_path, item["publisher_md5"], expanded_limit, item.get("expected_raw_sha256"))
            record.update(filename=item["filename"], raw_filename=raw_path.name)
            receipt["inputs"][name] = record
            receipt["expanded_bytes_complete_bodies"] += record["bytes"]
            receipt["publisher_checksums"][record["publisher_checksum_status"]] += 1
        check_frozen(frozen)
        receipt["status"] = "passed"
    except Exception as error:
        receipt.update(status="failed", active_run=active, error_type=type(error).__name__, error=str(error))
        if args.inputs.exists():
            receipt["partial_files"] = {p.name: transport.identity(p) for p in args.inputs.iterdir() if p.is_file()}
        raise
    finally:
        if old_handler is not None:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        receipt.update(elapsed_seconds=time.monotonic() - started,
                       finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        transport.write_new(args.receipt, receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "identity_contract", "publisher_checksums", "transfer_bytes_complete_bodies", "elapsed_seconds")}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "preflight", "receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    acquire(parser.parse_args())


if __name__ == "__main__":
    main()
