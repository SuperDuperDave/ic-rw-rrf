import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[2] / "_sessions/tools/acquire_cycle23_inputs.py"
SPEC = importlib.util.spec_from_file_location("cycle23_acquisition", PATH)
acquire = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquire)


class Response(io.BytesIO):
    def __init__(self, url, body, unsafe=False):
        super().__init__(body)
        self.url = url + ("/unexpected" if unsafe else "")
        self.status = 200
        self.headers = {"Content-Type": "text/plain", "Content-Length": str(len(body)), "Set-Cookie": "private"}


class AcquisitionTests(unittest.TestCase):
    def test_truthful_mismatch_and_preserved_old_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            raw = p / "raw"
            raw.write_bytes(b"unchanged archive representation\n")
            result = acquire.materialize(raw, p / "new", "0" * 32, 100)
            self.assertEqual(result["publisher_checksum_status"], "mismatch")
            self.assertEqual(result["matched_representation"], [])
            self.assertEqual(result["publisher_md5"], "0" * 32)
            self.assertEqual(result["sha256"], result["raw"]["sha256"])
            with self.assertRaisesRegex(ValueError, "publisher MD5"):
                acquire.transport.materialize(raw, p / "old", "0" * 32, 100)

    def test_wrong_stability_pin_stops_before_decoding(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            raw = p / "raw"
            raw.write_bytes(b"body\n")
            with self.assertRaisesRegex(ValueError, "SHA256 changed"):
                acquire.materialize(raw, p / "new", "0" * 32, 100, "0" * 64)
            self.assertFalse((p / "new").exists())

    def test_gzip_layer_status_and_expansion_ceiling(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            body = b"archive data\n"
            raw = p / "raw"
            raw.write_bytes(gzip.compress(body, mtime=0))
            result = acquire.materialize(raw, p / "decoded", hashlib.md5(body).hexdigest(), 100)
            self.assertEqual(result["publisher_checksum_status"], "match")
            self.assertEqual(result["matched_representation"], ["expanded"])
            with self.assertRaisesRegex(ValueError, "ceiling"):
                acquire.materialize(raw, p / "too-large", "0" * 32, 3)
            self.assertEqual((p / "too-large").stat().st_size, 3)

    def test_initial_failure_recorded_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            preflight = p / "preflight.json"
            preflight.write_text('{"status":"failed"}')
            args = SimpleNamespace(inputs=p / "inputs", preflight=preflight, receipt=p / "receipt.json")
            with patch.object(acquire.urllib.request, "build_opener") as opener:
                with self.assertRaisesRegex(ValueError, "preflight"):
                    acquire.acquire(args)
                opener.assert_not_called()
            original = args.receipt.read_bytes()
            self.assertEqual(json.loads(original)["status"], "failed")
            with self.assertRaises(FileExistsError):
                acquire.acquire(args)
            self.assertEqual(args.receipt.read_bytes(), original)

    def run_mocked_acquisition(self, p, unsafe=False):
        names = [f"run{i:03}" for i in range(81)]
        groups = {}
        cursor = 0
        for i in range(29):
            count = 3 if i < 23 else 2
            groups[f"team{i}"] = names[cursor:cursor + count]
            cursor += count
        body = b"synthetic transport fixture\n"
        expected = hashlib.sha256(body).hexdigest()
        known = p / "known"
        known.write_bytes(b"synthetic custody input")
        prior_freeze = p / "prior-preflight.json"
        prior_freeze.write_text('{"frozen":{}}')
        prior_failure = p / "prior-failure.json"
        prior_failure.write_text(json.dumps({"status": "failed", "active_run": names[0],
            "partial_files": {"000.run.download": {"sha256": expected}}}))
        frozen = {str(prior_freeze): "fixture", str(prior_failure): "fixture"}
        preflight = p / "preflight.json"
        preflight.write_text(json.dumps({"status": "passed", "frozen": frozen}))
        plan = {"schema": 2, "identity_contract": acquire.CONTRACT, "groups": groups,
            "max_run_count": 180, "max_acquisition_seconds": 900, "max_total_bytes": 100000,
            "max_expanded_per_run": 1000, "max_total_expanded_bytes": 100000, "timeout_seconds": 60,
            "supersedes_failed_attempt": {"preflight": str(prior_freeze), "acquisition": str(prior_failure), "preserve_failure": True},
            "items": {n: {"filename": f"{i:03}.run", "url": "https://ir.nist.gov/trec-covid/archive/round1/" + n,
                          "max_bytes": 1000, "publisher_md5": "0" * 32} for i, n in enumerate(names)}}
        plan["items"][names[0]]["expected_raw_sha256"] = expected
        for key in ("inventory", "S", "prior_verification", "docids", "qrels"):
            plan[key] = {"path": str(known), "sha256": hashlib.sha256(known.read_bytes()).hexdigest()}
        plan_path = p / "plan.json"
        plan_path.write_text(json.dumps(plan))
        args = SimpleNamespace(inputs=p / "inputs", preflight=preflight, receipt=p / "receipt.json")
        # Only transport orchestration is exercised here. Complete frozen custody
        # is independently tested by the producer/checker fixtures before freeze.
        with patch.object(acquire, "PLAN", plan_path), patch.object(acquire, "check_frozen"), patch.object(acquire.urllib.request, "build_opener") as network:
            network.return_value.open.side_effect = lambda request, timeout: Response(request.full_url, body, unsafe)
            if unsafe:
                with self.assertRaisesRegex(ValueError, "HTTP response"):
                    acquire.acquire(args)
                self.assertEqual(network.return_value.open.call_count, 1)
            else:
                acquire.acquire(args)
                self.assertEqual(network.return_value.open.call_count, 81)
        return json.loads(args.receipt.read_text())

    def test_complete_transport_frame_preserves_every_mismatch_and_safe_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_mocked_acquisition(Path(directory))
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["identity_contract"], acquire.CONTRACT)
            self.assertEqual(result["publisher_checksums"], {"match": 0, "mismatch": 81})
            self.assertEqual(len(result["inputs"]), 81)
            self.assertTrue(all("Set-Cookie" not in row["headers"] for row in result["transport"].values()))

    def test_wrong_effective_url_preserves_failure_before_body_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_mocked_acquisition(Path(directory), unsafe=True)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["inputs"], {})
            self.assertEqual(result["transfer_bytes_complete_bodies"], 0)


if __name__ == "__main__":
    unittest.main()
