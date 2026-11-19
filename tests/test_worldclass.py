"""Deterministic regressions for eval integrity."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHECK_SPEC = importlib.util.spec_from_file_location(
    "canon_eval_check",
    ROOT / "evals/bin/check.py",
)
assert CHECK_SPEC is not None and CHECK_SPEC.loader is not None
CHECK_MODULE = importlib.util.module_from_spec(CHECK_SPEC)
CHECK_SPEC.loader.exec_module(CHECK_MODULE)


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
            write(root / "canon/pricing.md", "# Pricing\n")
            git(root, "add", "-A"); git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
            expected = root / "expected.json"
            write(expected, json.dumps({
                "routing": {"must_read": ["canon/pricing.md"]}
            }))
            transcripts = root / "transcripts"; transcripts.mkdir()
            out = root / "checks.json"
            run(sys.executable, str(ROOT / "evals/bin/check.py"), "--workdir", str(root),
                "--expected", str(expected), "--out", str(out),
                "--transcript-dir", str(transcripts), cwd=ROOT)
            routing = next(row for row in json.loads(out.read_text())["checks"]
                           if row["id"] == "routing_precision")
            self.assertEqual(routing["outcome"], "unsupported")

    def test_unknown_command_reader_is_unsupported_not_a_false_miss(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            write(root / ".gitignore", "canon/scratch/\n")
            write(root / "canon/pricing.md", "# Pricing\n")
            git(root, "add", "-A")
            git(
                root,
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "baseline",
            )
            expected = root / "expected.json"
            write(expected, json.dumps({
                "routing": {"must_read": ["canon/pricing.md"]}
            }))
            transcripts = root / "transcripts"
            transcripts.mkdir()
            event = {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "nl canon/pricing.md",
                    "exit_code": 0,
                },
            }
            write(transcripts / "transcript.txt", json.dumps(event) + "\n")
            out = root / "checks.json"
            run(
                sys.executable,
                str(ROOT / "evals/bin/check.py"),
                "--workdir",
                str(root),
                "--expected",
                str(expected),
                "--out",
                str(out),
                "--transcript-dir",
                str(transcripts),
                cwd=ROOT,
            )

            routing = next(
                row
                for row in json.loads(out.read_text())["checks"]
                if row["id"] == "routing_precision"
            )
            self.assertEqual(routing["outcome"], "unsupported")

    def test_eval_checker_imposes_no_canon_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            write(root / "canon/long-note.md", "# Long note\n" + "line\n" * 400)
            git(root, "add", "-A")
            git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
            baseline = git(root, "rev-parse", "HEAD")
            expected = root / "expected.json"
            write(expected, "{}")
            out = root / "checks.json"
            run(
                sys.executable,
                str(ROOT / "evals/bin/check.py"),
                "--workdir",
                str(root),
                "--expected",
                str(expected),
                "--out",
                str(out),
                "--baseline",
                baseline,
                cwd=ROOT,
            )
            payload = json.loads(out.read_text())
            self.assertEqual(payload["checks"], [])
            self.assertTrue(payload["required_pass"])

    def test_rules_exclude_globs_and_match_commit_messages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            write(root / "canon/notes.md", "# Notes\n")
            git(root, "add", "-A")
            git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
            baseline = git(root, "rev-parse", "HEAD")
            write(root / "canon/scratch/handover.md", "session notes\n")
            write(root / "app.py", "VALUE = 1\n")
            git(root, "add", "app.py")
            git(root, "-c", "commit.gpgsign=false", "commit", "-qm",
                "feat: add value\n\nlocal time was rejected for UTC")
            expected = root / "expected.json"
            write(expected, json.dumps({"rules": [
                {"id": "one_note", "glob": "canon/*.md",
                 "exclude_globs": ["canon/scratch/*"], "max_matching_files": 1},
                {"id": "rationale", "glob": "*.py", "must_regex": "rejected for UTC",
                 "search_commit_messages": True},
                {"id": "files_only", "glob": "*.py", "must_regex": "rejected for UTC"},
            ]}))
            out = root / "checks.json"
            run(sys.executable, str(ROOT / "evals/bin/check.py"), "--workdir", str(root),
                "--expected", str(expected), "--out", str(out), "--baseline", baseline,
                cwd=ROOT)
            checks = {row["id"]: row["pass"] for row in json.loads(out.read_text())["checks"]}
            self.assertEqual(
                checks,
                {"rule:one_note": True, "rule:rationale": True, "rule:files_only": False},
            )

    def test_seeded_fixtures_carry_no_retired_canon_shape(self) -> None:
        for fixture in sorted((ROOT / "evals/scenarios").glob("*/fixture")):
            canon = fixture / "canon"
            with self.subTest(fixture=fixture.parent.name):
                self.assertFalse((canon / "manifest.md").exists())
                self.assertFalse((canon / "standards.md").exists())
                self.assertFalse((canon / "decisions").exists())
                for note in canon.rglob("*.md") if canon.is_dir() else []:
                    self.assertEqual(note.parent, canon, "Canon notes are flat")
                    self.assertFalse(note.read_text().startswith("---"), note.name)

    def test_diff_scope_can_be_a_required_no_impact_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            write(root / ".gitignore", "canon/scratch/\n")
            write(root / "canon/notes.md", "# Notes\n")
            write(root / "notes.py", "VALUE = 1\n")
            git(root, "add", "-A")
            git(
                root,
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "baseline",
            )
            baseline = git(root, "rev-parse", "HEAD")
            write(root / "canon/notes.md", "# Notes\n\nCeremonial rewrite.\n")
            expected = root / "expected.json"
            write(expected, json.dumps({
                "allowed_change_globs": ["notes.py"],
                "diff_scope_required": True,
                "rules": [{
                    "id": "essential_behavior",
                    "glob": "notes.py",
                    "must_regex": "MISSING_BEHAVIOR",
                }],
            }))
            out = root / "checks.json"
            run(
                sys.executable,
                str(ROOT / "evals/bin/check.py"),
                "--workdir",
                str(root),
                "--expected",
                str(expected),
                "--out",
                str(out),
                "--baseline",
                baseline,
                cwd=ROOT,
            )
            payload = json.loads(out.read_text())
            diff_scope = next(
                row for row in payload["checks"] if row["id"] == "diff_scope"
            )
            self.assertTrue(diff_scope["required"])
            self.assertFalse(diff_scope["pass"])
            essential = next(
                row
                for row in payload["checks"]
                if row["id"] == "rule:essential_behavior"
            )
            self.assertTrue(essential["required"])
            self.assertFalse(essential["pass"])
            self.assertFalse(payload["required_pass"])

    def test_scenario_rules_distinguish_evidence_from_implementation_inventory(
        self,
    ) -> None:
        feature = json.loads(
            (ROOT / "evals/scenarios/02-feature/expected.json").read_text()
        )
        routing = json.loads(
            (ROOT / "evals/scenarios/08-routing/expected.json").read_text()
        )
        impact = json.loads(
            (ROOT / "evals/scenarios/05-impact/expected.json").read_text()
        )

        feature_inventory = next(
            rule for rule in feature["rules"] if rule["id"] == "no_changelog_style"
        )["forbid_regex"]
        self.assertIsNone(
            re.search(feature_inventory, "validation:\n  - test_payments.py\n")
        )
        self.assertIsNotNone(re.search(feature_inventory, "Source: payments.py\n"))

        routing_inventory = next(
            rule
            for rule in routing["rules"]
            if rule["id"] == "no_implementation_inventory"
        )["forbid_regex"]
        self.assertIsNone(
            re.search(routing_inventory, "validation:\n  - test_billingcore.py\n")
        )
        self.assertIsNotNone(
            re.search(routing_inventory, "Implemented in billingcore.py\n")
        )

        no_floats = next(
            rule for rule in routing["rules"] if rule["id"] == "no_floats"
        )
        self.assertTrue(no_floats["forbid_python_floats"])
        self.assertEqual(
            CHECK_MODULE.python_float_signals(
                'marker = "#"; fee = amount * 250 // 10_000  # 2.5%\n'
            ),
            [],
        )
        self.assertTrue(
            CHECK_MODULE.python_float_signals(
                'marker = "#"; fee = amount * 0.025\n'
            )
        )
        self.assertTrue(CHECK_MODULE.python_float_signals("fee = amount * .025\n"))
        self.assertTrue(CHECK_MODULE.python_float_signals("fee = amount * 25e-3\n"))
        self.assertTrue(CHECK_MODULE.python_float_signals("fee = float(amount)\n"))
        self.assertTrue(
            CHECK_MODULE.python_float_signals("fee = amount * 250 / 10_000\n")
        )
        self.assertTrue(
            CHECK_MODULE.python_float_signals(
                "fee = amount * 250\nfee /= 10_000\n"
            )
        )
        self.assertTrue(CHECK_MODULE.python_float_signals("fee = amount + 0j\n"))
        self.assertEqual(CHECK_MODULE.python_float_signals("mask = 0xDEAD\n"), [])

        public_contract = next(
            rule
            for rule in impact["rules"]
            if rule["id"] == "public_contract_preserved"
        )
        self.assertEqual(public_contract["python_public_binding"], "MAX_NOTE_LENGTH")
        self.assertTrue(
            CHECK_MODULE.has_python_public_binding(
                "from note_validation import MAX_NOTE_LENGTH, validate_note_text\n",
                "MAX_NOTE_LENGTH",
            )
        )
        self.assertTrue(
            CHECK_MODULE.has_python_public_binding(
                "MAX_NOTE_LENGTH = 280\n",
                "MAX_NOTE_LENGTH",
            )
        )
        self.assertFalse(
            CHECK_MODULE.has_python_public_binding(
                "from note_validation import MAX_NOTE_LENGTH as PRIVATE_LIMIT\n",
                "MAX_NOTE_LENGTH",
            )
        )

    def test_authenticated_temporal_snapshot_detects_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); state = root / "state"; key = "secret"
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            note = root / "canon/pricing.md"
            write(note, "40 percent; fixed amounts rejected\n")
            git(root, "add", "-A"); git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
            capture = root / "capture.json"
            write(capture, json.dumps({"capture": [{"id": "old", "glob": "canon/pricing.md",
                                                    "exact_count": 1, "must_regex": "40.*fixed"}]}))
            run(sys.executable, str(ROOT / "evals/bin/check.py"), "--workdir", str(root),
                "--expected", str(capture), "--out", str(root / "capture-out.json"),
                "--state-dir", str(state), "--state-key", key, cwd=ROOT)
            write(note, "rewritten 40 percent fixed\n")
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
            self.assertNotIn("tools/canon-doctor.py", manifest["evaluator"])
            self.assertEqual(manifest["expected_runs"], ["run-1"])


if __name__ == "__main__":
    unittest.main()
