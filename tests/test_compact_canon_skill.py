import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".codex" / "skills" / "compact-canon"
SCRIPT = SKILL / "scripts" / "analyze_canon.py"


class CompactCanonSkillTests(unittest.TestCase):
    def test_analyzer_is_read_only_and_reports_growth_signals(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            canon = repo / "canon"
            (canon / "domain").mkdir(parents=True)
            (canon / "overview.md").write_text("# Overview\n")
            (canon / "glossary.md").write_text("# Glossary\n")
            (canon / "standards.md").write_text("# Standards\n")
            (canon / "manifest.md").write_text("- [Overview](overview.md)\n- [Glossary](glossary.md)\n- [Standards](standards.md)\n- [Topic](domain/topic.md)\n")
            repeated = "This durable paragraph is deliberately long enough to be detected as repeated project knowledge across multiple Canon files."
            (canon / "domain" / "topic.md").write_text(f"# Topic\n\n{repeated}\n")
            (canon / "domain" / "duplicate.md").write_text(f"# Duplicate\n\n{repeated}\n")
            before = {path: path.read_bytes() for path in canon.rglob("*") if path.is_file()}
            result = subprocess.run(
                ["python3", str(SCRIPT), "--root", str(repo), "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            report = json.loads(result.stdout)
            after = {path: path.read_bytes() for path in canon.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(report["summary"]["files"], 6)
            self.assertEqual(report["missing_routes"], ["domain/duplicate.md"])
            self.assertTrue(report["repeated_paragraphs"])

    def test_analyzer_accepts_prettier_multiline_frontmatter_and_rejects_malformed_yaml(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "-q", "--template=", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            canon = repo / "canon"
            (canon / "domain").mkdir(parents=True)
            (canon / "overview.md").write_text("# Overview\n")
            (canon / "glossary.md").write_text("# Glossary\n")
            (canon / "standards.md").write_text("# Standards\n")
            (canon / "manifest.md").write_text("- [Topic](domain/topic.md)\n")
            (repo / "first.py").write_text("FIRST = 1\n")
            (repo / "second.py").write_text("SECOND = 2\n")
            (repo / "src").mkdir()
            (repo / "src" / "it's.py").write_text("THIRD = 3\n")
            for ambiguous in ("%source.py", "- source.py", "true", "123", ".5"):
                (repo / ambiguous).write_text("VALUE = 1\n")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)
            anchor = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            topic = canon / "domain" / "topic.md"
            topic.write_text(
                "---\nsources: # source paths verified below\n"
                "  [\n    first.py,\n    'second.py',\n    src/it's.py,\n  ]\n"
                f'verified: "{anchor}"\n---\n# Topic\n'
            )
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "canon"], check=True)

            report = json.loads(subprocess.run(
                ["python3", str(SCRIPT), "--root", str(repo), "--json"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout)
            record = next(item for item in report["files"] if item["path"] == "domain/topic.md")
            self.assertEqual(record["freshness"], "fresh")

            topic.write_text(
                "---\nsources: # block-list form is valid too\n"
                "  - first.py\n  - second.py\n  - src/it's.py\n"
                f"verified: {anchor}\n---\n# Topic\n"
            )
            block_report = json.loads(subprocess.run(
                ["python3", str(SCRIPT), "--root", str(repo), "--json"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout)
            record = next(
                item for item in block_report["files"]
                if item["path"] == "domain/topic.md"
            )
            self.assertEqual(record["freshness"], "fresh")

            malformed_cases = {
                "nested mapping": "sources:\n  path: first.py",
                "directive indicator": "sources: [%source.py]",
                "sequence indicator": "sources:\n  - - source.py",
                "implicit boolean": "sources: [true]",
                "implicit integer": "sources: [123]",
                "implicit leading-dot float": "sources: [.5]",
            }
            for label, sources in malformed_cases.items():
                with self.subTest(label=label):
                    topic.write_text(
                        f"---\n{sources}\nverified: {anchor}\n---\n# Topic\n"
                    )
                    malformed = json.loads(subprocess.run(
                        ["python3", str(SCRIPT), "--root", str(repo), "--json"],
                        text=True,
                        capture_output=True,
                        check=True,
                    ).stdout)
                    record = next(
                        item for item in malformed["files"]
                        if item["path"] == "domain/topic.md"
                    )
                    self.assertEqual(record["freshness"], "indeterminate")

    def test_skill_has_no_template_placeholders(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertNotIn("TODO", text)
        self.assertIn("name: compact-canon", text)


if __name__ == "__main__":
    unittest.main()
