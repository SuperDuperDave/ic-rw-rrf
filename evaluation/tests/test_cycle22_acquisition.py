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

PATH = Path(__file__).resolve().parents[2] / "_sessions/tools/acquire_cycle22_inputs.py"
SPEC = importlib.util.spec_from_file_location("cycle22_acquisition", PATH)
acquire = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquire)


class AcquisitionTests(unittest.TestCase):
    def test_initial_identity_failure_is_recorded_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / "inventory").write_text("known metadata")
            (p / "preflight.json").write_text(json.dumps({"status": "passed", "frozen": {}}))
            (p / "plan.json").write_text(json.dumps({
                "groups": {"team": ["run"]}, "items": {"run": {}}, "max_run_count": 180,
                "inventory": {"path": str(p / "inventory"), "sha256": "0" * 64},
            }))
            args = SimpleNamespace(preflight=p / "preflight.json", inputs=p / "inputs", receipt=p / "receipt.json")
            with patch.object(acquire, "PLAN", p / "plan.json"), patch.object(acquire, "check_frozen"), patch.object(acquire.urllib.request, "build_opener") as network:
                with self.assertRaisesRegex(ValueError, "known input identity changed"):
                    acquire.acquire(args)
                network.assert_not_called()
            saved = json.loads(args.receipt.read_text())
            self.assertEqual(saved["status"], "failed")
            self.assertEqual(saved["error_type"], "ValueError")
            self.assertFalse(args.inputs.exists())
            original = args.receipt.read_bytes()
            with self.assertRaises(FileExistsError):
                acquire.acquire(args)
            self.assertEqual(args.receipt.read_bytes(), original)

    def test_exact_limit_and_overflow_preserve_bounded_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            self.assertEqual(acquire.bounded_copy(io.BytesIO(b"abc"), p / "exact", 3), 3)
            with self.assertRaises(ValueError):
                acquire.bounded_copy(io.BytesIO(b"abcdef"), p / "partial", 3)
            self.assertEqual((p / "partial").read_bytes(), b"abc")
            with self.assertRaises(FileExistsError):
                acquire.bounded_copy(io.BytesIO(b"new"), p / "exact", 3)

    def test_gzip_identity_layers_and_expansion_limit(self):
        data = b"1 Q0 example1 0 0.5 run\n"
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            raw = p / "raw"
            raw.write_bytes(gzip.compress(data, mtime=0))
            result = acquire.materialize(raw, p / "decoded", hashlib.md5(data).hexdigest(), 100)
            self.assertTrue(result["gzip"])
            self.assertEqual(result["matched_representation"], ["expanded"])
            self.assertEqual((p / "decoded").read_bytes(), data)
            result = acquire.materialize(raw, p / "decoded2", hashlib.md5(raw.read_bytes()).hexdigest(), 100)
            self.assertEqual(result["matched_representation"], ["raw"])
            with self.assertRaises(ValueError):
                acquire.materialize(raw, p / "oversized", hashlib.md5(data).hexdigest(), 4)
            self.assertEqual((p / "oversized").stat().st_size, 4)
            with self.assertRaises(ValueError):
                acquire.materialize(raw, p / "wrong", "0" * 32, 100)

    def test_public_headers_exclude_cookie_and_authorization(self):
        original = {"Content-Type": "text/plain", "ETag": "test", "Set-Cookie": "private", "Authorization": "private"}
        public = acquire.public_headers(original)
        self.assertEqual(public, {"Content-Type": "text/plain", "ETag": "test"})
        self.assertIn("Set-Cookie", original)


if __name__ == "__main__":
    unittest.main()
