"""Security regressions for evaluator temporal-state artifact paths."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "evals/bin/check.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class CheckStatePathSecurityTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> Path:
        work = root / "work"
        work.mkdir()
        subprocess.run(["git", "init", "-q", "--template="], cwd=work, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"],
                       cwd=work, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=work, check=True)
        write(work / "canon/item.md", "captured\n")
        subprocess.run(["git", "add", "-A"], cwd=work, check=True)
        subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-qm", "base"],
                       cwd=work, check=True)
        return work

    def run_check(self, root: Path, work: Path, expected: dict) -> dict:
        expected_path = root / "expected.json"
        output_path = root / "checks.json"
        write(expected_path, json.dumps(expected))
        proc = subprocess.run(
            [sys.executable, str(CHECK), "--workdir", str(work),
             "--expected", str(expected_path), "--out", str(output_path),
             "--state-dir", str(root / "state"), "--state-key", "secret"],
            cwd=ROOT, text=True, capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(output_path.read_text())

    def test_capture_and_preserve_reject_unsafe_state_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = self.make_workspace(root)
            absolute_id = str(root / "absolute-escape")
            unsafe_ids = [
                "", absolute_id, "nested/id", "../escape", "..", "two..dots",
                r"..\escape", ".hidden", "space id", "naïve",
            ]

            capture = self.run_check(root, work, {
                "capture": [{"id": value, "glob": "canon/*.md"} for value in unsafe_ids]
            })
            preserve = self.run_check(root, work, {
                "preserve": [{"snapshot": value} for value in unsafe_ids]
            })

            capture_rows = [row for row in capture["checks"] if row["id"].startswith("capture:")]
            preserve_rows = [row for row in preserve["checks"] if row["id"].startswith("preserve:")]
            self.assertEqual(len(capture_rows), len(unsafe_ids))
            self.assertEqual(len(preserve_rows), len(unsafe_ids))
            self.assertTrue(all(not row["pass"] for row in capture_rows))
            self.assertTrue(all(not row["pass"] for row in preserve_rows))
            self.assertFalse(Path(f"{absolute_id}.json").exists())
            self.assertFalse((root / "escape.json").exists())

    def test_state_artifacts_cannot_be_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = self.make_workspace(root)
            state = root / "state"
            state.mkdir()
            outside = root / "outside.json"
            write(outside, "do not overwrite\n")
            (state / "safe.json").symlink_to(outside)

            capture = self.run_check(root, work, {
                "capture": [{"id": "safe", "glob": "canon/*.md"}]
            })
            preserve = self.run_check(root, work, {
                "preserve": [{"snapshot": "safe"}]
            })

            self.assertFalse(capture["required_pass"])
            self.assertFalse(preserve["required_pass"])
            self.assertEqual(outside.read_text(), "do not overwrite\n")


if __name__ == "__main__":
    unittest.main()
