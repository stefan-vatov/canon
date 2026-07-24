"""Deterministic regressions for Canon validation and eval integrity."""

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
sys.path.insert(0, str(ROOT / "tools"))
from canonlib import manifest_routes  # noqa: E402

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


class CanonValidationTests(unittest.TestCase):
    def init_repo(self, root: Path) -> None:
        git(root, "init", "-q", "--template=")
        git(root, "config", "user.email", "test@example.invalid")
        git(root, "config", "user.name", "Test")
        write(root / ".gitignore", "canon/scratch/\n")
        write(
            root / "canon/standards.md",
            "---\nstatus: normative\nscope: [project-wide]\n---\n# Standards\n",
        )
        write(root / "canon/manifest.md", """---
status: reference
---
# Manifest
- [Standards](standards.md) — read for project-wide rules
- [API](architecture/api.md) — read when changing API behavior
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

    def test_manifest_routes_require_exact_safe_paths(self) -> None:
        self.assertEqual(manifest_routes("overview.md beta/overview.md canon/gamma/overview.md"),
                         set())
        self.assertEqual(manifest_routes('[Beta](beta/overview.md "title") — read for beta'),
                         {"beta/overview.md"})
        self.assertEqual(manifest_routes("[Escape](../outside.md) [Abs](/tmp/x.md)"), set())
        self.assertEqual(
            manifest_routes(
                "<!-- [Hidden](architecture/hidden.md) — read hidden -->\n"
                "```\n[Code](architecture/code.md) — read code\n```\n"
                "- [No hook](architecture/no-hook.md)\n"
                "- [Live](<architecture/live.md>) — read when changing live behavior\n"
            ),
            {"architecture/live.md"},
        )

    def test_source_only_changes_do_not_require_canon_edits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.init_repo(root)
            source = root / "app.py"
            architecture = root / "canon/architecture/api.md"
            write(source, "VALUE = 1\n")
            write(
                architecture,
                "---\nstatus: normative\nscope: [api]\n---\n"
                "# API\n\nResponses preserve the public contract.\n",
            )
            self.commit(root, "initial")
            write(source, "VALUE = 2\n")
            self.commit(root, "implementation only")

            self.assertEqual(self.doctor(root)["findings"], [])

    def test_legacy_source_inventory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.init_repo(root)
            write(root / "app.py", "VALUE = 1\n")
            write(
                root / "canon/architecture/api.md",
                "---\nstatus: normative\nsources: [app.py]\n"
                "verified: HEAD\n---\n# API\n",
            )
            self.commit(root, "baseline")
            findings = [
                row
                for row in self.doctor(root)["findings"]
                if row["check"] == "frontmatter"
            ]
            self.assertTrue(findings)
            self.assertTrue(all(
                "retired implementation-inventory" in row["detail"]
                for row in findings
            ))

    def test_symlinked_manifest_target_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.init_repo(root)
            outside = root.parent / f"{root.name}-outside.md"
            write(outside, "secret\n")
            (root / "canon/architecture").mkdir()
            (root / "canon/architecture/api.md").symlink_to(outside)
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
            write(
                root / "canon/manifest.md",
                "[Pricing](architecture/pricing.md) — read when changing pricing\n",
            )
            write(root / "canon/architecture/pricing.md", "# Pricing\n")
            git(root, "add", "-A"); git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
            expected = root / "expected.json"
            write(expected, json.dumps({
                "routing": {"must_read": ["canon/architecture/pricing.md"]}
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
            write(
                root / "canon/manifest.md",
                "---\nstatus: reference\n---\n"
                "[Pricing](architecture/pricing.md) — read when changing pricing\n",
            )
            write(
                root / "canon/standards.md",
                "---\nstatus: normative\n---\n# Standards\n",
            )
            write(
                root / "canon/architecture/pricing.md",
                "---\nstatus: normative\n---\n# Pricing\n",
            )
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
                "routing": {"must_read": ["canon/architecture/pricing.md"]}
            }))
            transcripts = root / "transcripts"
            transcripts.mkdir()
            event = {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "nl canon/architecture/pricing.md",
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

    def test_eval_checker_uses_strict_doctor_status_routing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            write(root / ".gitignore", "canon/scratch/\n")
            write(
                root / "canon/manifest.md",
                "---\nstatus: reference\n---\n"
                "- [Standards](standards.md) — read for project rules\n",
            )
            write(
                root / "canon/standards.md",
                "---\nstatus: normative\n---\n# Standards\n",
            )
            write(
                root / "canon/context.md",
                "---\nstatus: reference\n---\n# Optional context\n",
            )
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
            doctor = next(
                row for row in payload["checks"] if row["id"] == "canon_doctor"
            )
            self.assertTrue(doctor["pass"])

            write(
                root / "canon/context.md",
                "---\nstatus: invented\n---\n# Invalid context\n",
            )
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
            doctor = next(
                row for row in payload["checks"] if row["id"] == "canon_doctor"
            )
            self.assertFalse(doctor["pass"])
            self.assertFalse(payload["required_pass"])

    def test_diff_scope_can_be_a_required_no_impact_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            write(root / ".gitignore", "canon/scratch/\n")
            write(
                root / "canon/manifest.md",
                "---\nstatus: reference\n---\n"
                "- [Standards](standards.md) — read for project rules\n",
            )
            write(
                root / "canon/standards.md",
                "---\nstatus: normative\n---\n# Standards\n",
            )
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
            write(
                root / "canon/standards.md",
                "---\nstatus: normative\n---\n# Standards\n\nCeremonial rewrite.\n",
            )
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
            self.assertIn("tools/canon-doctor.py", manifest["evaluator"])
            self.assertIn("tools/canonlib.py", manifest["evaluator"])
            self.assertEqual(manifest["expected_runs"], ["run-1"])


if __name__ == "__main__":
    unittest.main()
