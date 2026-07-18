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

    def test_skill_has_no_template_placeholders(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertNotIn("TODO", text)
        self.assertIn("name: compact-canon", text)


if __name__ == "__main__":
    unittest.main()
