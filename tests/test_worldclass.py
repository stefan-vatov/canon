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
                    agent_status: str = "completed", scenario_expected=None,
                    judge_criteria=None) -> Path:
        result, run_dir = root, root / "run-1"
        run_dir.mkdir(parents=True)
        write(result / "guidance-used.md", "guidance\n")
        write(result / "inputs/scenario/task.md", "task\n")
        if scenario_expected is not None:
            write(result / "inputs/scenario/expected.json", json.dumps(scenario_expected))
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
            criteria = judge_criteria or [{"id": "quality", "score": 1, "reason": ""}]
            scores = [c["score"] for c in criteria if c["score"] is not None]
            payload = {"criteria": criteria, "notes": "",
                       "judge_score": round(sum(scores) / len(scores), 3)}
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

    def test_required_judge_criteria_gate_a_full_pass(self) -> None:
        expected = {"judge_required": [{"id": "meaning_kept", "criterion": "..."}]}
        for criteria, passes in (
            ([{"id": "quality", "score": 1, "reason": ""}], False),
            ([{"id": "meaning_kept", "score": 0, "reason": ""}], False),
            ([{"id": "meaning_kept", "score": 1, "reason": ""}], True),
        ):
            with self.subTest(criteria=criteria), tempfile.TemporaryDirectory() as directory:
                result = self.make_result(Path(directory), judge=True,
                                          scenario_expected=expected,
                                          judge_criteria=criteria)
                self.summarize(result)
                summary = json.loads((result / "summary.json").read_text())
                self.assertEqual(summary["pass_all_required"], passes, summary["failed"])

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
                "routing": {"must_read": ["canon/pricing.md"], "require_telemetry": False}
            }))
            transcripts = root / "transcripts"; transcripts.mkdir()
            out = root / "checks.json"
            run(sys.executable, str(ROOT / "evals/bin/check.py"), "--workdir", str(root),
                "--expected", str(expected), "--out", str(out),
                "--transcript-dir", str(transcripts), cwd=ROOT)
            routing = next(row for row in json.loads(out.read_text())["checks"]
                           if row["id"] == "routing_precision")
            self.assertEqual(routing["outcome"], "unsupported")

    def routing_check(self, events, routing: dict, parent: str = "") -> dict:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / parent / "workspace" if parent else Path(directory)
            root.mkdir(parents=True, exist_ok=True)
            if callable(events):
                events = events(root)
            git(root, "init", "-q", "--template=")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            for name in ("pricing", "billing", "tax"):
                write(root / f"canon/{name}.md", f"# {name}\n")
            write(root / "app.py", "VALUE = 1\n")
            git(root, "add", "-A")
            git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
            expected = root / "expected.json"
            write(expected, json.dumps({"routing": routing}))
            transcripts = root / "transcripts"
            transcripts.mkdir()
            write(transcripts / "transcript.txt",
                  "".join(json.dumps(event) + "\n" for event in events))
            out = root / "checks.json"
            run(sys.executable, str(ROOT / "evals/bin/check.py"), "--workdir", str(root),
                "--expected", str(expected), "--out", str(out),
                "--transcript-dir", str(transcripts), cwd=ROOT)
            return next(row for row in json.loads(out.read_text())["checks"]
                        if row["id"] == "routing_precision")

    @staticmethod
    def codex(command: str, exit_code: int = 0) -> dict:
        return {"type": "item.completed", "item": {
            "type": "command_execution", "command": command, "exit_code": exit_code}}

    @staticmethod
    def claude(tool: str, tool_input: dict, error: bool = False) -> list[dict]:
        return [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": tool, "input": tool_input}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "is_error": error}]}},
        ]

    def test_zero_canon_reads_is_a_measured_pass(self) -> None:
        cold = {"domain_glob": "canon/*", "max_domain_reads": 0, "require_telemetry": True}
        row = self.routing_check(
            [self.codex("ls canon/"), self.codex("cat app.py")], cold)
        self.assertEqual(row["outcome"], "pass", row)
        self.assertIn("none", row["detail"])

    def test_cold_start_requires_telemetry(self) -> None:
        cold = {"domain_glob": "canon/*", "max_domain_reads": 0, "require_telemetry": True}
        row = self.routing_check([], cold)
        self.assertEqual(row["outcome"], "fail", row)
        self.assertTrue(row["required"])

    def test_canon_reads_are_detected_in_every_common_form(self) -> None:
        cold = {"domain_glob": "canon/*", "max_domain_reads": 0}
        for events in (
            [self.codex("cat canon/*.md")],
            [self.codex("rg -n retry canon")],
            [self.codex("bash -lc 'cat canon/pricing.md'")],
            [self.codex("nl ./canon/pricing.md | head")],
            [self.codex("grep -r fee canon/ && echo done")],
            [self.codex("cd canon && cat pricing.md")],
            [self.codex("bash -lc '(cd canon; wc -w *.md)'")],
            [self.codex("rg foo")],
            [self.codex("grep -rn fee .")],
            [self.codex("for f in canon/*.md; do head -3 \"$f\"; done")],
            [self.codex("find canon -name '*.md' -exec cat {} +")],
            lambda root: self.claude("Read", {"file_path": f"{root}/canon/pricing.md"}),
            self.claude("Bash", {"command": "sed -n 1,20p canon/tax.md"}),
            self.claude("Grep", {"pattern": "fee", "path": "canon"}),
        ):
            with self.subTest(events=events):
                row = self.routing_check(events, cold)
                self.assertEqual(row["outcome"], "fail", row)

    def test_failed_or_listing_commands_are_not_reads(self) -> None:
        cold = {"domain_glob": "canon/*", "max_domain_reads": 0}
        events = [self.codex("cat canon/missing.md", exit_code=1), self.codex("ls canon"),
                  self.codex("find canon -type f"), self.codex("cat app.py | rg VALUE"),
                  self.codex("grep VALUE app.py")]
        events += self.claude("Read", {"file_path": "canon/pricing.md"}, error=True)
        self.assertEqual(self.routing_check(events, cold)["outcome"], "pass")

    def test_workspace_under_a_canon_parent_is_not_canon(self) -> None:
        cold = {"domain_glob": "canon/*", "max_domain_reads": 0}

        def events(root: Path) -> list[dict]:
            return (self.claude("Read", {"file_path": f"{root}/app.py"})
                    + [self.codex("cat app.py"), self.codex(f"cat {root}/app.py")])

        row = self.routing_check(events, cold, parent="canon/evals/results")
        self.assertEqual(row["outcome"], "pass", row)

    def test_bulk_read_fails_routing_and_targeted_read_passes(self) -> None:
        routing = {"domain_glob": "canon/*.md", "must_read": ["canon/pricing.md"],
                   "max_domain_reads": 2}
        bulk = self.routing_check([self.codex("cat canon/*.md")], routing)
        self.assertEqual(bulk["outcome"], "fail", bulk)
        targeted = self.routing_check([self.codex("cat canon/pricing.md")], routing)
        self.assertEqual(targeted["outcome"], "pass", targeted)

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

    def test_generated_artifacts_are_one_managed_block(self) -> None:
        core = (ROOT / "canon-core.md").read_text()
        for name in ("AGENTS.md", "CLAUDE.md"):
            text = (ROOT / "dist" / name).read_text()
            with self.subTest(artifact=name):
                self.assertTrue(text.startswith("<!-- BEGIN PROJECT CANON -->\n<!-- GENERATED"))
                self.assertTrue(text.endswith(core + "<!-- END PROJECT CANON -->\n"))
                self.assertEqual(text.count("<!-- BEGIN PROJECT CANON -->"), 1)

    def test_record_rules_match_any_case(self) -> None:
        rules = {}
        for path in sorted((ROOT / "evals/scenarios").rglob("expected.json")):
            for rule in json.loads(path.read_text()).get("rules", []):
                if rule["id"] in ("no_decision_records", "no_adr_records"):
                    rules[rule["id"]] = rule
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("docs/ADR-0001.md", "DECISIONS.md", "canon/Decision-Log.md"):
                write(root / name, "x\n")
            write(root / "decision_helpers.py", "x = 1\n")
            found = {
                rule_id: [p.relative_to(root).as_posix() for p in CHECK_MODULE.selected_files(
                    root, rule["glob"], rule["exclude_globs"], rule["ignore_case"])]
                for rule_id, rule in rules.items()
            }
        self.assertEqual(found["no_adr_records"], ["docs/ADR-0001.md"])
        self.assertEqual(found["no_decision_records"], ["DECISIONS.md", "canon/Decision-Log.md"])

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
