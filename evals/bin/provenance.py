#!/usr/bin/env python3
"""Create hash-bound eval batch provenance and terminal run receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 2


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root)
        if ".git" in rel.parts or "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        digest.update(rel.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def source_revision(root: Path) -> tuple[str | None, bool | None]:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None, None
    dirty = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True,
    )
    return proc.stdout.strip(), bool(dirty.stdout.strip()) if dirty.returncode == 0 else None


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def write_once(path: Path, data: dict) -> None:
    """Atomically publish a file without ever replacing an existing path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(path):
        raise ValueError(f"terminal receipt already exists: {path}")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        try:
            os.link(tmp, path)
        except FileExistsError as exc:
            raise ValueError(f"terminal receipt already exists: {path}") from exc
    finally:
        tmp.unlink(missing_ok=True)


def load_receipt(path: Path, expected_status: str) -> dict:
    data = json.loads(path.read_text())
    if data.get("schema_version") != SCHEMA_VERSION or data.get("status") != expected_status:
        raise ValueError(f"invalid receipt state in {path}")
    return data


def artifact(path: Path, run: Path) -> dict:
    if path.is_symlink():
        raise ValueError(f"artifact is symlinked: {path}")
    resolved = path.resolve(strict=True)
    resolved.relative_to(run.resolve())
    current = run.resolve()
    for part in resolved.relative_to(run.resolve()).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"artifact path contains a symlink: {path}")
    if not resolved.is_file():
        raise ValueError(f"artifact is not a regular file: {path}")
    return {"path": resolved.relative_to(run.resolve()).as_posix(), "sha256": file_hash(resolved)}


def repo_input(path: str, root: Path, *, directory: bool) -> Path:
    """Resolve an input while rejecting repo escapes and symlink components."""
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"input is outside repository: {path}") from exc
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"input path contains a symlink: {path}")
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    if directory != resolved.is_dir() or (not directory and not resolved.is_file()):
        raise ValueError(f"input has the wrong type: {path}")
    return resolved


