import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "evals/bin/provenance.py"


def write(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) if isinstance(payload, dict) else payload)


class TerminalReceiptTests(unittest.TestCase):
    def command(self, *args: str, check: bool = True):
        return subprocess.run(
            [sys.executable, str(PROVENANCE), *args], text=True,
            capture_output=True, check=check,
        )

    def manifest(self, out: Path, runs: int = 1) -> None:
        write(out / "manifest.json", {
            "schema_version": 2, "status": "running", "batch_id": "batch",
            "judge": {"status": "skipped"},
            "expected_runs": [f"run-{i}" for i in range(1, runs + 1)],
        })

    def receipt(self, out: Path, index: int, status: str = "completed") -> None:
        write(out / f"run-{index}/receipt.json", {
            "schema_version": 2, "batch_id": "batch", "run_index": index,
            "status": status, "agent_status": "completed", "judge_status": "skipped",
        })

    def test_terminal_receipt_is_immutable_and_completed_state_is_coherent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); self.manifest(out); self.receipt(out, 1)
            self.command("batch-finish", "--out", str(out), "--status", "completed")
            original = (out / "batch-receipt.json").read_bytes()
            proc = self.command("batch-finish", "--out", str(out),
                                "--status", "failed", check=False)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual((out / "batch-receipt.json").read_bytes(), original)

            (out / "batch-receipt.json").unlink()
            self.receipt(out, 1, "failed")
            proc = self.command("batch-finish", "--out", str(out),
                                "--status", "completed", check=False)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse((out / "batch-receipt.json").exists())

    def test_failed_batch_rejects_running_or_all_completed_runs(self) -> None:
        for status in ("running", "completed"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                out = Path(directory); self.manifest(out); self.receipt(out, 1, status)
                proc = self.command("batch-finish", "--out", str(out),
                                    "--status", "failed", check=False)
                self.assertNotEqual(proc.returncode, 0)
                self.assertFalse((out / "batch-receipt.json").exists())

    def test_retained_guidance_path_and_symlink_input_rejection(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            base = Path(directory); scenario = base / "scenario"; scenario.mkdir()
            guidance = base / "guidance.md"; write(guidance, "guidance\n")
            retained = base / "result/guidance-used.md"; write(retained, "guidance\n")
            self.command(
                "batch", "--out", str(base / "result"), "--root", str(ROOT),
                "--scenario-dir", str(scenario), "--scenario", "fixture",
                "--guidance", str(retained), "--guidance-source", str(guidance),
                "--harness", "codex", "--adapter", str(ROOT / "evals/adapters/codex.sh"),
                "--runs", "1", "--judge", "skipped",
            )
            manifest = json.loads((base / "result/manifest.json").read_text())
            self.assertEqual(manifest["guidance"]["path"], "guidance-used.md")
            self.assertEqual(manifest["guidance"]["source_path"], str(guidance))

            proc = self.command("validate-inputs", "--root", str(ROOT),
                                "--scenario-dir", str(scenario), "--guidance", str(guidance))
            self.assertEqual(proc.returncode, 0)
            (scenario / "escape").symlink_to(Path("/tmp"))
            proc = self.command("validate-inputs", "--root", str(ROOT),
                                "--scenario-dir", str(scenario), "--guidance", str(guidance),
                                check=False)
            self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
