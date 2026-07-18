"""Regression tests for Canon doctor rule consistency."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "tools/canon-doctor.py"


def run(*args: str, cwd: Path, check: bool = True, env: dict[str, str] | None = None):
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class DoctorRuleConsistencyTests(unittest.TestCase):
    def init_canon(self, root: Path, *extra_routes: str) -> None:
        write(root / ".gitignore", "canon/scratch/\n")
        write(root / "canon/overview.md", "# Overview\n")
        write(root / "canon/glossary.md", "# Glossary\n")
        write(root / "canon/standards.md", "# Standards\n")
        routes = [
            "- [Overview](overview.md)",
            "- [Glossary](glossary.md)",
            "- [Standards](standards.md)",
            *extra_routes,
        ]
        write(root / "canon/manifest.md", "# Manifest\n" + "\n".join(routes) + "\n")

    def init_git(self, root: Path) -> None:
        run("git", "init", "-q", "--template=", cwd=root)
        run("git", "config", "user.email", "test@example.invalid", cwd=root)
        run("git", "config", "user.name", "Canon Test", cwd=root)

    def commit(self, root: Path, message: str) -> str:
        run("git", "add", "-A", cwd=root)
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
        })
        run(
            "git", "-c", "commit.gpgsign=false", "commit", "-qm", message,
            cwd=root, env=env,
        )
        return run("git", "rev-parse", "HEAD", cwd=root).stdout.strip()

    def doctor(self, root: Path) -> list[dict[str, str]]:
        result = run(
            sys.executable,
            str(DOCTOR),
            "--root",
            str(root),
            "--json",
            cwd=ROOT,
            check=False,
        )
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)["findings"]

    def staleness(self, root: Path) -> list[dict[str, str]]:
        return [row for row in self.doctor(root) if row["check"] == "staleness"]

    def make_domain_repo(self, root: Path, verified: str | None = None) -> str:
        self.init_canon(root, "- [API](api/overview.md)")
        self.init_git(root)
        write(root / "app.py", "VALUE = 1\n")
        anchor = self.commit(root, "baseline")
        write(
            root / "canon/api/overview.md",
            "---\nsources: [app.py]\n"
            f"verified: {verified or anchor}\n---\n# API\n",
        )
        self.commit(root, "add domain knowledge")
        return anchor

    def test_immutable_decision_history_is_exempt_from_changelog_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(root, "- [Decision](decisions/retention.md)")
            write(root / "canon/overview.md", "# Overview\n\nPreviously supported.\n")
            write(
                root / "canon/decisions/retention.md",
                "# Retention decision\n\nOn 2025-01-01 we changed the previous policy.\n",
            )

            warnings = [
                row for row in self.doctor(root) if row["check"] == "changelog-smell"
            ]

            self.assertEqual(len(warnings), 1)
            self.assertIn("overview.md", warnings[0]["detail"])

    def test_existing_abbreviated_anchor_is_indeterminate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            anchor = self.make_domain_repo(root)
            domain = root / "canon/api/overview.md"
            write(
                domain,
                "---\nsources: [app.py]\n"
                f"verified: {anchor[:7]}\n---\n# API\n",
            )

            warnings = self.staleness(root)

            self.assertEqual(len(warnings), 1)
            self.assertIn("history indeterminate", warnings[0]["detail"])
            self.assertIn("full immutable hexadecimal commit id", warnings[0]["detail"])

    def test_full_existing_anchor_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_domain_repo(root)

            self.assertEqual(self.staleness(root), [])

    def test_missing_full_length_anchor_is_indeterminate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_domain_repo(root, verified="0" * 40)

            warnings = self.staleness(root)

            self.assertEqual(len(warnings), 1)
            self.assertIn("history indeterminate", warnings[0]["detail"])
            self.assertIn("not found", warnings[0]["detail"])


if __name__ == "__main__":
    unittest.main()
