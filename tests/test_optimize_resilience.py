"""Deterministic failure-path tests for the guidance optimizer."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
OPTIMIZE_PATH = ROOT / "evals/bin/optimize.py"
SPEC = importlib.util.spec_from_file_location("canon_optimize", OPTIMIZE_PATH)
OPTIMIZE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(OPTIMIZE)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def valid_guidance(label: str) -> str:
    return "canon/ guidance\n" + "\n".join(f"{label} line {i}" for i in range(30)) + "\n"


class OptimizeResilienceTests(unittest.TestCase):
    def test_failure_signals_exclude_unsupported_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "batch-run-data-routing-stub-1"
            write(result / "run-1/checks.json", json.dumps({
                "checks": [
                    {
                        "id": "routing_precision", "pass": False,
                        "outcome": "unsupported", "detail": "telemetry unavailable",
                    },
                    {
                        "id": "manifest_complete", "pass": False,
                        "outcome": "fail", "detail": "missing route",
                    },
                ],
            }))

            failures = OPTIMIZE.gather_failures([result])

            self.assertEqual(
                failures,
                ["[routing-stub-1] check 'manifest_complete': missing route"],
            )

    def test_candidate_integrity_failures_are_recorded_and_optimization_completes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evals = root / "evals"
            baseline_results = root / "baseline-results"
            baseline_results.mkdir()
            guidance = root / "guidance.md"
            baseline_text = valid_guidance("baseline")
            write(guidance, baseline_text)
            candidate_text = valid_guidance("candidate")
            evaluation_results = [
                (0.5, [baseline_results], {"baseline": 0.5}),
                RuntimeError("incomplete eval result: first-candidate"),
                RuntimeError("eval failed a required integrity/correctness gate: second-candidate"),
            ]
            argv = [
                "optimize.py", "--scenarios", "scenario", "--iterations", "2",
                "--runs", "1", "--guidance", str(guidance),
                "--improver-cmd", "unused",
            ]

            with (
                mock.patch.object(OPTIMIZE, "EVALS", evals),
                mock.patch.object(OPTIMIZE.time, "strftime", return_value="20260718-000000"),
                mock.patch.object(OPTIMIZE, "evaluate", side_effect=evaluation_results) as evaluate,
                mock.patch.object(OPTIMIZE, "propose", return_value=candidate_text),
                mock.patch.object(sys, "argv", argv),
            ):
                OPTIMIZE.main()

            output = evals / "results/opt-20260718-000000"
            history = json.loads((output / "history.json").read_text())
            self.assertEqual(evaluate.call_count, 3)
            self.assertEqual([row["kind"] for row in history],
                             ["baseline", "rejected", "rejected"])
            self.assertTrue(all(not row["kept"] for row in history[1:]))
            self.assertEqual((output / "best.md").read_text(), baseline_text)

    def test_nonzero_improver_exit_is_not_accepted_as_a_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evals = Path(directory) / "evals"
            write(evals / "judge/improver-prompt.md", "Improve the guidance.")
            completed = subprocess.CompletedProcess(
                args="improver", returncode=7,
                stdout=valid_guidance("untrusted"), stderr="backend failed",
            )

            with (
                mock.patch.object(OPTIMIZE, "EVALS", evals),
                mock.patch.object(OPTIMIZE.subprocess, "run", return_value=completed),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "exit code 7: backend failed"
                ):
                    OPTIMIZE.propose("improver", "current", [], 0.5)


if __name__ == "__main__":
    unittest.main()
