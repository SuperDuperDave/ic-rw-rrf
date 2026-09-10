"""Exercise the wrapper with disposable executables, never real providers."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


FAKE = r'''#!/usr/bin/python3
import json, os, pathlib, signal, sys, time
arguments = sys.argv[1:]
kind = pathlib.Path(sys.argv[0]).name.split()[0]
record = {"kind": kind, "argv": arguments, "cwd": os.getcwd()}
if kind == "claude":
    record["stdin"] = sys.stdin.read()
    if os.environ.get("TEST_RELAY_WAIT"):
        record["pid"] = os.getpid()
with open(os.environ["TEST_RELAY_LOG"], "a") as stream:
    stream.write(json.dumps(record) + "\n")
if os.environ.get("TEST_RELAY_FAIL") and kind == "relay":
    sys.exit(17)
if kind == "relay" and "provider-config" in arguments:
    hooks = ["--settings", '{"hooks":{"note":"quote \' $();\\n"}}']
    if os.environ.get("TEST_RELAY_BAD_PLAN"):
        hooks = [123]
    print(json.dumps({"schema": 1, "provider": "claude",
                     "repo": arguments[arguments.index("--repo") + 1],
                     "native_arguments": hooks}))
if kind == "claude" and os.environ.get("TEST_RELAY_SIGNAL"):
    os.kill(os.getpid(), signal.SIGTERM)
if kind == "claude" and os.environ.get("TEST_RELAY_WAIT"):
    time.sleep(30)
sys.exit(int(os.environ.get("TEST_RELAY_EXIT", "0")))
'''


class RelayHelperTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repo = self.directory / "project with spaces"
        self.script = self.repo / "_sessions/tools/relay.py"
        self.script.parent.mkdir(parents=True)
        shutil.copyfile(Path(__file__).resolve().parents[1] / "relay.py", self.script)
        self.log = self.directory / "calls.jsonl"
        self.environment = dict(os.environ, TEST_RELAY_LOG=str(self.log))
        for kind in ("relay", "claude"):
            executable = self.directory / (kind + " executable")
            executable.write_text(FAKE)
            executable.chmod(0o700)
            self.environment["IC_RRF_{}_BIN".format(kind.upper())] = str(executable)

    def invoke(self, *arguments):
        result = subprocess.run(
            [sys.executable, str(self.script)] + list(arguments),
            cwd=str(self.directory), env=self.environment, input="native stdin\n",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10,
        )
        records = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return result, records

    def test_standard_relay_arguments_keep_project_scope_and_exit(self):
        self.environment["TEST_RELAY_EXIT"] = "23"
        result, calls = self.invoke("--json", "status", "--compact")
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(calls, [{"kind": "relay", "cwd": str(self.repo),
                                 "argv": ["--repo", str(self.repo), "--json", "status", "--compact"]}])

    def test_claude_receives_exact_settings_arguments_stdin_and_cwd(self):
        prompt = "quotes ' $() ; and\na second line"
        result, calls = self.invoke("claude", "--print", prompt)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call["kind"] for call in calls], ["relay", "claude"])
        self.assertEqual(calls[1]["argv"], ["--settings", '{"hooks":{"note":"quote \' $();\\n"}}', "--print", prompt])
        self.assertEqual(calls[1]["cwd"], str(self.repo))
        self.assertEqual(calls[1]["stdin"], "native stdin\n")

    def test_plan_never_starts_claude(self):
        result, calls = self.invoke("claude-plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["repo"], str(self.repo))
        self.assertEqual([call["kind"] for call in calls], ["relay"])

    def test_scope_and_settings_conflicts_refuse_before_any_subprocess(self):
        for arguments in (("--repo", "/other", "status"), ("--repo=/other", "status"),
                          ("--rep=/other", "status"),
                          ("claude", "--settings", "{}"), ("claude", "--settings={}")):
            with self.subTest(arguments=arguments):
                result, calls = self.invoke(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(calls, [])

    def test_failed_or_malformed_plan_never_starts_claude(self):
        for variable in ("TEST_RELAY_FAIL", "TEST_RELAY_BAD_PLAN"):
            with self.subTest(variable=variable):
                self.environment[variable] = "1"
                result, calls = self.invoke("claude", "--print", "review")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual([call["kind"] for call in calls], ["relay"])
                self.log.unlink()
                del self.environment[variable]

    def test_provider_signal_is_reported_as_shell_exit_code(self):
        self.environment["TEST_RELAY_SIGNAL"] = "1"
        result, calls = self.invoke("claude", "--print", "review")
        self.assertEqual(result.returncode, 143, result.stderr)
        self.assertEqual([call["kind"] for call in calls], ["relay", "claude"])

    def test_terminating_helper_reaps_its_provider(self):
        self.environment["TEST_RELAY_WAIT"] = "1"
        process = subprocess.Popen(
            [sys.executable, str(self.script), "claude", "--print", "review"],
            env=self.environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        provider_pid = None
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and process.poll() is None:
                if self.log.exists():
                    lines = self.log.read_text().splitlines()
                    if len(lines) == 2:
                        provider_pid = json.loads(lines[-1])["pid"]
                        break
                time.sleep(0.01)
            self.assertIsNotNone(provider_pid, "provider failed to start")
            process.terminate()
            _, errors = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143, errors)
            with self.assertRaises(ProcessLookupError):
                os.kill(provider_pid, 0)
            provider_pid = None
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()
            if provider_pid is not None:
                try:
                    os.kill(provider_pid, 9)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    unittest.main()