def validate_run_receipt(receipt: dict, manifest: dict, run_name: str, index: int) -> str:
    if not isinstance(receipt, dict) or (
        receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("batch_id") != manifest.get("batch_id")
        or receipt.get("run_index") != index
    ):
        raise ValueError(f"inconsistent receipt for {run_name}")
    status = receipt.get("status")
    agent_status = receipt.get("agent_status")
    judge_status = receipt.get("judge_status")
    judge_requested = manifest["judge"]["status"] == "requested"
    if status not in ("completed", "failed") or agent_status not in ("completed", "failed"):
        raise ValueError(f"nonterminal receipt for {run_name}")
    if judge_requested:
        if judge_status not in ("completed", "failed", "skipped"):
            raise ValueError(f"inconsistent judge state for {run_name}")
    elif judge_status != "skipped":
        raise ValueError(f"inconsistent judge state for {run_name}")
    if status == "completed" and (
        agent_status != "completed"
        or judge_status != ("completed" if judge_requested else "skipped")
    ):
        raise ValueError(f"inconsistent completed receipt for {run_name}")
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    batch = commands.add_parser("batch")
    batch.add_argument("--out", required=True)
    batch.add_argument("--root", required=True)
    batch.add_argument("--scenario-dir", required=True)
    batch.add_argument("--scenario", required=True)
    batch.add_argument("--guidance", required=True)
    batch.add_argument("--guidance-source")
    batch.add_argument("--harness", required=True)
    batch.add_argument("--adapter", required=True)
    batch.add_argument("--runs", required=True, type=int)
    batch.add_argument("--model", default=None)
    batch.add_argument("--reasoning", default=None)
    batch.add_argument("--judge", choices=("requested", "skipped"), required=True)
    batch.add_argument("--judge-command", default="")

    start = commands.add_parser("run-start")
    start.add_argument("--run", required=True)
    start.add_argument("--index", required=True, type=int)
    start.add_argument("--batch-id", required=True)
    start.add_argument("--baseline", required=True)

    finish = commands.add_parser("run-finish")
    finish.add_argument("--run", required=True)
    finish.add_argument("--status", choices=("completed", "failed"), required=True)
    finish.add_argument("--agent-status", choices=("completed", "failed"), required=True)
    finish.add_argument("--judge-status", choices=("completed", "failed", "skipped"), required=True)
    finish.add_argument("--check", action="append", default=[])
    finish.add_argument("--judge-artifact")
    finish.add_argument("--state", action="append", default=[])

    batch_finish = commands.add_parser("batch-finish")
    batch_finish.add_argument("--out", required=True)
    batch_finish.add_argument("--status", choices=("completed", "failed"), required=True)

    validate = commands.add_parser("validate-inputs")
    validate.add_argument("--root", required=True)
    validate.add_argument("--scenario-dir", required=True)
    validate.add_argument("--guidance", required=True)

    args = parser.parse_args()
    if args.command == "batch":
        if args.runs < 1:
            raise ValueError("runs must be positive")
        out = Path(args.out).resolve()
        root = Path(args.root).resolve()
        guidance = Path(args.guidance).resolve(strict=True)
        scenario_dir = Path(args.scenario_dir).resolve(strict=True)
        adapter_path = Path(args.adapter).resolve(strict=True)
        revision, dirty = source_revision(root)
        evaluator_files = [
            root / "evals/bin/check.py",
            root / "evals/bin/judge.sh",
            root / "evals/bin/summarize.py",
            root / "evals/bin/provenance.py",
            root / "evals/judge/judge-prompt.md",
            root / "evals/rubric.md",
            root / "tools/canon-doctor.py",
            root / "tools/canonlib.py",
            adapter_path,
        ]
        guidance_data = {"path": str(guidance), "sha256": file_hash(guidance)}
        try:
            guidance_data["path"] = guidance.relative_to(out).as_posix()
        except ValueError:
            pass  # Preserve the legacy absolute path for direct callers.
        if args.guidance_source:
            source = Path(args.guidance_source).resolve(strict=True)
            if file_hash(source) != guidance_data["sha256"]:
                raise ValueError("retained guidance differs from its source")
            guidance_data["source_path"] = str(source)
        data = {
            "schema_version": SCHEMA_VERSION,
            "batch_id": secrets.token_hex(16),
            "status": "running",
            "created_at": now(),
            "scenario": args.scenario,
            "scenario_sha256": tree_hash(scenario_dir),
            "guidance": guidance_data,
            "evaluator": {
                path.relative_to(root).as_posix(): file_hash(path)
                for path in evaluator_files
            },
            "harness": args.harness,
            "adapter": adapter_path.relative_to(root).as_posix(),
            "requested_model": args.model or None,
            "requested_reasoning": args.reasoning or None,
            "judge": {
                "status": args.judge,
                "command_sha256": hashlib.sha256(args.judge_command.encode()).hexdigest()
                if args.judge_command else None,
            },
            "source_revision": revision,
            "source_dirty": dirty,
            "expected_runs": [f"run-{index}" for index in range(1, args.runs + 1)],
        }
        write(out / "manifest.json", data)
    elif args.command == "run-start":
        run = Path(args.run).resolve()
        write(run / "receipt.json", {
            "schema_version": SCHEMA_VERSION,
            "batch_id": args.batch_id,
            "run_index": args.index,
            "status": "running",
            "baseline": args.baseline,
            "started_at": now(),
        })
    elif args.command == "run-finish":
        run = Path(args.run).resolve()
        receipt_path = run / "receipt.json"
        receipt = load_receipt(receipt_path, "running")
        checks = [artifact(Path(path), run) for path in args.check]
        states = [artifact(Path(path), run) for path in args.state]
        judge_artifact = artifact(Path(args.judge_artifact), run) if args.judge_artifact else None
        receipt.update({
            "status": args.status,
            "completed_at": now(),
            "agent_status": args.agent_status,
            "judge_status": args.judge_status,
            "check_artifacts": checks,
            "judge_artifact": judge_artifact,
            "state_artifacts": states,
        })
        write(receipt_path, receipt)
    elif args.command == "batch-finish":
        out = Path(args.out).resolve()
        terminal_path = out / "batch-receipt.json"
        if os.path.lexists(terminal_path):
            raise ValueError(f"terminal receipt already exists: {terminal_path}")
        manifest_path = out / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema_version") != SCHEMA_VERSION
            or manifest.get("status") != "running"
            or not isinstance(manifest.get("batch_id"), str)
            or manifest.get("judge", {}).get("status") not in ("requested", "skipped")
        ):
            raise ValueError("invalid batch manifest")
        expected_runs = manifest.get("expected_runs")
        if not isinstance(expected_runs, list) or not expected_runs:
            raise ValueError("invalid expected run list")
        receipts = {}
        run_statuses = []
        missing = False
        for index, run_name in enumerate(expected_runs, 1):
            if run_name != f"run-{index}":
                raise ValueError("invalid expected run list")
            receipt_path = out / run_name / "receipt.json"
            if not os.path.lexists(receipt_path):
                missing = True
                continue
            if receipt_path.is_symlink() or not receipt_path.is_file():
                raise ValueError(f"invalid receipt path for {run_name}")
            receipt = json.loads(receipt_path.read_text())
            run_statuses.append(validate_run_receipt(receipt, manifest, run_name, index))
            receipts[run_name] = file_hash(receipt_path)
        if args.status == "completed" and (missing or any(s != "completed" for s in run_statuses)):
            raise ValueError("completed batch requires every run to be completed")
        if args.status == "failed" and not missing and all(s == "completed" for s in run_statuses):
            raise ValueError("failed batch has no failed or missing run")
        write_once(terminal_path, {
            "schema_version": SCHEMA_VERSION,
            "batch_id": manifest["batch_id"],
            "status": args.status,
            "completed_at": now(),
            "manifest_sha256": file_hash(manifest_path),
            "receipt_sha256": receipts,
        })
    else:
        root = Path(args.root).resolve(strict=True)
        scenario = repo_input(args.scenario_dir, root, directory=True)
        repo_input(args.guidance, root, directory=False)
        for path in scenario.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"scenario contains a symlink: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
