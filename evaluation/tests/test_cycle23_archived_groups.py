"""Synthetic identity-contract tests; no empirical body or label access."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle22_grouped_outputs as old
from evaluation import cycle23_archived_groups as producer
from evaluation.tests.test_cycle22_grouped_outputs import make_cli_fixture


REPO = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def make_archive_fixture(root, full_depth=100, include_short=True):
    """Construct a fresh synthetic failed parent and a separately sealed snapshot.

    Repository source dependencies use their actual immutable bytes. The prior
    protocol/plan/preflight and failure are synthetic; no research inputs enter.
    """
    root = Path(root)
    old_preflight_path, inputs, old_receipt_path, _ = make_cli_fixture(root, full_depth, include_short)
    base_receipt = json.loads(old_receipt_path.read_text())
    old_plan = json.loads((root / old.PLAN).read_text())
    inventory_path = root / old_plan["inventory"]["path"]
    inventory = json.loads(inventory_path.read_text())
    index = {row["run"]: row for row in inventory["runs"]}
    for number, run in enumerate(sorted(old_plan["items"])):
        if number % 2 == 0:
            old_plan["items"][run]["publisher_md5"] = "0" * 32
            index[run]["publisher_md5"] = "0" * 32
    write_json(inventory_path, inventory)
    old_plan["inventory"].update(old.identity(inventory_path))
    write_json(root / old.PLAN, old_plan)
    old_frozen = json.loads(old_preflight_path.read_text())["frozen"]
    for relative in old_frozen:
        if relative != old.PLAN:
            (root / relative).write_bytes((REPO / relative).read_bytes())
    old_frozen = {relative: old.identity(root / relative)["sha256"] for relative in old_frozen}
    write_json(old_preflight_path, {"schema": 1, "status": "passed", "frozen": old_frozen})
    first_run = sorted(old_plan["items"])[0]
    first = old_plan["items"][first_run]
    prior_failure = {"schema": 1, "status": "failed", "active_run": first_run,
                     "preflight_sha256": old.identity(old_preflight_path)["sha256"],
                     "plan_sha256": old.identity(root / old.PLAN)["sha256"], "frozen": old_frozen,
                     "error_type": "ValueError", "error": "publisher MD5 matches neither representation",
                     "partial_files": {name: old.identity(inputs / name) for name in
                                       (first["filename"], first["filename"] + ".download")}}
    write_json(old_receipt_path, prior_failure)
    plan = deepcopy(old_plan)
    plan.update(schema=2, identity_contract=producer.CONTRACT,
                supersedes_failed_attempt={"preflight": old_preflight_path.name,
                                           "acquisition": old_receipt_path.name, "preserve_failure": True})
    plan["items"][first_run]["expected_raw_sha256"] = prior_failure["partial_files"][first["filename"] + ".download"]["sha256"]
    for relative in producer.REQUIRED - set(old_frozen) - {producer.PLAN}:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((REPO / relative).read_bytes())
    write_json(root / producer.PLAN, plan)
    frozen = {**old_frozen, **{relative: old.identity(root / relative)["sha256"] for relative in producer.REQUIRED},
              old_preflight_path.name: old.identity(old_preflight_path)["sha256"],
              old_receipt_path.name: old.identity(old_receipt_path)["sha256"]}
    preflight_path, receipt_path = root / "cycle23-preflight.json", root / "cycle23-acquisition.json"
    write_json(preflight_path, {"schema": 1, "status": "passed", "frozen": frozen})
    receipt = deepcopy(base_receipt)
    receipt.update(schema=2, identity_contract=producer.CONTRACT, frozen=frozen,
                   preflight_sha256=old.identity(preflight_path)["sha256"],
                   plan_sha256=old.identity(root / producer.PLAN)["sha256"],
                   supersedes_failed_attempt=plan["supersedes_failed_attempt"])
    for run, record in receipt["inputs"].items():
        record["publisher_md5"] = plan["items"][run]["publisher_md5"]
        record["matched_representation"] = [name for name, layer in (("raw", record["raw"]), ("expanded", record))
                                            if layer["md5"] == record["publisher_md5"]]
        record["publisher_checksum_status"] = "match" if record["matched_representation"] else "mismatch"
    receipt["publisher_checksums"] = {status: sum(v["publisher_checksum_status"] == status for v in receipt["inputs"].values())
                                      for status in ("match", "mismatch")}
    write_json(receipt_path, receipt)
    return preflight_path, inputs, receipt_path, root / "cycle23-output"


class ArchivedGroupsTests(unittest.TestCase):
    def test_immutable_functions_are_used_directly(self):
        for name in ("parse_docids", "parse_run", "parse_qrels", "build_policies", "analyze"):
            self.assertIs(getattr(producer, name), getattr(old, name))

    def test_truthful_mismatch_and_unchanged_science(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_archive_fixture(tmp)
            parent_before = {name: (Path(tmp) / name).read_bytes() for name in ("preflight.json", "acquisition.json", old.PLAN)}
            with patch.object(producer, "ROOT", Path(tmp)):
                manifest = producer.execute(*paths)
            self.assertEqual(manifest["publisher_checksums"], {"match": 40, "mismatch": 41})
            self.assertEqual(manifest["phase"], "cycle23")
            self.assertEqual(manifest["identity_contract"], producer.CONTRACT)
            self.assertEqual(manifest["tracked_before"], manifest["tracked_after"])
            self.assertEqual(manifest["inputs"][sorted(manifest["inputs"])[0]]["matched_representation"], [])
            p = json.loads((paths[3] / "policies.json").read_text())
            a = json.loads((paths[3] / "analysis.json").read_text())
            labels = old.parse_qrels((Path(tmp) / "cached/late.qrels").read_text())
            self.assertEqual(a, old.analyze(p, labels))
            self.assertEqual(p, old.build_policies(p["groups"], p["retained"]["members"], p["retained"]["S"], p["query_ids"]))
            self.assertEqual(parent_before, {name: (Path(tmp) / name).read_bytes() for name in parent_before})
            before = (paths[3] / "success.json").read_bytes()
            with patch.object(producer, "ROOT", Path(tmp)), self.assertRaises(FileExistsError):
                producer.execute(*paths)
            self.assertEqual((paths[3] / "success.json").read_bytes(), before)

    def test_old_md5_rejection_remains_intact(self):
        module_spec = importlib.util.spec_from_file_location("cycle22_acquisition_for_test", REPO / old.ACQUIRER)
        legacy = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(legacy)
        with tempfile.TemporaryDirectory() as tmp:
            raw, decoded = Path(tmp) / "raw", Path(tmp) / "decoded"
            raw.write_bytes(b"synthetic plain bytes\n")
            with self.assertRaisesRegex(ValueError, "publisher MD5"):
                legacy.materialize(raw, decoded, "0" * 32, 1000)

    def assert_custody_failure(self, change, message=None):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_archive_fixture(tmp)
            receipt = json.loads(paths[2].read_text())
            change(paths, receipt)
            write_json(paths[2], receipt)
            with patch.object(producer, "ROOT", Path(tmp)), patch.object(producer, "parse_run") as parse:
                with self.assertRaisesRegex((ValueError, KeyError), message or ".*"):
                    producer.execute(*paths)
                parse.assert_not_called()
            self.assertEqual(json.loads((paths[3] / "failure.json").read_text())["stage"], "custody")
            self.assertFalse((paths[3] / "policies.json").exists())

    def test_false_checksum_claim_rejected(self):
        def change(paths, receipt):
            receipt["inputs"][sorted(receipt["inputs"])[0]]["publisher_checksum_status"] = "match"
        self.assert_custody_failure(change, "observation is false")

    def test_changed_sha_rejected(self):
        def change(paths, receipt):
            receipt["inputs"][sorted(receipt["inputs"])[0]]["sha256"] = "0" * 64
        self.assert_custody_failure(change, "identity mismatch")

    def test_raw_decoded_disagreement_rejected(self):
        def change(paths, receipt):
            row = receipt["inputs"][sorted(receipt["inputs"])[0]]
            decoded = paths[1] / row["filename"]
            decoded.write_bytes(decoded.read_bytes() + b"changed\n")
            row.update(old.identity(decoded))
        self.assert_custody_failure(change, "representations disagree")

    def test_missing_member_rejected(self):
        def change(paths, receipt):
            receipt["inputs"].pop(sorted(receipt["inputs"])[-1])
        self.assert_custody_failure(change, "census differs")

    def test_private_or_redirected_transport_rejected(self):
        for kind in ("cookie", "redirect"):
            def change(paths, receipt):
                row = receipt["transport"][sorted(receipt["transport"])[0]]
                if kind == "cookie":
                    row["headers"]["Set-Cookie"] = "synthetic-secret"
                else:
                    row["effective_url"] += "?different"
            self.assert_custody_failure(change, "transport")

    def test_old_contract_receipt_cannot_pass(self):
        def change(paths, receipt):
            receipt["schema"] = 1
            receipt.pop("identity_contract")
        self.assert_custody_failure(change, "identity contract")

    def test_wrong_first_pin_rejected(self):
        def change(paths, receipt):
            root = paths[0].parent
            plan = json.loads((root / producer.PLAN).read_text())
            plan["items"][sorted(plan["items"])[0]]["expected_raw_sha256"] = "0" * 64
            write_json(root / producer.PLAN, plan)
            preflight = json.loads(paths[0].read_text())
            preflight["frozen"][producer.PLAN] = old.identity(root / producer.PLAN)["sha256"]
            write_json(paths[0], preflight)
            receipt.update(frozen=preflight["frozen"], plan_sha256=old.identity(root / producer.PLAN)["sha256"],
                           preflight_sha256=old.identity(paths[0])["sha256"])
        self.assert_custody_failure(change, "first raw SHA")

    def test_policies_precede_label_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_archive_fixture(tmp)
            def checked(text):
                self.assertTrue((paths[3] / "policies.json").exists())
                self.assertTrue((paths[3] / "sources.json").exists())
                return old.parse_qrels(text)
            with patch.object(producer, "ROOT", Path(tmp)), patch.object(producer, "parse_qrels", checked):
                producer.execute(*paths)
            self.assertIs(producer.parse_qrels, old.parse_qrels)

    def test_after_hash_preserves_failed_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_archive_fixture(tmp)
            def tamper(policies, labels):
                result = old.analyze(policies, labels)
                with (Path(tmp) / "acquisition.json").open("a") as handle:
                    handle.write(" ")
                return result
            with patch.object(producer, "ROOT", Path(tmp)), patch.object(producer, "analyze", tamper):
                with self.assertRaisesRegex(ValueError, "bytes changed"):
                    producer.execute(*paths)
            self.assertFalse((paths[3] / "success.json").exists())
            self.assertTrue((paths[3] / "failure.json").exists())


if __name__ == "__main__":
    unittest.main()
