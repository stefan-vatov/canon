"""Deterministic regressions for Canon validation and eval integrity."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from canonlib import manifest_routes  # noqa: E402


def run(*args: str, cwd: Path, check: bool = True):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=check)


def git(root: Path, *args: str) -> str:
    return run("git", *args, cwd=root).stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    value = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        value.update(path.relative_to(root).as_posix().encode())
        value.update(b"\0"); value.update(path.read_bytes()); value.update(b"\0")
    return value.hexdigest()


class CanonValidationTests(unittest.TestCase):
    def init_repo(self, root: Path) -> None:
        git(root, "init", "-q", "--template=")
        git(root, "config", "user.email", "test@example.invalid")
        git(root, "config", "user.name", "Test")
        write(root / ".gitignore", "canon/scratch/\n")
        write(root / "canon/overview.md", "# Overview\n")
        write(root / "canon/glossary.md", "# Glossary\n")
        write(root / "canon/standards.md", "# Standards\n")
        write(root / "canon/manifest.md", """# Manifest
- [Overview](overview.md)
- [Glossary](glossary.md)
- [Standards](standards.md)
- [API](api/overview.md)
""")

    def commit(self, root: Path, message: str) -> str:
        git(root, "add", "-A")
        git(root, "-c", "commit.gpgsign=false", "commit", "-qm", message)
        return git(root, "rev-parse", "HEAD")

    def doctor(self, root: Path) -> dict:
        proc = run(sys.executable, str(ROOT / "tools/canon-doctor.py"),
                   "--root", str(root), "--json", cwd=ROOT, check=False)
        self.assertTrue(proc.stdout, proc.stderr)
        return json.loads(proc.stdout)

    def staleness(self, root: Path) -> list[dict]:
        return [row for row in self.doctor(root)["findings"] if row["check"] == "staleness"]

    def test_manifest_routes_require_exact_safe_paths(self) -> None:
        self.assertEqual(manifest_routes("overview.md beta/overview.md canon/gamma/overview.md"),
                         {"gamma/overview.md"})
        self.assertEqual(manifest_routes('[Beta](beta/overview.md "title")'),
                         {"beta/overview.md"})
        self.assertEqual(manifest_routes("[Escape](../outside.md) [Abs](/tmp/x.md)"), set())

    def test_same_commit_refresh_then_later_and_dirty_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.init_repo(root)
            source, domain = root / "app.py", root / "canon/api/overview.md"
            write(source, "VALUE = 1\n")
            write(domain, "---\nsources: [app.py]\nverified: 0000000\n---\n# API\n")
            first = self.commit(root, "initial")
            write(domain, f"---\nsources: [app.py]\nverified: {first}\n---\n# API\n")
            anchor = self.commit(root, "anchor")
            write(source, "VALUE = 2\n")
            write(domain, f"---\nsources: [app.py]\nverified: {anchor}\n---\n# API\n\nVALUE is 2.\n")
            self.commit(root, "atomic refresh")
            self.assertEqual(self.staleness(root), [])
            write(source, "VALUE = 3\n"); self.commit(root, "source only")
            self.assertTrue(self.staleness(root))
            write(source, "VALUE = 4\n")
            self.assertTrue(self.staleness(root))

    def test_symbolic_anchor_and_escaping_source_are_not_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.init_repo(root)
            write(root / "app.py", "VALUE = 1\n")
            write(root / "canon/api/overview.md",
                  "---\nsources: [../outside.py]\nverified: HEAD\n---\n# API\n")
            self.commit(root, "baseline")
            findings = self.staleness(root)
            self.assertTrue(findings)
            self.assertIn("immutable hexadecimal", findings[0]["detail"])

    def test_symlinked_manifest_target_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.init_repo(root)
            outside = root.parent / f"{root.name}-outside.md"
            write(outside, "secret\n")
            (root / "canon/api").mkdir()
            (root / "canon/api/overview.md").symlink_to(outside)
            self.commit(root, "fixture")
            findings = self.doctor(root)["findings"]
            self.assertTrue(any(row["severity"] == "error" and "symlink" in row["detail"]
                                for row in findings))
            outside.unlink(missing_ok=True)


class EvalIntegrityTests(unittest.TestCase):
    def check_payload(self, passed: bool = True) -> dict:
        return {
            "schema_version": 2,
            "passed": int(passed),
            "total": 1,
            "unsupported": 0,
            "score": 1.0 if passed else 0.0,
            "required_pass": passed,
            "checks": [{
                "id": "canonical", "pass": passed,
                "outcome": "pass" if passed else "fail",
                "required": True, "detail": "",
            }],
        }

    def make_result(self, root: Path, *, judge: bool = False,
                    agent_status: str = "completed") -> Path:
        result, run_dir = root, root / "run-1"
        run_dir.mkdir(parents=True)
        write(result / "guidance-used.md", "guidance\n")
        write(result / "inputs/scenario/task.md", "task\n")
        retained_checker = result / "inputs/evaluator/evals/bin/check.py"
        write(retained_checker, "# frozen checker\n")
        manifest = {
            "schema_version": 2, "status": "running", "batch_id": "batch",
            "expected_runs": ["run-1"],
            "judge": {"status": "requested" if judge else "skipped"},
            "guidance": {"sha256": digest(result / "guidance-used.md")},
            "scenario_sha256": tree_digest(result / "inputs/scenario"),
            "evaluator": {"evals/bin/check.py": digest(retained_checker)},
        }
        write(result / "manifest.json", json.dumps(manifest))
        write(run_dir / "checks.json", json.dumps(self.check_payload()))
        judge_spec = None
        if judge:
            payload = {"criteria": [{"id": "quality", "score": 1}], "judge_score": 1.0}
            write(run_dir / "judge.json", json.dumps(payload))
            judge_spec = {"path": "judge.json", "sha256": digest(run_dir / "judge.json")}
        receipt = {
            "schema_version": 2, "batch_id": "batch", "run_index": 1,
            "status": "completed", "agent_status": agent_status,
            "judge_status": "completed" if judge else "skipped",
            "baseline": "a" * 40,
            "check_artifacts": [{"path": "checks.json", "sha256": digest(run_dir / "checks.json")}],
            "judge_artifact": judge_spec, "state_artifacts": [],
        }
        write(run_dir / "receipt.json", json.dumps(receipt))
        terminal = {
            "schema_version": 2, "batch_id": "batch", "status": "completed",
            "manifest_sha256": digest(result / "manifest.json"),
            "receipt_sha256": {"run-1": digest(run_dir / "receipt.json")},
        }
        write(result / "batch-receipt.json", json.dumps(terminal))
        return result

    def summarize(self, result: Path, check: bool = True):
        return run(sys.executable, str(ROOT / "evals/bin/summarize.py"), str(result),
                   cwd=ROOT, check=check)

    def test_summary_uses_hash_bound_receipt_lineage_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.make_result(Path(directory))
            write(result / "run-1/checks-rescored.json", json.dumps(self.check_payload(False)))
            self.summarize(result)
            summary = json.loads((result / "summary.json").read_text())
            self.assertTrue(summary["complete"])
            self.assertEqual(summary["mechanical_mean"], 1.0)

    def test_corrupt_judge_failed_agent_and_digest_mismatch_reject(self) -> None:
        for mode in ("judge", "agent", "digest"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                result = self.make_result(Path(directory), judge=mode == "judge",
                                          agent_status="failed" if mode == "agent" else "completed")
                if mode == "judge":
                    write(result / "run-1/judge.json", '{"unexpected": true}')
                    # Rebind the artifact to prove schema validation, not just digest validation.
                    receipt = json.loads((result / "run-1/receipt.json").read_text())
                    receipt["judge_artifact"]["sha256"] = digest(result / "run-1/judge.json")
                    write(result / "run-1/receipt.json", json.dumps(receipt))
                    terminal = json.loads((result / "batch-receipt.json").read_text())
                    terminal["receipt_sha256"]["run-1"] = digest(result / "run-1/receipt.json")
                    write(result / "batch-receipt.json", json.dumps(terminal))
                elif mode == "digest":
                    write(result / "run-1/checks.json", json.dumps(self.check_payload(False)))
                proc = self.summarize(result, check=False)
                self.assertNotEqual(proc.returncode, 0)
                self.assertFalse(json.loads((result / "summary.json").read_text())["complete"])

    def test_missing_routing_telemetry_is_unsupported_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            write(root / "canon/manifest.md", "[Pricing](pricing/overview.md)\n")
            write(root / "canon/pricing/overview.md", "# Pricing\n")
            git(root, "add", "-A"); git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
            expected = root / "expected.json"
            write(expected, json.dumps({"routing": {"must_read": ["canon/pricing/overview.md"]}}))
            transcripts = root / "transcripts"; transcripts.mkdir()
            out = root / "checks.json"
            run(sys.executable, str(ROOT / "evals/bin/check.py"), "--workdir", str(root),
                "--expected", str(expected), "--out", str(out),
                "--transcript-dir", str(transcripts), cwd=ROOT)
            routing = next(row for row in json.loads(out.read_text())["checks"]
                           if row["id"] == "routing_precision")
            self.assertEqual(routing["outcome"], "unsupported")

    def test_authenticated_temporal_snapshot_detects_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); state = root / "state"; key = "secret"
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            decision = root / "canon/decisions/old.md"
            write(decision, "40 percent; fixed amounts rejected\n")
            write(root / "canon/manifest.md", "[Old](decisions/old.md)\n")
            git(root, "add", "-A"); git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
            capture = root / "capture.json"
            write(capture, json.dumps({"capture": [{"id": "old", "glob": "canon/decisions/*.md",
                                                    "exact_count": 1, "must_regex": "40.*fixed"}]}))
            run(sys.executable, str(ROOT / "evals/bin/check.py"), "--workdir", str(root),
                "--expected", str(capture), "--out", str(root / "capture-out.json"),
                "--state-dir", str(state), "--state-key", key, cwd=ROOT)
            write(decision, "rewritten 40 percent fixed\n")
            preserve = root / "preserve.json"
            write(preserve, json.dumps({"preserve": [{"snapshot": "old", "exact_set": True}]}))
            run(sys.executable, str(ROOT / "evals/bin/check.py"), "--workdir", str(root),
                "--expected", str(preserve), "--out", str(root / "preserve-out.json"),
                "--state-dir", str(state), "--state-key", key, cwd=ROOT)
            payload = json.loads((root / "preserve-out.json").read_text())
            self.assertFalse(payload["required_pass"])

    def test_batch_provenance_hashes_inputs_and_toolchain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory); scenario = temp / "scenario"; out = temp / "result"
            write(scenario / "task.md", "Task\n"); write(temp / "guidance.md", "Guidance\n")
            out.mkdir()
            run(sys.executable, str(ROOT / "evals/bin/provenance.py"), "batch",
                "--out", str(out), "--root", str(ROOT), "--scenario-dir", str(scenario),
                "--scenario", "fixture", "--guidance", str(temp / "guidance.md"),
                "--harness", "codex", "--adapter", str(ROOT / "evals/adapters/codex.sh"),
                "--runs", "1", "--judge", "skipped", cwd=ROOT)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(len(manifest["guidance"]["sha256"]), 64)
            self.assertIn("evals/bin/check.py", manifest["evaluator"])
            self.assertEqual(manifest["expected_runs"], ["run-1"])


if __name__ == "__main__":
    unittest.main()
