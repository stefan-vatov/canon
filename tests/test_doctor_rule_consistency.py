"""Regression tests for invariant-first Canon doctor rules."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "tools/canon-doctor.py"


def run(*args: str, cwd: Path, check: bool = True):
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class DoctorRuleConsistencyTests(unittest.TestCase):
    def init_canon(self, root: Path, *extra_routes: str) -> None:
        if not (root / ".git").is_dir():
            self.init_git(root)
        write(root / ".gitignore", "canon/scratch/\n")
        write(
            root / "canon/standards.md",
            "---\nstatus: normative\nscope: [project-wide]\n---\n# Standards\n",
        )
        routes = [
            "- [Standards](standards.md) — read for project-wide rules",
            *extra_routes,
        ]
        write(
            root / "canon/manifest.md",
            "---\nstatus: reference\n---\n# Manifest\n" + "\n".join(routes) + "\n",
        )

    def init_git(self, root: Path) -> None:
        run("git", "init", "-q", "--template=", cwd=root)

    def doctor(
        self,
        root: Path,
        *,
        baseline: str | None = None,
    ) -> list[dict[str, str]]:
        args = [
            sys.executable,
            str(DOCTOR),
            "--root",
            str(root),
            "--json",
        ]
        if baseline is not None:
            args.extend(["--baseline", baseline])
        result = run(
            *args,
            cwd=ROOT,
            check=False,
        )
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)["findings"]

    def findings(
        self,
        root: Path,
        check: str,
        *,
        baseline: str | None = None,
    ) -> list[dict[str, str]]:
        return [
            row
            for row in self.doctor(root, baseline=baseline)
            if row["check"] == check
        ]

    def test_immutable_legacy_decision_is_not_rewritten_for_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Decision](decisions/retention.md) — read for retention policy",
                "- [History](architecture/history.md) — read for compatibility",
            )
            write(
                root / "canon/decisions/retention.md",
                "---\nsources: [src/retention.py]\nverified: deadbeef\n---\n"
                "# Retention decision\n\n"
                "On 2025-01-01 we changed the previous policy.\n",
            )
            write(
                root / "canon/architecture/history.md",
                "---\nstatus: reference\n---\n# History\n\nPreviously supported.\n",
            )
            run("git", "add", "-A", cwd=root)
            run(
                "git",
                "-c",
                "user.email=test@example.invalid",
                "-c",
                "user.name=Test",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "legacy baseline",
                cwd=root,
            )

            metadata = self.findings(root, "frontmatter", baseline="HEAD")
            changelog = self.findings(
                root,
                "changelog-smell",
                baseline="HEAD",
            )

            self.assertEqual(metadata, [])
            self.assertEqual(len(changelog), 1)
            self.assertIn("architecture/history.md", changelog[0]["detail"])

            write(
                root / "canon/decisions/retention.md",
                (root / "canon/decisions/retention.md").read_text()
                + "\nRewritten history.\n",
            )
            immutable = self.findings(
                root,
                "decision-immutability",
                baseline="HEAD",
            )
            self.assertEqual(len(immutable), 1)
            self.assertIn("differs", immutable[0]["detail"])

    def test_trusted_baseline_grandfathers_all_unchanged_decision_schemas(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Status](decisions/status.md) — read for status history",
                "- [Unknown](decisions/unknown.md) — read for schema history",
                "- [Malformed](decisions/malformed.md) — read for format history",
                "- [Plain](decisions/plain.md) — read for plain history",
            )
            write(
                root / "canon/decisions/status.md",
                "---\nstatus: reference\n---\n# Historical status\n",
            )
            write(
                root / "canon/decisions/unknown.md",
                "---\nstatus: normative\nhistorical_owner: team\n---\n"
                "# Historical field\n",
            )
            write(
                root / "canon/decisions/malformed.md",
                "---\nstatus:\n  nested: invalid\n---\n# Historical format\n",
            )
            write(
                root / "canon/decisions/plain.md",
                "# Historical decision without front matter\n",
            )
            run("git", "add", "-A", cwd=root)
            run(
                "git",
                "-c",
                "user.email=test@example.invalid",
                "-c",
                "user.name=Test",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "trusted migration baseline",
                cwd=root,
            )
            migration_baseline = run(
                "git",
                "rev-parse",
                "HEAD",
                cwd=root,
            ).stdout.strip()

            self.assertEqual(
                self.findings(
                    root,
                    "frontmatter",
                    baseline=migration_baseline,
                ),
                [],
            )

            write(
                root / "canon/manifest.md",
                (root / "canon/manifest.md").read_text()
                + "- [New](decisions/new.md) — read for new policy\n",
            )
            write(
                root / "canon/decisions/new.md",
                "---\nstatus: reference\n---\n# Invalid new decision\n",
            )
            new_findings = self.findings(
                root,
                "frontmatter",
                baseline=migration_baseline,
            )
            self.assertTrue(any(
                "new.md decision records must have status: normative"
                in row["detail"]
                for row in new_findings
            ))

    def test_normative_metadata_and_multiline_lists_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Runtime](architecture/runtime.md) — read for runtime policy",
            )
            write(root / "tests/runtime_policy_test.py", "POLICY = True\n")
            write(
                root / "canon/architecture/runtime.md",
                "---\n"
                "status: normative\n"
                "scope:\n  - runtime\n  - persistence\n"
                "validation:\n  [\n    tests/runtime_policy_test.py,\n  ]\n"
                "related: [../standards.md]\n"
                "---\n# Runtime\n\nMutations are not retried automatically.\n",
            )

            self.assertEqual(self.doctor(root), [])

    def test_legacy_inventory_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Runtime](architecture/runtime.md) — read for runtime policy",
            )
            write(
                root / "canon/architecture/runtime.md",
                "---\nstatus: normative\nsources: [src/runtime.py]\n"
                "verified: deadbeef\n---\n# Runtime\n",
            )

            findings = self.findings(root, "frontmatter")

            self.assertEqual(len(findings), 2)
            self.assertTrue(all("retired implementation-inventory" in row["detail"]
                                for row in findings))

    def test_malformed_frontmatter_and_unrouted_normative_page_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(root)
            write(
                root / "canon/architecture/runtime.md",
                "---\nstatus: normative\nscope:\n  path: runtime\n---\n# Runtime\n",
            )

            findings = self.doctor(root)

            self.assertTrue(any(
                row["check"] == "frontmatter" and "no valid front matter" in row["detail"]
                for row in findings
            ))

            write(
                root / "canon/architecture/runtime.md",
                "---\nstatus: normative\nscope: [runtime]\n---\n# Runtime\n",
            )
            findings = self.findings(root, "manifest")
            self.assertEqual(len(findings), 1)
            self.assertIn("normative page", findings[0]["detail"])

    def test_manifest_routes_require_one_link_and_explicit_read_condition(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(root)
            write(
                root / "canon/architecture/topic.md",
                "---\nstatus: normative\nscope: [topic]\n---\n# Topic\n",
            )
            invalid_routes = (
                "- [Standards](standards.md) [Topic](architecture/topic.md)\n",
                "- [Standards](standards.md) page\n"
                "- [Topic](architecture/topic.md) page\n",
                "- read about [Standards](standards.md)\n"
                "- see [Topic](architecture/topic.md) for details\n",
                "- [Standards](standards.md) — read for project rules\n"
                "- ![Topic](architecture/topic.md) — read when changing topic\n",
                "- [Standards](standards.md) — read for project rules\n"
                r"- \[Topic](architecture/topic.md) — read when changing topic"
                "\n",
                "- [Standards](standards.md) — read for project rules\n"
                "- `[Topic](architecture/topic.md)` — read when changing topic\n",
            )
            for routes in invalid_routes:
                write(
                    root / "canon/manifest.md",
                    "---\nstatus: reference\n---\n# Manifest\n" + routes,
                )
                findings = self.findings(root, "manifest")
                self.assertTrue(findings, routes)

            write(
                root / "canon/manifest.md",
                "---\nstatus: reference\n---\n# Manifest\n"
                "- [Standards](standards.md) — read for project rules\n"
                "- read when changing topics: "
                "[Topic](architecture/topic.md)\n",
            )
            self.assertEqual(self.findings(root, "manifest"), [])

            write(
                root / "canon/manifest.md",
                "---\nstatus: reference\n---\n# Manifest\n"
                "- [Standards](standards.md) — read for project rules\n"
                r"- \\[Topic](architecture/topic.md) — read when changing topic"
                "\n",
            )
            self.assertEqual(self.findings(root, "manifest"), [])

    def test_deprecated_and_decision_relationships_must_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Current](architecture/current.md) — read for current policy",
                "- [Decision](decisions/new.md) — read for the active decision",
            )
            write(
                root / "canon/architecture/current.md",
                "---\nstatus: normative\nscope: [api]\n---\n# Current\n",
            )
            write(
                root / "canon/architecture/old.md",
                "---\nstatus: deprecated\nreplaced_by: ./missing.md\n---\n# Old\n",
            )
            write(
                root / "canon/decisions/new.md",
                "---\nstatus: normative\nsupersedes: [./missing.md]\n---\n# New\n",
            )

            links = self.findings(root, "links")

            self.assertEqual(len(links), 2)
            self.assertTrue(all("missing" in row["detail"] for row in links))

    def test_replacement_and_supersession_fields_have_semantic_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Current](architecture/current.md) — read for current policy",
                "- [Decision](decisions/new.md) — read for the active decision",
            )
            write(
                root / "canon/architecture/current.md",
                "---\nstatus: normative\nscope: [api]\n"
                "replaced_by: ./current.md\n---\n# Current\n",
            )
            write(
                root / "canon/decisions/new.md",
                "---\nstatus: normative\n"
                "supersedes: [../architecture/current.md]\n"
                "---\n# New\n",
            )

            findings = self.doctor(root)

            self.assertTrue(any(
                row["check"] == "frontmatter"
                and "replaced_by outside" in row["detail"]
                for row in findings
            ))
            self.assertTrue(any(
                row["check"] == "links"
                and "predecessor in decisions/" in row["detail"]
                for row in findings
            ))

    def test_new_decisions_require_metadata_and_supersession_must_be_acyclic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [A](decisions/a.md) — read for decision A",
                "- [B](decisions/b.md) — read for decision B",
            )
            write(root / "canon/decisions/a.md", "# New decision without metadata\n")

            failures = self.findings(root, "frontmatter")
            self.assertEqual(len(failures), 1)
            self.assertIn("new decision", failures[0]["detail"])

            write(
                root / "canon/decisions/a.md",
                "---\nstatus: normative\nsupersedes: [./b.md]\n---\n# A\n",
            )
            write(
                root / "canon/decisions/b.md",
                "---\nstatus: normative\nsupersedes: [./a.md]\n---\n# B\n",
            )
            links = self.findings(root, "links")
            self.assertTrue(any("supersession cycle" in row["detail"] for row in links))

    def test_legacy_baseline_does_not_stop_protecting_newer_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(root)
            run("git", "add", "-A", cwd=root)
            run(
                "git",
                "-c",
                "user.email=test@example.invalid",
                "-c",
                "user.name=Test",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "migration baseline",
                cwd=root,
            )
            migration_baseline = run(
                "git",
                "rev-parse",
                "HEAD",
                cwd=root,
            ).stdout.strip()
            write(
                root / "canon/manifest.md",
                (root / "canon/manifest.md").read_text()
                + "- [Decision](decisions/current.md) — read for current policy\n",
            )
            write(
                root / "canon/decisions/current.md",
                "---\nstatus: normative\nscope: [policy]\n---\n# Current\n",
            )
            run("git", "add", "-A", cwd=root)
            run(
                "git",
                "-c",
                "user.email=test@example.invalid",
                "-c",
                "user.name=Test",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "new decision",
                cwd=root,
            )
            write(
                root / "canon/decisions/current.md",
                "---\nstatus: normative\nscope: [policy]\n---\n# Rewritten\n",
            )

            immutable = self.findings(
                root,
                "decision-immutability",
                baseline=migration_baseline,
            )

            self.assertTrue(any(
                "current.md differs" in row["detail"] and "HEAD" in row["detail"]
                for row in immutable
            ))

    def test_validation_references_are_safe_repository_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Runtime](architecture/runtime.md) — read for runtime policy",
            )
            write(root / "tests/runtime_policy_test.py", "POLICY = True\n")
            write(
                root / "canon/architecture/runtime.md",
                "---\nstatus: normative\nscope: [runtime]\n"
                "validation: [tests/runtime_policy_test.py]\n---\n# Runtime\n",
            )
            self.assertEqual(self.findings(root, "validation"), [])

            write(
                root / "canon/architecture/runtime.md",
                "---\nstatus: normative\nscope: [runtime]\n"
                "validation: [../outside.py]\n---\n# Runtime\n",
            )
            failures = self.findings(root, "validation")
            self.assertEqual(len(failures), 1)
            self.assertIn("safe repository-relative path", failures[0]["detail"])

    def test_permanent_canon_directories_must_not_be_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "repo"
            outside = workspace / "outside"
            root.mkdir()
            outside.mkdir()
            self.init_canon(root)
            (root / "canon/linked").symlink_to(
                outside,
                target_is_directory=True,
            )

            failures = self.findings(root, "structure")

            self.assertEqual(len(failures), 1)
            self.assertIn("linked must not be a symlink", failures[0]["detail"])

    def test_scratch_must_be_ignored_and_not_routed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_git(root)
            self.init_canon(
                root,
                "- [Scratch](scratch/notes.md) — read when handling scratch",
            )
            write(root / "canon/scratch/notes.md", "temporary\n")
            write(root / ".gitignore", "")

            findings = self.doctor(root)

            self.assertTrue(any(
                row["check"] == "scratch-ignored" for row in findings
            ))
            self.assertTrue(any(
                row["check"] == "manifest" and "scratch" in row["detail"]
                for row in findings
            ))

    def test_scratch_must_not_contain_tracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_git(root)
            self.init_canon(root)
            write(root / "canon/scratch/notes.md", "temporary\n")
            run("git", "add", "-f", "canon/scratch/notes.md", cwd=root)

            failures = self.findings(root, "scratch-ignored")

            self.assertEqual(len(failures), 1)
            self.assertIn("contains tracked files", failures[0]["detail"])

    def test_scratch_ignore_must_be_portable_and_not_hide_permanent_canon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "repo"
            root.mkdir()
            self.init_canon(root)
            global_ignore = workspace / "global-ignore"
            write(global_ignore, "canon/scratch/\n")
            write(root / ".gitignore", "")
            run("git", "config", "core.excludesFile", str(global_ignore), cwd=root)

            failures = self.findings(root, "scratch-ignored")
            self.assertTrue(any("repository-root" in row["detail"] for row in failures))

            run("git", "config", "--unset", "core.excludesFile", cwd=root)
            write(root / ".gitignore", "canon/\n")
            failures = self.findings(root, "scratch-ignored")
            self.assertTrue(any(
                "permanent Canon file is ignored" in row["detail"]
                for row in failures
            ))


if __name__ == "__main__":
    unittest.main()
