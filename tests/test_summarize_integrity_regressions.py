"""Focused regressions for eval summary integrity boundaries."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "canon_summarize", ROOT / "evals/bin/summarize.py"
)
assert SPEC and SPEC.loader
SUMMARIZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARIZE)


class SummaryIntegrityRegressions(unittest.TestCase):
    def test_judge_requires_nonempty_ids_and_string_reasons_and_notes(self) -> None:
        invalid_payloads = [
            {"criteria": [{"id": "", "score": 1, "reason": "ok"}], "notes": "ok"},
            {"criteria": [{"id": "quality", "score": 1}], "notes": "ok"},
            {"criteria": [{"id": "quality", "score": 1, "reason": "ok"}]},
        ]
        for payload in invalid_payloads:
            payload["judge_score"] = 1.0
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                artifact = Path(directory) / "judge.json"
                artifact.write_text(json.dumps(payload))

                with self.assertRaises(SUMMARIZE.InvalidResult):
                    SUMMARIZE.validate_judge(artifact)

    def test_retained_input_paths_reject_symlinks_and_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "result"
            outside = Path(directory) / "outside"
            result.mkdir()
            outside.mkdir()
            (outside / "input.md").write_text("outside\n")
            (result / "inputs").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(SUMMARIZE.InvalidResult):
                SUMMARIZE.retained_path(result, "inputs/input.md", "fixture")
            with self.assertRaises(SUMMARIZE.InvalidResult):
                SUMMARIZE.retained_path(result, "../outside/input.md", "fixture")

    def test_scenario_tree_rejects_nested_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario = root / "scenario"
            scenario.mkdir()
            (root / "outside.md").write_text("outside\n")
            (scenario / "task.md").symlink_to(root / "outside.md")

            with self.assertRaises(SUMMARIZE.InvalidResult):
                SUMMARIZE.tree_sha256(scenario)

    def test_filesystem_failure_replaces_stale_complete_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory)
            summary = result / "summary.json"
            summary.write_text(json.dumps({"complete": True}))

            with mock.patch.object(SUMMARIZE, "summarize", side_effect=OSError("unreadable")):
                status = SUMMARIZE.main([str(result)])

            self.assertEqual(status, 1)
            self.assertFalse(json.loads(summary.read_text())["complete"])

    def test_invalid_summary_atomically_replaces_symlink_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = root / "result"
            result.mkdir()
            target = root / "outside-summary.json"
            target.write_text(json.dumps({"complete": True}))
            (result / "summary.json").symlink_to(target)
            invalid = {"complete": False, "error": "invalid"}

            error = SUMMARIZE.invalidate_summary(result, invalid)

            self.assertIsNone(error)
            self.assertFalse((result / "summary.json").is_symlink())
            self.assertEqual(json.loads((result / "summary.json").read_text()), invalid)
            self.assertTrue(json.loads(target.read_text())["complete"])


if __name__ == "__main__":
    unittest.main()
