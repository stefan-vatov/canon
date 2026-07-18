"""Security regressions for evaluator adapter install and process boundaries."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTERS = {
    "codex": (ROOT / "evals/adapters/codex.sh", Path("AGENTS.md")),
    "claude": (ROOT / "evals/adapters/claude.sh", Path("CLAUDE.md")),
    "pi": (ROOT / "evals/adapters/pi.sh", Path(".pi/APPEND_SYSTEM.md")),
}
PRIVATE_ENV = {
    "JUDGE_CMD", "IMPROVER_CMD", "ROOT", "EVALS", "SCEN_DIR",
    "ADAPTER_SOURCE", "OUT", "PRIVATE_STATE", "FROZEN_SCENARIO",
    "FROZEN_EVALUATOR", "FROZEN_GUIDANCE", "ADAPTER", "PROVENANCE",
    "CHECKER", "JUDGE_SCRIPT", "SUMMARIZER", "BATCH_ID", "RUN", "WORK",
    "STATE", "STATE_KEY", "PRIVATE_TASK", "STEP_DIR", "BASELINE",
    "JUDGE_REQUEST", "BATCH_FINALIZED", "OVERALL_FAILED", "AGENT_STATUS",
    "JUDGE_STATUS", "RUN_FAILED", "CHECK_FILES", "JUDGE_FILE", "STATE_FILES",
    "RUN_STATUS", "FINISH_ARGS",
    "WORKDIR", "TASK_FILE", "GUIDANCE_FILE", "TRANSCRIPT", "EVAL_MODEL",
    "EVAL_REASONING",
}


class AdapterSecurityTests(unittest.TestCase):
    def run_adapter(self, adapter: Path, operation: str, env: dict[str, str]):
        return subprocess.run(
            (str(adapter), operation), env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_install_refuses_unsafe_destinations_without_following_them(self) -> None:
        for name, (adapter, relative) in ADAPTERS.items():
            with self.subTest(adapter=name), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                root = Path(directory)
                work = root / "work"
                work.mkdir()
                guidance = root / "guidance.md"
                guidance.write_text("trusted guidance\n")
                destination = work / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                outside = root / "outside.md"
                outside.write_text("do not overwrite\n")
                destination.symlink_to(outside)
                env = os.environ | {"WORKDIR": str(work), "GUIDANCE_FILE": str(guidance)}

                result = self.run_adapter(adapter, "install", env)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(outside.read_text(), "do not overwrite\n")
                self.assertTrue(destination.is_symlink())

                destination.unlink()
                destination.mkdir()
                result = self.run_adapter(adapter, "install", env)
                self.assertNotEqual(result.returncode, 0)
                destination.rmdir()

                linked_work = root / "linked-work"
                linked_work.symlink_to(work, target_is_directory=True)
                result = self.run_adapter(
                    adapter, "install", env | {"WORKDIR": str(linked_work)},
                )
                self.assertNotEqual(result.returncode, 0)

                result = self.run_adapter(adapter, "install", env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(destination.read_text(), "trusted guidance\n")

    def test_run_scrubs_private_environment_but_preserves_cli_options(self) -> None:
        for name, (adapter, _) in ADAPTERS.items():
            with self.subTest(adapter=name), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                root = Path(directory)
                work, bin_dir = root / "work", root / "bin"
                work.mkdir(); bin_dir.mkdir()
                task, transcript, guidance = root / "task.md", root / "transcript.txt", root / "g.md"
                task.write_text("perform task")
                guidance.write_text("guidance")
                executable = bin_dir / name
                executable.write_text("#!/bin/sh\nprintf 'ARGV:%s\\n' \"$*\"\nenv\n")
                executable.chmod(0o755)
                env = os.environ.copy()
                env.update({key: "private-leak" for key in PRIVATE_ENV})
                env.update({
                    "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
                    "WORKDIR": str(work), "TASK_FILE": str(task),
                    "GUIDANCE_FILE": str(guidance), "TRANSCRIPT": str(transcript),
                    "EVAL_MODEL": "model-x", "EVAL_REASONING": "high",
                    "CANON_SENTINEL": "preserved",
                })

                result = self.run_adapter(adapter, "run", env)
                self.assertEqual(result.returncode, 0, result.stderr)
                output = transcript.read_text()
                worker_env = {line.split("=", 1)[0] for line in output.splitlines() if "=" in line}
                self.assertTrue(PRIVATE_ENV.isdisjoint(worker_env), PRIVATE_ENV & worker_env)
                self.assertIn("CANON_SENTINEL", worker_env)
                self.assertIn("perform task", output)
                self.assertIn("model-x", output)
                if name == "codex":
                    self.assertIn('model_reasoning_effort="high"', output)


if __name__ == "__main__":
    unittest.main()
