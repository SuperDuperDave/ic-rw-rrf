#!/usr/bin/env python3
"""Cycle23 current-archive-byte custody and independent grouped reconstruction.

Numerical and parser kernels are the immutable independent Cycle22 kernels.
This is a separate acquisition contract: publisher MD5 mismatches are recorded,
never converted into checksum matches. No producer implementation is imported.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import signal
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = "_sessions/cycles/2026-09-26-cycle23-input-plan.json"
PROTOCOL = "_sessions/cycles/2026-09-26-cycle23-protocol.md"
SOURCE = "_sessions/tools/check_cycle23_archived_groups.py"
HELPER = "_sessions/tools/check_cycle22_grouped_outputs.py"
HELPER_SHA256 = "c5c5985ad246b016bcabe9dcb4d7ab06a189c924471d82ff1f7fd51d4f838069"
CONTRACT = "current-nist-archive-bytes-v1"

# Loading a pinned independent module exposes pure parser/arithmetic helpers.
# Its verify(), check_acquisition(), and main() are never called or patched.
_helper_path = ROOT / HELPER
if hashlib.sha256(_helper_path.read_bytes()).hexdigest() != HELPER_SHA256:
    raise ValueError("immutable independent Cycle22 helper identity changed")
_spec = importlib.util.spec_from_file_location("cycle23_independent_kernels", _helper_path)
kernels = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kernels)
require, same, identity, read_json = kernels.require, kernels.same, kernels.identity, kernels.read_json
QIDS = kernels.QIDS
REQUIRED = {
    PROTOCOL, PLAN, SOURCE, HELPER,
    "_sessions/tools/acquire_cycle23_inputs.py",
    "evaluation/cycle23_archived_groups.py", "evaluation/tests/test_cycle23_archived_groups.py",
    "evaluation/tests/test_cycle23_acquisition.py",
    "evaluation/cycle22_grouped_outputs.py", "evaluation/tests/test_cycle22_grouped_outputs.py",
}
SAFE_HEADERS = {"Content-Type", "Content-Length", "ETag", "Last-Modified", "Content-Encoding"}


def artifact_path(value):
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def portable(path):
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def checksum_status(published, raw, decoded):
    matches = [name for name, value in (("raw", raw), ("expanded", decoded)) if value["md5"] == published]
    return matches, "match" if matches else "mismatch"


def validate_frame(plan):
    require(plan["schema"] == 2 and plan["identity_contract"] == CONTRACT, "plan identity contract")
    groups = plan["groups"]
    require(len(groups) == 29 and Counter(map(len, groups.values())) == {2: 6, 3: 23}, "29-team/81-member frame")
    members = [r for runs in groups.values() for r in runs]
    require(len(members) == len(set(members)) == 81 and set(members) == set(plan["items"]), "unique complete member frame")
    same(plan["query_ids"], QIDS, "query cohort")
    require(all(runs == sorted(runs) for runs in groups.values()), "sorted member IDs")
    inventory = read_json(artifact_path(plan["inventory"]["path"]))
    require(len({row["team"] for row in inventory["teams"]}) == len(inventory["teams"]), "duplicate inventory team")
    require(all(len(row["automatic_runs"]) == len(set(row["automatic_runs"])) for row in inventory["teams"]),
            "duplicate inventory member")
    expected = {row["team"]: sorted(row["automatic_runs"]) for row in inventory["teams"] if row["eligible"]}
    same(groups, expected, "complete metadata-defined groups")
    index = {row["run"]: row for row in inventory["runs"]}
    require(len(index) == len(inventory["runs"]), "duplicate inventory run ID")
    names = set()
    for run, item in plan["items"].items():
        require(item["filename"] == Path(item["filename"]).name and item["filename"] not in names, "safe unique filenames")
        names.add(item["filename"])
        require(index[run]["type"] == "automatic" and index[run]["team"] in groups, "member metadata domain")
        require(run in groups[index[run]["team"]], "member owner")
        require(item["url"] == index[run]["url"] == "https://ir.nist.gov/trec-covid/archive/round1/" + run,
                "exact official archive URL")
        require(item["publisher_md5"] == index[run]["publisher_md5"], "original publisher checksum metadata")


def verify_layers(path, raw_path, item, record, max_expanded):
    decoded, raw = identity(path, True), identity(raw_path, True)
    same({k: record[k] for k in decoded}, decoded, "decoded identity")
    same(record["raw"], raw, "raw identity")
    require(0 < raw["bytes"] <= min(item["max_bytes"], 16 * 1024 * 1024), "raw byte cap")
    require(0 < decoded["bytes"] <= max_expanded, "expanded byte cap")
    if "expected_raw_sha256" in item:
        require(raw["sha256"] == item["expected_raw_sha256"], "predeclared raw SHA stability pin")
    with raw_path.open("rb") as handle:
        compressed = handle.read(2) == b"\x1f\x8b"
    same(record["gzip"], compressed, "gzip magic")
    if compressed:
        sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
        with gzip.open(raw_path, "rb") as handle:
            while block := handle.read(min(1024 * 1024, max_expanded - size + 1)):
                size += len(block)
                require(size <= max_expanded, "independent gzip expansion cap")
                sha.update(block)
                md5.update(block)
        same({"bytes": size, "sha256": sha.hexdigest(), "md5": md5.hexdigest()}, decoded, "independent gzip decode")
    else:
        same(raw, decoded, "plain representation equality")
    require(record["publisher_md5"] == item["publisher_md5"], "publisher checksum preserved")
    matches, status = checksum_status(item["publisher_md5"], raw, decoded)
    same(record["matched_representation"], matches, "honest matching representations")
    same(record["publisher_checksum_status"], status, "honest publisher checksum status")
    return raw, decoded, compressed, matches, status


def verify_transport(item, transport, raw):
    require(transport["url"] == transport["effective_url"] == item["url"], "transport exact URL")
    require(transport["http_code"] == 200, "transport HTTP status")
    require(set(transport["headers"]) <= SAFE_HEADERS, "nonpublic HTTP header")
    require(transport["headers"].get("Content-Encoding", "identity") == "identity", "transport encoding")
    require("html" not in transport["headers"].get("Content-Type", "").lower(), "HTML response")
    if "Content-Length" in transport["headers"]:
        require(int(transport["headers"]["Content-Length"]) == raw["bytes"], "transport declared length")


def check_acquisition(plan, preflight, acquisition, inputs_dir):
    require(acquisition["schema"] == 2 and acquisition["status"] == "passed", "Cycle23 acquisition status/schema")
    require(acquisition["identity_contract"] == CONTRACT, "acquisition identity contract")
    same(acquisition["supersedes_failed_attempt"], plan["supersedes_failed_attempt"], "acquisition preserved prior attempt")
    same(acquisition["frozen"], preflight["frozen"], "acquisition frozen map")
    require(acquisition["plan_sha256"] == identity(artifact_path(PLAN))["sha256"], "acquisition plan hash")
    require(set(acquisition["inputs"]) == set(plan["items"]), "acquisition complete frame")
    require(set(acquisition["transport"]) == set(plan["items"]), "transport complete frame")
    require(acquisition["max_attempts_per_file"] == 1 and acquisition["byte_limit_sentinel"] == 1, "acquisition attempt limits")
    require(0 <= acquisition["elapsed_seconds"] <= plan["max_acquisition_seconds"], "acquisition wall cap")
    tracked, verified = set(), {}
    counts = {"match": 0, "mismatch": 0}
    total_raw = total_expanded = 0
    for run in sorted(plan["items"]):
        item, record = plan["items"][run], acquisition["inputs"][run]
        require(record["filename"] == item["filename"] and record["raw_filename"] == item["filename"] + ".download",
                "acquisition filenames")
        path, raw_path = inputs_dir / item["filename"], inputs_dir / record["raw_filename"]
        raw, decoded, compressed, matches, status = verify_layers(path, raw_path, item, record, plan["max_expanded_per_run"])
        verify_transport(item, acquisition["transport"][run], raw)
        verified[run] = {"path": portable(path), **decoded, "raw_path": portable(raw_path), "raw": raw,
                         "gzip": compressed, "publisher_md5": item["publisher_md5"],
                         "matched_representation": matches, "publisher_checksum_status": status}
        tracked.update((path.resolve(), raw_path.resolve()))
        counts[status] += 1
        total_raw += raw["bytes"]
        total_expanded += decoded["bytes"]
    require(total_raw <= plan["max_total_bytes"] and total_expanded <= plan["max_total_expanded_bytes"], "aggregate byte caps")
    require(acquisition["transfer_bytes_complete_bodies"] == total_raw, "transferred bytes")
    require(acquisition["expanded_bytes_complete_bodies"] == total_expanded, "expanded bytes")
    same(acquisition["publisher_checksums"], counts, "complete publisher checksum counts")
    return verified, tracked, counts


def check_frozen(preflight):
    require(preflight.get("status") == "passed" and preflight.get("schema") in (1, 2), "preflight schema/status")
    frozen = preflight["frozen"]
    require(REQUIRED <= set(frozen), "missing frozen source/contract")
    require(frozen[HELPER] == HELPER_SHA256, "frozen independent helper hash")
    for name, sha in frozen.items():
        path = artifact_path(name).resolve()
        require(not Path(name).is_absolute() and path.is_relative_to(ROOT.resolve()), "frozen path outside repository")
        require(identity(path)["sha256"] == sha, "changed frozen file: " + name)
    return {artifact_path(p).resolve() for p in frozen}


def check_preserved_attempt(plan, preflight):
    previous = plan["supersedes_failed_attempt"]
    require(previous["preserve_failure"] is True, "prior failure preservation declaration")
    paths = {previous["preflight"], previous["acquisition"]}
    require(paths <= set(preflight["frozen"]), "prior attempt receipts not frozen")
    old_preflight = read_json(artifact_path(previous["preflight"]))
    require(old_preflight["status"] == "passed", "previous preflight status")
    for path, sha in old_preflight["frozen"].items():
        require(preflight["frozen"].get(path) == sha, "old frozen identity not preserved: " + path)
    old_failure = read_json(artifact_path(previous["acquisition"]))
    require(old_failure["status"] == "failed", "old failure not preserved as failed")
    require(old_failure["preflight_sha256"] == identity(artifact_path(previous["preflight"]))["sha256"],
            "previous failure/preflight binding")
    same(old_failure["frozen"], old_preflight["frozen"], "previous failure frozen map")
    old_plan_path = "_sessions/cycles/2026-09-26-cycle22-input-plan.json"
    require(old_plan_path in old_preflight["frozen"], "previous input plan was not frozen")
    old_plan = read_json(artifact_path(old_plan_path))
    require(old_failure["plan_sha256"] == identity(artifact_path(old_plan_path))["sha256"], "previous failure/plan binding")
    # Only the envelope and first-run current-byte stability pin may differ.
    old_science = {k: v for k, v in old_plan.items() if k not in ("schema", "status")}
    new_science = {k: v for k, v in plan.items() if k not in ("schema", "status", "identity_contract", "supersedes_failed_attempt")}
    new_science["items"] = {r: {k: v for k, v in item.items() if k != "expected_raw_sha256"}
                            for r, item in plan["items"].items()}
    same(new_science, old_science, "scientific contract and original metadata unchanged")
    first = sorted(plan["items"])[0]
    require(old_failure["active_run"] == first, "previous first failed run")
    require([r for r in plan["items"] if "expected_raw_sha256" in plan["items"][r]] == [first],
            "exact first-run stability pin")
    expected = plan["items"][first]["expected_raw_sha256"]
    require(expected == old_failure["partial_files"][plan["items"][first]["filename"] + ".download"]["sha256"],
            "first stability pin differs from preserved failed raw bytes")
    return {artifact_path(p).resolve() for p in paths}


def verify(args):
    started = time.monotonic()
    preflight, acquisition = read_json(args.preflight), read_json(args.acquisition)
    tracked = check_frozen(preflight)
    plan = read_json(artifact_path(PLAN))
    tracked.update(check_preserved_attempt(plan, preflight))
    cached = {}
    for key in ("inventory", "S", "prior_verification", "docids", "qrels"):
        item = plan[key]
        path = artifact_path(item["path"]).resolve()
        value = identity(path, True)
        require(value["sha256"] == item["sha256"], f"cached {key} SHA mismatch")
        if "bytes" in item:
            require(value["bytes"] == item["bytes"], f"cached {key} bytes mismatch")
        cached[key] = {"path": portable(path), **value}
        tracked.add(path)
    validate_frame(plan)
    require(acquisition["preflight_sha256"] == identity(args.preflight)["sha256"], "acquisition preflight identity")
    inputs, raw_paths, checksum_counts = check_acquisition(plan, preflight, acquisition, args.inputs)
    tracked.update(raw_paths)
    tracked.update((args.preflight.resolve(), args.acquisition.resolve()))
    files = {name: args.result / name for name in ("sources.json", "policies.json", "analysis.json", "manifest.json", "success.json")}
    tracked.update(p.resolve() for p in files.values())
    before = {portable(p): identity(p, True) for p in sorted(tracked)}
    manifest, success = read_json(files["manifest.json"]), read_json(files["success.json"])
    require(set(manifest) == {"schema", "phase", "identity_contract", "frozen", "preflight", "acquisition", "inputs", "cached",
                              "tracked_before", "tracked_after", "labels_joined_after_policies_sha256", "outputs", "elapsed_seconds",
                              "publisher_checksums", "supersedes_failed_attempt", "numerical_kernel"}, "producer manifest fields")
    require(manifest["schema"] == 2 and manifest["phase"] == "cycle23" and manifest["identity_contract"] == CONTRACT,
            "producer new-contract envelope")
    same(success, {"status": "passed", "identity_contract": CONTRACT, "manifest": identity(files["manifest.json"], True)},
         "producer success envelope")
    same(manifest["publisher_checksums"], checksum_counts, "producer original-checksum disclosures")
    same(manifest["supersedes_failed_attempt"], plan["supersedes_failed_attempt"], "producer preserved prior attempt")
    numerical_path = "evaluation/cycle22_grouped_outputs.py"
    same(manifest["numerical_kernel"], {"path": numerical_path, "sha256": preflight["frozen"][numerical_path]},
         "producer immutable numerical kernel identity")
    same(manifest["frozen"], preflight["frozen"], "producer complete frozen map")
    for key in ("preflight", "acquisition"):
        path = getattr(args, key)
        same(manifest[key], {"path": portable(path), **identity(path, True)}, "producer " + key)
    same(manifest["inputs"], inputs, "producer all actual input identities and checksum statuses")
    same(manifest["cached"], cached, "producer cached input identities")
    for row in cached.values():
        same(before[row["path"]], {k: row[k] for k in ("bytes", "sha256", "md5")}, "cached identity at audit start")
    for row in inputs.values():
        same(before[row["path"]], {k: row[k] for k in ("bytes", "sha256", "md5")}, "input identity at audit start")
        same(before[row["raw_path"]], row["raw"], "raw identity at audit start")
    same(manifest["outputs"], {name: identity(files[name], True) for name in ("sources.json", "policies.json", "analysis.json")},
         "producer output identities")
    require(manifest["labels_joined_after_policies_sha256"] == identity(files["policies.json"])["sha256"],
            "policies-before-labels identity")
    same(manifest["tracked_before"], manifest["tracked_after"], "producer unchanged tracked custody")
    expected_tracked = {artifact_path(p).resolve() for p in preflight["frozen"]} | raw_paths
    expected_tracked.update(artifact_path(row["path"]).resolve() for row in cached.values())
    expected_tracked.update((args.preflight.resolve(), args.acquisition.resolve(), files["policies.json"].resolve()))
    require(expected_tracked <= {artifact_path(p).resolve() for p in manifest["tracked_before"]}, "producer custody omits required paths")
    for path, value in manifest["tracked_before"].items():
        same(identity(artifact_path(path), True), value, "producer tracked identity " + path)
    require(0 <= manifest["elapsed_seconds"] <= 300, "producer wall cap")
    docids = kernels.read_docids(artifact_path(plan["docids"]["path"]))
    prior = read_json(artifact_path(plan["S"]["path"]))
    same(prior["query_ids"], QIDS, "prior query cohort")
    require(read_json(artifact_path(plan["prior_verification"]["path"]))["status"] == "passed", "prior S independent check")
    s_orders = {}
    for q in QIDS:
        order = prior["queries"][q]["sources"]["S"]["retained_order"]
        require(len(order) == len(set(order)) == 100 and set(order) <= docids, "fixed S100 domain")
        same(order[:10], prior["queries"][q]["policies"]["S"], "fixed S reference head")
        s_orders[q] = order
    orders, diagnostics = {}, {}
    for run in sorted(plan["items"]):
        orders[run], diagnostics[run] = kernels.read_run(args.inputs / plan["items"][run]["filename"], run, docids)
    policies = kernels.build_policies(plan["groups"], s_orders, orders)
    sources = {"schema": "cycle22-grouped-sources-v1-provisional", "query_ids": QIDS, "runs": diagnostics}
    same(read_json(files["sources.json"]), sources, "all source fields")
    same(read_json(files["policies.json"]), policies, "all policy fields")
    # No label body is parsed until every retained order and ordered head agrees.
    labels = kernels.read_labels(artifact_path(plan["qrels"]["path"]))
    analysis = kernels.build_analysis(policies, labels)
    same(read_json(files["analysis.json"]), analysis, "all analysis fields")
    check_frozen(preflight)
    after = {portable(p): identity(p, True) for p in sorted(tracked)}
    same(after, before, "independent before/after custody")
    return {
        "schema": 2, "status": "passed", "identity_contract": CONTRACT,
        "method": "new current-archive custody; immutable independent Decimal/Fraction parser, policies and bounds",
        "independent_kernel": {"path": HELPER, "sha256": HELPER_SHA256},
        "audited_fields": {"sources.json": "all", "policies.json": "all", "analysis.json": "all",
                           "manifest.json": "all identities, disclosures, prior-attempt binding, phase, label gate, custody and wall cap",
                           "success.json": "all"},
        "query_count": 30, "team_count": 29, "member_count": 81, "heads_checked": 3300,
        "publisher_checksums": checksum_counts, "supersedes_failed_attempt": plan["supersedes_failed_attempt"],
        "primary": analysis["primary"], "G-S": analysis["G-S"], "denominators": analysis["denominators"],
        "team_sign_counts": analysis["team_sign_counts"], "before": before, "after": after,
        "elapsed_seconds": time.monotonic() - started,
        "limits": ["Current named archive bytes do not establish historical submitted-byte identity or explain publisher MD5 mismatches.",
                   "Acquisition is sequential with cached S, not an atomic archive snapshot.",
                   "Saved custody claims and immutable outputs are verified; this is not an OS trace of fetches or label-read timing.",
                   "Same development queries and fixed qrels; no source-independence or population inference."]}


def self_test():
    started = time.monotonic()
    old = kernels.self_test()
    checks = []
    with tempfile.TemporaryDirectory(prefix="cycle23-independent-") as directory:
        base = Path(directory)
        raw_path, decoded_path = base / "raw", base / "decoded"
        body = b"1 Q0 synthetic 0 1 run\n"
        raw_path.write_bytes(body)
        decoded_path.write_bytes(body)
        raw = identity(raw_path, True)
        item = {"publisher_md5": "0" * 32, "max_bytes": 4096, "expected_raw_sha256": raw["sha256"]}
        record = {**raw, "raw": raw, "gzip": False, "publisher_md5": item["publisher_md5"],
                  "matched_representation": [], "publisher_checksum_status": "mismatch"}
        require(verify_layers(decoded_path, raw_path, item, record, 4096)[-1] == "mismatch", "truthful mismatch accepted")
        checks.append("truthful original publisher mismatch passes the new byte contract")
        false = {**record, "matched_representation": ["raw"], "publisher_checksum_status": "match"}
        kernels.expect_failure(lambda: verify_layers(decoded_path, raw_path, item, false, 4096), "false publisher match")
        kernels.expect_failure(lambda: verify_layers(decoded_path, raw_path, {**item, "expected_raw_sha256": "0" * 64}, record, 4096),
                               "wrong first SHA")
        kernels.expect_failure(lambda: verify_layers(decoded_path, raw_path, item, {**record, "sha256": "0" * 64}, 4096),
                               "changed decoded receipt SHA")
        checks.append("false match claims, wrong first SHA and changed receipt SHA rejected")
        match_item = {**item, "publisher_md5": raw["md5"]}
        match_record = {**record, "publisher_md5": raw["md5"], "matched_representation": ["raw", "expanded"],
                        "publisher_checksum_status": "match"}
        require(verify_layers(decoded_path, raw_path, match_item, match_record, 4096)[-1] == "match", "truthful plain match")
        checks.append("truthful plain checksum match includes both representations")
        raw_path.write_bytes(gzip.compress(body, mtime=0))
        zipped = identity(raw_path, True)
        gzip_item = {"publisher_md5": raw["md5"], "max_bytes": 4096, "expected_raw_sha256": zipped["sha256"]}
        gzip_record = {**raw, "raw": zipped, "gzip": True, "publisher_md5": raw["md5"],
                       "matched_representation": ["expanded"], "publisher_checksum_status": "match"}
        require(verify_layers(decoded_path, raw_path, gzip_item, gzip_record, 4096)[3] == ["expanded"], "expanded-only match")
        kernels.expect_failure(lambda: verify_layers(decoded_path, raw_path, gzip_item, gzip_record, len(body) - 1), "expansion cap")
        decoded_path.write_bytes(b"different\n")
        inconsistent = {**gzip_record, **identity(decoded_path, True)}
        kernels.expect_failure(lambda: verify_layers(decoded_path, raw_path, gzip_item, inconsistent, 4096), "gzip decode disagreement")
        checks.append("gzip representation provenance, expansion cap and decode disagreement checked")
        url = "https://ir.nist.gov/trec-covid/archive/round1/synthetic"
        transport = {"url": url, "effective_url": url, "http_code": 200,
                     "headers": {"Content-Type": "text/plain", "Content-Length": str(raw["bytes"])}}
        verify_transport({"url": url}, transport, raw)
        bad_transports = [
            {**transport, "effective_url": url + "/redirect"},
            {**transport, "http_code": 302},
            {**transport, "headers": {"Set-Cookie": "synthetic-only"}},
            {**transport, "headers": {"Content-Type": "text/html"}},
            {**transport, "headers": {"Content-Encoding": "gzip"}},
            {**transport, "headers": {"Content-Length": str(raw["bytes"] + 1)}},
        ]
        for value in bad_transports:
            kernels.expect_failure(lambda value=value: verify_transport({"url": url}, value, raw), "unsafe or inconsistent transport")
        checks.append("redirect, status, cookie header, HTML, content encoding and length rejection")
    return {"schema": 2, "status": "passed", "identity_contract": CONTRACT,
            "independent_kernel": {"path": HELPER, "sha256": HELPER_SHA256},
            "inherited_kernel_tests": old["tests"], "new_contract_tests": checks,
            "elapsed_seconds": time.monotonic() - started}


def timed_out(signum, frame):
    raise TimeoutError("Cycle23 independent verifier exceeded 300-second wall cap")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    for name in ("result", "preflight", "inputs", "acquisition", "output"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(300)
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    require(all(getattr(args, key) is not None for key in ("result", "preflight", "inputs", "acquisition", "output")),
            "all execution paths required")
    require(not args.output.exists(), "refusing to overwrite verifier receipt")
    started = time.monotonic()
    try:
        result = verify(args)
        result["command"] = sys.argv
    except Exception as error:
        result = {"schema": 2, "status": "failed", "identity_contract": CONTRACT, "error_type": type(error).__name__,
                  "error": str(error), "command": sys.argv, "elapsed_seconds": time.monotonic() - started}
    finally:
        signal.alarm(0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "elapsed_seconds")}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
