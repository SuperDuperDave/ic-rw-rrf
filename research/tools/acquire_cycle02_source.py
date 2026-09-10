#!/usr/bin/env python3
"""Acquire a frozen source selection and emit text-free TREC runs.

Usage (relative paths resolve against the repository, from any working directory):
  python3 /path/to/repo/_sessions/tools/acquire_cycle02_source.py \
    --selection data/cycle02/source-selection.json \
    --cache-dir _sessions/local/cycle02/source-cache \
    --output data/cycle02/acquired

Selection schema (additional metadata is permitted but is not copied to outputs):
  {"source_id": "example", "dataset_id": "owner/dataset",
   "dataset_revision": "pinned-revision", "files": [
     {"year": 2019, "filename": "dl19_top1000.jsonl",
      "url": "https://example.org/pinned-revision/dl19_top1000.jsonl",
      "expected_bytes": 1234, "expected_sha256": "64 lowercase hex digits"}]}

Each input line must contain {"query": {"qid": "1", "text": "..."},
"candidates": [{"docid": "2", "score": 0.5, "doc": {"contents": "..."}}]}.
IDs may also be integers. Candidate arrays must already have nonincreasing
finite numeric scores. Their order, including ties, becomes one-based TREC rank.
No qrels are read and no query or passage text is written to the output directory.
The raw cache DOES contain source text and should remain in an ignored location.

The output directory must not exist. On failure only this invocation's partial
outputs are removed; verified cache artifacts may remain. A success manifest is
written last. The manifest records selection and script hashes, original input
provenance, observed depths/ties, and repository-relative derived run paths.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
CHUNK_BYTES = 64 * 1024


class AcquisitionError(ValueError):
    """A safely reportable error that contains no input record text."""


def safe_id(value, field):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise AcquisitionError(f"Invalid {field}: expected a string or integer ID")
    value = str(value)
    if not value or any(char.isspace() or not char.isprintable() for char in value):
        raise AcquisitionError(f"Invalid {field}: empty, whitespace, or control character")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AcquisitionError("JSON object contains duplicate keys")
        result[key] = value
    return result


def parse_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique_object)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise AcquisitionError("Invalid JSON input") from error


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_selection(path):
    raw = Path(path).read_bytes()
    selection = parse_json(raw)
    if not isinstance(selection, dict):
        raise AcquisitionError("Selection must be an object")
    source_id = safe_id(selection.get("source_id"), "source_id")
    for key in ("dataset_id", "dataset_revision"):
        if not isinstance(selection.get(key), str) or not selection[key].strip():
            raise AcquisitionError(f"Selection requires a nonempty {key}")
    files = selection.get("files")
    if not isinstance(files, list) or not files:
        raise AcquisitionError("Selection requires a nonempty files array")
    seen_years, seen_names = set(), set()
    for item in files:
        if not isinstance(item, dict):
            raise AcquisitionError("Selected file must be an object")
        year = item.get("year")
        if isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 9999:
            raise AcquisitionError("Selected year must be a four-digit integer")
        filename = item.get("filename")
        if (not isinstance(filename, str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]+\.jsonl", filename)
                or filename.startswith(".")):
            raise AcquisitionError("Selected filename must be a plain JSONL basename")
        if year in seen_years or filename in seen_names:
            raise AcquisitionError("Selection contains duplicate years or filenames")
        seen_years.add(year)
        seen_names.add(filename)
        size = item.get("expected_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise AcquisitionError("Selected expected_bytes must be a positive integer")
        digest = item.get("expected_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AcquisitionError("Selected SHA256 must be 64 lowercase hex digits")
        url = item.get("url")
        if not isinstance(url, str):
            raise AcquisitionError("Selected URL must be HTTPS")
        try:
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or parsed.fragment
                    or any(char.isspace() for char in url)):
                raise AcquisitionError("Selected URL must be HTTPS without credentials or fragments")
        except ValueError as error:
            raise AcquisitionError("Invalid selected URL") from error
    selection["source_id"] = source_id
    return selection, hashlib.sha256(raw).hexdigest()


def cache_matches(path, item):
    return (path.is_file() and path.stat().st_size == item["expected_bytes"]
            and sha256_file(path) == item["expected_sha256"])


def acquire_raw(item, cache_dir, opener=None):
    """Verify reuse or download with both a streaming byte cap and SHA256 check."""
    opener = opener or urlopen
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / (item["expected_sha256"] + "-" + item["filename"])
    if cache_matches(cached, item):
        return cached, True
    temporary = None
    try:
        request = Request(item["url"], headers={"Accept-Encoding": "identity",
                                              "User-Agent": "IC-RW-RRF-source-acquisition/1"})
        with opener(request, timeout=60) as response:
            if getattr(response, "status", 200) != 200:
                raise AcquisitionError("Download did not return HTTP 200")
            supplied_length = response.headers.get("Content-Length")
            if supplied_length is not None:
                try:
                    length = int(supplied_length)
                except (ValueError, TypeError) as error:
                    raise AcquisitionError("Invalid Content-Length header") from error
                if length != item["expected_bytes"]:
                    raise AcquisitionError("Content-Length differs from frozen expected_bytes")
            with tempfile.NamedTemporaryFile(mode="wb", dir=cache_dir,
                                             prefix=".cycle02-", delete=False) as stream:
                temporary = Path(stream.name)
                digest, total = hashlib.sha256(), 0
                while True:
                    chunk = response.read(min(CHUNK_BYTES, item["expected_bytes"] - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > item["expected_bytes"]:
                        raise AcquisitionError("Download exceeds frozen expected_bytes")
                    stream.write(chunk)
                    digest.update(chunk)
                if total != item["expected_bytes"]:
                    raise AcquisitionError("Download byte count differs from frozen expected_bytes")
                if digest.hexdigest() != item["expected_sha256"]:
                    raise AcquisitionError("Download SHA256 differs from frozen expected_sha256")
                stream.flush()
                os.fsync(stream.fileno())
        os.replace(temporary, cached)
        temporary = None
        return cached, False
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def convert_jsonl(input_path, output_path, source_id):
    """Convert without changing eligibility, candidates, score values, or tie order."""
    source_id = safe_id(source_id, "source_id")
    seen_queries = set()
    depths = []
    ties = queries_with_ties = rows = 0
    output_path = Path(output_path)
    created = False
    try:
        with Path(input_path).open("rb") as source, output_path.open("x", encoding="utf-8", newline="\n") as target:
            created = True
            for line_number, raw in enumerate(source, 1):
                try:
                    record = parse_json(raw)
                    if not isinstance(record, dict):
                        raise AcquisitionError("Record must be an object")
                    query = record.get("query")
                    if not isinstance(query, dict) or not isinstance(query.get("text"), str):
                        raise AcquisitionError("Record requires query object with text string")
                    qid = safe_id(query.get("qid"), "query ID")
                    if qid in seen_queries:
                        raise AcquisitionError("Duplicate query ID")
                    seen_queries.add(qid)
                    candidates = record.get("candidates")
                    if not isinstance(candidates, list) or not candidates:
                        raise AcquisitionError("Record requires a nonempty candidates array")
                    seen_docs = set()
                    previous = None
                    query_ties = 0
                    for rank, candidate in enumerate(candidates, 1):
                        if (not isinstance(candidate, dict)
                                or not isinstance(candidate.get("doc"), (dict, str))):
                            raise AcquisitionError("Candidate requires an object with doc object or string")
                        docid = safe_id(candidate.get("docid"), "document ID")
                        if docid in seen_docs:
                            raise AcquisitionError("Duplicate document ID within query")
                        seen_docs.add(docid)
                        score = candidate.get("score")
                        if isinstance(score, bool) or not isinstance(score, (int, float)):
                            raise AcquisitionError("Score must be a finite number")
                        try:
                            finite = math.isfinite(score)
                        except OverflowError:
                            finite = False
                        if not finite:
                            raise AcquisitionError("Score must be a finite number")
                        if previous is not None:
                            if score > previous:
                                raise AcquisitionError("Candidate scores must be nonincreasing")
                            if score == previous:
                                query_ties += 1
                        previous = score
                        target.write(f"{qid} Q0 {docid} {rank} {score!r} {source_id}\n")
                    depths.append(len(candidates))
                    rows += len(candidates)
                    ties += query_ties
                    queries_with_ties += bool(query_ties)
                except AcquisitionError as error:
                    raise AcquisitionError(f"Input line {line_number}: {error}") from error
            if not depths:
                raise AcquisitionError("Input contains no query records")
            target.flush()
            os.fsync(target.fileno())
        return {"query_count": len(depths), "row_count": rows,
                "depth_min": min(depths), "depth_max": max(depths),
                "adjacent_score_ties": ties, "queries_with_score_ties": queries_with_ties,
                "rank_origin": 1, "tie_policy": "preserve candidate array order"}
    except BaseException:
        if created:
            output_path.unlink(missing_ok=True)
        raise


def rooted(path, root):
    path = Path(path)
    return (path if path.is_absolute() else root / path).resolve()


def acquire(selection_path, cache_dir, output_dir, *, root=ROOT, opener=None):
    root = Path(root).resolve()
    selection_path, cache_dir, output_dir = (
        rooted(path, root) for path in (selection_path, cache_dir, output_dir))
    try:
        relative_output = output_dir.relative_to(root)
    except ValueError as error:
        raise AcquisitionError("Output directory must be inside the repository") from error
    if cache_dir == output_dir or output_dir in cache_dir.parents:
        raise AcquisitionError("Raw cache must be outside the output directory")
    selection, selection_hash = load_selection(selection_path)
    if output_dir.exists():
        raise AcquisitionError("Output directory already exists; choose a fresh directory")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir()  # Exclusive reservation; never replace an existing output directory.
    owned = []
    try:
        inputs, derived = [], []
        for item in selection["files"]:
            raw, reused = acquire_raw(item, cache_dir, opener=opener)
            filename = f"dl{item['year']}.trec"
            run_path = output_dir / filename
            stats = convert_jsonl(raw, run_path, selection["source_id"])
            owned.append(run_path)
            original = {"year": item["year"], "filename": item["filename"],
                        "url": item["url"], "sha256": item["expected_sha256"],
                        "bytes": item["expected_bytes"], "cache_reused": reused}
            inputs.append(original)
            derived.append({"year": item["year"],
                            "path": (relative_output / filename).as_posix(),
                            "sha256": sha256_file(run_path), "bytes": run_path.stat().st_size,
                            **stats})
        command = shlex.join([sys.executable, str(Path(__file__).resolve()),
                              "--selection", str(selection_path),
                              "--cache-dir", str(cache_dir), "--output", str(output_dir)])
        manifest = {"schema_version": 1, "source_id": selection["source_id"],
                    "dataset_id": selection["dataset_id"],
                    "dataset_revision": selection["dataset_revision"],
                    "selection_sha256": selection_hash,
                    "script_sha256": sha256_file(Path(__file__).resolve()),
                    "command": command, "original_inputs": inputs, "derived_runs": derived}
        manifest_path = output_dir / "source-manifest.json"
        partial_manifest = output_dir / ".source-manifest.json.partial"
        with partial_manifest.open("x", encoding="utf-8", newline="\n") as stream:
            owned.append(partial_manifest)
            stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic publication without replacing a concurrently created file.
        os.link(partial_manifest, manifest_path)
        owned.append(manifest_path)
        partial_manifest.unlink()
        return manifest
    except BaseException:
        for path in reversed(owned):
            path.unlink(missing_ok=True)
        try:
            output_dir.rmdir()
        except OSError:
            pass  # Preserve any files created concurrently by another process.
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selection", required=True, help="Frozen source-selection JSON")
    parser.add_argument("--cache-dir", required=True, help="Raw JSONL cache (contains source text)")
    parser.add_argument("--output", required=True, help="Fresh repository output directory")
    args = parser.parse_args(argv)
    try:
        manifest = acquire(args.selection, args.cache_dir, args.output)
    except AcquisitionError as error:
        print(f"Acquisition failed: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        # Transport/filesystem errors can contain server-controlled text or URLs.
        print(f"Acquisition failed: {type(error).__name__}", file=sys.stderr)
        return 1
    print(f"Acquired {len(manifest['derived_runs'])} verified run files; source-manifest.json written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
