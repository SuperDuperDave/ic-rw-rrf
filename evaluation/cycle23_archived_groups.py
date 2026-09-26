"""Cycle23 current archive-byte custody with unchanged Cycle22 calculations."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import cycle22_grouped_outputs as kernel


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "_sessions/cycles/2026-09-26-cycle23-protocol.md"
PLAN = "_sessions/cycles/2026-09-26-cycle23-input-plan.json"
SOURCE = "evaluation/cycle23_archived_groups.py"
TESTS = "evaluation/tests/test_cycle23_archived_groups.py"
ACQUIRER = "_sessions/tools/acquire_cycle23_inputs.py"
ACQUIRER_TESTS = "evaluation/tests/test_cycle23_acquisition.py"
CHECKER = "_sessions/tools/check_cycle23_archived_groups.py"
CONTRACT = "current-nist-archive-bytes-v1"
REQUIRED = {PROTOCOL, PLAN, SOURCE, TESTS, ACQUIRER, ACQUIRER_TESTS, CHECKER,
            kernel.SOURCE, kernel.TESTS, kernel.PLAN, kernel.PROTOCOL}
SAFE_HEADERS = {"Content-Type", "Content-Length", "ETag", "Last-Modified", "Content-Encoding"}
QUERY_IDS = kernel.QUERY_IDS
identity, _need, _json, _write = kernel.identity, kernel._need, kernel._json, kernel._write
parse_docids, parse_run, parse_qrels = kernel.parse_docids, kernel.parse_run, kernel.parse_qrels
build_policies, analyze = kernel.build_policies, kernel.analyze


def _display(path):
    path = Path(path).resolve()
    return str(path.relative_to(ROOT.resolve())) if path.is_relative_to(ROOT.resolve()) else str(path)


def _validate_lineage(plan, frozen):
    """The new identity contract leaves the failed attempt and scientific plan intact."""
    _need(plan.get("schema") == 2 and plan.get("identity_contract") == CONTRACT, "wrong plan identity contract")
    prior = plan["supersedes_failed_attempt"]
    _need(prior["preserve_failure"] is True and {prior["preflight"], prior["acquisition"]} <= set(frozen),
          "failed attempt evidence is not frozen")
    old_preflight, failure = _json(ROOT / prior["preflight"]), _json(ROOT / prior["acquisition"])
    _need(old_preflight.get("status") == "passed" and failure.get("status") == "failed", "prior attempt status differs")
    _need(failure["preflight_sha256"] == identity(ROOT / prior["preflight"])["sha256"]
          and failure["plan_sha256"] == identity(ROOT / kernel.PLAN)["sha256"]
          and failure["frozen"] == old_preflight["frozen"], "failed receipt lineage differs")
    _need(all(frozen.get(path) == sha for path, sha in old_preflight["frozen"].items()), "old frozen dependencies changed")
    old_plan = _json(ROOT / kernel.PLAN)
    for key in ("groups", "query_ids", "inventory", "S", "prior_verification", "docids", "qrels",
                "timeout_seconds", "max_acquisition_seconds", "max_attempts_per_file", "max_total_bytes",
                "max_expanded_per_run", "max_total_expanded_bytes", "max_run_count"):
        _need(plan[key] == old_plan[key], "scientific/resource plan changed: " + key)
    _need(set(plan["items"]) == set(old_plan["items"]), "member item frame changed")
    first_run = sorted(plan["items"])[0]
    for run, original in old_plan["items"].items():
        current = plan["items"][run]
        _need(all(current.get(k) == v for k, v in original.items())
              and set(current) == set(original) | ({"expected_raw_sha256"} if run == first_run else set()),
              "original member metadata changed")
    first = plan["items"][first_run]
    _need(failure["active_run"] == first_run
          and first["expected_raw_sha256"] == failure["partial_files"][first["filename"] + ".download"]["sha256"],
          "first raw SHA does not bind the preserved observation")


def _validate_frame(plan):
    groups = plan["groups"]
    names = [r for members in groups.values() for r in members]
    _need(plan["query_ids"] == QUERY_IDS and len(groups) == 29 and len(names) == len(set(names)) == 81
          and Counter(map(len, groups.values())) == {2: 6, 3: 23}, "planned complete panel differs")
    _need(set(plan["items"]) == set(names), "item census differs")
    inventory = _json(ROOT / plan["inventory"]["path"])
    eligible = [row for row in inventory["teams"] if row["eligible"]]
    _need(len({row["team"] for row in eligible}) == len(eligible)
          and all(len(row["automatic_runs"]) == len(set(row["automatic_runs"])) for row in eligible),
          "duplicate metadata group/member")
    _need({row["team"]: sorted(row["automatic_runs"]) for row in eligible}
          == {t: sorted(members) for t, members in groups.items()}
          and inventory["eligible_teams"] == 29 and inventory["eligible_runs"] == 81,
          "metadata grouping differs")
    _need(inventory["archive_metadata_team_and_run_match"] is True and inventory["run_bodies_fetched"] is False,
          "metadata validation flags differ")
    records = {row["run"]: row for row in inventory["runs"]}
    _need(len(records) == len(inventory["runs"]), "duplicate metadata run ID")
    for team, members in groups.items():
        for run in members:
            row, item = records[run], plan["items"][run]
            _need(row["team"] == team and row["type"] == "automatic"
                  and row["publisher_md5"] == item["publisher_md5"]
                  and row["url"] == item["url"] == "https://ir.nist.gov/trec-covid/archive/round1/" + run,
                  "named source metadata differs")


def _decoded_identity(raw_path, compressed, limit):
    sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
    with (gzip.open(raw_path, "rb") if compressed else raw_path.open("rb")) as stream:
        while block := stream.read(min(1024 * 1024, limit - size + 1)):
            size += len(block)
            _need(size <= limit, "decoded byte cap exceeded")
            sha.update(block)
            md5.update(block)
    return {"bytes": size, "sha256": sha.hexdigest(), "md5": md5.hexdigest()}


def _inputs(plan, receipt, directory, track):
    _need(set(receipt["inputs"]) == set(receipt["transport"]) == set(plan["items"]), "acquisition census differs")
    _need(receipt["max_attempts_per_file"] == 1 and receipt["byte_limit_sentinel"] == 1
          and 0 <= receipt["elapsed_seconds"] <= plan["max_acquisition_seconds"], "acquisition limits differ")
    verified, paths, filenames = {}, {}, set()
    for run in sorted(plan["items"]):
        item, record = plan["items"][run], receipt["inputs"][run]
        filename = item["filename"]
        _need(Path(filename).name == filename and filename not in filenames and record["filename"] == filename
              and record["raw_filename"] == filename + ".download", "unsafe/changed input filename")
        filenames.add(filename)
        path, raw_path = directory / filename, directory / record["raw_filename"]
        decoded, raw = track(path, record), track(raw_path, record["raw"])
        _need(0 < raw["bytes"] <= min(item["max_bytes"], 16 * 1024 * 1024)
              and 0 < decoded["bytes"] <= plan["max_expanded_per_run"], "input byte cap exceeded")
        if "expected_raw_sha256" in item:
            _need(raw["sha256"] == item["expected_raw_sha256"], "expected raw SHA256 differs")
        with raw_path.open("rb") as stream:
            compressed = stream.read(2) == b"\x1f\x8b"
        _need(type(record["gzip"]) is bool and record["gzip"] == compressed, "compression flag differs")
        _need(_decoded_identity(raw_path, compressed, plan["max_expanded_per_run"]) == decoded,
              "raw and decoded representations disagree")
        advertised = item["publisher_md5"]
        matches = [name for name, info in (("raw", raw), ("expanded", decoded)) if info["md5"] == advertised]
        status = "match" if matches else "mismatch"
        _need(record["publisher_md5"] == advertised and record["matched_representation"] == matches
              and record["publisher_checksum_status"] == status, "publisher checksum observation is false")
        transport = receipt["transport"][run]
        headers = transport["headers"]
        _need(transport["url"] == transport["effective_url"] == item["url"] and transport["http_code"] == 200,
              "transport endpoint/status differs")
        _need(set(headers) <= SAFE_HEADERS and headers.get("Content-Encoding", "identity") == "identity"
              and "html" not in headers.get("Content-Type", "").lower(), "unsafe transport metadata")
        if "Content-Length" in headers:
            _need(isinstance(headers["Content-Length"], str) and headers["Content-Length"].isascii()
                  and headers["Content-Length"].isdecimal()
                  and int(headers["Content-Length"]) == raw["bytes"], "transport length differs")
        paths[run] = path
        verified[run] = {"path": _display(path), **decoded, "raw_path": _display(raw_path), "raw": raw,
                         "gzip": compressed, "publisher_md5": advertised, "matched_representation": matches,
                         "publisher_checksum_status": status}
    raw_total, decoded_total = sum(v["raw"]["bytes"] for v in verified.values()), sum(v["bytes"] for v in verified.values())
    _need(raw_total <= plan["max_total_bytes"] and decoded_total <= plan["max_total_expanded_bytes"], "total byte caps exceeded")
    _need(receipt["transfer_bytes_complete_bodies"] == raw_total and receipt["expanded_bytes_complete_bodies"] == decoded_total,
          "acquisition byte totals differ")
    counts = {status: sum(v["publisher_checksum_status"] == status for v in verified.values()) for status in ("match", "mismatch")}
    _need(receipt["publisher_checksums"] == counts, "publisher checksum counts differ")
    return paths, verified, counts


def execute(preflight_path, inputs, acquisition_path, output):
    preflight_path, inputs, acquisition_path, output = map(Path, (preflight_path, inputs, acquisition_path, output))
    output.mkdir(parents=True, exist_ok=False)
    started, tracked, stage = time.monotonic(), {}, "custody"

    def track(path, expected=None):
        path = Path(path).resolve()
        found = identity(path)
        if expected is not None:
            _need(all(found[key] == expected[key] for key in ("bytes", "sha256", "md5") if key in expected),
                  "identity mismatch: " + _display(path))
        tracked[str(path)] = found
        return found

    def after():
        result = {}
        for path in tracked:
            try:
                result[_display(path)] = identity(path)
            except OSError as exc:
                result[_display(path)] = {"error": type(exc).__name__}
        return result

    def elapsed_gate():
        _need(time.monotonic() - started < 300, "producer300-second limit exceeded")

    try:
        preflight_id, acquisition_id = track(preflight_path), track(acquisition_path)
        preflight, acquisition = _json(preflight_path), _json(acquisition_path)
        frozen = preflight.get("frozen", {})
        _need(preflight.get("status") == "passed" and REQUIRED <= set(frozen), "preflight failed or required keys absent")
        for name, sha in frozen.items():
            path = (ROOT / name).resolve()
            _need(path.is_relative_to(ROOT.resolve()), "frozen path escapes repository")
            track(path, {"sha256": sha})
        _need(acquisition.get("schema") == 2 and acquisition.get("status") == "passed"
              and acquisition.get("identity_contract") == CONTRACT and acquisition.get("frozen") == frozen,
              "acquisition identity contract failed or frozen map differs")
        _need(acquisition["preflight_sha256"] == preflight_id["sha256"], "acquisition preflight differs")
        plan = _json(ROOT / PLAN)
        _need(acquisition["plan_sha256"] == identity(ROOT / PLAN)["sha256"], "acquisition plan differs")
        _need(acquisition["supersedes_failed_attempt"] == plan["supersedes_failed_attempt"], "acquisition lineage differs")
        _validate_lineage(plan, frozen)
        cached = {key: {"path": _display(ROOT / plan[key]["path"]), **track(ROOT / plan[key]["path"], plan[key])}
                  for key in ("inventory", "S", "prior_verification", "docids", "qrels")}
        _validate_frame(plan)
        paths, input_ids, checksum_counts = _inputs(plan, acquisition, inputs, track)
        elapsed_gate()
        stage = "rankings"
        prior = _json(ROOT / plan["prior_verification"]["path"])
        _need(prior.get("status") == "passed"
              and prior["custody"]["outputs"]["policies.json"]["sha256"] == plan["S"]["sha256"], "prior S binding differs")
        historical = _json(ROOT / plan["S"]["path"])
        _need(historical["query_ids"] == QUERY_IDS, "S query cohort differs")
        s_orders = {q: historical["queries"][q]["sources"]["S"]["retained_order"] for q in QUERY_IDS}
        docids = parse_docids((ROOT / plan["docids"]["path"]).read_bytes().decode("ascii"))
        _need(all(d in docids for order in s_orders.values() for d in order), "S ID outside inventory")
        diagnostics = {}
        for run in sorted(paths):
            diagnostics[run] = parse_run(paths[run].read_bytes().decode("ascii"), docids, run)
            elapsed_gate()
        runs = {r: {q: diagnostics[r]["queries"][q]["retained_order"] for q in QUERY_IDS} for r in paths}
        policies = build_policies(plan["groups"], runs, s_orders, QUERY_IDS)
        _need(all(policies["queries"][q]["S"] == historical["queries"][q]["policies"]["S"] for q in QUERY_IDS), "S head replay differs")
        _write(output / "sources.json", {"schema": "cycle22-grouped-sources-v1-provisional", "query_ids": QUERY_IDS, "runs": diagnostics})
        _write(output / "policies.json", policies)
        policy_id = track(output / "policies.json")
        stage = "labels"
        labels = parse_qrels((ROOT / plan["qrels"]["path"]).read_bytes().decode("ascii"))
        _write(output / "analysis.json", analyze(policies, labels))
        elapsed_gate()
        before, final = {_display(p): info for p, info in tracked.items()}, after()
        _need(before == final, "tracked source/input/policy bytes changed during execution")
        manifest = {"schema": 2, "phase": "cycle23", "identity_contract": CONTRACT, "frozen": frozen,
                    "numerical_kernel": {"path": kernel.SOURCE, "sha256": frozen[kernel.SOURCE]},
                    "supersedes_failed_attempt": plan["supersedes_failed_attempt"], "publisher_checksums": checksum_counts,
                    "preflight": {"path": _display(preflight_path), **preflight_id},
                    "acquisition": {"path": _display(acquisition_path), **acquisition_id},
                    "inputs": input_ids, "cached": cached, "tracked_before": before, "tracked_after": final,
                    "labels_joined_after_policies_sha256": policy_id["sha256"],
                    "outputs": {name: identity(output / name) for name in ("sources.json", "policies.json", "analysis.json")},
                    "elapsed_seconds": time.monotonic() - started}
        _write(output / "manifest.json", manifest)
        _write(output / "success.json", {"status": "passed", "identity_contract": CONTRACT, "manifest": identity(output / "manifest.json")})
        return manifest
    except Exception as exc:
        _write(output / "failure.json", {"status": "failed", "phase": "cycle23", "identity_contract": CONTRACT, "stage": stage,
                                        "error_type": type(exc).__name__, "error": str(exc),
                                        "tracked_before": {_display(p): info for p, info in tracked.items()},
                                        "tracked_after": after(), "elapsed_seconds": time.monotonic() - started})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("preflight", "inputs", "acquisition", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)

    def timeout(signum, frame):
        raise TimeoutError("producer300-second wall limit exceeded")

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    try:
        execute(args.preflight, args.inputs, args.acquisition, args.output)
    except Exception as exc:
        print(json.dumps({"status": "failed", "identity_contract": CONTRACT, "error_type": type(exc).__name__, "error": str(exc)}))
        return 1
    finally:
        signal.alarm(0)
    print(json.dumps({"status": "passed", "identity_contract": CONTRACT, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
