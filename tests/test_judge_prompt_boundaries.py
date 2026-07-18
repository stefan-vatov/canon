"""Regressions for judge prompt assembly boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "evals/bin/judge.sh"


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def git(root: Path, *args: str) -> str:
    result = run("git", *args, cwd=root)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class JudgePromptBoundaryTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, str, Path]:
        run_dir = root / "run"
        workspace = run_dir / "workspace"
        scenario = root / "scenario"
        workspace.mkdir(parents=True)
        scenario.mkdir()
        git(workspace, "init", "-q", "--template=")
        git(workspace, "config", "user.email", "test@example.invalid")
        git(workspace, "config", "user.name", "Test")
        (workspace / "large.txt").write_text("baseline\n")
        git(workspace, "add", "-A")
        git(workspace, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
        baseline = git(workspace, "rev-parse", "HEAD")
        (run_dir / "receipt.json").write_text(json.dumps({"baseline": baseline}))
        (run_dir / "transcript.txt").write_text("completed\n")
        (scenario / "task.md").write_text("Test task\n")
        capture = root / "judge-received.md"
        stub = root / "judge-stub.sh"
        stub.write_text(
            "#!/bin/sh\n"
            "cat > \"$JUDGE_CAPTURE\"\n"
            "printf '%s\\n' '{\"criteria\":[{\"id\":\"quality\",\"score\":1}]}'\n"
        )
        stub.chmod(0o755)
        return run_dir, scenario, baseline, capture

    def judge(self, run_dir: Path, scenario: Path, capture: Path, stub: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(JUDGE_CMD=str(stub), JUDGE_CAPTURE=str(capture))
        return run("bash", str(JUDGE), str(run_dir), str(scenario), cwd=ROOT, env=env)

    def test_diff_over_30k_is_truncated_without_aborting_prompt_assembly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir, scenario, baseline, capture = self.fixture(root)
            workspace = run_dir / "workspace"
            (workspace / "large.txt").write_text("changed line for a large diff\n" * 2000)
            git(workspace, "add", "-A")
            expected = run("git", "diff", "--cached", baseline, cwd=workspace).stdout.encode()
            self.assertGreater(len(expected), 30_000)

            result = self.judge(run_dir, scenario, capture, root / "judge-stub.sh")

            self.assertEqual(result.returncode, 0, result.stderr)
            prompt = capture.read_bytes()
            marker = b"## Agent's diff against the baseline\n```diff\n"
            payload = prompt.split(marker, 1)[1].split(b"```\n\n## Canon files", 1)[0]
            self.assertEqual(payload, expected[:30_000])
            self.assertEqual(list(run_dir.glob(".judge-diff.*")), [])

    def test_symlinked_canon_markdown_never_reaches_judge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir, scenario, _, capture = self.fixture(root)
            canon = run_dir / "workspace/canon"
            canon.mkdir()
            secret = "HOST_SECRET_MUST_NOT_REACH_JUDGE"
            host_file = root / "host-secret.md"
            host_file.write_text(secret)
            (canon / "safe.md").write_text("safe canon evidence\n")
            (canon / "leak.md").symlink_to(host_file)

            result = self.judge(run_dir, scenario, capture, root / "judge-stub.sh")

            self.assertEqual(result.returncode, 0, result.stderr)
            received = capture.read_text()
            self.assertNotIn(secret, received)
            self.assertIn("safe canon evidence", received)
            self.assertIn("<BEGIN_UNTRUSTED_EVIDENCE>", received)
            self.assertIn("<END_UNTRUSTED_EVIDENCE>", received)


if __name__ == "__main__":
    unittest.main()
