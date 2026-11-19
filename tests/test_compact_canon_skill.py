import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".codex" / "skills" / "compact-canon"
SCRIPT = SKILL / "scripts" / "analyze_canon.py"


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        text=True,
        capture_output=True,
        check=True,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class CompactCanonSkillTests(unittest.TestCase):
    def analyze(self, repo: Path) -> dict:
        result = subprocess.run(
            ["python3", str(SCRIPT), "--root", str(repo), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def legacy_repo(self, repo: Path) -> None:
        git(repo, "init", "-q", "--template=")
        git(repo, "config", "user.email", "test@example.invalid")
        git(repo, "config", "user.name", "Test")
        write(
            repo / "AGENTS.md",
            "First action: read canon/manifest.md and canon/glossary.md.\n",
        )
        write(repo / "canon/manifest.md", "- [Pricing](architecture/pricing.md)\n")
        write(repo / "canon/glossary.md", "Ledger: the append-only record.\n")
        write(
            repo / "canon/architecture/pricing.md",
            "---\nsources: [pricing.py]\nverified: aaaaaaa\n---\n# Pricing\n\nCaps at 40%.\n",
        )
        write(repo / "canon/decisions/2026-01-01-cap.md", "We decided 40%.\n")
        write(repo / ".gitignore", "canon/scratch/\n")
        write(repo / "canon/scratch/handover.md", "ignored session notes\n")
        write(repo / "pricing.py", "# see canon/architecture/pricing.md\nCAP = 40\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "baseline")

    def test_analyzer_is_read_only_and_inventories_legacy_canon(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            self.legacy_repo(repo)
            before = {
                path: path.read_bytes() for path in repo.rglob("*") if path.is_file()
            }

            report = self.analyze(repo)

            after = {
                path: path.read_bytes() for path in repo.rglob("*") if path.is_file()
            }
            self.assertEqual(before, after)
            canon = report["canon"]
            self.assertEqual(canon["files"], 4)
            self.assertEqual(canon["decision_records"], 1)
            self.assertEqual(canon["front_matter_files"], 1)
            self.assertEqual(canon["stamp_fields"], {"sources": 1, "verified": 1})
            self.assertEqual(canon["per_directory"]["decisions"]["files"], 1)
            self.assertNotIn("scratch", canon["per_directory"])

    def test_analyzer_counts_stamp_only_touches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            self.legacy_repo(repo)
            pricing = repo / "canon/architecture/pricing.md"
            pricing.write_text(pricing.read_text().replace("aaaaaaa", "bbbbbbb"))
            git(repo, "commit", "-qam", "docs: reverify")
            pricing.write_text(pricing.read_text().replace("40%", "45%"))
            (repo / "pricing.py").write_text("CAP = 45\n")
            git(repo, "commit", "-qam", "feat: raise cap")
            (repo / "pricing.py").write_text("CAP = 45  # cap\n")
            git(repo, "commit", "-qam", "chore: comment")

            churn = self.analyze(repo)["churn"]

            self.assertEqual(churn["commits"], 4)
            self.assertEqual(churn["commits_touching_canon"], 3)
            self.assertEqual(churn["stamp_only_touches"], 1)
            self.assertEqual(churn["canon_file_touches"], 6)

    def test_analyzer_reports_inbound_references_and_startup_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            self.legacy_repo(repo)

            report = self.analyze(repo)

            inbound = report["inbound_references"]
            self.assertIn("canon/architecture/pricing.md", inbound["targets"])
            self.assertIn("canon/manifest.md", inbound["targets"])
            startup = report["startup"]
            self.assertEqual(
                startup["canon_files_named_with_read"],
                ["canon/glossary.md", "canon/manifest.md"],
            )
            self.assertGreater(startup["canon_words_named_with_read"], 0)

    def test_analyzer_handles_a_repository_without_canon_or_git(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = self.analyze(Path(temp))
            self.assertEqual(report["canon"]["files"], 0)
            self.assertIsNone(report["churn"])

    def test_skill_migrates_decision_records_out_and_installs_no_check(self) -> None:
        text = (SKILL / "SKILL.md").read_text()
        self.assertNotIn("TODO", text)
        self.assertIn("name: compact-canon", text)
        self.assertIn("Tag", text)
        self.assertIn("decision records", text)
        self.assertIn("installs no check", text)


if __name__ == "__main__":
    unittest.main()
