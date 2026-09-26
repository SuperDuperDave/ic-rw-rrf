#!/usr/bin/env python3
"""Publish only selected HTTP metadata; keep frozen original receipts local."""
import copy
import hashlib
import json
from pathlib import Path
import sys

SAFE_HEADERS = {"content-length", "content-type", "content-encoding", "etag",
                "last-modified", "date", "cache-control"}


def public_value(value):
    result = copy.deepcopy(value)
    for transport in result.get("transport", {}).values():
        if "headers" in transport:
            transport["headers"] = {key: val for key, val in transport["headers"].items()
                                    if key.lower() in SAFE_HEADERS}
    result["http_header_scope"] = "Selected public metadata only; response cookies omitted."
    return result


def export(source):
    source = Path(source)
    target = source.with_name(source.stem + "-public.json")
    value = public_value(json.loads(source.read_text()))
    value["original_receipt_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    with target.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(target)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        print(export(path))
