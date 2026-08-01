import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".codex" / "skills" / "compact-canon"
SCRIPT = SKILL / "scripts" / "analyze_canon.py"


class CompactCanonSkillTests(unittest.TestCase):
    def analyze(self, repo: Path) -> dict:
        result = subprocess.run(
            ["python3", str(SCRIPT), "--root", str(repo), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_analyzer_is_read_only_and_reports_growth_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            canon = repo / "canon"
            (canon / "architecture").mkdir(parents=True)
            (canon / "standards.md").write_text(
                "---\nstatus: normative\nscope: [project-wide]\n---\n# Standards\n"
            )
            (canon / "manifest.md").write_text(
                "---\nstatus: reference\n---\n"
                "- [Standards](standards.md) — read for project rules\n"
                "- [Topic](architecture/topic.md) — read for topic behavior\n"
            )
            repeated = (
                "This durable paragraph is deliberately long enough to be "
                "detected as repeated project knowledge across Canon pages."
            )
            (canon / "architecture/topic.md").write_text(
                f"---\nstatus: normative\nscope: [topic]\n---\n# Topic\n\n{repeated}\n"
            )
            (canon / "architecture/duplicate.md").write_text(
                f"---\nstatus: normative\nscope: [duplicate]\n---\n# Duplicate\n\n{repeated}\n"
            )
            before = {
                path: path.read_bytes()
                for path in canon.rglob("*")
                if path.is_file()
            }

            report = self.analyze(repo)

            after = {
                path: path.read_bytes()
                for path in canon.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertEqual(report["summary"]["files"], 4)
            self.assertEqual(
                report["missing_normative_routes"],
                ["architecture/duplicate.md"],
            )
            self.assertTrue(report["repeated_paragraphs"])

    def test_analyzer_reports_status_metadata_and_legacy_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            canon = repo / "canon"
            (canon / "architecture").mkdir(parents=True)
            (canon / "manifest.md").write_text(
                "---\nstatus: reference\n---\n"
                "- [Standards](standards.md) — read for project rules\n"
                "- [Runtime](architecture/runtime.md) — read for runtime behavior\n"
            )
            (canon / "standards.md").write_text(
                "---\nstatus: normative\nscope:\n  - project-wide\n---\n# Standards\n"
            )
            runtime = canon / "architecture/runtime.md"
            runtime.write_text(
                "---\nstatus: normative\nscope:\n  [\n    runtime,\n    persistence,\n  ]\n"
                "validation:\n  - tests/runtime_policy_test.py\n"
                "---\n# Runtime\n"
            )

            report = self.analyze(repo)
            record = next(
                item
                for item in report["files"]
                if item["path"] == "architecture/runtime.md"
            )
            self.assertEqual(record["status"], "normative")
            self.assertEqual(report["summary"]["status"]["normative"], 2)
            self.assertEqual(report["inventory_candidates"], [])

            runtime.write_text(
                "---\nstatus: normative\nsources: [src/runtime.py]\n"
                "verified: deadbeef\n---\n# Runtime\n"
            )
            legacy = self.analyze(repo)
            self.assertEqual(
                legacy["inventory_candidates"][0]["legacy_fields"],
                ["sources", "verified"],
            )

            runtime.write_text(
                "---\nstatus: normative\nscope:\n  path: runtime\n---\n# Runtime\n"
            )
            malformed = self.analyze(repo)
            record = next(
                item
                for item in malformed["files"]
                if item["path"] == "architecture/runtime.md"
            )
            self.assertEqual(record["status"], "missing")

    def test_analyzer_reports_symlinked_permanent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            canon = repo / "canon"
            outside = repo / "outside"
            canon.mkdir()
            outside.mkdir()
            (canon / "linked").symlink_to(outside, target_is_directory=True)
            (canon / "manifest.md").write_text(
                "---\nstatus: reference\n---\n# Manifest\n"
            )
            (canon / "standards.md").write_text(
                "---\nstatus: normative\n---\n# Standards\n"
            )

            report = self.analyze(repo)

            self.assertEqual(report["unsafe_paths"], ["linked"])

    def test_analyzer_route_parser_matches_titled_and_angle_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            canon = repo / "canon"
            (canon / "architecture").mkdir(parents=True)
            (canon / "manifest.md").write_text(
                "---\nstatus: reference\n---\n"
                "- [Standards](standards.md \"title\") — read for project rules\n"
                "- [Topic](<architecture/topic.md>) — read for topic behavior\n"
            )
            (canon / "standards.md").write_text(
                "---\nstatus: normative\n---\n# Standards\n"
            )
            (canon / "architecture/topic.md").write_text(
                "---\nstatus: normative\n---\n# Topic\n"
            )

            report = self.analyze(repo)

            self.assertEqual(report["missing_normative_routes"], [])
            self.assertEqual(report["dead_routes"], [])

    def test_analyzer_rejects_catalog_entries_without_read_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            canon = repo / "canon"
            (canon / "architecture").mkdir(parents=True)
            (canon / "manifest.md").write_text(
                "---\nstatus: reference\n---\n"
                "- [Standards](standards.md) "
                "[Topic](architecture/topic.md)\n"
            )
            (canon / "standards.md").write_text(
                "---\nstatus: normative\n---\n# Standards\n"
            )
            (canon / "architecture/topic.md").write_text(
                "---\nstatus: normative\n---\n# Topic\n"
            )

            report = self.analyze(repo)

            self.assertEqual(
                report["missing_normative_routes"],
                ["architecture/topic.md", "standards.md"],
            )

    def test_analyzer_rejects_image_escaped_and_code_span_pseudo_links(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            canon = repo / "canon"
            (canon / "architecture").mkdir(parents=True)
            (canon / "standards.md").write_text(
                "---\nstatus: normative\n---\n# Standards\n"
            )
            (canon / "architecture/topic.md").write_text(
                "---\nstatus: normative\n---\n# Topic\n"
            )
            pseudo_links = (
                "![Topic](architecture/topic.md)",
                r"\[Topic](architecture/topic.md)",
                "`[Topic](architecture/topic.md)`",
            )
            for pseudo_link in pseudo_links:
                (canon / "manifest.md").write_text(
                    "---\nstatus: reference\n---\n"
                    "- [Standards](standards.md) — read for project rules\n"
                    f"- {pseudo_link} — read when changing topic\n"
                )

                report = self.analyze(repo)

                self.assertEqual(
                    report["missing_normative_routes"],
                    ["architecture/topic.md"],
                    pseudo_link,
                )

    def test_analyzer_bounds_overlap_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            canon = repo / "canon"
            (canon / "architecture").mkdir(parents=True)
            (canon / "manifest.md").write_text(
                "---\nstatus: reference\n---\n# Manifest\n"
            )
            (canon / "standards.md").write_text(
                "---\nstatus: normative\n---\n# Standards\n"
            )
            for index in range(450):
                (canon / "architecture" / f"page-{index:03}.md").write_text(
                    "---\nstatus: reference\n---\n"
                    f"# Reference {index}\n\nUnique token reference-{index}.\n"
                )

            report = self.analyze(repo)

            self.assertTrue(report["summary"]["overlap_truncated"])
            self.assertEqual(
                report["summary"]["overlap_pairs_examined"],
                100_000,
            )

    def test_skill_has_no_template_placeholders(self) -> None:
        text = (SKILL / "SKILL.md").read_text()
        self.assertNotIn("TODO", text)
        self.assertIn("name: compact-canon", text)
        self.assertIn("implementation inventories", text)


if __name__ == "__main__":
    unittest.main()
