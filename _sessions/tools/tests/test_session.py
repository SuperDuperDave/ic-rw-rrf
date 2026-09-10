"""Run with: python3 -B -m unittest discover -s _sessions/tools/tests -v"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HELPER = Path(__file__).resolve().parents[1] / "session.py"
SPEC = importlib.util.spec_from_file_location("session_helper", str(HELPER))
SESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SESSION)


def snapshot(directory):
    return {str(path.relative_to(directory)): path.read_bytes() if path.is_file() else None
            for path in directory.rglob("*")}


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_sequence_across_slugs_preserves_existing_content(self):
        first = SESSION.start_session(self.root, "first-probe", "2026-09-10")
        first.write_text("Evidence to preserve.\n", encoding="utf-8")
        third = first.with_name("2026-09-10-003-other-slug.md")
        third.write_text("Different session.\n", encoding="utf-8")
        fourth = SESSION.start_session(self.root, "first-probe", "2026-09-10")
        self.assertEqual(fourth.name, "2026-09-10-004-first-probe.md")
        self.assertEqual(first.read_text(encoding="utf-8"), "Evidence to preserve.\n")
        self.assertEqual(third.read_text(encoding="utf-8"), "Different session.\n")
        self.assertIn(third.name, fourth.read_text(encoding="utf-8"))

    def test_invalid_slug_creates_nothing(self):
        for slug in ("", "../escape", "a/b", "a\\b", ".hidden", "Uppercase",
                     "two words", "café", "a--b", "-start", "end-", "x" * 65):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                SESSION.start_session(self.root, slug, "2026-09-10")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_same_slug_concurrent_creates_are_distinct(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            paths = list(pool.map(
                lambda _: SESSION.start_session(self.root, "parallel", "2026-09-10"),
                range(12),
            ))
        self.assertEqual(len(set(paths)), 12)
        self.assertEqual(sorted(path.name for path in paths),
                         ["2026-09-10-{:03d}-parallel.md".format(i) for i in range(1, 13)])
        for path in paths:
            self.assertIn("## Carryforward pointers", path.read_text(encoding="utf-8"))

    def test_status_and_start_resolve_script_location_outside_cwd(self):
        repo = self.root / "repo"
        helper = repo / "_sessions" / "tools" / "session.py"
        helper.parent.mkdir(parents=True)
        shutil.copyfile(str(HELPER), str(helper))
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        before = snapshot(self.root)
        status = subprocess.run([sys.executable, "-B", str(helper), "status"],
                                cwd=str(elsewhere), capture_output=True, text=True, check=True)
        self.assertIn("Repository: {}".format(repo), status.stdout)
        self.assertEqual(snapshot(self.root), before)
        start = subprocess.run([sys.executable, "-B", str(helper), "start", "outside-cwd"],
                               cwd=str(elsewhere), capture_output=True, text=True, check=True)
        created = Path(start.stdout.strip())
        self.assertEqual(created.parent, repo / "_sessions" / "streams")
        self.assertTrue(created.is_file())
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_status_lists_recent_paths_and_disables_git_writes(self):
        paths = [SESSION.start_session(self.root, "probe", "2026-09-{:02d}".format(i))
                 for i in range(1, 8)]
        for _, relative in SESSION.CONTEXT_FILES:
            (self.root / relative).write_text("Do not read this file.\n", encoding="utf-8")
        before = snapshot(self.root)
        result = subprocess.CompletedProcess([], 0, "## topic\n?? untracked.md\n", "")
        output = io.StringIO()
        with mock.patch.object(SESSION.subprocess, "run", return_value=result) as run:
            with redirect_stdout(output):
                SESSION.show_status(self.root)
        self.assertEqual(snapshot(self.root), before)
        self.assertIn("## topic\n?? untracked.md", output.getvalue())
        self.assertIn(str(paths[-1]), output.getvalue())
        self.assertNotIn(str(paths[0]), output.getvalue())
        for _, relative in SESSION.CONTEXT_FILES:
            self.assertIn(str(self.root / relative), output.getvalue())
        command = run.call_args.args[0]
        self.assertIn("--no-optional-locks", command)
        self.assertIn("--untracked-files=normal", command)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_local_date_is_used(self):
        with mock.patch.object(SESSION, "date") as local_date:
            local_date.today.return_value.isoformat.return_value = "2026-09-10"
            created = SESSION.start_session(self.root, "local-date")
        self.assertEqual(created.name, "2026-09-10-001-local-date.md")
        local_date.today.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
