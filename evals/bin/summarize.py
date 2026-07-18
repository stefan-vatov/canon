#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Validate and aggregate only hash-bound canonical eval artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path


SCHEMA_VERSION = 2


class InvalidResult(ValueError):
    pass


def read_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except OSError as exc:
        raise InvalidResult(f"missing artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InvalidResult(f"corrupt JSON artifact: {path}") from exc
    if not isinstance(data, dict):
        raise InvalidResult(f"JSON object required: {path}")
    return data


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retained_path(
    result_dir: Path,
    relative: str,
    label: str,
    *,
    directory: bool = False,
) -> Path:
    """Return a retained input only when every in-bundle component is trusted."""
    candidate = Path(relative) if isinstance(relative, str) else Path("/")
    if (
        not isinstance(relative, str)
        or candidate.is_absolute()
        or not candidate.parts
        or ".." in candidate.parts
    ):
        raise InvalidResult(f"invalid retained {label} path: {relative!r}")

    root = result_dir.resolve(strict=True)
    current = result_dir
    if current.is_symlink():
        raise InvalidResult(f"retained {label} path is symlinked: {relative}")
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise InvalidResult(f"retained {label} path is symlinked: {relative}")

    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise InvalidResult(f"retained {label} escapes or is missing: {relative}") from exc
    expected_kind = current.is_dir() if directory else current.is_file()
    if not expected_kind:
        kind = "directory" if directory else "file"
        raise InvalidResult(f"retained {label} is not a regular {kind}: {relative}")
    return current


def tree_sha256(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise InvalidResult(f"retained scenario is not a trusted directory: {root}")
    resolved_root = root.resolve(strict=True)
    digest = hashlib.sha256()
    files = []

    def raise_walk_error(exc: OSError) -> None:
        raise exc

    for directory, dirnames, filenames in os.walk(root, followlinks=False, onerror=raise_walk_error):
        parent = Path(directory)
        for name in dirnames + filenames:
            path = parent / name
            if path.is_symlink():
                raise InvalidResult(f"retained scenario contains a symlink: {path}")
            try:
                path.resolve(strict=True).relative_to(resolved_root)
            except (OSError, ValueError) as exc:
                raise InvalidResult(f"retained scenario path escapes or is missing: {path}") from exc
        for name in filenames:
            path = parent / name
            if not path.is_file():
                raise InvalidResult(f"retained scenario contains a non-file: {path}")
            files.append(path)

    for path in sorted(files):
        rel = path.relative_to(root)
        if ".git" in rel.parts or "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        digest.update(rel.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def atomic_write_summary(result_dir: Path, payload: dict) -> None:
    destination = result_dir / "summary.json"
    fd, raw = tempfile.mkstemp(prefix=".summary-", suffix=".json", dir=result_dir)
    temporary = Path(raw)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def write_summary(result_dir: Path, payload: dict) -> None:
    if (result_dir / "summary.json").is_symlink():
        raise InvalidResult("summary.json must not be a symlink")
    atomic_write_summary(result_dir, payload)


def invalidate_summary(result_dir: Path, payload: dict) -> str | None:
    """Atomically replace stale output, falling back to removing it on write failure."""
    destination = result_dir / "summary.json"
    try:
        result_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_summary(result_dir, payload)
        return None
    except OSError as write_error:
        try:
            destination.unlink(missing_ok=True)
        except OSError as remove_error:
            return f"could not invalidate summary ({write_error}); could not remove it ({remove_error})"
        return f"could not write invalid summary ({write_error}); stale summary removed"


def finite_score(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidResult(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise InvalidResult(f"{label} must be finite and within [0, 1]")
    return value


def artifact_path(run: Path, spec: dict, label: str) -> Path:
    if not isinstance(spec, dict) or set(spec) != {"path", "sha256"}:
        raise InvalidResult(f"invalid {label} artifact declaration")
    name = spec["path"]
    candidate = Path(name) if isinstance(name, str) else Path("/")
    if (
        not isinstance(name, str)
        or candidate.is_absolute()
        or not candidate.parts
        or ".." in candidate.parts
    ):
        raise InvalidResult(f"invalid {label} artifact path: {name!r}")
    path = run / name
    if path.is_symlink() or not path.is_file():
        raise InvalidResult(f"missing or symlinked {label} artifact: {name}")
    current = run
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise InvalidResult(f"{label} artifact path is symlinked: {name}")
    try:
        path.resolve().relative_to(run.resolve())
    except ValueError as exc:
        raise InvalidResult(f"{label} artifact escapes run: {name}") from exc
    if not isinstance(spec["sha256"], str) or sha256(path) != spec["sha256"]:
        raise InvalidResult(f"{label} artifact digest mismatch: {name}")
    return path


def validate_checks(path: Path) -> tuple[list[dict], float, bool]:
    data = read_object(path)
    required_keys = {
        "schema_version", "passed", "total", "unsupported", "score",
        "required_pass", "checks",
    }
    if data.get("schema_version") != SCHEMA_VERSION or not required_keys <= set(data):
        raise InvalidResult(f"unsupported or incomplete check schema: {path}")
    checks = data["checks"]
    if not isinstance(checks, list) or not checks:
        raise InvalidResult(f"non-empty checks list required: {path}")
    ids = []
    measured = []
    required_ok = True
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise InvalidResult(f"check {index} is not an object: {path}")
        check_id = check.get("id")
        outcome = check.get("outcome")
        if not isinstance(check_id, str) or not check_id:
            raise InvalidResult(f"check {index} has no id: {path}")
        if check_id in ids:
            raise InvalidResult(f"duplicate check id {check_id!r}: {path}")
        ids.append(check_id)
        if outcome not in ("pass", "fail", "unsupported"):
            raise InvalidResult(f"invalid outcome for {check_id}: {outcome!r}")
        expected_pass = outcome == "pass"
        if check.get("pass") is not expected_pass:
            raise InvalidResult(f"inconsistent pass/outcome for {check_id}")
        if not isinstance(check.get("required"), bool):
            raise InvalidResult(f"required flag missing for {check_id}")
        if check["required"] and outcome != "pass":
            required_ok = False
        if outcome != "unsupported":
            measured.append(check)
    passed = sum(check["outcome"] == "pass" for check in measured)
    score = round(passed / len(measured), 3) if measured else None
    if (
        data["passed"] != passed
        or data["total"] != len(measured)
        or data["unsupported"] != len(checks) - len(measured)
        or data["score"] != score
        or data["required_pass"] is not required_ok
    ):
        raise InvalidResult(f"check totals do not match payload: {path}")
    if score is None:
        raise InvalidResult(f"no measured checks: {path}")
    return checks, score, required_ok


def validate_judge(path: Path) -> tuple[dict, float]:
    judge = read_object(path)
    if "notes" not in judge or not isinstance(judge["notes"], str):
        raise InvalidResult("judge notes must be a string")
    criteria = judge.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise InvalidResult("judge criteria must be a non-empty list")
    ids, numeric = set(), []
    for criterion in criteria:
        if (
            not isinstance(criterion, dict)
            or not isinstance(criterion.get("id"), str)
            or not criterion["id"]
        ):
            raise InvalidResult("invalid judge criterion")
        if "reason" not in criterion or not isinstance(criterion["reason"], str):
            raise InvalidResult(f"judge criterion {criterion['id']} reason must be a string")
        if criterion["id"] in ids:
            raise InvalidResult(f"duplicate judge criterion: {criterion['id']}")
        ids.add(criterion["id"])
        score = criterion.get("score")
        if score is not None:
            if score not in (0, 1) or isinstance(score, bool):
                raise InvalidResult(f"judge criterion {criterion['id']} must be 0, 1, or null")
            numeric.append(score)
    if not numeric:
        raise InvalidResult("judge has no measured criteria")
    score = finite_score(judge.get("judge_score"), "judge_score")
    expected = round(sum(numeric) / len(numeric), 3)
    if score != expected:
        raise InvalidResult(f"judge_score {score} does not equal criterion mean {expected}")
    return judge, score


def summarize(result_dir: Path) -> dict:
    result_dir = result_dir.resolve()
    manifest = read_object(result_dir / "manifest.json")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("status") != "running":
        raise InvalidResult("unsupported batch manifest")
    batch_id = manifest.get("batch_id")
    guidance = manifest.get("guidance")
    retained_guidance = retained_path(result_dir, "guidance-used.md", "guidance")
    if (
        not isinstance(guidance, dict)
        or guidance.get("sha256") != sha256(retained_guidance)
    ):
        raise InvalidResult("retained guidance does not match manifest")
    scenario_inputs = retained_path(
        result_dir, "inputs/scenario", "scenario", directory=True
    )
    if (
        manifest.get("scenario_sha256") != tree_sha256(scenario_inputs)
    ):
        raise InvalidResult("retained scenario does not match manifest")
    evaluator = manifest.get("evaluator")
    if not isinstance(evaluator, dict) or not evaluator:
        raise InvalidResult("evaluator lineage is missing")
    evaluator_inputs = retained_path(
        result_dir, "inputs/evaluator", "evaluator", directory=True
    )
    for relative, expected_digest in evaluator.items():
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or not Path(relative).parts
            or ".." in Path(relative).parts
            or not isinstance(expected_digest, str)
        ):
            raise InvalidResult("invalid evaluator input path")
        retained = retained_path(evaluator_inputs, relative, "evaluator input")
        if sha256(retained) != expected_digest:
            raise InvalidResult(f"retained evaluator input mismatch: {relative}")
    batch_receipt = read_object(result_dir / "batch-receipt.json")
    if (
        batch_receipt.get("schema_version") != SCHEMA_VERSION
        or batch_receipt.get("batch_id") != batch_id
        or batch_receipt.get("status") != "completed"
        or batch_receipt.get("manifest_sha256") != sha256(result_dir / "manifest.json")
    ):
        raise InvalidResult("batch receipt is missing, failed, or inconsistent")
    expected_runs = manifest.get("expected_runs")
    if (
        not isinstance(batch_id, str)
        or not batch_id
        or not isinstance(expected_runs, list)
        or not expected_runs
        or any(not isinstance(name, str) for name in expected_runs)
        or len(expected_runs) != len(set(expected_runs))
        or any(name != f"run-{index}" for index, name in enumerate(expected_runs, 1))
    ):
        raise InvalidResult("invalid expected run lineage")
    disk_runs = sorted(path.name for path in result_dir.glob("run-*") if path.is_dir())
    if disk_runs != sorted(expected_runs):
        raise InvalidResult("run directories do not match expected run lineage")

    judge_declaration = manifest.get("judge")
    if (
        not isinstance(judge_declaration, dict)
        or judge_declaration.get("status") not in ("requested", "skipped")
    ):
        raise InvalidResult("invalid judge lineage")
    judge_requested = judge_declaration["status"] == "requested"
    rows, failed_checks, unsupported, judge_notes = [], {}, {}, []
    all_required = True
    for index, run_name in enumerate(expected_runs, 1):
        run = result_dir / run_name
        receipt = read_object(run / "receipt.json")
        if batch_receipt.get("receipt_sha256", {}).get(run_name) != sha256(run / "receipt.json"):
            raise InvalidResult(f"{run_name}: receipt digest does not match terminal batch receipt")
        if (
            receipt.get("schema_version") != SCHEMA_VERSION
            or receipt.get("batch_id") != batch_id
            or receipt.get("run_index") != index
            or receipt.get("status") != "completed"
            or receipt.get("agent_status") != "completed"
        ):
            raise InvalidResult(f"{run_name}: incomplete or inconsistent receipt")
        baseline = receipt.get("baseline")
        if not isinstance(baseline, str) or len(baseline) < 7:
            raise InvalidResult(f"{run_name}: missing immutable baseline")

        specs = receipt.get("check_artifacts")
        if not isinstance(specs, list) or not specs:
            raise InvalidResult(f"{run_name}: no canonical check artifacts")
        all_checks, scores, required_flags, names = [], [], [], []
        for spec in specs:
            path = artifact_path(run, spec, "check")
            names.append(path.relative_to(run).as_posix())
            checks, score, required_ok = validate_checks(path)
            step = "final" if path.name == "checks.json" else path.stem.removeprefix("checks-")
            all_checks.extend((step, check) for check in checks)
            scores.append(score)
            required_flags.append(required_ok)
        if len(names) != len(set(names)):
            raise InvalidResult(f"{run_name}: duplicate canonical check lineage")

        state_specs = receipt.get("state_artifacts")
        if not isinstance(state_specs, list):
            raise InvalidResult(f"{run_name}: invalid temporal-state lineage")
        state_names = []
        for spec in state_specs:
            state_names.append(artifact_path(run, spec, "state").name)
        if len(state_names) != len(set(state_names)):
            raise InvalidResult(f"{run_name}: duplicate temporal-state lineage")

        judge = None
        judge_score = None
        judge_spec = receipt.get("judge_artifact")
        if judge_requested:
            if receipt.get("judge_status") != "completed" or judge_spec is None:
                raise InvalidResult(f"{run_name}: requested judge is incomplete")
            judge, judge_score = validate_judge(artifact_path(run, judge_spec, "judge"))
        elif receipt.get("judge_status") != "skipped" or judge_spec is not None:
            raise InvalidResult(f"{run_name}: skipped judge state is inconsistent")

        measured = [check for _, check in all_checks if check["outcome"] != "unsupported"]
        mechanical = round(
            sum(check["outcome"] == "pass" for check in measured) / len(measured), 3
        )
        run_required = all(required_flags)
        all_required = all_required and run_required
        rows.append((run_name, mechanical, judge_score, run_required))
        for step, check in all_checks:
            check_id = check["id"] if step == "final" else f"{step}:{check['id']}"
            if check["outcome"] == "unsupported":
                unsupported.setdefault(check_id, []).append(run_name)
            elif check["outcome"] != "pass":
                failed_checks.setdefault(check_id, []).append(run_name)
        if judge:
            for criterion in judge["criteria"]:
                if criterion.get("score") == 0:
                    failed_checks.setdefault(f"judge:{criterion['id']}", []).append(run_name)
            if judge.get("notes"):
                judge_notes.append(f"{run_name}: {judge['notes']}")

    mechanical_mean = round(sum(row[1] for row in rows) / len(rows), 3)
    judge_values = [row[2] for row in rows if row[2] is not None]
    if judge_requested and len(judge_values) != len(rows):
        raise InvalidResult("judge denominator does not match requested runs")
    summary = {
        "schema_version": SCHEMA_VERSION,
        "result_dir": str(result_dir),
        "runs": len(rows),
        "complete": True,
        "pass_all_required": all_required,
        "mechanical_mean": mechanical_mean,
        "judge_mean": round(sum(judge_values) / len(judge_values), 3) if judge_values else None,
        "failed": {key: value for key, value in sorted(failed_checks.items())},
        "unsupported": {key: value for key, value in sorted(unsupported.items())},
        "manifest_sha256": sha256(result_dir / "manifest.json"),
        "comparison_key": {
            "scenario": manifest.get("scenario"),
            "scenario_sha256": manifest.get("scenario_sha256"),
            "harness": manifest.get("harness"),
            "adapter": manifest.get("adapter"),
            "requested_model": manifest.get("requested_model"),
            "requested_reasoning": manifest.get("requested_reasoning"),
            "judge": manifest.get("judge"),
            "source_revision": manifest.get("source_revision"),
            "source_dirty": manifest.get("source_dirty"),
            "runs": len(expected_runs),
            "evaluator": manifest.get("evaluator"),
        },
    }
    write_summary(result_dir, summary)

    print(f"\n=== {result_dir.name} ===")
    print(f"{'run':<10} {'mechanical':>11} {'judge':>7} {'required':>9}")
    for name, mechanical, judge_score, required_ok in rows:
        print(f"{name:<10} {mechanical:>11.2f} {fmt(judge_score):>7} {str(required_ok):>9}")
    print(f"{'mean':<10} {mechanical_mean:>11.2f} {fmt(summary['judge_mean']):>7} {str(all_required):>9}")
    for note in judge_notes:
        print(f"note  {note}")
    return summary


def fmt(value):
    return "-" if value is None else f"{value:.2f}"


def main(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("usage: summarize.py RESULTS_DIR [RESULTS_DIR ...]")
    failed = False
    valid_summaries = []
    for raw in argv:
        result_dir = Path(raw)
        try:
            result_dir = result_dir.resolve()
            valid_summaries.append(summarize(result_dir))
        except Exception as exc:
            failed = True
            invalid = {
                "schema_version": SCHEMA_VERSION,
                "result_dir": str(result_dir),
                "runs": 0,
                "complete": False,
                "pass_all_required": False,
                "mechanical_mean": None,
                "judge_mean": None,
                "error": str(exc),
            }
            invalidation_error = invalidate_summary(result_dir, invalid)
            print(f"invalid eval result {result_dir}: {exc}", file=sys.stderr)
            if invalidation_error:
                print(f"invalid eval result {result_dir}: {invalidation_error}", file=sys.stderr)
    if len(valid_summaries) > 1:
        reference = json.dumps(valid_summaries[0]["comparison_key"], sort_keys=True)
        incompatible = [
            summary["result_dir"] for summary in valid_summaries[1:]
            if json.dumps(summary["comparison_key"], sort_keys=True) != reference
        ]
        if incompatible:
            failed = True
            print(
                "incompatible result bundles; comparison refused: " + ", ".join(incompatible),
                file=sys.stderr,
            )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
