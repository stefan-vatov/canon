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


    def commit_all(self, root: Path, message: str) -> str:
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
            message,
            cwd=root,
        )
        return run("git", "rev-parse", "HEAD", cwd=root).stdout.strip()

    def test_grandfathered_decision_is_exempt_from_links_and_caps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Legacy](decisions/legacy.md) — read for legacy history",
            )
            write(
                root / "canon/decisions/legacy.md",
                "# Legacy decision\n\n"
                "See the [old page](../payments/overview.md) for details.\n"
                + ("filler " * 50 + "line\n") * 260,
            )
            baseline = self.commit_all(root, "legacy baseline")

            findings = self.doctor(root, baseline=baseline)
            self.assertEqual(
                [row for row in findings if row["severity"] == "error"],
                [],
                findings,
            )

            write(
                root / "canon/manifest.md",
                (root / "canon/manifest.md").read_text()
                + "- [New](decisions/new.md) — read for new policy\n",
            )
            write(
                root / "canon/decisions/new.md",
                "---\nstatus: normative\n---\n# New decision\n\n"
                "See the [old page](../payments/overview.md).\n"
                + "filler line\n" * 260,
            )
            new_findings = self.doctor(root, baseline=baseline)
            self.assertTrue(any(
                row["check"] == "links" and "decisions/new.md" in row["detail"]
                for row in new_findings
            ))
            self.assertTrue(any(
                row["check"] == "line-caps" and "decisions/new.md" in row["detail"]
                for row in new_findings
            ))

    def test_page_body_links_ignore_fences_code_spans_and_bare_fragments(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Topic](architecture/topic.md) — read for topic rules",
            )
            write(
                root / "canon/architecture/topic.md",
                "---\nstatus: normative\nscope: [topic]\n---\n# Topic\n\n"
                "```md\nDo not write [inventory](missing.md) links.\n```\n\n"
                "~~~md\nTilde fences hide [these](absent.md) too.\n~~~\n\n"
                "<!-- drafted [note](draft.md) -->\n\n"
                "Avoid `[quoted](nope.md)` counter-examples.\n\n"
                "Stray fragment ](stray.md) is prose, not a link.\n\n"
                "Images like ![diagram](diagram.md) are not routes.\n",
            )

            self.assertEqual(self.findings(root, "links"), [])

            write(
                root / "canon/architecture/topic.md",
                "---\nstatus: normative\nscope: [topic]\n---\n# Topic\n\n"
                "A real [broken link](gone.md).\n\n"
                "[](empty-label.md)\n\n"
                "A [see [1]](bracketed.md) reference.\n\n"
                "A [wrapped\nlabel](wrapped.md) link.\n\n"
                "Type a stray ` character here.\n\n"
                "Still a [checked](after-span.md) link.\n\n"
                "```txt\n<!-- literal comment opener in a fence\n```\n\n"
                "Fences do not hide [this](after-fence.md).\n"
                "closer -->\n\n"
                "An empty comment <!--> then [visible](after-comment.md).\n\n"
                "A stray [ bracket here.\n\n"
                "And prose ](not-a-link.md) paragraphs later.\n",
            )
            failures = self.findings(root, "links")
            broken = "\n".join(row["detail"] for row in failures)
            for target in (
                "gone.md",
                "empty-label.md",
                "bracketed.md",
                "wrapped.md",
                "after-span.md",
                "after-fence.md",
                "after-comment.md",
            ):
                self.assertIn(target, broken)
            self.assertNotIn("not-a-link.md", broken)

    def test_router_and_link_checker_agree_on_canon_prefixed_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(root)
            write(
                root / "canon/manifest.md",
                "---\nstatus: reference\n---\n# Manifest\n"
                "- [Standards](canon/standards.md) — read for project rules\n",
            )
            self.assertEqual(
                [
                    row
                    for row in self.doctor(root)
                    if row["check"] in ("manifest", "links")
                ],
                [],
            )

            for spelling in ("./canon/standards.md", "canon//standards.md"):
                write(
                    root / "canon/manifest.md",
                    "---\nstatus: reference\n---\n# Manifest\n"
                    f"- [Standards]({spelling}) — read for project rules\n",
                )
                findings = self.doctor(root)
                self.assertTrue(
                    any(row["check"] == "manifest" for row in findings),
                    (spelling, findings),
                )
                self.assertTrue(
                    any(row["check"] == "links" for row in findings),
                    (spelling, findings),
                )

    def test_decision_differing_from_head_and_baseline_reports_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Policy](decisions/policy.md) — read for policy history",
            )
            write(
                root / "canon/decisions/policy.md",
                "---\nstatus: normative\n---\n# Policy v1\n",
            )
            baseline = self.commit_all(root, "policy v1")
            write(
                root / "canon/decisions/policy.md",
                "---\nstatus: normative\n---\n# Policy v2\n",
            )
            self.commit_all(root, "policy v2")
            write(
                root / "canon/decisions/policy.md",
                "---\nstatus: normative\n---\n# Policy v3\n",
            )

            failures = self.findings(
                root,
                "decision-immutability",
                baseline=baseline,
            )
            self.assertEqual(len(failures), 1)
            self.assertIn("decisions/policy.md", failures[0]["detail"])

            (root / "canon/decisions/policy.md").unlink()
            failures = self.findings(
                root,
                "decision-immutability",
                baseline=baseline,
            )
            self.assertEqual(len(failures), 1)
            self.assertIn("missing or unsafe", failures[0]["detail"])

    def test_non_ascii_decision_filenames_stay_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Décision](decisions/décision.md) — read for accent history",
            )
            write(
                root / "canon/decisions/décision.md",
                "---\nstatus: normative\n---\n# Décision v1\n",
            )
            self.commit_all(root, "decision with non-ascii name")

            self.assertEqual(self.findings(root, "decision-immutability"), [])

            write(
                root / "canon/decisions/décision.md",
                "---\nstatus: normative\n---\n# Décision rewritten\n",
            )
            failures = self.findings(root, "decision-immutability")
            self.assertEqual(len(failures), 1)
            self.assertIn("differs", failures[0]["detail"])

    def test_percent_signs_in_paths_are_taken_literally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Rollout](architecture/rollout.md) — read for rollout policy",
            )
            write(root / "tests/rollout%20policy_test.py", "POLICY = True\n")
            write(
                root / "canon/architecture/rollout.md",
                "---\nstatus: normative\nscope: [rollout]\n"
                "validation: [tests/rollout%20policy_test.py]\n"
                "---\n# Rollout\n",
            )

            self.assertEqual(self.findings(root, "validation"), [])

    def test_nested_manifest_and_standards_names_are_not_special(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Naming](architecture/manifest.md) — read for naming rules",
                "- [Levels](architecture/standards.md) — read for level context",
            )
            write(
                root / "canon/architecture/manifest.md",
                "---\nstatus: normative\nscope: [naming]\n---\n# Naming\n",
            )
            write(
                root / "canon/architecture/standards.md",
                "---\nstatus: reference\n---\n# Levels\n",
            )

            self.assertEqual(self.doctor(root), [])

            write(
                root / "canon/manifest.md",
                "---\nstatus: reference\n---\n# Manifest\n"
                "- [Standards](standards.md) — read for project-wide rules\n"
                "- [Levels](architecture/standards.md) — read for level context\n",
            )
            failures = self.findings(root, "manifest")
            self.assertEqual(len(failures), 1)
            self.assertIn("architecture/manifest.md", failures[0]["detail"])

    def test_line_and_size_caps_reject_oversized_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_canon(
                root,
                "- [Long](architecture/long.md) — read for long rules",
                "- [Wide](architecture/wide.md) — read for wide rules",
            )
            write(
                root / "canon/architecture/long.md",
                "---\nstatus: normative\nscope: [long]\n---\n# Long\n"
                + "rule line\n" * 260,
            )
            write(
                root / "canon/architecture/wide.md",
                "---\nstatus: normative\nscope: [wide]\n---\n# Wide\n"
                + ("w" * 7000 + "\n") * 10,
            )

            line_failures = self.findings(root, "line-caps")
            self.assertEqual(len(line_failures), 1)
            self.assertIn("architecture/long.md", line_failures[0]["detail"])
            size_failures = self.findings(root, "size-caps")
            self.assertEqual(len(size_failures), 1)
            self.assertIn("architecture/wide.md", size_failures[0]["detail"])


if __name__ == "__main__":
    unittest.main()
