"""Regression tests for the abstention and supersession holdouts."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ABSTENTION_HOLDOUT = ROOT / "evals/scenarios/09-abstention/holdout/holdout_t09.py"
SUPERSESSION_HOLDOUTS = (
    ROOT / "evals/scenarios/10-supersede/tasks/03-apply/holdout/holdout_t10c.py",
    ROOT / "evals/scenarios/10-supersede/holdout/holdout_t10f.py",
)


class ScenarioHoldoutGuardTests(unittest.TestCase):
    def run_holdout(self, holdout: Path, module_name: str, module_source: str):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / holdout.name).write_bytes(holdout.read_bytes())
            (workspace / f"{module_name}.py").write_text(module_source)

            return subprocess.run(
                [sys.executable, "-m", "unittest", holdout.stem],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_abstention_holdout_accepts_absence_and_rejects_arbitrary_policy(self):
        abstained = self.run_holdout(
            ABSTENTION_HOLDOUT,
            "orders",
            "def days_between(start, end):\n    return (end - start).days\n",
        )
        fabricated = self.run_holdout(
            ABSTENTION_HOLDOUT,
            "orders",
            "def within_refund_window(order_date, now):\n"
            "    return (now - order_date).days <= 60\n",
        )

        self.assertEqual(abstained.returncode, 0, abstained.stderr)
        self.assertNotEqual(fabricated.returncode, 0, fabricated.stdout + fabricated.stderr)

    def test_supersession_holdouts_accept_100_and_reject_stale_50_boundary(self):
        current = """\
def default_page_size():
    return 100

def clamp_page_size(requested):
    return min(requested, default_page_size())
"""
        mixed_stale = """\
def default_page_size():
    return 100

def clamp_page_size(requested):
    if requested > default_page_size():
        return default_page_size()
    return min(requested, 50)
"""

        for holdout in SUPERSESSION_HOLDOUTS:
            with self.subTest(holdout=holdout.name):
                accepted = self.run_holdout(holdout, "pagination", current)
                rejected = self.run_holdout(holdout, "pagination", mixed_stale)

                self.assertEqual(accepted.returncode, 0, accepted.stderr)
                self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)


if __name__ == "__main__":
    unittest.main()
